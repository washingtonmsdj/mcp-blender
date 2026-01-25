/**
 * FASE 10: GENOME VIEWER
 * 
 * Componente para visualizar o genoma de um jogo
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { GameGenome } from '@/lib/ordax/game-genome';

interface GenomeViewerProps {
  genome: GameGenome;
  compact?: boolean;
}

export function GenomeViewer({ genome, compact = false }: GenomeViewerProps) {
  if (compact) {
    return <GenomeViewerCompact genome={genome} />;
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>🧬</span>
          <span>Game Genome</span>
        </CardTitle>
        <CardDescription>
          Representação canônica da identidade do jogo
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Genre */}
        <div>
          <div className="text-sm font-medium text-muted-foreground mb-1">Genre</div>
          <Badge variant="outline">{genome.genre}</Badge>
        </div>
        
        {/* Themes */}
        {genome.themes.length > 0 && !genome.themes.includes('default') && (
          <div>
            <div className="text-sm font-medium text-muted-foreground mb-1">Themes</div>
            <div className="flex gap-2 flex-wrap">
              {genome.themes.map(theme => (
                <Badge key={theme} variant="secondary">{theme}</Badge>
              ))}
            </div>
          </div>
        )}
        
        <Separator />
        
        {/* Modifiers */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-sm font-medium text-muted-foreground mb-1">Difficulty</div>
            <Badge variant={
              genome.difficulty === 'easy' ? 'default' :
              genome.difficulty === 'hard' ? 'destructive' :
              'outline'
            }>
              {genome.difficulty}
            </Badge>
          </div>
          
          <div>
            <div className="text-sm font-medium text-muted-foreground mb-1">Speed</div>
            <Badge variant={
              genome.speed === 'slower' ? 'secondary' :
              genome.speed === 'faster' ? 'default' :
              'outline'
            }>
              {genome.speed}
            </Badge>
          </div>
          
          <div>
            <div className="text-sm font-medium text-muted-foreground mb-1">Boss</div>
            <Badge variant={genome.boss ? 'default' : 'outline'}>
              {genome.boss ? '👑 Yes' : 'No'}
            </Badge>
          </div>
        </div>
        
        <Separator />
        
        {/* Progression */}
        <div>
          <div className="text-sm font-medium text-muted-foreground mb-2">Progression</div>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Win:</span>
              <span className="font-medium">
                {genome.progression.winCondition}
                {genome.progression.winTarget && ` (${genome.progression.winTarget})`}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Lose:</span>
              <span className="font-medium">
                {genome.progression.loseCondition}
                {genome.progression.loseTarget !== undefined && ` (${genome.progression.loseTarget})`}
              </span>
            </div>
          </div>
        </div>
        
        {/* Enemy Types */}
        {genome.enemyTypes.length > 0 && (
          <>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Enemy Types</div>
              <div className="space-y-1">
                {genome.enemyTypes.map((type, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span>
                      <Badge variant="outline" className="mr-2">{type.archetype}</Badge>
                      <span className="text-muted-foreground">({type.behavior})</span>
                    </span>
                    <span className="font-medium">{type.count}x</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
        
        {/* Mechanics */}
        {genome.mechanics.length > 0 && (
          <>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">Mechanics</div>
              <div className="flex gap-1 flex-wrap">
                {genome.mechanics.map(mechanic => (
                  <Badge key={mechanic} variant="outline" className="text-xs">
                    {mechanic}
                  </Badge>
                ))}
              </div>
            </div>
          </>
        )}
        
        {/* UI */}
        {genome.ui.hud.length > 0 && (
          <>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">HUD Elements</div>
              <div className="flex gap-1 flex-wrap">
                {genome.ui.hud.map(element => (
                  <Badge key={element} variant="secondary" className="text-xs">
                    {element}
                  </Badge>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function GenomeViewerCompact({ genome }: { genome: GameGenome }) {
  return (
    <div className="flex items-center gap-2 flex-wrap text-sm">
      <span className="text-muted-foreground">🧬</span>
      
      {genome.themes.length > 0 && !genome.themes.includes('default') && (
        <Badge variant="secondary">{genome.themes.join('+')}</Badge>
      )}
      
      {genome.difficulty !== 'normal' && (
        <Badge variant="outline">{genome.difficulty}</Badge>
      )}
      
      {genome.speed !== 'normal' && (
        <Badge variant="outline">{genome.speed}</Badge>
      )}
      
      {genome.boss && (
        <Badge variant="default">👑</Badge>
      )}
      
      <span className="text-muted-foreground">
        {genome.enemyTypes.length} enemies
      </span>
      
      <span className="text-muted-foreground">
        {genome.mechanics.length} mechanics
      </span>
    </div>
  );
}
