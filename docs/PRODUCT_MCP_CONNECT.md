# Product MCP — conexão externa

O host Product MCP é **read-only** e usa o mesmo Control Plane, grants e auditoria do OrdaX Device Agent.

## Pré-requisitos

- pacote instalado com o entrypoint `ordax-product-mcp`;
- Cloudflare v3 Product Auth implantado;
- JWT Product atual em `ORDAX_PRODUCT_ACCESS_TOKEN`;
- pelo menos um grant Product ativo e explicitamente vinculado a um dispositivo.

## Variáveis

```text
ORDAX_PRODUCT_CONTROL_PLANE_URL=https://ordax-control-plane-v3.ordax-ac1ca1b50d09.workers.dev
ORDAX_PRODUCT_ACCESS_TOKEN=<JWT atual>
```

O token não deve ser salvo no repositório. O host o lê do ambiente a cada chamada.

## Smoke sem mutação

```powershell
python scripts/product_mcp_smoke.py
```

Esse smoke chama somente:

- `GET /v3/product/session`
- `GET /v3/product/targets`

Ele não enfileira jobs e não executa ações no dispositivo.

## Cliente MCP

Use `config/product-mcp.example.json` como referência. O campo do token é apenas um placeholder; substitua-o pelo mecanismo seguro de segredo/ambiente do cliente MCP escolhido.

Ferramentas expostas:

- `product_session`
- `product_targets`
- `projects_list`
- `project_inventory`
- `project_text_read`
- `git_status`
- `git_diff`
- `artifacts_list`
- `artifact_preview`

Não existe shell, escrita, `git.sync`, execução Blender/Unity ou ferramenta genérica de action nesse host.

## Fluxo de segurança

```text
MCP client
  -> ordax-product-mcp
  -> ProductRemoteClient
  -> Product JWT / Cloudflare
  -> subject-scoped targets
  -> device-bound grant
  -> Product read-only job
  -> ProductActionGateway
  -> audit
  -> sanitized result
```
