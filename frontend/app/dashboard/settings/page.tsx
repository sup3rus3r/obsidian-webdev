"use client";

import { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { listVaultKeys, upsertVaultKey, deleteVaultKey, validateVaultKey } from "@/lib/api/vault";
import { getPreferences, updatePreferences } from "@/lib/api/settings";
import type { VaultKey, VaultKeyCreate, ProviderType, UserPreferences } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  KeyRound,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  ShieldCheck,
  Bot,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const PROVIDERS: { value: ProviderType; label: string; placeholder: string }[] = [
  { value: "anthropic", label: "Anthropic", placeholder: "sk-ant-…" },
  { value: "openai", label: "OpenAI", placeholder: "sk-…" },
  { value: "ollama", label: "Ollama (local)", placeholder: "http://localhost:11434" },
  { value: "lmstudio", label: "LM Studio (local)", placeholder: "http://localhost:1234" },
  { value: "obsidian-ai", label: "Obsidian AI (self-hosted)", placeholder: "http://localhost:8000" },
];

const EMPTY_OBSIDIAN = { url: "", api_key: "", api_secret: "" };
const EMPTY_LOCAL = { base_url: "", api_key: "" };

function AddKeyDialog({ onAdded }: { onAdded: (key: VaultKey) => void }) {
  const { data: session } = useSession();
  const [open, setOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [form, setForm] = useState<VaultKeyCreate>({
    provider: "anthropic",
    label: "",
    value: "",
  });
  const [obsidianCfg, setObsidianCfg] = useState(EMPTY_OBSIDIAN);
  const [localCfg, setLocalCfg] = useState(EMPTY_LOCAL);

  const selectedProvider = PROVIDERS.find((p) => p.value === form.provider);
  const isObsidian = form.provider === "obsidian-ai";
  const isLocal = form.provider === "ollama" || form.provider === "lmstudio";

  const isSubmitDisabled =
    isLoading ||
    !form.label.trim() ||
    (isObsidian
      ? !obsidianCfg.url.trim() || !obsidianCfg.api_key.trim()
      : isLocal
      ? !localCfg.base_url.trim()
      : !form.value.trim());

  const handleProviderChange = (v: string) => {
    setForm((f) => ({ ...f, provider: v as ProviderType, value: "" }));
    setObsidianCfg(EMPTY_OBSIDIAN);
    setLocalCfg(EMPTY_LOCAL);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!session?.accessToken) return;
    setIsLoading(true);
    try {
      const payload: VaultKeyCreate = isObsidian
        ? { ...form, value: JSON.stringify(obsidianCfg) }
        : isLocal
        ? { ...form, value: JSON.stringify({ base_url: localCfg.base_url.trim(), api_key: localCfg.api_key.trim() || undefined }) }
        : form;
      const key = await upsertVaultKey(payload, session.accessToken);
      toast.success("API key saved");
      onAdded(key);
      setOpen(false);
      setForm({ provider: "anthropic", label: "", value: "" });
      setObsidianCfg(EMPTY_OBSIDIAN);
      setLocalCfg(EMPTY_LOCAL);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save key");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-1.5">
          <Plus className="h-4 w-4" />
          Add key
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>Add API key</DialogTitle>
          <DialogDescription>
            Keys are AES-encrypted at rest. The raw value is never stored.
          </DialogDescription>
        </DialogHeader>

        <form id="add-key-form" onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>Provider</Label>
            <Select value={form.provider} onValueChange={handleProviderChange}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map(({ value, label }) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="key-label">Label</Label>
            <Input
              id="key-label"
              placeholder="e.g. Production key"
              value={form.label}
              onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              required
            />
          </div>

          {isObsidian ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="obs-url">Base URL</Label>
                <Input
                  id="obs-url"
                  type="url"
                  placeholder="http://localhost:8000"
                  value={obsidianCfg.url}
                  onChange={(e) => setObsidianCfg((c) => ({ ...c, url: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="obs-key">API Key</Label>
                <Input
                  id="obs-key"
                  type="password"
                  placeholder="X-API-Key value"
                  value={obsidianCfg.api_key}
                  onChange={(e) => setObsidianCfg((c) => ({ ...c, api_key: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="obs-secret">API Secret</Label>
                <Input
                  id="obs-secret"
                  type="password"
                  placeholder="X-API-Secret value (optional)"
                  value={obsidianCfg.api_secret}
                  onChange={(e) => setObsidianCfg((c) => ({ ...c, api_secret: e.target.value }))}
                />
              </div>
            </>
          ) : isLocal ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="local-url">Endpoint URL</Label>
                <Input
                  id="local-url"
                  type="url"
                  placeholder={selectedProvider?.placeholder}
                  value={localCfg.base_url}
                  onChange={(e) => setLocalCfg((c) => ({ ...c, base_url: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="local-apikey">API Key <span className="text-muted-foreground font-normal">(optional)</span></Label>
                <Input
                  id="local-apikey"
                  type="password"
                  placeholder="Leave blank if not required"
                  value={localCfg.api_key}
                  onChange={(e) => setLocalCfg((c) => ({ ...c, api_key: e.target.value }))}
                />
              </div>
            </>
          ) : (
            <div className="space-y-1.5">
              <Label htmlFor="key-value">API Key</Label>
              <Input
                id="key-value"
                type="password"
                placeholder={selectedProvider?.placeholder}
                value={form.value}
                onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
                required
              />
            </div>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} type="button">
            Cancel
          </Button>
          <Button
            type="submit"
            form="add-key-form"
            disabled={isSubmitDisabled}
            className="gap-1.5"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ShieldCheck className="h-4 w-4" />
            )}
            Save key
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function VaultKeyRow({
  vaultKey,
  onDelete,
}: {
  vaultKey: VaultKey;
  onDelete: (id: string) => void;
}) {
  const { data: session } = useSession();
  const [validating, setValidating] = useState(false);
  const [validState, setValidState] = useState<boolean | null>(null);

  const handleValidate = async () => {
    if (!session?.accessToken) return;
    setValidating(true);
    try {
      const res = await validateVaultKey(vaultKey.provider as ProviderType, session.accessToken);
      setValidState(res.valid);
      toast[res.valid ? "success" : "error"](res.message);
    } catch {
      toast.error("Validation failed");
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="flex items-center gap-4 rounded-lg border bg-card px-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
        <KeyRound className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium truncate">{vaultKey.label}</span>
          <Badge variant="outline" className="text-[10px] capitalize">
            {vaultKey.provider}
          </Badge>
          {validState !== null && (
            validState ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
            ) : (
              <XCircle className="h-3.5 w-3.5 text-destructive" />
            )
          )}
        </div>
        <p className="text-[11px] text-muted-foreground">
          Added {formatDistanceToNow(
            new Date(vaultKey.created_at.endsWith("Z") ? vaultKey.created_at : vaultKey.created_at + "Z"),
            { addSuffix: true },
          )}
        </p>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={handleValidate}
          disabled={validating}
        >
          {validating ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            "Test"
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-destructive"
          onClick={() => onDelete(vaultKey.provider)}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

const PREF_DEFAULTS: UserPreferences = {
  permission_mode:   "ask",
  compact_threshold: 0.80,
  max_bash_lines:    400,
  max_file_lines:    500,
  max_web_chars:     20_000,
};

function AgentPreferencesSection() {
  const { data: session } = useSession();
  const [prefs, setPrefs] = useState<UserPreferences>(PREF_DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!session?.accessToken) return;
    getPreferences(session.accessToken)
      .then(setPrefs)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [session?.accessToken]);

  const handleSave = async () => {
    if (!session?.accessToken) return;
    setSaving(true);
    try {
      const saved = await updatePreferences(prefs, session.accessToken);
      setPrefs(saved);
      toast.success("Preferences saved");
    } catch {
      toast.error("Failed to save preferences");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border bg-card">
      <div className="flex items-center gap-3 border-b px-6 py-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
          <Bot className="h-4 w-4 text-muted-foreground" />
        </div>
        <div>
          <p className="text-sm font-semibold">Agent</p>
          <p className="text-xs text-muted-foreground">Default behaviour for the coding agent.</p>
        </div>
      </div>

      <div className="px-6 py-5 space-y-5">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-8 rounded-md" />
            ))}
          </div>
        ) : (
          <>

            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium">Permission mode</p>
                <p className="text-xs text-muted-foreground">Whether the agent asks before running write/bash tools.</p>
              </div>
              <div className="flex shrink-0 rounded-lg border border-border/50 p-0.5 text-xs">
                {(["ask", "auto"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setPrefs((p) => ({ ...p, permission_mode: mode }))}
                    className={cn(
                      "rounded-md px-3 py-1 capitalize transition-colors",
                      prefs.permission_mode === mode
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            <Separator />


            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium">Compaction trigger</p>
                <p className="text-xs text-muted-foreground">% of context window at which history is compacted.</p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <Input
                  type="number"
                  min={50}
                  max={95}
                  className="h-8 w-16 text-center text-sm"
                  value={Math.round(prefs.compact_threshold * 100)}
                  onChange={(e) => {
                    const v = Math.max(50, Math.min(95, Number(e.target.value)));
                    setPrefs((p) => ({ ...p, compact_threshold: v / 100 }));
                  }}
                />
                <span className="text-xs text-muted-foreground">%</span>
              </div>
            </div>

            <Separator />


            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Bash output limit</Label>
                <div className="flex items-center gap-1.5">
                  <Input
                    type="number"
                    min={50}
                    max={2000}
                    className="h-8 text-sm"
                    value={prefs.max_bash_lines}
                    onChange={(e) => setPrefs((p) => ({ ...p, max_bash_lines: Math.max(50, Math.min(2000, Number(e.target.value))) }))}
                  />
                  <span className="shrink-0 text-xs text-muted-foreground">lines</span>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">File read limit</Label>
                <div className="flex items-center gap-1.5">
                  <Input
                    type="number"
                    min={50}
                    max={2000}
                    className="h-8 text-sm"
                    value={prefs.max_file_lines}
                    onChange={(e) => setPrefs((p) => ({ ...p, max_file_lines: Math.max(50, Math.min(2000, Number(e.target.value))) }))}
                  />
                  <span className="shrink-0 text-xs text-muted-foreground">lines</span>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Web fetch limit</Label>
                <div className="flex items-center gap-1.5">
                  <Input
                    type="number"
                    min={5000}
                    max={100000}
                    step={1000}
                    className="h-8 text-sm"
                    value={prefs.max_web_chars}
                    onChange={(e) => setPrefs((p) => ({ ...p, max_web_chars: Math.max(5000, Math.min(100_000, Number(e.target.value))) }))}
                  />
                  <span className="shrink-0 text-xs text-muted-foreground">chars</span>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <Button size="sm" onClick={handleSave} disabled={saving} className="gap-1.5">
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Save
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}


export default function SettingsPage() {
  const { data: session } = useSession();
  const [keys, setKeys] = useState<VaultKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    if (!session?.accessToken) {
      setLoading(false);
      return;
    }
    setFetchError(null);
    try {
      const data = await listVaultKeys(session.accessToken);
      setKeys(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load API keys";
      setFetchError(msg);
    } finally {
      setLoading(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleAdded = (key: VaultKey) => {
    setKeys((prev) => {
      const exists = prev.findIndex((k) => k.id === key.id);
      if (exists >= 0) {
        const updated = [...prev];
        updated[exists] = key;
        return updated;
      }
      return [key, ...prev];
    });
  };

  const handleDelete = async (provider: string) => {
    if (!session?.accessToken) return;
    try {
      await deleteVaultKey(provider, session.accessToken);
      setKeys((prev) => prev.filter((k) => k.provider !== provider));
      toast.success("Key removed");
    } catch {
      toast.error("Failed to delete key");
    }
  };

  return (
    <div className="flex flex-1 flex-col min-h-0">
      <header className="flex h-14 shrink-0 items-center gap-4 border-b px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="h-5" />
        <h1 className="text-sm font-semibold">Settings</h1>
        <div className="ml-auto">
          <AddKeyDialog onAdded={handleAdded} />
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="space-y-8">

        <div>
          <h2 className="text-sm font-semibold mb-1">API Keys</h2>
          <p className="text-xs text-muted-foreground mb-4">
            Store your AI provider keys here. Keys are AES-encrypted at rest — the raw value is never accessible after saving.
          </p>

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-[60px] rounded-lg" />
            ))}
          </div>
        ) : fetchError ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-destructive/30 py-12 text-center">
            <XCircle className="h-8 w-8 text-destructive/50 mb-3" />
            <p className="text-sm font-medium text-destructive">Could not load API keys</p>
            <p className="mt-1 text-xs text-muted-foreground max-w-xs">
              Make sure the backend is running at{" "}
              <span className="font-mono">{process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100"}</span>
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={fetchKeys}
            >
              Retry
            </Button>
          </div>
        ) : keys.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
              <KeyRound className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="mt-4 text-sm font-semibold">No API keys</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Add an API key so Obsidian WebDev can call your preferred models.
            </p>
            <div className="mt-6">
              <AddKeyDialog onAdded={handleAdded} />
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {keys.map((key) => (
              <VaultKeyRow key={key.id} vaultKey={key} onDelete={handleDelete} />
            ))}
          </div>
        )}
        </div>

        <AgentPreferencesSection />

        </div>
      </main>
    </div>
  );
}
