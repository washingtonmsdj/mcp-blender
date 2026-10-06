# mcp-blender — repositório aposentado

Este repositório foi substituído pela arquitetura oficial do ORDAX e não deve receber novas implementações.

Repositórios canônicos:

- `washingtonmsdj/prototipo-ordax-os` — plataforma/OS e contratos públicos;
- `washingtonmsdj/ordax-apps` — aplicativos first-party, incluindo ORDAX Studio;
- `washingtonmsdj/ordax-runtime` — Runtime/Device Host/Computer Control e adapters locais;
- `washingtonmsdj/ordax-control-plane` — Product MCP, Control Plane, grants e connectors de provider.

A branch `retire/after-control-plane-cutover` é preparada antecipadamente e só deve ser mergeada depois que o gate canônico de aposentadoria confirmar:

1. deploy de produção pelo `ordax-control-plane`;
2. health e verificação remota verdes;
3. smoke ChatGPT -> Control Plane -> Runtime -> capability -> receipt verde;
4. ausência de dependência funcional build/deploy/launch apontando para este legado.

Após o merge desta branch, o histórico Git permanece disponível, mas o conteúdo operacional legado deixa de existir na `main`.
