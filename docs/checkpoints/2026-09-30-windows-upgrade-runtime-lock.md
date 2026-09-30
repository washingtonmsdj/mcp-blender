# Windows upgrade — runtime lock

## Falha reproduzida pelo usuário

Ao instalar ORDAX Studio 0.3.1 por cima de uma instalação ativa, o Inno Setup falhava ao substituir `ORDAX Runtime.exe` com `DeleteFile failed; code 5` porque o supervisor permanecia em execução e mantinha o executável bloqueado.

## Correção 0.3.2

- launchers nativos publicam eventos de shutdown por sessão para Studio e Runtime;
- o instalador sinaliza encerramento cooperativo antes da fase de cópia;
- o supervisor encerra também o processo Python filho pelo Job Object;
- 0.3.0/0.3.1 continuam atualizáveis por um caminho de compatibilidade que encerra os launchers antigos, que ainda não conhecem o evento;
- o CI reinstala o mesmo Setup por cima de um Runtime action-ready ainda em execução e exige que o processo antigo termine e o Runtime atualizado volte a ficar action-ready.

A correção não exige desinstalação prévia nem intervenção no Gerenciador de Tarefas.
