"use client";

import { useRef, useEffect, useState, useCallback, memo } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAgentWs } from "@/lib/api/ws";
import type { ClientEvent, AgentSession } from "@/types/api";
import {
  createAgentSession,
  getAgentSession,
} from "@/lib/api/agent";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  CornerDownLeft,
  Square,
  Loader2,
  Terminal,
  Wrench,
  FileCode2,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Copy,
  Check,
  ChevronDown,
  Paperclip,
  ShieldQuestion,
  Zap,
  MessageSquare,
} from "lucide-react";
import { parseAttachment, type ParsedAttachment } from "@/lib/api/projects";


interface ModelOption {
  provider: string;
  model: string;
  label: string;
  badge: string;
}

// Cloud model presets — extend here to add new models, no other changes needed.
const CLOUD_PRESETS: ModelOption[] = [
  { provider: "openai",    model: "gpt-5.2",                   label: "GPT-5.2",        badge: "OpenAI"    },
  { provider: "openai",    model: "gpt-5.2-pro",               label: "GPT-5.2 pro",    badge: "OpenAI"    },
  { provider: "openai",    model: "gpt-5",                     label: "GPT-5",          badge: "OpenAI"    },
  { provider: "openai",    model: "gpt-5-pro",                 label: "GPT-5 pro",      badge: "OpenAI"    },
  { provider: "openai",    model: "gpt-5-mini",                label: "GPT-5 mini",     badge: "OpenAI"    },
  { provider: "openai",    model: "gpt-5-nano",                label: "GPT-5 nano",     badge: "OpenAI"    },
  { provider: "openai",    model: "gpt-4.1",                   label: "GPT-4.1",        badge: "OpenAI"    },
  { provider: "openai",    model: "gpt-4.1-mini",              label: "GPT-4.1 mini",   badge: "OpenAI"    },
  { provider: "openai",    model: "gpt-4.1-nano",              label: "GPT-4.1 nano",   badge: "OpenAI"    },
  { provider: "openai",    model: "o3",                        label: "o3",             badge: "OpenAI"    },
  { provider: "openai",    model: "o3-mini",                   label: "o3-mini",        badge: "OpenAI"    },
  { provider: "openai",    model: "o3-pro",                    label: "o3-pro",         badge: "OpenAI"    },
  { provider: "openai",    model: "o4-mini",                   label: "o4-mini",        badge: "OpenAI"    },
  { provider: "anthropic", model: "claude-sonnet-4-6",         label: "Claude Sonnet", badge: "Anthropic" },
  { provider: "anthropic", model: "claude-opus-4-6",           label: "Claude Opus",   badge: "Anthropic" },
  { provider: "anthropic", model: "claude-haiku-4-5-20251001", label: "Claude Haiku",  badge: "Anthropic" },
];

// Local / self-hosted providers — model name is free-text input, no presets.
const LOCAL_PROVIDERS = [
  { provider: "ollama",      badge: "Ollama"      },
  { provider: "lmstudio",    badge: "LM Studio"   },
  { provider: "obsidian-ai", badge: "Obsidian AI" },
] as const;

const LOCAL_PROVIDER_IDS = LOCAL_PROVIDERS.map((p) => p.provider);

const DEFAULT_MODEL = CLOUD_PRESETS[0];


type MessageRole =
  | "user"
  | "agent"
  | "tool"
  | "tool_result"
  | "approval"
  | "clarification"
  | "file"
  | "done"
  | "stopped"
  | "compacting"
  | "error";

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  streaming?: boolean;
  meta?: Record<string, unknown>;
}


function CodeBlock({ children, className }: { children?: React.ReactNode; className?: string }) {
  const [copied, setCopied] = useState(false);
  const lang = className?.replace("language-", "") ?? "code";
  const code = String(children).replace(/\n$/, "");
  return (
    <div className="group relative my-2 overflow-hidden rounded-lg border border-border/40 bg-[#0d0d0d]">
      <div className="flex items-center justify-between border-b border-border/25 bg-muted/10 px-3 py-1">
        <span className="text-[10px] font-mono text-muted-foreground/70">{lang}</span>
        <button
          onClick={() => {
            navigator.clipboard.writeText(code).catch(() => {});
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          }}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100"
        >
          {copied ? <><Check className="h-2.5 w-2.5" />Copied</> : <><Copy className="h-2.5 w-2.5" />Copy</>}
        </button>
      </div>
      <pre className="max-w-full overflow-x-auto p-3">
        <code className="font-mono text-[11px] leading-relaxed text-foreground/85">{code}</code>
      </pre>
    </div>
  );
}


