"use client";

import { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import { listProjects, createProject, deleteProject, importFromGitHub, importFromZip } from "@/lib/api/projects";
import type { Project, ProjectCreate, ProjectImportGitHub, Framework, ModelProvider } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  Plus,
  MoreHorizontal,
  ExternalLink,
  Trash2,
  Loader2,
  FolderOpen,
  Clock,
  Zap,
  Github,
  Upload,
} from "lucide-react";


const FRAMEWORKS: { value: Framework; label: string; desc: string }[] = [
  { value: "blank", label: "Blank", desc: "Empty project — you decide the structure" },
  { value: "react", label: "React", desc: "Vite + React + TypeScript" },
  { value: "nextjs", label: "Next.js", desc: "Full-stack React with App Router" },
  { value: "fastapi", label: "FastAPI", desc: "Python REST API with async support" },
  { value: "fullstack", label: "Full-stack", desc: "Next.js frontend + FastAPI backend" },
];

const PROVIDERS: { value: ModelProvider; label: string }[] = [
  { value: "anthropic", label: "Anthropic" },
  { value: "openai", label: "OpenAI" },
  { value: "ollama", label: "Ollama (local)" },
  { value: "lmstudio", label: "LM Studio (local)" },
  { value: "obsidian-ai", label: "Obsidian AI" },
];

