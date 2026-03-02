import { apiFetch } from "./client";
import type { UserPreferences } from "@/types/api";

export async function getPreferences(token: string): Promise<UserPreferences> {
  return apiFetch<UserPreferences>("/settings/preferences", { method: "GET", token });
}

export async function updatePreferences(
  prefs: Partial<UserPreferences>,
  token: string,
): Promise<UserPreferences> {
  return apiFetch<UserPreferences>("/settings/preferences", {
    method: "PUT",
    body: prefs,
    token,
  });
}