function AgentMarkdown({ content, streaming }: { content: string; streaming?: boolean }) {
  return (
    <div className="min-w-0 max-w-full overflow-hidden text-xs leading-relaxed text-foreground/90">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children }) {
            if (className?.startsWith("language-")) {
              return <CodeBlock className={className}>{children}</CodeBlock>;
            }
            return (
              <code className="rounded bg-muted/70 px-1 py-0.5 font-mono text-[11px] text-foreground/90">
                {children}
              </code>
            );
          },
          p: ({ children }) => <p className="mb-1.5 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="mb-1.5 ml-4 list-disc space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="mb-1.5 ml-4 list-decimal space-y-0.5">{children}</ol>,
          li: ({ children }) => <li className="text-xs">{children}</li>,
          h1: ({ children }) => <h1 className="mb-1 mt-2 text-sm font-semibold">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-1 mt-2 text-xs font-semibold">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1 mt-2 text-xs font-medium">{children}</h3>,
          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
          blockquote: ({ children }) => (
            <blockquote className="my-1 border-l-2 border-primary/40 pl-2.5 text-muted-foreground">
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => (
            <a href={href} className="text-primary underline-offset-2 hover:underline" target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
      {streaming && (
        <span className="ml-0.5 inline-block h-3 w-1.5 animate-pulse rounded-sm bg-primary/70 align-middle" />
      )}
    </div>
  );
}


function formatParams(params: Record<string, unknown>): string {
  const truncated: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (typeof v === "string" && v.length > 200) {
      truncated[k] = v.slice(0, 200) + "…";
    } else {
      truncated[k] = v;
    }
  }
  return JSON.stringify(truncated, null, 2);
}


function ToolCallCard({ tool, params }: { tool: string; params: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen((o) => !o)}
      className="flex w-full items-start gap-2 rounded-lg border border-border/35 bg-muted/25 px-2.5 py-2 text-left transition-colors hover:bg-muted/40"
    >
      <Wrench className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1">
          <span className="font-mono text-[11px] font-medium text-foreground/75">{tool}</span>
          <ChevronRight className={cn("h-3 w-3 text-muted-foreground transition-transform", open && "rotate-90")} />
        </div>
        {open && (
          <pre className="mt-1.5 max-w-full overflow-x-auto whitespace-pre-wrap break-all text-[10px] text-muted-foreground">
            {formatParams(params)}
          </pre>
        )}
      </div>
    </button>
  );
}


function ToolResultCard({ tool, result, denied }: { tool: string; result: string; denied?: boolean }) {
  const [open, setOpen] = useState(false);
  const preview = result.split("\n").slice(0, 3).join("\n");
  const hasMore = result.split("\n").length > 3;
  return (
    <button
      onClick={() => setOpen((o) => !o)}
      className="flex w-full items-start gap-2 rounded-lg border border-border/25 bg-muted/10 px-2.5 py-1.5 text-left transition-colors hover:bg-muted/20"
    >
      <ChevronRight className={cn("mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/50 transition-transform", open && "rotate-90")} />
      <div className="min-w-0 flex-1">
        <span className="font-mono text-[10px] text-muted-foreground/50">
          {denied ? "denied" : "↳"} {tool}
        </span>
        <pre className={cn(
          "mt-0.5 max-w-full overflow-x-auto whitespace-pre-wrap break-all text-[10px]",
          denied ? "text-destructive/60" : "text-muted-foreground/60",
        )}>
          {open ? result : preview + (hasMore && !open ? "\n…" : "")}
        </pre>
      </div>
    </button>
  );
}


