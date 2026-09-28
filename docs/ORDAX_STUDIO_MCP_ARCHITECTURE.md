# ORDAX Studio MCP — contrato de arquitetura

## Identidade

- **Produto:** ORDAX Studio.
- **Repositório histórico:** `mcp-blender`.
- **MCP local canônico:** `ordax-studio-mcp` / `ordax-mcp`.
- **Alias histórico de cliente:** `mcp-blender`.
- **MCP remoto autenticado:** `ordax-product-mcp` (`ordax-studio-remote` no handshake).
- **Bridge legado de baixo nível:** `mcp-blender-unity`.

O nome do repositório não define mais o produto. Blender é um adapter/capability do ORDAX Studio, da mesma forma que Unity, Unreal, Git, preview e workspace.

## Regra estrutural

Não devem existir dois sistemas paralelos chamados “MCP Blender” e “ORDAX Studio”.
A UI, o MCP local, o Device Agent e o gateway remoto reutilizam o mesmo `ActionRegistry`, os mesmos projetos registrados e os mesmos contratos de segurança.

```text
ChatGPT / cliente MCP
        |
        +-- ORDAX Studio MCP local
        |       |
        |       +-- ActionRegistry tipado
        |
        +-- ORDAX Studio Remote MCP
                |
                +-- Control Plane autenticado
                        |
                        +-- mesmo ActionRegistry no dispositivo
```

## Superfície local

O MCP local é a superfície mais poderosa para um cliente já autorizado na estação. Ele oferece ferramentas de primeira classe para:

- descobrir repositórios e capabilities;
- carregar briefing/health do projeto;
- inventariar, buscar, ler em lote, escrever e aplicar patches com proteção SHA-256;
- inspecionar Git;
- iniciar e observar preview supervisionado;
- acessar memória, tarefas e checkpoints;
- executar actions tipadas de Blender, Unity, Unreal e pipeline de assets.

Escrita não usa acesso irrestrito ao filesystem: caminhos precisam pertencer ao projeto registrado, extensões são limitadas e substituições existentes exigem o SHA-256 observado anteriormente.

## Superfície remota

O MCP remoto deve ser comparável a um conector como Desktop Commander em disponibilidade para o cliente, mas não deve copiar um shell genérico.
Toda chamada passa por autenticação, device binding, Space/grant, allow-list e auditoria.

A superfície remota inicial permanece **read-only**. Ela inclui catálogo de repositórios, health, inventário, busca, leitura simples/em lote, preview status, Git e artifacts.
Ações mutáveis remotas deverão entrar em um contrato posterior com effects/grants próprios; não devem ser liberadas apenas porque a action local existe.

## Compatibilidade

Configurações antigas podem continuar chamando o servidor de `mcp-blender`. O console script com esse nome aponta para o MCP completo do ORDAX Studio.
`mcp-blender-unity` continua existindo apenas para testes/diagnóstico da bridge histórica e não é a superfície recomendada para novos clientes.
