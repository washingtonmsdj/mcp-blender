# ⚡ GUIA RÁPIDO - USO DOS COMPONENTES

## 🎯 Acesso Rápido

```bash
# Rodar o projeto
npm run dev

# Acessar páginas
http://localhost:8080/              # Workspace
http://localhost:8080/demo          # Visual Demo
http://localhost:8080/components    # Components Library ⭐
```

---

## 📦 COMPONENTES PRONTOS PARA COPIAR

### 1. Layout Completo

```typescript
import { MainLayout } from "@/components/layout/MainLayout";
import { ProjectSidebar } from "@/components/layout/ProjectSidebar";

export default function MyPage() {
  return (
    <MainLayout sidebar={<ProjectSidebar />}>
      <div className="p-8">
        <h1 className="text-4xl font-bold neon-text">Minha Página</h1>
      </div>
    </MainLayout>
  );
}
```

### 2. Formulário com Validação

```typescript
import { ProjectForm } from "@/components/forms/ProjectForm";

// Já vem com:
// - Validação Zod
// - React Hook Form
// - Toast notifications
// - Glass panel effect

<ProjectForm />
```

### 3. Modal de Criação

```typescript
import { NewProjectDialog } from "@/components/modals/NewProjectDialog";

// Botão + Modal em um componente
<NewProjectDialog />
```

### 4. Confirmação de Deleção

```typescript
import { DeleteConfirmDialog } from "@/components/modals/DeleteConfirmDialog";

<DeleteConfirmDialog 
  onConfirm={() => console.log("Deletado!")}
  itemName="Meu Projeto"
/>
```

### 5. Loading States

```typescript
import { Spinner } from "@/components/loading/Spinner";
import { ProgressBar } from "@/components/loading/ProgressBar";
import { ProjectListSkeleton } from "@/components/loading/Skeleton";

// Spinner
<Spinner size="lg" />

// Progress Bar
<ProgressBar autoProgress />

// Skeleton
<ProjectListSkeleton />
```

### 6. Tabela de Dados

```typescript
import { ProjectsTable } from "@/components/data/ProjectsTable";

// Tabela completa com ações
<ProjectsTable />
```

### 7. Grid de Cards

```typescript
import { ProjectsGrid } from "@/components/data/ProjectsGrid";

// Grid responsivo de cards
<ProjectsGrid />
```

### 8. Toast Notifications

```typescript
import { toast } from "sonner";

// Success
toast.success("Sucesso!");

// Error
toast.error("Erro!");

// Loading
const promise = fetch('/api/data');
toast.promise(promise, {
  loading: 'Carregando...',
  success: 'Pronto!',
  error: 'Erro!',
});

// Com ação
toast("Deletado", {
  action: {
    label: "Desfazer",
    onClick: () => console.log("Desfazer"),
  },
});
```

### 9. Tabs com Conteúdo

```typescript
import { ProjectTabs } from "@/components/advanced/ProjectTabs";

// Tabs com Overview, Code, Assets
<ProjectTabs />
```

### 10. FAQ Accordion

```typescript
import { FAQ } from "@/components/advanced/FAQ";

// Accordion com perguntas frequentes
<FAQ />
```

---

## 🎨 CLASSES UTILITÁRIAS

### Glass Panel
```typescript
<div className="glass-panel p-4 rounded-lg">
  Conteúdo com efeito vidro
</div>
```

### Neon Glow
```typescript
<Button className="neon-glow">
  Botão com brilho
</Button>
```

### Neon Text
```typescript
<h1 className="neon-text text-4xl font-bold">
  Título Neon
</h1>
```

### Cores Neon
```typescript
<Badge className="bg-neon-cyan/20 text-neon-cyan border-neon-cyan/40">
  Cyan
</Badge>

<Badge className="bg-neon-magenta/20 text-neon-magenta border-neon-magenta/40">
  Magenta
</Badge>

<Badge className="bg-neon-green/20 text-neon-green border-neon-green/40">
  Green
</Badge>
```

### Surfaces
```typescript
<div className="bg-surface-1 p-4">Surface 1 (mais escuro)</div>
<div className="bg-surface-2 p-4">Surface 2 (médio)</div>
<div className="bg-surface-3 p-4">Surface 3 (mais claro)</div>
```

