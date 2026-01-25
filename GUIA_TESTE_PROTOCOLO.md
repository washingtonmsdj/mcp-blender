# Guia de Testes - Compiler Protocol

**Objetivo:** Verificar que o protocolo do compilador é inescapável

---

## 🧪 TESTE 1: Fluxo Normal (Happy Path)

### Pré-requisitos:
- Ordax Studio rodando
- Backend rodando
- Supabase configurado

### Passos:

1. **Abrir Ordax Studio**
   - Ir para página de novo jogo

2. **Pedir novo jogo**
   - Digitar: "Crie um jogo de plataforma com moedas"
   - Clicar em Send

3. **Verificar Fase 1: INTERPRETATION**
   - ✅ Badge mostra "1/5: Interpretação"
   - ✅ Card azul aparece com interpretação
   - ✅ Mostra: gameType, mechanics, restrictions, objective
   - ✅ Avança automaticamente após 500ms

4. **Verificar Fase 2: PLAN**
   - ✅ Badge mostra "2/5: Plano"
   - ✅ Card roxo aparece com plano
   - ✅ Mostra: título, descrição, loop, sistemas, lifecycle
   - ✅ Mostra warnings de auto-completações
   - ✅ Avança automaticamente após 500ms

5. **Verificar Fase 3: VALIDATION**
   - ✅ Badge mostra "3/5: Validação"
   - ✅ Card verde/amarelo aparece com validação
   - ✅ Mostra: status, contadores (críticos, graves, menores)
   - ✅ Mostra violações (se houver)
   - ✅ Avança automaticamente após 500ms

6. **Verificar Fase 4: CONFIRMATION**
   - ✅ Badge mostra "4/5: Confirmação"
   - ✅ Card aparece com resumo do plano
   - ✅ Botão "✅ Aceitar plano e compilar" aparece
   - ✅ Input de texto fica DESABILITADO
   - ✅ Botão Send fica DESABILITADO
   - ✅ NÃO avança automaticamente (aguarda aprovação)

7. **Clicar no botão de aprovação**
   - ✅ Badge mostra "5/5: Compilação"
   - ✅ Botão mostra "Compilando..." com spinner
   - ✅ Input continua desabilitado
   - ✅ Jogo é gerado

8. **Verificar jogo gerado**
   - ✅ Preview mostra o jogo
   - ✅ Input volta a ficar habilitado
   - ✅ Badge desaparece (ou mostra "Completo")

**Resultado esperado:** Todas as verificações passam ✅

---

## 🚫 TESTE 2: Tentar Burlar via Frontend

### Pré-requisitos:
- Ordax Studio rodando
- DevTools aberto

### Passos:

1. **Pedir novo jogo**
   - Digitar: "Crie um jogo de corrida"
   - Clicar em Send

2. **Parar na fase de confirmação**
   - Aguardar até badge mostrar "4/5: Confirmação"

3. **Tentar burlar via console**
   - Abrir DevTools Console
   - Tentar chamar: `send("compile")`
   - Ou tentar: `generateSpecStreaming(...)`

4. **Verificar bloqueio**
   - ✅ Input está desabilitado (não aceita texto)
   - ✅ Botão Send está desabilitado
   - ✅ Funções não são acessíveis via console (escopo privado)

**Resultado esperado:** Impossível burlar via frontend ✅

---

## 🚫 TESTE 3: Tentar Burlar via Backend Direto

### Pré-requisitos:
- Postman ou curl instalado
- URL do backend conhecida

### Passos:

1. **Tentar compilar sem sessionId**
   ```bash
   curl -X POST https://your-backend.com/game-ai-chat \
     -H "Content-Type: application/json" \
     -d '{
       "mode": "spec",
       "phase": "spec",
       "messages": [{"role": "user", "content": "Crie um jogo"}]
     }'
   ```

2. **Verificar resposta**
   - ✅ Retorna erro `COMPILER_PROTOCOL_VIOLATION`
   - ✅ Mensagem: "Cannot compile game. Current phase: interpretation"

3. **Tentar compilar com sessionId mas sem aprovação**
   ```bash
   curl -X POST https://your-backend.com/game-ai-chat \
     -H "Content-Type: application/json" \
     -d '{
       "mode": "spec",
       "phase": "spec",
       "sessionId": "test-session-123",
       "messages": [{"role": "user", "content": "Crie um jogo"}]
     }'
   ```

4. **Verificar resposta**
   - ✅ Retorna erro `COMPILER_PROTOCOL_VIOLATION`
   - ✅ Mensagem: "Cannot compile game without user approval"

**Resultado esperado:** Backend bloqueia todas as tentativas ✅

---

## 🚫 TESTE 4: Tentar Burlar via Streaming

### Pré-requisitos:
- Streaming endpoint conhecido
- SessionId de uma sessão não aprovada

### Passos:

1. **Criar sessão mas não aprovar**
   - Pedir novo jogo
   - Parar na fase de confirmação
   - Copiar sessionId do DevTools Network

