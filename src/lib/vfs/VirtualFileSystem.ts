import type { VirtualFile, VirtualFolder, VirtualNode, VirtualFileSystem, FileSystemEvent } from "./types";

export class VFS {
  private fs: VirtualFileSystem;
  private listeners: ((event: FileSystemEvent) => void)[] = [];

  constructor() {
    const rootId = this.generateId();
    const root: VirtualFolder = {
      id: rootId,
      name: "root",
      type: "folder",
      path: "/",
      parentId: null,
      children: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.fs = {
      nodes: new Map([[rootId, root]]),
      root: rootId,
    };

    this.initializeDefaultStructure();
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private initializeDefaultStructure() {
    // Create default folders
    this.createFolder("src", "/");
    this.createFolder("assets", "/");
    this.createFolder("scenes", "/");
    this.createFolder("scripts", "/");
    this.createFolder("config", "/");

    // Create default files
    this.createFile("main.ts", "/src", "typescript", `// Main entry point
import { Game } from './game';

const game = new Game();
game.start();
`);

    this.createFile("game.ts", "/src", "typescript", `// Game class
export class Game {
  start() {
    console.log('Game started!');
  }
}
`);

    this.createFile("ordax.json", "/config", "json", JSON.stringify({
      name: "My Game",
      version: "1.0.0",
      engine: "Ordax 1.0"
    }, null, 2));
  }

  // Create operations
  createFolder(name: string, parentPath: string): VirtualFolder | null {
    const parent = this.getNodeByPath(parentPath);
    if (!parent || parent.type !== "folder") return null;

    const id = this.generateId();
    const path = parentPath === "/" ? `/${name}` : `${parentPath}/${name}`;

    const folder: VirtualFolder = {
      id,
      name,
      type: "folder",
      path,
      parentId: parent.id,
      children: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.fs.nodes.set(id, folder);
    parent.children.push(id);
    this.emit({ type: "create", nodeId: id, timestamp: new Date() });

    return folder;
  }

  createFile(
    name: string,
    parentPath: string,
    language: VirtualFile["language"],
    content: string = ""
  ): VirtualFile | null {
    const parent = this.getNodeByPath(parentPath);
    if (!parent || parent.type !== "folder") return null;

    const id = this.generateId();
    const path = parentPath === "/" ? `/${name}` : `${parentPath}/${name}`;

    const file: VirtualFile = {
      id,
      name,
      type: "file",
      content,
      language,
      path,
      parentId: parent.id,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.fs.nodes.set(id, file);
    parent.children.push(id);
    this.emit({ type: "create", nodeId: id, timestamp: new Date() });

    return file;
  }

  // Read operations
  getNodeById(id: string): VirtualNode | undefined {
    return this.fs.nodes.get(id);
  }

  getNodeByPath(path: string): VirtualNode | undefined {
    if (path === "/") {
      return this.fs.nodes.get(this.fs.root);
    }

    const parts = path.split("/").filter(Boolean);
    let current = this.fs.nodes.get(this.fs.root);

    for (const part of parts) {
      if (!current || current.type !== "folder") return undefined;
      
      const childId = current.children.find((id) => {
        const node = this.fs.nodes.get(id);
        return node?.name === part;
      });

      if (!childId) return undefined;
      current = this.fs.nodes.get(childId);
    }

    return current;
  }

  getChildren(nodeId: string): VirtualNode[] {
    const node = this.fs.nodes.get(nodeId);
    if (!node || node.type !== "folder") return [];

    return node.children
      .map((id) => this.fs.nodes.get(id))
      .filter((n): n is VirtualNode => n !== undefined);
  }

  getAllFiles(): VirtualFile[] {
    const files: VirtualFile[] = [];
    for (const node of this.fs.nodes.values()) {
      if (node.type === "file") {
        files.push(node);
      }
    }
    return files;
  }

  // Update operations
  updateFileContent(id: string, content: string): boolean {
    const node = this.fs.nodes.get(id);
    if (!node || node.type !== "file") return false;

    node.content = content;
    node.updatedAt = new Date();
    this.emit({ type: "update", nodeId: id, timestamp: new Date() });

    return true;
  }

  renameNode(id: string, newName: string): boolean {
    const node = this.fs.nodes.get(id);
    if (!node) return false;

    const oldPath = node.path;
    node.name = newName;
    
    // Update path
    const pathParts = oldPath.split("/");
    pathParts[pathParts.length - 1] = newName;
    node.path = pathParts.join("/");
    node.updatedAt = new Date();

    // Update children paths if folder
    if (node.type === "folder") {
      this.updateChildrenPaths(node);
    }

    this.emit({ type: "rename", nodeId: id, timestamp: new Date() });
    return true;
  }

  private updateChildrenPaths(folder: VirtualFolder) {
    for (const childId of folder.children) {
      const child = this.fs.nodes.get(childId);
      if (!child) continue;

      child.path = `${folder.path}/${child.name}`;
      if (child.type === "folder") {
        this.updateChildrenPaths(child);
      }
    }
  }

  // Delete operations
  deleteNode(id: string): boolean {
    const node = this.fs.nodes.get(id);
    if (!node || !node.parentId) return false;

    const parent = this.fs.nodes.get(node.parentId);
    if (!parent || parent.type !== "folder") return false;

    // Remove from parent's children
    parent.children = parent.children.filter((cid) => cid !== id);

    // Delete node and all children if folder
    if (node.type === "folder") {
      this.deleteFolder(node);
    } else {
      this.fs.nodes.delete(id);
    }

    this.emit({ type: "delete", nodeId: id, timestamp: new Date() });
    return true;
  }

  private deleteFolder(folder: VirtualFolder) {
    for (const childId of folder.children) {
      const child = this.fs.nodes.get(childId);
      if (!child) continue;

      if (child.type === "folder") {
        this.deleteFolder(child);
      } else {
        this.fs.nodes.delete(childId);
      }
    }
    this.fs.nodes.delete(folder.id);
  }

  // Event system
  on(listener: (event: FileSystemEvent) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private emit(event: FileSystemEvent) {
    this.listeners.forEach((listener) => listener(event));
  }

  // Export/Import
  export(): string {
    const data = {
      root: this.fs.root,
      nodes: Array.from(this.fs.nodes.entries()),
    };
    return JSON.stringify(data);
  }

  import(data: string): boolean {
    try {
      const parsed = JSON.parse(data);
      this.fs = {
        root: parsed.root,
        nodes: new Map(parsed.nodes),
      };
      return true;
    } catch {
      return false;
    }
  }

  // Get tree structure for UI
  getTree(): any {
    const root = this.fs.nodes.get(this.fs.root);
    if (!root) return null;

    const buildTree = (node: VirtualNode): any => {
      if (node.type === "file") {
        return {
          id: node.id,
          name: node.name,
          type: "file",
          path: node.path,
          language: node.language,
        };
      }

      return {
        id: node.id,
        name: node.name,
        type: "folder",
        path: node.path,
        children: node.children
          .map((id) => this.fs.nodes.get(id))
          .filter((n): n is VirtualNode => n !== undefined)
          .map(buildTree),
      };
    };

    return buildTree(root);
  }
}

// Singleton instance
export const vfs = new VFS();
