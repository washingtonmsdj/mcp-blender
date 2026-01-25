/**
 * FASE 10: CANONICAL GAME GENOME
 * 
 * Representação canônica e determinística da identidade de cada jogo.
 * Permite comparação estrutural e recriação de jogos.
 */

export interface GameGenome {
  // Identificação
  genre: string;
  
  // Temas visuais/narrativos
  themes: string[];
  
  // Modificadores de gameplay
  difficulty: 'easy' | 'normal' | 'hard';
  speed: 'slower' | 'normal' | 'faster';
  boss: boolean;
  
  // Progressão
  progression: {
    winCondition: 'score' | 'time' | 'survival' | 'collection';
    winTarget?: number;
    loseCondition: 'health' | 'time' | 'capture';
    loseTarget?: number;
  };
  
  // Tipos de inimigos
  enemyTypes: Array<{
    archetype: 'basic' | 'fast' | 'tank' | 'ranged' | 'boss';
    count: number;
    behavior: 'chase' | 'patrol' | 'ranged' | 'boss';
  }>;
  
  // Mecânicas
  mechanics: string[];
  
  // UI
  ui: {
    hud: string[];
    screens: string[];
  };
  
  // Metadata
  version: string;
  timestamp: number;
}

export { extractGenome } from './extract-genome';
export { applyGenome } from './apply-genome';
export { compareGenomes } from './compare-genomes';
export { formatGenome } from './format-genome';
