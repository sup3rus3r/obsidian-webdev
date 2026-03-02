"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import dynamic from "next/dynamic";
import { toast } from "sonner";
import { getProject, runProject, stopProject, exportProject, probePreview } from "@/lib/api/projects";
import { ApiError } from "@/lib/api/client";
import { listFiles, getFile, writeFile, buildFileTree } from "@/lib/api/files";
import type { Project, FileNode } from "@/types/api";
import { cn } from "@/lib/utils";
import { FileTree } from "@/components/workspace/file-tree";
import { AgentChat } from "@/components/workspace/agent-chat";
import { TerminalPanel } from "@/components/workspace/terminal-panel";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  Save,
  Loader2,
  Zap,
  FolderTree,
  Play,
  Square,
  X,
  ExternalLink,
  Maximize2,
  Minimize2,
  Download,
  Plus,
  Check,
  RefreshCw,
  Monitor,
} from "lucide-react";


const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  { ssr: false, loading: () => <Skeleton className="h-full w-full rounded-none" /> },
);


interface EditorTab {
  path: string;
  content: string;
  language: string;
  isDirty: boolean;
}


const STATUS_DOT: Record<string, string> = {
  idle:      "bg-muted-foreground",
  building:  "bg-yellow-400 animate-pulse",
  preparing: "bg-yellow-400 animate-pulse",
  running:   "bg-green-400",
  stopped:   "bg-muted-foreground",
  error:     "bg-destructive",
};


