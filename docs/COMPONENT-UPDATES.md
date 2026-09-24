# OrdaX Device Agent — atualização por componentes

O OrdaX Device Agent não deve exigir reinstalação do OrdaX inteiro para evoluir.

## Regra

No Owner/Development, Git `main` continua sendo a entrega rápida e confiável.
Um fast-forward pode atualizar o checkout inteiro, porém isso **não significa**
reinstalar o sistema: dependências Python só são atualizadas quando o contrato de
instalação realmente muda; o Device Agent reinicia somente quando o runtime
afetado exige isso.

Em produção, a direção é `signed-component-slot`: pacote independente assinado,
candidate/pending, health, promoção e rollback. Essa ativação independente ainda
não é declarada pronta.

## Domínios iniciais

- `device-agent-core`;
- `device-mcp`;
- `adapter-blender`;
- `adapter-unity`;
- `adapter-git`;
- `bridge-blender-unity-cli`.

Cada domínio possui identidade, versão e failure domain próprios.

Uma mudança no Blender não deve obrigar update do Unity. Uma atualização do
Device Agent não deve reconstruir kernel/base do OrdaX. Uma mudança documental
não deve reiniciar runtime.

## Relação com o OrdaX OS

O OrdaX OS já reserva `component-slot` para componentes independentes. O Device
Agent segue a mesma semântica:

```text
download candidate
  -> verify signature/hash
  -> stage independent slot
  -> health
  -> promote
  -> preserve previous known-good
  -> rollback on failure
```

Até essa cadeia estar implementada e provada para o Device Agent, desenvolvimento
continua Git-first e fail-closed.

## Reinício

O planejador publica explicitamente:
- componentes afetados;
- necessidade de refresh do install contract;
- necessidade de restart do Device Agent;
- políticas de restart por componente;
- `whole_os_reinstall_required=false`;
- `whole_os_reboot_required=false`.

Um reboot só poderá ser exigido por uma capability que realmente dependa de Base,
kernel ou hardware, nunca porque uma app/adapter comum foi atualizada.