---

## 🚀 EXEMPLOS PRÁTICOS

### Página com Sidebar e Tabela

```typescript
import { MainLayout } from "@/components/layout/MainLayout";
import { ProjectSidebar } from "@/components/layout/ProjectSidebar";
import { ProjectsTable } from "@/components/data/ProjectsTable";
import { NewProjectDialog } from "@/components/modals/NewProjectDialog";

export default function ProjectsPage() {
  return (
    <MainLayout sidebar={<ProjectSidebar />}>
      <div className="p-8 space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-4xl font-bold neon-text">Projetos</h1>
          <NewProjectDialog />
        </div>
        <ProjectsTable />
      </div>
    </MainLayout>
  );
}
```

### Página com Grid e Loading

```typescript
import { MainLayout } from "@/components/layout/MainLayout";
import { ProjectsGrid } from "@/components/data/ProjectsGrid";
import { ProjectListSkeleton } from "@/components/loading/Skeleton";
import { useState, useEffect } from "react";

export default function GalleryPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => setLoading(false), 2000);
  }, []);

  return (
    <MainLayout>
      <div className="p-8">
        <h1 className="text-4xl font-bold neon-text mb-8">Galeria</h1>
        {loading ? <ProjectListSkeleton /> : <ProjectsGrid />}
      </div>
    </MainLayout>
  );
}
```

### Card Customizado

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function MyCard() {
  return (
    <Card className="glass-panel hover:neon-glow transition-all">
      <CardHeader>
        <CardTitle className="neon-text">Meu Card</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Descrição do card
        </p>
        <div className="flex gap-2">
          <Badge className="bg-neon-cyan/20 text-neon-cyan">Tag 1</Badge>
          <Badge className="bg-neon-magenta/20 text-neon-magenta">Tag 2</Badge>
        </div>
        <Button className="w-full neon-glow">Ação</Button>
      </CardContent>
    </Card>
  );
}
```

---

## 🎯 DICAS RÁPIDAS

### 1. Sempre use glass-panel para cards
```typescript
<Card className="glass-panel">...</Card>
```

### 2. Adicione neon-glow em botões principais
```typescript
<Button className="neon-glow">Ação Principal</Button>
```

### 3. Use neon-text em títulos importantes
```typescript
<h1 className="neon-text">Título</h1>
```

### 4. Font monospace para código/dados
```typescript
<span className="font-mono text-xs">código</span>
```

### 5. Badges com cores neon para status
```typescript
<Badge className="bg-neon-green/20 text-neon-green">Active</Badge>
```

---

## 📱 RESPONSIVIDADE

Todos os componentes são responsivos por padrão:

```typescript
// Grid automático
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {/* Cards */}
</div>

// Flex responsivo
<div className="flex flex-col md:flex-row gap-4">
  {/* Conteúdo */}
</div>

// Esconder em mobile
<div className="hidden md:block">Desktop only</div>

// Mostrar apenas em mobile
<div className="block md:hidden">Mobile only</div>
```

---

## 🔥 ATALHOS ÚTEIS

### Criar nova página rapidamente
```typescript
import { MainLayout } from "@/components/layout/MainLayout";

export default function NewPage() {
  return (
    <MainLayout>
      <div className="p-8">
        <h1 className="text-4xl font-bold neon-text">Nova Página</h1>
      </div>
    </MainLayout>
  );
}
```

### Adicionar toast em qualquer lugar
```typescript
import { toast } from "sonner";

// Em qualquer função
const handleClick = () => {
  toast.success("Ação realizada!");
};
```

### Loading state padrão
```typescript
const [loading, setLoading] = useState(true);

return loading ? <Spinner size="lg" /> : <Content />;
```

---

## 📚 ONDE ENCONTRAR

- **Componentes**: `/src/components/`
- **Páginas**: `/src/pages/`
- **Showcase**: `http://localhost:8080/components`
- **Documentação**: `COMPONENTES_IMPLEMENTADOS.md`

---

## 🎉 PRONTO!

Agora você tem acesso a todos os componentes prontos para usar.

**Acesse:** `http://localhost:8080/components` para ver todos em ação!

---

**Happy coding! 🚀**
