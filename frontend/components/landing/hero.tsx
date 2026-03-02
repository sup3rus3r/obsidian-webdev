"use client";

import { motion, AnimatePresence } from "motion/react";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  Sparkles,
  Bot,
  MessageSquare,
  Terminal,
  FileCode2,
  CheckCircle,
  Loader2,
  Zap,
  GitBranch,
  Shield,
  Layers,
  Globe,
  Folder,
  Container,
  Wrench,
  ScanSearch,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";


function Background() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage: `radial-gradient(circle, oklch(0.97 0 0) 1px, transparent 1px)`,
          backgroundSize: "32px 32px",
        }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_-10%,rgba(139,92,246,0.28),transparent)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_40%_60%_at_0%_30%,rgba(109,40,217,0.12),transparent)]" />
      <motion.div
        className="absolute right-1/4 top-1/4 h-[500px] w-[500px] -translate-x-1/2 rounded-full"
        style={{ background: "rgba(139,92,246,0.10)", filter: "blur(90px)" }}
        animate={{ opacity: [0.6, 1, 0.6], scale: [1, 1.05, 1] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}


function DescribeDemo() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timers = [
      setTimeout(() => setStep(1), 700),
      setTimeout(() => setStep(2), 1600),
      setTimeout(() => setStep(3), 2800),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="flex h-full flex-col gap-2.5 p-3">
      <motion.div
        className="flex justify-end"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="max-w-[78%] rounded-2xl rounded-tr-sm bg-violet-600 px-3.5 py-2 text-[11px] leading-relaxed text-white">
          Build a full-stack task manager with a React frontend and FastAPI
          backend, with user auth and a dashboard.
        </div>
      </motion.div>

      {step >= 1 && (
        <motion.div
          className="flex items-start gap-2"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-violet-500/20">
            <Bot className="h-3 w-3 text-violet-400" />
          </div>
          {step === 1 ? (
            <div className="flex items-center gap-1 pt-1.5">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          ) : (
            <div className="max-w-[82%] text-[11px] leading-relaxed text-foreground/90">
              Got it. I&apos;ll scaffold a React + Vite frontend with a FastAPI backend,
              JWT auth, and a task dashboard. Starting now.
            </div>
          )}
        </motion.div>
      )}

      {step >= 3 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-border bg-muted/60 p-2.5 space-y-1.5"
        >
          {[
            { tool: "bash", param: "npm create vite@latest frontend", done: true },
            { tool: "write_file", param: "backend/main.py", done: true },
            { tool: "bash", param: "uv sync", done: false },
          ].map(({ tool, param, done }) => (
            <div key={param} className="flex items-center gap-2 text-[10px]">
              {done ? (
                <CheckCircle className="h-3 w-3 shrink-0 text-emerald-400" />
              ) : (
                <Loader2 className="h-3 w-3 shrink-0 animate-spin text-violet-400" />
              )}
              <span className="font-mono text-violet-300">{tool}</span>
              <span className="truncate text-muted-foreground/80">{param}</span>
            </div>
          ))}
        </motion.div>
      )}

      <div className="mt-auto border-t border-border pt-2">
        <div className="flex items-center gap-2 rounded-lg border border-border bg-muted px-3 py-1.5">
          <span className="flex-1 text-[11px] italic text-muted-foreground/50">
            Describe your project…
          </span>
          <div className="flex h-5 w-5 items-center justify-center rounded-md bg-violet-600/80">
            <ArrowRight className="h-2.5 w-2.5 text-white" />
          </div>
        </div>
      </div>
    </div>
  );
}


