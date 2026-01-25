/**
 * Top-Down Shooter Survival - Runtime Profile
 * 
 * Perfil canônico que define EXATAMENTE o que um top-down shooter survival
 * funcional DEVE ter para ser considerado jogável.
 * 
 * Este é o contrato mínimo para o gênero.
 */

export interface RuntimeProfile {
  genre: string;
  description: string;
  requiredSystems: string[];
  requiredEntities: EntityProfile[];
  requiredUI: UIProfile;
  requiredControls: ControlProfile;
  requiredSignals: SignalProfile[];
  requiredLifecycle: LifecycleProfile;
}

export interface EntityProfile {
  type: string;
  description: string;
  requiredComponents: ComponentProfile[];
  requiredProps?: Record<string, ComponentPropRequirement>;
}

export interface ComponentProfile {
  name: string;
  description: string;
  critical: boolean; // Se true, ausência é CRÍTICA
}

export interface ComponentPropRequirement {
  type: 'number' | 'boolean' | 'string' | 'object';
  required: boolean;
  description: string;
}

export interface UIProfile {
  startScreen: {
    required: boolean;
    mustHave: string[]; // Ex: ["title", "startButton"]
  };
  hud: {
    required: boolean;
    mustDisplay: string[]; // Ex: ["health", "score", "ammo"]
  };
  gameOverScreen: {
    required: boolean;
    mustHave: string[]; // Ex: ["finalScore", "restartButton"]
  };
}

export interface ControlProfile {
  movement: {
    keys: string[]; // Ex: ["W", "A", "S", "D"]
    description: string;
  };
  action: {
    keys: string[]; // Ex: ["SPACE", "MOUSE_LEFT"]
    description: string;
  };
  pause?: {
    keys: string[];
    description: string;
  };
}

export interface SignalProfile {
  name: string;
  type: 'player_health' | 'score' | 'timer' | 'wave' | 'ammo';
  required: boolean;
  description: string;
}

export interface LifecycleProfile {
  startCondition: string;
  loseCondition: string;
  winCondition?: string; // Opcional para survival
  restartMechanism: string;
}

/**
 * PERFIL CANÔNICO: TOP-DOWN SHOOTER SURVIVAL
 */
