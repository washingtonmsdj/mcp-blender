# OrdaX: projetos conectados e feedback visual

O agente agora seleciona projetos cadastrados localmente. O GPT remoto continua
enviando jobs pela fila autenticada Supabase existente. Não há chave OpenAI no
agente e ele não escolhe o modelo: a inteligência fica no cliente que envia os
jobs e examina os resultados.

## Ativar

O clone gerenciado acompanha a `main` por fast-forward e o bootstrap externo
valida atualização, dependências e compilação antes de iniciar o agente. Não
execute dois consumidores para a mesma identidade durante uma atualização.

O cadastro de projetos continua sendo uma autorização **local**. Em vez de editar
JSON manualmente, use o helper versionado:

```powershell
.\scripts\windows\ordax-project-register.ps1 `
  -Slug meu-projeto `
  -Path "C:\Projects\MeuProjeto" `
  -Apps unity,blender `
  -RestartAgent
```

O helper preserva as configurações existentes, valida que o caminho é local,
mantém projetos já cadastrados e só reinicia a tarefa agendada quando
`-RestartAgent` é solicitado. Se o agente estiver ocupado, o restart é recusado
por padrão. A edição direta de
`%LOCALAPPDATA%/OrdaX/DevAgent/agent-settings.json` continua suportada para
administração avançada. Sem `projects`, o perfil HORDAX antigo continua
disponível. Um objeto vazio desabilita todos os projetos. Projetos não precisam
ser repositórios Git para usar Blender ou Unity.

O cadastro é uma autorização local. Um payload remoto não pode cadastrar um
caminho novo. Cada aplicativo precisa estar em `apps`; branches e métodos Unity
permitidos também são definidos localmente. Caminhos de arquivos são resolvidos
dentro da raiz cadastrada, incluindo resolução de links simbólicos.

## Cliente remoto via Supabase

Nenhuma migração de banco é necessária. Use as operações existentes de criação e
consulta de jobs do seu cliente autorizado. Um job de captura tem este formato:

```json
{
  "agent_name": "TONECOS-HORDAX",
  "project_slug": "game",
  "action": "observation.capture",
  "payload": {"app": "unity", "frames": 3, "interval_seconds": 1, "width": 1280, "height": 720}
}
```

`project_slug` agora é repassado à execução. Se `payload.project` também existir,
precisa ser igual. `projects.list` devolve o cadastro e `agent.status` anuncia as
ações. O heartbeat também divulga os projetos ao controlador.

Para trabalhar bem, o controlador deve:

1. Descobrir projetos e capacidades, depois consultar `project.observe`.
2. Sincronizar apenas a branch autorizada com `git.sync` ou usar seu fluxo de Git.
3. Executar uma ação e esperar o resultado antes de agir novamente.
4. Pedir uma captura e ler os pixels **e** o snapshot; comparar com o objetivo.
5. Corrigir e repetir. Em timeout com `outcome_unknown`, observar antes de repetir
   uma ação: o Editor pode tê-la executado sem a resposta ter chegado.

As imagens/snapshots são enviados a cada frame concluído e anunciados em eventos
`visual observation available`. O controlador pode acompanhar os eventos durante
o job e ver o frame antes do fim da sequência. O resultado final agrega os metadados
em `result.data.uploaded_artifacts`, sem repetir uploads já concluídos. O cliente remoto deve carregar as
URLs assinadas retornadas enquanto válidas. Logs/snapshots disponíveis também
são enviados quando uma ação falha. A renovação do lease continua durante uploads.

## Cliente MCP na estação

O novo servidor stdio usa as mesmas ações/cadastro:

```powershell
python -m ordax_dev_agent.mcp_server
```

Configure esse comando no cliente MCP instalado na estação. Ferramentas:
`projects_list`, `agent_capabilities`, `action_execute`, `artifact_image`.
`artifact_image(project, artifact_path)` devolve conteúdo MCP de imagem, permitindo
ao modelo ver os pixels. Um cliente exclusivamente na nuvem deve continuar usando
a fila Supabase; stdio não é uma URL pública.

## Texto de projeto

Projetos cadastrados também expõem duas operações tipadas para trabalho em
código/configuração sem abrir um shell remoto:

- `project.text_read` lê texto UTF-8 dentro de `Assets`, `Packages`,
  `ProjectSettings`, `automation` ou `docs`, devolvendo conteúdo, tamanho e
  SHA-256.
- `project.text_write` escreve somente extensões de fonte/configuração
  permitidas e exige o `expected_sha256` obtido na leitura anterior para
  substituir um arquivo existente. Criação exige `create=true`.

A escrita é atômica e falha se o arquivo mudou desde a leitura. Diretórios
gerados/cache/build/repositório são bloqueados. Arquivos serializados Unity
(`.unity`, `.prefab`, `.meta`) podem ser inspecionados, mas não são gravados
por essa operação genérica; mudanças estruturais de cena devem continuar usando
operações Unity tipadas.

