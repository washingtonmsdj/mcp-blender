/**
 * Aplica um semantic patch a um RuntimeSpec
 */

import type { RuntimeSpec } from '../types';
import type { SemanticPatch } from './index';

export function applyRemixPatch(
  baseSpec: RuntimeSpec,
  patch: SemanticPatch
): RuntimeSpec {
  const remixed: RuntimeSpec = JSON.parse(JSON.stringify(baseSpec));
  
  // Aplicar mudanças em entities
  if (patch.entities) {
    if (!remixed.entities) remixed.entities = {};
    
    // Adicionar novas entities
    if (patch.entities.add) {
      Object.assign(remixed.entities, patch.entities.add);
    }
    
    // Remover entities
    if (patch.entities.remove) {
      patch.entities.remove.forEach(key => {
        delete remixed.entities![key];
      });
    }
    
    // Modificar entities existentes
    if (patch.entities.modify) {
      Object.keys(patch.entities.modify).forEach(key => {
        if (remixed.entities![key]) {
          remixed.entities![key] = {
            ...remixed.entities![key],
            ...patch.entities!.modify![key]
          };
        }
      });
    }
  }
  
  // Aplicar mudanças em spawners
  if (patch.spawners) {
    if (!remixed.spawners) remixed.spawners = {};
    
    // Adicionar novos spawners
    if (patch.spawners.add) {
      Object.assign(remixed.spawners, patch.spawners.add);
    }
    
    // Remover spawners
    if (patch.spawners.remove) {
      patch.spawners.remove.forEach(key => {
        delete remixed.spawners![key];
      });
    }
    
    // Modificar spawners existentes
    if (patch.spawners.modify) {
      Object.keys(patch.spawners.modify).forEach(key => {
        if (remixed.spawners![key]) {
          remixed.spawners![key] = {
            ...remixed.spawners![key],
            ...patch.spawners!.modify![key]
          };
        }
      });
    }
  }
  
  // Aplicar mudanças em rules
  if (patch.rules) {
    if (!remixed.rules) remixed.rules = {};
    
    if (patch.rules.winCondition) {
      remixed.rules.winCondition = patch.rules.winCondition;
    }
    
    if (patch.rules.loseCondition) {
      remixed.rules.loseCondition = patch.rules.loseCondition;
    }
  }
  
  // Aplicar mudanças em UI
  if (patch.ui) {
    if (!remixed.ui) remixed.ui = {};
    
    if (patch.ui.hud) {
      remixed.ui.hud = {
        ...remixed.ui.hud,
        ...patch.ui.hud
      };
    }
  }
  
  return remixed;
}
