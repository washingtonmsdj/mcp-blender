import type { VFS } from "@/lib/vfs/VirtualFileSystem";
import type { VirtualFile } from "@/lib/vfs/types";
import type { ApplyPatchResult, CodeSemanticPatch, CodeSemanticPatchOp } from "./types";

import contractText from "@/games/_template/CONTRACT.md?raw";

const ALLOWED_EXTENSIONS = new Set([".ts", ".tsx", ".json"]);

const CANONICAL_ALLOWED_DIRS = new Set([
  // code-first canonical dirs (see TEMPLATE_MUTATION_GUIDE.md)
  "systems",
  "entities",
  "ui",
  "state",
  "input",
  "audio",
  "spawn",
  "utils",
  "_derived",
]);

const CANONICAL_ROOT_FILES = new Set([
  "codeGame.ts", // mandatory
]);

function normalizePath(input: string): string {
  const trimmed = (input ?? "").trim();
  if (!trimmed.startsWith("/")) return `/${trimmed}`;
  return trimmed;
}

function extname(path: string): string {
  const idx = path.lastIndexOf(".");
  return idx === -1 ? "" : path.slice(idx).toLowerCase();
}

function dirname(path: string): string {
  const p = normalizePath(path);
  const idx = p.lastIndexOf("/");
  return idx <= 0 ? "/" : p.slice(0, idx);
}

function basename(path: string): string {
  const p = normalizePath(path);
  const idx = p.lastIndexOf("/");
  return idx === -1 ? p : p.slice(idx + 1);
}

function isValidGameId(gameId: string) {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(gameId);
}

function ensureFolders(vfs: VFS, absDirPath: string) {
  const dirPath = normalizePath(absDirPath);
  if (dirPath === "/") return;
  const parts = dirPath.split("/").filter(Boolean);
  let current = "/";
  for (const part of parts) {
    const next = current === "/" ? `/${part}` : `${current}/${part}`;
    const node = vfs.getNodeByPath(next);
    if (!node) {
      const created = vfs.createFolder(part, current);
      if (!created) throw new Error(`Falha ao criar pasta: ${next}`);
    } else if (node.type !== "folder") {
      throw new Error(`Caminho esperado como pasta, mas é arquivo: ${next}`);
    }
    current = next;
  }
}

function languageFromPath(path: string): VirtualFile["language"] {
  const ext = extname(path);
  if (ext === ".json") return "json";
  // NOTE: VFS language union currently doesn't include "tsx"; keep as typescript.
  return "typescript";
}

function validateSinglePathOrThrow(path: string, gameId: string) {
  const p = normalizePath(path);
  const allowedPrefix = `/vfs/games/${gameId}/`;
  if (!p.startsWith(allowedPrefix)) {
    throw new Error(`Path fora do escopo permitido (esperado prefixo ${allowedPrefix}): ${p}`);
  }
  if (p.includes("..")) {
    throw new Error(`Path inválido (não pode conter '..'): ${p}`);
  }
  if (p.startsWith("/vfs/games/_template/")) {
    throw new Error(`Path protegido: ${p}`);
  }

  // Enforce canonical mutation map (never invent directories)
  const rel = p.slice(allowedPrefix.length);
  const seg = rel.split("/").filter(Boolean);
  if (seg.length === 0) {
    throw new Error(`Path inválido (aponta para raiz): ${p}`);
  }
  if (seg.length === 1) {
    if (!CANONICAL_ROOT_FILES.has(seg[0])) {
      throw new Error(
        `Arquivo na raiz não permitido pelo TEMPLATE_MUTATION_GUIDE: ${p} (permitidos: ${Array.from(CANONICAL_ROOT_FILES).join(", ")})`
      );
    }
  } else {
    if (!CANONICAL_ALLOWED_DIRS.has(seg[0])) {
      throw new Error(
        `Diretório não permitido pelo TEMPLATE_MUTATION_GUIDE: ${p} (permitidos: ${Array.from(CANONICAL_ALLOWED_DIRS).join(", ")})`
      );
    }
  }

  const ext = extname(p);
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    throw new Error(`Extensão não permitida (${ext || "(sem extensão)"}): ${p}`);
  }
}

function assertDoesNotDeleteMandatory(path: string, gameId: string) {
  const mandatory = new Set([`/vfs/games/${gameId}/codeGame.ts`]);
  if (mandatory.has(normalizePath(path))) {
    throw new Error(`Não é permitido deletar arquivo obrigatório: ${path}`);
  }
}

/**
 * Applies a CodeSemanticPatch to the in-memory VFS.
 *
 * Security model (aligned to src/games/_template/CONTRACT.md):
 * - ONLY /vfs/games/<gameId>/** may be mutated
 * - Protected paths (template) are always blocked
 * - Mandatory files cannot be deleted
 * - Only .ts/.tsx/.json are allowed
 */