function ToolApprovalCard({
  msgId,
  approvalId,
  tool,
  params,
  status,
  onApprove,
  onDeny,
  onApproveAll,
}: {
  msgId: string;
  approvalId: string;
  tool: string;
  params: Record<string, unknown>;
  status?: string;
  onApprove?: (approvalId: string, msgId: string) => void;
  onDeny?: (approvalId: string, msgId: string) => void;
  onApproveAll?: (approvalId: string, msgId: string) => void;
}) {
  const [paramsOpen, setParamsOpen] = useState(false);

  if (status === "approved") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-green-500/20 bg-green-500/5 px-3 py-2">
        <CheckCircle2 className="h-3 w-3 shrink-0 text-green-400" />
        <span className="font-mono text-[11px] font-medium text-foreground/60">{tool}</span>
        <span className="ml-auto text-[10px] text-green-400">Approved</span>
      </div>
    );
  }

  if (status === "denied") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2">
        <XCircle className="h-3 w-3 shrink-0 text-destructive/60" />
        <span className="font-mono text-[11px] font-medium text-foreground/60">{tool}</span>
        <span className="ml-auto text-[10px] text-destructive/70">Denied</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-primary/30 bg-primary/5 p-3">
      <div className="mb-2 flex items-center gap-2">
        <ShieldQuestion className="h-3 w-3 text-primary" />
        <span className="text-[11px] font-semibold text-primary">Approval required</span>
      </div>
      <button
        onClick={() => setParamsOpen((o) => !o)}
        className="mb-2.5 flex w-full items-center gap-1.5 rounded-md border border-border/30 bg-background/50 px-2 py-1.5 text-left transition-colors hover:bg-background"
      >
        <Wrench className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className="font-mono text-[11px] text-foreground/80">{tool}</span>
        <ChevronRight className={cn("ml-auto h-3 w-3 text-muted-foreground transition-transform", paramsOpen && "rotate-90")} />
      </button>
      {paramsOpen && (
        <pre className="mb-2.5 max-w-full overflow-x-auto rounded bg-muted/20 p-2 text-[10px] text-muted-foreground whitespace-pre-wrap break-all">
          {formatParams(params)}
        </pre>
      )}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          className="h-6 flex-1 rounded-md border-green-500/30 bg-green-500/10 text-[11px] text-green-400 hover:bg-green-500/20"
          onClick={() => onApprove?.(approvalId, msgId)}
        >
          Approve
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-6 flex-1 rounded-md border-destructive/30 bg-destructive/10 text-[11px] text-destructive hover:bg-destructive/20"
          onClick={() => onDeny?.(approvalId, msgId)}
        >
          Deny
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-6 shrink-0 rounded-md px-2 text-[10px] text-muted-foreground hover:text-foreground"
          title="Approve this and all future tool calls"
          onClick={() => onApproveAll?.(approvalId, msgId)}
        >
          <Zap className="mr-1 h-2.5 w-2.5" />
          Approve all
        </Button>
      </div>
    </div>
  );
}


function ClarificationCard({
  msgId,
  clarificationId,
  question,
  status,
  answer,
  onSubmit,
}: {
  msgId: string;
  clarificationId: string;
  question: string;
  status?: string;
  answer?: string;
  onSubmit?: (clarificationId: string, msgId: string, answer: string) => void;
}) {
  const [text, setText] = useState("");

  if (status === "answered") {
    return (
      <div className="rounded-lg border border-border/30 bg-muted/10 px-3 py-2">
        <div className="flex items-center gap-1.5 mb-1">
          <MessageSquare className="h-3 w-3 text-muted-foreground/50" />
          <span className="text-[10px] text-muted-foreground/50">Agent asked</span>
        </div>
        <p className="text-[11px] text-foreground/60 mb-1">{question}</p>
        <p className="text-[11px] text-foreground/90 font-medium">{answer}</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-primary/30 bg-primary/5 p-3">
      <div className="mb-2 flex items-center gap-2">
        <MessageSquare className="h-3 w-3 text-primary" />
        <span className="text-[11px] font-semibold text-primary">Agent needs clarification</span>
      </div>
      <p className="mb-2.5 text-[11px] text-foreground/80">{question}</p>
      <div className="flex gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && text.trim()) {
              onSubmit?.(clarificationId, msgId, text.trim());
            }
          }}
          placeholder="Type your answer…"
          className="flex-1 rounded-md border border-border/40 bg-background/60 px-2.5 py-1.5 text-[11px] text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/40"
          autoFocus
        />
        <Button
          size="sm"
          variant="outline"
          className="h-7 shrink-0 rounded-md border-primary/30 bg-primary/10 text-[11px] text-primary hover:bg-primary/20"
          disabled={!text.trim()}
          onClick={() => onSubmit?.(clarificationId, msgId, text.trim())}
        >
          <CornerDownLeft className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}


function FileChip({ path }: { path: string }) {
  const parts = path.split("/");
  const fileName = parts[parts.length - 1];
  const dir = parts.length > 1 ? parts.slice(0, -1).join("/") + "/" : "";
  return (
    <div className="flex items-center gap-2 rounded-md border border-border/30 bg-muted/15 px-2.5 py-1.5">
      <FileCode2 className="h-3 w-3 shrink-0 text-primary/70" />
      <span className="min-w-0 truncate font-mono text-[11px]">
        {dir && <span className="text-muted-foreground">{dir}</span>}
        <span className="text-foreground/80">{fileName}</span>
      </span>
    </div>
  );
}