## Unity genérico

Em um projeto novo com `apps: ["unity"]`, execute `unity.install_companion` uma vez.
Isso adiciona `Assets/OrdaX/Editor/OrdaXGenericAgent.cs`; deixe o Unity importá-lo.
Depois use `unity.editor_status`, `unity.scene_summary`,
`unity.physics_audit`, `unity.spatial_audit`, `unity.play_start`,
`unity.play_stop` e `unity.capture`. O `spatial_audit` procura evidências de
mundo quebrado — transforms espelhados, escalas quase zero ou extremas, posições
não finitas/extremas, roots invertidos, bounds globais dos renderers e câmera
abaixo/inside de colliders — sem depender de tipos específicos do jogo. O companion usa o Editor aberto e não abre uma segunda instância.

Uma captura genérica fotografa a câmera ativa da cena atual, sem trocar de cena
ou iniciar/parar Play automaticamente. O JSON inclui hierarquia, posições,
escalas e estado do Editor (até 1.000 objetos). É necessário ter uma câmera.
Screen-space overlay UI não aparece nesse render; confirme a compatibilidade do
pipeline de renderização do projeto antes de usar como teste visual completo.
Os contadores de erros abrangem somente mensagens observadas desde o carregamento
do companion. A ação de validação genérica não substitui testes do jogo nem força
uma recompilação; métodos personalizados usam allow-list e batch com Editor fechado.

HORDAX mantém seu companion e seu fluxo de gameplay através de `unity.profile:
"hordax"`. Não instale o genérico sobre ele. Não há dependências HORDAX no companion
genérico. `companion_source` permite indicar um caminho relativo personalizado.

## Blender

`blender.inspect` devolve cena, câmera, objetos, dimensões, materiais e contagem de
vértices. `blender.render_preview` produz PNG e o mesmo snapshot, com resolução,
frame e amostras configuráveis. Informe `blend_file` relativo ao projeto ou defina-o
no cadastro. O arquivo original não é salvo/modificado durante observação.

`blender.run_python` executa scripts versionados no `scripts_dir` cadastrado
(padrão `automation/blender` dentro do projeto). Exceções Python agora resultam em
falha, através de `--python-exit-code 1`. Scripts executados continuam tendo os
privilégios do usuário: use branches e scripts confiáveis. Render/inspect desabilitam
a execução automática de scripts embutidos no `.blend`; cenas que dependem disso
podem precisar de adaptação. A integração atual é CLI, não controla a sessão Blender
aberta nem vê alterações ainda não salvas.

## Feedback, latência e armazenamento

`observation.capture` coleta de 1 a 12 imagens, com intervalo mínimo configurável
(0,2 a 30 segundos). O intervalo não acelera renderizações: o próximo frame só
começa após o anterior terminar. Isso é captura sequencial, não WebRTC/vídeo ao vivo.
Use uma imagem pequena primeiro; aumente a qualidade somente para validar o resultado.
O HORDAX pode reiniciar seu playtest em cada captura conforme seu companion.

Cada captura recebe diretório único em `artifacts/<project>/<capture-id>/`.
Resultados incluem timestamps e duração; Blender também inclui hash SHA-256.
Não há remoção automática de evidências nesta versão: defina retenção operacional
no computador e no Storage para uso contínuo. O bloqueio de execução serializa
clientes MCP e agente usando o mesmo diretório de estado; ele não bloqueia ações
manuais do usuário no aplicativo ou agentes antigos sem esse mecanismo.

## Outros aplicativos

Instale um pacote Python confiável com entry point no grupo
`ordax_dev_agent.adapters`, habilite seu nome em `adapters` no settings e em `apps`
nos projetos. A fábrica recebe `AgentConfig` e devolve um dicionário de operações:

```python
from ordax_dev_agent.models import ActionResult

def create_adapter(config):
    def observe(project, payload):
        # Consultar o SDK/API local do aplicativo e devolver evidências reais.
        return ActionResult(True, "Adapter ready", {"project": project.slug})
    return {"observe": observe}
```

Um entry point `myapp = "my_package:create_adapter"` habilita `myapp.observe`.
Plugins não podem substituir ações nativas. Estarem cadastrados não significa que
qualquer aplicativo já está implementado: cada um precisa de seu adaptador.

## Verificação

```powershell
python -m unittest discover -s tests -v
python scripts/verify_visual_agent.py
```

O segundo comando precisa do Blender instalado e gera uma cena temporária com duas
capturas reais, conferindo que o `.blend` original permanece intacto.

Referências: [Blender CLI](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html),
[Unity RenderTexture](https://docs.unity.com/en-us/engine/6000.7/script-reference/unityengine/rendertexture).


`project.text_patch` aplica substituições textuais exatas e limitadas com o mesmo
precondition SHA-256. Cada substituição declara a contagem esperada de ocorrências;
qualquer ambiguidade ou mudança concorrente aborta o patch antes de escrever.
