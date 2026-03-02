"use client";

import { useEffect, useRef, useCallback } from "react";
import { useSession } from "next-auth/react";
import { wsUrl } from "@/lib/api/client";

interface TerminalPanelProps {
  projectId: string;
  visible?: boolean;
}

const FATAL_CODES = new Set([4001, 4004, 4009]);

export function TerminalPanel({ projectId, visible = true }: TerminalPanelProps) {
  const { data: session } = useSession();
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<import("@xterm/xterm").Terminal | null>(null);
  const fitRef = useRef<import("@xterm/addon-fit").FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const atBottomRef = useRef(true);
  const fitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fit = useCallback(() => {
    try {
      fitRef.current?.fit();
      if (wsRef.current?.readyState === WebSocket.OPEN && termRef.current) {
        wsRef.current.send(
          JSON.stringify({ type: "resize", cols: termRef.current.cols, rows: termRef.current.rows }),
        );
      }
    } catch {}
  }, []);

  const fitDebounced = useCallback(() => {
    if (fitTimerRef.current) clearTimeout(fitTimerRef.current);
    fitTimerRef.current = setTimeout(fit, 60);
  }, [fit]);

  useEffect(() => {
    if (!session?.accessToken) return;

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connectWs = (xterm: import("@xterm/xterm").Terminal) => {
      if (cancelled) return;

      const url = wsUrl(
        `/ws/terminal/${projectId}?token=${encodeURIComponent(session!.accessToken!)}`,
      );
      const ws = new WebSocket(url);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        xterm.writeln("\x1b[32mConnected.\x1b[0m");
        ws.send(JSON.stringify({ type: "resize", cols: xterm.cols, rows: xterm.rows }));
      };

      ws.onmessage = (ev: MessageEvent) => {
        const write = () => {
          if (ev.data instanceof ArrayBuffer) xterm.write(new Uint8Array(ev.data));
          else if (typeof ev.data === "string") xterm.write(ev.data);
        };

        if (atBottomRef.current) {
          write();
        } else {
          const prevViewportY = xterm.buffer.active.viewportY;
          const prevLength = xterm.buffer.active.length;
          write();
          const addedLines = xterm.buffer.active.length - prevLength;
          xterm.scrollToLine(prevViewportY + addedLines);
        }
      };

      ws.onclose = (ev: CloseEvent) => {
        wsRef.current = null;
        const fatal = FATAL_CODES.has(ev.code);
        const reason =
          ev.code === 4009
            ? "No active container — start the project first."
            : ev.code === 4001
            ? "Unauthorized."
            : `Connection closed (${ev.code}).`;
        xterm.writeln(`\r\n\x1b[33m${reason}\x1b[0m`);

        if (!fatal && !cancelled) {
          xterm.writeln("\x1b[90mReconnecting in 3s…\x1b[0m");
          reconnectTimer = setTimeout(() => connectWs(xterm), 3000);
        }
      };

      ws.onerror = () => {
        xterm.writeln("\r\n\x1b[31mWebSocket error.\x1b[0m");
      };
    };

    const timer = window.setTimeout(async () => {
      if (cancelled || !containerRef.current) return;

      const { Terminal: XTerm } = await import("@xterm/xterm");
      const { FitAddon } = await import("@xterm/addon-fit");
      const { WebLinksAddon } = await import("@xterm/addon-web-links");

      if (cancelled || !containerRef.current) return;

      const xterm = new XTerm({
        theme: {
          background: "#0a0a0a",
          foreground: "#4ade80",
          cursor: "#a78bfa",
          selectionBackground: "#4c1d9530",
          black: "#1a1a2e",
          red: "#f87171",
          green: "#4ade80",
          yellow: "#fbbf24",
          blue: "#818cf8",
          magenta: "#c084fc",
          cyan: "#22d3ee",
          white: "#e2e8f0",
        },
        fontFamily: '"Geist Mono", "JetBrains Mono", monospace',
        fontSize: 12,
        lineHeight: 1.4,
        cursorStyle: "bar",
        cursorBlink: true,
        scrollback: 5000,
      });

      const fitAddon = new FitAddon();
      xterm.loadAddon(fitAddon);
      xterm.loadAddon(new WebLinksAddon());
      xterm.open(containerRef.current);

      termRef.current = xterm;
      fitRef.current = fitAddon;

      if (cancelled) {
        xterm.dispose();
        return;
      }

      atBottomRef.current = true;
      xterm.onScroll(() => {
        const buf = xterm.buffer.active;
        atBottomRef.current = buf.viewportY + xterm.rows >= buf.length - 1;
      });

      xterm.onData((data) => {
        atBottomRef.current = true;
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(new TextEncoder().encode(data));
        }
      });


      const fitAndConnect = () => {
        if (cancelled) return;
        const el = containerRef.current;
        if (!el || el.offsetWidth === 0 || el.offsetHeight === 0) {
          requestAnimationFrame(fitAndConnect);
          return;
        }
        fitAddon.fit();
        xterm.scrollToBottom();
        connectWs(xterm);

        setTimeout(() => {
          if (cancelled) return;
          fitAddon.fit();
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(
              JSON.stringify({ type: "resize", cols: xterm.cols, rows: xterm.rows }),
            );
          }
        }, 200);
      };

      requestAnimationFrame(fitAndConnect);
    }, 0);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (fitTimerRef.current) clearTimeout(fitTimerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
      termRef.current?.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, [session?.accessToken, projectId]);

  useEffect(() => {
    if (visible) {
      requestAnimationFrame(() => {
        fit();
        termRef.current?.scrollToBottom();
      });
    }
  }, [visible, fit]);

  useEffect(() => {
    const obs = new ResizeObserver(fitDebounced);
    if (containerRef.current) obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, [fitDebounced]);

  return (
    <div style={{ position: "relative", height: "100%", background: "#0a0a0a" }}>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
    </div>
  );
}
