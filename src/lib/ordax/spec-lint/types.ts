export type SpecIssueSeverity = "error" | "warn";

export type OrdaxSpecIssue = {
  code:
    | "MISSING_GAME_TYPE"
    | "MISSING_TITLE"
    | "MISSING_ENTITIES"
    | "DUPLICATE_ENTITY_IDS"
    | "INVALID_SYSTEMS"
    | "ENTITY_OUT_OF_BOUNDS"
    | "THEME_NOT_HSL";
  severity: SpecIssueSeverity;
  message: string;
  details?: string;
};

export type OrdaxSpecFix = {
  code:
    | "ADD_PLAYER"
    | "RENAME_DUPLICATE_IDS"
    | "FILTER_OR_MAP_SYSTEMS"
    | "CLAMP_ENTITIES_TO_WORLD"
    | "FILL_DEFAULTS";
  message: string;
  details?: string;
};
