// Virtual File System Types

export type FileType = "file" | "folder";

export type VirtualFile = {
  id: string;
  name: string;
  type: "file";
  content: string;
  language: "typescript" | "json" | "css" | "html";
  path: string;
  parentId: string | null;
  createdAt: Date;
  updatedAt: Date;
};

export type VirtualFolder = {
  id: string;
  name: string;
  type: "folder";
  path: string;
  parentId: string | null;
  children: string[]; // IDs of children
  createdAt: Date;
  updatedAt: Date;
};

export type VirtualNode = VirtualFile | VirtualFolder;

export type VirtualFileSystem = {
  nodes: Map<string, VirtualNode>;
  root: string; // ID of root folder
};

export type FileSystemEvent = {
  type: "create" | "update" | "delete" | "rename";
  nodeId: string;
  timestamp: Date;
};
