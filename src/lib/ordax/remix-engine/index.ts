/**
 * FASE 8: REMIX ENGINE
 * 
 * Sistema que permite remixar jogos existentes.
 * Qualquer jogo pode virar base para um novo jogo.
 */

import type { RuntimeSpec } from '../types';

export interface RemixIntent {
  baseGameId: string;
  remixOf: string;
  userIntent: string;
  timestamp: number;
}

export interface RemixResult {
  newGameId: string;
  remixOf: string;
  runtimeSpec: RuntimeSpec;
  semanticPatch: SemanticPatch;
  changes: RemixChange[];
}

export interface SemanticPatch {
  entities?: {
    add?: Record<string, any>;
    remove?: string[];
    modify?: Record<string, any>;
  };
  spawners?: {
    add?: Record<string, any>;
    remove?: string[];
    modify?: Record<string, any>;
  };
  rules?: {
    winCondition?: any;
    loseCondition?: any;
  };
  ui?: {
    hud?: any;
  };
}

export interface RemixChange {
  type: 'add' | 'remove' | 'modify';
  category: 'entity' | 'spawner' | 'rule' | 'ui';
  target: string;
  description: string;
}

export { generateRemixPatch } from './generate-remix-patch';
export { applyRemixPatch } from './apply-remix-patch';
export { validateRemix } from './validate-remix';