export function applyCodeSemanticPatch(vfs: VFS, patch: CodeSemanticPatch): ApplyPatchResult {
  const appliedOps: CodeSemanticPatchOp[] = [];
  const warnings: string[] = [];
  const errors: string[] = [];

  try {
    if (!patch || patch.kind !== "CODE_SEMANTIC_PATCH") {
      return { ok: false, appliedOps, warnings, errors: ["Patch inválido: kind"] };
    }
    if (patch.version !== "1") {
      return { ok: false, appliedOps, warnings, errors: [`Patch inválido: version=${String(patch.version)}`] };
    }
    if (!isValidGameId(patch.gameId)) {
      return { ok: false, appliedOps, warnings, errors: [`gameId inválido: ${patch.gameId}`] };
    }
    if (!Array.isArray(patch.ops)) {
      return { ok: false, appliedOps, warnings, errors: ["Patch inválido: ops"] };
    }

    // Use contract text as an audit trail and to ensure we don't drift from doc.
    if (!contractText.includes("src/games/_template/")) {
      warnings.push("CONTRACT.md não encontrado via ?raw (ou formato inesperado). Mantendo validações hardcoded.");
    }

    // First pass: validate deterministically
    const requiresRegistration = new Set<string>();
    for (const op of patch.ops) {
      if (!op || typeof op !== "object" || typeof (op as any).op !== "string") {
        throw new Error("Op inválida (esperado objeto com campo 'op')");
      }

      switch (op.op) {
        case "create_file":
        case "update_file":
        case "delete_file": {
          validateSinglePathOrThrow((op as any).path, patch.gameId);

          // Light semantic requirement: if we touch canonical dirs, require codeGame.ts update in same patch.
          const p = normalizePath((op as any).path);
          const allowedPrefix = `/vfs/games/${patch.gameId}/`;
          const rel = p.slice(allowedPrefix.length);
          const seg = rel.split("/").filter(Boolean);
          if (seg.length >= 2) {
            const top = seg[0];
            if (["systems", "entities", "ui", "state", "input", "audio", "spawn"].includes(top)) {
              requiresRegistration.add(top);
            }
          }
          break;
        }
        case "rename_file": {
          validateSinglePathOrThrow((op as any).from, patch.gameId);
          validateSinglePathOrThrow((op as any).to, patch.gameId);
          // Deterministic and safe rename: same directory only.
          if (dirname((op as any).from) !== dirname((op as any).to)) {
            throw new Error(`rename_file só pode renomear dentro do mesmo diretório: ${(op as any).from} -> ${(op as any).to}`);
          }
          break;
        }
        default:
          throw new Error(`Op desconhecida: ${(op as any).op}`);
      }

      if (op.op === "delete_file") {
        assertDoesNotDeleteMandatory((op as any).path, patch.gameId);
      }
      if (op.op === "rename_file") {
        assertDoesNotDeleteMandatory((op as any).from, patch.gameId);
      }
    }

    // Enforce: if we touched canonical dirs, codeGame.ts must be updated in the same patch.
    if (requiresRegistration.size) {
      const codeGamePath = `/vfs/games/${patch.gameId}/codeGame.ts`;
      const hasCodeGameUpdate = patch.ops.some((op) => op.op === "update_file" && normalizePath((op as any).path) === codeGamePath);
      if (!hasCodeGameUpdate) {
        throw new Error(
          `Patch incompleto: alterou/criou arquivos em [${Array.from(requiresRegistration).join(", ")}] mas não inclui update_file em ${codeGamePath} (registro obrigatório).`
        );
      }
    }

    // Second pass: apply in the given order (deterministic)
    for (const op of patch.ops) {
      switch (op.op) {
        case "create_file": {
          const path = normalizePath(op.path);
          const existing = vfs.getNodeByPath(path);
          if (existing) throw new Error(`create_file: já existe: ${path}`);
          const parent = dirname(path);
          ensureFolders(vfs, parent);
          const fileName = basename(path);
          const created = vfs.createFile(fileName, parent, languageFromPath(path), op.content ?? "");
          if (!created) throw new Error(`create_file: falha ao criar: ${path}`);
          appliedOps.push(op);
          break;
        }
        case "update_file": {
          const path = normalizePath(op.path);
          const existing = vfs.getNodeByPath(path);
          if (!existing || existing.type !== "file") throw new Error(`update_file: arquivo não encontrado: ${path}`);
          const ok = vfs.updateFileContent(existing.id, op.content ?? "");
          if (!ok) throw new Error(`update_file: falha ao atualizar: ${path}`);
          appliedOps.push(op);
          break;
        }
        case "rename_file": {
          const from = normalizePath(op.from);
          const to = normalizePath(op.to);
          const node = vfs.getNodeByPath(from);
          if (!node || node.type !== "file") throw new Error(`rename_file: arquivo não encontrado: ${from}`);
          const destExists = vfs.getNodeByPath(to);
          if (destExists) throw new Error(`rename_file: destino já existe: ${to}`);
          const ok = vfs.renameNode(node.id, basename(to));
          if (!ok) throw new Error(`rename_file: falha ao renomear: ${from} -> ${to}`);
          appliedOps.push(op);
          break;
        }
        case "delete_file": {
          const path = normalizePath(op.path);
          const node = vfs.getNodeByPath(path);
          if (!node) throw new Error(`delete_file: arquivo não encontrado: ${path}`);
          if (node.type !== "file") throw new Error(`delete_file: só suporta arquivos: ${path}`);
          const ok = vfs.deleteNode(node.id);
          if (!ok) throw new Error(`delete_file: falha ao deletar: ${path}`);
          appliedOps.push(op);
          break;
        }
      }
    }

    return { ok: true, appliedOps, warnings };
  } catch (e) {
    errors.push(e instanceof Error ? e.message : String(e));
    return { ok: false, appliedOps, errors, warnings };
  }
}
