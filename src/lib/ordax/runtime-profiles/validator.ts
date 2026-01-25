/**
 * Runtime Profile Validator
 * 
 * Valida se um runtimeSpec cumpre EXATAMENTE o perfil canônico de um gênero.
 * 
 * Diferente do constitutional validator (que valida pilares gerais),
 * este validador verifica se o jogo tem TUDO que o gênero específico exige.
 */

import type { RuntimeProfile, EntityProfile } from './topdown-shooter';
import type { OrdaxSpec } from '../types';

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
    components: Record<string, string[]>; // entityType -> missing components
    uiElements: string[];
    controls: string[];
    signals: string[];
  };
}

/**
 * Valida um runtimeSpec contra um perfil de gênero
 */
export function validateRuntimeAgainstProfile(
  runtimeSpec: OrdaxSpec,
  profile: RuntimeProfile
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

  // ============================================================================
  // 1. VALIDAR SISTEMAS
  // ============================================================================
  const runtimeSystems = runtimeSpec.systems || [];
  
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

  // ============================================================================
  // 2. VALIDAR ENTIDADES
  // ============================================================================
  const runtimeEntities = runtimeSpec.scene?.entities || [];
  const entityTypeMap = new Map<string, any[]>();
  
  // Agrupar entidades por tipo
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

    // ============================================================================
    // 3. VALIDAR COMPONENTES DA ENTIDADE
    // ============================================================================
    const sampleEntity = entitiesOfType[0]; // Validar primeira entidade como amostra
    const entityProps = sampleEntity.props || {};
    
    for (const requiredComponent of requiredEntity.requiredComponents) {
      // Verificar se componente existe (heurística: procurar por props relacionadas)
      const hasComponent = checkComponentPresence(
        requiredComponent.name,
        entityProps,
        sampleEntity
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

    // ============================================================================
    // 4. VALIDAR PROPS OBRIGATÓRIAS
    // ============================================================================
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
            fix: `Adicionar propriedade '${propName}' (${propReq.description})`
          });
        }
      }
    }
  }

  // ============================================================================
  // 5. VALIDAR UI
  // ============================================================================
  
  // StartScreen
  if (profile.requiredUI.startScreen.required) {
    const hasStartScreen = checkUIPresence(runtimeSpec, 'startScreen', 'StartScreen');
    if (!hasStartScreen) {
      missingElements.uiElements.push('StartScreen');
      violations.push({
        id: 'UI_START_SCREEN',
        level: 'CRITICAL',
        category: 'ui',
        message: 'StartScreen obrigatória ausente',
        expected: 'StartScreen com ' + profile.requiredUI.startScreen.mustHave.join(', '),
        actual: 'não encontrada',
        fix: 'Adicionar StartScreen à UI'
      });
    }
  }

  // HUD
  if (profile.requiredUI.hud.required) {
    const hasHUD = checkUIPresence(runtimeSpec, 'hud', 'HUD');
    if (!hasHUD) {
      missingElements.uiElements.push('HUD');
      violations.push({
        id: 'UI_HUD',
        level: 'CRITICAL',
        category: 'ui',
        message: 'HUD obrigatória ausente',
        expected: 'HUD exibindo ' + profile.requiredUI.hud.mustDisplay.join(', '),
        actual: 'não encontrada',
        fix: 'Adicionar HUD à UI'
      });
    }
  }

  // GameOverScreen
  if (profile.requiredUI.gameOverScreen.required) {
    const hasGameOver = checkUIPresence(runtimeSpec, 'gameOverScreen', 'GameOverScreen', 'GameOver');
    if (!hasGameOver) {
      missingElements.uiElements.push('GameOverScreen');
      violations.push({
        id: 'UI_GAME_OVER',
        level: 'CRITICAL',
        category: 'ui',
        message: 'GameOverScreen obrigatória ausente',
        expected: 'GameOverScreen com ' + profile.requiredUI.gameOverScreen.mustHave.join(', '),
        actual: 'não encontrada',
        fix: 'Adicionar GameOverScreen à UI'
      });
    }
  }

  // ============================================================================
  // 6. VALIDAR CONTROLES
  // ============================================================================
  
  // Movimento
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
      fix: `Adicionar controles de movimento: ${profile.requiredControls.movement.description}`
    });
  }

  // Ação (atirar)
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
      fix: `Adicionar controles de ação: ${profile.requiredControls.action.description}`
    });
  }

  // ============================================================================
  // 7. VALIDAR SINAIS
  // ============================================================================
  
  for (const requiredSignal of profile.requiredSignals) {
    if (!requiredSignal.required) continue;

    const hasSignal = checkSignalPresence(runtimeSpec, requiredSignal.name, requiredSignal.type);
    if (!hasSignal) {
      missingElements.signals.push(requiredSignal.name);
      violations.push({
        id: `SIG_${requiredSignal.name.toUpperCase()}`,
        level: 'SEVERE',
        category: 'signal',
        message: `Sinal obrigatório ausente: ${requiredSignal.name}`,
        expected: requiredSignal.description,
        actual: 'sinal não encontrado',
        fix: `Adicionar sinal '${requiredSignal.name}' (${requiredSignal.description})`
      });
    }
  }

  // ============================================================================
  // RESUMO
  // ============================================================================
  
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

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Verifica se um componente está presente na entidade (heurística)
 */
