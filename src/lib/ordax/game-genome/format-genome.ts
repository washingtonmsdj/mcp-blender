/**
 * Formata um genoma para exibição humana
 */

import type { GameGenome } from './index';
import type { GenomeDiff } from './compare-genomes';

export function formatGenome(genome: GameGenome): string {
  const lines: string[] = [];
  
  lines.push(`🧬 Game Genome`);
  lines.push(`Genre: ${genome.genre}`);
  
  if (genome.themes.length > 0) {
    lines.push(`Themes: ${genome.themes.join(', ')}`);
  }
  
  lines.push(`Difficulty: ${genome.difficulty}`);
  lines.push(`Speed: ${genome.speed}`);
  lines.push(`Boss: ${genome.boss ? 'Yes' : 'No'}`);
  
  lines.push(`\nProgression:`);
  lines.push(`  Win: ${genome.progression.winCondition}${genome.progression.winTarget ? ` (${genome.progression.winTarget})` : ''}`);
  lines.push(`  Lose: ${genome.progression.loseCondition}${genome.progression.loseTarget ? ` (${genome.progression.loseTarget})` : ''}`);
  
  if (genome.enemyTypes.length > 0) {
    lines.push(`\nEnemy Types:`);
    genome.enemyTypes.forEach(type => {
      lines.push(`  ${type.archetype} (${type.behavior}): ${type.count}x`);
    });
  }
  
  if (genome.mechanics.length > 0) {
    lines.push(`\nMechanics: ${genome.mechanics.join(', ')}`);
  }
  
  if (genome.ui.hud.length > 0) {
    lines.push(`\nHUD: ${genome.ui.hud.join(', ')}`);
  }
  
  return lines.join('\n');
}

export function formatGenomeDiff(diff: GenomeDiff): string {
  const lines: string[] = [];
  
  lines.push(`📊 Genome Differences`);
  
  if (diff.genre) {
    lines.push(`Genre: ${diff.genre.from} → ${diff.genre.to}`);
  }
  
  if (diff.themes.added.length > 0) {
    lines.push(`Themes Added: ${diff.themes.added.join(', ')}`);
  }
  if (diff.themes.removed.length > 0) {
    lines.push(`Themes Removed: ${diff.themes.removed.join(', ')}`);
  }
  
  if (diff.difficulty) {
    lines.push(`Difficulty: ${diff.difficulty.from} → ${diff.difficulty.to}`);
  }
  
  if (diff.speed) {
    lines.push(`Speed: ${diff.speed.from} → ${diff.speed.to}`);
  }
  
  if (diff.boss) {
    lines.push(`Boss: ${diff.boss.from ? 'Yes' : 'No'} → ${diff.boss.to ? 'Yes' : 'No'}`);
  }
  
  if (diff.progression.winCondition) {
    lines.push(`Win Condition: ${diff.progression.winCondition.from} → ${diff.progression.winCondition.to}`);
  }
  
  if (diff.enemyTypes.added.length > 0) {
    lines.push(`\nEnemy Types Added:`);
    diff.enemyTypes.added.forEach(type => {
      lines.push(`  + ${type.archetype} (${type.behavior}): ${type.count}x`);
    });
  }
  
  if (diff.enemyTypes.removed.length > 0) {
    lines.push(`\nEnemy Types Removed:`);
    diff.enemyTypes.removed.forEach(type => {
      lines.push(`  - ${type.archetype} (${type.behavior}): ${type.count}x`);
    });
  }
  
  if (diff.enemyTypes.modified.length > 0) {
    lines.push(`\nEnemy Types Modified:`);
    diff.enemyTypes.modified.forEach(mod => {
      const sign = mod.countDiff > 0 ? '+' : '';
      lines.push(`  ${mod.archetype}: ${sign}${mod.countDiff}`);
    });
  }
  
  if (diff.mechanics.added.length > 0) {
    lines.push(`\nMechanics Added: ${diff.mechanics.added.join(', ')}`);
  }
  if (diff.mechanics.removed.length > 0) {
    lines.push(`Mechanics Removed: ${diff.mechanics.removed.join(', ')}`);
  }
  
  if (diff.ui.hud.added.length > 0) {
    lines.push(`\nHUD Added: ${diff.ui.hud.added.join(', ')}`);
  }
  if (diff.ui.hud.removed.length > 0) {
    lines.push(`HUD Removed: ${diff.ui.hud.removed.join(', ')}`);
  }
  
  return lines.join('\n');
}

export function formatGenomeCompact(genome: GameGenome): string {
  const parts: string[] = [];
  
  if (genome.themes.length > 0 && !genome.themes.includes('default')) {
    parts.push(genome.themes.join('+'));
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
  
  parts.push(`${genome.enemyTypes.length}enemies`);
  parts.push(`${genome.mechanics.length}mechanics`);
  
  return parts.join('|');
}