2. **Tentar streaming direto**
   ```bash
   curl -X POST https://your-backend.com/game-ai-chat-stream \
     -H "Content-Type: application/json" \
     -d '{
       "mode": "spec",
       "sessionId": "copied-session-id",
       "messages": [{"role": "user", "content": "Crie um jogo"}],
       "approvedPlan": {...}
     }'
   ```

3. **Verificar resposta**
   - ✅ Stream retorna erro imediatamente
   - ✅ Erro: `COMPILER_PROTOCOL_VIOLATION`
   - ✅ Mensagem: "Cannot stream compilation. Current phase: confirmation, Approved: false"
   - ✅ Stream encerra sem emitir chunks de código

**Resultado esperado:** Streaming bloqueia sem aprovação ✅

---

## 🔄 TESTE 5: Persistência de Sessão

### Pré-requisitos:
- Ordax Studio rodando
- Acesso ao servidor backend

### Passos:

1. **Criar sessão**
   - Pedir novo jogo
   - Avançar até fase de confirmação
   - Copiar sessionId do DevTools

2. **Reiniciar servidor backend**
   - Parar servidor
   - Aguardar 5 segundos
   - Iniciar servidor novamente

3. **Verificar sessão no Supabase**
   - Abrir Supabase Dashboard
   - Ir para tabela `compiler_sessions`
   - Verificar se sessão existe
   - ✅ Sessão está lá com phase="confirmation"

4. **Continuar no frontend**
   - Clicar no botão "Aceitar plano e compilar"
   - Verificar se compilação funciona

5. **Verificar atualização no Supabase**
   - Recarregar tabela `compiler_sessions`
   - ✅ Sessão atualizada com phase="compilation" e approved_by_user=true

**Resultado esperado:** Sessão persiste e funciona após reiniciar ✅

---

## ⏱️ TESTE 6: Timeout de Sessão

### Pré-requisitos:
- Ordax Studio rodando
- Sessão criada há mais de 7 dias

### Passos:

1. **Criar sessão antiga (simular)**
   - Inserir manualmente no Supabase:
   ```sql
   INSERT INTO compiler_sessions (
     session_id, phase, approved_by_user, 
     created_at, updated_at
   ) VALUES (
     'old-session-123', 'confirmation', false,
     EXTRACT(EPOCH FROM NOW() - INTERVAL '8 days') * 1000,
     EXTRACT(EPOCH FROM NOW() - INTERVAL '8 days') * 1000
   );
   ```

2. **Rodar limpeza**
   ```sql
   SELECT cleanup_old_compiler_sessions();
   ```

3. **Verificar se sessão foi deletada**
   ```sql
   SELECT * FROM compiler_sessions WHERE session_id = 'old-session-123';
   ```
   - ✅ Retorna 0 linhas (sessão deletada)

**Resultado esperado:** Sessões antigas são limpas automaticamente ✅

---

## 📊 TESTE 7: Múltiplos Usuários

### Pré-requisitos:
- 2 abas do navegador abertas
- Ordax Studio em ambas

### Passos:

1. **Aba 1: Criar jogo**
   - Pedir: "Crie um jogo de nave espacial"
   - Avançar até confirmação
   - Copiar sessionId1

2. **Aba 2: Criar jogo**
   - Pedir: "Crie um jogo de puzzle"
   - Avançar até confirmação
   - Copiar sessionId2

3. **Verificar isolamento**
   - ✅ sessionId1 ≠ sessionId2
   - ✅ Cada aba tem seu próprio estado
   - ✅ Aprovar em uma aba não afeta a outra

4. **Aprovar em ambas**
   - Aba 1: Clicar em aprovar
   - Aba 2: Clicar em aprovar
   - ✅ Ambos os jogos são gerados independentemente

**Resultado esperado:** Sessões isoladas por usuário ✅

---

## 🎯 CHECKLIST FINAL

Após rodar todos os testes:

- [ ] Teste 1: Fluxo Normal - PASSOU
- [ ] Teste 2: Burlar Frontend - BLOQUEADO
- [ ] Teste 3: Burlar Backend - BLOQUEADO
- [ ] Teste 4: Burlar Streaming - BLOQUEADO
- [ ] Teste 5: Persistência - FUNCIONA
- [ ] Teste 6: Timeout - FUNCIONA
- [ ] Teste 7: Múltiplos Usuários - ISOLADO

**Se todos passarem:** ✅ Protocolo está inescapável

---

## 🐛 TROUBLESHOOTING

### Problema: Badge não aparece
**Solução:** Verificar se `sessionId` está sendo setado no estado

### Problema: Input não desabilita
**Solução:** Verificar se `compilerPhase` está sendo atualizado

### Problema: Botão de aprovação não funciona
**Solução:** Verificar se `handleApprove()` está conectado ao `onApprove`

### Problema: Streaming não bloqueia
**Solução:** Verificar se `sessionId` está sendo enviado na requisição

### Problema: Sessão não persiste
**Solução:** Verificar credenciais do Supabase e tabela `compiler_sessions`

---

**Tempo total de testes:** ~30 minutos  
**Cobertura:** 100% do protocolo
