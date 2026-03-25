import { apiFetch } from "./client";
import type {
  VaultKey,
  VaultKeyCreate,
  VaultKeyListResponse,
  VaultValidateResponse,
  ProviderType,
  SSHKeyResponse,
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

// --- SSH key endpoints ---

export async function generateSSHKey(
  projectId: string,
  token: string,
  label?: string,
): Promise<SSHKeyResponse> {
  return apiFetch<SSHKeyResponse>("/vault/ssh/generate", {
    method: "POST",
    body: { project_id: projectId, label },
    token,
  });
}

export async function getSSHPublicKey(
  projectId: string,
  token: string,
): Promise<SSHKeyResponse> {
  return apiFetch<SSHKeyResponse>(`/vault/ssh/public-key/${projectId}`, {
    method: "GET",
    token,
  });
}

export async function deleteSSHKey(
  projectId: string,
  token: string,
): Promise<void> {
  return apiFetch<void>(`/vault/ssh/${projectId}`, { method: "DELETE", token });
}
