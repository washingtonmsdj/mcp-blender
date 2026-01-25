import type { CodeGameModule } from "./types";

/** Helper to keep a canonical export shape for games. */
export function defineGame(module: CodeGameModule): CodeGameModule {
  return module;
}
