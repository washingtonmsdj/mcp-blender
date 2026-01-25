/**
 * FASE 9: SEMANTIC REMIX INTELLIGENCE
 * 
 * Parser de intenções naturais para remixes determinísticos
 */

export interface ParsedIntent {
  themes: string[];
  difficulty: 'easy' | 'normal' | 'hard';
  speed: 'slower' | 'normal' | 'faster';
  boss: boolean;
  conflicts: string[];
  raw: string;
}

const THEME_KEYWORDS = {
  zombie: ['zumbi', 'zombie', 'morto-vivo', 'undead'],
  space: ['espaço', 'space', 'espacial', 'nave', 'asteroide'],
  medieval: ['medieval', 'dungeon', 'castelo', 'cavaleiro', 'dragão'],
  ninja: ['ninja', 'samurai', 'japão'],
  pirate: ['pirata', 'pirate', 'navio', 'tesouro'],
  robot: ['robô', 'robot', 'cyborg', 'mecha']
};

const DIFFICULTY_KEYWORDS = {
  easy: ['fácil', 'easy', 'simples', 'casual'],
  hard: ['difícil', 'hard', 'hardcore', 'impossível', 'insano']
};

const SPEED_KEYWORDS = {
  slower: ['lento', 'slower', 'devagar', 'calmo'],
  faster: ['rápido', 'faster', 'veloz', 'acelerado', 'turbo']
};

const BOSS_KEYWORDS = ['boss', 'chefe', 'chefão', 'final boss'];

export function parseRemixIntent(text: string): ParsedIntent {
  const normalized = text.toLowerCase().trim();
  
  const intent: ParsedIntent = {
    themes: [],
    difficulty: 'normal',
    speed: 'normal',
    boss: false,
    conflicts: [],
    raw: text
  };
  
  // Parse themes
  for (const [theme, keywords] of Object.entries(THEME_KEYWORDS)) {
    if (keywords.some(kw => normalized.includes(kw))) {
      intent.themes.push(theme);
    }
  }
  
  // Parse difficulty
  for (const [level, keywords] of Object.entries(DIFFICULTY_KEYWORDS)) {
    if (keywords.some(kw => normalized.includes(kw))) {
      intent.difficulty = level as 'easy' | 'hard';
      break;
    }
  }
  
  // Parse speed
  for (const [speed, keywords] of Object.entries(SPEED_KEYWORDS)) {
    if (keywords.some(kw => normalized.includes(kw))) {
      intent.speed = speed as 'slower' | 'faster';
      break;
    }
  }
  
  // Parse boss
  intent.boss = BOSS_KEYWORDS.some(kw => normalized.includes(kw));
  
  // Detect conflicts
  intent.conflicts = detectConflicts(intent);
  
  return intent;
}

function detectConflicts(intent: ParsedIntent): string[] {
  const conflicts: string[] = [];
  const normalized = intent.raw.toLowerCase();
  
  // Conflito: múltiplos temas incompatíveis
  const incompatibleThemes = [
    ['space', 'medieval'],
    ['zombie', 'robot'],
    ['ninja', 'pirate']
  ];
  
  for (const [theme1, theme2] of incompatibleThemes) {
    if (intent.themes.includes(theme1) && intent.themes.includes(theme2)) {
      conflicts.push(`Temas incompatíveis: ${theme1} e ${theme2}`);
    }
  }
  
  // Conflito: mais de 2 temas
  if (intent.themes.length > 2) {
    conflicts.push(`Muitos temas (${intent.themes.length}). Máximo: 2`);
  }
  
  // Conflito: slower + faster
  if (intent.speed === 'slower' && normalized.includes('rápido')) {
    conflicts.push('Velocidade conflitante: lento e rápido');
  }
  
  return conflicts;
}

export function resolveConflicts(intent: ParsedIntent): ParsedIntent {
  const resolved = { ...intent };
  
  // Resolver conflitos de tema: manter apenas o primeiro
  if (resolved.themes.length > 2) {
    resolved.themes = resolved.themes.slice(0, 2);
    resolved.conflicts = resolved.conflicts.filter(c => !c.includes('Muitos temas'));
  }
  
  // Resolver temas incompatíveis: manter o primeiro
  const incompatiblePairs = [
    ['space', 'medieval'],
    ['zombie', 'robot'],
    ['ninja', 'pirate']
  ];
  
  for (const [theme1, theme2] of incompatiblePairs) {
    if (resolved.themes.includes(theme1) && resolved.themes.includes(theme2)) {
      // Remove o segundo tema
      const idx = resolved.themes.indexOf(theme2);
      resolved.themes.splice(idx, 1);
      resolved.conflicts = resolved.conflicts.filter(
        c => !c.includes(`${theme1} e ${theme2}`)
      );
    }
  }
  
  return resolved;
}

export function formatIntentSummary(intent: ParsedIntent): string {
  const parts: string[] = [];
  
  if (intent.themes.length > 0) {
    parts.push(`Tema: ${intent.themes.join(' + ')}`);
  }
  
  if (intent.difficulty !== 'normal') {
    parts.push(`Dificuldade: ${intent.difficulty}`);
  }
  
  if (intent.speed !== 'normal') {
    parts.push(`Velocidade: ${intent.speed}`);
  }
  
  if (intent.boss) {
    parts.push('Boss: adicionado');
  }
  
  return parts.join(' | ');
}
