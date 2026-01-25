/**
 * Runtime Profile Validator for Deno (Supabase Functions)
 * 
 * Versão adaptada do validador de perfil para uso em Deno Edge Functions.
 * Valida se um runtimeSpec cumpre os requisitos do perfil de gênero.
 */

// ============================================================================
// TYPES
// ============================================================================

export type ProfileViolationLevel = 'CRITICAL' | 'SEVERE' | 'MINOR';

export interface ProfileViolation {
  id: string;
  level: ProfileViolationLevel;
  category: 'system' | 'entity' | 'component' | 'ui' | 'control' | 'signal' | 'lifecycle';
  message: string;
  expected: string;
  actual: string;
  fix: string;
}

export interface ProfileValidationResult {
  isValid: boolean;
  genre: string;
  violations: ProfileViolation[];
  summary: {
    critical: number;
    severe: number;
    minor: number;
  };
  missingElements: {
    systems: string[];
    entities: string[];
    components: Record<string, string[]>;
    uiElements: string[];
    controls: string[];
    signals: string[];
  };
}

export interface OrdaxSpec {
  gameType: string;
  title: string;
  description: string;
  systems: string[];
  scene: {
    gravity: { x: number; y: number };
    entities: Array<{
      id: string;
      type: string;
      x: number;
      y: number;
      w: number;
      h: number;
      props?: Record<string, unknown>;
    }>;
  };
}

// ============================================================================
// TOP-DOWN SHOOTER PROFILE
// ============================================================================

const TOPDOWN_SHOOTER_PROFILE = {
  genre: "topdown-shooter-survival",
  
  requiredSystems: [
    "PhysicsSystem",
    "CollisionSystem",
    "AISystem",
    "SpawnerSystem",
    "ScoreSystem",
    "TimerSystem",
    "UISystem"
  ],
  
  requiredEntities: [
    {
      type: "player",
      requiredComponents: [
        { name: "Transform", critical: true },
        { name: "Velocity", critical: true },
        { name: "Health", critical: true },
        { name: "Weapon", critical: true },
        { name: "Collider", critical: true },
      ],
      requiredProps: {
        health: { type: 'number', required: true },
        speed: { type: 'number', required: true },
      }
    },
    {
      type: "enemy",
      requiredComponents: [
        { name: "Transform", critical: true },
        { name: "Velocity", critical: true },
        { name: "Health", critical: true },
        { name: "AI", critical: true },
        { name: "Collider", critical: true },
      ],
      requiredProps: {
        health: { type: 'number', required: true },
        speed: { type: 'number', required: true },
        damage: { type: 'number', required: true },
      }
    },
    {
      type: "bullet",
      requiredComponents: [
        { name: "Transform", critical: true },
        { name: "Velocity", critical: true },
        { name: "Collider", critical: true },
      ],
      requiredProps: {
        speed: { type: 'number', required: true },
        damage: { type: 'number', required: true },
      }
    },
    {
      type: "spawner",
      requiredComponents: [
        { name: "Transform", critical: true },
        { name: "Spawner", critical: true },
      ],
      requiredProps: {
        spawnRate: { type: 'number', required: true },
      }
    },
  ],
  
  requiredUI: {
    startScreen: { required: true },
    hud: { required: true },
    gameOverScreen: { required: true },
  },
  
  requiredControls: {
    movement: { keys: ["W", "A", "S", "D"] },
    action: { keys: ["SPACE", "MOUSE_LEFT"] },
  },
  
  requiredSignals: [
    { name: "player_health", required: true },
    { name: "score", required: true },
    { name: "timer", required: true },
  ],
};

// ============================================================================
// VALIDATOR
// ============================================================================

function checkComponentPresence(
  componentName: string,
  entityProps: Record<string, unknown>
): boolean {
  const name = componentName.toLowerCase();
  
  if (name === 'transform') {
    return 'x' in entityProps || 'y' in entityProps;
  }
  
  if (name === 'velocity') {
    return 'vx' in entityProps || 'vy' in entityProps || 'speed' in entityProps;
  }
  
  if (name === 'health') {
    return 'health' in entityProps || 'hp' in entityProps;
  }
  
  if (name === 'weapon') {
    return 'weapon' in entityProps || 'fireRate' in entityProps || 'damage' in entityProps;
  }
  
  if (name === 'collider') {
    return 'w' in entityProps || 'h' in entityProps || 'radius' in entityProps || 'collider' in entityProps;
  }
  
  if (name === 'ai') {
    return 'ai' in entityProps || 'behavior' in entityProps || 'target' in entityProps;
  }
  
  if (name === 'spawner') {
    return 'spawner' in entityProps || 'spawnRate' in entityProps;
  }
  
  return name in entityProps;
}

function checkUIPresence(runtimeSpec: OrdaxSpec, ...possibleNames: string[]): boolean {
  const specStr = JSON.stringify(runtimeSpec).toLowerCase();
  return possibleNames.some(name => specStr.includes(name.toLowerCase()));
}

