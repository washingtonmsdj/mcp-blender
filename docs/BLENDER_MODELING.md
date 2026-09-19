# Etapa 4 — ferramentas explícitas de modelagem

As ferramentas abaixo operam na sessão Blender aberta, sem shell, `eval`, scripts
remotos ou mudança automática de modo. Use primeiro `blender.modeling_tools {}`
para consultar os schemas e `blender.object_info {"object":"Body"}` para examinar
transformações e modificadores. O esquema completo só é enviado quando solicitado.

## Autorização local independente

No cadastro do projeto, habilite `blender.allow_modeling: true`. No Blender,
recarregue o companion atualizado e conecte com:

```python
ordax['start'](r"RAIZ_DO_PROJETO", allow_modeling=True)
```

São necessárias as duas autorizações. `allow_scripts` pode e deve permanecer
desabilitado quando não houver necessidade de scripts livres. Consultas e capturas
não exigem autorização para modelagem. Todos os helpers `.py` precisam estar junto
do companion instalado. Publicar no Git não atualiza uma sessão já carregada.

## Ações

Os exemplos são argumentos de `action_execute`/payload da fila; inclua o projeto
cadastrado. `timeout_seconds` é opcional, padrão 60. Parâmetros desconhecidos ou
inaplicáveis ao tipo escolhido são recusados, não ignorados.

```json
{"action":"blender.model_create","payload":{"project":"model","name":"Body","primitive":"cube","size":2}}
{"action":"blender.model_transform","payload":{"project":"model","object":"Body","location":[0,0,1],"scale":[1,0.5,2],"rotation_degrees":[0,0,30]}}
{"action":"blender.model_modifier","payload":{"project":"model","object":"Body","name":"SoftEdges","type":"BEVEL","width":0.05,"segments":3}}
```

- **Criar:** `cube` (`size`), `sphere` (`radius`, `segments`) ou `cylinder`
  (`radius`, `depth`, `segments`). `location` opcional; objeto novo na coleção raiz
  da cena, sem alterar seleção/câmera. Usa BMesh, não operadores dependentes da UI.
  Nomes existentes são recusados. Esta etapa não configura UVs nem materiais.
- **Transformar:** valores absolutos de localização, escala e rotação local do
  objeto. Posição respeita o parent existente. Rotação usa graus e muda o modo para
  Euler XYZ; o retorno descreve o antes/depois. Escala positiva, não aplicada à malha.
- **Adicionar modificador:** BEVEL (`width`, `segments`), SUBSURF (`levels`),
  SOLIDIFY (`thickness`) ou MIRROR (`axis`: X/Y/Z). Acrescenta ao fim da pilha;
  não substitui nem aplica modificadores. Mirror usa a origem local e pode produzir
  sobreposição em malhas já simétricas; examine as capturas.

Comprimentos usam unidades internas da cena, não metros presumidos. Para projetos
com escala física, consulte `unit_scale_m` nas capturas. Os schemas descrevem limites
numéricos; nomes aceitam até 63 bytes UTF-8. Subdivisão limitada a dois níveis, pilha
até oito modificadores; há limites conservadores de faces avaliadas. Não representam
garantia absoluta de tempo/memória para qualquer malha ou pilha preexistente.

## Verificação e limites

Uma resposta contém `before`, `after`, comando e sessão; não envia a cena inteira.
Após editar, use `blender.live_capture` ou `blender.reference_review` para avaliar
o resultado visual. Sucesso operacional não significa qualidade artística.

As ações exigem Object Mode, nenhum render ativo e, para editar existentes, malha
local sem vínculo/override de biblioteca, animação ou constraints. Não há exclusão,
extrusão de faces, aplicação destrutiva de modificadores, seleção de vértices,
salvamento ou edição em lote nesta etapa.

Em exceções, criação remove os dados recém-criados, transformações tentam restaurar
seus valores e adição de modificador tenta remover o recém-adicionado. Isso não é
uma transação durável: falhas do processo, callbacks de outros add-ons e efeitos em
dependentes podem escapar à reversão. Falhas são marcadas como potencialmente
parciais; consulte o objeto e capture novamente. Não há integração garantida com
Ctrl+Z nem checkpoints persistentes ainda. Nunca salve automaticamente por essa razão.

Em timeout, consulte `blender.live_result` pelo comando antes de repetir qualquer
alteração. IDs de comandos evitam reexecução do mesmo pedido na fila, mas enviar
outro pedido com novo ID continua sendo uma nova operação.

Verificação focada: `python -m unittest discover -s tests -p test_blender_modeling.py`.
Smoke com Blender: `blender --background --factory-startup --python-exit-code 1
--python scripts/verify_live_modeling.py`. Exercita oito operações, permissões,
nomes duplicados e reversão em falhas injetadas, sem salvar um arquivo.

API: [BMesh no Blender 5.2](https://docs.blender.org/api/5.2/bmesh.ops.html).
