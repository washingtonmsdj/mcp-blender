/**
 * PRESET: SPACE SURVIVAL
 * 
 * Sobreviva no espaço coletando recursos e evitando asteroides.
 * - Player nave espacial
 * - Asteroides como inimigos
 * - Cristais como coletáveis
 * - Score por tempo + coleta
 */

import type { RuntimeSpec } from '../types';
import type { CanonicalPreset } from './index';

export function createSpaceSurvivalPreset(): CanonicalPreset {
  const runtimeSpec: RuntimeSpec = {
    profile: 'topdown-shooter',
    
    entities: {
      player: {
        sprite: '🚀',
        position: { x: 400, y: 300 },
        velocity: { x: 0, y: 0 },
        health: 100,
        maxHealth: 100,
        speed: 200,
        size: { width: 32, height: 32 },
        collisionLayer: 'player',
        collidesWith: ['enemy', 'collectible']
      },
      
      asteroid: {
        sprite: '☄️',
        position: { x: 0, y: 0 },
        velocity: { x: 0, y: 0 },
        health: 30,
        damage: 20,
        speed: 80,
        size: { width: 40, height: 40 },
        collisionLayer: 'enemy',
        collidesWith: ['player'],
        aiType: 'chase'
      },
      
      crystal: {
        sprite: '💎',
        position: { x: 0, y: 0 },
        size: { width: 24, height: 24 },
        collisionLayer: 'collectible',
        collidesWith: ['player'],
        scoreValue: 50
      }
    },
    
    spawners: {
      asteroidSpawner: {
        entityType: 'asteroid',
        interval: 2000,
        maxActive: 8,
        spawnArea: {
          x: 0,
          y: 0,
          width: 800,
          height: 600
        }
      },
      
      crystalSpawner: {
        entityType: 'crystal',
        interval: 3000,
        maxActive: 5,
        spawnArea: {
          x: 0,
          y: 0,
          width: 800,
          height: 600
        }
      }
    },
    
    rules: {
      winCondition: {
        type: 'score',
        target: 1000
      },
      
      loseCondition: {
        type: 'health',
        target: 0
      }
    },
    
    ui: {
      hud: {
        health: true,
        score: true,
        timer: true
      }
    }
  };

  return {
    id: 'space-survival',
    name: 'Space Survival',
    description: 'Sobreviva no espaço coletando cristais e evitando asteroides',
    emoji: '🚀',
    runtimeSpec
  };
}
