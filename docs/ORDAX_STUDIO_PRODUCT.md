# ORDAX Studio como produto instalado

> **Direção atual do ORDAX Dev:** para usuários que querem preservar a franquia Work/Codex,
> o modo principal é o **ChatGPT normal usando o plugin/MCP ORDAX**. O chat embutido via
> Sign in with ChatGPT/Responses é um modo opcional e usa a franquia aplicável de Work/Codex.
> O runtime não automatiza cookies, endpoints privados ou extração do site do ChatGPT.


O ORDAX Studio é o produto local. ChatGPT, Codex, Claude, Cursor ou qualquer outro cliente compatível com MCP são consumidores opcionais; nenhum deles faz parte do runtime do ORDAX.

## Arquitetura cliente-neutra

```text
Cliente MCP compatível
(ChatGPT / Codex / Claude / Cursor / outro)
              |
              | MCP Streamable HTTP + OAuth
              v
https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev/mcp
              |
              | autenticação, grants e auditoria
              v
      ORDAX Control Plane
              |
              | conexão de saída persistente
              v
      ORDAX Device Agent
         no Windows
              |
              +--> projetos / arquivos / Git / preview
              +--> Blender Live
              +--> Unity / Unreal
              +--> adapters futuros
```

O endpoint `/mcp` é a superfície remota canônica e não pertence a um fornecedor de IA. Um cliente pode usar um adaptador próprio de instalação, como o plugin do ChatGPT, ou conectar diretamente ao endpoint quando suportar MCP remoto e OAuth.

## Windows

Depois de instalado, o `OrdaX Dev Agent` inicia automaticamente no logon por Scheduled Task e mantém a conexão de saída com o Control Plane. A interface **ORDAX Studio** pode estar fechada; a conectividade remota continua ativa enquanto o Device Agent estiver saudável.

O usuário final não precisa instalar Codex e não precisa manter PowerShell aberto. Codex local é apenas um cliente opcional do endpoint `stdio` de desenvolvimento.

Hoje `scripts/windows/ordax-studio-install.ps1` faz o bootstrap da instalação gerenciada, cria o app no Menu Iniciar e configura o Device Agent persistente. Esse script é infraestrutura de instalação, não rotina de uso.

A distribuição final do Windows deve ser um instalador clicável **ORDAX Studio Setup.exe** (ou MSIX equivalente) que encapsule esse bootstrap e apresente login, vínculo do dispositivo, atualização e diagnóstico sem terminal. O runtime não deve exigir Codex.

## Clientes

- **ChatGPT:** usa o pacote em `plugins/ordax-studio/`, que aponta para o MCP remoto genérico.
- **Outros clientes MCP remotos:** conectam ao mesmo `/mcp` e concluem sua própria autorização OAuth.
- **Clientes locais:** podem usar `ordax-studio-mcp` por `stdio` quando isso fizer sentido para desenvolvimento ou uso local.

Nenhum cliente ganha privilégios por ser ChatGPT ou Codex. As permissões vêm de identidade, dispositivo, projeto, grants e ações tipadas.

## Regras de produto

- o MCP é cliente-neutro;
- o Device Agent é a ponte persistente entre o PC e o Control Plane;
- o usuário final não inicia `mcp-start.ps1`;
- o usuário final não mantém terminal aberto;
- o app ORDAX Studio é a superfície de configuração, projetos e diagnóstico;
- a UI não precisa ficar aberta para o acesso remoto funcionar;
- não existe shell remoto genérico;
- Blender é acessado pelo companion tipado e pelo fluxo de adoção de janela existente;
- cada conta/cliente conclui sua própria autorização OAuth e não compartilha tokens.

## Pacote reproduzível do adaptador ChatGPT

A fonte do adaptador ChatGPT vive em `plugins/ordax-studio/`. `python scripts/build_ordax_plugin.py` valida os manifests, rejeita BOM UTF-8, cria um ZIP determinístico em `dist/plugins/` e grava o SHA-256 ao lado.

Esse ZIP não contém o ORDAX MCP nem o runtime Windows; ele apenas registra o endpoint MCP remoto no ChatGPT. Outras plataformas podem usar seus próprios adapters sem alterar o núcleo ORDAX.
