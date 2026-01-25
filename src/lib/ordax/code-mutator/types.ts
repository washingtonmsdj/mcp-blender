export const CODE_SEMANTIC_PATCH_VERSION = "1" as const;

export type CodeSemanticPatchOp =
  | {
      op: "create_file";
      path: string;
      content: string;
    }
  | {
      op: "update_file";
      path: string;
      content: string;
    }
  | {
      op: "rename_file";
      from: string;
      to: string;
    }
  | {
      op: "delete_file";
      path: string;
    };

export type CodeSemanticPatch = {
  kind: "CODE_SEMANTIC_PATCH";
  version: typeof CODE_SEMANTIC_PATCH_VERSION;
  /** Target gameId (kebab-case) */
  gameId: string;
  /** All paths MUST be rooted at /vfs/games/<gameId>/ */
  ops: CodeSemanticPatchOp[];
};

export type ApplyPatchResult =
  | {
      ok: true;
      appliedOps: CodeSemanticPatchOp[];
      warnings: string[];
    }
  | {
      ok: false;
      appliedOps: CodeSemanticPatchOp[];
      errors: string[];
      warnings: string[];
    };
