/**
 * EXEMPLO DE USO: Profile Validator
 * 
 * Demonstra como usar o validador de perfil para verificar
 * se um runtimeSpec cumpre os requisitos do gênero top-down shooter.
 */

import { TOPDOWN_SHOOTER_PROFILE } from './topdown-shooter';
import { validateRuntimeAgainstProfile, formatProfileViolations, generateMissingElementsReport } from './validator';
import type { OrdaxSpec } from '../types';

// ============================================================================
// EXEMPLO 1: Runtime INCOMPLETO (muitas violações)
// ============================================================================

const incompleteRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "My Shooter",
  description: "A simple shooter game",
  systems: ["PhysicsSystem"], // Faltam vários sistemas!
  scene: {
    gravity: { x: 0, y: 0 },
    entities: [
      {
        id: "player1",
        type: "player",
        x: 400,
        y: 300,
        w: 32,
        h: 32,
        props: {
          // Faltam health, speed, fireRate!
        }
      }
      // Faltam enemy, bullet, spawner!
    ]
  }
};

console.log("=== VALIDAÇÃO: Runtime Incompleto ===\n");
const result1 = validateRuntimeAgainstProfile(incompleteRuntime, TOPDOWN_SHOOTER_PROFILE);
console.log(formatProfileViolations(result1));
console.log("\n" + generateMissingElementsReport(result1));

// ============================================================================
// EXEMPLO 2: Runtime COMPLETO (válido)
// ============================================================================

const completeRuntime: OrdaxSpec = {
  gameType: "topdown",
  title: "Stellar Vanguard",
  description: "Survive waves of enemies in space",
  systems: [
    "PhysicsSystem",
    "CollisionSystem",
    "AISystem",
    "SpawnerSystem",
    "ScoreSystem",
    "TimerSystem",
    "UISystem"
  ],
  visual: {
    theme: {
      background: "hsl(220, 20%, 10%)",
      primary: "hsl(200, 80%, 60%)",
      accent: "hsl(30, 90%, 60%)"
    }
  },
  scene: {
    gravity: { x: 0, y: 0 },
    entities: [
      // PLAYER
      {
        id: "player1",
        type: "player",
        x: 400,
        y: 300,
        w: 32,
        h: 32,
        props: {
          health: 100,
          speed: 200,
          fireRate: 0.2,
          vx: 0,
          vy: 0,
          rotation: 0
        }
      },
      // ENEMY
      {
        id: "enemy1",
        type: "enemy",
        x: 200,
        y: 100,
        w: 24,
        h: 24,
        props: {
          health: 50,
          speed: 100,
          damage: 10,
          ai: "chase",
          target: "player"
        }
      },
      // BULLET (template)
      {
        id: "bullet_template",
        type: "bullet",
        x: 0,
        y: 0,
        w: 4,
        h: 4,
        props: {
          speed: 400,
          damage: 25,
          lifetime: 2.0
        }
      },
      // SPAWNER
      {
        id: "spawner1",
        type: "spawner",
        x: 400,
        y: 50,
        w: 1,
        h: 1,
        props: {
          spawnRate: 2.0,
          maxEnemies: 20,
          spawner: true
        }
      }
    ]
  }
};

console.log("\n\n=== VALIDAÇÃO: Runtime Completo ===\n");
const result2 = validateRuntimeAgainstProfile(completeRuntime, TOPDOWN_SHOOTER_PROFILE);
console.log(formatProfileViolations(result2));

if (result2.isValid) {
  console.log("\n✅ Este runtime está pronto para ser jogado!");
} else {
  console.log("\n❌ Ainda há violações críticas.");
}

// ============================================================================
// EXEMPLO 3: Uso em pipeline de compilação
// ============================================================================

export function validateGameBeforeCompile(runtimeSpec: OrdaxSpec): boolean {
  const result = validateRuntimeAgainstProfile(runtimeSpec, TOPDOWN_SHOOTER_PROFILE);
  
  if (!result.isValid) {
    console.error("❌ COMPILATION BLOCKED: Runtime não cumpre perfil do gênero");
    console.error(formatProfileViolations(result));
    console.error(generateMissingElementsReport(result));
    return false;
  }
  
  console.log("✅ Runtime válido. Prosseguindo com compilação...");
  return true;
}

// ============================================================================
// EXEMPLO 4: Relatório para IA
// ============================================================================

export function generateAIFeedback(runtimeSpec: OrdaxSpec): string {
  const result = validateRuntimeAgainstProfile(runtimeSpec, TOPDOWN_SHOOTER_PROFILE);
  
  if (result.isValid) {
    return "✅ Seu jogo está completo e funcional! Todos os elementos obrigatórios estão presentes.";
  }
  
  let feedback = "⚠️ Seu jogo ainda não está completo. Aqui está o que falta:\n\n";
  
  if (result.missingElements.systems.length > 0) {
    feedback += "**Sistemas faltantes:**\n";
    result.missingElements.systems.forEach(s => {
      feedback += `- ${s}\n`;
    });
    feedback += "\n";
  }
  
  if (result.missingElements.entities.length > 0) {
    feedback += "**Entidades faltantes:**\n";
    result.missingElements.entities.forEach(e => {
      feedback += `- ${e}\n`;
    });
    feedback += "\n";
  }
  
  if (Object.keys(result.missingElements.components).length > 0) {
    feedback += "**Componentes faltantes:**\n";
    for (const [entity, components] of Object.entries(result.missingElements.components)) {
      feedback += `- Em '${entity}': ${components.join(', ')}\n`;
    }
    feedback += "\n";
  }
  
  feedback += `\n**Resumo:** ${result.summary.critical} críticas, ${result.summary.severe} graves, ${result.summary.minor} menores.`;
  
  return feedback;
}
