/**
 * FASE 7: PRESET SELECTION MODAL
 * 
 * Modal para seleção de presets canônicos.
 * Fluxo:
 * 1. Usuário clica em preset
 * 2. Mostra HumanGamePlanView
 * 3. Usuário confirma
 * 4. Jogo é compilado e rodado
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { CanonicalPresetButtons } from './CanonicalPresetButtons';
import { HumanGamePlanView } from './HumanGamePlanView';
import { Button } from '@/components/ui/button';
import type { CanonicalPreset } from '@/lib/ordax/canonical-presets';
import type { HumanSummary } from '@/lib/ordax/human-readable/generateHumanSummary';
import type { AutofillReport } from '@/lib/ordax/human-readable/generateAutofillReport';
import type { OrdaxSpec } from '@/lib/ordax/types';

interface PresetSelectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (spec: OrdaxSpec) => void;
}

export function PresetSelectionModal({
  open,
  onOpenChange,
  onConfirm
}: PresetSelectionModalProps) {
  const [selectedPreset, setSelectedPreset] = useState<CanonicalPreset | null>(null);
  const [humanSummary, setHumanSummary] = useState<HumanSummary | null>(null);
  const [autofillReport, setAutofillReport] = useState<AutofillReport | null>(null);
  const [showPlan, setShowPlan] = useState(false);

  const handlePresetSelected = (
    preset: CanonicalPreset,
    summary: HumanSummary,
    report: AutofillReport
  ) => {
    setSelectedPreset(preset);
    setHumanSummary(summary);
    setAutofillReport(report);
    setShowPlan(true);
  };

  const handleConfirm = () => {
    if (!selectedPreset) return;
    
    // Converter RuntimeSpec para OrdaxSpec
    const ordaxSpec: OrdaxSpec = {
      gameType: 'topdown',
      title: selectedPreset.name,
      description: selectedPreset.description,
      systems: ['InputSystem', 'PhysicsSystem', 'CollisionSystem', 'RenderSystem'],
      scene: {
        gravity: { x: 0, y: 0 },
        entities: []
      }
    };
    
    onConfirm(ordaxSpec);
    handleClose();
  };

  const handleBack = () => {
    setShowPlan(false);
    setSelectedPreset(null);
    setHumanSummary(null);
    setAutofillReport(null);
  };

  const handleClose = () => {
    setShowPlan(false);
    setSelectedPreset(null);
    setHumanSummary(null);
    setAutofillReport(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        {!showPlan ? (
          <>
            <DialogHeader>
              <DialogTitle className="text-2xl">
                🎮 Escolha um Jogo Canônico
              </DialogTitle>
              <DialogDescription>
                Selecione um preset para criar um jogo instantaneamente.
                Cada preset é validado e pronto para jogar.
              </DialogDescription>
            </DialogHeader>
            
            <CanonicalPresetButtons onPresetSelected={handlePresetSelected} />
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="text-2xl flex items-center gap-2">
                <span>{selectedPreset?.emoji}</span>
                <span>{selectedPreset?.name}</span>
              </DialogTitle>
              <DialogDescription>
                Revise o plano do jogo antes de confirmar
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {humanSummary && selectedPreset && (
                <HumanGamePlanView
                  spec={{
                    gameType: 'topdown',
                    title: selectedPreset.name,
                    description: selectedPreset.description,
                    systems: ['InputSystem', 'PhysicsSystem', 'CollisionSystem', 'RenderSystem'],
                    scene: {
                      gravity: { x: 0, y: 0 },
                      entities: []
                    }
                  }}
                />
              )}
              
              <div className="flex gap-3 justify-end pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={handleBack}
                >
                  ← Voltar
                </Button>
                
                <Button
                  onClick={handleConfirm}
                  size="lg"
                  className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700"
                >
                  ✓ Aceitar e Criar Jogo
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
