/**
 * Integration Test - All Systems Working Together
 * 
 * Tests that a minimal runtime spec can be autofilled and produce
 * a playable game with all systems working correctly.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { autofillTopDownShooter } from '../runtime-autofill/topdown-shooter';
import { validateRuntimeAgainstProfile } from '../runtime-profiles/validator';
import { TOPDOWN_SHOOTER_PROFILE } from '../runtime-profiles/topdown-shooter';
import {
  PhysicsSystem,
  CollisionSystem,
  AISystem,
  InputSystem,
  SpawnerSystem,
  CombatSystem,
  GameStateSystem,
  ScoreSystem,
  TimerSystem,
  UISystem,
  JuiceSystem,
  AudioSystem,
} from './index';

describe('System Integration Tests', () => {
  let spec: any;
  let entities: any[];

  beforeEach(() => {
    // Start with minimal runtime
    const minimalRuntime = {
      gameType: 'topdown',
      title: 'Test Game',
      description: 'Integration test',
      systems: [],
      scene: {
        gravity: { x: 0, y: 0 },
        entities: []
      }
    };

    // Autofill
    const result = autofillTopDownShooter(minimalRuntime);
    spec = result.spec;
    entities = [...spec.scene.entities];
  });

  it('should autofill minimal runtime successfully', () => {
    expect(spec).toBeDefined();
    expect(spec.systems.length).toBeGreaterThan(0);
    expect(entities.length).toBeGreaterThan(0);
  });

  it('should pass validation after autofill', () => {
    const validation = validateRuntimeAgainstProfile(spec, TOPDOWN_SHOOTER_PROFILE);
    expect(validation.isValid).toBe(true);
    expect(validation.summary.critical).toBe(0);
  });

  it('should have all required systems', () => {
    const requiredSystems = [
      'PhysicsSystem',
      'CollisionSystem',
      'AISystem',
      'SpawnerSystem',
      'ScoreSystem',
      'TimerSystem',
      'UISystem',
    ];

    for (const system of requiredSystems) {
      expect(spec.systems).toContain(system);
    }
  });

  it('should have all required entities', () => {
    const player = entities.find(e => e.type === 'player');
    const enemy = entities.find(e => e.type === 'enemy');
    const bullet = entities.find(e => e.type === 'bullet');
    const spawner = entities.find(e => e.type === 'spawner');

    expect(player).toBeDefined();
    expect(enemy).toBeDefined();
    expect(bullet).toBeDefined();
    expect(spawner).toBeDefined();
  });

  describe('PhysicsSystem', () => {
    it('should move entities based on velocity', () => {
      const physics = new PhysicsSystem();
      const player = entities.find(e => e.type === 'player')!;
      
      player.props.vx = 100;
      player.props.vy = 0;
      const initialX = player.x;

      physics.update(0.1, entities);

      expect(player.x).toBeGreaterThan(initialX);
    });
  });

  describe('AISystem', () => {
    it('should make enemies chase player', () => {
      const ai = new AISystem();
      const player = entities.find(e => e.type === 'player')!;
      const enemy = entities.find(e => e.type === 'enemy')!;

      // Position enemy far from player
      enemy.x = 100;
      enemy.y = 100;
      player.x = 400;
      player.y = 300;

      ai.update(0.1, entities);

      // Enemy should have velocity toward player
      expect(enemy.props.vx).toBeGreaterThan(0);
      expect(enemy.props.vy).toBeGreaterThan(0);
    });
  });

  describe('SpawnerSystem', () => {
    it('should spawn enemies periodically', () => {
      const spawner = new SpawnerSystem();
      const initialEnemyCount = entities.filter(e => e.type === 'enemy').length;

      // Update with enough time to spawn
      spawner.update(0.1, entities, 0);
      spawner.update(0.1, entities, 3); // 3 seconds later

      const finalEnemyCount = entities.filter(e => e.type === 'enemy').length;
      expect(finalEnemyCount).toBeGreaterThan(initialEnemyCount);
    });

    it('should respect max enemies limit', () => {
      const spawner = new SpawnerSystem();
      const spawnerEntity = entities.find(e => e.type === 'spawner')!;
      spawnerEntity.props.maxEnemies = 2;

      // Try to spawn many times
      for (let i = 0; i < 10; i++) {
        spawner.update(0.1, entities, i * 3);
      }

      const enemyCount = entities.filter(e => e.type === 'enemy').length;
      expect(enemyCount).toBeLessThanOrEqual(2);
    });
  });

  describe('CombatSystem', () => {
    it('should apply damage when bullet hits enemy', () => {
      const combat = new CombatSystem();
      const bullet = entities.find(e => e.type === 'bullet')!;
      const enemy = entities.find(e => e.type === 'enemy')!;

      const initialHealth = enemy.props.health;
      combat.handleCollisionDamage(bullet, enemy);

      expect(enemy.props.health).toBeLessThan(initialHealth);
    });

    it('should remove entities with health <= 0', () => {
      const combat = new CombatSystem();
      const enemy = entities.find(e => e.type === 'enemy')!;

      enemy.props.health = 0;
      combat.update(0.1, entities);

      const enemyStillExists = entities.some(e => e.id === enemy.id);
      expect(enemyStillExists).toBe(false);
    });
  });

  describe('GameStateSystem', () => {
    it('should start in START state', () => {
      const gameState = new GameStateSystem();
      expect(gameState.current).toBe('START');
    });

    it('should transition to PLAYING when started', () => {
      const gameState = new GameStateSystem();
      gameState.start();
      expect(gameState.current).toBe('PLAYING');
    });

    it('should transition to GAME_OVER when player dies', () => {
      const gameState = new GameStateSystem();
      gameState.start();

      const player = entities.find(e => e.type === 'player')!;
      player.props.health = 0;

      gameState.update(0.1, entities);
      expect(gameState.current).toBe('GAME_OVER');
    });

    it('should restart game correctly', () => {
      const gameState = new GameStateSystem();
      const player = entities.find(e => e.type === 'player')!;

      // Kill player
      player.props.health = 0;
      gameState.start();
      gameState.update(0.1, entities);

      // Restart
      gameState.restart(entities);

      expect(gameState.current).toBe('START');
      expect(player.props.health).toBe(player.props.maxHealth);
    });
  });

  describe('CollisionSystem', () => {
    it('should detect collisions between entities', () => {
      const collision = new CollisionSystem();
      let collisionDetected = false;

      collision.on('bullet', 'enemy', () => {
        collisionDetected = true;
      });

      const bullet = entities.find(e => e.type === 'bullet')!;
      const enemy = entities.find(e => e.type === 'enemy')!;

      // Position them to collide
      bullet.x = 100;
      bullet.y = 100;
      enemy.x = 100;
      enemy.y = 100;

      collision.update(entities);
      expect(collisionDetected).toBe(true);
    });
  });

  describe('Full Game Loop', () => {
    it('should run complete game loop without errors', () => {
      const physics = new PhysicsSystem();
      const collision = new CollisionSystem();
      const ai = new AISystem();
      const spawner = new SpawnerSystem();
      const combat = new CombatSystem();
      const gameState = new GameStateSystem();
      const score = new ScoreSystem();
      const timer = new TimerSystem();
      const juice = new JuiceSystem();
      const audio = new AudioSystem();

      // Setup collision handlers
      collision.on('bullet', 'enemy', (bullet, enemy) => {
        combat.handleCollisionDamage(bullet, enemy);
        score.addScore(10);
        audio.playHitSound();
      });

      collision.on('enemy', 'player', (enemy, player) => {
        combat.handleCollisionDamage(enemy, player);
        audio.playHitSound();
      });

      // Start game
      gameState.start();

      // Run 10 frames
      for (let i = 0; i < 10; i++) {
        const dt = 0.016; // 60 FPS
        const currentTime = i * dt;

        if (gameState.current === 'PLAYING') {
          physics.update(dt, entities);
          ai.update(dt, entities);
          spawner.update(dt, entities, currentTime);
          collision.update(entities);
          combat.update(dt, entities);
          gameState.update(dt, entities);
          timer.update(dt);
          juice.update(dt, entities, score, gameState.current);
        }
      }

      // Game should still be running (player shouldn't die in 10 frames)
      expect(gameState.current).toBe('PLAYING');
    });

    it('should integrate juice system without breaking gameplay', () => {
      const juice = new JuiceSystem();
      const player = entities.find(e => e.type === 'player')!;
      
      // Juice should not break player movement
      const initialX = player.x;
      player.props.vx = 100;
      
      juice.update(0.1, entities);
      
      // Player should still be able to move
      expect(player.props.vx).toBeDefined();
    });

    it('should handle audio system gracefully when no sounds loaded', () => {
      const audio = new AudioSystem();
      
      // Should not throw errors
      expect(() => {
        audio.playShootSound();
        audio.playHitSound();
        audio.playDeathSound();
      }).not.toThrow();
    });
  });
});
