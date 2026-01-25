# 🎮 Ordax Engine

> Motor de jogos 2D com IA integrada e sistema visual moderno

[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-blue)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-18.3-61dafb)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646cff)](https://vitejs.dev/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.4-38bdf8)](https://tailwindcss.com/)

## ✨ Features

- 🎨 **Tema Dark Gaming** com efeitos neon profissionais
- 🤖 **IA Integrada** para geração de jogos via chat
- 🎯 **16+ Componentes** prontos para uso
- 📦 **50+ Componentes UI** (shadcn/ui)
- 🚀 **Performance Otimizada** com Vite + SWC
- 📱 **Totalmente Responsivo**
- ♿ **Acessível** (ARIA compliant)
- 📚 **Documentação Completa**

## 🚀 Quick Start

```bash
# Instalar dependências
npm install

# Rodar em desenvolvimento
npm run dev

# Build para produção
npm run build
```

## 🌐 Páginas Disponíveis

- **/** - Home (Dashboard com projetos e quick actions)
- **/workspace** - Workspace Ordax (Editor de jogos com IA)
- **/demo** - Visual Showcase (Demonstração do tema)
- **/components** - Components Library (Todos os componentes) ⭐

## 📦 Stack Tecnológica

### Core
- React 18.3 + TypeScript 5.8
- Vite 5.4 (build tool)
- React Router 6.30

### UI
- Tailwind CSS 3.4
- shadcn/ui (50+ componentes)
- Radix UI (primitivos)
- Lucide React (ícones)

### State & Forms
- TanStack Query 5.83
- React Hook Form 7.61
- Zod 3.25 (validação)

### Backend
- Supabase 2.91
- Edge Functions (Deno)

## 🎨 Sistema Visual

### Cores Neon
- **Cyan**: `#00D9FF` - Primary
- **Magenta**: `#E600E6` - Secondary
- **Green**: `#00E673` - Success
- **Orange**: `#FF8C1A` - Warning
- **Purple**: `#9933FF` - Special

### Classes Utilitárias
```css
.glass-panel    /* Efeito vidro fosco */
.neon-glow      /* Brilho neon */
.neon-text      /* Texto com glow */
```

### Fontes
- **UI**: Space Grotesk
- **Code**: JetBrains Mono

## 📚 Documentação

### Guias Principais
- [FRONTEND_REPLICATION_GUIDE.md](./FRONTEND_REPLICATION_GUIDE.md) - Guia completo
- [FRONTEND_COMPONENTS_EXAMPLES.md](./FRONTEND_COMPONENTS_EXAMPLES.md) - Exemplos
- [FRONTEND_COMPLETE_SUMMARY.md](./FRONTEND_COMPLETE_SUMMARY.md) - Resumo

### Implementação
- [VISUAL_SYSTEM.md](./VISUAL_SYSTEM.md) - Sistema visual
- [COMPONENTES_IMPLEMENTADOS.md](./COMPONENTES_IMPLEMENTADOS.md) - Componentes
- [GUIA_RAPIDO_COMPONENTES.md](./GUIA_RAPIDO_COMPONENTES.md) - Guia rápido

### Referência
- [INDEX_DOCUMENTACAO.md](./INDEX_DOCUMENTACAO.md) - Índice completo
- [RESUMO_FINAL_IMPLEMENTACAO.md](./RESUMO_FINAL_IMPLEMENTACAO.md) - Resumo final

## 🧩 Componentes Disponíveis

### Layout
- Header, MainLayout, ProjectSidebar

### Forms
- ProjectForm (com validação Zod)

### Modals
- NewProjectDialog, DeleteConfirmDialog

### Loading
- Spinner, ProgressBar, Skeleton

### Data
- ProjectsTable, ProjectCard, ProjectsGrid

### Advanced
- ToastExamples, ProjectTabs, FAQ

### Ordax
- OrdaxWorkspace, ChatPanel, EditorPanel, PreviewPanel, OrdaxCanvas

## 💡 Exemplos de Uso

### Layout Completo
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

### Toast Notification
```typescript
import { toast } from "sonner";

toast.success("Projeto criado com sucesso!");
toast.error("Erro ao salvar");
```

### Card com Efeitos
```typescript
<Card className="glass-panel hover:neon-glow transition-all">
  <CardHeader>
    <CardTitle className="neon-text">Título</CardTitle>
  </CardHeader>
  <CardContent>Conteúdo</CardContent>
</Card>
```

## 🛠️ Scripts Disponíveis

```bash
npm run dev          # Servidor de desenvolvimento
npm run build        # Build de produção
npm run preview      # Preview do build
npm run lint         # Lint do código
```

## 📁 Estrutura do Projeto

```
src/
├── components/
│   ├── ui/              # shadcn/ui (50+ componentes)
│   ├── layout/          # Header, MainLayout, ProjectSidebar
│   ├── forms/           # ProjectForm
│   ├── modals/          # Dialogs
│   ├── loading/         # Loading states
│   ├── data/            # Tables, Cards, Grids
│   ├── advanced/        # Tabs, FAQ, Toast
│   ├── demo/            # VisualShowcase
│   └── ordax/           # Engine components
├── pages/
│   ├── Index.tsx        # Workspace
│   ├── Demo.tsx         # Visual demo
│   ├── Components.tsx   # Components library
│   └── NotFound.tsx     # 404
├── lib/
│   ├── ordax/           # Engine logic
│   └── utils.ts
├── hooks/               # Custom hooks
├── integrations/        # Supabase
├── App.tsx
├── main.tsx
└── index.css
```

## 🎯 Roadmap

- [x] Sistema visual completo
- [x] Componentes base
- [x] Integração com IA
- [x] Editor de código
- [x] Preview em tempo real
- [ ] Sistema de assets
- [ ] Exportação de projetos
- [ ] Multiplayer
- [ ] Marketplace de templates

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🙏 Agradecimentos

- [shadcn/ui](https://ui.shadcn.com/) - Componentes UI
- [Radix UI](https://www.radix-ui.com/) - Primitivos acessíveis
- [Tailwind CSS](https://tailwindcss.com/) - Framework CSS
- [Lucide](https://lucide.dev/) - Ícones
- [Lovable](https://lovable.dev/) - Plataforma de desenvolvimento

## 📞 Suporte

- 📚 [Documentação Completa](./INDEX_DOCUMENTACAO.md)
- 🎨 [Visual Showcase](http://localhost:8080/demo)
- 📦 [Components Library](http://localhost:8080/components)

---

**Feito com ❤️ usando React + TypeScript + Vite**
