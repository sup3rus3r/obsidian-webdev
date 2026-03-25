"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import {
  GitBranch,
  GitCommit,
  ArrowDown,
  ArrowUp,
  RefreshCw,
  Loader2,
  Check,
  Plus,
  ChevronDown,
  Circle,
  AlertTriangle,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SSHKeySetup } from "./ssh-key-setup";
import {
  gitStatus,
  gitLog,
  gitBranches,
  gitPull,
  gitPush,
  gitCommit,
  gitCheckout,
  gitInit,
  gitClone,
} from "@/lib/api/git";
import { getSSHPublicKey } from "@/lib/api/vault";
import type { GitStatus, GitCommit as GitCommitType, GitBranches, Project } from "@/types/api";
import { cn } from "@/lib/utils";

type GitTab = "changes" | "log" | "branches" | "ssh";

interface GitPanelProps {
  projectId: string;
  containerRunning: boolean;
  project?: Project | null;
}

export function GitPanel({ projectId, containerRunning, project }: GitPanelProps) {
  const { data: session } = useSession();
  const [tab, setTab] = useState<GitTab>("changes");
  const [status, setStatus] = useState<GitStatus | null>(null);
  const [log, setLog] = useState<GitCommitType[]>([]);
  const [branches, setBranches] = useState<GitBranches | null>(null);
  const [loading, setLoading] = useState(false);
  const [commitMsg, setCommitMsg] = useState("");
  const [committing, setCommitting] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [initing, setIniting] = useState(false);
  const [newBranch, setNewBranch] = useState("");
  const [showNewBranch, setShowNewBranch] = useState(false);
  const [cloneUrl, setCloneUrl] = useState(project?.github_url ?? project?.remote_url ?? "");
  const [cloning, setCloning] = useState(false);
  const [hasSSHKey, setHasSSHKey] = useState<boolean | null>(null);

  const token = session?.accessToken as string | undefined;

  // Check whether an SSH key exists for this project (needed for private repos)
  useEffect(() => {
    if (!token || !containerRunning) return;
    getSSHPublicKey(projectId, token)
      .then(() => setHasSSHKey(true))
      .catch(() => setHasSSHKey(false));
  }, [projectId, token, containerRunning]);

  const refresh = useCallback(async () => {
    if (!token || !containerRunning) return;
    setLoading(true);
    try {
      const [s, l, b] = await Promise.all([
        gitStatus(projectId, token),
        gitLog(projectId, token),
        gitBranches(projectId, token),
      ]);
      setStatus(s);
      setLog(l);
      setBranches(b);
    } catch {
      // container may not be running yet — fail silently
    } finally {
      setLoading(false);
    }
  }, [projectId, token, containerRunning]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleInit = async () => {
    if (!token) return;
    setIniting(true);
    try {
      await gitInit(projectId, token);
      toast.success("Git repository initialized");
      await refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Init failed");
    } finally {
      setIniting(false);
    }
  };

  const handleClone = async () => {
    if (!token || !cloneUrl.trim()) return;
    setCloning(true);
    try {
      await gitClone(projectId, cloneUrl.trim(), token);
      toast.success("Repository cloned");
      await refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Clone failed");
    } finally {
      setCloning(false);
    }
  };

  const handleCommit = async () => {
    if (!token || !commitMsg.trim()) return;
    setCommitting(true);
    try {
      await gitCommit(projectId, commitMsg.trim(), token);
      setCommitMsg("");
      toast.success("Changes committed");
      await refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Commit failed");
    } finally {
      setCommitting(false);
    }
  };

  const handlePull = async () => {
    if (!token) return;
    setPulling(true);
    try {
      const res = await gitPull(projectId, token);
      toast.success(res.output || "Pulled successfully");
      await refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Pull failed");
    } finally {
      setPulling(false);
    }
  };

  const handlePush = async () => {
    if (!token) return;
    setPushing(true);
    try {
      const res = await gitPush(projectId, token);
      toast.success(res.output || "Pushed successfully");
      await refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Push failed");
    } finally {
      setPushing(false);
    }
  };

  const handleCheckout = async (branch: string, create = false) => {
    if (!token) return;
    try {
      await gitCheckout(projectId, branch, create, token);
      toast.success(`Switched to ${branch}`);
      setNewBranch("");
      setShowNewBranch(false);
      await refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Checkout failed");
    }
  };

  const statusColor = (xy: string) => {
    const code = xy.trim()[0] ?? "?";
    if (code === "M") return "text-yellow-500";
    if (code === "A") return "text-green-500";
    if (code === "D") return "text-destructive";
    if (code === "?") return "text-muted-foreground";
    return "text-foreground";
  };

  const statusLabel = (xy: string) => {
    const code = xy.trim()[0] ?? "?";
    if (code === "M") return "M";
    if (code === "A") return "A";
    if (code === "D") return "D";
    if (code === "R") return "R";
    if (code === "?") return "U";
    return code;
  };

  if (!containerRunning) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 p-4 text-center">
        <GitBranch className="h-4 w-4 text-muted-foreground/40" />
        <p className="text-[11px] text-muted-foreground">Start the container to use git</p>
      </div>
    );
  }

  if (!status?.initialized) {
    const isSSHUrl = cloneUrl.startsWith("git@") || cloneUrl.startsWith("ssh://");
    const needsSSH = isSSHUrl && hasSSHKey === false;

    return (
      <div className="flex flex-col gap-3 p-3">
        <div className="flex flex-col gap-2 py-2">
          <GitBranch className="h-5 w-5 text-muted-foreground/40 self-center" />
          <p className="text-center text-[11px] text-muted-foreground">No git repository in this workspace.</p>

          {/* Clone section */}
          <div className="flex flex-col gap-1.5 mt-1">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Clone a repository</p>
            <Input
              value={cloneUrl}
              onChange={(e) => setCloneUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !needsSSH && handleClone()}
              placeholder="https://github.com/… or git@github.com:…"
              className="h-7 text-[11px] font-mono"
            />

            {/* SSH warning */}
            {needsSSH && (
              <div className="flex items-start gap-1.5 rounded-md border border-yellow-500/30 bg-yellow-500/10 px-2 py-1.5">
                <AlertTriangle className="h-3 w-3 shrink-0 text-yellow-500 mt-0.5" />
                <p className="text-[10px] text-yellow-600 dark:text-yellow-400 leading-snug">
                  SSH URL — generate a key in the <button className="underline" onClick={() => setTab("ssh")}>SSH tab</button> and add it to GitHub first.
                </p>
              </div>
            )}
            {/* HTTPS private repo hint */}
            {!isSSHUrl && cloneUrl.startsWith("https://") && (
              <p className="text-[10px] text-muted-foreground leading-snug">
                Private repo? Save a GitHub PAT in <span className="font-medium">Settings → Add key → GitHub (PAT)</span>.
              </p>
            )}

            <Button
              size="sm"
              className="h-7 gap-1.5 text-[11px] w-full"
              onClick={handleClone}
              disabled={cloning || !cloneUrl.trim() || needsSSH}
            >
              {cloning ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
              Clone repository
            </Button>
          </div>

          <div className="flex items-center gap-2 my-1">
            <div className="flex-1 border-t" />
            <span className="text-[10px] text-muted-foreground">or</span>
            <div className="flex-1 border-t" />
          </div>

          <Button
            size="sm"
            variant="outline"
            className="h-7 gap-1.5 text-[11px]"
            onClick={handleInit}
            disabled={initing || loading}
          >
            {initing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
            Initialize empty repository
          </Button>
        </div>
        <div className="border-t pt-3">
          <SSHKeySetup projectId={projectId} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex h-8 shrink-0 items-center justify-between border-b px-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <GitBranch className="h-3 w-3 text-muted-foreground shrink-0" />
          <span className="truncate text-[11px] font-medium text-foreground">
            {status.branch ?? "HEAD"}
          </span>
          {(status.ahead > 0 || status.behind > 0) && (
            <span className="flex items-center gap-0.5 text-[10px] text-muted-foreground shrink-0">
              {status.ahead > 0 && (
                <span className="flex items-center gap-0.5 text-green-500">
                  <ArrowUp className="h-2.5 w-2.5" />{status.ahead}
                </span>
              )}
              {status.behind > 0 && (
                <span className="flex items-center gap-0.5 text-yellow-500">
                  <ArrowDown className="h-2.5 w-2.5" />{status.behind}
                </span>
              )}
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5"
            title="Pull"
            onClick={handlePull}
            disabled={pulling}
          >
            {pulling ? <Loader2 className="h-3 w-3 animate-spin" /> : <ArrowDown className="h-3 w-3" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5"
            title="Push"
            onClick={handlePush}
            disabled={pushing}
          >
            {pushing ? <Loader2 className="h-3 w-3 animate-spin" /> : <ArrowUp className="h-3 w-3" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5"
            title="Refresh"
            onClick={refresh}
            disabled={loading}
          >
            {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
          </Button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex shrink-0 border-b">
        {(["changes", "log", "branches", "ssh"] as GitTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "flex-1 py-1 text-[10px] font-medium capitalize transition-colors",
              tab === t
                ? "border-b-2 border-primary text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t === "changes" && status.files.length > 0
              ? `Changes (${status.files.length})`
              : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {tab === "changes" && (
          <div className="flex flex-col gap-2 p-2">
            {/* Commit input */}
            <div className="flex gap-1">
              <Input
                value={commitMsg}
                onChange={(e) => setCommitMsg(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleCommit()}
                placeholder="Commit message…"
                className="h-7 text-[11px] font-mono"
              />
              <Button
                size="sm"
                className="h-7 w-7 p-0 shrink-0"
                onClick={handleCommit}
                disabled={committing || !commitMsg.trim()}
                title="Commit all changes"
              >
                {committing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
              </Button>
            </div>

            {/* File list */}
            {status.files.length === 0 ? (
              <p className="py-3 text-center text-[11px] text-muted-foreground">
                Working tree is clean
              </p>
            ) : (
              <div className="flex flex-col gap-0.5">
                {status.files.map((f) => (
                  <div key={f.path} className="flex items-center gap-1.5 rounded px-1 py-0.5 hover:bg-muted/30">
                    <span className={cn("w-3 shrink-0 text-[10px] font-bold font-mono", statusColor(f.status))}>
                      {statusLabel(f.status)}
                    </span>
                    <span className="truncate font-mono text-[10px] text-foreground/80">{f.path}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "log" && (
          <div className="flex flex-col">
            {log.length === 0 ? (
              <p className="py-3 text-center text-[11px] text-muted-foreground">No commits yet</p>
            ) : (
              log.map((c) => (
                <div key={c.hash} className="flex items-start gap-2 border-b border-border/30 px-2 py-1.5 hover:bg-muted/20">
                  <GitCommit className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/50" />
                  <div className="min-w-0">
                    <p className="truncate text-[11px] text-foreground">{c.message}</p>
                    <p className="text-[10px] text-muted-foreground">
                      <span className="font-mono">{c.short_hash}</span>
                      {" · "}{c.author}{" · "}{c.ago}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "branches" && (
          <div className="flex flex-col gap-2 p-2">
            {/* New branch */}
            {showNewBranch ? (
              <div className="flex gap-1">
                <Input
                  autoFocus
                  value={newBranch}
                  onChange={(e) => setNewBranch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCheckout(newBranch, true);
                    if (e.key === "Escape") { setShowNewBranch(false); setNewBranch(""); }
                  }}
                  placeholder="new-branch-name"
                  className="h-7 text-[11px] font-mono"
                />
                <Button size="sm" className="h-7 w-7 p-0 shrink-0" onClick={() => handleCheckout(newBranch, true)}>
                  <Check className="h-3 w-3" />
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="h-7 gap-1 text-[11px]"
                onClick={() => setShowNewBranch(true)}
              >
                <Plus className="h-3 w-3" /> New branch
              </Button>
            )}

            {/* Local branches */}
            {branches && branches.local.length > 0 && (
              <div>
                <p className="mb-1 px-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Local</p>
                {branches.local.map((b) => (
                  <button
                    key={b}
                    onClick={() => b !== branches.current && handleCheckout(b)}
                    className={cn(
                      "flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-[11px] text-left transition-colors",
                      b === branches.current
                        ? "text-foreground cursor-default"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/30",
                    )}
                  >
                    {b === branches.current ? (
                      <Circle className="h-2 w-2 fill-primary text-primary shrink-0" />
                    ) : (
                      <ChevronDown className="h-3 w-3 shrink-0 opacity-0" />
                    )}
                    <span className="truncate font-mono">{b}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Remote branches */}
            {branches && branches.remote.length > 0 && (
              <div>
                <p className="mb-1 px-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Remote</p>
                {branches.remote.map((b) => (
                  <div key={b} className="flex items-center gap-1.5 rounded px-1.5 py-1">
                    <GitBranch className="h-3 w-3 shrink-0 text-muted-foreground/50" />
                    <span className="truncate font-mono text-[11px] text-muted-foreground">{b}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "ssh" && (
          <SSHKeySetup projectId={projectId} />
        )}
      </div>
    </div>
  );
}