function ReActDemo() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timers = [400, 1100, 1900, 2700].map((delay, i) =>
      setTimeout(() => setStep(i + 1), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  const steps = [
    {
      tool: "bash",
      param: "npm create vite@latest frontend -- --template react-ts",
      result: "Scaffolding project… done.",
      accent: "text-violet-400",
    },
    {
      tool: "write_file",
      param: "backend/main.py",
      result: "FastAPI app written.",
      accent: "text-blue-400",
    },
    {
      tool: "bash",
      param: "uv add fastapi uvicorn python-jose",
      result: "Packages installed.",
      accent: "text-emerald-400",
    },
    {
      tool: "bash",
      param: "npm run dev",
      result: "Dev server ready on :5173",
      accent: "text-amber-400",
    },
  ];

  return (
    <div className="flex h-full flex-col gap-2 overflow-auto p-3">
      {steps.slice(0, step).map((s, i) => (
        <motion.div
          key={s.param}
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          className="rounded-lg border border-border bg-muted p-3"
        >
          <div className="mb-1 flex items-center gap-2">
            <Wrench className={`h-3 w-3 shrink-0 ${s.accent}`} />
            <span className={`font-mono text-[10px] font-semibold ${s.accent}`}>
              {s.tool}
            </span>
            <span className="truncate text-[10px] text-muted-foreground/80">
              {s.param}
            </span>
            <div className="ml-auto">
              {i === step - 1 ? (
                <Loader2 className="h-3 w-3 animate-spin text-muted-foreground/85" />
              ) : (
                <CheckCircle className="h-3 w-3 text-emerald-400" />
              )}
            </div>
          </div>
          {i < step - 1 && (
            <p className="text-[10px] text-muted-foreground/70">{s.result}</p>
          )}
        </motion.div>
      ))}
    </div>
  );
}


function EditorDemo() {
  const tree = [
    { label: "src/", icon: Folder, indent: 0 },
    { label: "components/", icon: Folder, indent: 1 },
    { label: "TaskList.tsx", icon: FileCode2, indent: 2, active: true },
    { label: "TaskCard.tsx", icon: FileCode2, indent: 2 },
    { label: "App.tsx", icon: FileCode2, indent: 1 },
    { label: "main.py", icon: FileCode2, indent: 0 },
    { label: "models.py", icon: FileCode2, indent: 0 },
  ];

  const codeLines = [
    { t: 'import { useState, useEffect } from "react"', c: "text-violet-300" },
    { t: 'import { TaskCard } from "./TaskCard"', c: "text-violet-300" },
    { t: "", c: "" },
    { t: "export function TaskList() {", c: "text-foreground/90" },
    { t: "  const [tasks, setTasks] = useState([])", c: "text-blue-300" },
    { t: "", c: "" },
    { t: "  useEffect(() => {", c: "text-foreground/80" },
    { t: '    fetch("/api/tasks")', c: "text-emerald-300" },
    { t: "      .then(r => r.json())", c: "text-emerald-300" },
    { t: "      .then(setTasks)", c: "text-emerald-300" },
    { t: "  }, [])", c: "text-foreground/80" },
    { t: "", c: "" },
    { t: "  return (", c: "text-foreground/90" },
    { t: '    <ul className="space-y-2">', c: "text-amber-300" },
    { t: "      {tasks.map(t => <TaskCard key={t.id} task={t} />)}", c: "text-amber-300" },
    { t: "    </ul>", c: "text-amber-300" },
    { t: "  )", c: "text-foreground/90" },
    { t: "}", c: "text-foreground/90" },
  ];

  return (
    <div className="flex h-full overflow-hidden">
      <div className="hidden w-36 shrink-0 flex-col border-r border-border bg-muted/40 p-2 sm:flex">
        <p className="mb-1 px-2 py-1 text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/80">
          Explorer
        </p>
        {tree.map((f, i) => {
          const Icon = f.icon;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.05 }}
              className={`flex cursor-default items-center gap-1.5 rounded px-2 py-1 text-[10px] ${
                f.active
                  ? "bg-violet-500/15 text-violet-300"
                  : "text-muted-foreground/85 hover:text-muted-foreground/85"
              }`}
              style={{ paddingLeft: `${(f.indent ?? 0) * 8 + 8}px` }}
            >
              <Icon className="h-3 w-3 shrink-0" />
              {f.label}
            </motion.div>
          );
        })}
      </div>

      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="border-b border-border bg-muted/40 px-3 py-1.5 text-[10px] text-violet-300">
          TaskList.tsx
        </div>
        <div className="flex-1 overflow-auto p-3 font-mono">
          {codeLines.map((line, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.055 }}
              className={`text-[10px] leading-[1.6] ${line.c || "text-muted-foreground/40"}`}
            >
              {line.t || "\u00a0"}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}


