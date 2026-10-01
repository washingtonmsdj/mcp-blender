# ORDAX Chat App

Produto para transformar o ChatGPT normal em um agente de desenvolvimento conectado ao computador do usuário, sem depender do Codex/Work como runtime de execução.

## Princípio

O ChatGPT continua sendo o modelo e o planejador. O ORDAX fornece o runtime local: arquivos, terminal, Git, processos, preview, browser/computer control e adapters como Blender/Unity. O transporte remoto usa o Control Plane/MCP existente; não existe um segundo backend paralelo.

## Arquitetura

```text
ChatGPT normal
  -> app MCP remoto / Secure MCP Tunnel
  -> ORDAX Control Plane (OAuth, grants, audit)
  -> conexão de saída do Device Agent
  -> ActionRegistry
       -> workspace/files
       -> terminal
       -> Git
       -> preview/processes
       -> browser/computer (próximo gate)
       -> Blender / Unity / outros adapters
```

## Níveis de capacidade

- **read**: inventário, busca, leitura, status, diff, health, previews.
- **write**: criar/editar/remover/mover arquivos e diretórios.
- **git-write**: branch, add, commit, merge, pull, push e demais comandos Git autorizados.
- **terminal**: execução de comandos com as permissões do usuário local.
- **computer**: captura e interação com aplicações/desktop; capability separada.
- **adapters**: Blender, Unity e futuros programas especializados.

Terminal e computer control nunca são implicados por acesso de leitura/escrita a arquivos. São grants explícitos e auditados.

## Objetivo de produto

A experiência alvo é comparável a um agente de código completo: o usuário pode pedir para analisar um projeto, alterar múltiplos arquivos, executar testes/builds, revisar o resultado, usar Git e trabalhar com ferramentas visuais, tudo a partir de uma conversa normal do ChatGPT.

Blender é apenas um adapter. Este produto não é um “MCP Blender”.
