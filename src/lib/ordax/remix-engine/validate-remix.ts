/**
 * Valida que um remix não quebrou o jogo
 */

import type { RuntimeSpec } from '../types';

export interface RemixValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function validateRemix(remixedSpec: RuntimeSpec): RemixValidation {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // 1. Verificar que tem player
  if (!remixedSpec.entities?.player) {
    errors.push('Player entity é obrigatória');
  }
  
  // 2. Verificar que tem pelo menos um inimigo ou coletável
  const hasEnemies = Object.values(remixedSpec.entities || {}).some(
    (e: any) => e.damage || e.aiType
  );
  const hasCollectibles = Object.values(remixedSpec.entities || {}).some(
    (e: any) => e.scoreValue || e.healAmount
  );
  
  if (!hasEnemies && !hasCollectibles) {
    warnings.push('Jogo não tem inimigos nem coletáveis');
  }
  
  // 3. Verificar que tem spawners
  if (!remixedSpec.spawners || Object.keys(remixedSpec.spawners).length === 0) {
    warnings.push('Jogo não tem spawners configurados');
  }
  
  // 4. Verificar que tem rules
  if (!remixedSpec.rules?.winCondition) {
    warnings.push('Condição de vitória não definida');
  }
  
  if (!remixedSpec.rules?.loseCondition) {
    warnings.push('Condição de derrota não definida');
  }
  
  // 5. Verificar que tem UI
  if (!remixedSpec.ui?.hud) {
    warnings.push('HUD não configurada');
  }
  
  // 6. Verificar valores numéricos válidos
  Object.entries(remixedSpec.entities || {}).forEach(([key, entity]: [string, any]) => {
    if (entity.speed && (entity.speed <= 0 || entity.speed > 1000)) {
      warnings.push(`${key}: velocidade fora do range (0-1000)`);
    }
    
    if (entity.health && entity.health <= 0) {
      errors.push(`${key}: health deve ser > 0`);
    }
    
    if (entity.damage && entity.damage < 0) {
      errors.push(`${key}: damage não pode ser negativo`);
    }
  });
  
  // 7. Verificar spawners válidos
  Object.entries(remixedSpec.spawners || {}).forEach(([key, spawner]: [string, any]) => {
    if (!spawner.entityType) {
      errors.push(`${key}: spawner sem entityType`);
    }
    
    if (spawner.interval && spawner.interval <= 0) {
      errors.push(`${key}: interval deve ser > 0`);
    }
    
    if (spawner.maxActive && spawner.maxActive <= 0) {
      errors.push(`${key}: maxActive deve ser > 0`);
    }
  });
  
  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}
