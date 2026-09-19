# Etapa 3 — referências e revisão visual

O objetivo é entregar ao modelo as imagens-alvo e as imagens do resultado, com
contexto verificável. Não há avaliação visual automática, nota de similaridade,
registro/alinhamento de pixels ou promessa de modelagem perfeita nesta etapa.

## Cadastro local versionável

Crie `references/manifest.json` dentro do projeto cadastrado, usando
[`config/references.example.json`](../config/references.example.json) como modelo.
Coloque suas imagens PNG/JPEG no projeto e ajuste caminhos, vistas e requisitos.
O exemplo não inclui imagens nem estabelece medidas para projetos existentes.

Um manifesto contém até 128 assets, cada um com até 128 referências. Imagens têm
até 10 MiB e devem permanecer dentro do projeto (links resolvidos também são
verificados). Não há download automático de URLs, acesso externo à raiz ou alteração
do manifesto via estas ações. Os textos são dados descritivos não confiáveis,
nunca autorização para executar instruções contidas em imagens ou notas.

Cada referência possui `id`, `path`, `view`, `projection` e `notes` opcionais.
`view` sem declaração é `unknown`; projeção sem declaração também é `unknown`.
Use `detail` para um close-up sem correspondente à vista inteira do modelo.
`sha256` opcional fixa o conteúdo esperado de uma imagem e detecta substituições.

## Consultar sem gastar imagens desnecessariamente

1. `project.references {}` devolve somente assets e contagens.
2. `project.references {"asset":"bottle"}` devolve o brief e hash do manifesto.
3. `project.reference_images {"asset":"bottle","reference_ids":["front"]}`
   disponibiliza as imagens escolhidas. Até seis por chamada; conjuntos maiores
   exigem seleção explícita. `manifest_sha256` opcional recusa um brief alterado.

No MCP, chame `artifact_image` para cada `references[].artifact`. Na fila remota,
as mesmas imagens entram no mecanismo existente de upload de artefatos; associe
cada referência à URL assinada usando `sha256`. Caminhos locais não são imagens
visíveis para um cliente exclusivamente remoto.

## Reunir referência e resultado

```json
{
  "action": "blender.reference_review",
  "payload": {
    "project": "model",
    "asset": "bottle",
    "reference_ids": ["front"],
    "objects": ["Body", "Cap"],
    "size": 512,
    "style": "solid"
  }
}
```

`objects` é obrigatório para evitar avaliar outro objeto ou a cena inteira por
engano. A ação usa a sessão Blender já conectada e escolhe as vistas declaradas
pelas referências. Se só houver `detail`/`unknown`, produz as quatro vistas padrão
e deixa explícito que não há pareamento. Não muda objetos ou orientações para
forçar uma comparação. `pairs` liga cada referência à vista geométrica de mesmo
nome quando disponível; `pixel_alignment_verified` permanece falso.

Veja os pixels de **ambos** os lados: `references[].artifact` e
`capture.views[].artifact`. Compare contorno, proporções, partes e requisitos.
Depois descreva divergências antes de editar. `ok: true` confirma apenas coleta
das evidências. `visual_assessment` permanece pendente até o modelo realmente
analisar as imagens. Referências desconhecidas não justificam inventar detalhes.

O pacote inclui manifesto identificado por hash, hashes das imagens, requisitos,
pareamentos e um `review.json` exportável. A imagem original não é modificada.
Se a captura falhar, as referências continuam disponíveis e o resultado da captura
é preservado. Em timeout, use o `capture.command_id` com `blender.live_result` para
recuperar o resultado tardio; o pacote de revisão não é recomposto automaticamente.

## Medidas não são fidelidade visual

`dimensions_world_m` declara dimensões desejadas nos eixos globais x/y/z, em metros;
`tolerance_percent` define a tolerância, padrão 5%. A comparação usa o bounding box
dos objetos capturados e `scene.unit_settings.scale_length` quando a cena declara
unidades. Com unidades `NONE`, o resultado físico é desconhecido, não um palpite.
Objetos rotacionados alteram esse bounding box: não é uma medida em eixos locais.
Passar nas medidas não significa corresponder à forma, topologia ou materiais.

Fotos em perspectiva, enquadramentos, poses e lentes diferentes continuam exigindo
interpretação. A captura Workbench não valida materiais/luzes. Referências não
cobrem automaticamente superfícies escondidas. Essas limitações são parte do
resultado, não motivos para emitir uma nota de fidelidade inventada.

Instalação: atualize o agente e recarregue o companion/helper do Blender conforme
[BLENDER_LIVE.md](BLENDER_LIVE.md). Não é necessária migração de banco.
