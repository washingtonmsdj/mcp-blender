# ORDAX Intelligence — modos de IA e consumo

## Objetivo

Este documento é o contrato canônico entre OrdaX OS, ORDAX Studio, ORDAX Runtime e provedores de IA.
Ele existe para impedir duplicação de cérebro/memória e para deixar claro quando uma integração externa pode consumir cota ou créditos do usuário.

## Regra de arquitetura

O OrdaX OS é a plataforma. O ORDAX Studio é a bancada de trabalho. O ORDAX Runtime executa ações no computador. A ORDAX Intelligence mantém memória, contexto, roteamento e continuidade.

Blender, Unity, Git, navegador, arquivos e outras integrações são capabilities do Studio/Runtime; não são produtos de IA separados.

```text
OrdaX Intelligence
  +-- memória e contexto
  +-- IA local 24h
  +-- model router
         |
         v
ORDAX Studio -> ORDAX Runtime -> capabilities
         ^
         |
provedores externos autorizados
```

## Modo 1 — ChatGPT normal + ORDAX MCP

O usuário abre uma conversa normal no ChatGPT e o ChatGPT chama as ferramentas ORDAX autorizadas.
O local da conversa continua sendo o ChatGPT; o Studio fornece contexto e capacidades do computador.

O ORDAX não deve afirmar que consegue iniciar programaticamente uma conversa normal nem consumir a "cota do chat normal" fora da experiência do ChatGPT.
Esse modo depende de uma conversa iniciada pelo usuário e do suporte do ChatGPT ao plugin/MCP.

## Modo 2 — IA local 24h

A IA local pode permanecer ativa sem depender de uma janela do ChatGPT. Ela pode monitorar estado, preparar contexto, executar tarefas permitidas, criar checkpoints e manter continuidade.

Por padrão, tarefas locais não devem consumir cota da OpenAI. Se uma tarefa precisar ser escalada para um provedor externo, o roteador deve usar somente um modo previamente habilitado e autorizado pelo usuário.

A IA local pode preparar um handoff para o ChatGPT normal, mas não deve automatizar `chatgpt.com`, abrir conversas escondidas ou transformar a interface web em uma API não oficial.

## Modo 3 — usar o plano ChatGPT em outro aplicativo

Esse modo é separado do ChatGPT normal e deve permanecer opcional. Quando suportado oficialmente pelo produto, a conexão deve usar o fluxo autorizado pela OpenAI, como Sign in with ChatGPT / uso do plano em aplicativo participante.

**AVISO OBRIGATÓRIO:** requisições elegíveis feitas por esse modo contam para a cota de **ChatGPT Work e Codex** incluída no plano. Elas **não usam a cota do chat normal**.

O Studio deve mostrar esse aviso antes de habilitar o modo e nunca ativá-lo silenciosamente. Se créditos adicionais puderem ser usados após a cota, isso também deve depender de autorização explícita do usuário e ser mostrado na mesma superfície.

Esse modo não concede acesso automático às conversas ou memórias do ChatGPT. O ORDAX deve enviar apenas o contexto necessário, seguindo as permissões do projeto.

## Modo 4 — API com chave própria

Se houver suporte futuro a uma chave de API do usuário, esse caminho deve ser identificado separadamente como **API cobrada à parte**, conforme a conta/API do provedor. Ele nunca pode ser apresentado como uso incluído do chat normal.

## Regras do roteador

1. `local` é o caminho padrão para tarefas compatíveis com a IA local.
2. `chatgpt_mcp` representa a conversa normal iniciada pelo usuário no ChatGPT.
3. `chatgpt_plan_external` representa uso autorizado do plano em aplicativo externo e deve exibir aviso de cota Work/Codex.
4. `provider_api` representa API cobrada separadamente.
5. Nunca fazer fallback de `local` para um modo pago/limitado sem autorização.
6. Nunca chamar um modo externo apenas porque ele é mais inteligente; considerar política, custo/cota, privacidade e necessidade real.
7. Memória e continuidade pertencem ao ORDAX, não ao provedor de IA.

## Handoff entre IA local e GPT

O handoff é um checkpoint estruturado, não uma automação da interface do ChatGPT. Ele deve incluir projeto, objetivo, estado atual, concluídos, bloqueios, próxima ação, evidências e permissões necessárias.

Quando o usuário abrir uma conversa normal com o plugin/MCP, o GPT recupera esse briefing pelo ORDAX. Se no futuro o usuário habilitar um modo externo oficial, o mesmo checkpoint poderá ser enviado ao modelo por esse caminho.

## Copy obrigatória de produto

Para qualquer botão equivalente a “Usar meu plano ChatGPT”, exibir antes da ativação:

> Este modo usa a cota de ChatGPT Work e Codex incluída no seu plano. Não usa a cota do chat normal. O ORDAX só enviará solicitações depois da sua autorização.

Para Conta ORDAX, deixar explícito:

> Conectar sua Conta ORDAX não conecta automaticamente o ChatGPT e não consome cota da OpenAI. Integrações de IA são configuradas separadamente.

## Integração com OrdaX OS

Quando o Studio entrar no `prototipo-ordax-os`, ele deve consumir a Intelligence, memória, identidade, Spaces, permissões e model router da plataforma em vez de criar equivalentes próprios. O Studio mantém apenas a experiência de projeto e as capabilities especializadas.

## Referências externas e revisão

A regra de consumo da OpenAI deve ser revalidada antes de cada release que habilite integração de plano, porque limites e elegibilidade podem mudar. Referências oficiais atuais:

- OpenAI Help — Using your ChatGPT plan in other apps and sites;
- OpenAI Developers — Sign in with ChatGPT / plan usage.

O código não deve hardcodar preços, quantidades de mensagens ou limites semanais. A UI deve consultar/mostrar apenas o que a integração oficial disponibilizar e manter a distinção: **chat normal != Work/Codex != API**.
