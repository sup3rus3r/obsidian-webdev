import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { encryptPayload } from "@/lib/crypto-server";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) {
          return null;
        }

        try {
          const encryptedData = encryptPayload({
            username: credentials.username,
            password: credentials.password,
          });

          const res = await fetch("http://localhost:8100/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ encrypted: encryptedData }),
          });

          if (!res.ok) {
            return null;
          }

          const data = await res.json();
          return {
            id: data.user.id.toString(),
            name: data.user.username,
            email: data.user.email,
            role: data.user.role,
            accessToken: data.access_token,
          };
        } catch (error) {
          console.error("Auth error:", error);
          return null;
        }
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user, trigger, session }) {
      // Initial sign-in
      if (user) {
        token.id = user.id;
        token.role = user.role;
        token.accessToken = user.accessToken;
        // Store expiry: 30 min from now, refresh 2 min early
        token.accessTokenExpires = Date.now() + (30 * 60 - 120) * 1000;
      }

      // Manual session update (e.g. role toggle)
      if (trigger === "update" && session) {
        if (session.name) token.name = session.name;
        if (session.role) token.role = session.role;
        if (session.accessToken) {
          token.accessToken = session.accessToken;
          token.accessTokenExpires = Date.now() + (30 * 60 - 120) * 1000;
        }
      }

      // Proactive refresh: token still valid but expiry approaching
      if (token.accessToken && token.accessTokenExpires && Date.now() < token.accessTokenExpires) {
        return token;
      }

      // Token expired or expiry unknown — attempt refresh
      if (token.accessToken) {
        try {
          const res = await fetch("http://localhost:8100/auth/refresh", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${token.accessToken}`,
            },
          });
          if (res.ok) {
            const data = await res.json();
            token.accessToken = data.access_token;
            token.accessTokenExpires = Date.now() + (data.expires_in - 120) * 1000;
          }
        } catch {
          // Refresh failed — token will be invalid, user will need to re-login
        }
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as string;
      }
      session.accessToken = token.accessToken as string;
      return session;
    },
  },
});
