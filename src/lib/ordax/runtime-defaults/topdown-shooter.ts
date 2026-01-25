/**
 * Top-Down Shooter Survival - Default Values
 * 
 * Valores canônicos e fechados para entidades do gênero top-down shooter.
 * Estes valores garantem que o jogo seja jogável mesmo com runtime mínimo.
 */

import type { OrdaxEntity } from '../types';

// ============================================================================
// PLAYER DEFAULTS
// ============================================================================

export const DEFAULT_PLAYER: Partial<OrdaxEntity> = {
  type: 'player',
  w: 32,
  h: 32,
  props: {
    // Transform
    x: 400,
    y: 300,
    rotation: 0,
    
    // Velocity
    vx: 0,
    vy: 0,
    speed: 200,
    
    // Health
    health: 100,
    maxHealth: 100,
    
    // Weapon
    fireRate: 0.25, // 4 tiros por segundo
    damage: 25,
    lastFired: 0,
    
    // Collider
    radius: 16,
    collider: 'circle',
    
    // Visual
    color: 'hsl(200, 80%, 60%)', // Azul
  }
};

// ============================================================================
// ENEMY DEFAULTS
// ============================================================================

export const DEFAULT_ENEMY: Partial<OrdaxEntity> = {
  type: 'enemy',
  w: 24,
  h: 24,
  props: {
    // Transform
    x: 0,
    y: 0,
    rotation: 0,
    
    // Velocity
    vx: 0,
    vy: 0,
    speed: 100,
    
    // Health
    health: 50,
    maxHealth: 50,
    
    // AI
    ai: 'chase',
    behavior: 'aggressive',
    target: 'player',
    detectionRadius: 300,
    
    // Damage
    damage: 10,
    contactDamage: 10,
    
    // Collider
    radius: 12,
    collider: 'circle',
    
    // Visual
    color: 'hsl(0, 80%, 60%)', // Vermelho
    
    // Score
    scoreValue: 10,
  }
};

// ============================================================================
// BULLET DEFAULTS
// ============================================================================

export const DEFAULT_BULLET: Partial<OrdaxEntity> = {
  type: 'bullet',
  w: 4,
  h: 4,
  props: {
    // Transform
    x: 0,
    y: 0,
    rotation: 0,
    
    // Velocity
    vx: 0,
    vy: 0,
    speed: 400,
    
    // Damage
    damage: 25,
    
    // Lifetime
    lifetime: 2.0,
    ttl: 2.0,
    
    // Collider
    radius: 2,
    collider: 'circle',
    
    // Visual
    color: 'hsl(60, 100%, 70%)', // Amarelo
    
    // Owner
    owner: 'player',
  }
};

// ============================================================================
// SPAWNER DEFAULTS
// ============================================================================

export const DEFAULT_SPAWNER: Partial<OrdaxEntity> = {
  type: 'spawner',
  w: 1,
  h: 1,
  props: {
    // Transform
    x: 400,
    y: 50,
    
    // Spawner
    spawner: true,
    spawnRate: 2.0, // 1 inimigo a cada 2 segundos
    maxEnemies: 20,
    currentWave: 1,
    enemiesSpawned: 0,
    
    // Spawn area
    spawnRadius: 50,
    spawnType: 'enemy',
    
    // Wave progression
    waveMultiplier: 1.2, // Cada onda aumenta 20% dificuldade
  }
};

// ============================================================================
// UI DEFAULTS
// ============================================================================

export const DEFAULT_UI = {
  startScreen: {
    title: 'Top-Down Shooter',
    subtitle: 'Survive as long as you can!',
    instructions: [
      'WASD - Move',
      'SPACE - Shoot',
      'ESC - Pause'
    ],
    startButtonText: 'Start Game',
    backgroundColor: 'hsl(220, 20%, 10%)',
    textColor: 'hsl(0, 0%, 100%)',
  },
  
  hud: {
    position: 'top',
    elements: [
      { type: 'health', label: 'Health', format: 'bar' },
      { type: 'score', label: 'Score', format: 'number' },
      { type: 'timer', label: 'Time', format: 'time' },
      { type: 'wave', label: 'Wave', format: 'number' },
    ],
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    textColor: 'hsl(0, 0%, 100%)',
  },
  
  gameOverScreen: {
    title: 'Game Over',
    showFinalScore: true,
    showSurvivalTime: true,
    showHighScore: true,
    restartButtonText: 'Restart',
    mainMenuButtonText: 'Main Menu',
    backgroundColor: 'hsl(220, 20%, 10%)',
    textColor: 'hsl(0, 0%, 100%)',
  }
};

