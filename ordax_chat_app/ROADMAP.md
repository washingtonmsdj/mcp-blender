# Roadmap — ORDAX Chat App

## Product mode decision — regular ChatGPT first

- **Default:** regular ChatGPT conversation → ORDAX plugin/MCP → local runtime.
  This keeps model usage on the normal ChatGPT chat allowance when the user's plan/surface supports the required plugin capabilities.
- **Optional:** embedded Agent / Responses → uses the applicable Work/Codex usage pool.
- **24x7/headless:** must use an explicitly configured background-capable provider (Responses/API/other/local); it does not automate or scrape consumer ChatGPT conversations.
- The desktop is primarily runtime/dashboard/configuration for regular-chat mode; the embedded chat remains an optional agent surface.
- Plugin package: `plugins/ordax-studio/`.
- Production MCP: `https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp`.
- **ORDAX Web Bridge:** managed OpenAI Secure MCP Tunnel inside the desktop, mirroring the proven OpenChatX transport pattern for connecting regular ChatGPT to a private/local runtime.
- **cross-chat Handoff:** expiring project-scoped continuation IDs available through local and remote MCP, avoiding browser scraping while preserving long-running work.


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

## Gate 3 — Embedded Agent / Responses (optional) ✅ foundation

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

- Browser Companion ✅ foundation;
- private Chrome for Testing runtime for the managed ChatGPT browser ✅ foundation;
- primary Google Chrome profile is never modified; ORDAX uses its own persistent browser profile;
- managed browser download restricted to the official Chrome for Testing origin, with local SHA-256 recording, Authenticode signer inspection and release-version matching;
- loopback pareado em 127.0.0.1, código one-time e bearer isolado no service worker ✅;
- extensão Chrome/Edge empacotada com o produto ✅;
- conversa real do ChatGPT Web espelhada na UI do ORDAX ✅;
- envio explícito pelo compositor do ORDAX para a conversa anexada ✅;
- polling/stream visual de respostas na UI do ORDAX ✅;
- páginas comuns não podem parear nem chamar o loopback do Companion ✅;
- Companion não recebe autoridade de filesystem/terminal/Git/computer ✅;
- próximo: smoke real no ChatGPT Web, robustez dos seletores e fluxo de criação/reabertura de chats.

- ORDAX Web Bridge panel ✅;
- official `tunnel-client` install from OpenAI release with SHA-256 verification ✅;
- tunnel ID + runtime key protected locally; key is never passed to the model ✅;
- init/doctor/run lifecycle from the desktop ✅;
- restricted dedicated Tunnel MCP surface without generic `action_execute` ✅;
- Web Bridge daemon 24/7 with heartbeat, bounded backoff and crash recovery ✅;
- desired on/off state persists independently from credentials ✅;
- Windows logon Scheduled Task install/remove controlled from the desktop ✅;
- process identity survives desktop restart and rejects PID reuse ✅;
- next: migrate the packaged Windows launcher from legacy ORDAX Studio UI to ORDAX Dev and include the Web Bridge startup task in the final installer.


- instalação única;
- login/pairing;
- chat central;
- projetos/arquivos/terminal/Git/preview;
- status dos agentes e fila;
- grants por projeto/capability;
- revogação e histórico;
- updates assinados.
