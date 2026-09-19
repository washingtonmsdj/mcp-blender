# Etapa 5 — checkpoints e recuperação

Checkpoints são cópias locais completas do arquivo Blender, incluindo geometria
em memória ainda não salva. Não são commits Git, backups completos de assets
externos nem garantia de recuperação após falha de disco. Nenhum `.blend` é enviado
à nuvem automaticamente.

## Autorizações independentes

No `blender` do projeto cadastrado:

```json
{
  "allow_modeling": true,
  "allow_checkpoints": true,
  "allow_restore": false,
  "checkpoint_before_modeling": true
}
```

No companion atualizado, dentro do Blender:

```python
ordax['start'](r"RAIZ_DO_PROJETO", allow_modeling=True,
              allow_checkpoints=True, checkpoint_before_modeling=True)
```

Isso protege as operações tipadas `model_*`, mas **não permite restauração remota**.
Para restaurar, habilite `allow_restore: true` no cadastro local e
`allow_restore=True` ao conectar a sessão. Criação/restauração exigem autorização
no agente e no companion. A proteção automática é acionada se estiver habilitada
em qualquer um dos dois; sem permissão de checkpoint, a alteração é recusada.
`allow_scripts` não é necessário e continua independente.

A proteção automática salva uma cópia antes de cada comando tipado de modelagem,
o que custa disco e tempo. Ela não intercepta edição manual, scripts livres,
outros add-ons ou ferramentas de outro processo. Para essas operações, crie um
checkpoint explicitamente antes de começar. Não há checkpoint a cada frame.

## Ações

```json
{"action":"blender.checkpoint_create","payload":{"project":"model","label":"antes-dos-detalhes"}}
{"action":"blender.checkpoint_list","payload":{"project":"model","limit":20}}
{"action":"blender.checkpoint_restore","payload":{"project":"model","checkpoint_id":"ID_HEX_RETORNADO","expected_sha256":"HASH_RETORNADO","confirm_replace_scene":true}}
```

`checkpoint_create` usa Save Copy: não troca o arquivo ativo nem sobrescreve o
original. Retorna ID, SHA-256, tamanho, origem e data. O catálogo pode ser consultado
sem Blender conectado. Os hashes são conferidos ao restaurar, não em cada listagem.

`checkpoint_restore`:

1. Verifica ID, hash e autorização, e recusa modo Edit/Sculpt ou render ativo.
2. Salva um checkpoint de segurança do estado **atual**, antes de substituí-lo.
3. Copia o checkpoint escolhido para um novo arquivo de trabalho no mesmo diretório,
   preservando os caminhos relativos remapeados.
4. Grava um registro de recuperação, troca a identidade da sessão e abre a cópia
   com `load_ui=False` e `use_scripts=False`.
5. Retorna o arquivo ativo e o ID da cópia de segurança. Comandos enfileirados com
   a identidade antiga são rejeitados; observe novamente antes de continuar.

Depois da restauração, o Blender trabalha em `recovery-<command_id>.blend`, **não
no arquivo original nem no checkpoint imutável**. Um Ctrl+S posterior salva essa
cópia de trabalho. Para promover o resultado ao projeto, escolha conscientemente
um destino com Save As; esta etapa não sobrescreve o original automaticamente.

Em timeout, consulte `blender.live_result` com o ID do comando. Não repita a
restauração às cegas. Em falha, `checkpoint`/`recovery` na resposta e o journal
local indicam o backup criado. Em queda do processo, o journal pode permanecer
em `opening`: isso não prova se a abertura terminou. Inspecione a cena após reiniciar.

## Armazenamento e limitações

- Arquivos em `.ordax/blender/checkpoints/<id>/`: `checkpoint.blend`, metadados,
  cópias de recuperação e journals. Ignore `.ordax/` no Git do projeto.
- Até 100 diretórios de checkpoints; abaixo de 512 MiB livres, novos checkpoints
  são recusados. Esse espaço mínimo não garante que uma cena grande caberá.
  Falha de gravação impede a alteração protegida/restauração. Não há exclusão ou
  retenção automática. Arquivos incompletos ficam para inspeção local.
- Chegar ao limite também bloqueia restauração, porque ela precisa de um novo
  backup. Faça manutenção local consciente, preservando os checkpoints necessários.
- Texturas, caches, bibliotecas vinculadas e outros arquivos externos não são
  copiados. Preserve-os separadamente. Imagens com alterações pendentes bloqueiam
  o checkpoint; salve esses dados explicitamente primeiro. Não há empacotamento
  automático nem garantia sobre estado externo de simulações/add-ons.
- A criação pode disparar handlers de salvamento; a abertura, handlers de carga
  instalados. `use_scripts=False` desabilita autoexec do arquivo, não transforma
  Blender/add-ons em um sandbox. O histórico de Undo pode ser reiniciado.
- Checkpoints não são assinatura criptográfica nem proteção contra outro programa
  local autorizado a modificar os mesmos arquivos. SHA-256 detecta divergências.

Teste focal: `python -m unittest discover -s tests -p test_blender_checkpoints.py`.
Smoke: `blender --background --factory-startup --python-exit-code 1 --python
scripts/verify_live_checkpoints.py`. Verifica restauração, recuperação das mudanças
não salvas, original intacto, caminhos relativos e sobrevivência do timer. O teste
usa uma cena descartável; não substitui validação com todos os add-ons na GUI.

API utilizada: [operadores de arquivo do Blender 5.2](https://docs.blender.org/api/5.2/bpy.ops.wm.html).
