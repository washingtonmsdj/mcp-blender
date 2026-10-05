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


## Blender: descoberta e adoção

Blender é uma capability do Studio e segue uma política de **uma única janela por intenção do usuário**. O add-on persistente `ordax_studio_bridge` é propositalmente mínimo: publica discovery local por PID/arquivo e só carrega o companion completo quando o arquivo aberto pertence a um projeto Blender registrado e o pedido de adoção é válido.

O fluxo é `discover → match project root → adopt by PID → validate companion fingerprint → typed actions`. `blender.live_start` tenta esse fluxo antes de criar processo novo. Uma falha ambígua nunca causa spawn como fallback; somente a ausência comprovada de uma candidata permite abrir Blender. Janelas múltiplas exigem PID explícito.

O bootstrap/add-on não recebe Python arbitrário, caminho de companion fornecido pelo cliente ou raiz de projeto fora do catálogo. O companion usado vem da instalação atual do ORDAX e continua sujeito ao protocolo/fingerprint existentes.

## Superfície remota

O MCP remoto é a superfície do **ORDAX Studio** para clientes autorizados, incluindo o ChatGPT normal,
e fornece uma capacidade comparável à de um agente de desenvolvimento completo. Toda chamada
passa por autenticação, device binding, Space/grant, catálogo explícito e auditoria.

A superfície é dividida por autoridade, não por uma limitação artificial de
produto:

- leitura: catálogo, health, inventário, busca, leitura, diff, artifacts e preview;
- escrita: criação/edição/patch/move/remove dentro de projetos registrados;
- Git: comandos Git project-scoped por capability própria;
- terminal: `terminal.exec`, capability privilegiada e explícita que executa com
  as permissões do usuário local;
- adapters: Blender, Unity e futuras integrações especializadas;
- computer/browser control: capability separada, prevista no roadmap.

Não existe um `action_execute` genérico que bypassa grants. Terminal e controle
do computador não são inferidos a partir de permissões comuns de arquivo.

## Compatibilidade

Configurações antigas podem continuar chamando o servidor de `mcp-blender`. O console script com esse nome aponta para o MCP completo do ORDAX Studio.
`mcp-blender-unity` continua existindo apenas para testes/diagnóstico da bridge histórica e não é a superfície recomendada para novos clientes.
