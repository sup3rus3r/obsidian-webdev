import { apiFetch } from "./client";

export interface UserDetails {
  id: string;
  username: string;
  email: string;
  role: string | null;
  auth_type: string;
  client_name: string | null;
}

export interface UpdateProfilePayload {
  username?: string;
  email?: string;
}

export interface UpdateProfileResponse {
  id: string;
  username: string;
  email: string;
  role: string;
}

export async function getUserDetails(token: string): Promise<UserDetails> {
  return apiFetch<UserDetails>("/get_user_details", { token });
}

export async function updateProfile(
  payload: UpdateProfilePayload,
  token: string,
): Promise<UpdateProfileResponse> {
  return apiFetch<UpdateProfileResponse>("/user/profile", {
    method: "PUT",
    body: payload,
    token,
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
  token: string,
): Promise<void> {
  return apiFetch<void>("/user/password", {
    method: "PUT",
    body: { current_password: currentPassword, new_password: newPassword },
    token,
  });
}
