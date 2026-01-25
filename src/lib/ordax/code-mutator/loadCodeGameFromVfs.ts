import type { VFS } from "@/lib/vfs/VirtualFileSystem";
import type { CodeGameModule } from "@/games/_template";

type AnyModule = Record<string, unknown>;

function normalizePath(input: string): string {
  const trimmed = (input ?? "").trim();
  if (!trimmed.startsWith("/")) return `/${trimmed}`;
  return trimmed;
}

function dirname(path: string): string {
  const p = normalizePath(path);
  const idx = p.lastIndexOf("/");
  return idx <= 0 ? "/" : p.slice(0, idx);
}

function resolveImport(fromPath: string, spec: string): string {
  if (spec.startsWith("/")) return spec;
  const base = dirname(fromPath);
  const joined = base === "/" ? `/${spec}` : `${base}/${spec}`;
  const parts = joined.split("/");
  const out: string[] = [];
  for (const part of parts) {
    if (!part || part === ".") continue;
    if (part === "..") out.pop();
    else out.push(part);
  }
  return `/${out.join("/")}`;
}

function findCodeGameExport(mod: AnyModule): CodeGameModule | null {
  for (const v of Object.values(mod)) {
    const maybe = v as any;
    if (
      maybe &&
      typeof maybe === "object" &&
      typeof maybe.setup === "function" &&
      maybe.meta &&
      typeof maybe.meta === "object" &&
      typeof maybe.meta.id === "string"
    ) {
      return maybe as CodeGameModule;
    }
  }
  return null;
}

/**
 * Loads a code-first game module from the in-memory VFS.
 *
 * This loader is intentionally narrow:
 * - Only supports relative imports between VFS files
 * - Allows importing the canonical template via "@/games/_template"
 * - Blocks other "@/" imports (keeps isolation)
 *
 * Note: this is used to run the EXTRACT pass (setup({mode:"extract"}))
 * so it should remain pure.
 */
export async function loadCodeGameFromVfs(vfs: VFS, entryPath: string): Promise<CodeGameModule> {
  const memo = new Map<string, string>(); // vfsPath -> blobUrl

  const readFileOrThrow = (path: string) => {
    const node = vfs.getNodeByPath(path);
    if (!node || node.type !== "file") throw new Error(`VFS file not found: ${path}`);
    return node.content;
  };

  const createModuleUrl = (path: string): string => {
    const absPath = normalizePath(path);
    const existing = memo.get(absPath);
    if (existing) return existing;

    let source = readFileOrThrow(absPath);

    // Rewrite allowed alias import(s)
    source = source.replace(
      /from\s+["']@\/games\/_template(?:\/index\.ts)?["']/g,
      'from "/src/games/_template/index.ts"'
    );

    // Block other @/ imports
    const illegalAlias = source.match(/from\s+["']@\/(?!games\/_template)/);
    if (illegalAlias) {
      throw new Error(`Import não permitido em VFS module: apenas @/games/_template é permitido. File=${absPath}`);
    }

    // Rewrite relative imports to blob urls
    source = source.replace(/from\s+["'](\.{1,2}\/[^"']+)["']/g, (_m, rel) => {
      const resolved = resolveImport(absPath, rel);
      const withExtCandidates = [resolved, `${resolved}.ts`, `${resolved}.tsx`, `${resolved}/index.ts`, `${resolved}/index.tsx`];
      const target = withExtCandidates.find((p) => {
        const n = vfs.getNodeByPath(p);
        return !!n && n.type === "file";
      });
      if (!target) throw new Error(`Import relativo não resolvido: ${rel} em ${absPath}`);
      const url = createModuleUrl(target);
      return `from "${url}"`;
    });

    const blob = new Blob([source], { type: "text/javascript" });
    const url = URL.createObjectURL(blob);
    memo.set(absPath, url);
    return url;
  };

  const url = createModuleUrl(entryPath);
  const mod = (await import(/* @vite-ignore */ url)) as AnyModule;
  const game = findCodeGameExport(mod);
  if (!game) {
    throw new Error(`Nenhum export CodeGameModule encontrado em: ${entryPath}`);
  }
  return game;
}
