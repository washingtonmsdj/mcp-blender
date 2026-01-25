/**
 * Gera um semantic patch baseado no intent do usuário
 * FASE 9: Agora usa parseRemixIntent + composePatches
 */

import type { RuntimeSpec } from '../types';
import type { SemanticPatch, RemixChange } from './index';
import { parseRemixIntent, resolveConflicts, formatIntentSummary } from './parse-remix-intent';
import { composePatches } from './compose-patches';

export function generateRemixPatch(
  baseSpec: RuntimeSpec,
  userIntent: string
): { patch: SemanticPatch; changes: RemixChange[]; parsedIntent?: any } {
  // Parse intent
  let intent = parseRemixIntent(userIntent);
  
  // Resolver conflitos
  if (intent.conflicts.length > 0) {
    intent = resolveConflicts(intent);
  }
  
  // Se não detectou nada, usar fallback legado
  if (intent.themes.length === 0 && 
      intent.difficulty === 'normal' && 
      intent.speed === 'normal' && 
      !intent.boss) {
    return generateLegacyRemix(baseSpec, userIntent);
  }
  
  // Compor patches
  const { patch, changes } = composePatches(baseSpec, intent);
  
  // Adicionar resumo do intent
  const summary = formatIntentSummary(intent);
  if (summary) {
    changes.unshift({
      type: 'modify',
      category: 'entity',
      target: 'intent',
      description: `Intent: ${summary}`
    });
  }
  
  return { patch, changes, parsedIntent: intent };
}

// Fallback para intents não reconhecidos (mantém compatibilidade)
function generateLegacyRemix(
  baseSpec: RuntimeSpec,
  userIntent: string
): { patch: SemanticPatch; changes: RemixChange[] } {
  const intent = userIntent.toLowerCase();
  
  // Detectar intenções simples legadas
  if (intent.includes('zumbi') || intent.includes('zombie')) {
    return generateZombieRemix(baseSpec);
  }
  
  if (intent.includes('space') || intent.includes('espaço')) {
    return generateSpaceRemix(baseSpec);
  }
  
  if (intent.includes('medieval') || intent.includes('dungeon')) {
    return generateMedievalRemix(baseSpec);
  }
  
  if (intent.includes('mais rápido') || intent.includes('faster')) {
    return generateFasterRemix(baseSpec);
  }
  
  if (intent.includes('mais difícil') || intent.includes('harder')) {
    return generateHarderRemix(baseSpec);
  }
  
  // Remix genérico
  return generateGenericRemix(baseSpec, userIntent);
}

function generateZombieRemix(baseSpec: RuntimeSpec): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = {
    entities: {
      modify: {}
    }
  };
  
  const changes: RemixChange[] = [];
  
  // Modificar inimigos para zumbis
  Object.keys(baseSpec.entities || {}).forEach(key => {
    const entity = baseSpec.entities![key];
    if (entity.damage || entity.aiType) {
      patch.entities!.modify![key] = {
        ...entity,
        sprite: '🧟',
        speed: Math.max(50, (entity.speed || 100) * 0.6), // Mais lentos
        health: (entity.health || 50) * 1.5, // Mais resistentes
        damage: (entity.damage || 10) * 1.2
      };
      
      changes.push({
        type: 'modify',
        category: 'entity',
        target: key,
        description: `Transformado em zumbi: mais lento, mais resistente`
      });
    }
  });
  
  return { patch, changes };
}

function generateSpaceRemix(baseSpec: RuntimeSpec): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = {
    entities: {
      modify: {}
    }
  };
  
  const changes: RemixChange[] = [];
  
  // Modificar para tema espacial
  Object.keys(baseSpec.entities || {}).forEach(key => {
    const entity = baseSpec.entities![key];
    
    if (key === 'player') {
      patch.entities!.modify![key] = {
        ...entity,
        sprite: '🚀'
      };
      changes.push({
        type: 'modify',
        category: 'entity',
        target: key,
        description: 'Player virou nave espacial'
      });
    } else if (entity.damage || entity.aiType) {
      patch.entities!.modify![key] = {
        ...entity,
        sprite: '☄️'
      };
      changes.push({
        type: 'modify',
        category: 'entity',
        target: key,
        description: 'Inimigo virou asteroide'
      });
    }
  });
  
  return { patch, changes };
}

