import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileCode, Image, Settings } from "lucide-react";

export const ProjectTabs = () => {
  return (
    <Tabs defaultValue="overview" className="w-full">
      <TabsList className="grid w-full grid-cols-3 glass-panel">
        <TabsTrigger value="overview" className="font-mono text-xs">
          <Settings className="h-4 w-4 mr-2" />
          Visão Geral
        </TabsTrigger>
        <TabsTrigger value="code" className="font-mono text-xs">
          <FileCode className="h-4 w-4 mr-2" />
          Código
        </TabsTrigger>
        <TabsTrigger value="assets" className="font-mono text-xs">
          <Image className="h-4 w-4 mr-2" />
          Assets
        </TabsTrigger>
      </TabsList>
      
      <TabsContent value="overview" className="mt-4">
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="neon-text">Visão Geral do Projeto</CardTitle>
            <CardDescription className="text-xs">
              Informações gerais sobre o projeto
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="glass-panel p-4 rounded-lg">
                <div className="text-xs text-muted-foreground font-mono">Tipo</div>
                <div className="text-lg font-bold text-primary mt-1">Shooter</div>
              </div>
              <div className="glass-panel p-4 rounded-lg">
                <div className="text-xs text-muted-foreground font-mono">Status</div>
                <div className="text-lg font-bold text-neon-green mt-1">Active</div>
              </div>
              <div className="glass-panel p-4 rounded-lg">
                <div className="text-xs text-muted-foreground font-mono">Entidades</div>
                <div className="text-lg font-bold text-primary mt-1">12</div>
              </div>
              <div className="glass-panel p-4 rounded-lg">
                <div className="text-xs text-muted-foreground font-mono">Assets</div>
                <div className="text-lg font-bold text-primary mt-1">24</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
      
      <TabsContent value="code" className="mt-4">
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="neon-text">Editor de Código</CardTitle>
            <CardDescription className="text-xs">
              Edite o código do seu jogo
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="bg-surface-1 p-4 rounded-lg border border-border/50 overflow-x-auto">
              <code className="font-mono text-xs text-primary">{`// main.ts
import { Game } from './game';

const game = new Game({
  width: 800,
  height: 600,
  backgroundColor: '#0a0e1a'
});

game.start();`}</code>
            </pre>
          </CardContent>
        </Card>
      </TabsContent>
      
      <TabsContent value="assets" className="mt-4">
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="neon-text">Biblioteca de Assets</CardTitle>
            <CardDescription className="text-xs">
              Gerencie sprites, sons e outros recursos
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="aspect-square glass-panel rounded-lg flex items-center justify-center hover:neon-glow transition-all cursor-pointer">
                  <Image className="h-8 w-8 text-muted-foreground" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
};
