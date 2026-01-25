/**
 * Top-Down Shooter Survival - Runtime Autofill
 * 
 * Preenche automaticamente elementos faltantes em um runtimeSpec
 * para garantir que o jogo seja jogável.
 * 
 * Usa os defaults canônicos e o perfil de validação para
 * adicionar apenas o que está faltando.
 */

import type { OrdaxSpec } from '../types';
import { TOPDOWN_SHOOTER_PROFILE } from '../runtime-profiles/topdown-shooter';
import { validateRuntimeAgainstProfile } from '../runtime-profiles/validator';
import {
  createDefaultPlayer,
  createDefaultEnemy,
  createDefaultBullet,
  createDefaultSpawner,
  DEFAULT_UI,
  DEFAULT_CONTROLS,
  DEFAULT_VISUAL,
  DEFAULT_AUDIO,
  DEFAULT_SCENE,
} from '../runtime-defaults/topdown-shooter';

// ============================================================================
// AUTOFILL FUNCTION
// ============================================================================

export interface AutofillResult {
  spec: OrdaxSpec;
  changes: string[];
  wasModified: boolean;
}

/**
 * Preenche automaticamente um runtimeSpec de top-down shooter
 * com valores default para elementos faltantes.
 * 
 * @param runtimeSpec - Runtime spec parcial ou completo
 * @returns Runtime spec completo e jogável
 */