const PROVIDER_MODELS: Record<ModelProvider, { value: string; label: string }[]> = {
  anthropic: [
    { value: "claude-opus-4-6", label: "Claude Opus 4.6" },
    { value: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
    { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" },
  ],
  openai: [
    { value: "gpt-5.2", label: "GPT-5.2" },
    { value: "gpt-5.2-pro", label: "GPT-5.2 Pro" },
    { value: "gpt-5", label: "GPT-5" },
    { value: "gpt-5-pro", label: "GPT-5 Pro" },
    { value: "gpt-5-mini", label: "GPT-5 Mini" },
    { value: "gpt-5-nano", label: "GPT-5 Nano" },
    { value: "gpt-4.1", label: "GPT-4.1" },
    { value: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
    { value: "gpt-4.1-nano", label: "GPT-4.1 Nano" },
    { value: "o3", label: "o3" },
    { value: "o3-mini", label: "o3-mini" },
    { value: "o3-pro", label: "o3-pro" },
    { value: "o4-mini", label: "o4-mini" },
  ],
  ollama: [],
  lmstudio: [],
  "obsidian-ai": [],
};


const STATUS_CONFIG: Record<string, { label: string; dot: string }> = {
  idle:       { label: "Idle",       dot: "bg-muted-foreground" },
  building:   { label: "Building",   dot: "bg-yellow-400 animate-pulse" },
  preparing:  { label: "Preparing",  dot: "bg-yellow-400 animate-pulse" },
  running:    { label: "Running",    dot: "bg-green-400" },
  stopped:    { label: "Stopped",    dot: "bg-muted-foreground" },
  error:      { label: "Error",      dot: "bg-destructive" },
};

const FRAMEWORK_COLORS: Record<Framework, string> = {
  blank:     "border-muted-foreground/30 text-muted-foreground",
  react:     "border-sky-500/40 text-sky-400",
  nextjs:    "border-foreground/30 text-foreground",
  fastapi:   "border-green-500/40 text-green-400",
  fullstack: "border-primary/40 text-primary",
};


function ProjectCard({
  project,
  onDelete,
}: {
  project: Project;
  onDelete: (id: string) => void;
}) {
  const router = useRouter();
  const status = STATUS_CONFIG[project.status] ?? STATUS_CONFIG.idle;
  const fwColor = FRAMEWORK_COLORS[project.framework as Framework] ?? FRAMEWORK_COLORS.blank;

  return (
    <div className="group relative rounded-xl border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-[0_0_0_1px_oklch(0.68_0.20_280/0.15)]">

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge
              variant="outline"
              className={`text-[10px] px-1.5 py-0 capitalize ${fwColor}`}
            >
              {project.framework}
            </Badge>
            <div className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
              <span className="text-[10px] text-muted-foreground">{status.label}</span>
            </div>
          </div>
          <h3 className="mt-2 font-semibold text-sm leading-snug truncate">
            {project.name}
          </h3>
          {project.description && (
            <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
              {project.description}
            </p>
          )}
        </div>


        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44">
            <DropdownMenuItem onClick={() => router.push(`/workspace/${project.id}`)}>
              <ExternalLink className="mr-2 h-3.5 w-3.5" />
              Open workspace
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => onDelete(project.id)}
            >
              <Trash2 className="mr-2 h-3.5 w-3.5" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>


      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <Clock className="h-3 w-3" />
          {formatDistanceToNow(
            new Date(project.created_at.endsWith("Z") ? project.created_at : project.created_at + "Z"),
            { addSuffix: true },
          )}
        </div>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 px-2.5 text-xs"
          onClick={() => router.push(`/workspace/${project.id}`)}
        >
          Open
          <ExternalLink className="ml-1.5 h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

function ProviderModelFields({
  provider,
  modelId,
  onProviderChange,
  onModelChange,
}: {
  provider: ModelProvider;
  modelId: string;
  onProviderChange: (v: ModelProvider) => void;
  onModelChange: (v: string) => void;
}) {
  const models = PROVIDER_MODELS[provider] ?? [];
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="space-y-1.5">
        <Label>AI Provider</Label>
        <Select value={provider} onValueChange={(v) => onProviderChange(v as ModelProvider)}>
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
        <Label>{provider === "obsidian-ai" ? "Agent / Team ID" : "Model"}</Label>
        {models.length > 0 ? (
          <Select value={modelId} onValueChange={onModelChange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {models.map(({ value, label }) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Input
            placeholder={provider === "obsidian-ai" ? "e.g. my-coding-agent" : "e.g. llama3.2"}
            value={modelId}
            onChange={(e) => onModelChange(e.target.value)}
          />
        )}
      </div>
    </div>
  );
}

function NewProjectDialog({
  onCreated,
}: {
  onCreated: (project: Project) => void;
}) {
  const { data: session } = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"build" | "import">("build");
  const [isLoading, setIsLoading] = useState(false);

  // Build new state
  const [form, setForm] = useState<ProjectCreate>({
    name: "",
    description: "",
    framework: "nextjs",
    model_provider: "openai",
    model_id: "gpt-4.1",
  });

  // Import state
  const [importMode, setImportMode] = useState<"github" | "zip">("github");
  const [importForm, setImportForm] = useState({
    name: "",
    description: "",
    model_provider: "openai" as ModelProvider,
    model_id: "gpt-4.1",
    github_url: "",
  });
  const [zipFile, setZipFile] = useState<File | null>(null);

  const handleProviderChange = (v: ModelProvider) => {
    const defaultModel = PROVIDER_MODELS[v][0]?.value ?? "";
    setForm((f) => ({ ...f, model_provider: v, model_id: defaultModel }));
  };

  const handleImportProviderChange = (v: ModelProvider) => {
    const defaultModel = PROVIDER_MODELS[v][0]?.value ?? "";
    setImportForm((f) => ({ ...f, model_provider: v, model_id: defaultModel }));
  };

  const extractNameFromUrl = (url: string) => {
    try {
      const path = new URL(url).pathname;
      const segments = path.split("/").filter(Boolean);
      const last = segments[segments.length - 1] ?? "";
      return last.replace(/\.git$/, "");
    } catch {
      return "";
    }
  };

  const handleGitHubUrlChange = (url: string) => {
    setImportForm((f) => {
      const autoName = extractNameFromUrl(url);
      return {
        ...f,
        github_url: url,
        name: f.name || autoName,
      };
    });
  };

  const handleZipFileChange = (file: File | null) => {
    setZipFile(file);
    if (file) {
      const autoName = file.name.replace(/\.zip$/i, "");
      setImportForm((f) => ({ ...f, name: f.name || autoName }));
    }
  };

  const resetAndClose = () => {
    setOpen(false);
    setTab("build");
    setForm({ name: "", description: "", framework: "nextjs", model_provider: "openai", model_id: "gpt-4.1" });
    setImportForm({ name: "", description: "", model_provider: "openai", model_id: "gpt-4.1", github_url: "" });
    setImportMode("github");
    setZipFile(null);
  };

  const handleBuildSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session?.accessToken) return;
    setIsLoading(true);
    try {
      const project = await createProject(form, session.accessToken);
      onCreated(project);
      resetAndClose();
      router.push(`/workspace/${project.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsLoading(false);
    }
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session?.accessToken) return;
    setIsLoading(true);
    try {
      let project: Project;
      if (importMode === "github") {
        const payload: ProjectImportGitHub = {
          name: importForm.name,
          description: importForm.description,
          model_provider: importForm.model_provider,
          model_id: importForm.model_id,
          github_url: importForm.github_url,
        };
        project = await importFromGitHub(payload, session.accessToken);
      } else {
        if (!zipFile) {
          toast.error("Please select a zip file");
          return;
        }
        const fd = new FormData();
        fd.append("file", zipFile);
        fd.append("name", importForm.name);
        fd.append("description", importForm.description);
        fd.append("model_provider", importForm.model_provider);
        fd.append("model_id", importForm.model_id);
        project = await importFromZip(fd, session.accessToken);
      }
      onCreated(project);
      resetAndClose();
      router.push(`/workspace/${project.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to import project");
    } finally {
      setIsLoading(false);
    }
  };

  const importSubmitDisabled =
    isLoading ||
    !importForm.name.trim() ||
    !importForm.model_id.trim() ||
    (importMode === "github" ? !importForm.github_url.trim() : !zipFile);

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) resetAndClose(); else setOpen(true); }}>
      <DialogTrigger asChild>
        <Button className="gap-1.5">
          <Plus className="h-4 w-4" />
          New project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {tab === "build" ? "Create a new project" : "Import a project"}
          </DialogTitle>
          <DialogDescription>
            {tab === "build"
              ? "Choose a framework and model — Obsidian WebDev will do the rest."
              : "Bring in existing code from GitHub or a zip file."}
          </DialogDescription>
        </DialogHeader>

        {/* Tab switcher */}
        <div className="flex gap-1 rounded-lg border bg-muted/40 p-1">
          <button
            type="button"
            onClick={() => setTab("build")}
            className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === "build"
                ? "bg-background shadow-sm text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Build new
          </button>
          <button
            type="button"
            onClick={() => setTab("import")}
            className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === "import"
                ? "bg-background shadow-sm text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Import existing
          </button>
        </div>

        {tab === "build" ? (
          <form id="new-project-form" onSubmit={handleBuildSubmit} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="proj-name">Project name</Label>
              <Input
                id="proj-name"
                placeholder="My awesome app"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="proj-desc">
                Description{" "}
                <span className="text-muted-foreground font-normal">(optional)</span>
              </Label>
              <Textarea
                id="proj-desc"
                placeholder="What does this project do?"
                rows={2}
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                className="resize-none"
              />
            </div>

            <div className="space-y-1.5">
              <Label>Framework</Label>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {FRAMEWORKS.map(({ value, label, desc }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, framework: value }))}
                    className={`rounded-lg border p-3 text-left transition-colors hover:border-primary/50 ${
                      form.framework === value
                        ? "border-primary bg-primary/10"
                        : "border-border"
                    }`}
                  >
                    <p className="text-xs font-medium">{label}</p>
                    <p className="mt-0.5 text-[10px] text-muted-foreground leading-snug">
                      {desc}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            <ProviderModelFields
              provider={form.model_provider!}
              modelId={form.model_id!}
              onProviderChange={handleProviderChange}
              onModelChange={(v) => setForm((f) => ({ ...f, model_id: v }))}
            />
          </form>
        ) : (
          <form id="new-project-form" onSubmit={handleImportSubmit} className="space-y-4 py-2">
            {/* Import mode toggle */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setImportMode("github")}
                className={`flex items-center gap-2 rounded-lg border p-3 text-left transition-colors hover:border-primary/50 ${
                  importMode === "github" ? "border-primary bg-primary/10" : "border-border"
                }`}
              >
                <Github className="h-4 w-4 shrink-0" />
                <div>
                  <p className="text-xs font-medium">Git URL</p>
                  <p className="text-[10px] text-muted-foreground">Clone public or private repo</p>
                </div>
              </button>
              <button
                type="button"
                onClick={() => setImportMode("zip")}
                className={`flex items-center gap-2 rounded-lg border p-3 text-left transition-colors hover:border-primary/50 ${
                  importMode === "zip" ? "border-primary bg-primary/10" : "border-border"
                }`}
              >
                <Upload className="h-4 w-4 shrink-0" />
                <div>
                  <p className="text-xs font-medium">Upload ZIP</p>
                  <p className="text-[10px] text-muted-foreground">Upload a .zip file</p>
                </div>
              </button>
            </div>

            {importMode === "github" ? (
              <div className="space-y-1.5">
                <Label htmlFor="import-url">Repository URL</Label>
                <Input
                  id="import-url"
                  placeholder="https://github.com/owner/repo or git@github.com:owner/repo.git"
                  value={importForm.github_url}
                  onChange={(e) => handleGitHubUrlChange(e.target.value)}
                  required
                />
                {(importForm.github_url.startsWith("git@") || importForm.github_url.startsWith("ssh://")) && (
                  <p className="flex items-center gap-1.5 text-[11px] text-yellow-600 dark:text-yellow-400">
                    <span className="text-yellow-500">⚠</span>
                    SSH URL detected — generate an SSH key in the workspace Git panel and add it to GitHub before starting this project.
                  </p>
                )}
                {importForm.github_url.startsWith("https://") && (
                  <p className="text-[10px] text-muted-foreground">
                    For private repos, save a GitHub PAT in <span className="font-medium">Settings → Add key → GitHub (PAT)</span> — it will be used automatically.
                  </p>
                )}
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label htmlFor="import-zip">ZIP file</Label>
                <div
                  className={`flex items-center justify-center rounded-lg border-2 border-dashed p-6 text-center transition-colors cursor-pointer hover:border-primary/50 ${
                    zipFile ? "border-primary/50 bg-primary/5" : "border-border"
                  }`}
                  onClick={() => document.getElementById("import-zip-input")?.click()}
                >
                  {zipFile ? (
                    <div className="space-y-1">
                      <Upload className="mx-auto h-5 w-5 text-primary" />
                      <p className="text-xs font-medium">{zipFile.name}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {(zipFile.size / 1024 / 1024).toFixed(1)} MB — click to change
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <Upload className="mx-auto h-5 w-5 text-muted-foreground" />
                      <p className="text-xs text-muted-foreground">
                        Click to select a <span className="font-medium">.zip</span> file
                      </p>
                      <p className="text-[10px] text-muted-foreground">Max 100 MB</p>
                    </div>
                  )}
                </div>
                <input
                  id="import-zip-input"
                  type="file"
                  accept=".zip,application/zip"
                  className="hidden"
                  onChange={(e) => handleZipFileChange(e.target.files?.[0] ?? null)}
                />
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="import-name">Project name</Label>
              <Input
                id="import-name"
                placeholder="My awesome app"
                value={importForm.name}
                onChange={(e) => setImportForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="import-desc">
                Description{" "}
                <span className="text-muted-foreground font-normal">(optional)</span>
              </Label>
              <Textarea
                id="import-desc"
                placeholder="What does this project do?"
                rows={2}
                value={importForm.description}
                onChange={(e) => setImportForm((f) => ({ ...f, description: e.target.value }))}
                className="resize-none"
              />
            </div>

            <ProviderModelFields
              provider={importForm.model_provider}
              modelId={importForm.model_id}
              onProviderChange={handleImportProviderChange}
              onModelChange={(v) => setImportForm((f) => ({ ...f, model_id: v }))}
            />
          </form>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={resetAndClose} type="button">
            Cancel
          </Button>
          {tab === "build" ? (
            <Button
              type="submit"
              form="new-project-form"
              disabled={isLoading || !form.name.trim()}
              className="gap-1.5"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating…
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  Create project
                </>
              )}
            </Button>
          ) : (
            <Button
              type="submit"
              form="new-project-form"
              disabled={importSubmitDisabled}
              className="gap-1.5"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Importing…
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  Import project
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


export default function DashboardPage() {
  const { data: session } = useSession();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchProjects = useCallback(async () => {
    if (!session?.accessToken) return;
    try {
      const data = await listProjects(session.accessToken);
      setProjects(data);
    } catch {
      toast.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreated = (project: Project) => {
    setProjects((prev) => [project, ...prev]);
  };

  const confirmDelete = async () => {
    if (!pendingDeleteId || !session?.accessToken) return;
    setIsDeleting(true);
    try {
      await deleteProject(pendingDeleteId, session.accessToken);
      setProjects((prev) => prev.filter((p) => p.id !== pendingDeleteId));
      for (const k of ["msgs", "session", "build", "history"]) {
        localStorage.removeItem(`wai-${k}-${pendingDeleteId}`);
      }
      localStorage.removeItem(`agent-chat-model-${pendingDeleteId}`);
      toast.success("Project deleted");
      setPendingDeleteId(null);
    } catch {
      toast.error("Failed to delete project");
    } finally {
      setIsDeleting(false);
    }
  };

  const pendingProject = projects.find((p) => p.id === pendingDeleteId);

  return (
    <div className="flex flex-1 flex-col min-h-0">

      <header className="flex h-14 shrink-0 items-center gap-4 border-b px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="h-5" />
        <h1 className="text-sm font-semibold">Projects</h1>
        <div className="ml-auto">
          <NewProjectDialog onCreated={handleCreated} />
        </div>
      </header>


      <main className="flex-1 p-6">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-[152px] rounded-xl" />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-24 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
              <FolderOpen className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="mt-4 text-sm font-semibold">No projects yet</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Create your first project to start building with AI.
            </p>
            <div className="mt-6">
              <NewProjectDialog onCreated={handleCreated} />
            </div>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onDelete={setPendingDeleteId}
              />
            ))}
          </div>
        )}
      </main>

      <Dialog
        open={!!pendingDeleteId}
        onOpenChange={(open) => { if (!open && !isDeleting) setPendingDeleteId(null); }}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete project</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete{" "}
              <span className="font-medium text-foreground">
                {pendingProject?.name ?? "this project"}
              </span>
              ? All files, agent sessions, and container data will be permanently removed.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex gap-3 sm:gap-2">
            <Button
              variant="outline"
              onClick={() => setPendingDeleteId(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={isDeleting}
              className="gap-1.5"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Deleting…
                </>
              ) : (
                <>
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete project
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
