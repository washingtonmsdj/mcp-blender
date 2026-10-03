# ORDAX Dev — produto instalado

## Direção atual

O **ORDAX Dev** é um host local de desenvolvimento. Ele não incorpora um segundo ChatGPT e não depende de Codex.

```text
ChatGPT normal / outro cliente MCP
              |
              | MCP remoto autenticado
              v
ORDAX Control Plane (Cloudflare)
              |
              | conexão de saída persistente
              v
ORDAX Runtime no Windows
              |
              +-- projetos / arquivos / Git / preview
              +-- processos e ferramentas de desenvolvimento
              +-- Blender / Unity / adapters
```

O app Windows mostra projetos, status, memória/checkpoints, Git, arquivos, preview, adapters e a saúde da conexão. O **ORDAX Runtime** inicia com o Windows e continua online mesmo com a janela fechada.

## Sem licença/assinatura nesta etapa

A versão atual não possui plano pago, licença ou gate de assinatura. O vínculo de conta ORDAX é apenas autenticação opcional do dispositivo para acesso remoto; ele não desbloqueia tiers.

## ChatGPT

O pacote `plugins/ordax-studio/` registra o endpoint MCP de produção. O ChatGPT continua sendo o local da conversa; o ORDAX Dev fornece as ferramentas do computador.

Endpoint canônico:

`https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp`

## Regras

- o MCP é cliente-neutro;
- nenhuma UI de chat é necessária no host;
- nenhum Browser Companion é necessário;
- nenhum navegador privado é instalado pelo ORDAX;
- o Device Agent não depende da janela aberta;
- permissões e auditoria continuam no runtime/control plane;
- Blender e Unity são adapters do mesmo host, não produtos separados.

## Modos de IA e cotas

O Studio não possui um segundo cérebro, memória ou roteador independente do OrdaX OS. O contrato canônico de IA está em [ORDAX_INTELLIGENCE_MODES.md](ORDAX_INTELLIGENCE_MODES.md).

- **ChatGPT normal + MCP:** a conversa é iniciada pelo usuário no ChatGPT e o ORDAX fornece ferramentas.
- **IA local 24h:** trabalha com memória/checkpoints do ORDAX e não deve consumir OpenAI por padrão.
- **Usar plano ChatGPT em aplicativo externo:** é um modo separado e opcional; quando suportado oficialmente, deve avisar antes da ativação que requisições elegíveis consomem a cota **ChatGPT Work e Codex**, não a cota do chat normal.
- **API com chave própria:** deve ser identificada como API cobrada separadamente.

Conta ORDAX, assinatura ORDAX e consumo de IA são conceitos separados. Nenhum modo limitado/pago pode ser habilitado silenciosamente como fallback.
