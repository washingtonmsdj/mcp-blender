/**
 * FASE 7: CANONICAL PRESET BUTTONS
 * 
 * Botões para criar jogos instantâneos a partir de presets canônicos.
 * Cada botão:
 * 1. Gera o preset
 * 2. Valida o RuntimeSpec
 * 3. Aplica autofill
 * 4. Mostra HumanGamePlanView
 * 5. Aguarda confirmação
 * 6. Compila e roda
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Rocket, Skull, Sword } from 'lucide-react';
import {
  createSpaceSurvivalPreset,
  createZombieArenaPreset,
  createDungeonShooterPreset,
  type CanonicalPreset
} from '@/lib/ordax/canonical-presets';
import { applyAutofill } from '@/lib/ordax/runtime-autofill';
import { generateHumanSummary, type HumanSummary } from '@/lib/ordax/human-readable/generateHumanSummary';
import { generateAutofillReport, type AutofillReport } from '@/lib/ordax/human-readable/generateAutofillReport';
import { toast } from 'sonner';

interface CanonicalPresetButtonsProps {
  onPresetSelected: (
    preset: CanonicalPreset, 
    humanSummary: HumanSummary, 
    autofillReport: AutofillReport
  ) => void;
}

export function CanonicalPresetButtons({ onPresetSelected }: CanonicalPresetButtonsProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const handlePresetClick = async (
    presetFn: () => CanonicalPreset,
    presetId: string
  ) => {
    setLoading(presetId);
    
    try {
      // 1. Gerar preset
      const preset = presetFn();
      
      // 2. Aplicar autofill (preenche campos faltantes)
      const autofillResult = applyAutofill(preset.runtimeSpec);
      
      // 3. Converter para OrdaxSpec para gerar resumo
      const ordaxSpec: any = {
        gameType: 'topdown',
        title: preset.name,
        description: preset.description,
        systems: ['InputSystem', 'PhysicsSystem', 'CollisionSystem', 'RenderSystem'],
        scene: {
          gravity: { x: 0, y: 0 },
          entities: []
        }
      };
      
      // 4. Gerar resumos humanos
      const humanSummary = generateHumanSummary(ordaxSpec);
      const autofillReport = generateAutofillReport(autofillResult);
      
      // 5. Atualizar preset com spec preenchido
      const finalPreset: CanonicalPreset = {
        ...preset,
        runtimeSpec: autofillResult.spec
      };
      
      // 6. Notificar sucesso
      toast.success('Preset carregado', {
        description: `${preset.name} pronto para jogar!`
      });
      
      // 7. Passar para o componente pai
      onPresetSelected(finalPreset, humanSummary, autofillReport);
      
    } catch (error) {
      console.error('Erro ao carregar preset:', error);
      toast.error('Erro ao carregar preset', {
        description: error instanceof Error ? error.message : 'Erro desconhecido'
      });
    } finally {
      setLoading(null);
    }
  };

  const presets = [
    {
      id: 'space-survival',
      name: 'Space Survival',
      description: 'Sobreviva no espaço coletando cristais',
      icon: Rocket,
      color: 'from-blue-500 to-purple-600',
      fn: createSpaceSurvivalPreset
    },
    {
      id: 'zombie-arena',
      name: 'Zombie Arena',
      description: 'Enfrente ondas de zumbis',
      icon: Skull,
      color: 'from-green-500 to-emerald-600',
      fn: createZombieArenaPreset
    },
    {
      id: 'dungeon-shooter',
      name: 'Dungeon Shooter',
      description: 'Explore dungeons e derrote monstros',
      icon: Sword,
      color: 'from-orange-500 to-red-600',
      fn: createDungeonShooterPreset
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4">
      {presets.map((preset) => {
        const Icon = preset.icon;
        const isLoading = loading === preset.id;
        
        return (
          <Card
            key={preset.id}
            className="overflow-hidden hover:shadow-lg transition-shadow"
          >
            <div className={`h-2 bg-gradient-to-r ${preset.color}`} />
            
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-lg bg-gradient-to-br ${preset.color}`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">{preset.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {preset.description}
                  </p>
                </div>
              </div>
              
              <Button
                onClick={() => handlePresetClick(preset.fn, preset.id)}
                disabled={isLoading}
                className="w-full"
                size="lg"
              >
                {isLoading ? (
                  <>
                    <span className="animate-spin mr-2">⚙️</span>
                    Carregando...
                  </>
                ) : (
                  <>
                    <span className="mr-2">🎮</span>
                    Criar Jogo
                  </>
                )}
              </Button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
