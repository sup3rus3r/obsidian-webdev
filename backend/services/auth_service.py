"""Auth business logic — keeps routers thin."""
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from core.security import (
    create_access_token,
    get_password_hash,
    generate_client_credentials,
    hash_client_secret,
    verify_password,
    verify_client_secret,
)
from core.crypto import decrypt_payload
from schemas.auth import (
    UserResponse,
    LoginResponse,
    APIClientCreateResponse,
    APIClientListResponse,
    APIClientResponse,
    UserDetailsResponse,
    ToggleRoleResponse,
    UpdateProfileResponse,
)


class AuthService:

    @staticmethod
    async def register_user(encrypted: str, db: Session) -> UserResponse:
        try:
            data = decrypt_payload(encrypted)
            username = data["username"]
            email = data["email"]
            password = data["password"]
            role = data.get("role", "guest")
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid encrypted data")

        if len(password.encode("utf-8")) > 72:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password too long (max 72 bytes)")

        if settings.DATABASE_TYPE == "mongo":
            return await AuthService._register_mongo(username, email, password, role)

        return AuthService._register_sql(username, email, password, role, db)

    @staticmethod
    def _register_sql(username: str, email: str, password: str, role: str, db: Session) -> UserResponse:
        from models.sql_models import User

        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already registered")
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

        user = User(
            username=username,
            email=email,
            role=role,
            hashed_password=get_password_hash(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return UserResponse(id=str(user.id), username=user.username, email=user.email, role=user.role)

    @staticmethod
    async def _register_mongo(username: str, email: str, password: str, role: str) -> UserResponse:
        from database.mongo import get_database
        from models.mongo_models import UserCollection

        mongo_db = get_database()
        if await UserCollection.find_by_username(mongo_db, username):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already registered")
        if await UserCollection.find_by_email(mongo_db, email):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

        user = await UserCollection.create(mongo_db, {
            "username": username,
            "email": email,
            "role": role,
            "hashed_password": get_password_hash(password),
        })
        return UserResponse(id=str(user["_id"]), username=user["username"], email=user["email"], role=user["role"])


    @staticmethod
    async def login_user(encrypted: str, db: Session) -> LoginResponse:
        try:
            data = decrypt_payload(encrypted)
            username = data["username"]
            password = data["password"]
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid encrypted data")

        if settings.DATABASE_TYPE == "mongo":
            return await AuthService._login_mongo(username, password)

        return AuthService._login_sql(username, password, db)

    @staticmethod
    def _login_sql(username: str, password: str, db: Session) -> LoginResponse:
        from models.sql_models import User

        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

        token = create_access_token(
            data={"user_id": str(user.id), "username": user.username, "role": user.role, "token_type": "user"},
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(id=str(user.id), username=user.username, email=user.email, role=user.role),
        )

    @staticmethod
    async def _login_mongo(username: str, password: str) -> LoginResponse:
        from database.mongo import get_database
        from models.mongo_models import UserCollection

        mongo_db = get_database()
        user = await UserCollection.find_by_username(mongo_db, username)
        if not user or not verify_password(password, user["hashed_password"]):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

        token = create_access_token(
            data={"user_id": str(user["_id"]), "username": user["username"], "role": user["role"], "token_type": "user"},
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(id=str(user["_id"]), username=user["username"], email=user["email"], role=user["role"]),
        )


    @staticmethod
    async def get_user_details(user_id: str, db: Session) -> UserDetailsResponse:
        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import UserCollection
            mongo_db = get_database()
            user = await UserCollection.find_by_id(mongo_db, user_id)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
            return UserDetailsResponse(
                id=str(user["_id"]), username=user["username"], email=user["email"],
                role=user["role"], auth_type="user",
            )
        from models.sql_models import User
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        return UserDetailsResponse(
            id=str(user.id), username=user.username, email=user.email,
            role=user.role, auth_type="user",
        )


    @staticmethod
    async def toggle_role(user_id: str, current_role: str, username: str, db: Session) -> ToggleRoleResponse:
        new_role = "guest" if current_role == "admin" else "admin"

        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import UserCollection
            mongo_db = get_database()
            user = await UserCollection.update_role(mongo_db, user_id, new_role)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
            return AuthService._build_toggle_response(str(user["_id"]), user["username"], user["email"], new_role, current_role)

        from models.sql_models import User
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        user.role = new_role
        db.commit()
        db.refresh(user)
        return AuthService._build_toggle_response(str(user.id), user.username, user.email, new_role, current_role)

    @staticmethod
    def _build_toggle_response(user_id: str, username: str, email: str, new_role: str, old_role: str) -> ToggleRoleResponse:
        token = create_access_token(
            data={"user_id": user_id, "username": username, "role": new_role, "token_type": "user"},
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return ToggleRoleResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(id=user_id, username=username, email=email, role=new_role),
            message=f"Role changed from '{old_role}' to '{new_role}'",
        )


    @staticmethod
    async def update_profile(
        user_id: str,
        username: str | None,
        email: str | None,
        db: Session,
    ) -> UpdateProfileResponse:
        if settings.DATABASE_TYPE == "mongo":
            return await AuthService._update_profile_mongo(user_id, username, email)
        return AuthService._update_profile_sql(user_id, username, email, db)

    @staticmethod
    def _update_profile_sql(
        user_id: str,
        username: str | None,
        email: str | None,
        db: Session,
    ) -> UpdateProfileResponse:
        from models.sql_models import User

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        if username and username != user.username:
            if db.query(User).filter(User.username == username).first():
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")
            user.username = username

        if email and email != user.email:
            if db.query(User).filter(User.email == email).first():
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already in use")
            user.email = email

        db.commit()
        db.refresh(user)
        return UpdateProfileResponse(id=str(user.id), username=user.username, email=user.email, role=user.role)

    @staticmethod
    async def _update_profile_mongo(
        user_id: str,
        username: str | None,
        email: str | None,
    ) -> UpdateProfileResponse:
        from database.mongo import get_database
        from models.mongo_models import UserCollection

        mongo_db = get_database()
        user = await UserCollection.find_by_id(mongo_db, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        updates: dict = {}
        if username and username != user["username"]:
            if await UserCollection.find_by_username(mongo_db, username):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")
            updates["username"] = username

        if email and email != user["email"]:
            if await UserCollection.find_by_email(mongo_db, email):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already in use")
            updates["email"] = email

        if updates:
            await mongo_db[UserCollection.collection_name].update_one(
                {"_id": user["_id"]}, {"$set": updates}
            )
            user.update(updates)

        return UpdateProfileResponse(
            id=str(user["_id"]), username=user["username"], email=user["email"], role=user["role"]
        )


    @staticmethod
    async def change_password(
        user_id: str,
        current_password: str,
        new_password: str,
        db: Session,
    ) -> dict:
        if len(new_password.encode("utf-8")) > 72:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password too long (max 72 bytes)")

        if settings.DATABASE_TYPE == "mongo":
            return await AuthService._change_password_mongo(user_id, current_password, new_password)
        return AuthService._change_password_sql(user_id, current_password, new_password, db)

    @staticmethod
    def _change_password_sql(
        user_id: str,
        current_password: str,
        new_password: str,
        db: Session,
    ) -> dict:
        from models.sql_models import User

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")

        user.hashed_password = get_password_hash(new_password)
        db.commit()
        return {"message": "Password updated successfully"}

    @staticmethod
    async def _change_password_mongo(
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> dict:
        from database.mongo import get_database
        from models.mongo_models import UserCollection

        mongo_db = get_database()
        user = await UserCollection.find_by_id(mongo_db, user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        if not verify_password(current_password, user["hashed_password"]):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")

        await mongo_db[UserCollection.collection_name].update_one(
            {"_id": user["_id"]},
            {"$set": {"hashed_password": get_password_hash(new_password)}},
        )
        return {"message": "Password updated successfully"}


    @staticmethod
    async def create_api_client(name: str, owner_id: str, db: Session) -> APIClientCreateResponse:
        from datetime import datetime, timezone
        client_id, client_secret = generate_client_credentials()
        hashed = hash_client_secret(client_secret)

        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import APIClientCollection
            mongo_db = get_database()
            doc = await APIClientCollection.create(mongo_db, {
                "name": name, "client_id": client_id, "hashed_secret": hashed,
                "created_by": owner_id, "is_active": True,
                "created_at": datetime.now(timezone.utc),
            })
            return APIClientCreateResponse(
                id=str(doc["_id"]), name=doc["name"], client_id=doc["client_id"],
                client_secret=client_secret, is_active=True, created_at=doc["created_at"],
            )

        from models.sql_models import APIClient
        client = APIClient(
            name=name, client_id=client_id, hashed_secret=hashed,
            created_by=int(owner_id), is_active=True,
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        return APIClientCreateResponse(
            id=str(client.id), name=client.name, client_id=client.client_id,
            client_secret=client_secret, is_active=client.is_active, created_at=client.created_at,
        )

    @staticmethod
    async def list_api_clients(owner_id: str, db: Session) -> APIClientListResponse:
        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import APIClientCollection
            mongo_db = get_database()
            clients = await APIClientCollection.find_by_user(mongo_db, owner_id)
            return APIClientListResponse(clients=[
                APIClientResponse(id=str(c["_id"]), name=c["name"], client_id=c["client_id"],
                                  is_active=c.get("is_active", True), created_at=c["created_at"])
                for c in clients
            ])

        from models.sql_models import APIClient
        clients = db.query(APIClient).filter(APIClient.created_by == int(owner_id)).all()
        return APIClientListResponse(clients=[
            APIClientResponse(id=str(c.id), name=c.name, client_id=c.client_id,
                              is_active=c.is_active, created_at=c.created_at)
            for c in clients
        ])

    @staticmethod
    async def revoke_api_client(client_id: str, owner_id: str, db: Session) -> dict:
        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import APIClientCollection
            mongo_db = get_database()
            ok = await APIClientCollection.deactivate(mongo_db, client_id, owner_id)
            if not ok:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "API client not found or already revoked")
            return {"message": "API client revoked successfully"}

        from models.sql_models import APIClient
        client = db.query(APIClient).filter(
            APIClient.client_id == client_id, APIClient.created_by == int(owner_id),
        ).first()
        if not client:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "API client not found")
        client.is_active = False
        db.commit()
        return {"message": "API client revoked successfully"}
