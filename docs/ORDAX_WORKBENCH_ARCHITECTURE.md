# ORDAX Dev Workbench — arquitetura nativa

## Objetivo

O ORDAX Dev deve funcionar como um ambiente de trabalho local para agentes, não como um IDE preso a um único modelo.

A janela principal é dividida em dois contextos independentes:

1. **Provider Deck (esquerda)** — interface humana para ChatGPT, Grok, Claude, Gemini, UI local ou URL personalizada.
2. **Work Deck (direita)** — Studio, preview do projeto, browser de trabalho, execuções e logs.

O Runtime e o MCP permanecem processos independentes da UI. Fechar, trocar aba ou navegar no Provider Deck não encerra jobs, browsers gerenciados, previews ou conexões remotas.

## Regra central: provider não é agente

O WebView de ChatGPT/Grok é uma superfície de uso do usuário. O ORDAX não injeta automação programática na página consumer do ChatGPT.

Quando ChatGPT trabalha no computador, o caminho autoritativo é:

ChatGPT → ORDAX MCP → Control Plane → Runtime → ações tipadas/grants.

Outros provedores podem usar o mesmo Runtime por MCP, API/adapters ou integração local. A shell apenas hospeda a experiência visual.

## Browser e preview

Há três superfícies distintas:

- **Provider WebView**: login/conversa do usuário com uma IA.
- **Visible Browser**: navegador que o usuário pode usar ao lado da IA.
- **Managed Browser**: Chromium supervisionado pelo Runtime e controlado por CDP.

O Managed Browser é a superfície usada pelo agente para DOM, click/type validados e screenshots. Como a captura é feita por CDP, ela continua disponível quando o usuário muda a aba visível do Work Deck.

Para frontend, o preview do projeto pode ser exibido no Work Deck e, ao mesmo tempo, inspecionado/capturado pelo agente em segundo plano.

## Segurança e controle do computador

Acesso amplo ao computador não deve ser representado por uma única permissão opaca.

O modelo ORDAX separa:

- leitura de filesystem;
- escrita/edição;
- criação/movimentação/remoção;
- execução de processos;
- interação com processos;
- inspeção de processos do sistema;
- desktop visual;
- input de mouse/teclado;
- browser/network;
- Git;
- adapters de aplicações.

Cada capacidade possui grant e auditoria. O usuário pode autorizar raízes específicas ou habilitar explicitamente acesso de computador inteiro.

## Paridade funcional KV22Code / Desktop Commander

Capacidades que o ORDAX deve cobrir:

- ler e editar arquivos;
- criar arquivos, documentos, relatórios e planilhas;
- listar, mover, organizar, renomear e converter conteúdo;
- buscar arquivos e conteúdo;
- executar comandos, testes e builds;
- manter sessões de terminal/processos persistentes;
- enviar stdin e ler logs;
- inspecionar/listar/encerrar processos;
- Git status/diff/commit/sync conforme grant;
- trabalhar em um computador remoto;
- monitor visual das ações;
- múltiplos computadores;
- atualização do produto;
- projetos duráveis com contexto/memória;
- browser gerenciado e validação visual;
- controle do desktop;
- providers múltiplos (web, API e local);
- modo de infraestrutura privada/self-hosted como evolução do Control Plane.

## Fases

### Fase 1 — Workbench nativa
WPF + WebView2CompositionControl, bridge local allowlisted e painéis Provider/Work Deck.

### Fase 2 — Computer Access
Filesystem/processos em escopo de dispositivo com política de allowed roots e opt-in de computador inteiro.

### Fase 3 — Provider adapters
Contrato uniforme para provider web, provider API e inference local, sem acoplar o Runtime a um fornecedor.

### Fase 4 — Project Brain
Recall híbrido lexical + semântico, indexação incremental e contexto compartilhado entre conversas/provedores.

### Fase 5 — Private/self-host
Pacote documentado de Control Plane privado e dispositivos gerenciados para times.
