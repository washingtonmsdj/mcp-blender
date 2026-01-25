# 🎮 GUIA COMPLETO DE REPLICAÇÃO DO FRONTEND

## 📋 ÍNDICE
1. [Stack Tecnológica](#stack)
2. [Estrutura de Pastas](#estrutura)
3. [Configurações Base](#configuracoes)
4. [Dependências](#dependencias)
5. [Componentes UI](#componentes)
6. [Tema e Estilos](#tema)
7. [Rotas e Páginas](#rotas)
8. [Contextos e Hooks](#contextos)

---

## 🛠️ STACK TECNOLÓGICA {#stack}

### Core
- **React 18.3.1** - Framework principal
- **TypeScript 5.8.3** - Tipagem estática
- **Vite 5.4.19** - Build tool e dev server
- **React Router DOM 6.30.1** - Roteamento

### UI Framework
- **Tailwind CSS 3.4.17** - Utility-first CSS
- **shadcn/ui** - Componentes baseados em Radix UI
- **Radix UI** - Componentes primitivos acessíveis
- **Lucide React 0.462.0** - Ícones

### State Management
- **TanStack Query 5.83.0** - Server state
- **React Context** - Client state

### Backend Integration
- **Supabase 2.90.1** - Backend as a Service
- **OpenAI 6.16.0** - Integração com IA

### Outras Libs Importantes
- **React Hook Form 7.61.1** - Formulários
- **Zod 3.25.76** - Validação de schemas
- **Sonner 1.7.4** - Toast notifications
- **date-fns 3.6.0** - Manipulação de datas


---

## 📁 ESTRUTURA DE PASTAS {#estrutura}

```
projeto/
├── public/
│   ├── assets-collection/     # Assets do jogo
│   ├── favicon.ico
│   └── robots.txt
├── src/
│   ├── components/
│   │   ├── ui/               # Componentes shadcn/ui (50+ componentes)
│   │   ├── layout/           # Header, Sidebar, MainLayout
│   │   ├── editor/           # Editor de código e canvas
│   │   ├── preview/          # Preview do jogo
│   │   ├── project/          # Gerenciamento de projetos
│   │   ├── templates/        # Templates de jogos
│   │   ├── assets/           # Gerenciamento de assets
│   │   ├── chat/             # Chat com IA
│   │   ├── cost/             # Dashboard de custos
│   │   ├── deployment/       # Deploy
│   │   ├── dialogue/         # Sistema de diálogos
│   │   ├── export/           # Exportação de jogos
│   │   ├── github/           # Integração GitHub
│   │   ├── workspace/        # Workspace principal
│   │   ├── demo/             # Demos e showcases
│   │   ├── ErrorBoundary.tsx
│   │   └── NavLink.tsx
│   ├── contexts/
│   │   └── GameContext.tsx   # Context principal do jogo
│   ├── hooks/
│   │   ├── use-mobile.tsx
│   │   ├── use-toast.ts
│   │   ├── useAssets.ts
│   │   ├── useDeployment.ts
│   │   ├── useGitHub.ts
│   │   ├── useLocalProject.ts
│   │   ├── useOpenAI.ts
│   │   ├── useProject.ts
│   │   ├── useSSOT.ts
│   │   └── useStorage.ts
│   ├── integrations/
│   │   └── supabase/         # Cliente e tipos Supabase
│   ├── lib/
│   │   ├── ai/               # Lógica de IA
│   │   ├── ai-assets/        # Geração de assets com IA
│   │   ├── ai-music/         # Geração de música
│   │   ├── assets/           # Gerenciamento de assets
│   │   ├── compiler/         # Compilador de código
│   │   ├── game/             # Engine do jogo
│   │   ├── templates/        # Templates de jogos
│   │   ├── systems/          # Sistemas do jogo
│   │   └── utils.ts          # Utilitários
│   ├── pages/
│   │   ├── Index.tsx         # Página principal
│   │   ├── Assets.tsx        # Gerenciamento de assets
│   │   ├── ChatTest.tsx      # Teste de chat
│   │   ├── Deploy.tsx        # Deploy
│   │   ├── TestGame.tsx      # Teste de jogos
│   │   └── NotFound.tsx      # 404
│   ├── types/
│   │   └── project.ts        # Tipos TypeScript
│   ├── config/
│   │   └── ssot.ts           # Single Source of Truth
│   ├── App.tsx               # Componente raiz
│   ├── main.tsx              # Entry point
│   └── index.css             # Estilos globais
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── components.json           # Config shadcn/ui
└── postcss.config.js
```


---

## ⚙️ CONFIGURAÇÕES BASE {#configuracoes}

### 1. package.json (Copie e cole este arquivo completo)

```json
{
  "name": "seu-projeto",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  },
  "dependencies": {
    "@hookform/resolvers": "^3.10.0",
    "@radix-ui/react-accordion": "^1.2.11",
    "@radix-ui/react-alert-dialog": "^1.1.14",
    "@radix-ui/react-avatar": "^1.1.10",
    "@radix-ui/react-checkbox": "^1.3.2",
    "@radix-ui/react-dialog": "^1.1.14",
    "@radix-ui/react-dropdown-menu": "^2.1.15",
    "@radix-ui/react-label": "^2.1.7",
    "@radix-ui/react-popover": "^1.1.14",
    "@radix-ui/react-progress": "^1.1.7",
    "@radix-ui/react-scroll-area": "^1.2.9",
    "@radix-ui/react-select": "^2.2.5",
    "@radix-ui/react-separator": "^1.1.7",
    "@radix-ui/react-slider": "^1.3.5",
    "@radix-ui/react-slot": "^1.2.3",
    "@radix-ui/react-switch": "^1.2.5",
    "@radix-ui/react-tabs": "^1.1.12",
    "@radix-ui/react-toast": "^1.2.14",
    "@radix-ui/react-tooltip": "^1.2.7",
    "@supabase/supabase-js": "^2.90.1",
    "@tanstack/react-query": "^5.83.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "cmdk": "^1.1.1",
    "date-fns": "^3.6.0",
    "lucide-react": "^0.462.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-hook-form": "^7.61.1",
    "react-router-dom": "^6.30.1",
    "sonner": "^1.7.4",
    "tailwind-merge": "^2.6.0",
    "tailwindcss-animate": "^1.0.7",
    "zod": "^3.25.76"
  },
  "devDependencies": {
    "@types/node": "^22.16.5",
    "@types/react": "^18.3.23",
    "@types/react-dom": "^18.3.7",
    "@vitejs/plugin-react-swc": "^3.11.0",
    "autoprefixer": "^10.4.21",
    "eslint": "^9.32.0",
    "postcss": "^8.5.6",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.8.3",
    "vite": "^5.4.19"
  }
}
```


### 2. vite.config.ts

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

### 3. tsconfig.json

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ],
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### 4. tsconfig.app.json

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}
```

### 5. tsconfig.node.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```


### 6. tailwind.config.ts (TEMA COMPLETO - COPIE TUDO)

```typescript
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}"
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        neon: {
          cyan: "hsl(var(--neon-cyan))",
          magenta: "hsl(var(--neon-magenta))",
          green: "hsl(var(--neon-green))",
          orange: "hsl(var(--neon-orange))",
          purple: "hsl(var(--neon-purple))",
        },
        surface: {
          1: "hsl(var(--surface-1))",
          2: "hsl(var(--surface-2))",
          3: "hsl(var(--surface-3))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          from: { backgroundPosition: "200% 0" },
          to: { backgroundPosition: "-200% 0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.3s ease-out",
        shimmer: "shimmer 3s linear infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
```


### 7. postcss.config.js

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

### 8. components.json (Config shadcn/ui)

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```


---

## 🎨 TEMA E ESTILOS {#tema}

### src/index.css (COPIE COMPLETO - Tema Dark Gaming)

```css
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Dark gaming theme */
    --background: 225 25% 6%;
    --foreground: 210 40% 98%;
    --card: 225 25% 8%;
    --card-foreground: 210 40% 98%;
    --popover: 225 25% 10%;
    --popover-foreground: 210 40% 98%;
    --primary: 186 100% 45%;
    --primary-foreground: 225 25% 6%;
    --secondary: 300 100% 45%;
    --secondary-foreground: 210 40% 98%;
    --muted: 225 20% 15%;
    --muted-foreground: 215 20% 55%;
    --accent: 186 100% 45%;
    --accent-foreground: 225 25% 6%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 210 40% 98%;
    --border: 225 20% 18%;
    --input: 225 20% 15%;
    --ring: 186 100% 45%;
    --radius: 0.5rem;

    /* Gaming colors */
    --neon-cyan: 186 100% 45%;
    --neon-magenta: 300 100% 45%;
    --neon-green: 150 100% 45%;
    --neon-orange: 25 100% 55%;
    --neon-purple: 270 100% 60%;

    --surface-1: 225 25% 8%;
    --surface-2: 225 25% 10%;
    --surface-3: 225 25% 12%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground font-sans antialiased;
    font-family: 'Space Grotesk', system-ui, sans-serif;
  }
  code, pre, .font-mono {
    font-family: 'JetBrains Mono', monospace;
  }
}

@layer components {
  .glass-panel {
    @apply bg-card/80 backdrop-blur-xl border border-border/50;
  }
  .neon-glow {
    box-shadow: 0 0 20px hsl(var(--primary) / 0.3), 0 0 40px hsl(var(--primary) / 0.1);
  }
  .neon-text {
    text-shadow: 0 0 10px hsl(var(--primary) / 0.5), 0 0 20px hsl(var(--primary) / 0.3);
  }
}
```


---

## 🚀 ARQUIVOS PRINCIPAIS {#principais}

### index.html

```html
<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Seu Projeto</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.ico" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### src/main.tsx

```typescript
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

createRoot(document.getElementById("root")!).render(<App />);
```

### src/App.tsx

```typescript
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";

const Index = lazy(() => import("./pages/Index"));
const NotFound = lazy(() => import("./pages/NotFound"));

const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
```


### src/lib/utils.ts

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### src/pages/Index.tsx

```typescript
const Index = () => {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold neon-text mb-4">
          Bem-vindo ao Projeto
        </h1>
        <p className="text-muted-foreground">
          Frontend configurado e pronto para uso
        </p>
      </div>
    </div>
  );
};

export default Index;
```

### src/pages/NotFound.tsx

```typescript
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const NotFound = () => {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-4">404</h1>
        <p className="text-xl text-muted-foreground mb-8">
          Página não encontrada
        </p>
        <Link to="/">
          <Button>Voltar para Home</Button>
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
```


---

## 🔧 COMPONENTES UI (shadcn/ui) {#componentes}

### Instalação dos Componentes

Este projeto usa **shadcn/ui**. Para instalar os componentes:

```bash
# Instalar CLI do shadcn/ui
npx shadcn@latest init

# Instalar componentes individuais
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add dialog
npx shadcn@latest add input
npx shadcn@latest add label
npx shadcn@latest add select
npx shadcn@latest add tabs
npx shadcn@latest add toast
npx shadcn@latest add tooltip
npx shadcn@latest add dropdown-menu
npx shadcn@latest add scroll-area
npx shadcn@latest add separator
npx shadcn@latest add switch
npx shadcn@latest add slider
npx shadcn@latest add progress
npx shadcn@latest add avatar
npx shadcn@latest add badge
npx shadcn@latest add accordion
npx shadcn@latest add alert-dialog
npx shadcn@latest add checkbox
npx shadcn@latest add popover
```

### Lista Completa de Componentes UI Usados

O projeto usa 50+ componentes do shadcn/ui:
- accordion
- alert-dialog
- alert
- aspect-ratio
- avatar
- badge
- breadcrumb
- button
- calendar
- card
- carousel
- chart
- checkbox
- collapsible
- command
- context-menu
- dialog
- drawer
- dropdown-menu
- form
- hover-card
- input-otp
- input
- label
- menubar
- navigation-menu
- pagination
- popover
- progress
- radio-group
- resizable
- scroll-area
- select
- separator
- sheet
- sidebar
- skeleton
- slider
- sonner (toast)
- switch
- table
- tabs
- textarea
- toast
- toaster
- toggle-group
- toggle
- tooltip


---

## 🔌 INTEGRAÇÃO COM SUPABASE {#supabase}

### src/integrations/supabase/client.ts

```typescript
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_PUBLISHABLE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

export const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: {
    storage: localStorage,
    persistSession: true,
    autoRefreshToken: true,
  }
});
```

### .env (Crie este arquivo na raiz)

```env
VITE_SUPABASE_URL=sua_url_aqui
VITE_SUPABASE_PUBLISHABLE_KEY=sua_chave_aqui
```

---

## 📦 PASSO A PASSO PARA REPLICAR {#passos}

### 1. Criar Novo Projeto

```bash
# Criar projeto Vite + React + TypeScript
npm create vite@latest meu-projeto -- --template react-swc-ts
cd meu-projeto
```

### 2. Copiar Arquivos de Configuração

Copie e cole os seguintes arquivos (conteúdo acima):
- `package.json`
- `vite.config.ts`
- `tsconfig.json`
- `tsconfig.app.json`
- `tsconfig.node.json`
- `tailwind.config.ts`
- `postcss.config.js`
- `components.json`

### 3. Instalar Dependências

```bash
npm install
```

### 4. Criar Estrutura de Pastas

```bash
# Windows (CMD)
mkdir src\components\ui
mkdir src\components\layout
mkdir src\lib
mkdir src\hooks
mkdir src\pages
mkdir src\contexts
mkdir src\integrations\supabase
mkdir src\types
mkdir public

# Linux/Mac
mkdir -p src/components/ui
mkdir -p src/components/layout
mkdir -p src/lib
mkdir -p src/hooks
mkdir -p src/pages
mkdir -p src/contexts
mkdir -p src/integrations/supabase
mkdir -p src/types
mkdir -p public
```

### 5. Copiar Arquivos Base

Copie e cole o conteúdo dos arquivos:
- `index.html`
- `src/main.tsx`
- `src/App.tsx`
- `src/index.css`
- `src/lib/utils.ts`
- `src/pages/Index.tsx`
- `src/pages/NotFound.tsx`

### 6. Instalar Componentes shadcn/ui

```bash
npx shadcn@latest init
```

Responda as perguntas:
- Style: Default
- Base color: Slate
- CSS variables: Yes

Depois instale os componentes que precisar:
```bash
npx shadcn@latest add button card dialog input toast
```

### 7. Configurar Variáveis de Ambiente

Crie `.env` na raiz:
```env
VITE_SUPABASE_URL=sua_url
VITE_SUPABASE_PUBLISHABLE_KEY=sua_chave
```

### 8. Rodar o Projeto

```bash
npm run dev
```

Acesse: `http://localhost:8080`


---

## 🎯 FEATURES PRINCIPAIS DO FRONTEND {#features}

### 1. Sistema de Tema Dark Gaming
- Cores neon (cyan, magenta, green, orange, purple)
- Efeitos de glow e neon
- Gradientes personalizados
- Fontes: Space Grotesk (sans) e JetBrains Mono (mono)

### 2. Componentes UI Completos
- 50+ componentes do shadcn/ui
- Totalmente acessíveis (Radix UI)
- Customizáveis via Tailwind
- Animações suaves

### 3. Roteamento
- React Router DOM v6
- Lazy loading de páginas
- Loading states
- 404 page

### 4. State Management
- TanStack Query para server state
- React Context para client state
- Local storage integration

### 5. Integração Backend
- Supabase client configurado
- Auth ready
- Real-time ready

### 6. Performance
- Code splitting automático
- Lazy loading
- SWC para build rápido
- Otimização de bundle

### 7. Developer Experience
- TypeScript strict mode
- ESLint configurado
- Hot Module Replacement
- Path aliases (@/)

---

## 🎨 EXEMPLOS DE USO {#exemplos}

### Exemplo 1: Criar um Card com Glow

```typescript
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export const GlowCard = () => {
  return (
    <Card className="glass-panel neon-glow">
      <CardHeader>
        <CardTitle className="neon-text">Título com Neon</CardTitle>
      </CardHeader>
      <CardContent>
        <p>Conteúdo do card com efeito glass e glow</p>
      </CardContent>
    </Card>
  );
};
```

### Exemplo 2: Botão com Gradiente

```typescript
import { Button } from "@/components/ui/button";

export const GradientButton = () => {
  return (
    <Button className="bg-gradient-to-r from-primary to-secondary">
      Botão Gradiente
    </Button>
  );
};
```

### Exemplo 3: Dialog Modal

```typescript
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export const MyDialog = () => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>Abrir Modal</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Título do Modal</DialogTitle>
        </DialogHeader>
        <p>Conteúdo do modal aqui</p>
      </DialogContent>
    </Dialog>
  );
};
```


---

## 🔥 RECURSOS AVANÇADOS {#avancados}

### Layout System

O projeto usa um sistema de layout modular:

```typescript
// src/components/layout/MainLayout.tsx
import { ReactNode } from "react";

interface MainLayoutProps {
  children: ReactNode;
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  return (
    <div className="h-screen flex overflow-hidden bg-background">
      <aside className="w-64 border-r border-border">
        {/* Sidebar */}
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="h-16 border-b border-border">
          {/* Header */}
        </header>
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
```

### Context Pattern

```typescript
// src/contexts/AppContext.tsx
import { createContext, useContext, useState, ReactNode } from "react";

interface AppContextType {
  data: any;
  setData: (data: any) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const [data, setData] = useState(null);

  return (
    <AppContext.Provider value={{ data, setData }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }
  return context;
};
```

### Custom Hooks Pattern

```typescript
// src/hooks/useLocalStorage.ts
import { useState, useEffect } from "react";

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(error);
      return initialValue;
    }
  });

  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(error);
    }
  };

  return [storedValue, setValue] as const;
}
```

### TanStack Query Pattern

```typescript
// src/hooks/useData.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

export function useData() {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["data"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("table")
        .select("*");
      if (error) throw error;
      return data;
    },
  });

  const mutation = useMutation({
    mutationFn: async (newData: any) => {
      const { data, error } = await supabase
        .from("table")
        .insert(newData);
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["data"] });
    },
  });

  return { data, isLoading, error, mutation };
}
```


---

## 📚 ESTRUTURA DE COMPONENTES ESPECÍFICOS {#especificos}

### Componentes de Layout

```
src/components/layout/
├── Header.tsx          # Cabeçalho com navegação
├── MainLayout.tsx      # Layout principal da aplicação
└── ProjectSidebar.tsx  # Sidebar de projetos
```

### Componentes de Editor

```
src/components/editor/
├── CodeEditor.tsx      # Editor de código
├── LayersPanel.tsx     # Painel de camadas
└── SceneCanvas.tsx     # Canvas de cena
```

### Componentes de Preview

```
src/components/preview/
├── GameCanvas.tsx      # Canvas do jogo
└── GamePreview.tsx     # Preview completo
```

### Componentes de Projeto

```
src/components/project/
├── AutoSaveIndicator.tsx    # Indicador de auto-save
├── NewProjectDialog.tsx     # Dialog de novo projeto
└── ProjectListDialog.tsx    # Lista de projetos
```

### Componentes de Assets

```
src/components/assets/
├── AssetCard.tsx            # Card de asset
├── AssetFilters.tsx         # Filtros de assets
├── AssetLibrary.tsx         # Biblioteca de assets
├── AssetPreviewModal.tsx    # Preview de asset
├── AssetUploadDialog.tsx    # Upload de assets
├── SpriteGenerator.tsx      # Gerador de sprites
└── MusicGenerator.tsx       # Gerador de música
```

---

## 🛠️ UTILITÁRIOS E HELPERS {#utils}

### src/lib/utils.ts (Expandido)

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: Date): string {
  return new Intl.DateTimeFormat("pt-BR").format(date);
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
```


---

## 🎯 CHECKLIST DE REPLICAÇÃO {#checklist}

### ✅ Fase 1: Setup Inicial
- [ ] Criar projeto Vite + React + TypeScript
- [ ] Copiar `package.json` e instalar dependências
- [ ] Copiar arquivos de configuração (vite, tsconfig, tailwind, postcss)
- [ ] Copiar `components.json`
- [ ] Criar estrutura de pastas

### ✅ Fase 2: Configuração Base
- [ ] Copiar `index.html`
- [ ] Copiar `src/main.tsx`
- [ ] Copiar `src/App.tsx`
- [ ] Copiar `src/index.css` (tema completo)
- [ ] Copiar `src/lib/utils.ts`

### ✅ Fase 3: Componentes UI
- [ ] Instalar shadcn/ui CLI
- [ ] Instalar componentes básicos (button, card, dialog, input)
- [ ] Instalar componentes de formulário (form, label, select)
- [ ] Instalar componentes de feedback (toast, alert)
- [ ] Instalar componentes de navegação (tabs, dropdown)

### ✅ Fase 4: Páginas
- [ ] Criar `src/pages/Index.tsx`
- [ ] Criar `src/pages/NotFound.tsx`
- [ ] Adicionar outras páginas conforme necessário

### ✅ Fase 5: Integração Backend
- [ ] Criar `src/integrations/supabase/client.ts`
- [ ] Configurar `.env` com variáveis do Supabase
- [ ] Testar conexão com Supabase

### ✅ Fase 6: Contextos e Hooks
- [ ] Criar contextos necessários em `src/contexts/`
- [ ] Criar hooks customizados em `src/hooks/`
- [ ] Integrar TanStack Query

### ✅ Fase 7: Layout
- [ ] Criar componentes de layout em `src/components/layout/`
- [ ] Implementar Header
- [ ] Implementar Sidebar
- [ ] Implementar MainLayout

### ✅ Fase 8: Teste e Deploy
- [ ] Rodar `npm run dev` e testar localmente
- [ ] Verificar responsividade
- [ ] Testar navegação entre páginas
- [ ] Build de produção: `npm run build`
- [ ] Deploy

---

## 🚨 PROBLEMAS COMUNS E SOLUÇÕES {#troubleshooting}

### Erro: "Cannot find module '@/...'"
**Solução:** Verifique se o `vite.config.ts` tem o alias configurado:
```typescript
resolve: {
  alias: {
    "@": path.resolve(__dirname, "./src"),
  },
}
```

### Erro: Tailwind não está funcionando
**Solução:** 
1. Verifique se `tailwind.config.ts` está correto
2. Verifique se `postcss.config.js` existe
3. Verifique se `@tailwind` directives estão no `index.css`

### Erro: shadcn/ui componentes não encontrados
**Solução:** Instale os componentes:
```bash
npx shadcn@latest add button
```

### Erro: Supabase não conecta
**Solução:** 
1. Verifique se `.env` existe e tem as variáveis corretas
2. Verifique se as variáveis começam com `VITE_`
3. Reinicie o servidor de desenvolvimento

### Erro: TypeScript errors
**Solução:** 
1. Verifique se todos os `tsconfig` files estão corretos
2. Rode `npm install` novamente
3. Reinicie o VS Code


---

## 📦 COMANDOS ÚTEIS {#comandos}

### Desenvolvimento
```bash
npm run dev              # Inicia servidor de desenvolvimento
npm run build            # Build de produção
npm run preview          # Preview do build
npm run lint             # Roda ESLint
```

### shadcn/ui
```bash
npx shadcn@latest init                    # Inicializar shadcn/ui
npx shadcn@latest add [component]         # Adicionar componente
npx shadcn@latest add button card dialog  # Adicionar múltiplos
```

### Instalação de Dependências Específicas
```bash
# UI e Styling
npm install tailwindcss-animate class-variance-authority clsx tailwind-merge

# Formulários
npm install react-hook-form @hookform/resolvers zod

# Ícones
npm install lucide-react

# Notificações
npm install sonner

# Backend
npm install @supabase/supabase-js

# State Management
npm install @tanstack/react-query

# Roteamento
npm install react-router-dom

# Utilitários
npm install date-fns
```

---

## 🎨 PALETA DE CORES {#cores}

### Cores Principais (HSL)
```css
/* Background e Foreground */
--background: 225 25% 6%      /* Azul escuro profundo */
--foreground: 210 40% 98%     /* Branco quase puro */

/* Primary (Cyan Neon) */
--primary: 186 100% 45%       /* Cyan vibrante */
--primary-foreground: 225 25% 6%

/* Secondary (Magenta Neon) */
--secondary: 300 100% 45%     /* Magenta vibrante */

/* Cores Neon */
--neon-cyan: 186 100% 45%     /* #00D9FF */
--neon-magenta: 300 100% 45%  /* #E600E6 */
--neon-green: 150 100% 45%    /* #00E673 */
--neon-orange: 25 100% 55%    /* #FF8C1A */
--neon-purple: 270 100% 60%   /* #9933FF */

/* Surfaces */
--surface-1: 225 25% 8%       /* Mais escuro */
--surface-2: 225 25% 10%      /* Médio */
--surface-3: 225 25% 12%      /* Mais claro */
```

### Uso das Cores
```typescript
// Em componentes
<div className="bg-primary text-primary-foreground">Primary</div>
<div className="bg-secondary text-secondary-foreground">Secondary</div>
<div className="bg-neon-cyan">Neon Cyan</div>
<div className="bg-surface-1">Surface 1</div>

// Com opacity
<div className="bg-primary/50">Primary 50%</div>
<div className="bg-neon-magenta/20">Magenta 20%</div>
```

---

## 🎭 ANIMAÇÕES E EFEITOS {#animacoes}

### Classes Utilitárias Customizadas

```css
/* Glass Effect */
.glass-panel {
  @apply bg-card/80 backdrop-blur-xl border border-border/50;
}

/* Neon Glow */
.neon-glow {
  box-shadow: 0 0 20px hsl(var(--primary) / 0.3), 
              0 0 40px hsl(var(--primary) / 0.1);
}

/* Neon Text */
.neon-text {
  text-shadow: 0 0 10px hsl(var(--primary) / 0.5), 
               0 0 20px hsl(var(--primary) / 0.3);
}
```

### Animações Disponíveis

```typescript
// Fade In
<div className="animate-fade-in">Fade In</div>

// Shimmer
<div className="animate-shimmer">Shimmer</div>

// Accordion
<div className="animate-accordion-down">Accordion Down</div>
<div className="animate-accordion-up">Accordion Up</div>

// Pulse Slow
<div className="animate-pulse-slow">Pulse Slow</div>
```


---

## 🔐 VARIÁVEIS DE AMBIENTE {#env}

### .env (Raiz do Projeto)

```env
# Supabase
VITE_SUPABASE_URL=https://seu-projeto.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sua_chave_publica_aqui

# OpenAI (se usar)
VITE_OPENAI_API_KEY=sua_chave_openai_aqui

# Outras APIs
VITE_API_URL=https://sua-api.com
```

### .env.example (Para compartilhar)

```env
# Supabase
VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=

# OpenAI
VITE_OPENAI_API_KEY=

# API
VITE_API_URL=
```

### Uso no Código

```typescript
// Acessar variáveis de ambiente
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

// Verificar se existe
if (!supabaseUrl || !supabaseKey) {
  throw new Error("Missing Supabase environment variables");
}
```

---

## 📱 RESPONSIVIDADE {#responsivo}

### Breakpoints Tailwind

```typescript
// Breakpoints padrão
sm: '640px'   // Small devices
md: '768px'   // Medium devices
lg: '1024px'  // Large devices
xl: '1280px'  // Extra large devices
2xl: '1400px' // 2X Extra large (customizado)
```

### Exemplos de Uso

```typescript
// Mobile first
<div className="text-sm md:text-base lg:text-lg">
  Texto responsivo
</div>

// Grid responsivo
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Cards */}
</div>

// Flex responsivo
<div className="flex flex-col md:flex-row gap-4">
  {/* Conteúdo */}
</div>

// Padding responsivo
<div className="p-4 md:p-6 lg:p-8">
  {/* Conteúdo */}
</div>

// Esconder em mobile
<div className="hidden md:block">
  Desktop only
</div>

// Mostrar apenas em mobile
<div className="block md:hidden">
  Mobile only
</div>
```

---

## 🧪 TESTES {#testes}

### Configuração de Testes (Opcional)

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

### vitest.config.ts

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### src/test/setup.ts

```typescript
import '@testing-library/jest-dom';
```

### Exemplo de Teste

```typescript
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui/button';

describe('Button', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
});
```


---

## 🚀 DEPLOY {#deploy}

### Build de Produção

```bash
npm run build
```

Isso gera a pasta `dist/` com os arquivos otimizados.

### Deploy em Vercel

```bash
# Instalar Vercel CLI
npm i -g vercel

# Deploy
vercel

# Deploy de produção
vercel --prod
```

### Deploy em Netlify

```bash
# Instalar Netlify CLI
npm i -g netlify-cli

# Deploy
netlify deploy

# Deploy de produção
netlify deploy --prod
```

### Deploy em GitHub Pages

```bash
# Instalar gh-pages
npm install -D gh-pages

# Adicionar ao package.json
"scripts": {
  "predeploy": "npm run build",
  "deploy": "gh-pages -d dist"
}

# Deploy
npm run deploy
```

### Configuração para Deploy

#### vercel.json
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

#### netlify.toml
```toml
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

---

## 📊 PERFORMANCE {#performance}

### Otimizações Implementadas

1. **Code Splitting**: Lazy loading de páginas
2. **Tree Shaking**: Vite remove código não usado
3. **Minificação**: Build otimizado
4. **Compression**: Gzip/Brotli automático
5. **Image Optimization**: Use WebP quando possível
6. **Font Loading**: Fontes do Google otimizadas

### Dicas de Performance

```typescript
// 1. Lazy load de componentes
const HeavyComponent = lazy(() => import('./HeavyComponent'));

// 2. Memoização
const MemoizedComponent = memo(({ data }) => {
  return <div>{data}</div>;
});

// 3. useMemo para cálculos pesados
const expensiveValue = useMemo(() => {
  return heavyCalculation(data);
}, [data]);

// 4. useCallback para funções
const handleClick = useCallback(() => {
  doSomething();
}, []);

// 5. Virtualização para listas grandes
import { useVirtualizer } from '@tanstack/react-virtual';
```

---

## 🎓 RECURSOS DE APRENDIZADO {#recursos}

### Documentação Oficial
- [React](https://react.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)
- [Radix UI](https://www.radix-ui.com/)
- [TanStack Query](https://tanstack.com/query)
- [React Router](https://reactrouter.com/)
- [Supabase](https://supabase.com/docs)

### Tutoriais Recomendados
- shadcn/ui: https://ui.shadcn.com/docs
- Tailwind CSS: https://tailwindcss.com/docs
- React Query: https://tanstack.com/query/latest/docs

---

## 🎯 RESUMO EXECUTIVO {#resumo}

### O que você tem aqui:

✅ **Frontend Moderno Completo**
- React 18 + TypeScript + Vite
- 50+ componentes UI prontos (shadcn/ui)
- Tema dark gaming com efeitos neon
- Totalmente responsivo
- Performance otimizada

✅ **Arquitetura Profissional**
- Path aliases (@/)
- Code splitting automático
- Lazy loading de páginas
- Context API + TanStack Query
- Integração Supabase pronta

✅ **Developer Experience**
- Hot Module Replacement
- TypeScript strict mode
- ESLint configurado
- Componentes reutilizáveis
- Documentação completa

### Para replicar:

1. **Copie os arquivos de configuração** (package.json, vite.config.ts, etc)
2. **Instale as dependências** (`npm install`)
3. **Copie a estrutura de pastas**
4. **Copie os arquivos base** (main.tsx, App.tsx, index.css)
5. **Instale componentes shadcn/ui** conforme necessário
6. **Configure variáveis de ambiente** (.env)
7. **Rode o projeto** (`npm run dev`)

### Tempo estimado de replicação:
- Setup básico: **30 minutos**
- Com todos componentes: **2-3 horas**
- Customização completa: **1 dia**

---

## 📞 SUPORTE {#suporte}

Se tiver dúvidas durante a replicação:

1. Verifique o checklist de replicação
2. Consulte a seção de troubleshooting
3. Revise a documentação oficial das libs
4. Verifique se todas as dependências foram instaladas

**Boa sorte com seu projeto! 🚀**

