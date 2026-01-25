# 🎨 Sistema Visual Ordax - Documentação

## Visão Geral

O Ordax agora possui um sistema visual completo baseado no guia de replicação, com tema dark gaming, efeitos neon e componentes modernos.

## 🎯 Principais Mudanças Implementadas

### 1. Tema Dark Gaming

**Cores Principais:**
- Background: `hsl(225 25% 6%)` - Azul escuro profundo
- Primary: `hsl(186 100% 45%)` - Cyan neon vibrante
- Secondary: `hsl(300 100% 45%)` - Magenta neon

**Cores Neon:**
- Cyan: `hsl(186 100% 45%)`
- Magenta: `hsl(300 100% 45%)`
- Green: `hsl(150 100% 45%)`
- Orange: `hsl(25 100% 55%)`
- Purple: `hsl(270 100% 60%)`

**Surfaces (Camadas de Profundidade):**
- Surface 1: `hsl(225 25% 8%)` - Mais escuro
- Surface 2: `hsl(225 25% 10%)` - Médio
- Surface 3: `hsl(225 25% 12%)` - Mais claro

### 2. Tipografia

**Fontes Customizadas:**
- **Space Grotesk** - Fonte sans-serif para UI
- **JetBrains Mono** - Fonte monospace para código

Importadas via Google Fonts no `index.css`.

### 3. Efeitos Visuais

**Classes Utilitárias:**

```css
/* Glass Panel - Efeito vidro fosco */
.glass-panel {
  @apply bg-card/80 backdrop-blur-xl border border-border/50;
}

/* Neon Glow - Brilho neon */
.neon-glow {
  box-shadow: 0 0 20px hsl(var(--primary) / 0.3), 
              0 0 40px hsl(var(--primary) / 0.1);
}

/* Neon Text - Texto com brilho */
.neon-text {
  text-shadow: 0 0 10px hsl(var(--primary) / 0.5), 
               0 0 20px hsl(var(--primary) / 0.3);
}
```

### 4. Animações

**Novas Animações:**
- `animate-fade-in` - Fade in suave com movimento
- `animate-shimmer` - Efeito shimmer/brilho
- `animate-pulse` - Pulse padrão do Tailwind

### 5. Componentes Atualizados

**OrdaxWorkspace:**
- Header com efeito glass e neon text
- Badge com cores neon e bordas brilhantes
- Botão "View Demo" para acessar showcase
- ResizableHandle com transição de cor

**ChatPanel:**
- Header com indicador de status (ponto verde pulsante)
- Mensagens com glass-panel effect
- Input com estilo monospace
- Botão de envio com neon-glow

**EditorPanel:**
- Tabs com estilo monospace
- Cards de módulos com hover effects
- Badges ativos com neon-glow
- Search input com glass effect

**PreviewPanel:**
- Header com badges de status
- FPS counter com cor neon-green
- Botões com glass-panel
- Card de "aguardando spec" com neon-glow

### 6. Novos Componentes

**VisualShowcase (`src/components/demo/VisualShowcase.tsx`):**
- Demonstração completa do sistema visual
- Cards com diferentes efeitos
- Paleta de cores neon
- Exemplos de tipografia
- Demonstração de animações

**ErrorBoundary (`src/components/ErrorBoundary.tsx`):**
- Tratamento de erros com UI consistente
- Card com glass-panel effect
- Mensagem de erro em monospace

**Demo Page (`src/pages/Demo.tsx`):**
- Página dedicada para showcase visual
- Botão de voltar ao workspace
- Demonstração de todos os componentes

**NotFound Page (atualizada):**
- Design moderno com glass-panel
- Botões para home e demo
- Efeito neon-glow

## 🚀 Como Usar

### Classes Utilitárias

