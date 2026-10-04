# Conectar o ORDAX ao ChatGPT

## Arquitetura

O ORDAX Runtime mantém o computador conectado ao Control Plane. O ChatGPT não acessa `localhost` e não precisa manter um terminal aberto.

```text
ChatGPT normal
   |
   | ORDAX for ChatGPT
   v
https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp
   |
   v
ORDAX Runtime no Windows
   |
   +-- projetos
   +-- arquivos / Git
   +-- preview / processos
   +-- Computer Control
   +-- Blender / Unity
```

## Conector

A fonte do conector do ChatGPT fica em `plugins/ordax-chatgpt/`. O pacote contém somente os manifests/configuração e assets necessários para apontar o ChatGPT ao MCP remoto. O runtime real continua no dispositivo.

O nome user-facing do conector é **ORDAX for ChatGPT**. **ORDAX Studio** permanece reservado ao aplicativo first-party do ORDAX; o conector não é o Studio e não contém um Runtime próprio.

Outros providers devem seguir o mesmo padrão com conectores independentes, por exemplo `ORDAX for Grok`, reutilizando o mesmo protocolo, Control Plane, grants e handlers tipados.

## Produto atual

Nesta etapa não há licença nem assinatura. Conta ORDAX, quando usada, serve para autenticar/vincular o dispositivo e seus grants; ela não conecta automaticamente um provider de IA.

A UI Windows é o ORDAX Studio. A conversa acontece no cliente externo, por exemplo o ChatGPT normal, e o conector apenas disponibiliza as capabilities ORDAX autorizadas.
