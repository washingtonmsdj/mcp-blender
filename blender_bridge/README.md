# OpenAI Blender Bridge

Ponte simples entre comandos versionados no GitHub e o Blender rodando localmente.

## Arquitetura

ChatGPT -> GitHub (`blender-bridge`) -> `relay.py` no Windows -> Blender MCP addon em `127.0.0.1:9876` -> Blender.

O relay usa somente a biblioteca padrao do Python e Git instalado no Windows.

## 1. Instalar o addon Blender MCP

No PowerShell:

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uvx mcp-for-blender install-addon
```

Depois abra/reinicie o Blender e habilite o addon MCP for Blender em:

`Edit -> Preferences -> Add-ons`

Na Viewport 3D pressione `N`, abra a aba do MCP e clique em `Start MCP Server`.

Porta esperada: `9876`.

Mantenha o servidor preso ao localhost/127.0.0.1.

## 2. Clonar e entrar na branch da ponte

```powershell
git clone https://github.com/washingtonmsdj/testepodedeletar.git
cd testepodedeletar
git fetch origin
git checkout blender-bridge
```

Se o repositorio ja estiver clonado:

```powershell
cd CAMINHO_DO_REPOSITORIO
git fetch origin
git checkout blender-bridge
git pull --rebase origin blender-bridge
```

## 3. Primeiro teste, somente leitura

Com o Blender aberto e o MCP Server iniciado:

```powershell
powershell -ExecutionPolicy Bypass -File .\blender_bridge\start_bridge.ps1
```

A fila ja contem:

`blender_bridge/commands/0001-get-scene-info.json`

O relay deve executar `get_scene_info` e criar automaticamente:

`blender_bridge/results/0001-get-scene-info.json`

Em seguida ele faz commit e push do resultado para a branch `blender-bridge`.

## 4. Habilitar alteracoes de cena

Por seguranca, comandos que alteram a cena ficam bloqueados no modo padrao.

Quando quiser permitir modelagem via bridge:

```powershell
powershell -ExecutionPolicy Bypass -File .\blender_bridge\start_bridge.ps1 -AllowSceneChanges
```

Isso habilita os comandos de escrita presentes na allowlist do relay, incluindo `execute_code`.

## Estrutura

```text
blender_bridge/
  relay.py
  start_bridge.ps1
  commands/
  results/
  previews/
```

Cada arquivo `.json` em `commands/` e processado uma unica vez. Um comando e considerado concluido quando existe um JSON com o mesmo nome em `results/`.

## Exemplo de comando de leitura

```json
{
  "id": "scene-info",
  "type": "get_scene_info",
  "params": {},
  "enabled": true
}
```

## Exemplo de comando para modelagem

Requer iniciar o relay com `-AllowSceneChanges`.

```json
{
  "id": "create-cube",
  "type": "execute_code",
  "params": {
    "code": "import bpy\nbpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,1))\nobj=bpy.context.object\nobj.name='Bridge_Test_Cube'"
  },
  "enabled": true
}
```

## Screenshots

Um comando `get_viewport_screenshot` recebe automaticamente um caminho dentro de `blender_bridge/previews/` para que o PNG seja versionado e possa ser lido depois.

## Seguranca

- O Blender continua ouvindo somente em `127.0.0.1:9876`.
- Nao exponha a porta 9876 diretamente na internet.
- A branch e privada.
- O modo padrao da ponte e somente leitura.
- `execute_code` so e aceito quando o relay e iniciado com `-AllowSceneChanges`.
- Use uma copia/backup do `.blend` durante os primeiros testes.
