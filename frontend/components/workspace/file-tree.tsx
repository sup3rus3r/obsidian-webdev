"use client";

import { useState } from "react";
import type { FileNode } from "@/types/api";
import { cn } from "@/lib/utils";
import {
  ChevronRight,
  File,
  FileCode,
  FileJson,
  FileText,
  FolderOpen,
  Folder,
} from "lucide-react";


const LANG_ICONS: Record<string, React.ElementType> = {
  typescript: FileCode,
  javascript: FileCode,
  tsx: FileCode,
  jsx: FileCode,
  json: FileJson,
  markdown: FileText,
  md: FileText,
  text: FileText,
  py: FileCode,
  python: FileCode,
};

function getFileIcon(name: string): React.ElementType {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return LANG_ICONS[ext] ?? File;
}


function TreeNode({
  node,
  depth,
  selectedPath,
  onSelect,
}: {
  node: FileNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isDir = node.type === "directory";
  const isSelected = !isDir && node.path === selectedPath;
  const FileIcon = getFileIcon(node.name);

  if (isDir) {
    return (
      <div>
        <button
          onClick={() => setExpanded((e) => !e)}
          className={cn(
            "flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left text-xs transition-colors hover:bg-sidebar-accent",
          )}
          style={{ paddingLeft: `${8 + depth * 12}px` }}
        >
          <ChevronRight
            className={cn(
              "h-3 w-3 shrink-0 text-muted-foreground transition-transform",
              expanded && "rotate-90",
            )}
          />
          {expanded ? (
            <FolderOpen className="h-3.5 w-3.5 shrink-0 text-primary/70" />
          ) : (
            <Folder className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate text-foreground/80">{node.name}</span>
        </button>
        {expanded && node.children?.map((child) => (
          <TreeNode
            key={child.path}
            node={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            onSelect={onSelect}
          />
        ))}
      </div>
    );
  }

  return (
    <button
      onClick={() => onSelect(node.path)}
      className={cn(
        "flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left text-xs transition-colors hover:bg-sidebar-accent",
        isSelected && "bg-sidebar-accent text-sidebar-accent-foreground font-medium",
      )}
      style={{ paddingLeft: `${8 + depth * 12}px` }}
    >
      <span className="w-3" /> 
      <FileIcon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <span className="truncate">{node.name}</span>
    </button>
  );
}


export function FileTree({
  nodes,
  selectedPath,
  onSelect,
}: {
  nodes: FileNode[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 py-8 px-4 text-center">
        <File className="h-8 w-8 text-muted-foreground/40" />
        <p className="text-[11px] text-muted-foreground">
          No files yet. Start the agent to generate your project.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5 py-2 overflow-y-auto h-full">
      {nodes.map((node) => (
        <TreeNode
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