export default function WorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const { data: session, status: authStatus } = useSession();

  const [project, setProject] = useState<Project | null>(null);
  const [fileNodes, setFileNodes] = useState<FileNode[]>([]);


  const [openTabs, setOpenTabs] = useState<EditorTab[]>([]);
  const [activeTabPath, setActiveTabPath] = useState<string | null>(null);

  const [isSaving, setIsSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isContainerLoading, setIsContainerLoading] = useState(false);
  const [terminalKey, setTerminalKey] = useState(0);
  const [newFileInputOpen, setNewFileInputOpen] = useState(false);
  const [newFileInput, setNewFileInput] = useState("");
  const [previewIframeKey, setPreviewIframeKey] = useState(0);
  const [isProbing, setIsProbing] = useState(false);
  const [isBuildRunning, setIsBuildRunning] = useState(false);
  const [previewExpanded, setPreviewExpanded] = useState(false);


  const editorValueRef = useRef("");
  const newFileInputRef = useRef<HTMLInputElement>(null);

  const activeTab = openTabs.find((t) => t.path === activeTabPath) ?? null;
  editorValueRef.current = activeTab?.content ?? "";


  const previewUrl = project?.preview_url ?? null;


  useEffect(() => {
    if (authStatus === "unauthenticated") router.push("/login");
  }, [authStatus, router]);


  const loadData = useCallback(async () => {
    if (!session?.accessToken) return;
    try {
      const [proj, files] = await Promise.all([
        getProject(projectId, session.accessToken),
        listFiles(projectId, session.accessToken),
      ]);
      setProject(proj);
      setFileNodes(buildFileTree(files));


      if (proj.status !== "running" && proj.status !== "building") {
        setIsContainerLoading(true);
        setProject((p) => (p ? { ...p, status: "building" } : p));
        try {
          const updated = await runProject(projectId, session.accessToken);
          setProject(updated);
          setTerminalKey((k) => k + 1);
        } catch {

          setProject(proj);
        } finally {
          setIsContainerLoading(false);
        }
      }
    } catch {
      toast.error("Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [projectId, session?.accessToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);


  const handleSelectFile = useCallback(
    async (path: string) => {

      const existing = openTabs.find((t) => t.path === path);
      if (existing) {
        setActiveTabPath(path);
        return;
      }

      if (!session?.accessToken) return;
      try {
        const file = await getFile(projectId, path, session.accessToken);
        const language = mapLanguage(file.language, path);
        setOpenTabs((prev) => [
          ...prev,
          { path, content: file.content, language, isDirty: false },
        ]);
        setActiveTabPath(path);
      } catch {
        toast.error("Failed to load file");
      }
    },
    [projectId, session?.accessToken, openTabs],
  );

  const handleCloseTab = useCallback(
    (path: string, e: React.MouseEvent) => {
      e.stopPropagation();
      const idx = openTabs.findIndex((t) => t.path === path);
      const next = openTabs.filter((t) => t.path !== path);
      setOpenTabs(next);
      if (path === activeTabPath) {

        setActiveTabPath(next[Math.min(idx, next.length - 1)]?.path ?? null);
      }
    },
    [openTabs, activeTabPath],
  );


  const handleFileWrite = useCallback(
    async (path?: string) => {
      if (!session?.accessToken) return;
      try {
        const files = await listFiles(projectId, session.accessToken);
        setFileNodes(buildFileTree(files));

        if (!path) return;

        const isOpen = openTabs.some((t) => t.path === path);
        if (isOpen) {
          try {
            const file = await getFile(projectId, path, session.accessToken);
            const language = mapLanguage(file.language, path);
            setOpenTabs((prev) =>
              prev.map((t) =>
                t.path === path
                  ? { ...t, content: file.content, language, isDirty: false }
                  : t,
              ),
            );
          } catch {

          }
        } else if (openTabs.length === 0) {
          try {
            const file = await getFile(projectId, path, session.accessToken!);
            const language = mapLanguage(file.language, path);
            setOpenTabs([{ path, content: file.content, language, isDirty: false }]);
            setActiveTabPath(path);
          } catch {

          }
        }
      } catch {

      }
    },
    [projectId, session?.accessToken, openTabs, handleSelectFile],
  );


  const handleRun = async () => {
    if (!session?.accessToken || !project) return;
    setIsContainerLoading(true);
    setProject((p) => (p ? { ...p, status: "building" } : p));
    try {
      const updated = await runProject(projectId, session.accessToken);
      setProject(updated);
      setTerminalKey((k) => k + 1);
      toast.success("Container started");
    } catch (err) {
      setProject((p) => (p ? { ...p, status: "error" } : p));
      const msg = err instanceof ApiError ? err.detail : "Failed to start container";
      toast.error(msg);
    } finally {
      setIsContainerLoading(false);
    }
  };

  const handleStopContainer = async () => {
    if (!session?.accessToken || !project) return;
    setIsContainerLoading(true);
    try {
      const updated = await stopProject(projectId, session.accessToken);
      setProject(updated);
      toast.success("Container stopped");
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "Failed to stop container";
      toast.error(msg);
    } finally {
      setIsContainerLoading(false);
    }
  };


  const handleSave = async () => {
    if (!session?.accessToken || !activeTab || !activeTab.isDirty) return;
    setIsSaving(true);
    try {
      await writeFile(projectId, activeTab.path, editorValueRef.current, session.accessToken);
      setOpenTabs((prev) =>
        prev.map((t) => (t.path === activeTab.path ? { ...t, isDirty: false } : t)),
      );
      toast.success("Saved");
    } catch {
      toast.error("Save failed");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreateFile = useCallback(async () => {
    const path = newFileInput.trim();
    if (!path || !session?.accessToken) return;
    setNewFileInputOpen(false);
    setNewFileInput("");
    try {
      await writeFile(projectId, path, "", session.accessToken);
      const files = await listFiles(projectId, session.accessToken);
      setFileNodes(buildFileTree(files));
      await handleSelectFile(path);
    } catch {
      toast.error("Failed to create file");
    }
  }, [newFileInput, projectId, session?.accessToken, handleSelectFile]);

  const handleDownloadFile = useCallback(() => {
    if (!activeTab) return;
    const blob = new Blob([editorValueRef.current], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileBasename(activeTab.path);
    a.click();
    URL.revokeObjectURL(url);
  }, [activeTab]);

  const handleExportZip = async () => {
    if (!session?.accessToken) return;
    try {
      await exportProject(projectId, session.accessToken);
    } catch {
      toast.error("Export failed");
    }
  };


  useEffect(() => {
    if (newFileInputOpen) {
      setTimeout(() => newFileInputRef.current?.focus(), 0);
    }
  }, [newFileInputOpen]);


  useEffect(() => {
    if (project?.status !== "preparing" || !session?.accessToken) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const updated = await getProject(projectId, session.accessToken!);
        if (cancelled) return;
        if (updated.status === "running") {


          const files = await listFiles(projectId, session.accessToken!);
          if (cancelled) return;
          setFileNodes(buildFileTree(files));
          setProject(updated);
        } else {
          setProject(updated);
        }
      } catch {}
    };

    const id = setInterval(poll, 2500);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [project?.status, projectId, session?.accessToken]);


  useEffect(() => {
    if (project?.status !== "running" || fileNodes.length > 0 || !session?.accessToken) return;
    let cancelled = false;
    const id = setTimeout(async () => {
      try {
        const files = await listFiles(projectId, session.accessToken!);
        if (!cancelled) setFileNodes(buildFileTree(files));
      } catch {}
    }, 1500);
    return () => { cancelled = true; clearTimeout(id); };
  }, [project?.status, fileNodes.length, projectId, session?.accessToken]);


  useEffect(() => {
    if (project?.status !== "running" || !session?.accessToken) return;
    let cancelled = false;

    const probe = async () => {
      setIsProbing(true);
      try {
        const found = await probePreview(projectId, session.accessToken!);
        if (!cancelled && found !== null) {
          setProject((p) => (p ? { ...p, preview_url: found } : p));
        }
      } catch {  } finally {
        if (!cancelled) setIsProbing(false);
      }
    };

    probe();
    const id = setInterval(probe, 5000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };

  }, [project?.status, session?.accessToken, projectId]);


  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);

  }, [activeTab]);


  if (authStatus === "loading" || loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  if (authStatus === "unauthenticated") return null;

  const statusDot = project ? (STATUS_DOT[project.status] ?? STATUS_DOT.idle) : "";

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">

      <header className="flex h-12 shrink-0 items-center gap-3 border-b px-4">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => router.push("/dashboard")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>

        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-primary/15">
            <Zap className="h-3.5 w-3.5 text-primary" />
          </div>
          <span className="text-sm font-semibold">{project?.name ?? "…"}</span>
          {project && (
            <div className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${statusDot}`} />
              <span className="text-[11px] text-muted-foreground capitalize">
                {project.status}
              </span>
            </div>
          )}
          {project && (
            <Badge variant="outline" className="text-[10px] capitalize px-1.5 py-0">
              {project.framework}
            </Badge>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {project && (
            project.status === "running" ? (
              <Button
                size="sm"
                variant="outline"
                className="h-7 gap-1.5 text-xs"
                onClick={handleStopContainer}
                disabled={isContainerLoading}
              >
                {isContainerLoading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Square className="h-3.5 w-3.5" />
                )}
                Stop
              </Button>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="h-7 gap-1.5 text-xs"
                onClick={handleRun}
                disabled={isContainerLoading || project.status === "building"}
              >
                {isContainerLoading || project.status === "building" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Play className="h-3.5 w-3.5" />
                )}
                Run
              </Button>
            )
          )}
          {activeTab?.isDirty && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 gap-1.5 text-xs"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Save
            </Button>
          )}
        </div>
      </header>


      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup id="workspace" orientation="horizontal" className="h-full">

          <ResizablePanel id="sidebar" defaultSize="18" minSize="12" maxSize="35">
            <div className="h-full flex flex-col border-r overflow-hidden">
              <div className="flex h-8 shrink-0 items-center gap-1 border-b px-2">
                <FolderTree className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="flex-1 text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
                  Files
                </span>
                <button
                  type="button"
                  title="New file"
                  onClick={() => setNewFileInputOpen((o) => !o)}
                  className="flex h-5 w-5 items-center justify-center rounded hover:bg-muted/60 text-muted-foreground/60 hover:text-foreground"
                >
                  <Plus className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  title="Export as ZIP"
                  onClick={handleExportZip}
                  className="flex h-5 w-5 items-center justify-center rounded hover:bg-muted/60 text-muted-foreground/60 hover:text-foreground"
                >
                  <Download className="h-3 w-3" />
                </button>
              </div>
              {newFileInputOpen && (
                <div className="flex items-center gap-1 border-b px-2 py-1">
                  <input
                    ref={newFileInputRef}
                    type="text"
                    value={newFileInput}
                    onChange={(e) => setNewFileInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleCreateFile();
                      if (e.key === "Escape") { setNewFileInputOpen(false); setNewFileInput(""); }
                    }}
                    placeholder="src/file.ts"
                    className="flex-1 rounded bg-muted/40 px-1.5 py-0.5 text-[11px] font-mono text-foreground outline-none focus:ring-1 focus:ring-primary/40 border border-border/30"
                  />
                  <button
                    type="button"
                    onClick={handleCreateFile}
                    className="flex h-5 w-5 items-center justify-center rounded bg-primary/20 hover:bg-primary/30 text-primary"
                  >
                    <Check className="h-3 w-3" />
                  </button>
                </div>
              )}
              <div className="flex-1 overflow-hidden">
                <FileTree
                  nodes={fileNodes}
                  selectedPath={activeTabPath}
                  onSelect={handleSelectFile}
                />
              </div>
            </div>
          </ResizablePanel>
          <ResizableHandle withHandle />


          <ResizablePanel id="main" defaultSize="82">
            <ResizablePanelGroup id="workspace-vertical" orientation="vertical" className="h-full">

              <ResizablePanel defaultSize="68" minSize="40">
                <ResizablePanelGroup orientation="horizontal" className="h-full">

                  <ResizablePanel defaultSize="60" minSize="30">
                    <div className="h-full flex flex-col">

                      <div className="flex h-8 shrink-0 items-stretch border-b overflow-x-auto scrollbar-none bg-muted/30">
                        {openTabs.length === 0 ? (
                          <span className="flex items-center px-3 text-[11px] text-muted-foreground">
                            Select a file to edit
                          </span>
                        ) : (
                          openTabs.map((tab) => (
                            <button
                              key={tab.path}
                              onClick={() => setActiveTabPath(tab.path)}
                              className={cn(
                                "group flex items-center gap-1.5 h-full px-3 border-r shrink-0",
                                "text-[11px] font-mono transition-colors",
                                tab.path === activeTabPath
                                  ? "bg-background text-foreground border-t-2 border-t-primary"
                                  : "text-muted-foreground hover:text-foreground hover:bg-accent/40",
                              )}
                            >
                              <span className="max-w-[120px] truncate">
                                {fileBasename(tab.path)}
                              </span>
                              {tab.isDirty && (
                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                              )}
                              <span
                                role="button"
                                onClick={(e) => handleCloseTab(tab.path, e)}
                                className={cn(
                                  "shrink-0 rounded-sm p-0.5 -mr-1",
                                  "opacity-0 group-hover:opacity-100",
                                  "hover:bg-accent text-muted-foreground hover:text-foreground",
                                )}
                              >
                                <X className="h-3 w-3" />
                              </span>
                            </button>
                          ))
                        )}

                        {activeTab && (
                          <button
                            type="button"
                            title="Download file"
                            onClick={handleDownloadFile}
                            className="ml-auto flex h-full items-center px-2 text-muted-foreground/50 hover:text-foreground hover:bg-accent/40 border-l shrink-0"
                          >
                            <Download className="h-3 w-3" />
                          </button>
                        )}
                      </div>


                      <div className="flex-1 min-h-0">
                        <MonacoEditor
                          height="100%"
                          language={activeTab?.language ?? "plaintext"}
                          value={activeTab?.content ?? ""}
                          theme="vs-dark"
                          options={{
                            fontSize: 13,
                            fontFamily: '"Geist Mono", "JetBrains Mono", monospace',
                            minimap: { enabled: false },
                            padding: { top: 12, bottom: 12 },
                            scrollBeyondLastLine: false,
                            renderLineHighlight: "none",
                            overviewRulerBorder: false,
                            lineNumbersMinChars: 3,
                            readOnly: !activeTab,
                          }}
                          onChange={(value) => {
                            const content = value ?? "";
                            editorValueRef.current = content;
                            setOpenTabs((prev) =>
                              prev.map((t) =>
                                t.path === activeTabPath
                                  ? { ...t, content, isDirty: true }
                                  : t,
                              ),
                            );
                          }}
                        />
                      </div>
                    </div>
                  </ResizablePanel>

                  <ResizableHandle withHandle />


                  <ResizablePanel defaultSize="40" minSize="25" maxSize="55">
                    <AgentChat
                      projectId={projectId}
                      onFileWrite={handleFileWrite}
                      onBuildRunningChange={setIsBuildRunning}
                      defaultModelProvider={project?.model_provider}
                      defaultModelId={project?.model_id}
                      disabled={project?.status === "preparing"}
                    />
                  </ResizablePanel>
                </ResizablePanelGroup>
              </ResizablePanel>

              <ResizableHandle withHandle />


              <ResizablePanel defaultSize="32" minSize="18">
                <ResizablePanelGroup orientation="horizontal" className="h-full">
                  <ResizablePanel defaultSize="55" minSize="30">
                    <div className="h-full flex flex-col">
                      <div className="flex h-8 shrink-0 items-center border-b px-3">
                        <span className="text-[11px] font-medium text-muted-foreground">Terminal</span>
                      </div>
                      <div className="flex-1 overflow-hidden">
                        <TerminalPanel key={terminalKey} projectId={projectId} visible={true} />
                      </div>
                    </div>
                  </ResizablePanel>
                  <ResizableHandle withHandle />
                  <ResizablePanel defaultSize="45" minSize="25">
                    <MiniPreview
                      previewUrl={previewUrl}
                      isBuildRunning={isBuildRunning}
                      containerRunning={project?.status === "running"}
                      isProbing={isProbing}
                      expanded={previewExpanded}
                      onExpand={() => setPreviewExpanded(true)}
                      onCollapse={() => setPreviewExpanded(false)}
                      onReload={() => setPreviewIframeKey((k) => k + 1)}
                      iframeKey={previewIframeKey}
                    />
                  </ResizablePanel>
                </ResizablePanelGroup>


                {previewExpanded && previewUrl && (
                  <div className="fixed inset-0 z-50 flex flex-col bg-background">
                    <div className="flex h-9 shrink-0 items-center justify-between border-b px-3">
                      <span className="text-xs font-medium text-muted-foreground">
                        Preview — {project?.name}
                      </span>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          title="Open in new tab"
                          onClick={() => window.open(previewUrl!, "_blank")}
                        >
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          title="Exit fullscreen"
                          onClick={() => setPreviewExpanded(false)}
                        >
                          <Minimize2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <iframe
                      key={previewIframeKey}
                      src={previewUrl!}
                      className="flex-1 border-0"
                      title="App preview (fullscreen)"
                    />
                  </div>
                )}
              </ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}


function MiniPreview({
  previewUrl,
  isBuildRunning,
  containerRunning,
  isProbing,
  expanded,
  onExpand,
  onCollapse,
  onReload,
  iframeKey,
}: {
  previewUrl: string | null;
  isBuildRunning: boolean;
  containerRunning: boolean;
  isProbing: boolean;
  expanded: boolean;
  onExpand: () => void;
  onCollapse: () => void;
  onReload: () => void;
  iframeKey: number;
}) {
  return (
    <div className="flex h-full flex-col border-t">
      <div className="flex h-8 shrink-0 items-center justify-between border-b px-2">
        <div className="flex items-center gap-1.5">
          <Monitor className="h-3 w-3 text-muted-foreground/60" />
          <span className="text-[11px] font-medium text-muted-foreground">Preview</span>
          {isBuildRunning && (
            <span className="flex items-center gap-1 text-[10px] text-yellow-500">
              <span className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-pulse" />
              Building
            </span>
          )}
          {!isBuildRunning && isProbing && !previewUrl && (
            <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
              Starting
            </span>
          )}
          {previewUrl && !isBuildRunning && (
            <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
          )}
        </div>
        <div className="flex items-center gap-0.5">
          <Button variant="ghost" size="icon" className="h-6 w-6" title="Reload" onClick={onReload}>
            <RefreshCw className="h-3 w-3" />
          </Button>
          {previewUrl && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                title="Open in new tab"
                onClick={() => window.open(previewUrl, "_blank")}
              >
                <ExternalLink className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                title="Expand preview"
                onClick={onExpand}
              >
                <Maximize2 className="h-3 w-3" />
              </Button>
            </>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-hidden bg-muted/10">
        {previewUrl ? (
          <iframe
            key={iframeKey}
            src={previewUrl}
            className="h-full w-full border-0"
            title="App preview"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center">
            {isBuildRunning ? (
              <>
                <div className="flex gap-1">
                  {[0, 100, 200].map((d) => (
                    <span
                      key={d}
                      className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-bounce"
                      style={{ animationDelay: `${d}ms` }}
                    />
                  ))}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Building — preview will appear when the dev server starts
                </p>
              </>
            ) : !containerRunning ? (
              <p className="text-[11px] text-muted-foreground">
                Start the container to see the preview
              </p>
            ) : (
              <>
                {isProbing && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                <p className="text-[11px] text-muted-foreground">
                  Waiting for dev server…
                </p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


function fileBasename(path: string): string {
  return path.split("/").pop() ?? path;
}

function mapLanguage(lang: string, path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  const EXT_MAP: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    json: "json",
    md: "markdown",
    css: "css",
    html: "html",
    yaml: "yaml",
    yml: "yaml",
    sh: "shell",
    bash: "shell",
    toml: "toml",
    env: "shell",
  };
  return EXT_MAP[ext] ?? lang ?? "plaintext";
}
