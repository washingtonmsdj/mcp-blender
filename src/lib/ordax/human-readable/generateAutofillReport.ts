// Autofill Report Generator
import type { AutofillResult } from '../runtime-autofill/topdown-shooter';

export type AutofillReport = {
  wasModified: boolean;
  summary: string;
  added: {
    systems: string[];
    entities: string[];
    components: string[];
    ui: string[];
    controls: string[];
    visual: string[];
    audio: string[];
  };
  corrected: {
    gravity: boolean;
    props: string[];
  };
};

/**
 * Gera relatório humano do autofill
 */
export function generateAutofillReport(result: AutofillResult): AutofillReport {
  const added = {
    systems: [] as string[],
    entities: [] as string[],
    components: [] as string[],
    ui: [] as string[],
    controls: [] as string[],
    visual: [] as string[],
    audio: [] as string[],
  };
  
  const corrected = {
    gravity: false,
    props: [] as string[],
  };
  
  // Parse changes
  for (const change of result.changes) {
    if (change.includes('Sistema adicionado:')) {
      const system = change.split(':')[1].trim();
      added.systems.push(system);
    }
    
    if (change.includes('Entidade adicionada:')) {
      const match = change.match(/Entidade adicionada: (\w+)/);
      if (match) {
        added.entities.push(match[1]);
      }
    }
    
    if (change.includes('Props adicionadas')) {
      const match = change.match(/Props adicionadas em (\w+)/);
      if (match) {
        added.components.push(match[1]);
      }
    }
    
    if (change.includes('UI metadata adicionada')) {
      added.ui.push('StartScreen, HUD, GameOverScreen');
    }
    
    if (change.includes('Controls metadata adicionados')) {
      added.controls.push('WASD + SPACE');
    }
    
    if (change.includes('Visual theme adicionado')) {
      added.visual.push('Tema visual padrão');
    }
    
    if (change.includes('Background layers adicionadas')) {
      added.visual.push('Camadas de fundo (starfield + nebula)');
    }
    
    if (change.includes('Audio config adicionada')) {
      added.audio.push('Configuração de áudio');
    }
    
    if (change.includes('Gravity ajustado')) {
      corrected.gravity = true;
    }
    
    if (change.includes('Props adicionadas')) {
      const match = change.match(/(\d+) propriedades/);
      if (match) {
        corrected.props.push(`${match[1]} propriedades corrigidas`);
      }
    }
  }
  
  // Generate summary
  let summary = '';
  if (!result.wasModified) {
    summary = 'O runtime já estava completo. Nenhuma modificação foi necessária.';
  } else {
    const totalChanges = result.changes.length;
    summary = `${totalChanges} modificação(ões) aplicada(s) para tornar o jogo jogável.`;
  }
  
  return {
    wasModified: result.wasModified,
    summary,
    added,
    corrected,
  };
}

/**
 * Gera texto de preview do autofill
 */
export function generateAutofillPreview(report: AutofillReport): string {
  if (!report.wasModified) {
    return '✅ **Nenhuma modificação necessária**\n\nO runtime já estava completo e pronto para uso.';
  }
  
  const parts: string[] = [];
  
  parts.push(`**${report.summary}**`);
  
  // Sistemas adicionados
  if (report.added.systems.length > 0) {
    parts.push(`\n\n**Sistemas Adicionados:**`);
    report.added.systems.forEach(system => {
      parts.push(`- ${system}`);
    });
  }
  
  // Entidades adicionadas
  if (report.added.entities.length > 0) {
    parts.push(`\n\n**Entidades Adicionadas:**`);
    report.added.entities.forEach(entity => {
      parts.push(`- ${entity}`);
    });
  }
  
  // Componentes adicionados
  if (report.added.components.length > 0) {
    parts.push(`\n\n**Componentes Completados:**`);
    report.added.components.forEach(comp => {
      parts.push(`- ${comp}`);
    });
  }
  
  // UI adicionada
  if (report.added.ui.length > 0) {
    parts.push(`\n\n**Interface Adicionada:**`);
    report.added.ui.forEach(ui => {
      parts.push(`- ${ui}`);
    });
  }
  
  // Controles adicionados
  if (report.added.controls.length > 0) {
    parts.push(`\n\n**Controles Adicionados:**`);
    report.added.controls.forEach(control => {
      parts.push(`- ${control}`);
    });
  }
  
  // Visual adicionado
  if (report.added.visual.length > 0) {
    parts.push(`\n\n**Visual Adicionado:**`);
    report.added.visual.forEach(visual => {
      parts.push(`- ${visual}`);
    });
  }
  
  // Áudio adicionado
  if (report.added.audio.length > 0) {
    parts.push(`\n\n**Áudio Adicionado:**`);
    report.added.audio.forEach(audio => {
      parts.push(`- ${audio}`);
    });
  }
  
  // Correções
  if (report.corrected.gravity || report.corrected.props.length > 0) {
    parts.push(`\n\n**Correções Aplicadas:**`);
    if (report.corrected.gravity) {
      parts.push(`- Gravidade ajustada para top-down (x=0, y=0)`);
    }
    report.corrected.props.forEach(prop => {
      parts.push(`- ${prop}`);
    });
  }
  
  return parts.join('\n');
}