export const TOPDOWN_SHOOTER_PROFILE: RuntimeProfile = {
  genre: "topdown-shooter-survival",
  description: "Top-down shooter onde o jogador sobrevive ondas de inimigos, atirando e se movendo em 360°",

  // ============================================================================
  // SISTEMAS OBRIGATÓRIOS
  // ============================================================================
  requiredSystems: [
    "PhysicsSystem",      // Movimento do jogador e inimigos
    "CollisionSystem",    // Detecção de colisões (balas, inimigos, pickups)
    "AISystem",           // Comportamento de inimigos
    "SpawnerSystem",      // Geração de ondas de inimigos
    "ScoreSystem",        // Pontuação (kills, sobrevivência)
    "TimerSystem",        // Tempo de sobrevivência
    "UISystem",           // Interface (HUD, telas)
  ],

  // ============================================================================
  // ENTIDADES OBRIGATÓRIAS
  // ============================================================================
  requiredEntities: [
    // PLAYER
    {
      type: "player",
      description: "Jogador controlável com movimento 360° e capacidade de atirar",
      requiredComponents: [
        { name: "Transform", description: "Posição e rotação", critical: true },
        { name: "Velocity", description: "Movimento", critical: true },
        { name: "Health", description: "Vida do jogador", critical: true },
        { name: "Weapon", description: "Arma/capacidade de atirar", critical: true },
        { name: "Collider", description: "Detecção de colisão", critical: true },
      ],
      requiredProps: {
        health: { type: 'number', required: true, description: "Vida inicial (ex: 100)" },
        speed: { type: 'number', required: true, description: "Velocidade de movimento (ex: 200)" },
        fireRate: { type: 'number', required: false, description: "Taxa de tiro (ex: 0.2)" },
      }
    },

    // ENEMY
    {
      type: "enemy",
      description: "Inimigo que persegue e ataca o jogador",
      requiredComponents: [
        { name: "Transform", description: "Posição", critical: true },
        { name: "Velocity", description: "Movimento", critical: true },
        { name: "Health", description: "Vida do inimigo", critical: true },
        { name: "AI", description: "Comportamento (perseguir jogador)", critical: true },
        { name: "Collider", description: "Detecção de colisão", critical: true },
      ],
      requiredProps: {
        health: { type: 'number', required: true, description: "Vida do inimigo (ex: 50)" },
        speed: { type: 'number', required: true, description: "Velocidade (ex: 100)" },
        damage: { type: 'number', required: true, description: "Dano ao jogador (ex: 10)" },
      }
    },

    // BULLET
    {
      type: "bullet",
      description: "Projétil disparado pelo jogador",
      requiredComponents: [
        { name: "Transform", description: "Posição", critical: true },
        { name: "Velocity", description: "Movimento", critical: true },
        { name: "Collider", description: "Detecção de colisão", critical: true },
        { name: "Lifetime", description: "Tempo de vida", critical: false },
      ],
      requiredProps: {
        speed: { type: 'number', required: true, description: "Velocidade da bala (ex: 400)" },
        damage: { type: 'number', required: true, description: "Dano ao inimigo (ex: 25)" },
      }
    },

    // SPAWNER
    {
      type: "spawner",
      description: "Gerador de ondas de inimigos",
      requiredComponents: [
        { name: "Transform", description: "Posição de spawn", critical: true },
        { name: "Spawner", description: "Lógica de spawn", critical: true },
      ],
      requiredProps: {
        spawnRate: { type: 'number', required: true, description: "Taxa de spawn (ex: 2.0)" },
        maxEnemies: { type: 'number', required: false, description: "Máximo de inimigos simultâneos" },
      }
    },
  ],

  // ============================================================================
  // UI OBRIGATÓRIA
  // ============================================================================
  requiredUI: {
    startScreen: {
      required: true,
      mustHave: [
        "title",           // Título do jogo
        "startButton",     // Botão para iniciar
        "instructions",    // Instruções básicas (WASD + SPACE)
      ]
    },
    hud: {
      required: true,
      mustDisplay: [
        "health",          // Vida do jogador (barra ou número)
        "score",           // Pontuação (kills)
        "timer",           // Tempo de sobrevivência
        "wave",            // Onda atual (opcional mas recomendado)
      ]
    },
    gameOverScreen: {
      required: true,
      mustHave: [
        "finalScore",      // Pontuação final
        "survivalTime",    // Tempo sobrevivido
        "restartButton",   // Botão para reiniciar
        "highScore",       // Melhor pontuação (persistida)
      ]
    }
  },

  // ============================================================================
  // CONTROLES OBRIGATÓRIOS
  // ============================================================================
  requiredControls: {
    movement: {
      keys: ["W", "A", "S", "D"],
      description: "Movimento em 8 direções (WASD)"
    },
    action: {
      keys: ["SPACE", "MOUSE_LEFT"],
      description: "Atirar (SPACE ou clique esquerdo)"
    },
    pause: {
      keys: ["ESC", "P"],
      description: "Pausar jogo (opcional)"
    }
  },

  // ============================================================================
  // SINAIS OBRIGATÓRIOS
  // ============================================================================
  requiredSignals: [
    {
      name: "player_health",
      type: "player_health",
      required: true,
      description: "Vida do jogador (0 = game over)"
    },
    {
      name: "score",
      type: "score",
      required: true,
      description: "Pontuação (kills, tempo)"
    },
    {
      name: "timer",
      type: "timer",
      required: true,
      description: "Tempo de sobrevivência"
    },
    {
      name: "wave",
      type: "wave",
      required: false,
      description: "Onda atual de inimigos"
    }
  ],

  // ============================================================================
  // LIFECYCLE OBRIGATÓRIO
  // ============================================================================
  requiredLifecycle: {
    startCondition: "Jogador clica em 'Start' na StartScreen",
    loseCondition: "player.health <= 0",
    winCondition: undefined, // Survival não tem vitória
    restartMechanism: "Jogador clica em 'Restart' na GameOverScreen"
  }
};

/**
 * Helper: Verifica se um sistema está na lista de obrigatórios
 */
export function isSystemRequired(systemName: string): boolean {
  return TOPDOWN_SHOOTER_PROFILE.requiredSystems.includes(systemName);
}

/**
 * Helper: Verifica se uma entidade está na lista de obrigatórias
 */
export function isEntityRequired(entityType: string): boolean {
  return TOPDOWN_SHOOTER_PROFILE.requiredEntities.some(e => e.type === entityType);
}

/**
 * Helper: Obtém perfil de uma entidade
 */
export function getEntityProfile(entityType: string): EntityProfile | undefined {
  return TOPDOWN_SHOOTER_PROFILE.requiredEntities.find(e => e.type === entityType);
}

/**
 * Helper: Lista todos os componentes críticos de uma entidade
 */
export function getCriticalComponents(entityType: string): string[] {
  const profile = getEntityProfile(entityType);
  if (!profile) return [];
  return profile.requiredComponents
    .filter(c => c.critical)
    .map(c => c.name);
}
