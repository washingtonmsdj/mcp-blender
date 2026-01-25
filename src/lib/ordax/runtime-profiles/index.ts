/**
 * Runtime Profiles - Perfis Canônicos de Gêneros
 * 
 * Este módulo define perfis canônicos para cada gênero de jogo suportado pela Ordax.
 * Cada perfil especifica EXATAMENTE o que um jogo funcional daquele gênero DEVE ter.
 * 
 * Uso:
 * 
 * ```ts
 * import { TOPDOWN_SHOOTER_PROFILE, validateRuntimeAgainstProfile } from '@/lib/ordax/runtime-profiles';
 * 
 * const result = validateRuntimeAgainstProfile(myRuntimeSpec, TOPDOWN_SHOOTER_PROFILE);
 * 
 * if (!result.isValid) {
 *   console.error(formatProfileViolations(result));
 * }
 * ```
 */

// Perfis de gênero
export {
  TOPDOWN_SHOOTER_PROFILE,
  isSystemRequired,
  isEntityRequired,
  getEntityProfile,
  getCriticalComponents,
  type RuntimeProfile,
  type EntityProfile,
  type ComponentProfile,
  type ComponentPropRequirement,
  type UIProfile,
  type ControlProfile,
  type SignalProfile,
  type LifecycleProfile,
} from './topdown-shooter';

// Validador
export {
  validateRuntimeAgainstProfile,
  formatProfileViolations,
  generateMissingElementsReport,
  type ProfileViolation,
  type ProfileViolationLevel,
  type ProfileValidationResult,
} from './validator';

// Exemplos (útil para testes e documentação)
export {
  validateGameBeforeCompile,
  generateAIFeedback,
} from './example-validation';
