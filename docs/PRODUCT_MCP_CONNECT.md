# Conectar o ORDAX Dev ao ChatGPT

## Arquitetura

O ORDAX Dev mantém o computador conectado ao Control Plane. O ChatGPT não acessa `localhost` e não precisa manter um terminal aberto.

```text
ChatGPT normal
   |
   | plugin / MCP remoto
   v
https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp
   |
   v
ORDAX Runtime no Windows
   |
   +-- projetos
   +-- arquivos / Git
   +-- preview / processos
   +-- Blender / Unity
```

## Plugin

A fonte do adaptador fica em `plugins/ordax-studio/`. Ele contém apenas os manifests que apontam para o MCP remoto. O runtime real continua no computador.

## Produto atual

Nesta etapa não há licença nem assinatura. Conta ORDAX, quando usada, serve apenas para autenticar/vincular o dispositivo.

A UI Windows é um host/monitor. A conversa acontece no cliente MCP, por exemplo o ChatGPT normal.
