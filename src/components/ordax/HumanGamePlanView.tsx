// Human Game Plan View - Camada de apresentação humana
import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Gamepad2, 
  Target, 
  Zap, 
  Users, 
  TrendingUp, 
  Skull, 
  Palette, 
  Volume2,
  Code,
  Eye,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import type { OrdaxSpec } from '@/lib/ordax/types';
import type { AutofillResult } from '@/lib/ordax/runtime-autofill/topdown-shooter';
import { generateHumanSummary, generateSemanticPreview } from '@/lib/ordax/human-readable/generateHumanSummary';
import { generateAutofillReport, generateAutofillPreview } from '@/lib/ordax/human-readable/generateAutofillReport';

type Props = {
  spec: OrdaxSpec | null;
  autofillResult?: AutofillResult;
};

export function HumanGamePlanView({ spec, autofillResult }: Props) {
  const [showJson, setShowJson] = useState(false);
  
  const summary = generateHumanSummary(spec);
  const semanticPreview = generateSemanticPreview(summary);
  const autofillReport = autofillResult ? generateAutofillReport(autofillResult) : null;
  const autofillPreview = autofillReport ? generateAutofillPreview(autofillReport) : null;

  if (!spec) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center space-y-4">
          <p className="text-lg text-muted-foreground">No game spec available</p>
          <p className="text-sm text-muted-foreground">Start the game to see the plan</p>
        </div>
      </div>
    );
  }

  if (showJson) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Code className="w-5 h-5" />
            JSON Técnico
          </h3>
          <Button variant="outline" size="sm" onClick={() => setShowJson(false)}>
            <Eye className="w-4 h-4 mr-2" />
            Ver Versão Humana
          </Button>
        </div>
        
        <ScrollArea className="h-[600px] w-full rounded-md border p-4">
          <pre className="text-xs font-mono">
            {JSON.stringify(spec, null, 2)}
          </pre>
        </ScrollArea>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Gamepad2 className="w-6 h-6" />
            {summary.title}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Resumo do jogo que será criado
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowJson(true)}>
          <Code className="w-4 h-4 mr-2" />
          Ver JSON Técnico
        </Button>
      </div>

      {/* Genre Badge */}
      <div>
        <Badge className="text-sm px-3 py-1">
          {summary.genre}
        </Badge>
      </div>

      <Separator />

      {/* Main Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Objetivo */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Target className="w-4 h-4" />
              Objetivo
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{summary.objective}</p>
          </CardContent>
        </Card>

        {/* Controles */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Gamepad2 className="w-4 h-4" />
              Controles
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">{summary.controls.movement}</p>
            {summary.controls.actions.map((action, i) => (
              <p key={i} className="text-sm text-muted-foreground">{action}</p>
            ))}
          </CardContent>
        </Card>

        {/* Mecânicas */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Mecânicas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {summary.mechanics.map((mechanic, i) => (
                <li key={i} className="text-sm text-muted-foreground flex items-center gap-2">
                  <CheckCircle2 className="w-3 h-3 text-green-500" />
                  {mechanic}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {/* Inimigos */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="w-4 h-4" />
              Inimigos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {summary.enemies.types.map((type, i) => (
                <li key={i} className="text-sm text-muted-foreground">{type}</li>
              ))}
              {summary.enemies.behaviors.map((behavior, i) => (
                <li key={i} className="text-sm text-muted-foreground flex items-center gap-2">
                  <AlertCircle className="w-3 h-3 text-orange-500" />
                  {behavior}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {/* Progressão */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Progressão
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{summary.progression}</p>
          </CardContent>
        </Card>

        {/* Derrota */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Skull className="w-4 h-4" />
              Condição de Derrota
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{summary.defeat}</p>
          </CardContent>
        </Card>

        {/* Visual */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Palette className="w-4 h-4" />
              Visual
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <p className="text-sm text-muted-foreground">{summary.visual.theme}</p>
            <p className="text-sm text-muted-foreground">{summary.visual.style}</p>
          </CardContent>
        </Card>

        {/* Áudio */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Volume2 className="w-4 h-4" />
              Áudio
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summary.audio.music && (
              <p className="text-sm text-muted-foreground">Música de fundo</p>
            )}
            {summary.audio.sounds.length > 0 && (
              <p className="text-sm text-muted-foreground">
                Efeitos: {summary.audio.sounds.join(', ')}
              </p>
            )}
            {!summary.audio.music && summary.audio.sounds.length === 0 && (
              <p className="text-sm text-muted-foreground">Sem áudio configurado</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Semantic Preview */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-base">Preview Semântico</CardTitle>
          <CardDescription>
            Descrição em linguagem natural do jogo
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <div dangerouslySetInnerHTML={{ 
              __html: semanticPreview.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>') 
            }} />
          </div>
        </CardContent>
      </Card>

      {/* Autofill Report */}
      {autofillReport && autofillPreview && (
        <Card className={autofillReport.wasModified ? 'border-orange-500/50' : 'border-green-500/50'}>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              {autofillReport.wasModified ? (
                <AlertCircle className="w-4 h-4 text-orange-500" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-green-500" />
              )}
              Relatório de Autofill
            </CardTitle>
            <CardDescription>
              {autofillReport.summary}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <div dangerouslySetInnerHTML={{ 
                __html: autofillPreview.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>') 
              }} />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
