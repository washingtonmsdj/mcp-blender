/**
 * PRESET: DUNGEON SHOOTER
 * 
 * Explore uma dungeon atirando em monstros e coletando tesouros.
 * - Player explorador
 * - Monstros variados
 * - Tesouros e chaves
 * - Score por exploração
 */

import type { RuntimeSpec } from '../types';
import type { CanonicalPreset } from './index';

export function createDungeonShooterPreset(): CanonicalPreset {
  const runtimeSpec: RuntimeSpec = {
    profile: 'topdown-shooter',
    
    entities: {
      player: {
        sprite: '🗡️',
        position: { x: 100, y: 100 },
        velocity: { x: 0, y: 0 },
        health: 100,
        maxHealth: 100,
        speed: 160,
        size: { width: 32, height: 32 },
        collisionLayer: 'player',
        collidesWith: ['enemy', 'collectible', 'wall'],
        weapon: {
          damage: 30,
          fireRate: 400,
          projectileSpeed: 350,
          projectileSprite: '⚔️'
        }
      },
      
      goblin: {
        sprite: '👺',
        position: { x: 0, y: 0 },
        velocity: { x: 0, y: 0 },
        health: 40,
        damage: 12,
        speed: 90,
        size: { width: 32, height: 32 },
        collisionLayer: 'enemy',
        collidesWith: ['player', 'projectile', 'wall'],
        aiType: 'patrol',
        scoreValue: 15
      },
      
      skeleton: {
        sprite: '💀',
        position: { x: 0, y: 0 },
        velocity: { x: 0, y: 0 },
        health: 60,
        damage: 18,
        speed: 70,
        size: { width: 32, height: 32 },
        collisionLayer: 'enemy',
        collidesWith: ['player', 'projectile', 'wall'],
        aiType: 'chase',
        scoreValue: 25
      },
      
      treasure: {
        sprite: '💰',
        position: { x: 0, y: 0 },
        size: { width: 24, height: 24 },
        collisionLayer: 'collectible',
        collidesWith: ['player'],
        scoreValue: 100
      },
      
      key: {
        sprite: '🔑',
        position: { x: 0, y: 0 },
        size: { width: 24, height: 24 },
        collisionLayer: 'collectible',
        collidesWith: ['player'],
        scoreValue: 50
      }
    },
    
    spawners: {
      goblinSpawner: {
        entityType: 'goblin',
        interval: 3000,
        maxActive: 6,
        spawnArea: {
          x: 200,
          y: 200,
          width: 600,
          height: 400
        }
      },
      
      skeletonSpawner: {
        entityType: 'skeleton',
        interval: 5000,
        maxActive: 4,
        spawnArea: {
          x: 200,
          y: 200,
          width: 600,
          height: 400
        }
      },
      
      treasureSpawner: {
        entityType: 'treasure',
        interval: 10000,
        maxActive: 3,
        spawnArea: {
          x: 100,
          y: 100,
          width: 700,
          height: 500
        }
      },
      
      keySpawner: {
        entityType: 'key',
        interval: 15000,
        maxActive: 1,
        spawnArea: {
          x: 100,
          y: 100,
          width: 700,
          height: 500
        }
      }
    },
    
    rules: {
      winCondition: {
        type: 'score',
        target: 800
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
        ammo: true,
        keys: true
      }
    }
  };

  return {
    id: 'dungeon-shooter',
    name: 'Dungeon Shooter',
    description: 'Explore a dungeon, derrote monstros e colete tesouros',
    emoji: '🗡️',
    runtimeSpec
  };
}