function TerminalDemo() {
  const lines = [
    { t: "$ docker exec -it webdev-ai-f3a2 bash", c: "text-violet-400" },
    { t: "root@f3a2:/workspace#", c: "text-white/90" },
    { t: "$ npm install", c: "text-white/90" },
    { t: "added 312 packages in 4.1s", c: "text-muted-foreground/85" },
    { t: "", c: "" },
    { t: "$ npm run dev", c: "text-white/90" },
    { t: "", c: "" },
    { t: "  VITE v5.4.2  ready in 218 ms", c: "text-emerald-400" },
    { t: "", c: "" },
    { t: "  ➜  Local:   http://localhost:5173/", c: "text-blue-400" },
    { t: "  ➜  Network: http://172.17.0.2:5173/", c: "text-muted-foreground/80" },
    { t: "  ➜  HMR ready.", c: "text-emerald-400" },
    { t: "", c: "" },
    { t: "  page reload  src/App.tsx", c: "text-muted-foreground/80" },
  ];

  const [shown, setShown] = useState(0);
  useEffect(() => {
    const t = setInterval(
      () => setShown((s) => (s < lines.length ? s + 1 : s)),
      280
    );
    return () => clearInterval(t);
  }, [lines.length]);

  return (
    <div className="flex h-full flex-col overflow-auto bg-black/60 p-3 font-mono">
      {lines.slice(0, shown).map((line, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`text-[10px] leading-[1.65] ${line.c || "text-muted-foreground/40"}`}
        >
          {line.t || "\u00a0"}
        </motion.div>
      ))}
      {shown < lines.length && (
        <span className="animate-pulse text-[10px] text-white/60">|</span>
      )}
    </div>
  );
}


const DEMOS = [
  {
    id: "describe",
    label: "Describe",
    icon: MessageSquare,
    Demo: DescribeDemo,
    desc: "Chat with the agent — it plans and immediately starts building",
  },
  {
    id: "agent",
    label: "Agent",
    icon: Bot,
    Demo: ReActDemo,
    desc: "ReAct loop: think → call tool → observe result → repeat until done",
  },
  {
    id: "editor",
    label: "Editor",
    icon: FileCode2,
    Demo: EditorDemo,
    desc: "Browse and edit the generated code in a multi-tab IDE with live file tree",
  },
  {
    id: "terminal",
    label: "Terminal",
    icon: Terminal,
    Demo: TerminalDemo,
    desc: "Live terminal inside an isolated Docker container — dev server auto-starts",
  },
];

const CHIPS = [
  { icon: Bot, label: "ReAct agent loop" },
  { icon: Wrench, label: "Tool use" },
  { icon: MessageSquare, label: "HITL approval" },
  { icon: Container, label: "Docker isolation" },
  { icon: Globe, label: "Live preview" },
  { icon: Terminal, label: "Integrated terminal" },
  { icon: Layers, label: "Framework-aware" },
  { icon: FileCode2, label: "Multi-tab editor" },
  { icon: Shield, label: "Secrets vault" },
  { icon: Sparkles, label: "Web search" },
  { icon: Zap, label: "Auto dev-server" },
  { icon: ArrowRight, label: "ZIP export" },
];


