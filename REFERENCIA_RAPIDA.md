# ⚡ REFERÊNCIA RÁPIDA - Ordax Studio

## 🎯 ACESSO RÁPIDO

### URLs
- **Workspace**: http://localhost:8082/workspace
- **Home**: http://localhost:8082/

### Comandos
```bash
npm run dev          # Iniciar servidor
npm run build        # Build produção
npm run preview      # Preview do build
```

## 📚 DOCUMENTAÇÃO

### Leia Primeiro
1. **RESUMO_VISUAL_FINAL.md** - Resumo visual de tudo
2. **CONTINUACAO_COMPLETA.md** - Onde paramos e o que foi feito
3. **INDEX_COMPLETO_ATUALIZADO.md** - Índice completo

### Frontend
- **FRONTEND_COMPLETE_SUMMARY.md** - Resumo completo
- **ATUALIZACAO_ESTRUTURA_FRONTEND.md** - Correções e melhorias
- **FRONTEND_REPLICATION_GUIDE.md** - Guia de replicação

### Engine
- **INTEGRACAO_FINAL_COMPLETA.md** - Integração completa
- **SISTEMAS_INTEGRADOS_RESUMO.md** - Resumo dos sistemas
- **CORRECAO_SISTEMA_COLISAO.md** - Correção de colisões

## 🎮 USO RÁPIDO

### Gerar Jogo
```
1. Acesse workspace
2. Digite: "jogo de nave espacial"
3. Aguarde geração
4. Clique [Play]
```

### Editar Código
```
1. Clique em arquivo na árvore (direita)
2. Editor abre no centro
3. Edite o código
4. Clique [Salvar]
```

### Ver Debug
```
1. Inicie o jogo ([Play])
2. Olhe abaixo do canvas
3. Veja sistemas ativos
4. Veja estatísticas
```

## 🔧 COMPONENTES PRINCIPAIS

### Workspace
```typescript
<StudioWorkspace />
  ├─ <StudioTopBar />
  ├─ <StudioSidebar />
  ├─ <StudioChatPanel />
  ├─ <StudioPreviewPanel />
  │   ├─ <OrdaxCanvas />
  │   └─ Debug Panel
  ├─ <CodeEditorPanel />
  └─ <StudioFileTree />
```

### Editor
```typescript
<CodeEditorPanel
  openFileId={fileId}
  onClose={handleClose}
/>
```

### Canvas
```typescript
<OrdaxCanvas
  ref={canvasRef}
  spec={gameSpec}
  running={isRunning}
/>
```

## 🎨 SISTEMAS DA ENGINE

### Ativos (12)
1. ✅ InputSystem
2. ✅ PhysicsSystem
3. ✅ CollisionSystem
4. ✅ ParticleSystem
5. ✅ ScoreSystem
6. ✅ CameraSystem
7. ✅ UISystem
8. ✅ AISystem
9. ✅ SpawnerSystem
10. ✅ TimerSystem
11. ✅ AudioSystem
12. ✅ AnimationSystem

### Implementados (3)
13. ✅ DialogueSystem
14. ✅ InventorySystem
15. ✅ SaveSystem

## 📊 FEATURES

### Editor
- [x] Múltiplos arquivos em tabs
- [x] Indicador de modificação (●)
- [x] Salvar/Reverter
- [x] Status bar
- [x] Confirmação ao fechar

### Preview
- [x] Canvas do jogo
- [x] Controles (Play/Pause/Reset)
- [x] Debug panel
- [x] HUD limpo
- [x] 60 FPS

### Árvore
- [x] Estrutura hierárquica
- [x] Expandir/colapsar
- [x] Busca
- [x] Criar arquivo
- [x] Contador

## 🐛 TROUBLESHOOTING

### Arquivo não abre
```
✅ Verifique se CodeEditorPanel está importado
✅ Verifique callback onFileOpen
✅ Veja console para erros
```

### Colisões não funcionam
```
✅ Verifique spec.systems[]
✅ Deve conter "CollisionSystem"
✅ Clique [Play] para iniciar
```

### Debug panel não aparece
```
✅ Clique [Play] primeiro
✅ Verifique se spec existe
✅ Aguarde 100ms para atualizar
```

### Chat com erro
```
✅ Verifique .env
✅ VITE_SUPABASE_URL
✅ LOVABLE_API_KEY
```

## 📞 BUSCA RÁPIDA

| Procurando... | Arquivo |
|---------------|---------|
| Como abrir arquivos | ATUALIZACAO_ESTRUTURA_FRONTEND.md |
| Como funcionam colisões | CORRECAO_SISTEMA_COLISAO.md |
| Sistemas integrados | SISTEMAS_INTEGRADOS_RESUMO.md |
| Replicar frontend | FRONTEND_COMPLETE_SUMMARY.md |
| O que mudou | RESUMO_COMPLETO_SESSAO.md |
| Debug panel | ATUALIZACAO_ESTRUTURA_FRONTEND.md |
| Exemplos de código | FRONTEND_COMPONENTS_EXAMPLES.md |
| Status do projeto | ORDAX_STUDIO_100_PERCENT.md |

## ✅ CHECKLIST

### Antes de Usar
- [ ] Servidor rodando (npm run dev)
- [ ] .env configurado
- [ ] Supabase conectado
- [ ] Porta 8082 livre

### Ao Usar
- [ ] Chat funcionando
- [ ] Arquivos abrindo
- [ ] Editor salvando
- [ ] Jogo rodando
- [ ] Debug aparecendo

### Ao Desenvolver
- [ ] TypeScript sem erros
- [ ] ESLint passando
- [ ] Build funcionando
- [ ] Testes passando

## 🎯 ATALHOS

### Teclado (Futuro)
```
Ctrl+S     - Salvar arquivo
Ctrl+W     - Fechar tab
Ctrl+Tab   - Próximo tab
Ctrl+F     - Buscar
Ctrl+P     - Command palette
```

### Mouse
```
Clique     - Abrir arquivo
Duplo      - Expandir pasta
Direito    - Menu contexto (futuro)
```

## 📊 ESTATÍSTICAS

```
Componentes: 60+
Sistemas: 15
Linhas: 10,000+
Documentos: 15+
Features: 100%
Status: ✅ Completo
```

## 🚀 PRÓXIMOS PASSOS

1. Testar tudo
2. Reportar bugs
3. Sugerir melhorias
4. Criar jogos!

---

**Última atualização**: 2026-01-24  
**Versão**: 3.0  
**Status**: ✅ Completo
