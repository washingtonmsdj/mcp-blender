import { MainLayout } from "@/components/layout/MainLayout";
import { ProjectSidebar } from "@/components/layout/ProjectSidebar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

// Import all components
import { ProjectForm } from "@/components/forms/ProjectForm";
import { NewProjectDialog } from "@/components/modals/NewProjectDialog";
import { DeleteConfirmDialog } from "@/components/modals/DeleteConfirmDialog";
import { ProjectListSkeleton } from "@/components/loading/Skeleton";
import { Spinner, LoadingScreen } from "@/components/loading/Spinner";
import { ProgressBar } from "@/components/loading/ProgressBar";
import { ProjectsTable } from "@/components/data/ProjectsTable";
import { ProjectsGrid } from "@/components/data/ProjectsGrid";
import { ToastExamples } from "@/components/advanced/ToastExamples";
import { ProjectTabs } from "@/components/advanced/ProjectTabs";
import { FAQ } from "@/components/advanced/FAQ";
import { CommandPalette } from "@/components/advanced/CommandPalette";

const Components = () => {
  return (
    <MainLayout sidebar={<ProjectSidebar />}>
      <div className="p-8 space-y-8 max-w-screen-2xl mx-auto">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold neon-text">Componentes</h1>
          <p className="text-muted-foreground">
            Biblioteca completa de componentes do Ordax Engine
          </p>
        </div>

        <Separator className="bg-border/50" />

        {/* Tabs */}
        <Tabs defaultValue="forms" className="w-full">
          <TabsList className="glass-panel grid w-full grid-cols-3 lg:grid-cols-6">
            <TabsTrigger value="forms" className="font-mono text-xs">Forms</TabsTrigger>
            <TabsTrigger value="modals" className="font-mono text-xs">Modals</TabsTrigger>
            <TabsTrigger value="loading" className="font-mono text-xs">Loading</TabsTrigger>
            <TabsTrigger value="data" className="font-mono text-xs">Data</TabsTrigger>
            <TabsTrigger value="feedback" className="font-mono text-xs">Feedback</TabsTrigger>
            <TabsTrigger value="advanced" className="font-mono text-xs">Advanced</TabsTrigger>
          </TabsList>

          {/* Forms */}
          <TabsContent value="forms" className="space-y-6">
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">Formulário de Projeto</CardTitle>
                <CardDescription className="text-xs">
                  Formulário completo com validação Zod e React Hook Form
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ProjectForm />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Modals */}
          <TabsContent value="modals" className="space-y-6">
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">Modais e Diálogos</CardTitle>
                <CardDescription className="text-xs">
                  Exemplos de Dialog e AlertDialog
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-4">
                  <NewProjectDialog />
                  <DeleteConfirmDialog 
                    onConfirm={() => console.log("Deletado!")} 
                    itemName="Space Shooter"
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Loading */}
          <TabsContent value="loading" className="space-y-6">
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">Estados de Carregamento</CardTitle>
                <CardDescription className="text-xs">
                  Skeleton, Spinner e Progress Bar
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                {/* Spinner */}
                <div>
                  <h3 className="font-mono text-sm mb-4">Spinner</h3>
                  <div className="flex gap-8 items-center">
                    <div className="text-center">
                      <Spinner size="sm" />
                      <p className="text-xs text-muted-foreground mt-2">Small</p>
                    </div>
                    <div className="text-center">
                      <Spinner size="default" />
                      <p className="text-xs text-muted-foreground mt-2">Default</p>
                    </div>
                    <div className="text-center">
                      <Spinner size="lg" />
                      <p className="text-xs text-muted-foreground mt-2">Large</p>
                    </div>
                  </div>
                </div>

                <Separator className="bg-border/50" />

                {/* Progress Bar */}
                <div>
                  <h3 className="font-mono text-sm mb-4">Progress Bar</h3>
                  <ProgressBar autoProgress />
                </div>

                <Separator className="bg-border/50" />

                {/* Skeleton */}
                <div>
                  <h3 className="font-mono text-sm mb-4">Skeleton Loader</h3>
                  <ProjectListSkeleton />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Data */}
          <TabsContent value="data" className="space-y-6">
            {/* Table */}
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">Tabela de Projetos</CardTitle>
                <CardDescription className="text-xs">
                  Tabela com ações e badges de status
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ProjectsTable />
              </CardContent>
            </Card>

            {/* Grid */}
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">Grid de Projetos</CardTitle>
                <CardDescription className="text-xs">
                  Cards responsivos em grid
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ProjectsGrid />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Feedback */}
          <TabsContent value="feedback" className="space-y-6">
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">Toast Notifications</CardTitle>
                <CardDescription className="text-xs">
                  Notificações com Sonner
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ToastExamples />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Advanced */}
          <TabsContent value="advanced" className="space-y-6">
            {/* Command Palette */}
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">Command Palette</CardTitle>
                <CardDescription className="text-xs">
                  Busca rápida com Ctrl+K (ou Cmd+K no Mac)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CommandPalette />
                <p className="text-xs text-muted-foreground mt-4 font-mono">
                  Pressione <kbd className="px-2 py-1 bg-surface-2 rounded border border-border/50">Ctrl+K</kbd> em qualquer lugar para abrir
                </p>
              </CardContent>
            </Card>

            {/* Project Tabs */}
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">Tabs de Projeto</CardTitle>
                <CardDescription className="text-xs">
                  Navegação por abas com conteúdo
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ProjectTabs />
              </CardContent>
            </Card>

            {/* FAQ */}
            <Card className="glass-panel">
              <CardHeader>
                <CardTitle className="neon-text">FAQ (Accordion)</CardTitle>
                <CardDescription className="text-xs">
                  Perguntas frequentes com accordion
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FAQ />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
};

export default Components;
