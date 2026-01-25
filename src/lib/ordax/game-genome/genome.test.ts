/**
 * FASE 10: GENOME TESTS
 * 
 * Testes para garantir propriedades do genoma:
 * - extract(apply(G)) ≈ G
 * - Determinismo
 * - Comparação estrutural
 */

import { describe, it, expect } from 'vitest';
import { extractGenome } from './extract-genome';
import { applyGenome } from './apply-genome';
import { compareGenomes, hasDifferences } from './compare-genomes';
import { createSpaceSurvivalPreset } from '../canonical-presets/space-survival';
import { createZombieArenaPreset } from '../canonical-presets/zombie-arena';
import type { GameGenome } from './index';

describe('Game Genome', () => {
  describe('extractGenome', () => {
    it('should extract genome from Space Survival', () => {
      const preset = createSpaceSurvivalPreset();
      const genome = extractGenome(preset.runtimeSpec);
      
      expect(genome.genre).toBe('topdown-shooter');
      expect(genome.themes).toContain('space');
      expect(genome.difficulty).toBeDefined();
      expect(genome.speed).toBeDefined();
      expect(genome.boss).toBeDefined();
      expect(genome.progression).toBeDefined();
      expect(genome.enemyTypes).toBeDefined();
      expect(genome.mechanics).toBeDefined();
      expect(genome.ui).toBeDefined();
    });
    
    it('should extract genome from Zombie Arena', () => {
      const preset = createZombieArenaPreset();
      const genome = extractGenome(preset.runtimeSpec);
      
      expect(genome.genre).toBe('topdown-shooter');
      expect(genome.themes).toContain('zombie');
      expect(genome.mechanics).toContain('shooting');
    });
    
    it('should be deterministic', () => {
      const preset = createSpaceSurvivalPreset();
      const genome1 = extractGenome(preset.runtimeSpec);
      const genome2 = extractGenome(preset.runtimeSpec);
      
      // Ignorar timestamp
      genome1.timestamp = 0;
      genome2.timestamp = 0;
      
      expect(genome1).toEqual(genome2);
    });
  });
  
  describe('applyGenome', () => {
    it('should apply genome to base spec', () => {
      const basePreset = createSpaceSurvivalPreset();
      const targetGenome: GameGenome = {
        genre: 'topdown-shooter',
        themes: ['zombie'],
        difficulty: 'hard',
        speed: 'faster',
        boss: true,
        progression: {
          winCondition: 'score',
          winTarget: 1000,
          loseCondition: 'health',
          loseTarget: 0
        },
        enemyTypes: [],
        mechanics: [],
        ui: { hud: ['health', 'score'], screens: [] },
        version: '1.0.0',
        timestamp: Date.now()
      };
      
      const result = applyGenome(basePreset.runtimeSpec, targetGenome);
      
      expect(result).toBeDefined();
      expect(result.rules?.winCondition?.type).toBe('score');
      expect(result.rules?.winCondition?.target).toBe(1000);
    });
  });
  
  describe('extract(apply(G)) ≈ G', () => {
    it('should preserve genome through apply/extract cycle', () => {
      const basePreset = createSpaceSurvivalPreset();
      const originalGenome = extractGenome(basePreset.runtimeSpec);
      
      // Apply genome to base spec
      const applied = applyGenome(basePreset.runtimeSpec, originalGenome);
      
      // Extract genome from applied spec
      const extractedGenome = extractGenome(applied);
      
      // Compare (ignoring timestamp)
      originalGenome.timestamp = 0;
      extractedGenome.timestamp = 0;
      
      // Core properties should match
      expect(extractedGenome.genre).toBe(originalGenome.genre);
      expect(extractedGenome.difficulty).toBe(originalGenome.difficulty);
      expect(extractedGenome.speed).toBe(originalGenome.speed);
      expect(extractedGenome.boss).toBe(originalGenome.boss);
      expect(extractedGenome.progression.winCondition).toBe(originalGenome.progression.winCondition);
      expect(extractedGenome.progression.loseCondition).toBe(originalGenome.progression.loseCondition);
    });
  });
  
  describe('compareGenomes', () => {
    it('should detect no differences for identical genomes', () => {
      const preset = createSpaceSurvivalPreset();
      const genome1 = extractGenome(preset.runtimeSpec);
      const genome2 = extractGenome(preset.runtimeSpec);
      
      const diff = compareGenomes(genome1, genome2);
      
      expect(hasDifferences(diff)).toBe(false);
    });
    
    it('should detect theme differences', () => {
      const preset1 = createSpaceSurvivalPreset();
      const preset2 = createZombieArenaPreset();
      
      const genome1 = extractGenome(preset1.runtimeSpec);
      const genome2 = extractGenome(preset2.runtimeSpec);
      
      const diff = compareGenomes(genome1, genome2);
      
      expect(hasDifferences(diff)).toBe(true);
      expect(diff.themes.added.length > 0 || diff.themes.removed.length > 0).toBe(true);
    });
    
    it('should detect difficulty differences', () => {
      const preset = createSpaceSurvivalPreset();
      const genome1 = extractGenome(preset.runtimeSpec);
      
      const genome2 = { ...genome1, difficulty: 'hard' as const };
      
      const diff = compareGenomes(genome1, genome2);
      
      expect(diff.difficulty).toBeDefined();
      expect(diff.difficulty?.from).toBe(genome1.difficulty);
      expect(diff.difficulty?.to).toBe('hard');
    });
  });
  
  describe('Structural Comparison', () => {
    it('should allow comparing two games structurally', () => {
      const game1 = createSpaceSurvivalPreset();
      const game2 = createZombieArenaPreset();
      
      const genome1 = extractGenome(game1.runtimeSpec);
      const genome2 = extractGenome(game2.runtimeSpec);
      
      // Can compare
      expect(genome1.genre).toBe(genome2.genre);
      expect(genome1.themes).not.toEqual(genome2.themes);
      
      // Can detect differences
      const diff = compareGenomes(genome1, genome2);
      expect(hasDifferences(diff)).toBe(true);
    });
  });
  
  describe('Recreation from Genome', () => {
    it('should recreate game from genome', () => {
      const original = createSpaceSurvivalPreset();
      const genome = extractGenome(original.runtimeSpec);
      
      // Use a different base
      const base = createZombieArenaPreset();
      
      // Apply genome to base
      const recreated = applyGenome(base.runtimeSpec, genome);
      
      // Extract genome from recreated
      const recreatedGenome = extractGenome(recreated);
      
      // Core properties should match original genome
      expect(recreatedGenome.difficulty).toBe(genome.difficulty);
      expect(recreatedGenome.speed).toBe(genome.speed);
      expect(recreatedGenome.boss).toBe(genome.boss);
    });
  });
});
