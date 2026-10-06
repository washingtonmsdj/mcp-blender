# mcp-blender — repositório aposentado

Este repositório foi aposentado após a consolidação da arquitetura oficial do ORDAX. Ele **não contém mais código operacional** e não deve receber novas implementações.

## Repositórios canônicos

- `washingtonmsdj/prototipo-ordax-os` — plataforma/OS e contratos públicos;
- `washingtonmsdj/ordax-apps` — aplicativos first-party, incluindo ORDAX Studio;
- `washingtonmsdj/ordax-runtime` — Runtime/Device Host/Computer Control e adapters locais;
- `washingtonmsdj/ordax-control-plane` — Product MCP, Control Plane, grants e connectors de provider.

## Retirement concluído

- conteúdo operacional removido em `ab9d6924d66539fcd10bc3b497971d9a44409bd5`;
- produção do Control Plane em `ordax-control-plane`, Cloudflare Worker versão 118;
- Runtime/Device Host em `ordax-runtime`;
- Studio em `ordax-apps`;
- source-lock e recovery OIDC do OrdaX OS repontados ao Runtime canônico;
- smoke pós-retirement confirmado com `computer.windows=succeeded`.

O histórico Git permanece disponível apenas como provenance histórica. Para qualquer desenvolvimento novo, use o repositório canônico correspondente acima.
