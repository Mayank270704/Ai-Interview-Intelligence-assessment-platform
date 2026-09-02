import { apiRequest } from "@/services/api/client";
import type { AuthSession, CurrentUser, SignUpResponse } from "@/services/api/types";

export async function signUp(email: string, password: string): Promise<SignUpResponse> {
  return apiRequest<SignUpResponse>("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function logIn(email: string, password: string): Promise<AuthSession> {
  return apiRequest<AuthSession>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function logOut(): Promise<void> {
  await apiRequest<void>("/auth/logout", { method: "POST" });
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/auth/me");
}
