

import { wsUrl } from "./client";
import type {
  ClientEvent,
  ServerEvent,
  ConnectedEvent,
  TokenEvent,
  ToolCallEvent,
  ToolResultEvent,
  ToolApprovalRequestEvent,
  ClarificationRequestEvent,
  CompactingEvent,
  DoneEvent,
  StoppedEvent,
  FileChangedEvent,
  FilesRefreshedEvent,
  ErrorEvent,
  HistoryEvent,
} from "@/types/api";

export interface AgentWsHandlers {
  onConnected?: (e: ConnectedEvent) => void;
  onToken?: (e: TokenEvent) => void;
  onToolCall?: (e: ToolCallEvent) => void;
  onToolResult?: (e: ToolResultEvent) => void;
  onToolApprovalRequest?: (e: ToolApprovalRequestEvent) => void;
  onClarificationRequest?: (e: ClarificationRequestEvent) => void;
  onCompacting?: (e: CompactingEvent) => void;
  onDone?: (e: DoneEvent) => void;
  onStopped?: (e: StoppedEvent) => void;
  onFileChanged?: (e: FileChangedEvent) => void;
  onFilesRefreshed?: (e: FilesRefreshedEvent) => void;
  onError?: (e: ErrorEvent) => void;
  onHistory?: (e: HistoryEvent) => void;
  onOpen?: () => void;
  onClose?: (code: number, reason: string) => void;
  onRawError?: (err: Event) => void;
}

type ReconnectState = { attempt: number; timer: ReturnType<typeof setTimeout> | null };

const RECONNECT_DELAYS = [1000, 2000, 5000, 10000];

export class AgentWsClient {
  private ws: WebSocket | null = null;
  private dead = false;
  private reconnect: ReconnectState = { attempt: 0, timer: null };

  constructor(
    private readonly sessionId: string,
    private readonly token: string,
    private readonly handlers: AgentWsHandlers,
    private readonly autoReconnect = true,
  ) {}

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    if (this.dead) return;
    const url = wsUrl(`/ws/agent/${this.sessionId}?token=${encodeURIComponent(this.token)}`);
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => {
      this.reconnect.attempt = 0;
      this.handlers.onOpen?.();
    };

    ws.onmessage = (ev: MessageEvent) => {
      let event: ServerEvent;
      try {
        event = JSON.parse(ev.data as string) as ServerEvent;
      } catch {
        console.error("[AgentWsClient] Failed to parse message", ev.data);
        return;
      }
      this.dispatch(event);
    };

    ws.onerror = (err: Event) => {
      this.handlers.onRawError?.(err);
    };

    ws.onclose = (ev: CloseEvent) => {
      this.handlers.onClose?.(ev.code, ev.reason);
      if (this.autoReconnect && !this.dead) {
        this.scheduleReconnect();
      }
    };
  }

  send(event: ClientEvent): void {
    if (!this.isConnected) {
      console.warn("[AgentWsClient] Not connected — cannot send", event.type);
      return;
    }
    this.ws!.send(JSON.stringify(event));
  }

  disconnect(): void {
    this.dead = true;
    if (this.reconnect.timer) clearTimeout(this.reconnect.timer);
    this.ws?.close(1000, "client disconnect");
    this.ws = null;
  }

  private scheduleReconnect(): void {
    const delay =
      RECONNECT_DELAYS[Math.min(this.reconnect.attempt, RECONNECT_DELAYS.length - 1)];
    this.reconnect.attempt++;
    this.reconnect.timer = setTimeout(() => {
      if (!this.dead) this.connect();
    }, delay);
  }

  private dispatch(event: ServerEvent): void {
    switch (event.type) {
      case "connected":
        this.handlers.onConnected?.(event);
        break;
      case "token":
        this.handlers.onToken?.(event);
        break;
      case "tool_call":
        this.handlers.onToolCall?.(event);
        break;
      case "tool_result":
        this.handlers.onToolResult?.(event);
        break;
      case "tool_approval_request":
        this.handlers.onToolApprovalRequest?.(event);
        break;
      case "clarification_request":
        this.handlers.onClarificationRequest?.(event);
        break;
      case "compacting":
        this.handlers.onCompacting?.(event);
        break;
      case "done":
        this.handlers.onDone?.(event);
        break;
      case "stopped":
        this.handlers.onStopped?.(event);
        break;
      case "file_changed":
        this.handlers.onFileChanged?.(event);
        break;
      case "files_refreshed":
        this.handlers.onFilesRefreshed?.(event);
        break;
      case "error":
        this.handlers.onError?.(event);
        break;
      case "history":
        this.handlers.onHistory?.(event);
        break;
      default:
        console.warn("[AgentWsClient] Unknown event type", event);
    }
  }
}


import { useEffect, useRef, useCallback } from "react";

export function useAgentWs(
  sessionId: string | null,
  token: string | null,
  handlers: AgentWsHandlers,
) {
  const clientRef = useRef<AgentWsClient | null>(null);

  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const stableHandlers: AgentWsHandlers = {
    onConnected:          (e) => handlersRef.current.onConnected?.(e),
    onToken:              (e) => handlersRef.current.onToken?.(e),
    onToolCall:           (e) => handlersRef.current.onToolCall?.(e),
    onToolResult:         (e) => handlersRef.current.onToolResult?.(e),
    onToolApprovalRequest:(e) => handlersRef.current.onToolApprovalRequest?.(e),
    onClarificationRequest:(e) => handlersRef.current.onClarificationRequest?.(e),
    onCompacting:         (e) => handlersRef.current.onCompacting?.(e),
    onDone:               (e) => handlersRef.current.onDone?.(e),
    onStopped:            (e) => handlersRef.current.onStopped?.(e),
    onFileChanged:        (e) => handlersRef.current.onFileChanged?.(e),
    onFilesRefreshed:     (e) => handlersRef.current.onFilesRefreshed?.(e),
    onError:              (e) => handlersRef.current.onError?.(e),
    onHistory:            (e) => handlersRef.current.onHistory?.(e),
    onOpen:               ()  => handlersRef.current.onOpen?.(),
    onClose:              (c, r) => handlersRef.current.onClose?.(c, r),
    onRawError:           (e) => handlersRef.current.onRawError?.(e),
  };

  useEffect(() => {
    if (!sessionId || !token) return;

    const client = new AgentWsClient(sessionId, token, stableHandlers, true);
    clientRef.current = client;
    client.connect();

    return () => {
      client.disconnect();
      clientRef.current = null;
    };

  }, [sessionId, token]);

  const send = useCallback((event: ClientEvent) => {
    clientRef.current?.send(event);
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
  }, []);

  return { send, disconnect, client: clientRef };
}