function checkControlsPresence(runtimeSpec: OrdaxSpec, keys: string[]): boolean {
  const specStr = JSON.stringify(runtimeSpec).toLowerCase();
  return keys.some(key => specStr.includes(key.toLowerCase()));
}

function checkSignalPresence(runtimeSpec: OrdaxSpec, signalName: string): boolean {
  const specStr = JSON.stringify(runtimeSpec).toLowerCase();
  const name = signalName.toLowerCase();
  return specStr.includes(name);
}

export function validateRuntimeAgainstProfile(
  runtimeSpec: OrdaxSpec
): ProfileValidationResult {
  const violations: ProfileViolation[] = [];
  const missingElements = {
    systems: [] as string[],
    entities: [] as string[],
    components: {} as Record<string, string[]>,
    uiElements: [] as string[],
    controls: [] as string[],
    signals: [] as string[],
  };

  // Validar apenas se for top-down shooter
  if (runtimeSpec.gameType !== 'topdown' && runtimeSpec.gameType !== 'shooter') {
    return {
      isValid: true,
      genre: runtimeSpec.gameType,
      violations: [],
      summary: { critical: 0, severe: 0, minor: 0 },
      missingElements,
    };
  }

  const profile = TOPDOWN_SHOOTER_PROFILE;
  const runtimeSystems = runtimeSpec.systems || [];
  
  // 1. Validar Sistemas
  for (const requiredSystem of profile.requiredSystems) {
    if (!runtimeSystems.includes(requiredSystem)) {
      missingElements.systems.push(requiredSystem);
      violations.push({
        id: `SYS_${requiredSystem.toUpperCase()}`,
        level: 'CRITICAL',
        category: 'system',
        message: `Sistema obrigatório ausente: ${requiredSystem}`,
        expected: requiredSystem,
        actual: 'não encontrado',
        fix: `Adicionar ${requiredSystem} à lista de sistemas`
      });
    }
  }

  // 2. Validar Entidades
  const runtimeEntities = runtimeSpec.scene?.entities || [];
  const entityTypeMap = new Map<string, any[]>();
  
  for (const entity of runtimeEntities) {
    const type = entity.type || 'unknown';
    if (!entityTypeMap.has(type)) {
      entityTypeMap.set(type, []);
    }
    entityTypeMap.get(type)!.push(entity);
  }

  for (const requiredEntity of profile.requiredEntities) {
    const entitiesOfType = entityTypeMap.get(requiredEntity.type) || [];
    
    if (entitiesOfType.length === 0) {
      missingElements.entities.push(requiredEntity.type);
      violations.push({
        id: `ENT_${requiredEntity.type.toUpperCase()}`,
        level: 'CRITICAL',
        category: 'entity',
        message: `Entidade obrigatória ausente: ${requiredEntity.type}`,
        expected: `Pelo menos 1 entidade do tipo '${requiredEntity.type}'`,
        actual: '0 entidades encontradas',
        fix: `Adicionar entidade do tipo '${requiredEntity.type}' à scene.entities`
      });
      continue;
    }

    // 3. Validar Componentes
    const sampleEntity = entitiesOfType[0];
    const entityProps = sampleEntity.props || {};
    
    for (const requiredComponent of requiredEntity.requiredComponents) {
      const hasComponent = checkComponentPresence(
        requiredComponent.name,
        entityProps
      );

      if (!hasComponent && requiredComponent.critical) {
        if (!missingElements.components[requiredEntity.type]) {
          missingElements.components[requiredEntity.type] = [];
        }
        missingElements.components[requiredEntity.type].push(requiredComponent.name);

        violations.push({
          id: `COMP_${requiredEntity.type.toUpperCase()}_${requiredComponent.name.toUpperCase()}`,
          level: 'CRITICAL',
          category: 'component',
          message: `Componente crítico ausente em '${requiredEntity.type}': ${requiredComponent.name}`,
          expected: `${requiredComponent.name} em ${requiredEntity.type}`,
          actual: 'componente não encontrado',
          fix: `Adicionar ${requiredComponent.name} à entidade '${requiredEntity.type}'`
        });
      }
    }

    // 4. Validar Props
    if (requiredEntity.requiredProps) {
      for (const [propName, propReq] of Object.entries(requiredEntity.requiredProps)) {
        if (propReq.required && !(propName in entityProps)) {
          violations.push({
            id: `PROP_${requiredEntity.type.toUpperCase()}_${propName.toUpperCase()}`,
            level: 'SEVERE',
            category: 'component',
            message: `Propriedade obrigatória ausente em '${requiredEntity.type}': ${propName}`,
            expected: `${propName}: ${propReq.type}`,
            actual: 'propriedade não encontrada',
            fix: `Adicionar propriedade '${propName}' à entidade '${requiredEntity.type}'`
          });
        }
      }
    }
  }

  // 5. Validar UI
  if (profile.requiredUI.startScreen.required) {
    const hasStartScreen = checkUIPresence(runtimeSpec, 'startScreen', 'StartScreen');
    if (!hasStartScreen) {
      missingElements.uiElements.push('StartScreen');
      violations.push({
        id: 'UI_START_SCREEN',
        level: 'CRITICAL',
        category: 'ui',
        message: 'StartScreen obrigatória ausente',
        expected: 'StartScreen com title, startButton, instructions',
        actual: 'não encontrada',
        fix: 'Adicionar StartScreen à UI'
      });
    }
  }

  if (profile.requiredUI.hud.required) {
    const hasHUD = checkUIPresence(runtimeSpec, 'hud', 'HUD');
    if (!hasHUD) {
      missingElements.uiElements.push('HUD');
      violations.push({
        id: 'UI_HUD',
        level: 'CRITICAL',
        category: 'ui',
        message: 'HUD obrigatória ausente',
        expected: 'HUD exibindo health, score, timer',
        actual: 'não encontrada',
        fix: 'Adicionar HUD à UI'
      });
    }
  }

  if (profile.requiredUI.gameOverScreen.required) {
    const hasGameOver = checkUIPresence(runtimeSpec, 'gameOverScreen', 'GameOverScreen', 'GameOver');
    if (!hasGameOver) {
      missingElements.uiElements.push('GameOverScreen');
      violations.push({
        id: 'UI_GAME_OVER',
        level: 'CRITICAL',
        category: 'ui',
        message: 'GameOverScreen obrigatória ausente',
        expected: 'GameOverScreen com finalScore, survivalTime, restartButton',
        actual: 'não encontrada',
        fix: 'Adicionar GameOverScreen à UI'
      });
    }
  }

  // 6. Validar Controles
  const hasMovementControls = checkControlsPresence(
    runtimeSpec,
    profile.requiredControls.movement.keys
  );
  if (!hasMovementControls) {
    missingElements.controls.push('movement');
    violations.push({
      id: 'CTRL_MOVEMENT',
      level: 'CRITICAL',
      category: 'control',
      message: 'Controles de movimento ausentes',
      expected: profile.requiredControls.movement.keys.join(', '),
      actual: 'controles não encontrados',
      fix: `Adicionar controles de movimento: WASD`
    });
  }

  const hasActionControls = checkControlsPresence(
    runtimeSpec,
    profile.requiredControls.action.keys
  );
  if (!hasActionControls) {
    missingElements.controls.push('action');
    violations.push({
      id: 'CTRL_ACTION',
      level: 'CRITICAL',
      category: 'control',
      message: 'Controles de ação ausentes',
      expected: profile.requiredControls.action.keys.join(', '),
      actual: 'controles não encontrados',
      fix: `Adicionar controles de ação: SPACE ou MOUSE_LEFT`
    });
  }

  // 7. Validar Sinais
  for (const requiredSignal of profile.requiredSignals) {
    if (!requiredSignal.required) continue;

    const hasSignal = checkSignalPresence(runtimeSpec, requiredSignal.name);
    if (!hasSignal) {
      missingElements.signals.push(requiredSignal.name);
      violations.push({
        id: `SIG_${requiredSignal.name.toUpperCase()}`,
        level: 'SEVERE',
        category: 'signal',
        message: `Sinal obrigatório ausente: ${requiredSignal.name}`,
        expected: requiredSignal.name,
        actual: 'sinal não encontrado',
        fix: `Adicionar sinal '${requiredSignal.name}' ao jogo`
      });
    }
  }

  const summary = {
    critical: violations.filter(v => v.level === 'CRITICAL').length,
    severe: violations.filter(v => v.level === 'SEVERE').length,
    minor: violations.filter(v => v.level === 'MINOR').length,
  };

  return {
    isValid: summary.critical === 0,
    genre: profile.genre,
    violations,
    summary,
    missingElements,
  };
}

export function formatProfileViolations(result: ProfileValidationResult): string {
  if (result.isValid) {
    return `✅ Runtime válido para gênero '${result.genre}'`;
  }

  let output = `❌ PROFILE VALIDATION FAILED: ${result.genre}\n\n`;
  
  output += `Resumo:\n`;
  output += `- Críticas: ${result.summary.critical}\n`;
  output += `- Graves: ${result.summary.severe}\n`;
  output += `- Menores: ${result.summary.minor}\n\n`;

  if (result.summary.critical > 0) {
    output += `VIOLAÇÕES CRÍTICAS:\n`;
    result.violations
      .filter(v => v.level === 'CRITICAL')
      .forEach(v => {
        output += `\n[${v.id}] ${v.category.toUpperCase()}\n`;
        output += `  Problema: ${v.message}\n`;
        output += `  Esperado: ${v.expected}\n`;
        output += `  Atual: ${v.actual}\n`;
        output += `  Fix: ${v.fix}\n`;
      });
  }

  return output;
}
