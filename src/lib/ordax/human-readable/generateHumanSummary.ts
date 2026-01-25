// Human-Readable Summary Generator
import type { OrdaxSpec } from '../types';

export type HumanSummary = {
  title: string;
  genre: string;
  objective: string;
  controls: {
    movement: string;
    actions: string[];
  };
  mechanics: string[];
  enemies: {
    types: string[];
    behaviors: string[];
  };
  progression: string;
  defeat: string;
  visual: {
    theme: string;
    style: string;
  };
  audio: {
    music: boolean;
    sounds: string[];
  };
};

/**
 * Gera um resumo humano do runtimeSpec
 */
export function generateHumanSummary(spec: OrdaxSpec | null | undefined): HumanSummary {
  if (!spec) {
    return {
      title: 'Untitled Game',
      genre: 'Unknown',
      objective: 'No objective defined',
      controls: { movement: 'Not configured', actions: [] },
      mechanics: [],
      enemies: { types: [], behaviors: [] },
      progression: 'No progression defined',
      defeat: 'Not defined',
      visual: { theme: 'Default', style: 'Minimal' },
      audio: { music: false, sounds: [] }
    };
  }
  
  const entities = spec.scene?.entities || [];
  const systems = spec.systems || [];
  
  // Detectar gênero
  const genre = detectGenre(spec.gameType, systems, entities);
  
  // Detectar objetivo
  const objective = detectObjective(spec.gameType, entities);
  
  // Detectar controles
  const controls = detectControls(entities);
  
  // Detectar mecânicas
  const mechanics = detectMechanics(systems, entities);
  
  // Detectar inimigos
  const enemies = detectEnemies(entities);
  
  // Detectar progressão
  const progression = detectProgression(entities, systems);
  
  // Detectar condição de derrota
  const defeat = detectDefeat(entities);
  
  // Detectar visual
  const visual = detectVisual(spec);
  
  // Detectar áudio
  const audio = detectAudio(spec);
  
  return {
    title: spec.title || 'Untitled Game',
    genre,
    objective,
    controls,
    mechanics,
    enemies,
    progression,
    defeat,
    visual,
    audio,
  };
}

function detectGenre(gameType: string | undefined, systems: string[], entities: any[]): string {
  if (gameType === 'topdown') {
    const hasSpawner = entities.some(e => e.type === 'spawner');
    const hasEnemies = entities.some(e => e.type === 'enemy');
    if (hasSpawner && hasEnemies) {
      return 'Top-Down Shooter Survival';
    }
    return 'Top-Down Shooter';
  }
  
  if (gameType === 'platformer') return 'Platformer';
  if (gameType === 'puzzle') return 'Puzzle';
  if (gameType === 'racing') return 'Racing';
  
  return 'Action Game';
}

function detectObjective(gameType: string | undefined, entities: any[]): string {
  if (gameType === 'topdown') {
    const hasSpawner = entities.some(e => e.type === 'spawner');
    if (hasSpawner) {
      return 'Sobreviva o máximo de tempo possível eliminando ondas de inimigos';
    }
    return 'Elimine todos os inimigos para vencer';
  }
  
  if (gameType === 'platformer') {
    return 'Chegue ao final da fase evitando obstáculos';
  }
  
  if (gameType === 'puzzle') {
    return 'Resolva os quebra-cabeças para avançar';
  }
  
  if (gameType === 'racing') {
    return 'Complete a corrida no menor tempo possível';
  }
  
  return 'Complete os objetivos do jogo';
}

function detectControls(entities: any[]): { movement: string; actions: string[] } {
  const controlsEntity = entities.find(e => e.type === 'controls');
  
  if (controlsEntity?.props) {
    const movement = controlsEntity.props.movement;
    const action = controlsEntity.props.action;
    
    const movementStr = movement?.up === 'W' 
      ? 'WASD para mover em 8 direções'
      : 'Setas para mover';
    
    const actions: string[] = [];
    if (action?.shoot) {
      actions.push(`${action.shoot} para atirar`);
    }
    if (action?.jump) {
      actions.push(`${action.jump} para pular`);
    }
    
    return { movement: movementStr, actions };
  }
  
  // Defaults
  return {
    movement: 'WASD para mover',
    actions: ['SPACE para atirar'],
  };
}

function detectMechanics(systems: string[], entities: any[]): string[] {
  const mechanics: string[] = [];
  
  // Movimento
  if (systems.includes('PhysicsSystem')) {
    mechanics.push('Movimento fluido com física');
  }
  
  // Tiro
  const hasBullets = entities.some(e => e.type === 'bullet');
  if (hasBullets) {
    mechanics.push('Sistema de tiro');
  }
  
  // IA
  if (systems.includes('AISystem')) {
    const hasChaseEnemies = entities.some(e => e.props?.ai === 'chase');
    if (hasChaseEnemies) {
      mechanics.push('Inimigos perseguem o jogador');
    }
  }
  
  // Spawn
  if (systems.includes('SpawnerSystem')) {
    mechanics.push('Ondas progressivas de inimigos');
  }
  
  // Colisão
  if (systems.includes('CollisionSystem')) {
    mechanics.push('Detecção de colisões');
  }
  
  // Combate
  if (systems.includes('CombatSystem')) {
    mechanics.push('Sistema de dano e vida');
  }
  
  // Score
  if (systems.includes('ScoreSystem')) {
    mechanics.push('Sistema de pontuação');
  }
  
  // Timer
  if (systems.includes('TimerSystem')) {
    mechanics.push('Cronômetro de sobrevivência');
  }
  
  return mechanics;
}

