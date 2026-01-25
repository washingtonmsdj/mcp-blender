/**
 * FASE 8: REMIX BUTTON
 * 
 * Botão que permite remixar o jogo atual
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Sparkles } from 'lucide-react';
import { RemixDialog } from './RemixDialog';
import type { RuntimeSpec } from '@/lib/ordax/types';

interface RemixButtonProps {
  currentSpec: RuntimeSpec | null;
  gameId: string;
  onRemixComplete: (remixedSpec: RuntimeSpec, remixId: string) => void;
}

export function RemixButton({ currentSpec, gameId, onRemixComplete }: RemixButtonProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  
  if (!currentSpec) {
    return null;
  }
  
  return (
    <>
      <Button
        onClick={() => setDialogOpen(true)}
        variant="outline"
        size="sm"
        className="gap-2"
      >
        <Sparkles className="w-4 h-4" />
        Remixar este jogo
      </Button>
      
      <RemixDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        baseSpec={currentSpec}
        baseGameId={gameId}
        onRemixComplete={onRemixComplete}
      />
    </>
  );
}
