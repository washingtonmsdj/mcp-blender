# Instalação e recuperação do Device Agent

No Windows, execute na cópia do repositório:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\ordax-device-agent-setup.ps1
```

O setup usa o checkout gerenciado `%LOCALAPPDATA%\OrdaX\DevAgent\src`, faz
fast-forward da `main`, repara o ambiente Python e instala a tarefa. Uma árvore
com alterações ou histórico divergente é preservada e diagnosticada. Não há
`reset --hard`. O comando pode ser repetido. `-NonInteractive` nunca abre login.
Git, Python e GitHub CLI ausentes são instalados pelo WinGet oficial. Se WinGet
também não estiver disponível, o setup informa qual pré-requisito falta.

Na primeira autenticação, o usuário entra no GitHub pelo navegador, via `gh`.
Este Control Plane de engenharia permite cadastrar dispositivos a usuários com
permissão **admin** no repositório oficial (ID 1141624338). O backend confirma a
identidade numérica do usuário e a permissão diretamente nas APIs do GitHub.
Acesso público ao repositório não concede permissão para cadastrar dispositivos.
O login do usuário não é uma credencial do Agent e não é salvo pelo setup.

Cada máquina possui um binding SHA-256 do Windows MachineGuid. O binding serve
para identificar o equipamento; quem autoriza enrollment/recovery é o usuário
autenticado. O backend exige o mesmo proprietário nas recuperações seguintes.
Cadastros legados sem binding precisam de migração administrativa auditada;
nunca são associados por coincidência do nome do computador.

O token aleatório nasce no PC, em arquivo pendente protegido, antes da chamada
de rede. Somente o SHA-256 é enviado ao backend. A transação serializa por
máquina, revoga credenciais anteriores e concede apenas `develop_heartbeat`,
`develop_poll`, `develop_report`. Repetir uma requisição confirmada reutiliza
a credencial; token revogado nunca é reativado. O limite é dez rotações/hora.
Se a resposta se perder, o setup identifica o token pendente e conclui sua
promoção local. A escrita usa rename atômico no mesmo volume e ACL restrita
ao usuário e SYSTEM. Falha de ACL impede enrollment.

`agent-settings.json` conserva projetos e opções existentes. Por padrão o setup
continua configurando o Control Plane oficial `development-v2`. Depois que o
backend Cloudflare estiver publicado e validado, o mesmo setup pode migrar
explicitamente para `cloudflare-v3`, sem copiar token manualmente:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\ordax-device-agent-setup.ps1 `
  -ControlPlaneProtocol cloudflare-v3 `
  -ControlPlaneUrl "https://<worker>.workers.dev"
```

No v3, o token continua nascendo localmente; somente o SHA-256 chega ao Worker.
O Worker valida o usuário diretamente no GitHub e exige permissão `admin` no
repositório oficial. O binding da máquina é único, o proprietário GitHub é
preservado e rotações são limitadas a dez por hora. O bootstrap lê o provider
salvo e recupera a mesma identidade após restart/reboot; ele não força retorno
ao Supabase.

O setup registra
`cerco-no-interior-mvp` e `dioramas-biblicos` quando suas pastas conhecidas existem,
sem sobrescrever personalizações de projetos já cadastrados.

A Scheduled Task aponta para o PowerShell em
`%LOCALAPPDATA%\OrdaX\DevAgent\bootstrap\ordax-agent-bootstrap.ps1`.
Ela executa no desktop do usuário, após login, com tentativa periódica e sem
limite de duração. O supervisor externo relança o processo, tenta reparar
venv ausente e recupera credenciais com o login já existente, sem abrir UI.
Sem internet, a credencial e as configurações são preservadas. Uma resposta
401 do transporte solicita recuperação; erros de rede não rotacionam tokens.
Se o login também expirou, execute novamente o setup para autenticar-se.

`ORDAX_DEVICE_AGENT=READY` só aparece depois de `/status` confirmar o protocolo
selecionado, identidade, projeto, tarefa externa e heartbeat aceito há menos de
60 segundos. No `cloudflare-v3`, o setup também exige que a URL salva corresponda
à URL solicitada.
`paired=true` sozinho não comprova conexão.

## GitHub Actions

Runner não participa do boot, heartbeat, enrollment nem recovery normal.
Recovery Actions é secundário: execução manual ou `ORDAX_RECOVERY_ENABLED=true`,
requer label `ordax-recovery`, cancela execuções
superadas e verifica HEAD atual antes de alterar o PC. Autopilot requer a
variável `HORDAX_AUTOPILOT_ENABLED=true` e a label `hordax-autopilot` para não
consumir um runner de recuperação. Filas antigas devem ser canceladas na
implantação, porque editar um workflow não reescreve execuções já enfileiradas.
Smoke e validação Unity usam labels `ordax-toolchain` e `hordax-unity`, com
concorrência limitada e cancelamento de execução superada.

## Verificação

Testes: `python -m unittest discover -s tests -p test_device_setup.py -v`.
Cobrem instalação, dez repetições, perda de resposta, token ausente/revogado,
offline, binding incorreto, ACL e preservação de settings/projetos.
O RPC tem testes transacionais de proprietário, replay e permissões de execução.
O teste de integração deve registrar device ID, heartbeat, job Blender e a
configuração da Scheduled Task, sem registrar tokens.

Reiniciar a tarefa comprova relançamento. Reboot real é uma verificação distinta:
salve o trabalho, reinicie o Windows e faça login; confirme novo boot ID e
heartbeat no backend. Não tratar simulação de restart como prova de reboot.

Referências: [autenticação Edge Functions](https://supabase.com/docs/guides/functions/auth),
[identidade GitHub](https://docs.github.com/en/rest/users/users#get-the-authenticated-user),
[permissões do repositório](https://docs.github.com/en/rest/repos/repos#get-a-repository).
