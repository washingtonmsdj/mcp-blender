# Roadmap — ORDAX Chat App

## Estado atual — implementado nesta branch

- runtime geral de desenvolvimento: workspace, escrita/patch, terminal e Git;
- Product/MCP remoto como porta secundária;
- `OrchestratorStore` persistente com agentes, Prime/workers, goals e mensagens;
- sessões encadeadas com estimativa de contexto, threshold configurável, checkpoint e rollover;
- fila persistente de trabalho com prioridade, delay, leases, retry e recuperação após crash;
- `WorkerLoop` 24/7 que não chama modelo quando está idle;
- provider `OpenAIChatGPTPlanProvider` para catálogo de modelos e Responses streaming;
- **Continue with ChatGPT** com OAuth/PKCE/JWKS/refresh e armazenamento protegido;
- chat desktop com conversas persistentes e model picker;
- tool loop real entre Responses e ActionRegistry;
- processos persistentes e browser control tipado;
- Rules/Skills por projeto (`AGENTS.md`, `.ordax/rules`, `.ordax/skills/*/SKILL.md`);
- painel de agentes, fila e supervisor 24/7 no desktop;
- ferramenta `agents` no chat para Prime criar workers, delegar e consultar equipe;
- feedback loop persistente Prime → worker → resultado → Prime;
- autonomia persistida entre reinícios;
- daemon headless `ordax-dev-autonomy` com lock global anti-duplicação;
- instalador Windows Scheduled Task para iniciar autonomia no logon;
- contrato do provider independente para receber outros modelos no futuro.

## Gate 1 — coding runtime completo ✅

- workspace amplo dentro de projetos registrados: stat/list/read/write/patch/mkdir/move/remove;
- terminal foreground com argv ou shell explícito;
- Git genérico project-scoped;
- busca, batch read, diff, health, artifacts e preview;
- OAuth/grants/audit mantidos para a superfície remota.

## Gate 2 — orquestração contínua ✅ foundation

- Prime + workers persistentes;
- goals;
- inbox Prime↔worker;
- checkpoints;
- rollover de contexto para nova sessão;
- work queue crash-safe;
- loop 24/7 idle-safe.

Entregue também:
- execução real do modelo ligada à fila;
- scheduler de múltiplos agentes;
- Prime cria/delega para workers pelo próprio tool loop;
- resultado de worker vira follow-up durável do Prime sem polling do modelo quando idle.

Entregue também:
- preferência 24/7 persistente;
- auto-resume após restart quando conta/projeto continuam válidos;
- daemon headless independente da janela;
- lock cross-process para impedir desktop + daemon executarem a mesma fila;
- Scheduled Task Windows para iniciar o daemon no logon.

Ainda neste gate:
- políticas de pausa/horário/custo e limites por projeto;
- telemetria de disponibilidade/heartbeat do daemon na UI.

## Gate 3 — ChatGPT dentro do app ✅ foundation

- **Continue with ChatGPT** conforme o fluxo OSS oficial:
  - dynamic client registration;
  - OAuth Authorization Code + PKCE;
  - callback loopback em `127.0.0.1`;
  - validação do ID token/JWKS;
  - scopes `offline_access resource.invoke chatgpt.tokens.use.direct`;
  - refresh token rotativo;
  - credenciais protegidas e múltiplas contas;
- model picker usando `GET /v1/models`;
- Responses em `store=false, stream=true` (provider já implementado);
- streaming na UI;
- tratamento explícito de usage-limit, revogação e reauth.

O fluxo base já está implementado; faltam provas de login real em conta elegível e endurecimento final de UX/erro.

## Gate 4 — tool loop do agente ✅ foundation

- filesystem, terminal, Git, processos, preview e browser expostos como tools;
- tool-call/result loop implementado;
- cancellation/timeout global ainda precisa de acabamento de UX;
- policy engine por capability;
- checkpoint automático antes de rollover;
- compaction/continuation bundle sem depender de histórico do ChatGPT.

## Gate 5 — processos persistentes ✅

- start/status/logs/stdin/stop implementados;
- stdin usa fila persistente project-scoped com pump para o processo filho;
- recuperação e cleanup validados no Windows real.
- identidade persistente do processo para evitar PID reuse;
- recuperação após restart do Device Agent;
- portas/preview vinculados ao projeto.

## Gate 6 — browser + computer control ✅ foundation

Browser implementado e validado no Windows real:
- Chromium ORDAX-owned com profile isolado e CDP;
- navigate/snapshot/click/type/screenshot/stop;
- cleanup de toda a árvore da sessão sem tocar em outros Chromes;
- screenshot pode voltar ao modelo como evidência visual.

Computer control geral implementado como capability separada:
- catálogo de janelas e janela ativa;
- screenshot do desktop ou janela ativa;
- focus/click/type/hotkey/scroll fora do navegador;
- backend Windows tipado, sem shell;
- `computer.observe` e `computer.interact` são grants persistentes e project-scoped;
- ambos começam negados; a ferramenta nem aparece ao modelo sem grant;
- toggles explícitos no desktop para conceder/revogar por projeto;
- observação validada no Windows real: enumeração de janelas + PNG 3840×2160;
- interação não é inferida a partir de observação.

Ainda neste gate:
- confirmação de ações de alto impacto por política;
- evidência/replay de ações de input;
- backend equivalente para Linux quando o produto exigir.

## Gate 7 — contexto de agente ✅ foundation

- Project Rules e Skills carregados por projeto;
- AGENTS.md e arquivos equivalentes;
- resumos de sessão;
- contexto recuperável entre conversas;
- toolbox por projeto/Space.

## Gate 8 — subagentes e MCP aggregation

- delegação Prime → workers locais ✅ foundation;
- workers com sessão/modelo/contexto independentes ✅;
- retorno worker → Prime e continuação automática ✅;
- delegação para modelos externos/local ainda pendente;
- servidores MCP adicionais como adapters ainda pendente;
- orçamento, cancelamento e auditoria por subtarefa;
- nenhuma credencial de terceiros exposta ao modelo.

## Gate 9 — produto desktop

- instalação única;
- login/pairing;
- chat central;
- projetos/arquivos/terminal/Git/preview;
- status dos agentes e fila;
- grants por projeto/capability;
- revogação e histórico;
- updates assinados.
