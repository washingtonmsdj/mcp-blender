# Roadmap — ORDAX Chat App

## Gate 1 — coding runtime completo
- workspace amplo dentro de projetos registrados: stat/list/read/write/patch/mkdir/move/remove;
- terminal foreground com argv ou shell explícito;
- Git genérico project-scoped;
- busca, batch read, diff, health, artifacts e preview expostos no MCP remoto;
- OAuth, device binding, grants e audit obrigatórios.

## Gate 2 — processos persistentes
- start/status/logs/stdin/stop;
- identidade persistente do processo para evitar PID reuse;
- recuperação após restart do Device Agent;
- portas/preview vinculados ao projeto.

## Gate 3 — computer/browser control
- screenshot/capture;
- janela ativa e catálogo de aplicações;
- click/type/hotkey/scroll;
- navegador com navegação e leitura estruturada;
- grants próprios e confirmação para efeitos de alto impacto.

## Gate 4 — contexto de agente
- Project Rules e Skills versionados;
- checkpoints e task state;
- resumos de sessão;
- contexto recuperável entre conversas;
- toolbox por projeto/Space.

## Gate 5 — subagentes e MCP aggregation
- delegação opcional para modelos externos/local;
- servidores MCP adicionais como adapters;
- orçamento, cancelamento e auditoria por subtarefa;
- nenhuma credencial de terceiros exposta ao modelo.

## Gate 6 — produto desktop
- instalação única;
- login/pairing;
- status do dispositivo e conexão ChatGPT;
- grants por projeto/capability;
- revogação e histórico de ações;
- updates assinados.
