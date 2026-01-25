import { MainLayout } from "@/components/layout/MainLayout";
import { ProjectSidebar } from "@/components/layout/ProjectSidebar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ProjectsGrid } from "@/components/data/ProjectsGrid";
import { NewProjectDialog } from "@/components/modals/NewProjectDialog";
import { Gamepad2, Sparkles, Zap, Code, Palette } from "lucide-react";
import { Link } from "react-router-dom";

const Index = () => {
  return (
    <MainLayout sidebar={<ProjectSidebar />}>
      <div className="p-8 space-y-8 max-w-screen-2xl mx-auto">
        {/* Hero Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-primary to-secondary rounded-xl flex items-center justify-center neon-glow">
              <Gamepad2 className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-5xl font-bold neon-text">Ordax Engine</h1>
              <p className="text-muted-foreground font-mono text-sm">
                Motor de jogos 2D com IA integrada
              </p>
            </div>
          </div>

          <div className="flex gap-3 flex-wrap">
            <Badge className="bg-neon-cyan/20 text-neon-cyan border-neon-cyan/40 neon-glow">
              <Sparkles className="w-3 h-3 mr-1" />
              AI Powered
            </Badge>
            <Badge className="bg-neon-magenta/20 text-neon-magenta border-neon-magenta/40">
              <Gamepad2 className="w-3 h-3 mr-1" />
              2D Engine
            </Badge>
            <Badge className="bg-neon-green/20 text-neon-green border-neon-green/40">
              <Zap className="w-3 h-3 mr-1" />
              Real-time
            </Badge>
          </div>
        </div>

        <Separator className="bg-border/50" />

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="glass-panel hover:neon-glow transition-all cursor-pointer group">
            <CardHeader>
              <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center mb-2 group-hover:neon-glow transition-all">
                <Code className="h-5 w-5 text-primary" />
              </div>
              <CardTitle className="group-hover:neon-text transition-all">Workspace</CardTitle>
              <CardDescription className="text-xs">
                Editor completo com IA para criar jogos
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/workspace">
                <Button className="w-full neon-glow">
                  Abrir Workspace
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="glass-panel hover:neon-glow transition-all cursor-pointer group">
            <CardHeader>
              <div className="w-10 h-10 bg-neon-cyan/20 rounded-lg flex items-center justify-center mb-2 group-hover:neon-glow transition-all">
                <Gamepad2 className="h-5 w-5 text-neon-cyan" />
              </div>
              <CardTitle className="group-hover:neon-text transition-all">Top-Down Demo</CardTitle>
              <CardDescription className="text-xs">
                Fases 4 + 5 integradas (Juice & Feel)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/topdown-demo">
                <Button className="w-full neon-glow bg-neon-cyan/20 hover:bg-neon-cyan/30">
                  Jogar Demo
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="glass-panel hover:neon-glow transition-all cursor-pointer group">
            <CardHeader>
              <div className="w-10 h-10 bg-neon-magenta/20 rounded-lg flex items-center justify-center mb-2 group-hover:neon-glow transition-all">
                <Palette className="h-5 w-5 text-neon-magenta" />
              </div>
              <CardTitle className="group-hover:neon-text transition-all">Visual Demo</CardTitle>
              <CardDescription className="text-xs">
                Demonstração do sistema visual
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/demo">
                <Button variant="outline" className="w-full glass-panel">
                  Ver Demo
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="glass-panel hover:neon-glow transition-all cursor-pointer group">
            <CardHeader>
              <div className="w-10 h-10 bg-neon-green/20 rounded-lg flex items-center justify-center mb-2 group-hover:neon-glow transition-all">
                <Sparkles className="h-5 w-5 text-neon-green" />
              </div>
              <CardTitle className="group-hover:neon-text transition-all">Components</CardTitle>
              <CardDescription className="text-xs">
                Biblioteca completa de componentes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/components">
                <Button variant="outline" className="w-full glass-panel">
                  Ver Componentes
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        <Separator className="bg-border/50" />

        {/* Projects Section */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold neon-text">Seus Projetos</h2>
              <p className="text-sm text-muted-foreground font-mono">
                Gerencie e crie novos projetos de jogos
              </p>
            </div>
            <NewProjectDialog />
          </div>

          <ProjectsGrid />
        </div>

        {/* Features Section */}
        <Separator className="bg-border/50" />

        <div className="space-y-6">
          <h2 className="text-3xl font-bold neon-text">Features</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  IA Integrada
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Crie jogos através de conversação com IA. Descreva o que você quer
                e a IA gera o código automaticamente.
              </CardContent>
            </Card>

            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-neon-green" />
                  Preview em Tempo Real
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Veja suas mudanças instantaneamente com hot reload e preview
                em tempo real do seu jogo.
              </CardContent>
            </Card>

            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-5 w-5 text-neon-cyan" />
                  Editor Completo
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Editor de código com syntax highlighting, autocomplete e
                gerenciamento de assets integrado.
              </CardContent>
            </Card>

            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5 text-neon-magenta" />
                  Visual Moderno
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Interface dark gaming com efeitos neon, glass morphism e
                animações suaves.
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default Index;
