/**
 * FASE 9: PATCH COMPOSER
 * 
 * Compõe múltiplos patches canônicos em um único patch determinístico
 */

import type { RuntimeSpec } from '../types';
import type { SemanticPatch, RemixChange } from './index';
import type { ParsedIntent } from './parse-remix-intent';

export function composePatches(
  baseSpec: RuntimeSpec,
  intent: ParsedIntent
): { patch: SemanticPatch; changes: RemixChange[] } {
  let composedPatch: SemanticPatch = {};
  let allChanges: RemixChange[] = [];
  
  // 1. Aplicar temas (ordem: primeiro tema é dominante)
  for (const theme of intent.themes) {
    const { patch, changes } = getThemePatch(baseSpec, theme);
    composedPatch = mergePatch(composedPatch, patch);
    allChanges.push(...changes);
  }
  
  // 2. Aplicar dificuldade
  if (intent.difficulty !== 'normal') {
    const { patch, changes } = getDifficultyPatch(baseSpec, intent.difficulty);
    composedPatch = mergePatch(composedPatch, patch);
    allChanges.push(...changes);
  }
  
  // 3. Aplicar velocidade
  if (intent.speed !== 'normal') {
    const { patch, changes } = getSpeedPatch(baseSpec, intent.speed);
    composedPatch = mergePatch(composedPatch, patch);
    allChanges.push(...changes);
  }
  
  // 4. Adicionar boss
  if (intent.boss) {
    const { patch, changes } = getBossPatch(baseSpec);
    composedPatch = mergePatch(composedPatch, patch);
    allChanges.push(...changes);
  }
  
  return { patch: composedPatch, changes: allChanges };
}

function getThemePatch(
  baseSpec: RuntimeSpec,
  theme: string
): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = { entities: { modify: {} } };
  const changes: RemixChange[] = [];
  
  const themeConfig = {
    zombie: { playerSprite: '🧑', enemySprite: '🧟', speedMult: 0.6, healthMult: 1.5 },
    space: { playerSprite: '🚀', enemySprite: '☄️', speedMult: 1.0, healthMult: 1.0 },
    medieval: { playerSprite: '🗡️', enemySprite: '👺', speedMult: 1.0, healthMult: 1.0 },
    ninja: { playerSprite: '🥷', enemySprite: '👹', speedMult: 1.3, healthMult: 0.8 },
    pirate: { playerSprite: '🏴‍☠️', enemySprite: '🦜', speedMult: 1.0, healthMult: 1.0 },
    robot: { playerSprite: '🤖', enemySprite: '👾', speedMult: 1.2, healthMult: 1.3 }
  };
  
  const config = themeConfig[theme as keyof typeof themeConfig];
  if (!config) return { patch, changes };
  
  // Modificar player
  if (baseSpec.entities?.player) {
    patch.entities!.modify!.player = {
      ...baseSpec.entities.player,
      sprite: config.playerSprite
    };
    changes.push({
      type: 'modify',
      category: 'entity',
      target: 'player',
      description: `Tema ${theme}: player virou ${config.playerSprite}`
    });
  }
  
  // Modificar inimigos
  Object.keys(baseSpec.entities || {}).forEach(key => {
    const entity = baseSpec.entities![key];
    if (entity.damage || entity.aiType) {
      patch.entities!.modify![key] = {
        ...entity,
        sprite: config.enemySprite,
        speed: (entity.speed || 100) * config.speedMult,
        health: (entity.health || 50) * config.healthMult
      };
      changes.push({
        type: 'modify',
        category: 'entity',
        target: key,
        description: `Tema ${theme}: inimigo virou ${config.enemySprite}`
      });
    }
  });
  
  return { patch, changes };
}

function getDifficultyPatch(
  baseSpec: RuntimeSpec,
  difficulty: 'easy' | 'hard'
): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = { entities: { modify: {} }, spawners: { modify: {} } };
  const changes: RemixChange[] = [];
  
  const mult = difficulty === 'easy' ? 0.7 : 1.5;
  const spawnMult = difficulty === 'easy' ? 1.5 : 0.7;
  
  // Modificar inimigos
  Object.keys(baseSpec.entities || {}).forEach(key => {
    const entity = baseSpec.entities![key];
    if (entity.damage || entity.aiType) {
      patch.entities!.modify![key] = {
        ...entity,
        health: (entity.health || 50) * mult,
        damage: (entity.damage || 10) * mult,
        speed: (entity.speed || 100) * (difficulty === 'easy' ? 0.8 : 1.2)
      };
    }
  });
  
  // Modificar spawners
  Object.keys(baseSpec.spawners || {}).forEach(key => {
    const spawner = baseSpec.spawners![key];
    patch.spawners!.modify![key] = {
      ...spawner,
      interval: spawner.interval * spawnMult,
      maxActive: Math.floor((spawner.maxActive || 5) * mult)
    };
  });
  
  changes.push({
    type: 'modify',
    category: 'entity',
    target: 'all',
    description: `Dificuldade ${difficulty}: ${difficulty === 'easy' ? '-30%' : '+50%'} stats`
  });
  
  return { patch, changes };
}

