"use client";

import { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import { listProjects, createProject, deleteProject } from "@/lib/api/projects";
import type { Project, ProjectCreate, Framework, ModelProvider } from "@/types/api";
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
    { value: "gpt-4.1", label: "GPT-4.1" },
    { value: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
    { value: "o3", label: "o3" },
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

function NewProjectDialog({
  onCreated,
}: {
  onCreated: (project: Project) => void;
}) {
  const { data: session } = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [form, setForm] = useState<ProjectCreate>({
    name: "",
    description: "",
    framework: "nextjs",
    model_provider: "openai",
    model_id: "gpt-4.1",
  });

  const models = PROVIDER_MODELS[form.model_provider!] ?? [];

  const handleProviderChange = (v: ModelProvider) => {
    const defaultModel = PROVIDER_MODELS[v][0]?.value ?? "";
    setForm((f) => ({ ...f, model_provider: v, model_id: defaultModel }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session?.accessToken) return;
    setIsLoading(true);
    try {
      const project = await createProject(form, session.accessToken);
      onCreated(project);
      setOpen(false);
      setForm({
        name: "",
        description: "",
        framework: "nextjs",
        model_provider: "openai",
        model_id: "gpt-4.1",
      });
      router.push(`/workspace/${project.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-1.5">
          <Plus className="h-4 w-4" />
          New project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create a new project</DialogTitle>
          <DialogDescription>
            Choose a framework and model — Obsidian WebDev will do the rest.
          </DialogDescription>
        </DialogHeader>

        <form id="new-project-form" onSubmit={handleSubmit} className="space-y-4 py-2">

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


          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>AI Provider</Label>
              <Select
                value={form.model_provider}
                onValueChange={(v) => handleProviderChange(v as ModelProvider)}
              >
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
              <Label>{form.model_provider === "obsidian-ai" ? "Agent / Team ID" : "Model"}</Label>
              {models.length > 0 ? (
                <Select
                  value={form.model_id}
                  onValueChange={(v) => setForm((f) => ({ ...f, model_id: v }))}
                >
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
                  placeholder={
                    form.model_provider === "obsidian-ai"
                      ? "e.g. my-coding-agent"
                      : "e.g. llama3.2"
                  }
                  value={form.model_id}
                  onChange={(e) => setForm((f) => ({ ...f, model_id: e.target.value }))}
                />
              )}
            </div>
          </div>
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} type="button">
            Cancel
          </Button>
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
