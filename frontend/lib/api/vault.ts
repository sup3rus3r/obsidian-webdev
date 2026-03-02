import { apiFetch } from "./client";
import type {
  VaultKey,
  VaultKeyCreate,
  VaultKeyListResponse,
  VaultValidateResponse,
  ProviderType,
} from "@/types/api";

export async function listVaultKeys(token: string): Promise<VaultKey[]> {
  const res = await apiFetch<VaultKeyListResponse>("/vault/secrets", {
    method: "GET",
    token,
  });
  return res.secrets;
}

export async function upsertVaultKey(
  data: VaultKeyCreate,
  token: string,
): Promise<VaultKey> {
  return apiFetch<VaultKey>("/vault/secrets", { method: "POST", body: data, token });
}

export async function deleteVaultKey(
  provider: string,
  token: string,
): Promise<void> {
  return apiFetch<void>(`/vault/secrets/${provider}`, { method: "DELETE", token });
}

export async function validateVaultKey(
  provider: ProviderType,
  token: string,
): Promise<VaultValidateResponse> {
  return apiFetch<VaultValidateResponse>("/vault/secrets/validate", {
    method: "POST",
    body: { provider },
    token,
  });
}
