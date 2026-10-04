# ORDAX Intelligence — modos de IA e consumo

## Objetivo

Este documento é o contrato canônico entre OrdaX OS, ORDAX Studio, ORDAX Runtime e provedores/clientes de IA.
Ele existe para impedir duplicação de cérebro/memória, manter o Runtime provider-neutral e deixar claro quando uma integração externa pode consumir cota ou créditos do usuário.

## Regra de arquitetura

O OrdaX OS é a plataforma. O ORDAX Studio é a bancada de trabalho. O runtime do dispositivo executa ações no computador. A ORDAX Intelligence mantém memória, contexto, roteamento e continuidade.

Blender, Unity, Git, navegador, arquivos, Computer Control e outras integrações são capabilities da plataforma/Runtime; não são produtos de IA separados e não recebem implementações diferentes por provider.

```text
OrdaX Intelligence
  +-- memória e contexto
  +-- IA local 24h
  +-- model/provider router
         |
         v
ORDAX Studio -> runtime/capabilities
         ^
         |
connectors de providers autorizados
```

O boundary dos conectores está em `docs/ORDAX_PROVIDER_CONNECTORS.md`.

## Modo 1 — conversa no cliente de IA + conector ORDAX

O usuário abre uma conversa no cliente suportado (por exemplo, ChatGPT) e esse cliente chama as ferramentas ORDAX autorizadas por meio do seu conector.

O local da conversa continua sendo o cliente externo; o ORDAX fornece contexto/capacidades do computador conforme grants e policy.

Esse modo é provider-neutral no core. Um futuro Grok, Claude, Gemini ou outro cliente deve usar a mesma classe de integração sem criar actions ou runtimes próprios.

O ORDAX não deve transformar interfaces web de terceiros em APIs não oficiais nem afirmar que consegue consumir a cota de uma experiência de chat fora dos mecanismos oficialmente suportados pelo provider.

## Modo 2 — IA local 24h

A IA local pode permanecer ativa sem depender de uma janela de provider externo. Ela pode monitorar estado, preparar contexto, executar tarefas permitidas, criar checkpoints e manter continuidade.

Por padrão, tarefas locais não devem consumir quota/créditos de provider externo. Se uma tarefa precisar ser escalada, o router deve usar somente um modo previamente habilitado e autorizado pelo usuário.

A IA local pode preparar um handoff para um cliente externo, mas não deve automatizar a interface web do provider, abrir conversas escondidas ou transformar UI em API não oficial. Em particular, a integração OpenAI não deve automatizar `chatgpt.com` como substituto de uma API ou integração oficial.

## Modo 3 — uso de plano/entitlement de provider em aplicativo externo

Alguns providers podem oferecer fluxos oficiais que permitem usar entitlement/plano do usuário em outro aplicativo. Esse caminho é separado da conversa normal do provider e deve permanecer opcional.

Antes de habilitar esse modo, o conector específico deve:

- usar apenas o fluxo oficial suportado pelo provider;
- informar qual quota/plano será consumido;
- informar se créditos adicionais podem ser utilizados;
- obter autorização explícita do usuário;
- nunca apresentar esse consumo como equivalente à quota do chat normal quando o provider fizer distinção.

As regras de quota/custo são metadata/policy do conector do provider, não lógica estrutural do Studio ou Runtime.

### OpenAI / ChatGPT

Para a integração OpenAI planejada, a copy de produto deve continuar distinguindo explicitamente a conversa normal do ChatGPT de qualquer uso oficial de plano em aplicativo externo. A regra exata de elegibilidade, quota e nomenclatura deve ser revalidada contra documentação oficial da OpenAI antes de cada release que habilite esse modo.

O contrato de produto atualmente preserva o aviso **ChatGPT Work e Codex** para o modo externo aplicável: requisições desse modo não usam a cota do chat normal. Se a nomenclatura ou regra oficial mudar, o conector deve ser atualizado junto com a validação de release — nunca o Runtime genérico.

A distinção que a UI deve preservar é: **chat normal != Work/Codex != API**.

Esse detalhe é específico do conector OpenAI e não concede ao Codex qualquer papel estrutural no ORDAX.

## Modo 4 — API/credencial de provider

Se houver suporte a API com credencial própria do usuário/organização, esse caminho deve ser identificado separadamente como consumo/billing do provider correspondente.

Credenciais de provider não pertencem ao source do Studio e não podem virar fallback silencioso para tarefas locais.

## Regras do router

1. `local` é o caminho padrão para tarefas compatíveis com a IA local.
2. `provider_connector` representa conversa/cliente externo que chama ORDAX por um conector autorizado.
3. `provider_plan_external` representa uso oficial de entitlement/plano do provider em aplicativo externo, quando existir.
4. `provider_api` representa API/credencial cobrada ou limitada pelo provider.
5. Toda rota externa carrega `provider` e `product` como metadata explícita, sem alterar a semântica da capability ORDAX.
6. Nunca fazer fallback de `local` para um modo pago/limitado sem autorização.
7. Nunca escolher um provider apenas porque ele parece mais inteligente; considerar policy, custo/quota, privacidade, disponibilidade e necessidade real.
8. Memória e continuidade pertencem ao ORDAX; não passam a pertencer ao provider por causa de uma sessão externa.
9. Provider identity não cria grants nem elevação implícita.

## Handoff entre IA local e clientes externos

O handoff é um checkpoint estruturado, não uma automação da interface de um provider. Ele deve incluir projeto, objetivo, estado atual, concluídos, bloqueios, próxima ação, evidências e permissões necessárias.

Quando o usuário abrir uma conversa com um conector ORDAX, o cliente recupera esse briefing pelo ORDAX. Se o usuário habilitar outro modo oficial de provider, o mesmo checkpoint pode ser enviado por esse caminho respeitando policy e consentimento.

## Copy de produto

Copy de quota/custo deve ficar no módulo/conector do provider e ser baseada nas regras oficiais vigentes no release.

Para Conta ORDAX, manter explícito:

> Conectar sua Conta ORDAX não conecta automaticamente um provedor de IA e não consome quota/créditos desse provedor. Integrações de IA são configuradas separadamente.

## Integração com OrdaX OS

Quando o Studio fizer o source-of-truth cutover para `ordax-apps`, ele deve consumir Intelligence, Memory, Identity, Spaces, permissions e model/provider router da plataforma em vez de criar equivalentes próprios. O Studio mantém a experiência de projeto e suas capabilities/app-private state.

No OrdaX OS não deve existir um Runtime separado por provider. No Windows, `ORDAX Runtime.exe` implementa o host local provider-neutral necessário porque o Windows não fornece os ports nativos da plataforma.

## Referências externas e revisão

Regras de consumo/quota de providers devem ser revalidadas antes de cada release que habilite uma integração de plano ou billing externo, porque limites, nomes e elegibilidade podem mudar.

O código não deve hardcodar preços, quantidades de mensagens ou limites semanais. A UI deve mostrar apenas o que a integração oficial disponibilizar e preservar a separação entre conversa normal, entitlement externo e API/billing.
