# OrdaX Device Agent — plano de evolução

Status: implementação iniciada em 2026-09-24.

## Decisão de produto

O antigo projeto `mcp-blender` evolui para **OrdaX Device Agent**.

Blender e Unity deixam de definir o produto. Eles passam a ser adapters/capabilities do
agente, ao lado de Git, arquivos, testes e futuras integrações. A base que já funciona
não será descartada nem reescrita sem necessidade.

O objetivo é permitir que o mesmo projeto OrdaX seja trabalhado por diferentes
interfaces sem duplicar autoridade nem lógica:

```text
                    OrdaX Account
                         |
                  identity / grants
                         |
                OrdaX Control Plane
                         |
                OrdaX Action Gateway
                         |
                 OrdaX Device Agent
                         |
       +-----------------+------------------+
       |                 |                  |
     Projects           Git              Adapters
       |                 |          Blender / Unity / ...
       +-----------------+------------------+
                         |
        +----------------+----------------+
        |                |                |
     OrdaX OS         OrdaX Web      External MCP
                                       |
                               ChatGPT / Grok / ...
```

## GitHub continua sendo primeira classe

GitHub não será removido nem substituído pelo MCP.

Para desenvolvimento, GitHub é uma das rotas mais eficientes porque entrega:
- versionamento e histórico;
- branches e pull requests;
- colaboração;
- CI;
- uma fonte compartilhada que pode ser usada diretamente por ChatGPT, Grok e
  outras ferramentas que já possuam integração GitHub;
- atualização do próprio Device Agent.

Um projeto OrdaX pode ter Git/GitHub, mas não precisa deles. Projetos locais de
Blender, Unity, documentos e outras ferramentas continuam válidos.

### Dois caminhos que podem coexistir

```text
ChatGPT/Grok -- GitHub connector --> repository
```

é ótimo para código versionado.

```text
ChatGPT/Grok -- OrdaX MCP --> Action Gateway --> Device Agent --> local project/apps
```

é necessário para capacidades que o GitHub sozinho não oferece, como Blender
aberto, Unity, captura visual, arquivos locais autorizados, memória do projeto e
ações tipadas na estação.

O usuário pode usar os dois simultaneamente.

## App Projetos

`Projetos` é a interface humana principal no OrdaX. MCP não é um app separado
que o usuário precisa entender.

Um Projeto OrdaX pode compor:
- pasta local;
- repositório Git;
- conexão GitHub opcional;
- arquivos/documentos;
- memória privada;
- notas;
- adapters de aplicativos;
- capabilities autorizadas;
- referências e artifacts;
- Intelligence.

No Profile Pack Developer, Projetos pode crescer para uma experiência de workspace
comparável a IDEs com IA, sem obrigar o usuário a pagar por uma IDE externa quando
já possui acesso a modelos como GPT ou Grok.

A primeira experiência Developer deve evoluir para:
- árvore de arquivos;
- editor;
- Git/status/diff/branches;
- testes e problemas;
- terminal restrito ou tarefas tipadas, nunca shell remoto irrestrito por padrão;
- Intelligence;
- artifacts/capturas;
- histórico de ações;
- conexões.

## Conexões

Conexões pertencem à Conta/Space e são reutilizadas pelos apps autorizados.

```text
Conta OrdaX
  +-- GitHub
  +-- futuras fontes
```

Projetos pode iniciar o fluxo "Conectar GitHub", mas não deve criar um segundo
sistema de credenciais.

Supabase é infraestrutura interna da Conta OrdaX; o usuário não "conecta o
Supabase".

## OrdaX MCP

O Product MCP é uma interface externa sobre o mesmo Action Gateway.

Ele não recebe acesso genérico ao computador. Expõe ferramentas tipadas e
capabilities concedidas por usuário, Space, Projeto e dispositivo.

Exemplos iniciais:
- `spaces.list`
- `projects.list`
- `project.read_context`
- `project.text_read`
- `git.status`
- `git.diff`
- `artifacts.list`
- `memory.search_authorized`

Mutações devem exigir grants explícitos, preconditions e auditoria.

O MCP não deve expor:
- shell genérico;
- disco bruto;
- segredos;
- release signing keys;
- memória de outro Space;
- GitHub não selecionado;
- privilégios administrativos implícitos.

## Controle Web

Não será criado um segundo backend de controle.

OrdaX Web é outro cliente do mesmo Action Gateway:

```text
OrdaX Web --> Control Plane --> Action Gateway --> Device Agent
```

Assim Web, app Projetos e MCP usam as mesmas capabilities, grants, auditoria,
limites e evidências.

A experiência Web poderá mostrar:
- dispositivos online/offline;
- projetos autorizados;
- estado de apps;
- capturas/artifacts;
- Git/status;
- Intelligence;
- ações tipadas seguras.

## Atualização do Device Agent

A atualização contínua que hoje já funciona pelo GitHub é preservada.

Regras:
1. `main` continua sendo a linha ativa.
2. Update é fast-forward e fail-closed.
3. O bootstrap externo continua capaz de recuperar uma versão antiga/quebrada.
4. Mudança de dependências exige refresh explícito.
5. Nova versão candidata passa compile/tests antes de substituir o agente em uso.
6. Blender/Unity/adapters têm versões/capability contracts independentes.
7. Rename de produto não quebra os entrypoints antigos até existir migração
   comprovada.

O agente deve informar:
- versão do Device Agent;
- versões dos adapters;
- versão dos contratos;
- capabilities compiladas;
- capabilities realmente disponíveis na máquina.

## Estratégia de migração do repositório

Fase 1 — agora:
- adotar o nome **OrdaX Device Agent** no produto e documentação;
- adicionar entrypoints `ordax-device-agent` e `ordax-device-mcp`;
- manter `ordax-dev-agent` e `ordax-project-mcp` como aliases compatíveis;
- manter package/imports antigos para não interromper a estação.

Fase 2:
- extrair interfaces genéricas de projeto, device, action e adapter;
- mover Blender e Unity para contratos claramente identificados como adapters;
- adicionar contratos de Product MCP e Action Gateway;
- ligar identidade/grants do Control Plane sem misturar credenciais de
  desenvolvimento com credenciais do produto.

Fase 3:
- integrar Device Agent ao app Projetos do OrdaX;
- adicionar conexão GitHub central da Conta/Space;
- criar contexto portátil seguro de projeto para GitHub, separado da memória
  privada;
- expor primeiro conjunto read-only do Product MCP.

Fase 4:
- habilitar mutações MCP por capability;
- OrdaX Web sobre o mesmo gateway;
- presença/remoto multi-device;
- adapters adicionais.

Fase 5:
- somente após compatibilidade e recovery comprovados, renomear o repositório
  GitHub físico se desejado. O runtime não deve depender do nome histórico do
  repositório.

## Limites de escopo do MVP USB

Esta evolução não altera os gates do primeiro Stable MVP USB.

Ela não autoriza escrita física, não substitui a prova canônica v4 e não transforma
CI/QEMU em evidência de hardware. A integração entra de forma modular e não deve
bloquear boot, Surface ou IA local.

## Critérios de sucesso da primeira etapa

- nome OrdaX Device Agent disponível sem quebrar os comandos existentes;
- GitHub preservado como fonte/update/colaboração;
- projeto local continua não exigindo Git;
- Blender e Unity continuam funcionando;
- MCP local continua funcionando;
- arquitetura explicita que MCP remoto e Web convergem no mesmo Action Gateway;
- nenhum token/segredo novo é exposto;
- testes cobrem aliases de compatibilidade.