function detectEnemies(entities: any[]): { types: string[]; behaviors: string[] } {
  const enemies = entities.filter(e => e.type === 'enemy');
  
  const types: string[] = [];
  const behaviors: string[] = [];
  
  if (enemies.length > 0) {
    types.push(`${enemies.length} tipo(s) de inimigo`);
    
    const hasChase = enemies.some(e => e.props?.ai === 'chase');
    if (hasChase) {
      behaviors.push('Perseguem o jogador');
    }
    
    const hasDamage = enemies.some(e => e.props?.damage || e.props?.contactDamage);
    if (hasDamage) {
      behaviors.push('Causam dano ao tocar');
    }
  }
  
  return { types, behaviors };
}

function detectProgression(entities: any[], systems: string[]): string {
  const hasSpawner = entities.some(e => e.type === 'spawner');
  const hasScore = systems.includes('ScoreSystem');
  const hasTimer = systems.includes('TimerSystem');
  
  if (hasSpawner && hasTimer) {
    return 'Ondas de inimigos aumentam com o tempo';
  }
  
  if (hasScore) {
    return 'Pontuação aumenta ao eliminar inimigos';
  }
  
  return 'Progressão linear';
}

function detectDefeat(entities: any[]): string {
  const player = entities.find(e => e.type === 'player');
  
  if (player?.props?.health !== undefined) {
    return 'Quando a vida do jogador chega a zero';
  }
  
  return 'Quando o jogador é atingido';
}

function detectVisual(spec: OrdaxSpec): { theme: string; style: string } {
  const theme = spec.visual?.theme;
  const background = spec.visual?.background;
  
  let themeStr = 'Tema escuro';
  if (theme?.background) {
    const bg = String(theme.background);
    if (bg.includes('hsl')) {
      themeStr = 'Tema customizado';
    }
  }
  
  let styleStr = 'Estilo minimalista';
  if (background?.layers) {
    const hasStarfield = background.layers.some((l: any) => l.type === 'starfield');
    const hasNebula = background.layers.some((l: any) => l.type === 'nebula');
    
    if (hasStarfield && hasNebula) {
      styleStr = 'Ambiente espacial com estrelas e nebulosas';
    } else if (hasStarfield) {
      styleStr = 'Ambiente espacial com estrelas';
    }
  }
  
  return { theme: themeStr, style: styleStr };
}

function detectAudio(spec: OrdaxSpec): { music: boolean; sounds: string[] } {
  const audio = spec.audio;
  
  const music = !!audio?.music;
  const sounds: string[] = [];
  
  if (audio?.sounds) {
    const soundKeys = Object.keys(audio.sounds);
    if (soundKeys.includes('shoot')) sounds.push('Tiro');
    if (soundKeys.includes('collision') || soundKeys.includes('hit')) sounds.push('Colisão');
    if (soundKeys.includes('gameOver')) sounds.push('Game Over');
    if (soundKeys.includes('score')) sounds.push('Pontuação');
  }
  
  return { music, sounds };
}

/**
 * Gera texto de preview semântico
 */
export function generateSemanticPreview(summary: HumanSummary): string {
  const parts: string[] = [];
  
  parts.push(`Este jogo é um **${summary.genre}**.`);
  parts.push(`\n**Objetivo:** ${summary.objective}`);
  
  parts.push(`\n\n**Controles:**`);
  parts.push(`- ${summary.controls.movement}`);
  summary.controls.actions.forEach(action => {
    parts.push(`- ${action}`);
  });
  
  if (summary.mechanics.length > 0) {
    parts.push(`\n\n**Mecânicas:**`);
    summary.mechanics.forEach(mechanic => {
      parts.push(`- ${mechanic}`);
    });
  }
  
  if (summary.enemies.types.length > 0) {
    parts.push(`\n\n**Inimigos:**`);
    summary.enemies.types.forEach(type => {
      parts.push(`- ${type}`);
    });
    summary.enemies.behaviors.forEach(behavior => {
      parts.push(`- ${behavior}`);
    });
  }
  
  parts.push(`\n\n**Progressão:** ${summary.progression}`);
  parts.push(`\n**Derrota:** ${summary.defeat}`);
  
  parts.push(`\n\n**Visual:**`);
  parts.push(`- ${summary.visual.theme}`);
  parts.push(`- ${summary.visual.style}`);
  
  if (summary.audio.music || summary.audio.sounds.length > 0) {
    parts.push(`\n\n**Áudio:**`);
    if (summary.audio.music) {
      parts.push(`- Música de fundo`);
    }
    if (summary.audio.sounds.length > 0) {
      parts.push(`- Efeitos sonoros: ${summary.audio.sounds.join(', ')}`);
    }
  }
  
  return parts.join('\n');
}
