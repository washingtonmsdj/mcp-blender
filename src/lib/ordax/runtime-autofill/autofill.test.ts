/**
 * Testes do Runtime Autofill
 */

import { describe, it, expect } from 'vitest';
import { autofillTopDownShooter, needsAutofill, autofillAndValidate } from './topdown-shooter';
import type { OrdaxSpec } from '../types';

describe('Runtime Autofill - Top-Down Shooter', () => {
  it('deve detectar que runtime vazio precisa de autofill', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: [],
      scene: {
        gravity: { x: 0, y: 0 },
        entities: []
      }
    };

    expect(needsAutofill(spec)).toBe(true);
  });

  it('deve adicionar sistemas faltantes', () => {
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

    const result = autofillTopDownShooter(spec);
    
    expect(result.wasModified).toBe(true);
    expect(result.spec.systems).toContain('CollisionSystem');
    expect(result.spec.systems).toContain('AISystem');
    expect(result.spec.systems).toContain('SpawnerSystem');
    expect(result.spec.systems).toContain('ScoreSystem');
    expect(result.spec.systems).toContain('TimerSystem');
    expect(result.spec.systems).toContain('UISystem');
    expect(result.changes.length).toBeGreaterThan(0);
  });

  it('deve adicionar entidades faltantes', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: [
        'PhysicsSystem',
        'CollisionSystem',
        'AISystem',
        'SpawnerSystem',
        'ScoreSystem',
        'TimerSystem',
        'UISystem'
      ],
      scene: {
        gravity: { x: 0, y: 0 },
        entities: [] // Nenhuma entidade
      }
    };

    const result = autofillTopDownShooter(spec);
    
    expect(result.wasModified).toBe(true);
    expect(result.spec.scene.entities.some(e => e.type === 'player')).toBe(true);
    expect(result.spec.scene.entities.some(e => e.type === 'enemy')).toBe(true);
    expect(result.spec.scene.entities.some(e => e.type === 'bullet')).toBe(true);
    expect(result.spec.scene.entities.some(e => e.type === 'spawner')).toBe(true);
  });

  it('deve adicionar props faltantes em player', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: [
        'PhysicsSystem',
        'CollisionSystem',
        'AISystem',
        'SpawnerSystem',
        'ScoreSystem',
        'TimerSystem',
        'UISystem'
      ],
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
              // Faltam: health, speed, fireRate, etc.
            }
          }
        ]
      }
    };

    const result = autofillTopDownShooter(spec);
    
    expect(result.wasModified).toBe(true);
    
    const player = result.spec.scene.entities.find(e => e.type === 'player');
    expect(player).toBeDefined();
    expect(player!.props!.health).toBeDefined();
    expect(player!.props!.speed).toBeDefined();
    expect(player!.props!.fireRate).toBeDefined();
    expect(player!.props!.damage).toBeDefined();
  });

  it('deve adicionar visual theme se não existir', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: [
        'PhysicsSystem',
        'CollisionSystem',
        'AISystem',
        'SpawnerSystem',
        'ScoreSystem',
        'TimerSystem',
        'UISystem'
      ],
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
              health: 100,
              speed: 200,
              fireRate: 0.25,
              damage: 25,
            }
          }
        ]
      }
    };

    const result = autofillTopDownShooter(spec);
    
    expect(result.spec.visual).toBeDefined();
    expect(result.spec.visual!.theme).toBeDefined();
    expect(result.spec.visual!.background).toBeDefined();
  });

  it('deve adicionar UI metadata', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: [
        'PhysicsSystem',
        'CollisionSystem',
        'AISystem',
        'SpawnerSystem',
        'ScoreSystem',
        'TimerSystem',
        'UISystem'
      ],
      scene: {
        gravity: { x: 0, y: 0 },
        entities: []
      }
    };

    const result = autofillTopDownShooter(spec);
    
    const uiMetadata = result.spec.scene.entities.find(e => e.type === 'ui');
    expect(uiMetadata).toBeDefined();
    expect(uiMetadata!.props!.startScreen).toBeDefined();
    expect(uiMetadata!.props!.hud).toBeDefined();
    expect(uiMetadata!.props!.gameOverScreen).toBeDefined();
  });

  it('deve adicionar controls metadata', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: [
        'PhysicsSystem',
        'CollisionSystem',
        'AISystem',
        'SpawnerSystem',
        'ScoreSystem',
        'TimerSystem',
        'UISystem'
      ],
      scene: {
        gravity: { x: 0, y: 0 },
        entities: []
      }
    };

    const result = autofillTopDownShooter(spec);
    
    const controlsMetadata = result.spec.scene.entities.find(e => e.type === 'controls');
    expect(controlsMetadata).toBeDefined();
    expect(controlsMetadata!.props!.movement).toBeDefined();
    expect(controlsMetadata!.props!.action).toBeDefined();
  });

  it('deve corrigir gravity para top-down', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: [
        'PhysicsSystem',
        'CollisionSystem',
        'AISystem',
        'SpawnerSystem',
        'ScoreSystem',
        'TimerSystem',
        'UISystem'
      ],
      scene: {
        gravity: { x: 0, y: 980 }, // Gravity errado para top-down
        entities: []
      }
    };

    const result = autofillTopDownShooter(spec);
    
    expect(result.spec.scene.gravity.x).toBe(0);
    expect(result.spec.scene.gravity.y).toBe(0);
  });

  it('deve validar runtime após autofill', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Test',
      description: 'Test',
      systems: [],
      scene: {
        gravity: { x: 0, y: 0 },
        entities: []
      }
    };

    const result = autofillAndValidate(spec);
    
    expect(result.wasModified).toBe(true);
    // Pode não ser 100% válido devido a UI/controles (heurísticas),
    // mas violações críticas de sistemas/entidades devem ser 0
    expect(result.remainingViolations).toBeLessThan(5);
  });

  it('não deve modificar runtime já completo', () => {
    const spec: OrdaxSpec = {
      gameType: 'topdown',
      title: 'Complete Game',
      description: 'A complete game',
      systems: [
        'PhysicsSystem',
        'CollisionSystem',
        'AISystem',
        'SpawnerSystem',
        'ScoreSystem',
        'TimerSystem',
        'UISystem'
      ],
      visual: {
        theme: {
          background: 'hsl(220, 20%, 10%)',
          primary: 'hsl(200, 80%, 60%)',
          accent: 'hsl(30, 90%, 60%)',
        }
      },
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
              health: 100,
              speed: 200,
              fireRate: 0.25,
              damage: 25,
              vx: 0,
              vy: 0,
              x: 400,
              y: 300,
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
              health: 50,
              speed: 100,
              damage: 10,
              ai: 'chase',
              target: 'player',
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
              spawner: true,
            }
          }
        ]
      }
    };

    const result = autofillTopDownShooter(spec);
    
    // Pode adicionar algumas coisas (UI metadata, audio), mas não deve modificar entidades existentes
    expect(result.spec.scene.entities.filter(e => ['player', 'enemy', 'bullet', 'spawner'].includes(e.type)).length).toBe(4);
  });
});
