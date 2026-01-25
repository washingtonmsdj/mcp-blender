/**
 * FASE 7: CANONICAL GAME PRESETS
 * 
 * Presets canônicos que sempre geram jogos jogáveis perfeitos.
 * Cada preset:
 * - Passa no validator
 * - Passa no autofill
 * - Gera resumo humano claro
 * - Roda perfeitamente sem chat adicional
 */

import type { RuntimeSpec } from '../types';

export { createSpaceSurvivalPreset } from './space-survival';
export { createZombieArenaPreset } from './zombie-arena';
export { createDungeonShooterPreset } from './dungeon-shooter';

export interface CanonicalPreset {
  id: string;
  name: string;
  description: string;
  emoji: string;
  runtimeSpec: RuntimeSpec;
}

export const CANONICAL_PRESETS = [
  'space-survival',
  'zombie-arena',
  'dungeon-shooter'
] as const;

export type CanonicalPresetId = typeof CANONICAL_PRESETS[number];
