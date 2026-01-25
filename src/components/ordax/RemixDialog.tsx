/**
 * FASE 8: REMIX DIALOG
 * 
 * Dialog para remixar jogos
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { HumanGamePlanView } from './HumanGamePlanView';
import { GenomeViewer } from './GenomeViewer';
import { generateRemixPatch } from '@/lib/ordax/remix-engine/generate-remix-patch';
import { applyRemixPatch } from '@/lib/ordax/remix-engine/apply-remix-patch';
import { validateRemix } from '@/lib/ordax/remix-engine/validate-remix';
import { applyAutofill } from '@/lib/ordax/runtime-autofill';
import { extractGenome, compareGenomes } from '@/lib/ordax/game-genome';
import { toast } from 'sonner';
import type { RuntimeSpec, OrdaxSpec } from '@/lib/ordax/types';
import type { RemixChange } from '@/lib/ordax/remix-engine';
import type { GameGenome } from '@/lib/ordax/game-genome';

interface RemixDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  baseSpec: RuntimeSpec;
  baseGameId: string;
  onRemixComplete: (remixedSpec: RuntimeSpec, remixId: string) => void;
}

export function RemixDialog({
  open,
  onOpenChange,
  baseSpec,
  baseGameId,
  onRemixComplete
}: RemixDialogProps) {
  const [remixIntent, setRemixIntent] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [remixedSpec, setRemixedSpec] = useState<OrdaxSpec | null>(null);
  const [remixedRuntimeSpec, setRemixedRuntimeSpec] = useState<RuntimeSpec | null>(null);
  const [changes, setChanges] = useState<RemixChange[]>([]);
  const [parsedIntent, setParsedIntent] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [baseGenome, setBaseGenome] = useState<GameGenome | null>(null);
  const [remixedGenome, setRemixedGenome] = useState<GameGenome | null>(null);

  const handleGenerateRemix = () => {
    if (!remixIntent.trim()) {
      toast.error('Digite o que você quer mudar');
      return;
    }
    
    setLoading(true);
    
    try {
      // 1. Extrair genoma base
      const baseGenomeData = extractGenome(baseSpec);
      setBaseGenome(baseGenomeData);
      
      // 2. Gerar semantic patch
      const { patch, changes: patchChanges, parsedIntent: parsed } = generateRemixPatch(baseSpec, remixIntent);
      
      // 3. Aplicar patch
      const remixed = applyRemixPatch(baseSpec, patch);
      
      // 4. Validar
      const validation = validateRemix(remixed);
      
      if (!validation.valid) {
        toast.error('Remix inválido', {
          description: validation.errors.join(', ')
        });
        setLoading(false);
        return;
      }
      
      // 5. Extrair genoma remixado
      const remixedGenomeData = extractGenome(remixed);
      setRemixedGenome(remixedGenomeData);
      
      // 6. Salvar RuntimeSpec remixado
      setRemixedRuntimeSpec(remixed);
      
      // 7. Converter para OrdaxSpec para preview
      const ordaxSpec: OrdaxSpec = {
        gameType: 'topdown',
        title: `${baseGameId} (Remix)`,
        description: remixIntent,
        systems: ['InputSystem', 'PhysicsSystem', 'CollisionSystem', 'RenderSystem'],
        scene: {
          gravity: { x: 0, y: 0 },
          entities: []
        }
      };
      
      // 8. Mostrar preview
      setRemixedSpec(ordaxSpec);
      setChanges(patchChanges);
      setParsedIntent(parsed);
      setShowPreview(true);
      
      toast.success('Remix gerado!', {
        description: `${patchChanges.length} mudanças aplicadas`
      });
      
    } catch (error) {
      console.error('Erro ao gerar remix:', error);
      toast.error('Erro ao gerar remix', {
        description: error instanceof Error ? error.message : 'Erro desconhecido'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = () => {
    if (!remixedRuntimeSpec) return;
    
    const remixId = `${baseGameId}-remix-${Date.now()}`;
    
    onRemixComplete(remixedRuntimeSpec, remixId);
    handleClose();
    
    toast.success('Remix criado!', {
      description: 'Seu novo jogo está pronto'
    });
  };

  const handleBack = () => {
    setShowPreview(false);
    setRemixedSpec(null);
    setRemixedRuntimeSpec(null);
    setChanges([]);
    setParsedIntent(null);
    setBaseGenome(null);
    setRemixedGenome(null);
  };

  const handleClose = () => {
    setShowPreview(false);
    setRemixedSpec(null);
    setRemixedRuntimeSpec(null);
    setChanges([]);
    setParsedIntent(null);
    setRemixIntent('');
    setBaseGenome(null);
    setRemixedGenome(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        {!showPreview ? (
          <>
            <DialogHeader>
              <DialogTitle className="text-2xl flex items-center gap-2">
                <span>✨</span>
                <span>Remixar Jogo</span>
              </DialogTitle>
              <DialogDescription>
                Descreva o que você quer mudar neste jogo
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="remix-intent">O que você quer mudar?</Label>
                <Textarea
                  id="remix-intent"
                  placeholder="Ex: transformar em zumbi medieval mais difícil com boss&#10;    tema espacial mais rápido&#10;    ninja fácil&#10;    pirata com boss"
                  value={remixIntent}
                  onChange={(e) => setRemixIntent(e.target.value)}
                  rows={5}
                  className="resize-none font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  💡 Combine temas, dificuldade, velocidade e boss em uma frase natural
                </p>
              </div>
              
              <div className="flex gap-2 justify-end">
                <Button
                  variant="outline"
                  onClick={handleClose}
                >
                  Cancelar
                </Button>
                
                <Button
                  onClick={handleGenerateRemix}
                  disabled={loading || !remixIntent.trim()}
                  className="bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700"
                >
                  {loading ? (
                    <>
                      <span className="animate-spin mr-2">⚙️</span>
                      Gerando...
                    </>
                  ) : (
                    <>
                      <span className="mr-2">✨</span>
                      Gerar Remix
                    </>
                  )}
                </Button>
              </div>
            </div>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="text-2xl flex items-center gap-2">
                <span>✨</span>
                <span>Preview do Remix</span>
              </DialogTitle>
              <DialogDescription>
                Revise as mudanças antes de confirmar
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Intent Parsed */}
              {parsedIntent && (
                <div className="bg-primary/10 border border-primary/30 rounded-lg p-4 space-y-2">
                  <h3 className="font-semibold text-sm flex items-center gap-2">
                    <span>🎯</span>
                    <span>Intent Detectado:</span>
                  </h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {parsedIntent.themes.length > 0 && (
                      <div>
                        <span className="text-muted-foreground">Temas:</span>
                        <span className="ml-2 font-medium">{parsedIntent.themes.join(' + ')}</span>
                      </div>
                    )}
                    {parsedIntent.difficulty !== 'normal' && (
                      <div>
                        <span className="text-muted-foreground">Dificuldade:</span>
                        <span className="ml-2 font-medium">{parsedIntent.difficulty}</span>
                      </div>
                    )}
                    {parsedIntent.speed !== 'normal' && (
                      <div>
                        <span className="text-muted-foreground">Velocidade:</span>
                        <span className="ml-2 font-medium">{parsedIntent.speed}</span>
                      </div>
                    )}
                    {parsedIntent.boss && (
                      <div>
                        <span className="text-muted-foreground">Boss:</span>
                        <span className="ml-2 font-medium">Sim 👑</span>
                      </div>
                    )}
                  </div>
                  {parsedIntent.conflicts.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-primary/20">
                      <span className="text-xs text-yellow-600">
                        ⚠️ Conflitos resolvidos: {parsedIntent.conflicts.join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              )}
              
              {/* Genome Comparison */}
              {baseGenome && remixedGenome && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="font-semibold text-sm mb-2">Jogo Original:</h3>
                    <GenomeViewer genome={baseGenome} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm mb-2">Jogo Remixado:</h3>
                    <GenomeViewer genome={remixedGenome} />
                  </div>
                </div>
              )}
              
              {/* Lista de mudanças */}
              <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                <h3 className="font-semibold text-sm">Mudanças Aplicadas:</h3>
                <ul className="space-y-1">
                  {changes.map((change, i) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <span className="text-primary">•</span>
                      <span>{change.description}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              {/* Preview do jogo */}
              {remixedSpec && (
                <HumanGamePlanView spec={remixedSpec} />
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
                  ✓ Aceitar Remix
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
