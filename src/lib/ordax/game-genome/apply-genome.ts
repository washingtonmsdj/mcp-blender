/**
 * Aplica um genoma a um RuntimeSpec
 * Usa Remix Engine internamente
 */

import type { RuntimeSpec } from '../types';
import type { GameGenome } from './index';
import { composePatches } from '../remix-engine/compose-patches';
import { applyRemixPatch } from '../remix-engine/apply-remix-patch';
import type { ParsedIntent } from '../remix-engine/parse-remix-intent';

export function applyGenome(
  baseSpec: RuntimeSpec,
  genome: GameGenome
): RuntimeSpec {
  // Converter genoma para ParsedIntent
  const intent: ParsedIntent = {
    themes: genome.themes.filter(t => t !== 'default'),
    difficulty: genome.difficulty,
    speed: genome.speed,
    boss: genome.boss,
    conflicts: [],
    raw: formatGenomeAsIntent(genome)
  };
  
  // Usar Remix Engine para gerar patch
  const { patch } = composePatches(baseSpec, intent);
  
  // Aplicar patch
  const remixed = applyRemixPatch(baseSpec, patch);
  
  // Aplicar progressão
  if (!remixed.rules) remixed.rules = {};
  remixed.rules.winCondition = {
    type: genome.progression.winCondition,
    target: genome.progression.winTarget
  };
  remixed.rules.loseCondition = {
    type: genome.progression.loseCondition,
    target: genome.progression.loseTarget
  };
  
  // Aplicar UI
  if (!remixed.ui) remixed.ui = {};
  if (!remixed.ui.hud) remixed.ui.hud = {};
  
  genome.ui.hud.forEach(element => {
    remixed.ui!.hud![element] = true;
  });
  
  return remixed;
}

function formatGenomeAsIntent(genome: GameGenome): string {
  const parts: string[] = [];
  
  if (genome.themes.length > 0 && !genome.themes.includes('default')) {
    parts.push(genome.themes.join(' + '));
  }
  
  if (genome.difficulty !== 'normal') {
    parts.push(genome.difficulty);
  }
  
  if (genome.speed !== 'normal') {
    parts.push(genome.speed);
  }
  
  if (genome.boss) {
    parts.push('boss');
  }
  
  return parts.join(' ');
}