// ============================================================================
// CONTROLS DEFAULTS
// ============================================================================

export const DEFAULT_CONTROLS = {
  movement: {
    up: 'W',
    down: 'S',
    left: 'A',
    right: 'D',
    type: '8-directional', // ou '4-directional'
  },
  
  action: {
    shoot: 'SPACE',
    shootAlt: 'MOUSE_LEFT',
    autoFire: false,
  },
  
  pause: {
    pause: 'ESC',
    pauseAlt: 'P',
  }
};

// ============================================================================
// VISUAL DEFAULTS
// ============================================================================

export const DEFAULT_VISUAL = {
  theme: {
    background: 'hsl(220, 20%, 10%)',
    primary: 'hsl(200, 80%, 60%)',
    accent: 'hsl(30, 90%, 60%)',
    font: 'ui-sans-serif, system-ui, sans-serif',
  },
  
  background: {
    layers: [
      {
        type: 'starfield' as const,
        parallax: 0.5,
        density: 100,
        speedY: -10,
      },
      {
        type: 'nebula' as const,
        parallax: 0.3,
        density: 50,
        speedY: -5,
      }
    ]
  }
};

// ============================================================================
// AUDIO DEFAULTS
// ============================================================================

export const DEFAULT_AUDIO = {
  sounds: {
    shoot: 'laser.mp3',
    hit: 'hit.mp3',
    explosion: 'explosion.mp3',
    pickup: 'pickup.mp3',
    gameOver: 'gameover.mp3',
  },
  music: {
    menu: 'menu-music.mp3',
    gameplay: 'gameplay-music.mp3',
  },
  volume: {
    master: 0.7,
    sfx: 0.8,
    music: 0.5,
  }
};

// ============================================================================
// SCENE DEFAULTS
// ============================================================================

export const DEFAULT_SCENE = {
  gravity: { x: 0, y: 0 }, // Top-down não tem gravidade
  bounds: {
    width: 800,
    height: 600,
    wrap: false, // Jogador não pode sair da tela
  }
};

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Cria uma entidade player com valores default
 */
export function createDefaultPlayer(overrides?: Partial<OrdaxEntity>): OrdaxEntity {
  return {
    id: overrides?.id || 'player1',
    type: 'player',
    x: overrides?.x ?? DEFAULT_PLAYER.props!.x as number,
    y: overrides?.y ?? DEFAULT_PLAYER.props!.y as number,
    w: overrides?.w ?? DEFAULT_PLAYER.w!,
    h: overrides?.h ?? DEFAULT_PLAYER.h!,
    props: {
      ...DEFAULT_PLAYER.props,
      ...overrides?.props,
    }
  };
}

/**
 * Cria uma entidade enemy com valores default
 */
export function createDefaultEnemy(overrides?: Partial<OrdaxEntity>): OrdaxEntity {
  return {
    id: overrides?.id || `enemy_${Date.now()}`,
    type: 'enemy',
    x: overrides?.x ?? DEFAULT_ENEMY.props!.x as number,
    y: overrides?.y ?? DEFAULT_ENEMY.props!.y as number,
    w: overrides?.w ?? DEFAULT_ENEMY.w!,
    h: overrides?.h ?? DEFAULT_ENEMY.h!,
    props: {
      ...DEFAULT_ENEMY.props,
      ...overrides?.props,
    }
  };
}

/**
 * Cria uma entidade bullet com valores default
 */
export function createDefaultBullet(overrides?: Partial<OrdaxEntity>): OrdaxEntity {
  return {
    id: overrides?.id || `bullet_${Date.now()}`,
    type: 'bullet',
    x: overrides?.x ?? DEFAULT_BULLET.props!.x as number,
    y: overrides?.y ?? DEFAULT_BULLET.props!.y as number,
    w: overrides?.w ?? DEFAULT_BULLET.w!,
    h: overrides?.h ?? DEFAULT_BULLET.h!,
    props: {
      ...DEFAULT_BULLET.props,
      ...overrides?.props,
    }
  };
}

/**
 * Cria uma entidade spawner com valores default
 */
export function createDefaultSpawner(overrides?: Partial<OrdaxEntity>): OrdaxEntity {
  return {
    id: overrides?.id || 'spawner1',
    type: 'spawner',
    x: overrides?.x ?? DEFAULT_SPAWNER.props!.x as number,
    y: overrides?.y ?? DEFAULT_SPAWNER.props!.y as number,
    w: overrides?.w ?? DEFAULT_SPAWNER.w!,
    h: overrides?.h ?? DEFAULT_SPAWNER.h!,
    props: {
      ...DEFAULT_SPAWNER.props,
      ...overrides?.props,
    }
  };
}
