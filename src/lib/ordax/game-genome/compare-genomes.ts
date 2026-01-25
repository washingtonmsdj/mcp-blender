/**
 * Compara dois genomas e retorna as diferenças
 */

import type { GameGenome } from './index';

export interface GenomeDiff {
  genre: { from: string; to: string } | null;
  themes: { added: string[]; removed: string[] };
  difficulty: { from: string; to: string } | null;
  speed: { from: string; to: string } | null;
  boss: { from: boolean; to: boolean } | null;
  progression: {
    winCondition: { from: string; to: string } | null;
    winTarget: { from: number | undefined; to: number | undefined } | null;
    loseCondition: { from: string; to: string } | null;
    loseTarget: { from: number | undefined; to: number | undefined } | null;
  };
  enemyTypes: {
    added: GameGenome['enemyTypes'];
    removed: GameGenome['enemyTypes'];
    modified: Array<{
      archetype: string;
      countDiff: number;
    }>;
  };
  mechanics: { added: string[]; removed: string[] };
  ui: {
    hud: { added: string[]; removed: string[] };
    screens: { added: string[]; removed: string[] };
  };
}

export function compareGenomes(from: GameGenome, to: GameGenome): GenomeDiff {
  const diff: GenomeDiff = {
    genre: from.genre !== to.genre ? { from: from.genre, to: to.genre } : null,
    themes: {
      added: to.themes.filter(t => !from.themes.includes(t)),
      removed: from.themes.filter(t => !to.themes.includes(t))
    },
    difficulty: from.difficulty !== to.difficulty ? { from: from.difficulty, to: to.difficulty } : null,
    speed: from.speed !== to.speed ? { from: from.speed, to: to.speed } : null,
    boss: from.boss !== to.boss ? { from: from.boss, to: to.boss } : null,
    progression: {
      winCondition: from.progression.winCondition !== to.progression.winCondition
        ? { from: from.progression.winCondition, to: to.progression.winCondition }
        : null,
      winTarget: from.progression.winTarget !== to.progression.winTarget
        ? { from: from.progression.winTarget, to: to.progression.winTarget }
        : null,
      loseCondition: from.progression.loseCondition !== to.progression.loseCondition
        ? { from: from.progression.loseCondition, to: to.progression.loseCondition }
        : null,
      loseTarget: from.progression.loseTarget !== to.progression.loseTarget
        ? { from: from.progression.loseTarget, to: to.progression.loseTarget }
        : null
    },
    enemyTypes: compareEnemyTypes(from.enemyTypes, to.enemyTypes),
    mechanics: {
      added: to.mechanics.filter(m => !from.mechanics.includes(m)),
      removed: from.mechanics.filter(m => !to.mechanics.includes(m))
    },
    ui: {
      hud: {
        added: to.ui.hud.filter(h => !from.ui.hud.includes(h)),
        removed: from.ui.hud.filter(h => !to.ui.hud.includes(h))
      },
      screens: {
        added: to.ui.screens.filter(s => !from.ui.screens.includes(s)),
        removed: from.ui.screens.filter(s => !to.ui.screens.includes(s))
      }
    }
  };
  
  return diff;
}

function compareEnemyTypes(
  from: GameGenome['enemyTypes'],
  to: GameGenome['enemyTypes']
): GenomeDiff['enemyTypes'] {
  const added: GameGenome['enemyTypes'] = [];
  const removed: GameGenome['enemyTypes'] = [];
  const modified: Array<{ archetype: string; countDiff: number }> = [];
  
  // Find added
  to.forEach(toType => {
    const fromType = from.find(f => 
      f.archetype === toType.archetype && f.behavior === toType.behavior
    );
    if (!fromType) {
      added.push(toType);
    } else if (fromType.count !== toType.count) {
      modified.push({
        archetype: toType.archetype,
        countDiff: toType.count - fromType.count
      });
    }
  });
  
  // Find removed
  from.forEach(fromType => {
    const toType = to.find(t => 
      t.archetype === fromType.archetype && t.behavior === fromType.behavior
    );
    if (!toType) {
      removed.push(fromType);
    }
  });
  
  return { added, removed, modified };
}

export function hasDifferences(diff: GenomeDiff): boolean {
  return !!(
    diff.genre ||
    diff.themes.added.length > 0 ||
    diff.themes.removed.length > 0 ||
    diff.difficulty ||
    diff.speed ||
    diff.boss ||
    diff.progression.winCondition ||
    diff.progression.winTarget ||
    diff.progression.loseCondition ||
    diff.progression.loseTarget ||
    diff.enemyTypes.added.length > 0 ||
    diff.enemyTypes.removed.length > 0 ||
    diff.enemyTypes.modified.length > 0 ||
    diff.mechanics.added.length > 0 ||
    diff.mechanics.removed.length > 0 ||
    diff.ui.hud.added.length > 0 ||
    diff.ui.hud.removed.length > 0 ||
    diff.ui.screens.added.length > 0 ||
    diff.ui.screens.removed.length > 0
  );
}