export function Hero() {
  const router = useRouter();
  const [activeIdx, setActiveIdx] = useState(0);
  const [resetKey, setResetKey] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setActiveIdx((d) => (d + 1) % DEMOS.length);
      setResetKey((k) => k + 1);
    }, 7000);
    return () => clearInterval(t);
  }, []);

  const handleTab = (i: number) => {
    setActiveIdx(i);
    setResetKey((k) => k + 1);
  };

  const { Demo, desc } = DEMOS[activeIdx];

  return (
    <section className="relative overflow-hidden pb-20">
      <Background />

      <div className="relative z-10 mx-auto max-w-screen-2xl px-8 pt-16 sm:pt-24">

        <div className="mb-10 flex items-stretch gap-8">

          <motion.div
            className="flex w-full shrink-0 flex-col justify-between lg:w-[46%] xl:w-[42%]"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <motion.div
              className="mb-6 inline-flex items-center gap-2 self-start rounded-full border border-violet-500/40 bg-violet-500/10 px-4 py-1.5"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 }}
            >
              <Sparkles className="h-3 w-3 text-muted-foreground" />
              <span className="text-[11px] font-medium tracking-wide text-muted-foreground/90">
                ReAct Agent &middot; Docker &middot; Multi-provider
              </span>
            </motion.div>

            <motion.h1
              className="mb-5 text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
            >
              Build full-stack apps{" "}
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: "linear-gradient(135deg, #a78bfa 0%, #7c3aed 60%, #6d28d9 100%)" }}
              >
                with an AI agent.
              </span>
            </motion.h1>

            <motion.p
              className="mb-8 max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.22 }}
            >
              Describe your idea. A single ReAct agent reads, writes, and runs
              code inside an isolated Docker container — looping until your
              application is built and running.
            </motion.p>

            <motion.div
              className="flex items-center gap-3"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.28 }}
            >
              <Button
                size="lg"
                className="flex-1 cursor-pointer gap-2 bg-violet-600 text-sm font-semibold text-white hover:bg-violet-700"
                onClick={() => router.push("/register")}
              >
                Start Building <ArrowRight className="h-4 w-4" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="flex-1 cursor-pointer text-sm"
                onClick={() => router.push("/login")}
              >
                Sign In
              </Button>
            </motion.div>
          </motion.div>

          <div
            className="relative hidden flex-1 self-stretch overflow-hidden rounded-2xl lg:block"
            style={{
              border: "1px solid rgba(139,92,246,0.50)",
              boxShadow:
                "0 0 40px rgba(139,92,246,0.15), 0 0 80px rgba(109,40,217,0.08)",
            }}
          >
            <div
              className="absolute inset-0"
              style={{
                backgroundImage: `linear-gradient(to right, oklch(0.97 0 0 / 0.08) 1px, transparent 1px),
                                  linear-gradient(to bottom, oklch(0.97 0 0 / 0.08) 1px, transparent 1px)`,
                backgroundSize: "48px 48px",
                WebkitMaskImage:
                  "radial-gradient(ellipse 95% 95% at 50% 50%, black 40%, transparent 100%)",
                maskImage:
                  "radial-gradient(ellipse 95% 95% at 50% 50%, black 40%, transparent 100%)",
              }}
            />

            <div className="relative z-10 grid h-full min-h-80 grid-cols-3 grid-rows-3 gap-2.5 p-1">

              <motion.div
                className="col-span-2 row-span-1 flex flex-col justify-between rounded-xl border border-border bg-card p-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.38 }}
              >
                <div className="mb-2 flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-muted">
                    <Bot className="h-3.5 w-3.5 text-foreground/80" />
                  </div>
                  <span className="text-[13px] font-semibold text-foreground/90">
                    ReAct agent loop
                  </span>
                </div>
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  Think &rarr; call tool &rarr; observe result &rarr; repeat.
                  Reads files, writes code, runs bash, searches the web — all in one loop.
                </p>
              </motion.div>

              <motion.div
                className="col-span-1 row-span-2 flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.44 }}
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-muted">
                  <Container className="h-4 w-4 text-foreground/80" />
                </div>
                <div>
                  <div className="mb-1 text-[13px] font-semibold text-foreground/90">
                    Docker isolation
                  </div>
                  <p className="text-[11px] leading-relaxed text-muted-foreground">
                    Each project runs in its own container with auto-started dev
                    server and live port mapping.
                  </p>
                </div>
                <div className="mt-auto flex flex-col gap-1.5">
                  {["Port 3000", "Port 5173", "Port 8000", "Volume mount"].map(
                    (c) => (
                      <div
                        key={c}
                        className="flex items-center gap-1.5 text-[10px] text-muted-foreground/85"
                      >
                        <div className="h-1 w-1 rounded-full bg-violet-400/60" />
                        {c}
                      </div>
                    )
                  )}
                </div>
              </motion.div>

              <motion.div
                className="col-span-1 row-span-1 flex flex-col justify-between rounded-xl border border-border bg-card p-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.48 }}
              >
                <ScanSearch className="mb-2 h-4 w-4 text-foreground/65" />
                <div>
                  <div className="text-[12px] font-semibold text-foreground/90">
                    Tool approval
                  </div>
                  <div className="mt-0.5 text-[10px] text-muted-foreground/90">
                    Approve or deny each tool call
                  </div>
                </div>
              </motion.div>

              <motion.div
                className="col-span-1 row-span-1 flex flex-col justify-between rounded-xl border border-border bg-card p-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.52 }}
              >
                <Layers className="mb-2 h-4 w-4 text-foreground/65" />
                <div>
                  <div className="text-[12px] font-semibold text-foreground/90">
                    Framework-aware
                  </div>
                  <div className="mt-0.5 text-[10px] text-muted-foreground/90">
                    Next.js · FastAPI · React · full-stack
                  </div>
                </div>
              </motion.div>

              <motion.div
                className="col-span-2 row-span-1 flex items-center gap-4 rounded-xl border border-border bg-card p-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.56 }}
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-muted">
                  <Shield className="h-4 w-4 text-foreground/80" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="mb-1 text-[12px] font-semibold text-foreground/90">
                    Encrypted secrets vault
                  </div>
                  <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                    {[
                      "Fernet AES",
                      "PBKDF2 per-user",
                      "JWT auth",
                      "Multi-provider LLMs",
                    ].map((t) => (
                      <span
                        key={t}
                        className="text-[10px] text-muted-foreground/85"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </motion.div>

              <motion.div
                className="col-span-1 row-span-1 flex flex-col justify-between rounded-xl border border-border bg-card p-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.60 }}
              >
                <Globe className="mb-2 h-4 w-4 text-foreground/65" />
                <div>
                  <div className="text-[12px] font-semibold text-foreground/90">
                    Live preview
                  </div>
                  <div className="mt-0.5 text-[10px] text-muted-foreground/90">
                    TCP probe &middot; auto-detects port
                  </div>
                </div>
              </motion.div>

            </div>
          </div>
        </div>

        <div className="mb-8 flex flex-wrap gap-2 lg:hidden">
          {CHIPS.map(({ icon: Icon, label }, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 + i * 0.04 }}
              className="flex items-center gap-1.5 rounded-full border border-border bg-muted px-3 py-1.5 text-[11px] text-muted-foreground"
            >
              <Icon className="h-3 w-3" />
              {label}
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.35 }}
          className="overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
        >
          <div className="flex items-center gap-2 border-b border-border bg-muted px-4 py-2.5">
            <div className="flex gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
              <div className="h-2.5 w-2.5 rounded-full bg-yellow-500/70" />
              <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/70" />
            </div>
            <span className="ml-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/85">
              Obsidian WebDev
            </span>
            <div className="ml-auto flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" />
              <span className="text-[10px] text-muted-foreground/85">live</span>
            </div>
          </div>

          <div className="flex overflow-x-auto border-b border-border bg-muted/50">
            {DEMOS.map(({ id, label, icon: Icon }, i) => (
              <button
                key={id}
                onClick={() => handleTab(i)}
                className={`flex shrink-0 items-center gap-1.5 border-b-2 px-4 py-2.5 text-[11px] font-medium transition-all ${
                  activeIdx === i
                    ? "border-violet-500 bg-background/30 text-foreground"
                    : "border-transparent text-muted-foreground/85 hover:bg-background/15 hover:text-muted-foreground"
                }`}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
            <div className="hidden flex-1 items-center justify-end px-4 md:flex">
              <AnimatePresence mode="wait">
                <motion.span
                  key={activeIdx}
                  className="text-[10px] italic text-muted-foreground/80"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.18 }}
                >
                  {desc}
                </motion.span>
              </AnimatePresence>
            </div>
          </div>

          <div className="h-80 overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.div
                key={`${activeIdx}-${resetKey}`}
                className="h-full"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <Demo />
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="h-px bg-border/20">
            <motion.div
              key={`bar-${activeIdx}-${resetKey}`}
              className="h-full bg-violet-500/50"
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ duration: 7, ease: "linear" }}
            />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