const Message = memo(function Message({
  msg,
  onApprove,
  onDeny,
  onApproveAll,
  onClarificationSubmit,
}: {
  msg: ChatMessage;
  onApprove?: (approvalId: string, msgId: string) => void;
  onDeny?: (approvalId: string, msgId: string) => void;
  onApproveAll?: (approvalId: string, msgId: string) => void;
  onClarificationSubmit?: (clarificationId: string, msgId: string, answer: string) => void;
}) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[82%] rounded-2xl rounded-tr-sm bg-primary px-3.5 py-2.5 text-xs text-primary-foreground shadow-sm break-words">
          {msg.content}
        </div>
      </div>
    );
  }

  if (msg.role === "tool") {
    return (
      <ToolCallCard
        tool={(msg.meta?.tool as string) ?? msg.content}
        params={(msg.meta?.params as Record<string, unknown>) ?? {}}
      />
    );
  }

  if (msg.role === "tool_result") {
    return (
      <ToolResultCard
        tool={(msg.meta?.tool as string) ?? ""}
        result={msg.content}
        denied={msg.meta?.denied as boolean | undefined}
      />
    );
  }

  if (msg.role === "approval") {
    return (
      <ToolApprovalCard
        msgId={msg.id}
        approvalId={(msg.meta?.approval_id as string) ?? ""}
        tool={(msg.meta?.tool as string) ?? ""}
        params={(msg.meta?.params as Record<string, unknown>) ?? {}}
        status={msg.meta?.status as string | undefined}
        onApprove={onApprove}
        onDeny={onDeny}
        onApproveAll={onApproveAll}
      />
    );
  }

  if (msg.role === "clarification") {
    return (
      <ClarificationCard
        msgId={msg.id}
        clarificationId={(msg.meta?.clarification_id as string) ?? ""}
        question={(msg.meta?.question as string) ?? ""}
        status={msg.meta?.status as string | undefined}
        answer={msg.meta?.answer as string | undefined}
        onSubmit={onClarificationSubmit}
      />
    );
  }

  if (msg.role === "file") return <FileChip path={msg.content} />;

  if (msg.role === "compacting") {
    return (
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground/50">
        <Loader2 className="h-3 w-3 animate-spin" />
        {msg.content}
      </div>
    );
  }

  if (msg.role === "done") {
    return (
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/40">
        <CheckCircle2 className="h-3 w-3 shrink-0 text-green-400/60" />
        <span>Done · type to continue</span>
      </div>
    );
  }

  if (msg.role === "stopped") {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-border/30 bg-muted/10 px-3.5 py-2.5 text-[11px] text-muted-foreground">
        <Square className="h-3 w-3 shrink-0" />
        {msg.content}
      </div>
    );
  }

  if (msg.role === "error") {
    return (
      <div className="flex items-start gap-2 rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-3">
        <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
        <p className="flex-1 break-words font-mono text-[11px] leading-relaxed text-destructive/90">{msg.content}</p>
      </div>
    );
  }


  return (
    <div className="pl-2.5 border-l-2 border-primary/25">
      <AgentMarkdown content={msg.content} streaming={msg.streaming} />
    </div>
  );
});


function lsKey(projectId: string, k: string) { return `wai-${k}-${projectId}`; }

function lsLoad<T>(projectId: string, k: string): T | null {
  try {
    const v = localStorage.getItem(lsKey(projectId, k));
    return v ? (JSON.parse(v) as T) : null;
  } catch { return null; }
}

function lsSave(projectId: string, k: string, v: unknown) {
  try { localStorage.setItem(lsKey(projectId, k), JSON.stringify(v)); } catch {}
}

function lsClear(projectId: string, k: string) {
  try { localStorage.removeItem(lsKey(projectId, k)); } catch {}
}


