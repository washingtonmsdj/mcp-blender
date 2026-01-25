/**
 * Runtime Autofill
 * 
 * Sistema de preenchimento automático de runtimes incompletos.
 * Garante que qualquer runtime nunca nasça quebrado.
 */

export {
  autofillTopDownShooter,
  needsAutofill,
  autofillAndValidate,
  generateAutofillReport,
  type AutofillResult,
} from './topdown-shooter';

// Alias para compatibilidade
export { autofillTopDownShooter as applyAutofill } from './topdown-shooter';
