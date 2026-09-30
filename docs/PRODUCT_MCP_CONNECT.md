# ORDAX Studio ? conex?o remota de produto

O ORDAX Studio possui duas superf?cies do mesmo produto: o MCP local (`ordax-studio-mcp`) para clientes autorizados na esta??o e o Product Remote para ChatGPT/servi?os externos atrav?s do Control Plane Cloudflare v3. O usu?rio final n?o deve iniciar `mcp-start.ps1` a cada sess?o.

## Windows

O instalador de produto ? `scripts/windows/ordax-studio-install.ps1`. Ele garante o Device Agent persistente, usa o runtime gerenciado em `%LOCALAPPDATA%\OrdaX\DevAgent\src` e cria **ORDAX Studio** no Menu Iniciar. O Device Agent continua respons?vel por logon, heartbeat, recovery e atualiza??o segura.

Depois de instalado, o fluxo normal ? abrir **ORDAX Studio** pelo Menu Iniciar; n?o h? terminal obrigat?rio no uso di?rio.

## Product Remote v2

A superf?cie remota n?o oferece shell, Python arbitr?rio nem `action_execute`. As opera??es s?o fechadas e tipadas e exigem autentica??o Product, v?nculo de dispositivo, grant por a??o/projeto e auditoria fail-closed.

Al?m das leituras existentes, a v2 permite de forma expl?cita:

- `project.text_write` e `project.text_patch`, com paths relativos e prote??o SHA-256;
- `blender.live_status`, `blender.live_scene_snapshot`, `blender.live_object_inspect` e `blender.live_modeling_schema`;
- `blender.live_start`, que adota a janela existente antes de abrir outra;
- `blender.live_object_transform`, `blender.live_create_primitive` e `blender.live_material_apply`;
- `blender.live_save`.

O job remoto can?nico ? `ordax.product.invoke`. `ordax.product.read.invoke` permanece aceito apenas para compatibilidade de jobs antigos em tr?nsito; n?o ? a superf?cie nova do produto.

## ChatGPT

Plugins do ChatGPT usam um MCP remoto HTTPS. O Control Plane ORDAX ? a fronteira p?blica autenticada; o Device Agent mant?m uma conex?o de sa?da com ele e executa apenas as a??es concedidas. O MCP local `stdio` continua ?til para Codex e desenvolvimento, mas n?o deve ser a rotina do usu?rio remoto.

A etapa seguinte para publica??o do plugin ? expor o endpoint Streamable HTTP `/mcp` do ORDAX sobre esse mesmo Product Remote e registrar essa URL no ChatGPT. N?o deve ser criado um segundo backend ou um shell proxy.