export function AgentChat({
  projectId,
  onFileWrite,
  onBuildRunningChange,
  defaultModelProvider,
  defaultModelId,
  disabled,
}: {
  projectId: string;
  onFileWrite?: (path?: string) => void;
  onBuildRunningChange?: (isRunning: boolean) => void;
  defaultModelProvider?: string;
  defaultModelId?: string;
  disabled?: boolean;
}) {
  const { data: session } = useSession();

  const [agentSession, setAgentSession] = useState<AgentSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = lsLoad<ChatMessage[]>(projectId, "msgs");
    return saved ? saved.map((m) => ({ ...m, streaming: false })) : [];
  });
  const [input, setInput] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ModelOption>(() => {
    // Prefer localStorage (user's last choice) over project default
    try {
      const saved = localStorage.getItem(`agent-chat-model-${projectId}`);
      if (saved) {
        const [provider, ...rest] = saved.split("/");
        const model = rest.join("/");
        const preset = CLOUD_PRESETS.find((o) => o.provider === provider && o.model === model);
        if (preset) return preset;
        if (LOCAL_PROVIDER_IDS.includes(provider as typeof LOCAL_PROVIDER_IDS[number])) {
          const lp = LOCAL_PROVIDERS.find((p) => p.provider === provider)!;
          return { provider, model, label: model, badge: lp.badge };
        }
      }
    } catch {}
    // Fall back to project default, then global default
    if (defaultModelProvider && defaultModelId) {
      const preset = CLOUD_PRESETS.find(
        (o) => o.provider === defaultModelProvider && o.model === defaultModelId,
      );
      if (preset) return preset;
      // Local providers (lmstudio, ollama, obsidian-ai) aren't in CLOUD_PRESETS
      if (LOCAL_PROVIDER_IDS.includes(defaultModelProvider as typeof LOCAL_PROVIDER_IDS[number])) {
        const lp = LOCAL_PROVIDERS.find((p) => p.provider === defaultModelProvider)!;
        return { provider: defaultModelProvider, model: defaultModelId, label: defaultModelId, badge: lp.badge };
      }
    }
    return DEFAULT_MODEL;
  });
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const [attachments, setAttachments] = useState<ParsedAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sendRef = useRef<((event: ClientEvent) => void) | null>(null);
  const pendingPromptRef = useRef<string | null>(null);
  const activeStreamIdRef = useRef<string | null>(null);
  const wasDisabledRef = useRef(false);
  const sessionRestoredRef = useRef(false);
  const usedToolsRef = useRef(false);


  const handleModelSelect = useCallback((opt: ModelOption) => {
    setSelectedModel(opt);
    localStorage.setItem(`agent-chat-model-${projectId}`, `${opt.provider}/${opt.model}`);
    setModelPickerOpen(false);
  }, [projectId]);

  const handleLocalModelConfirm = useCallback((provider: string, badge: string, modelName: string) => {
    const name = modelName.trim();
    if (!name) return;
    const opt: ModelOption = { provider, model: name, label: name, badge };
    setSelectedModel(opt);
    localStorage.setItem(`agent-chat-model-${projectId}`, `${provider}/${name}`);
    setModelPickerOpen(false);
  }, [projectId]);


  useEffect(() => {
    if (sessionRestoredRef.current || !session?.accessToken) return;
    sessionRestoredRef.current = true;
    const savedId = lsLoad<string>(projectId, "session");
    if (!savedId) return;
    getAgentSession(savedId, session.accessToken)
      .then((sess) => setAgentSession(sess))
      .catch(() => lsClear(projectId, "session"));
  }, [projectId, session?.accessToken]);


  useEffect(() => {
    if (messages.some((m) => m.streaming)) return;
    if (messages.length === 0) {
      lsClear(projectId, "msgs");
    } else {
      lsSave(projectId, "msgs", messages);
    }
  }, [messages, projectId]);


  useEffect(() => {
    if (agentSession?.session_id) {
      lsSave(projectId, "session", agentSession.session_id);
    }
  }, [agentSession?.session_id, projectId]);


  useEffect(() => {
    onBuildRunningChange?.(isRunning);
  }, [isRunning, onBuildRunningChange]);


  useEffect(() => {
    const end = messagesEndRef.current;
    if (!end) return;
    const parent = end.parentElement;
    if (parent) {
      const nearBottom = parent.scrollHeight - parent.scrollTop - parent.clientHeight < 120;
      if (nearBottom) end.scrollIntoView({ behavior: "instant" as ScrollBehavior });
    } else {
      end.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);


  useEffect(() => {
    if (wasDisabledRef.current && !isStarting && !isRunning) {
      textareaRef.current?.focus();
    }
    wasDisabledRef.current = isStarting || isRunning;
  }, [isStarting, isRunning]);


  const addMessage = useCallback((msg: Omit<ChatMessage, "id">) => {
    setMessages((prev) => [...prev, { ...msg, id: crypto.randomUUID() }]);
  }, []);

  const appendToken = useCallback((content: string) => {
    if (!activeStreamIdRef.current) {
      activeStreamIdRef.current = crypto.randomUUID();
    }
    const targetId = activeStreamIdRef.current;
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.id === targetId) {
        return [...prev.slice(0, -1), { ...last, content: last.content + content, streaming: true }];
      }
      return [...prev, { id: targetId, role: "agent", content, streaming: true }];
    });
  }, []);

  const flushStream = useCallback(() => {
    const id = activeStreamIdRef.current;
    if (!id) return;
    activeStreamIdRef.current = null;
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, streaming: false } : m)),
    );
  }, []);


  const handleApprove = useCallback((approvalId: string, msgId: string) => {
    sendRef.current?.({ type: "tool_approval_response", approval_id: approvalId, approved: true });
    setMessages((prev) =>
      prev.map((m) => m.id === msgId ? { ...m, meta: { ...m.meta, status: "approved" } } : m),
    );
  }, []);

  const handleDeny = useCallback((approvalId: string, msgId: string) => {
    sendRef.current?.({ type: "tool_approval_response", approval_id: approvalId, approved: false });
    setMessages((prev) =>
      prev.map((m) => m.id === msgId ? { ...m, meta: { ...m.meta, status: "denied" } } : m),
    );
  }, []);

  const handleApproveAll = useCallback((approvalId: string, msgId: string) => {
    sendRef.current?.({ type: "set_permission_mode", mode: "auto" });
    sendRef.current?.({ type: "tool_approval_response", approval_id: approvalId, approved: true });
    setMessages((prev) =>
      prev.map((m) => m.id === msgId ? { ...m, meta: { ...m.meta, status: "approved" } } : m),
    );
  }, []);

  const handleClarificationSubmit = useCallback((clarificationId: string, msgId: string, answer: string) => {
    sendRef.current?.({ type: "clarification_response", clarification_id: clarificationId, answer });
    setMessages((prev) =>
      prev.map((m) => m.id === msgId ? { ...m, meta: { ...m.meta, status: "answered", answer } } : m),
    );
  }, []);


  const wsHandlers = {
    onOpen: () => {
      if (pendingPromptRef.current) {
        sendRef.current?.({
          type: "chat",
          content: pendingPromptRef.current,
          model_provider: selectedModel.provider,
          model_id: selectedModel.model,
        });
        pendingPromptRef.current = null;
        setIsStarting(false);
        setIsRunning(true);
      }
    },

    onConnected: (e: { type: "connected"; status: string }) => {
      if (e.status === "running") setIsRunning(true);

      onFileWrite?.();
    },

    onToken: (e: { type: "token"; content: string }) => {
      appendToken(e.content);
    },

    onToolCall: (e: { type: "tool_call"; tool: string; params: Record<string, unknown> }) => {
      flushStream();
      usedToolsRef.current = true;
      addMessage({ role: "tool", content: "", meta: { tool: e.tool, params: e.params } });
    },

    onToolResult: (e: { type: "tool_result"; tool: string; result: string; denied?: boolean }) => {
      addMessage({ role: "tool_result", content: e.result, meta: { tool: e.tool, denied: e.denied } });
    },

    onToolApprovalRequest: (e: { type: "tool_approval_request"; approval_id: string; tool: string; params: Record<string, unknown> }) => {
      flushStream();
      addMessage({
        role: "approval",
        content: "",
        meta: { approval_id: e.approval_id, tool: e.tool, params: e.params },
      });
    },

    onClarificationRequest: (e: { type: "clarification_request"; clarification_id: string; question: string }) => {
      flushStream();
      addMessage({
        role: "clarification",
        content: "",
        meta: { clarification_id: e.clarification_id, question: e.question },
      });
    },

    onCompacting: () => {
      addMessage({ role: "compacting", content: "Compacting conversation context…" });
    },

    onDone: (_e: { type: "done"; content: string }) => {
      flushStream();
      setIsRunning(false);


      if (usedToolsRef.current) {
        addMessage({ role: "done", content: "" });
      }
      usedToolsRef.current = false;
    },

    onStopped: () => {
      flushStream();
      setIsRunning(false);
      addMessage({ role: "stopped", content: "Agent stopped." });
    },

    onFileChanged: (e: { type: "file_changed"; path: string }) => {
      addMessage({ role: "file", content: e.path });
      onFileWrite?.(e.path);
    },

    onError: (e: { type: "error"; message: string }) => {
      flushStream();
      setIsRunning(false);
      addMessage({ role: "error", content: e.message ?? "An error occurred." });
    },

    onHistory: (e: { type: "history"; messages: Array<{ role: string; content: string; meta?: Record<string, unknown> }> }) => {

      setMessages(e.messages.map((m) => ({ ...m, id: crypto.randomUUID() } as ChatMessage)));
    },

    onClose: (code: number) => {

      if (code === 4004 || code === 4001) {
        setAgentSession(null);
        lsClear(projectId, "session");
      }
    },
  };

  const { send } = useAgentWs(
    agentSession?.session_id ?? null,
    session?.accessToken ?? null,
    wsHandlers,
  );
  sendRef.current = send;


  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !session?.accessToken) return;
    e.target.value = "";
    setIsUploading(true);
    try {
      const parsed = await parseAttachment(projectId, file, session.accessToken);
      setAttachments((prev) => [...prev, parsed]);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to parse file");
    } finally {
      setIsUploading(false);
    }
  };

  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = Array.from(e.clipboardData.items);
    const imageItem = items.find((item) => item.type.startsWith("image/"));
    if (!imageItem || !session?.accessToken) return;
    e.preventDefault();
    const blob = imageItem.getAsFile();
    if (!blob) return;
    const ext = imageItem.type.split("/")[1] ?? "png";
    const file = new File([blob], `paste-${Date.now()}.${ext}`, { type: imageItem.type });
    setIsUploading(true);
    try {
      const parsed = await parseAttachment(projectId, file, session.accessToken);
      setAttachments((prev) => [...prev, parsed]);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to paste image");
    } finally {
      setIsUploading(false);
    }
  }, [session?.accessToken, projectId]);


  const handleSend = async () => {
    if (!session?.accessToken || !input.trim()) return;
    const userText = input.trim();
    setInput("");


    const contextBlocks = attachments.map((a) => {
      if (a.type === "image") {
        return `[Attached image: ${a.filename}]\n<image data omitted from text — sent as vision input>`;
      }
      return `[Attached: ${a.filename}]\n${a.content}\n---`;
    });
    const prompt = contextBlocks.length > 0
      ? `${contextBlocks.join("\n\n")}\n\n${userText}`
      : userText;

    addMessage({ role: "user", content: userText });
    attachments.forEach((a) => addMessage({ role: "file", content: a.filename }));
    setAttachments([]);
    usedToolsRef.current = false;

    try {
      if (!agentSession) {

        setIsStarting(true);
        const sess = await createAgentSession(
          { project_id: projectId, model_provider: selectedModel.provider, model_id: selectedModel.model },
          session.accessToken,
        );
        pendingPromptRef.current = prompt;
        setAgentSession(sess);
      } else {

        send({
          type: "chat",
          content: prompt,
          model_provider: selectedModel.provider,
          model_id: selectedModel.model,
        });
        setIsRunning(true);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start agent");
      setIsStarting(false);
    }
  };

  const handleStop = () => {
    sendRef.current?.({ type: "stop" });

  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isInputDisabled = isStarting || isRunning || !!disabled;


  return (
    <div className="flex h-full flex-col">

      <div className="flex h-10 shrink-0 items-center justify-between border-b px-3">
        <div className="flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5 text-primary/70" />
          <span className="text-xs font-medium">Agent</span>
          {isRunning && (
            <div className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-pulse" />
              <span className="text-[10px] text-muted-foreground">Running</span>
            </div>
          )}
          {isStarting && !isRunning && (
            <div className="flex items-center gap-1.5">
              <Loader2 className="h-2.5 w-2.5 animate-spin text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">Connecting…</span>
            </div>
          )}
        </div>
      </div>


      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-4">
        <div className="max-w-3xl mx-auto space-y-3 py-4">
          {messages.length === 0 && disabled && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="flex gap-1 mb-3">
                {[0, 150, 300].map((d) => (
                  <span
                    key={d}
                    className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-bounce"
                    style={{ animationDelay: `${d}ms` }}
                  />
                ))}
              </div>
              <p className="text-sm font-medium">Preparing workspace…</p>
              <p className="mt-2 max-w-52 text-[11px] leading-relaxed text-muted-foreground">
                Installing framework template. This usually takes 30–90 seconds.
              </p>
            </div>
          )}
          {messages.length === 0 && !disabled && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-sm font-medium">What do you want to build?</p>
              <p className="mt-2 max-w-45 text-[11px] leading-relaxed text-muted-foreground">
                Describe your task and the agent will write code, run commands, and build your project.
              </p>
            </div>
          )}
          {messages.map((msg) => (
            <Message
              key={msg.id}
              msg={msg}
              onApprove={handleApprove}
              onDeny={handleDeny}
              onApproveAll={handleApproveAll}
              onClarificationSubmit={handleClarificationSubmit}
            />
          ))}
          {isStarting && messages.length > 0 && (
            <div className="pl-2.5 border-l-2 border-primary/25 flex items-center gap-1">
              {[0, 150, 300].map((delay) => (
                <span
                  key={delay}
                  className="h-1 w-1 animate-bounce rounded-full bg-muted-foreground/40"
                  style={{ animationDelay: `${delay}ms` }}
                />
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>


      <div className="shrink-0 border-t px-4 py-3">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.md,.json"
          className="hidden"
          onChange={handleFileSelect}
        />

        <div className={cn(
          "max-w-3xl mx-auto rounded-xl border transition-all",
          isInputDisabled
            ? "border-border/30 bg-muted/10 opacity-60"
            : "border-border/50 bg-muted/15 focus-within:border-primary/40 focus-within:bg-background focus-within:ring-2 focus-within:ring-primary/10",
        )}>
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-1.5 px-3 pt-3 pb-1">
              {attachments.map((a, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 rounded-md border border-border/30 bg-muted/30 px-2 py-1 text-[11px]"
                >
                  <Paperclip className="h-2.5 w-2.5 shrink-0 text-muted-foreground" />
                  <span className="max-w-40 truncate text-foreground/70">{a.filename}</span>
                  <button
                    type="button"
                    onClick={() => setAttachments((prev) => prev.filter((_, j) => j !== i))}
                    className="ml-0.5 text-muted-foreground/50 hover:text-foreground"
                  >
                    <XCircle className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <Textarea
            ref={textareaRef}
            placeholder={
              disabled
                ? "Preparing workspace…"
                : isRunning
                ? "Agent is running…"
                : "Describe what to build or change…"
            }
            className="min-h-[72px] max-h-[180px] resize-none border-0 bg-transparent shadow-none text-sm focus-visible:ring-0 focus-visible:ring-offset-0 px-3 py-3"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            disabled={isInputDisabled}
          />


          <div className="flex items-center justify-between px-3 pb-3">
            <div className="flex items-center gap-1">

              <div className="relative">
                <button
                  type="button"
                  onClick={() => setModelPickerOpen((o) => !o)}
                  disabled={isRunning}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-muted-foreground/60 transition-colors hover:bg-muted/60 hover:text-muted-foreground disabled:opacity-40"
                >
                  <span>{selectedModel.label}</span>
                  <ChevronDown className="h-2.5 w-2.5" />
                </button>
                {modelPickerOpen && (
                  <div className="absolute bottom-full left-0 mb-1 z-50 w-56 rounded-lg border border-border/40 bg-popover shadow-lg flex flex-col" style={{maxHeight: "min(420px, calc(100vh - 120px))"}}>
                    <div className="overflow-y-auto overflow-x-hidden flex-1 min-h-0">
                    {/* Cloud presets */}
                    <div className="px-2 pt-2 pb-1">
                      <p className="px-1 pb-1 text-[9px] font-medium uppercase tracking-wider text-muted-foreground/40">Cloud</p>
                      {CLOUD_PRESETS.map((opt) => (
                        <button
                          key={`${opt.provider}/${opt.model}`}
                          type="button"
                          onClick={() => handleModelSelect(opt)}
                          className={cn(
                            "flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-[11px] transition-colors hover:bg-muted/50",
                            selectedModel.provider === opt.provider && selectedModel.model === opt.model && "text-primary",
                          )}
                        >
                          <span>{opt.label}</span>
                          <span className="text-[9px] text-muted-foreground/40">{opt.badge}</span>
                        </button>
                      ))}
                    </div>
                    {/* Local / self-hosted — free text input per provider */}
                    <div className="border-t border-border/30 px-2 pt-2 pb-2">
                      <p className="px-1 pb-1 text-[9px] font-medium uppercase tracking-wider text-muted-foreground/40">Local / self-hosted</p>
                      {LOCAL_PROVIDERS.map(({ provider, badge }) => (
                        <div key={provider} className="mb-1.5 last:mb-0">
                          <p className="px-1 pb-0.5 text-[9px] text-muted-foreground/50">{badge}</p>
                          <div className="flex gap-1">
                            <input
                              type="text"
                              placeholder={provider === "obsidian-ai" ? "model name" : "e.g. llama3.2"}
                              defaultValue={selectedModel.provider === provider ? selectedModel.model : ""}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleLocalModelConfirm(provider, badge, (e.target as HTMLInputElement).value);
                              }}
                              className="flex-1 rounded-md border border-border/30 bg-background/60 px-2 py-1 text-[11px] text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:ring-1 focus:ring-primary/40"
                            />
                            <button
                              type="button"
                              onClick={(e) => {
                                const inp = (e.currentTarget.previousSibling as HTMLInputElement).value;
                                handleLocalModelConfirm(provider, badge, inp);
                              }}
                              className="rounded-md border border-border/30 bg-muted/30 px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
                            >
                              Use
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                    </div>
                  </div>
                )}
              </div>


              <button
                type="button"
                disabled={isInputDisabled || isUploading}
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground/50 transition-colors hover:bg-muted/60 hover:text-muted-foreground disabled:opacity-30"
                title="Attach PDF or image"
              >
                {isUploading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Paperclip className="h-3.5 w-3.5" />
                )}
              </button>
            </div>


            {isRunning ? (
              <button
                type="button"
                onClick={handleStop}
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive/10 text-destructive transition-colors hover:bg-destructive/20"
                title="Stop agent"
              >
                <Square className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!input.trim() || isStarting}
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
                title="Send (Enter)"
              >
                {isStarting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CornerDownLeft className="h-3.5 w-3.5" />
                )}
              </button>
            )}
          </div>
        </div>

        <p className="mt-1.5 max-w-3xl mx-auto text-center text-[10px] text-muted-foreground/35">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