function generateMedievalRemix(baseSpec: RuntimeSpec): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = {
    entities: {
      modify: {}
    }
  };
  
  const changes: RemixChange[] = [];
  
  // Modificar para tema medieval
  Object.keys(baseSpec.entities || {}).forEach(key => {
    const entity = baseSpec.entities![key];
    
    if (key === 'player') {
      patch.entities!.modify![key] = {
        ...entity,
        sprite: '🗡️'
      };
      changes.push({
        type: 'modify',
        category: 'entity',
        target: key,
        description: 'Player virou guerreiro medieval'
      });
    } else if (entity.damage || entity.aiType) {
      patch.entities!.modify![key] = {
        ...entity,
        sprite: Math.random() > 0.5 ? '👺' : '💀'
      };
      changes.push({
        type: 'modify',
        category: 'entity',
        target: key,
        description: 'Inimigo virou monstro medieval'
      });
    }
  });
  
  return { patch, changes };
}

function generateFasterRemix(baseSpec: RuntimeSpec): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = {
    entities: {
      modify: {}
    },
    spawners: {
      modify: {}
    }
  };
  
  const changes: RemixChange[] = [];
  
  // Aumentar velocidades
  Object.keys(baseSpec.entities || {}).forEach(key => {
    const entity = baseSpec.entities![key];
    if (entity.speed) {
      patch.entities!.modify![key] = {
        ...entity,
        speed: entity.speed * 1.5
      };
      changes.push({
        type: 'modify',
        category: 'entity',
        target: key,
        description: 'Velocidade aumentada em 50%'
      });
    }
  });
  
  // Spawners mais rápidos
  Object.keys(baseSpec.spawners || {}).forEach(key => {
    const spawner = baseSpec.spawners![key];
    patch.spawners!.modify![key] = {
      ...spawner,
      interval: spawner.interval * 0.7
    };
    changes.push({
      type: 'modify',
      category: 'spawner',
      target: key,
      description: 'Spawn 30% mais rápido'
    });
  });
  
  return { patch, changes };
}

function generateHarderRemix(baseSpec: RuntimeSpec): { patch: SemanticPatch; changes: RemixChange[] } {
  const patch: SemanticPatch = {
    entities: {
      modify: {}
    },
    spawners: {
      modify: {}
    }
  };
  
  const changes: RemixChange[] = [];
  
  // Inimigos mais fortes
  Object.keys(baseSpec.entities || {}).forEach(key => {
    const entity = baseSpec.entities![key];
    if (entity.damage || entity.aiType) {
      patch.entities!.modify![key] = {
        ...entity,
        health: (entity.health || 50) * 1.5,
        damage: (entity.damage || 10) * 1.3,
        speed: (entity.speed || 100) * 1.2
      };
      changes.push({
        type: 'modify',
        category: 'entity',
        target: key,
        description: 'Inimigo mais forte: +50% HP, +30% dano, +20% velocidade'
      });
    }
  });
  
  // Mais inimigos
  Object.keys(baseSpec.spawners || {}).forEach(key => {
    const spawner = baseSpec.spawners![key];
    patch.spawners!.modify![key] = {
      ...spawner,
      maxActive: Math.floor((spawner.maxActive || 5) * 1.5),
      interval: spawner.interval * 0.8
    };
    changes.push({
      type: 'modify',
      category: 'spawner',
      target: key,
      description: '+50% inimigos ativos, spawn 20% mais rápido'
    });
  });
  
  return { patch, changes };
}

function generateGenericRemix(baseSpec: RuntimeSpec, intent: string): { patch: SemanticPatch; changes: RemixChange[] } {
  // Remix genérico: pequenos ajustes aleatórios
  const patch: SemanticPatch = {
    entities: {
      modify: {}
    }
  };
  
  const changes: RemixChange[] = [{
    type: 'modify',
    category: 'entity',
    target: 'all',
    description: `Remix aplicado: ${intent}`
  }];
  
  return { patch, changes };
}