function getSpeedPatch(
  baseSpec: RuntimeSpec,
  speed: 'slower' | 'faster'
): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = { entities: { modify: {} }, spawners: { modify: {} } };
  const changes: RemixChange[] = [];
  
  const mult = speed === 'slower' ? 0.7 : 1.5;
  const spawnMult = speed === 'slower' ? 1.5 : 0.7;
  
  // Modificar velocidades
  Object.keys(baseSpec.entities || {}).forEach(key => {
    const entity = baseSpec.entities![key];
    if (entity.speed) {
      patch.entities!.modify![key] = {
        ...entity,
        speed: entity.speed * mult
      };
    }
  });
  
  // Modificar spawners
  Object.keys(baseSpec.spawners || {}).forEach(key => {
    const spawner = baseSpec.spawners![key];
    patch.spawners!.modify![key] = {
      ...spawner,
      interval: spawner.interval * spawnMult
    };
  });
  
  changes.push({
    type: 'modify',
    category: 'entity',
    target: 'all',
    description: `Velocidade ${speed}: ${speed === 'slower' ? '-30%' : '+50%'}`
  });
  
  return { patch, changes };
}

function getBossPatch(
  baseSpec: RuntimeSpec
): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = { entities: { add: {} }, spawners: { add: {} } };
  const changes: RemixChange[] = [];
  
  // Adicionar entidade boss
  patch.entities!.add!.boss = {
    sprite: '👑',
    position: { x: 400, y: 100 },
    velocity: { x: 0, y: 0 },
    health: 500,
    maxHealth: 500,
    damage: 50,
    speed: 80,
    size: { width: 64, height: 64 },
    collisionLayer: 'enemy',
    collidesWith: ['player', 'projectile'],
    aiType: 'boss',
    scoreValue: 1000
  };
  
  // Adicionar spawner do boss
  patch.spawners!.add!.bossSpawner = {
    entityType: 'boss',
    interval: 60000, // 1 minuto
    maxActive: 1,
    spawnArea: {
      x: 300,
      y: 50,
      width: 200,
      height: 100
    }
  };
  
  changes.push({
    type: 'add',
    category: 'entity',
    target: 'boss',
    description: 'Boss adicionado: 👑 (500 HP, 50 dano)'
  });
  
  return { patch, changes };
}

function mergePatch(base: SemanticPatch, addition: SemanticPatch): SemanticPatch {
  const merged: SemanticPatch = JSON.parse(JSON.stringify(base));
  
  // Merge entities
  if (addition.entities) {
    if (!merged.entities) merged.entities = {};
    
    if (addition.entities.add) {
      if (!merged.entities.add) merged.entities.add = {};
      Object.assign(merged.entities.add, addition.entities.add);
    }
    
    if (addition.entities.remove) {
      if (!merged.entities.remove) merged.entities.remove = [];
      merged.entities.remove.push(...addition.entities.remove);
    }
    
    if (addition.entities.modify) {
      if (!merged.entities.modify) merged.entities.modify = {};
      // Deep merge modify
      Object.keys(addition.entities.modify).forEach(key => {
        if (merged.entities!.modify![key]) {
          merged.entities!.modify![key] = {
            ...merged.entities!.modify![key],
            ...addition.entities!.modify![key]
          };
        } else {
          merged.entities!.modify![key] = addition.entities!.modify![key];
        }
      });
    }
  }
  
  // Merge spawners
  if (addition.spawners) {
    if (!merged.spawners) merged.spawners = {};
    
    if (addition.spawners.add) {
      if (!merged.spawners.add) merged.spawners.add = {};
      Object.assign(merged.spawners.add, addition.spawners.add);
    }
    
    if (addition.spawners.remove) {
      if (!merged.spawners.remove) merged.spawners.remove = [];
      merged.spawners.remove.push(...addition.spawners.remove);
    }
    
    if (addition.spawners.modify) {
      if (!merged.spawners.modify) merged.spawners.modify = {};
      Object.keys(addition.spawners.modify).forEach(key => {
        if (merged.spawners!.modify![key]) {
          merged.spawners!.modify![key] = {
            ...merged.spawners!.modify![key],
            ...addition.spawners!.modify![key]
          };
        } else {
          merged.spawners!.modify![key] = addition.spawners!.modify![key];
        }
      });
    }
  }
  
  // Merge rules
  if (addition.rules) {
    if (!merged.rules) merged.rules = {};
    Object.assign(merged.rules, addition.rules);
  }
  
  // Merge UI
  if (addition.ui) {
    if (!merged.ui) merged.ui = {};
    Object.assign(merged.ui, addition.ui);
  }
  
  return merged;
}
