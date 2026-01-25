/**
 * PRESET: ZOMBIE ARENA
 * 
 * Sobreviva em uma arena contra ondas de zumbis.
 * - Player atirador
 * - Zumbis em ondas crescentes
 * - Power-ups de cura
 * - Score por kills
 */

import type { RuntimeSpec } from '../types';
import type { CanonicalPreset } from './index';

export function createZombieArenaPreset(): CanonicalPreset {
  const runtimeSpec: RuntimeSpec = {
    profile: 'topdown-shooter',
    
    entities: {
      player: {
        sprite: '🧑',
        position: { x: 400, y: 300 },
        velocity: { x: 0, y: 0 },
        health: 100,
        maxHealth: 100,
        speed: 180,
        size: { width: 32, height: 32 },
        collisionLayer: 'player',
        collidesWith: ['enemy', 'collectible'],
        weapon: {
          damage: 25,
          fireRate: 300,
          projectileSpeed: 400,
          projectileSprite: '💥'
        }
      },
      
      zombie: {
        sprite: '🧟',
        position: { x: 0, y: 0 },
        velocity: { x: 0, y: 0 },
        health: 50,
        damage: 15,
        speed: 60,
        size: { width: 32, height: 32 },
        collisionLayer: 'enemy',
        collidesWith: ['player', 'projectile'],
        aiType: 'chase',
        scoreValue: 10
      },
      
      healthPack: {
        sprite: '❤️',
        position: { x: 0, y: 0 },
        size: { width: 24, height: 24 },
        collisionLayer: 'collectible',
        collidesWith: ['player'],
        healAmount: 30
      }
    },
    
    spawners: {
      zombieSpawner: {
        entityType: 'zombie',
        interval: 1500,
        maxActive: 15,
        spawnArea: {
          x: 0,
          y: 0,
          width: 800,
          height: 600
        },
        waveScaling: {
          intervalDecrease: 100,
          maxActiveIncrease: 2,
          waveInterval: 30000
        }
      },
      
      healthSpawner: {
        entityType: 'healthPack',
        interval: 8000,
        maxActive: 2,
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
        target: 500
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
        wave: true
      }
    }
  };

  return {
    id: 'zombie-arena',
    name: 'Zombie Arena',
    description: 'Sobreviva contra ondas crescentes de zumbis',
    emoji: '🧟',
    runtimeSpec
  };
}
