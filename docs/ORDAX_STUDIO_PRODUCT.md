# ORDAX Studio como produto instalado

O fluxo de uso normal não depende de PowerShell, `mcp-start.ps1` ou de um shell remoto.

## Arquitetura de produto

```text
ChatGPT / Codex
      |
      |  plugin ORDAX Studio (MCP Streamable HTTP + OAuth)
      v
https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp
      |
      |  Control Plane autenticado, grants e auditoria
      v
ORDAX Device Agent no Windows
      |
      +--> projetos / Git / preview
      +--> Blender Live
      +--> Unity / Unreal
```

No Windows, `ordax-studio-install.ps1` é um instalador de produto, não um comando de uso diário. Ele cria **ORDAX Studio** no Menu Iniciar e garante o Device Agent persistente via Scheduled Task. Depois da instalação, o Device Agent sobe no logon e se recupera automaticamente sem exigir terminal aberto.

O pacote versionado do plugin está em `plugins/ordax-studio/` e aponta somente para o endpoint MCP HTTPS de produção. O endpoint local `stdio` continua disponível para Codex local, testes e desenvolvimento, mas não é a ponte do ChatGPT remoto.

## Regra de produto

- usuário final não inicia `mcp-start.ps1`;
- usuário final não precisa manter PowerShell aberto;
- ChatGPT usa o plugin ORDAX Studio e autenticação OAuth;
- o Device Agent mantém conexão de saída e executa somente ações tipadas concedidas;
- não existe shell remoto genérico;
- Blender é acessado pelo companion tipado e pelo fluxo de adoção de janela existente.