export function autofillTopDownShooter(runtimeSpec: OrdaxSpec): AutofillResult {
  const changes: string[] = [];
  let spec = { ...runtimeSpec };
  
  // Validar primeiro para saber o que falta
  const validation = validateRuntimeAgainstProfile(spec, TOPDOWN_SHOOTER_PROFILE);
  
  if (validation.isValid) {
    return {
      spec,
      changes: [],
      wasModified: false
    };
  }
  
  // ============================================================================
  // 1. ADICIONAR SISTEMAS FALTANTES
  // ============================================================================
  
  if (!spec.systems) {
    spec.systems = [];
  }
  
  for (const system of validation.missingElements.systems) {
    if (!spec.systems.includes(system)) {
      spec.systems.push(system);
      changes.push(`✅ Sistema adicionado: ${system}`);
    }
  }
  
  // ============================================================================
  // 2. ADICIONAR ENTIDADES FALTANTES
  // ============================================================================
  
  if (!spec.scene) {
    spec.scene = {
      gravity: DEFAULT_SCENE.gravity,
      entities: []
    };
    changes.push(`✅ Scene criada com gravity default`);
  }
  
  if (!spec.scene.entities) {
    spec.scene.entities = [];
  }
  
  // Agrupar entidades existentes por tipo
  const existingTypes = new Set(spec.scene.entities.map(e => e.type));
  
  // Adicionar player se não existir
  if (validation.missingElements.entities.includes('player')) {
    const player = createDefaultPlayer();
    spec.scene.entities.push(player);
    changes.push(`✅ Entidade adicionada: player (x=${player.x}, y=${player.y})`);
  }
  
  // Adicionar enemy se não existir
  if (validation.missingElements.entities.includes('enemy')) {
    const enemy = createDefaultEnemy({ x: 200, y: 100 });
    spec.scene.entities.push(enemy);
    changes.push(`✅ Entidade adicionada: enemy (x=${enemy.x}, y=${enemy.y})`);
  }
  
  // Adicionar bullet template se não existir
  if (validation.missingElements.entities.includes('bullet')) {
    const bullet = createDefaultBullet({ id: 'bullet_template' });
    spec.scene.entities.push(bullet);
    changes.push(`✅ Entidade adicionada: bullet (template)`);
  }
  
  // Adicionar spawner se não existir
  if (validation.missingElements.entities.includes('spawner')) {
    const spawner = createDefaultSpawner();
    spec.scene.entities.push(spawner);
    changes.push(`✅ Entidade adicionada: spawner (x=${spawner.x}, y=${spawner.y})`);
  }
  
  // ============================================================================
  // 3. ADICIONAR COMPONENTES E PROPS FALTANTES
  // ============================================================================
  
  for (const [entityType, missingComponents] of Object.entries(validation.missingElements.components)) {
    const entities = spec.scene.entities.filter(e => e.type === entityType);
    
    if (entities.length === 0) continue;
    
    for (const entity of entities) {
      if (!entity.props) {
        entity.props = {};
      }
      
      // Adicionar props default baseado no tipo
      let defaultProps: Record<string, unknown> = {};
      
      switch (entityType) {
        case 'player':
          defaultProps = createDefaultPlayer().props!;
          break;
        case 'enemy':
          defaultProps = createDefaultEnemy().props!;
          break;
        case 'bullet':
          defaultProps = createDefaultBullet().props!;
          break;
        case 'spawner':
          defaultProps = createDefaultSpawner().props!;
          break;
      }
      
      // Adicionar apenas props que estão faltando
      let propsAdded = 0;
      for (const [key, value] of Object.entries(defaultProps)) {
        if (!(key in entity.props)) {
          entity.props[key] = value;
          propsAdded++;
        }
      }
      
      if (propsAdded > 0) {
        changes.push(`✅ Props adicionadas em ${entityType} (${entity.id}): ${propsAdded} propriedades`);
      }
    }
  }
  
  // ============================================================================
  // 4. ADICIONAR VISUAL DEFAULT
  // ============================================================================
  
  if (!spec.visual) {
    spec.visual = DEFAULT_VISUAL;
    changes.push(`✅ Visual theme adicionado (starfield + nebula)`);
  } else {
    if (!spec.visual.theme) {
      spec.visual.theme = DEFAULT_VISUAL.theme;
      changes.push(`✅ Visual theme colors adicionadas`);
    }
    
    if (!spec.visual.background) {
      spec.visual.background = DEFAULT_VISUAL.background;
      changes.push(`✅ Background layers adicionadas`);
    }
  }
  
  // ============================================================================
  // 5. ADICIONAR AUDIO DEFAULT (OPCIONAL)
  // ============================================================================
  
  if (!spec.audio) {
    spec.audio = {
      sounds: {
        shoot: 'laser.mp3',
        collision: 'hit.mp3',
        gameOver: 'gameover.mp3',
      }
    };
    changes.push(`✅ Audio config adicionada (sons)`);
  }
  
  // ============================================================================
  // 6. INJETAR UI DEFAULT
  // ============================================================================
  
  // Nota: UI é geralmente injetada via código, não via spec
  // Mas podemos adicionar metadados para referência
  if (!spec.scene.entities.some(e => e.type === 'ui' || e.id.includes('ui'))) {
    // Adicionar entidade de metadados de UI
    spec.scene.entities.push({
      id: 'ui_metadata',
      type: 'ui',
      x: 0,
      y: 0,
      w: 0,
      h: 0,
      props: {
        startScreen: DEFAULT_UI.startScreen,
        hud: DEFAULT_UI.hud,
        gameOverScreen: DEFAULT_UI.gameOverScreen,
      }
    });
    changes.push(`✅ UI metadata adicionada (StartScreen, HUD, GameOverScreen)`);
  }
  
  // ============================================================================
  // 7. INJETAR CONTROLES DEFAULT
  // ============================================================================
  
  // Adicionar entidade de metadados de controles
  if (!spec.scene.entities.some(e => e.type === 'controls' || e.id.includes('controls'))) {
    spec.scene.entities.push({
      id: 'controls_metadata',
      type: 'controls',
      x: 0,
      y: 0,
      w: 0,
      h: 0,
      props: DEFAULT_CONTROLS
    });
    changes.push(`✅ Controls metadata adicionados (WASD + SPACE)`);
  }
  
  // ============================================================================
  // 8. GARANTIR GRAVITY CORRETO
  // ============================================================================
  
  if (!spec.scene.gravity || (spec.scene.gravity.x !== 0 || spec.scene.gravity.y !== 0)) {
    spec.scene.gravity = DEFAULT_SCENE.gravity;
    changes.push(`✅ Gravity ajustado para top-down (x=0, y=0)`);
  }
  
  return {
    spec,
    changes,
    wasModified: changes.length > 0
  };
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Verifica se um runtime precisa de autofill
 */
export function needsAutofill(runtimeSpec: OrdaxSpec): boolean {
  const validation = validateRuntimeAgainstProfile(runtimeSpec, TOPDOWN_SHOOTER_PROFILE);
  return !validation.isValid && validation.summary.critical > 0;
}

/**
 * Autofill com validação pós-processamento
 */
export function autofillAndValidate(runtimeSpec: OrdaxSpec): {
  spec: OrdaxSpec;
  changes: string[];
  wasModified: boolean;
  isValid: boolean;
  remainingViolations: number;
} {
  const result = autofillTopDownShooter(runtimeSpec);
  const validation = validateRuntimeAgainstProfile(result.spec, TOPDOWN_SHOOTER_PROFILE);
  
  return {
    ...result,
    isValid: validation.isValid,
    remainingViolations: validation.summary.critical
  };
}

/**
 * Gera relatório de autofill
 */
export function generateAutofillReport(result: AutofillResult): string {
  if (!result.wasModified) {
    return '✅ Runtime já está completo. Nenhuma modificação necessária.';
  }
  
  let report = `🔧 AUTOFILL APLICADO\n\n`;
  report += `Total de mudanças: ${result.changes.length}\n\n`;
  
  result.changes.forEach(change => {
    report += `${change}\n`;
  });
  
  return report;
}