function checkComponentPresence(
  componentName: string,
  entityProps: Record<string, any>,
  entity: any
): boolean {
  const name = componentName.toLowerCase();
  
  // Transform: verifica x, y, rotation
  if (name === 'transform') {
    return 'x' in entityProps || 'y' in entityProps || 'x' in entity || 'y' in entity;
  }
  
  // Velocity: verifica vx, vy, speed
  if (name === 'velocity') {
    return 'vx' in entityProps || 'vy' in entityProps || 'speed' in entityProps;
  }
  
  // Health: verifica health, hp
  if (name === 'health') {
    return 'health' in entityProps || 'hp' in entityProps;
  }
  
  // Weapon: verifica weapon, fireRate, damage
  if (name === 'weapon') {
    return 'weapon' in entityProps || 'fireRate' in entityProps || 'damage' in entityProps;
  }
  
  // Collider: verifica w, h, radius, collider
  if (name === 'collider') {
    return 'w' in entityProps || 'h' in entityProps || 'radius' in entityProps || 'collider' in entityProps;
  }
  
  // AI: verifica ai, behavior, target
  if (name === 'ai') {
    return 'ai' in entityProps || 'behavior' in entityProps || 'target' in entityProps;
  }
  
  // Spawner: verifica spawner, spawnRate
  if (name === 'spawner') {
    return 'spawner' in entityProps || 'spawnRate' in entityProps;
  }
  
  // Lifetime: verifica lifetime, ttl
  if (name === 'lifetime') {
    return 'lifetime' in entityProps || 'ttl' in entityProps;
  }
  
  // Fallback: procura pelo nome do componente
  return name in entityProps;
}

/**
 * Verifica se UI está presente (heurística)
 */
function checkUIPresence(
  runtimeSpec: OrdaxSpec,
  ...possibleNames: string[]
): boolean {
  const specStr = JSON.stringify(runtimeSpec).toLowerCase();
  return possibleNames.some(name => specStr.includes(name.toLowerCase()));
}

/**
 * Verifica se controles estão presentes (heurística)
 */
function checkControlsPresence(
  runtimeSpec: OrdaxSpec,
  keys: string[]
): boolean {
  const specStr = JSON.stringify(runtimeSpec).toLowerCase();
  // Verifica se pelo menos uma das teclas está mencionada
  return keys.some(key => specStr.includes(key.toLowerCase()));
}

/**
 * Verifica se sinal está presente (heurística)
 */
function checkSignalPresence(
  runtimeSpec: OrdaxSpec,
  signalName: string,
  signalType: string
): boolean {
  const specStr = JSON.stringify(runtimeSpec).toLowerCase();
  const name = signalName.toLowerCase();
  const type = signalType.toLowerCase();
  
  // Procura por menções ao sinal
  return specStr.includes(name) || specStr.includes(type);
}

/**
 * Formata violações para exibição
 */
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

  if (result.summary.severe > 0) {
    output += `\nVIOLAÇÕES GRAVES:\n`;
    result.violations
      .filter(v => v.level === 'SEVERE')
      .forEach(v => {
        output += `\n[${v.id}] ${v.message}\n`;
        output += `  Fix: ${v.fix}\n`;
      });
  }

  output += `\n⚠️ Jogo não pode ser considerado funcional até corrigir violações CRÍTICAS.\n`;

  return output;
}

/**
 * Gera relatório de elementos faltantes
 */
export function generateMissingElementsReport(result: ProfileValidationResult): string {
  const { missingElements } = result;
  let output = `ELEMENTOS FALTANTES (${result.genre}):\n\n`;

  if (missingElements.systems.length > 0) {
    output += `Sistemas:\n`;
    missingElements.systems.forEach(s => output += `  - ${s}\n`);
    output += `\n`;
  }

  if (missingElements.entities.length > 0) {
    output += `Entidades:\n`;
    missingElements.entities.forEach(e => output += `  - ${e}\n`);
    output += `\n`;
  }

  if (Object.keys(missingElements.components).length > 0) {
    output += `Componentes:\n`;
    for (const [entity, components] of Object.entries(missingElements.components)) {
      output += `  ${entity}:\n`;
      components.forEach(c => output += `    - ${c}\n`);
    }
    output += `\n`;
  }

  if (missingElements.uiElements.length > 0) {
    output += `UI:\n`;
    missingElements.uiElements.forEach(u => output += `  - ${u}\n`);
    output += `\n`;
  }

  if (missingElements.controls.length > 0) {
    output += `Controles:\n`;
    missingElements.controls.forEach(c => output += `  - ${c}\n`);
    output += `\n`;
  }

  if (missingElements.signals.length > 0) {
    output += `Sinais:\n`;
    missingElements.signals.forEach(s => output += `  - ${s}\n`);
  }

  return output;
}
