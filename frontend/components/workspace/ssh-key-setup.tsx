"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Key, Copy, Check, Loader2, Trash2, RefreshCw, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { generateSSHKey, getSSHPublicKey, deleteSSHKey } from "@/lib/api/vault";
import type { SSHKeyResponse } from "@/types/api";

interface SSHKeySetupProps {
  projectId: string;
}

export function SSHKeySetup({ projectId }: SSHKeySetupProps) {
  const { data: session } = useSession();
  const [keyData, setKeyData] = useState<SSHKeyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadKey = useCallback(async () => {
    if (!session?.accessToken) return;
    setLoading(true);
    try {
      const data = await getSSHPublicKey(projectId, session.accessToken);
      setKeyData(data);
    } catch {
      // 404 = no key yet, that's fine
      setKeyData(null);
    } finally {
      setLoading(false);
    }
  }, [projectId, session?.accessToken]);

  useEffect(() => {
    loadKey();
  }, [loadKey]);

  const handleGenerate = async () => {
    if (!session?.accessToken) return;
    setGenerating(true);
    try {
      const data = await generateSSHKey(projectId, session.accessToken);
      setKeyData(data);
      if (!data.already_existed) {
        toast.success("SSH key generated — add the public key to GitHub/GitLab to enable push/pull");
      }
    } catch {
      toast.error("Failed to generate SSH key");
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!keyData?.public_key) return;
    await navigator.clipboard.writeText(keyData.public_key);
    setCopied(true);
    toast.success("Public key copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async () => {
    if (!session?.accessToken) return;
    setDeleting(true);
    try {
      await deleteSSHKey(projectId, session.accessToken);
      setKeyData(null);
      toast.success("SSH key removed");
    } catch {
      toast.error("Failed to remove SSH key");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-3">
      <div className="flex items-center gap-2">
        <Key className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
          SSH Key
        </span>
      </div>

      {keyData ? (
        <>
          <div className="rounded-md border border-border/50 bg-muted/20 p-2">
            <p className="mb-1.5 text-[10px] text-muted-foreground">Public key — add this to GitHub/GitLab</p>
            <pre className="whitespace-pre-wrap break-all font-mono text-[9px] text-foreground/80 leading-relaxed">
              {keyData.public_key}
            </pre>
          </div>

          <div className="flex gap-1.5">
            <Button
              size="sm"
              variant="outline"
              className="flex-1 h-7 gap-1.5 text-[11px]"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="h-3 w-3 text-green-500" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
              {copied ? "Copied!" : "Copy key"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
              title="Regenerate key"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
              title="Remove key"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Trash2 className="h-3 w-3" />
              )}
            </Button>
          </div>

          <a
            href="https://github.com/settings/ssh/new"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[10px] text-primary hover:underline"
          >
            <ExternalLink className="h-2.5 w-2.5" />
            Add to GitHub
          </a>
        </>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Generate an SSH key to enable git push/pull for private repositories.
          </p>
          <Button
            size="sm"
            className="h-7 gap-1.5 text-[11px] w-full"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Key className="h-3 w-3" />
            )}
            Generate SSH Key
          </Button>
        </div>
      )}
    </div>
  );
}
