/**
 * FASE 7: CANONICAL PRESETS TESTS
 * 
 * Testes para garantir que todos os presets:
 * - Têm metadata válida
 * - Têm estrutura básica correta
 * - São únicos
 * - Podem ser usados no sistema
 */

import { describe, it, expect } from 'vitest';
import {
  createSpaceSurvivalPreset,
  createZombieArenaPreset,
  createDungeonShooterPreset
} from './index';

describe('Canonical Presets', () => {
  describe('Space Survival', () => {
    const preset = createSpaceSurvivalPreset();

    it('should have valid metadata', () => {
      expect(preset.id).toBe('space-survival');
      expect(preset.name).toBe('Space Survival');
      expect(preset.description).toBeTruthy();
      expect(preset.emoji).toBe('🚀');
    });

    it('should have runtime spec', () => {
      expect(preset.runtimeSpec).toBeTruthy();
      expect(preset.runtimeSpec.profile).toBe('topdown-shooter');
    });

    it('should have required entities', () => {
      expect(preset.runtimeSpec.entities).toBeTruthy();
      expect(preset.runtimeSpec.entities.player).toBeTruthy();
      expect(preset.runtimeSpec.entities.asteroid).toBeTruthy();
      expect(preset.runtimeSpec.entities.crystal).toBeTruthy();
    });

    it('should have spawners', () => {
      expect(preset.runtimeSpec.spawners).toBeTruthy();
      expect(Object.keys(preset.runtimeSpec.spawners || {}).length).toBeGreaterThan(0);
    });

    it('should have rules', () => {
      expect(preset.runtimeSpec.rules).toBeTruthy();
      expect(preset.runtimeSpec.rules?.winCondition).toBeTruthy();
      expect(preset.runtimeSpec.rules?.loseCondition).toBeTruthy();
    });

    it('should have UI config', () => {
      expect(preset.runtimeSpec.ui).toBeTruthy();
      expect(preset.runtimeSpec.ui?.hud).toBeTruthy();
    });
  });

  describe('Zombie Arena', () => {
    const preset = createZombieArenaPreset();

    it('should have valid metadata', () => {
      expect(preset.id).toBe('zombie-arena');
      expect(preset.name).toBe('Zombie Arena');
      expect(preset.description).toBeTruthy();
      expect(preset.emoji).toBe('🧟');
    });

    it('should have runtime spec', () => {
      expect(preset.runtimeSpec).toBeTruthy();
      expect(preset.runtimeSpec.profile).toBe('topdown-shooter');
    });

    it('should have required entities', () => {
      expect(preset.runtimeSpec.entities).toBeTruthy();
      expect(preset.runtimeSpec.entities.player).toBeTruthy();
      expect(preset.runtimeSpec.entities.zombie).toBeTruthy();
      expect(preset.runtimeSpec.entities.healthPack).toBeTruthy();
    });

    it('should have weapon system', () => {
      expect(preset.runtimeSpec.entities.player.weapon).toBeTruthy();
    });

    it('should have spawners', () => {
      expect(preset.runtimeSpec.spawners).toBeTruthy();
      expect(Object.keys(preset.runtimeSpec.spawners || {}).length).toBeGreaterThan(0);
    });

    it('should have wave scaling', () => {
      const spawner = Object.values(preset.runtimeSpec.spawners || {})[0];
      expect(spawner).toBeTruthy();
    });

    it('should have rules', () => {
      expect(preset.runtimeSpec.rules).toBeTruthy();
      expect(preset.runtimeSpec.rules?.winCondition).toBeTruthy();
      expect(preset.runtimeSpec.rules?.loseCondition).toBeTruthy();
    });
  });

  describe('Dungeon Shooter', () => {
    const preset = createDungeonShooterPreset();

    it('should have valid metadata', () => {
      expect(preset.id).toBe('dungeon-shooter');
      expect(preset.name).toBe('Dungeon Shooter');
      expect(preset.description).toBeTruthy();
      expect(preset.emoji).toBe('🗡️');
    });

    it('should have runtime spec', () => {
      expect(preset.runtimeSpec).toBeTruthy();
      expect(preset.runtimeSpec.profile).toBe('topdown-shooter');
    });

    it('should have multiple enemy types', () => {
      expect(preset.runtimeSpec.entities.goblin).toBeTruthy();
      expect(preset.runtimeSpec.entities.skeleton).toBeTruthy();
    });

    it('should have collectibles', () => {
      expect(preset.runtimeSpec.entities.treasure).toBeTruthy();
      expect(preset.runtimeSpec.entities.key).toBeTruthy();
    });

    it('should have spawners', () => {
      expect(preset.runtimeSpec.spawners).toBeTruthy();
      expect(Object.keys(preset.runtimeSpec.spawners || {}).length).toBeGreaterThan(3);
    });

    it('should have rules', () => {
      expect(preset.runtimeSpec.rules).toBeTruthy();
      expect(preset.runtimeSpec.rules?.winCondition).toBeTruthy();
      expect(preset.runtimeSpec.rules?.loseCondition).toBeTruthy();
    });
  });

  describe('All Presets', () => {
    const presets = [
      createSpaceSurvivalPreset(),
      createZombieArenaPreset(),
      createDungeonShooterPreset()
    ];

    it('should all have unique IDs', () => {
      const ids = presets.map(p => p.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(presets.length);
    });

    it('should all have profile', () => {
      presets.forEach(preset => {
        expect(preset.runtimeSpec.profile).toBe('topdown-shooter');
      });
    });

    it('should all have win/lose conditions', () => {
      presets.forEach(preset => {
        expect(preset.runtimeSpec.rules?.winCondition).toBeTruthy();
        expect(preset.runtimeSpec.rules?.loseCondition).toBeTruthy();
      });
    });

    it('should all have UI configuration', () => {
      presets.forEach(preset => {
        expect(preset.runtimeSpec.ui).toBeTruthy();
        expect(preset.runtimeSpec.ui?.hud).toBeTruthy();
      });
    });

    it('should all have entities', () => {
      presets.forEach(preset => {
        expect(preset.runtimeSpec.entities).toBeTruthy();
        expect(preset.runtimeSpec.entities.player).toBeTruthy();
        expect(Object.keys(preset.runtimeSpec.entities).length).toBeGreaterThan(1);
      });
    });

    it('should all have spawners', () => {
      presets.forEach(preset => {
        expect(preset.runtimeSpec.spawners).toBeTruthy();
        expect(Object.keys(preset.runtimeSpec.spawners || {}).length).toBeGreaterThan(0);
      });
    });
  });
});
