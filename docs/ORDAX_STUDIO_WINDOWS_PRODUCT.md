# ORDAX Studio para Windows

## Produto

A distribuição canônica é:

`ORDAX-Dev-Setup-<versão>-x64.exe`

Ela instala:

- **ORDAX Dev.exe** — launcher Windows legado/compatível que abre a Workbench do **ORDAX Studio**;
- **ORDAX Runtime.exe** — host persistente que conecta o computador ao Control Plane.

O runtime privado inclui CPython e dependências do produto, sem alterar o PATH do usuário.

## Identidade e integrações

A identidade do produto é a **Conta ORDAX**. Hoje ela é autenticada por Supabase Auth e é usada para vincular dispositivos, Spaces e grants.

O **Cloudflare** é infraestrutura do Control Plane/MCP e não exige login do usuário final.

O **GitHub** é opcional e deve ser tratado como provedor de projetos/remotos. Ele não substitui a Conta ORDAX e o plugin GitHub do ChatGPT não é a ponte do ORDAX. A ponte remota é o plugin ORDAX Studio → MCP do Control Plane → ORDAX Runtime.

Contrato detalhado: `docs/ORDAX_IDENTITY_AND_PROVIDERS.md`.

## Uso diário

1. instalar o ORDAX Studio (o instalador/binário 0.4.1 ainda usa o nome técnico `ORDAX Dev` por compatibilidade);
2. o Runtime inicia automaticamente com o Windows;
3. abrir o painel para ver projetos, Git, previews, memória e status;
4. conectar o plugin/MCP no ChatGPT quando quiser usar o ChatGPT normal como agente;
5. a janela do ORDAX pode ser fechada sem derrubar a conexão.

Não existe dependência de Codex, chat embutido, Browser Companion ou navegador gerenciado.

## Atualização

O instalador mantém o mesmo AppId para atualização segura das instalações anteriores. Antes de substituir arquivos ele encerra cooperativamente a UI e o Runtime; versões antigas que não suportam esse sinal usam o fallback de compatibilidade já existente.

O pipeline oficial é `.github/workflows/windows-product-build.yml`.
