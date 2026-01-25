/**
 * Testes do Profile Validator
 */

import { describe, it, expect } from 'vitest';
import { TOPDOWN_SHOOTER_PROFILE } from './topdown-shooter';
import { validateRuntimeAgainstProfile } from './validator';
import type { OrdaxSpec } from '../types';

describe('Profile Validator - Top-Down Shooter', () => {
  it('deve detectar sistemas faltantes', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: ['PhysicsSystem'], // Faltam 6 sistemas
      scene: {
        gravity: { x: 0, y: 0 },
        entities: []
      }
    };

    const result = validateRuntimeAgainstProfile(spec, TOPDOWN_SHOOTER_PROFILE);
    
    expect(result.isValid).toBe(false);
    expect(result.missingElements.systems).toContain('CollisionSystem');
    expect(result.missingElements.systems).toContain('AISystem');
    expect(result.missingElements.systems).toContain('SpawnerSystem');
    expect(result.summary.critical).toBeGreaterThan(0);
  });

  it('deve detectar entidades faltantes', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: TOPDOWN_SHOOTER_PROFILE.requiredSystems,
      scene: {
        gravity: { x: 0, y: 0 },
        entities: [] // Nenhuma entidade
      }
    };

    const result = validateRuntimeAgainstProfile(spec, TOPDOWN_SHOOTER_PROFILE);
    
    expect(result.isValid).toBe(false);
    expect(result.missingElements.entities).toContain('player');
    expect(result.missingElements.entities).toContain('enemy');
    expect(result.missingElements.entities).toContain('bullet');
    expect(result.missingElements.entities).toContain('spawner');
  });

  it('deve detectar componentes faltantes em entidades', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: TOPDOWN_SHOOTER_PROFILE.requiredSystems,
      scene: {
        gravity: { x: 0, y: 0 },
        entities: [
          {
            id: 'player1',
            type: 'player',
            x: 0,
            y: 0,
            w: 32,
            h: 32,
            props: {} // Sem componentes
          }
        ]
      }
    };

    const result = validateRuntimeAgainstProfile(spec, TOPDOWN_SHOOTER_PROFILE);
    
    expect(result.isValid).toBe(false);
    expect(result.missingElements.components['player']).toBeDefined();
    expect(result.missingElements.components['player']).toContain('Health');
    expect(result.missingElements.components['player']).toContain('Weapon');
  });

  it('deve validar runtime completo como válido', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Complete Game',
      description: 'A complete top-down shooter',
      systems: TOPDOWN_SHOOTER_PROFILE.requiredSystems,
      scene: {
        gravity: { x: 0, y: 0 },
        entities: [
          {
            id: 'player1',
            type: 'player',
            x: 400,
            y: 300,
            w: 32,
            h: 32,
            props: {
              x: 400,
              y: 300,
              health: 100,
              speed: 200,
              fireRate: 0.2,
              vx: 0,
              vy: 0,
              damage: 25,
              w: 32,
              h: 32
            }
          },
          {
            id: 'enemy1',
            type: 'enemy',
            x: 200,
            y: 100,
            w: 24,
            h: 24,
            props: {
              x: 200,
              y: 100,
              health: 50,
              speed: 100,
              damage: 10,
              ai: 'chase',
              vx: 0,
              vy: 0,
              w: 24,
              h: 24
            }
          },
          {
            id: 'bullet1',
            type: 'bullet',
            x: 0,
            y: 0,
            w: 4,
            h: 4,
            props: {
              speed: 400,
              damage: 25,
              vx: 0,
              vy: 0,
              lifetime: 2.0
            }
          },
          {
            id: 'spawner1',
            type: 'spawner',
            x: 400,
            y: 50,
            w: 1,
            h: 1,
            props: {
              spawnRate: 2.0,
              spawner: true
            }
          }
        ]
      }
    };

    const result = validateRuntimeAgainstProfile(spec, TOPDOWN_SHOOTER_PROFILE);
    
    // Pode ter algumas violações menores (UI, controles), mas não críticas de sistemas/entidades
    expect(result.missingElements.systems).toHaveLength(0);
    expect(result.missingElements.entities).toHaveLength(0);
  });

  it('deve detectar props obrigatórias faltantes', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: TOPDOWN_SHOOTER_PROFILE.requiredSystems,
      scene: {
        gravity: { x: 0, y: 0 },
        entities: [
          {
            id: 'player1',
            type: 'player',
            x: 0,
            y: 0,
            w: 32,
            h: 32,
            props: {
              x: 0,
              y: 0,
              vx: 0,
              vy: 0,
              // Faltam: health, speed, fireRate
            }
          }
        ]
      }
    };

    const result = validateRuntimeAgainstProfile(spec, TOPDOWN_SHOOTER_PROFILE);
    
    const propViolations = result.violations.filter(v => 
      v.category === 'component' && v.id.includes('PROP_')
    );
    
    expect(propViolations.length).toBeGreaterThan(0);
    expect(propViolations.some(v => v.message.includes('health'))).toBe(true);
    expect(propViolations.some(v => v.message.includes('speed'))).toBe(true);
  });
});
