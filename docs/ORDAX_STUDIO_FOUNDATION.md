# ORDAX Studio — Fundação

## Objetivo

O ORDAX Studio é a evolução do antigo `mcp-blender`/OrdaX Device Agent para um ambiente de desenvolvimento agentic persistente.
Ele não substitui Blender, Unity, Git ou o Device Agent: unifica essas capacidades em um mesmo núcleo de projeto, memória e execução.

A primeira regra da evolução é preservar compatibilidade. O aplicativo `C:\Users\TONECOS\Apps\OrdaxLocalAI` continua intacto e utilizável durante a migração.

## Decisão de arquitetura

O repositório histórico `mcp-blender` continua sendo a linha de desenvolvimento do agente. Blender e Unity passam a ser capabilities do ORDAX, não produtos separados.

```text
ChatGPT / cliente MCP
        |
        v
ORDAX Studio / Device Agent
        |
        +-- ORDAX Core
        |    +-- memória persistente
        |    +-- contexto por projeto
        |    +-- tarefas
        |    +-- checkpoints
        |
        +-- Workspace / Git / arquivos
        +-- Blender Live
        +-- Unity
        +-- adapters futuros
```

## Compatibilidade com ORDAX Local AI

`ordax_core.memory.resolve_memory_db()` procura o banco nesta ordem:

1. `ORDAX_MEMORY_DB`, quando definido explicitamente;
2. banco legado `~/Apps/OrdaxLocalAI/data/state.db`, quando já existe;
3. `%LOCALAPPDATA%/OrdaX/Studio/state.db` para instalações novas.

Isso permite continuar usando as memórias já criadas sem mover ou apagar dados. Contextos novos são gravados em `contexts/<projeto>.md`, ao lado do banco selecionado.

O esquema inicial é compatível com as tabelas já existentes: `projects`, `memories`, `tasks`, `checkpoints` e `events`.

## Capabilities de memória

O `ActionRegistry` agora inclui:

- `memory.status`
- `memory.context`
- `memory.remember`
- `memory.task_add`
- `memory.task_toggle`
- `memory.checkpoint`

O MCP local também possui atalhos de alto nível:

- `session_context`
- `memory_remember`
- `session_checkpoint`

A intenção é que um cliente MCP carregue `session_context` antes de continuar trabalho relevante em um projeto e registre um checkpoint ao concluir uma etapa significativa.

## Fases de produto

### Fase 1 — núcleo funcional

Consolidar memória, projetos, Git, terminal/arquivos e MCP num único runtime. Preservar o ORDAX Local AI como fallback e fonte de dados compatível.

### Fase 2 — Studio desktop

Evoluir a interface para workspace completo: explorador de arquivos, editor/diff, terminal, tarefas, histórico de decisões, capability status e controles de Blender/Unity.

### Fase 3 — produção 3D e engines

Integrar Blender Live, Unity e adapters de assets à experiência do Studio, mantendo contratos tipados, checkpoints e evidência visual.

### Fase 4 — autonomia controlada

Adicionar planejamento persistente, retomada automática de tarefas, políticas de permissão, auditoria e execução multi-etapa com gates explícitos para operações sensíveis.

### Fase 5 — integração no protótipo Ordax OS

A integração com `prototipo-ordax-os` fica deliberadamente adiada até o Studio cumprir um gate funcional mínimo. O desenvolvimento do Studio não deve depender do protótipo do sistema operacional.

Gate mínimo para iniciar a integração no OS:

- memória persistente validada entre processos/sessões;
- projeto ativo e contexto recuperável por MCP;
- operações de arquivos/Git estáveis;
- Blender e Unity operáveis como capabilities, sem acoplamento à UI;
- interface desktop funcional;
- testes de regressão do agente verdes;
- caminho de atualização e rollback definido.

## Sessao resumivel

A fundacao agora trata a continuidade como contrato explicito de runtime. `session.resume`:

- seleciona um projeto registrado;
- marca esse projeto como ativo no banco persistente;
- cria uma sessao com timestamp e referencia ao ultimo checkpoint;
- recupera memorias, tarefas e checkpoints do projeto;
- captura branch, HEAD e status Git atuais;
- publica as capabilities configuradas e os grupos de acoes disponiveis;
- atualiza `BOOT_CONTEXT.md` para compatibilidade com o ORDAX Local AI existente.

O MCP local expoe `session_resume` e `session_finish`. Quando nenhum projeto e informado, a retomada tenta primeiro o projeto ativo persistido, depois `default_project` e por fim o primeiro projeto registrado.

Essa camada nao depende da futura interface desktop: Blender, Unity, Git e workspace continuam capabilities do mesmo runtime e podem ser usados por qualquer cliente MCP autorizado.

## Runtime de produto

O pacote `ordax_studio` adiciona o primeiro entrypoint de produto sem duplicar o Device Agent:

```powershell
ordax-studio status
ordax-studio resume [projeto]
ordax-studio context [projeto]
ordax-studio checkpoint <projeto> "resumo"
ordax-studio finish <session_id>
ordax-studio mcp
```

`ordax-studio-mcp` permanece disponivel como alias direto para o MCP local. O CLI usa o mesmo `AgentConfig`, `ActionRegistry`, projetos cadastrados e banco persistente do Studio.

## Primeira shell desktop

`ordax-studio-desktop` abre a primeira interface desktop do produto. Ela usa o mesmo runtime do Device Agent e nao cria uma segunda implementacao de Blender/Unity/Git.

A shell inicial oferece projetos registrados, contexto persistente, memorias, tarefas, capabilities e terminal no diretorio do projeto. O botao **Retomar sessao** cria uma sessao persistente ligada ao ultimo checkpoint e ao estado Git atual; uma nova retomada do mesmo projeto encerra logicamente a sessao aberta anterior sem apagar seu historico.

Para validacao sem abrir janela:

```powershell
ordax-studio-desktop --smoke
```

O aplicativo legado `ORDAX Local AI` permanece preservado como fallback durante esta fase.