```tsx
// Glass Panel
<div className="glass-panel">Conteúdo</div>

// Neon Glow
<div className="neon-glow">Elemento com brilho</div>

// Neon Text
<h1 className="neon-text">Título Neon</h1>

// Cores Neon
<div className="bg-neon-cyan">Cyan</div>
<div className="bg-neon-magenta">Magenta</div>
<div className="bg-neon-green">Green</div>

// Surfaces
<div className="bg-surface-1">Surface 1</div>
<div className="bg-surface-2">Surface 2</div>
<div className="bg-surface-3">Surface 3</div>

// Animações
<div className="animate-fade-in">Fade In</div>
<div className="animate-shimmer">Shimmer</div>
```

### Badges com Efeitos

```tsx
// Badge Neon
<Badge className="bg-primary/20 text-primary border-primary/40 neon-glow">
  Active
</Badge>

// Badge Glass
<Badge className="glass-panel border-border/50">
  Status
</Badge>
```

### Botões com Efeitos

```tsx
// Botão com Neon Glow
<Button className="neon-glow">Primary Action</Button>

// Botão Glass
<Button variant="outline" className="glass-panel border-border/50">
  Secondary
</Button>
```

## 📁 Arquivos Modificados

### Configuração
- ✅ `tailwind.config.ts` - Cores neon, fontes, animações
- ✅ `src/index.css` - Tema completo, classes utilitárias

### Componentes Ordax
- ✅ `src/components/ordax/OrdaxWorkspace.tsx`
- ✅ `src/components/ordax/ChatPanel.tsx`
- ✅ `src/components/ordax/EditorPanel.tsx`
- ✅ `src/components/ordax/PreviewPanel.tsx`

### Novos Componentes
- ✅ `src/components/demo/VisualShowcase.tsx`
- ✅ `src/components/ErrorBoundary.tsx`

### Páginas
- ✅ `src/pages/Demo.tsx` (nova)
- ✅ `src/pages/NotFound.tsx` (atualizada)
- ✅ `src/App.tsx` (rotas e ErrorBoundary)

## 🎨 Paleta de Cores Completa

```typescript
// Tailwind Config
colors: {
  neon: {
    cyan: "hsl(var(--neon-cyan))",      // #00D9FF
    magenta: "hsl(var(--neon-magenta))", // #E600E6
    green: "hsl(var(--neon-green))",    // #00E673
    orange: "hsl(var(--neon-orange))",  // #FF8C1A
    purple: "hsl(var(--neon-purple))",  // #9933FF
  },
  surface: {
    1: "hsl(var(--surface-1))",
    2: "hsl(var(--surface-2))",
    3: "hsl(var(--surface-3))",
  },
}
```

## 🔧 Comandos

```bash
# Desenvolvimento
npm run dev

# Acessar workspace
http://localhost:8080/

# Acessar demo visual
http://localhost:8080/demo

# Build
npm run build
```

## 📚 Recursos

- **Fontes**: Google Fonts (Space Grotesk, JetBrains Mono)
- **UI Components**: shadcn/ui
- **Animações**: Tailwind CSS + Custom keyframes
- **Efeitos**: CSS custom properties + Tailwind utilities

## 🎯 Próximos Passos

Para continuar expandindo o sistema visual:

1. Adicionar mais variações de badges e botões
2. Criar componentes de loading com efeitos neon
3. Implementar transições de página
4. Adicionar mais animações customizadas
5. Criar variantes de cards (success, warning, error)
6. Implementar sistema de notificações com tema neon

## 💡 Dicas de Uso

1. **Combine efeitos**: Use `glass-panel` + `neon-glow` para destaque máximo
2. **Hierarquia visual**: Use surfaces (1, 2, 3) para criar profundidade
3. **Consistência**: Mantenha o uso de `font-mono` para código e dados técnicos
4. **Animações**: Use `animate-fade-in` em elementos que aparecem dinamicamente
5. **Cores neon**: Reserve para elementos importantes (CTAs, status, highlights)

---

**Sistema implementado com sucesso! 🎮✨**
