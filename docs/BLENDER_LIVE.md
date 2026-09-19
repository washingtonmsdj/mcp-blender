# Etapa 1 — sessão persistente Blender

Ações novas: `blender.live_status`, `blender.live_inspect`,
`blender.live_run_python`, `blender.live_result`. Disponíveis pelo mesmo dispatcher
MCP/fila remota, depois de instalar esta versão do agente. Não mudam as ações CLI
existentes. Esta etapa conecta a cena em memória; capturas multivista serão uma
etapa separada. Não existe fallback silencioso para um arquivo salvo.

## Conectar explicitamente

1. Cadastre o projeto com `apps: ["blender"]` nos settings locais do agente.
2. Obtenha `companion_path` por `blender.live_status`.
3. No Blender aberto, use a Python Console (Shift+F4):

```python
import runpy
ordax = runpy.run_path(r"CAMINHO_ABSOLUTO_DO_COMPANION")
ordax['start'](r"RAIZ_ABSOLUTA_DO_PROJETO")
```

Isso autoriza apenas inspeção. Para executar scripts confiáveis, habilite
`blender.allow_live_scripts: true` no cadastro local e use
`ordax['start'](..., allow_scripts=True)` ao conectar. O diretório padrão é
`automation/blender` relativo ao projeto; se configurar `blender.scripts_dir`,
passe o mesmo valor em `start(..., scripts_dir="...")`.
Scripts têm os privilégios do usuário: esta autorização não é um sandbox.

Não abre/salva/substitui a cena. Um arquivo aberto precisa estar dentro da raiz
autorizada. Uma cena ainda não salva é vinculada explicitamente pelo `start`.
Ao abrir um arquivo fora do projeto, os comandos são recusados. Um único Blender
pode possuir a sessão de cada projeto. Pare com `ordax['stop']()`; fechar o Blender
também libera o bloqueio. A ativação não é automática após reiniciar o aplicativo.

Exemplos de payloads (campo `project` é o slug cadastrado):

```json
{"action":"blender.live_inspect","payload":{"project":"model","limit":64}}
{"action":"blender.live_run_python","payload":{"project":"model","script_path":"automation/blender/edit.py","timeout_seconds":60}}
{"action":"blender.live_result","payload":{"project":"model","command_id":"ID_RETORNADO"}}
```

## Garantias e limites

- Fila local em `.ordax/blender`; não há servidor HTTP nem porta pública nova.
  Ignore `.ordax/` no Git do projeto. Não compartilhe essa pasta com usuários
  não confiáveis. Evidências da fila não são removidas automaticamente.
- Timer executa um comando por vez na thread principal. Intervalo de 0,2 s não é
  garantia de latência: renderizações, diálogos e scripts longos podem bloquear o
  Blender. Não executar tarefas longas em timers é responsabilidade dos scripts.
- Cada comando tem identificador, sessão, validade e resultado consultável.
  Um timeout não cancela uma execução já iniciada: consulte `live_result` antes de
  repetir. Comandos reivindicados nunca são reexecutados após falha/reinício.
- O script é relido e seu hash é conferido antes de executar. Exceções podem
  deixar alterações parciais: ainda não há transações/rollback automático.
- O snapshot informa arquivo, alterações não salvas, modo, objetos e dimensões.
  Limite padrão de 64 objetos; até 1.000 sob demanda. Não é evidência visual.
- Sessão identifica a instância, não a revisão da geometria. Edições manuais
  simultâneas ainda exigem coordenação. Contexto de operadores `bpy.ops` também
  exige cuidado: scripts devem preferir a API de dados para operações sem UI.

API utilizada: [Blender application timers](https://docs.blender.org/api/current/bpy.app.timers.html).

Verificação focada: `python -m unittest discover -s tests -p test_blender_live.py`.
Smoke com bpy real: `blender --background --factory-startup --python-exit-code 1
--python scripts/verify_live_blender.py`. O smoke verifica três comandos na mesma
sessão e alteração de objeto sem salvar; não substitui teste de interação na GUI.
