/**
 * Extrai o genoma de um RuntimeSpec
 * Totalmente determinístico, sem heurísticas frágeis
 */

import type { RuntimeSpec } from '../types';
import type { GameGenome } from './index';

export function extractGenome(runtimeSpec: RuntimeSpec): GameGenome {
  const genome: GameGenome = {
    genre: extractGenre(runtimeSpec),
    themes: extractThemes(runtimeSpec),
    difficulty: extractDifficulty(runtimeSpec),
    speed: extractSpeed(runtimeSpec),
    boss: extractBoss(runtimeSpec),
    progression: extractProgression(runtimeSpec),
    enemyTypes: extractEnemyTypes(runtimeSpec),
    mechanics: extractMechanics(runtimeSpec),
    ui: extractUI(runtimeSpec),
    version: '1.0.0',
    timestamp: Date.now()
  };
  
  return genome;
}

function extractGenre(spec: RuntimeSpec): string {
  return spec.profile || 'topdown-shooter';
}

function extractThemes(spec: RuntimeSpec): string[] {
  const themes: string[] = [];
  
  // Detectar temas por sprites
  const sprites = Object.values(spec.entities || {})
    .map((e: any) => e.sprite)
    .filter(Boolean);
  
  const themeMap: Record<string, string[]> = {
    zombie: ['🧟', '🧟‍♂️', '🧟‍♀️'],
    space: ['🚀', '☄️', '🛸', '👽'],
    medieval: ['🗡️', '👺', '💀', '🏰', '🐉'],
    ninja: ['🥷', '👹', '⚔️'],
    pirate: ['🏴‍☠️', '🦜', '⚓'],
    robot: ['🤖', '👾', '🔧']
  };
  
  for (const [theme, emojis] of Object.entries(themeMap)) {
    if (sprites.some(s => emojis.includes(s))) {
      themes.push(theme);
    }
  }
  
  return themes.length > 0 ? themes : ['default'];
}

function extractDifficulty(spec: RuntimeSpec): 'easy' | 'normal' | 'hard' {
  // Analisar stats de inimigos
  const enemies = Object.values(spec.entities || {})
    .filter((e: any) => e.damage || e.aiType);
  
  if (enemies.length === 0) return 'normal';
  
  const avgHealth = enemies.reduce((sum: number, e: any) => sum + (e.health || 50), 0) / enemies.length;
  const avgDamage = enemies.reduce((sum: number, e: any) => sum + (e.damage || 10), 0) / enemies.length;
  
  // Thresholds baseados em valores padrão
  if (avgHealth < 40 && avgDamage < 12) return 'easy';
  if (avgHealth > 70 && avgDamage > 15) return 'hard';
  return 'normal';
}

function extractSpeed(spec: RuntimeSpec): 'slower' | 'normal' | 'faster' {
  // Analisar velocidades
  const entities = Object.values(spec.entities || {});
  if (entities.length === 0) return 'normal';
  
  const avgSpeed = entities.reduce((sum: number, e: any) => sum + (e.speed || 100), 0) / entities.length;
  
  // Thresholds baseados em valores padrão
  if (avgSpeed < 90) return 'slower';
  if (avgSpeed > 150) return 'faster';
  return 'normal';
}

function extractBoss(spec: RuntimeSpec): boolean {
  // Verificar se existe entidade boss
  return Object.values(spec.entities || {}).some((e: any) => 
    e.aiType === 'boss' || 
    e.sprite === '👑' ||
    (e.health && e.health > 300)
  );
}

function extractProgression(spec: RuntimeSpec): GameGenome['progression'] {
  const rules = spec.rules || {};
  
  const progression: GameGenome['progression'] = {
    winCondition: 'score',
    loseCondition: 'health'
  };
  
  // Win condition
  if (rules.winCondition) {
    progression.winCondition = rules.winCondition.type || 'score';
    progression.winTarget = rules.winCondition.target;
  }
  
  // Lose condition
  if (rules.loseCondition) {
    progression.loseCondition = rules.loseCondition.type || 'health';
    progression.loseTarget = rules.loseCondition.target;
  }
  
  return progression;
}

function extractEnemyTypes(spec: RuntimeSpec): GameGenome['enemyTypes'] {
  const enemies = Object.entries(spec.entities || {})
    .filter(([_, e]: [string, any]) => e.damage || e.aiType)
    .map(([key, e]: [string, any]) => ({
      key,
      health: e.health || 50,
      damage: e.damage || 10,
      speed: e.speed || 100,
      behavior: e.aiType || 'chase'
    }));
  
  const types: GameGenome['enemyTypes'] = [];
  
  // Classificar por arquétipo
  enemies.forEach(enemy => {
    let archetype: 'basic' | 'fast' | 'tank' | 'ranged' | 'boss' = 'basic';
    
    if (enemy.behavior === 'boss' || enemy.health > 300) {
      archetype = 'boss';
    } else if (enemy.speed > 120) {
      archetype = 'fast';
    } else if (enemy.health > 80) {
      archetype = 'tank';
    } else if (enemy.behavior === 'ranged') {
      archetype = 'ranged';
    }
    
    // Agrupar por arquétipo
    const existing = types.find(t => t.archetype === archetype && t.behavior === enemy.behavior);
    if (existing) {
      existing.count++;
    } else {
      types.push({
        archetype,
        count: 1,
        behavior: enemy.behavior as any
      });
    }
  });
  
  return types;
}

function extractMechanics(spec: RuntimeSpec): string[] {
  const mechanics: string[] = [];
  
  // Detectar mecânicas por entidades e propriedades
  const entities = Object.values(spec.entities || {});
  
  // Shooting
  if (entities.some((e: any) => e.weapon)) {
    mechanics.push('shooting');
  }
  
  // Collection
  if (entities.some((e: any) => e.scoreValue || e.healAmount)) {
    mechanics.push('collection');
  }
  
  // Movement
  if (entities.some((e: any) => e.speed)) {
    mechanics.push('movement');
  }
  
  // Combat
  if (entities.some((e: any) => e.damage)) {
    mechanics.push('combat');
  }
  
  // Spawning
  if (spec.spawners && Object.keys(spec.spawners).length > 0) {
    mechanics.push('spawning');
  }
  
  // Health
  if (entities.some((e: any) => e.health)) {
    mechanics.push('health');
  }
  
  // Score
  if (spec.rules?.winCondition?.type === 'score') {
    mechanics.push('score');
  }
  
  return mechanics;
}

function extractUI(spec: RuntimeSpec): GameGenome['ui'] {
  const ui: GameGenome['ui'] = {
    hud: [],
    screens: []
  };
  
  // HUD elements
  if (spec.ui?.hud) {
    const hud = spec.ui.hud;
    if (hud.health) ui.hud.push('health');
    if (hud.score) ui.hud.push('score');
    if (hud.timer) ui.hud.push('timer');
    if (hud.ammo) ui.hud.push('ammo');
    if (hud.wave) ui.hud.push('wave');
    if (hud.keys) ui.hud.push('keys');
  }
  
  // Screens (inferir padrões)
  ui.screens.push('game');
  if (spec.rules?.winCondition) ui.screens.push('victory');
  if (spec.rules?.loseCondition) ui.screens.push('gameover');
  
  return ui;
}
