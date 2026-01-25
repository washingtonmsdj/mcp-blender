// AI Context Manager
import { vfs } from "@/lib/vfs/VirtualFileSystem";
import type { OrdaxSpec } from "@/lib/ordax/types";
import type { ChatMsg } from "./ai-streaming";

export type ProjectContext = {
  spec?: OrdaxSpec;
  files: { path: string; content: string }[];
  chatHistory: ChatMsg[];
  metadata: {
    gameType?: string;
    systems: string[];
    entities: string[];
    lastModified: Date;
  };
};

export class ContextManager {
  private context: ProjectContext;
  private maxHistoryLength: number = 20;
  private maxFileSize: number = 5000; // chars

  constructor() {
    this.context = {
      files: [],
      chatHistory: [],
      metadata: {
        systems: [],
        entities: [],
        lastModified: new Date(),
      },
    };
  }

  // Update spec
  updateSpec(spec: OrdaxSpec) {
    this.context.spec = spec;
    this.context.metadata.gameType = spec.gameType;
    this.context.metadata.systems = spec.systems || [];
    this.context.metadata.entities = spec.scene?.entities?.map((e) => e.id) || [];
    this.context.metadata.lastModified = new Date();
  }

  // Add chat message
  addMessage(message: ChatMsg) {
    this.context.chatHistory.push(message);

    // Keep only recent messages
    if (this.context.chatHistory.length > this.maxHistoryLength) {
      this.context.chatHistory = this.context.chatHistory.slice(-this.maxHistoryLength);
    }
  }

  // Sync files from VFS
  syncFiles() {
    const allFiles = vfs.getAllFiles();
    
    this.context.files = allFiles
      .filter((file) => {
        // Only include relevant files
        return (
          file.language === "typescript" ||
          file.language === "json"
        );
      })
      .map((file) => ({
        path: file.path,
        content: this.truncateContent(file.content),
      }));
  }

  // Get context for AI
  getAIContext(): {
    spec?: OrdaxSpec;
    files: { path: string; content: string }[];
    recentMessages: ChatMsg[];
    summary: string;
  } {
    this.syncFiles();

    return {
      spec: this.context.spec,
      files: this.context.files,
      recentMessages: this.context.chatHistory.slice(-10),
      summary: this.generateSummary(),
    };
  }

  // Generate context summary
  private generateSummary(): string {
    const parts: string[] = [];

    if (this.context.spec) {
      parts.push(`Game Type: ${this.context.spec.gameType}`);
      parts.push(`Title: ${this.context.spec.title}`);
    }

    if (this.context.metadata.systems.length > 0) {
      parts.push(`Systems: ${this.context.metadata.systems.join(", ")}`);
    }

    if (this.context.metadata.entities.length > 0) {
      parts.push(`Entities: ${this.context.metadata.entities.join(", ")}`);
    }

    parts.push(`Files: ${this.context.files.length}`);
    parts.push(`Last Modified: ${this.context.metadata.lastModified.toLocaleString()}`);

    return parts.join(" | ");
  }

  // Truncate content to fit context window
  private truncateContent(content: string): string {
    if (content.length <= this.maxFileSize) {
      return content;
    }

    // Keep beginning and end
    const half = Math.floor(this.maxFileSize / 2);
    return (
      content.slice(0, half) +
      "\n\n// ... (truncated) ...\n\n" +
      content.slice(-half)
    );
  }

  // Get relevant files for query
  getRelevantFiles(query: string): { path: string; content: string }[] {
    const keywords = query.toLowerCase().split(" ");
    
    return this.context.files
      .filter((file) => {
        const content = file.content.toLowerCase();
        const path = file.path.toLowerCase();
        
        return keywords.some((keyword) => 
          content.includes(keyword) || path.includes(keyword)
        );
      })
      .slice(0, 5); // Max 5 relevant files
  }

  // Export context
  export(): ProjectContext {
    return { ...this.context };
  }

  // Import context
  import(context: ProjectContext) {
    this.context = context;
  }

  // Clear context
  clear() {
    this.context = {
      files: [],
      chatHistory: [],
      metadata: {
        systems: [],
        entities: [],
        lastModified: new Date(),
      },
    };
  }

  // Get statistics
  getStats() {
    return {
      totalFiles: this.context.files.length,
      totalMessages: this.context.chatHistory.length,
      systems: this.context.metadata.systems.length,
      entities: this.context.metadata.entities.length,
      contextSize: JSON.stringify(this.context).length,
    };
  }
}

// Singleton instance
export const contextManager = new ContextManager();
