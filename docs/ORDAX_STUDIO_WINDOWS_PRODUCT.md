# ORDAX Studio para Windows

## Produto

A identidade user-facing é **ORDAX Studio**.

A distribuição Windows atual permanece compatível com instalações anteriores:

`ORDAX-Dev-Setup-<versão>-x64.exe`

Ela instala:

- **ORDAX Dev.exe** — launcher Windows legado/compatível que abre a Workbench do **ORDAX Studio**;
- **ORDAX Runtime.exe** — host persistente e provider-neutral que conecta o computador ao Control Plane.

O runtime privado inclui CPython e dependências do produto, sem alterar o PATH do usuário.

`ORDAX Dev.exe` é um nome físico legado mantido durante a janela de compatibilidade de upgrade. Ele não é um produto separado e não indica dependência de Codex. Uma migração futura para `ORDAX Studio.exe` deve preservar AppId, atualização in-place, desinstalação, atalhos, shutdown cooperativo e o estado do dispositivo.

## Identidade e integrações

A identidade do produto é a **Conta ORDAX**. Hoje ela é autenticada por Supabase Auth e é usada para vincular dispositivos, Spaces e grants.

O **Cloudflare** é infraestrutura do Control Plane/MCP e não exige login do usuário final.

O **GitHub** é opcional e deve ser tratado como provedor de projetos/remotos. Ele não substitui a Conta ORDAX e o plugin GitHub de um cliente de IA não é a ponte do ORDAX.

Clientes de IA são integrações separadas. O fluxo genérico é:

```text
cliente de IA autorizado
        │
        └─ conector ORDAX do provider
             │
             └─ Control Plane / protocolo ORDAX
                  │
                  └─ ORDAX Runtime no PC
```

O conector atual de ChatGPT é uma instância desse padrão. Um futuro conector Grok deve seguir o mesmo boundary e não criar outro Runtime.

Contratos detalhados:

- `docs/ORDAX_IDENTITY_AND_PROVIDERS.md`;
- `docs/ORDAX_PROVIDER_CONNECTORS.md`.

## Uso diário

1. instalar o ORDAX Studio (o instalador/binário atual ainda usa `ORDAX Dev` como nome físico legado de compatibilidade);
2. o Runtime inicia automaticamente com o Windows;
3. abrir o Studio para ver projetos, Git, previews, memória, Computer Control e status;
4. conectar um cliente/provider autorizado quando quiser usar uma IA externa com as ferramentas ORDAX;
5. a janela do Studio pode ser fechada sem derrubar a conexão do Runtime.

Não existe dependência estrutural de Codex, chat embutido, Browser Companion ou navegador gerenciado.

## Provider neutrality

`ORDAX Runtime.exe` não deve conter branches de execução por provider. O mesmo action handler executa a mesma capability autorizada independentemente de a solicitação ter vindo de ChatGPT, Grok ou outro cliente.

Provider metadata serve para autenticação, política, auditoria, revogação e UX; nunca para conceder autoridade implícita.

## Atualização

O instalador mantém o mesmo AppId para atualização segura das instalações anteriores. Antes de substituir arquivos ele encerra cooperativamente a UI e o Runtime; versões antigas que não suportam esse sinal usam o fallback de compatibilidade já existente.

A eventual troca do nome físico `ORDAX Dev.exe` para `ORDAX Studio.exe` deve acontecer como uma migração de packaging testada, e não por simples rename que deixe atalhos, uninstall records ou processos antigos órfãos.

O pipeline oficial é `.github/workflows/windows-product-build.yml`.
