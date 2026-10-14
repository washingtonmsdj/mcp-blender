# ORDAX Studio — conceito de interface v1

Conceito visual gerado em 3 de outubro de 2026. A imagem apresenta uma proposta; os projetos, a cena e os estados são ilustrativos. Não altera a interface executável nem habilita a integração.

## Fontes analisadas

- [mcp-blender — main analisada](https://github.com/washingtonmsdj/mcp-blender/tree/2258a5587acb668557f704cde1f22a3e49b17846).
- [Shell atual do Studio](https://github.com/washingtonmsdj/mcp-blender/blob/2258a5587acb668557f704cde1f22a3e49b17846/ordax_studio/studio_product.html).
- [CSS atual do Studio](https://github.com/washingtonmsdj/mcp-blender/blob/2258a5587acb668557f704cde1f22a3e49b17846/ordax_studio/assets/studio.css).
- [prototipo-ordax-os — main analisada](https://github.com/washingtonmsdj/prototipo-ordax-os/tree/4fcf197765fb94674d99fbc0eb489ea62325b4ad).
- [Tokens visuais canônicos](https://github.com/washingtonmsdj/prototipo-ordax-os/blob/4fcf197765fb94674d99fbc0eb489ea62325b4ad/system/surface/ui/tokens.css).
- [Layout da Surface](https://github.com/washingtonmsdj/prototipo-ordax-os/blob/4fcf197765fb94674d99fbc0eb489ea62325b4ad/system/surface/ui/surface.css).
- [Composição da barra lateral e da barra de status](https://github.com/washingtonmsdj/prototipo-ordax-os/blob/4fcf197765fb94674d99fbc0eb489ea62325b4ad/system/surface/ui/desktop-shell.mjs).
- [Contrato de integração Studio/OS](https://github.com/washingtonmsdj/prototipo-ordax-os/blob/4fcf197765fb94674d99fbc0eb489ea62325b4ad/docs/contracts/studio-runtime-integration.json).

## Diagnóstico visual

A avaliação abaixo é uma interpretação do HTML/CSS da main remota, não uma auditoria interativa do aplicativo em execução.

1. O Studio já utiliza grafite e azul glacial, mas mantém variáveis próprias. A integração deve consumir os tokens semânticos do OS.
2. A interface empilha appbar de 52px, barra de projeto de 46px e cabeçalhos internos de 52px. A repetição de cabeçalhos reduz a área útil e enfraquece a hierarquia.
3. O workspace usa três colunas, com lista de projetos, navegação, conteúdo central e prévia competindo por atenção. A prévia recebe 44% do espaço por padrão, independentemente da tarefa.
4. Muitos rótulos, metadados e estados usam 9–11px. O novo conceito aumenta a legibilidade e reduz a quantidade de informação simultânea.
5. A shell de produto ainda mostra “ORDAX Dev”, enquanto o produto documentado é ORDAX Studio. O conceito unifica o nome.
6. A Surface do prototipo-ordax-os já fornece a estrutura que deve abrigar o Studio: barra lateral de 102px, janela com título de 58px e barra de status inferior de 44px.

## Decisões do conceito

- Reutilizar a barra lateral e a barra de status da Surface.
- Mostrar o Studio maximizado na área de trabalho.
- Manter navegação e troca de projeto em uma coluna contextual, com densidade moderada.
- Destacar o nome do projeto, a tarefa e a prévia central.
- Organizar Prévia, Arquivos, Alterações e Memória em abas.
- Reservar o painel à direita para contexto e ferramentas; na implementação, torná-lo recolhível.
- Resumir atividade recente em linhas, evitando uma grade de indicadores.
- Usar Inter, raios de 8/12px e os tokens grafite/glacial do prototipo-ordax-os.

| Papel | Token da referência |
| --- | --- |
| Fundo | #080f19 |
| Aplicativo | #090f1b |
| Painéis | #111e30 |
| Bordas | #243249 |
| Texto | #e2ebf7 |
| Texto secundário | #8e9db4 |
| Destaque | #a9c9f7 |
| Botão principal | #d1e4ff |
| Texto do botão | #172b47 |

## Integração a respeitar

O contrato fixa o Studio como um único produto; Blender e Unity são capacidades. Identidade, espaços, permissões, memória e roteamento de modelos pertencem ao OS. A main analisada mantém o despacho de mutações desabilitado. Os controles e estados da imagem são exemplos de interface futura, sem comprovar conexão ou execução atual.

## Entregáveis

- Imagem: `ordax-studio-concept-v1.png`.
- Prompt completo: `ordax-studio-concept-v1.prompt.txt`.
- Método: ferramenta integrada de geração de imagens, categoria `ui-mockup`.
- Validação: inspeção visual da imagem gerada; estrutura, paleta, textos principais e indicação de dados ilustrativos conferidos.
