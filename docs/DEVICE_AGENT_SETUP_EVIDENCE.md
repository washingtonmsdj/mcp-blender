# Evidências da implantação — 25/09/2026

Máquina: DESKTOP-COHT67R. Device: `5f2d4e44-06d8-4bf7-8aef-a9cd63e96ff4`.
Control Plane: `ordax-control-plane` / `eobcxuyvhkvdmkbaihwh`.

## Causa raiz

O runtime 1.19.47 continuava em transporte legado e a tarefa executava
`pythonw.exe -m ordax_dev_agent.task_entry`. Faltava `device-token.txt`.
O enrollment automatizado dependia de identidade OIDC de self-hosted Actions;
o bootstrap identificava tokens existentes, mas não recuperava token ausente.
`paired=true` não demonstrava heartbeat válido. A troca da ação da tarefa também
deixava processos legados vivos, situação corrigida no setup.

## Resultado observado

- Runtime instalado: 1.20.1; protocolo `development-v2`.
- Enrollment partiu de PC sem `device-token.txt`, autenticando a conta GitHub
  local e vinculando o cadastro deste PC à identidade autorizada pelo proprietário.
- Token bruto gerado e armazenado somente localmente; backend recebe SHA-256.
- Nova execução do setup: `ORDAX_DEVICE_AGENT=READY`, `TOKEN_UNCHANGED=True`.
- Scheduled Task retargetada ao supervisor PowerShell externo e processo
  supervisionado confirmado pelo `/status`.
- `cerco-no-interior-mvp` registrado e disponível no catálogo local.
- Heartbeat observado diretamente em `ordax_devices.last_seen_at`.
- Zero processos `Runner.Listener`/`Runner.Worker`; zero serviços de runner ativos.
- Job real `45c81192-9456-4dbd-af15-44cc49a1bd0e`: ação `blender.version`, projeto
  `cerco-no-interior-mvp`, concluído `succeeded` em `2026-09-25T20:50:18.133332Z`.
  Retorno: Blender 5.2.2 LTS, exit code 0.
- Credencial revogada propositalmente às 20:51:03 UTC. Supervisor recuperou
  automaticamente com o login existente e iniciou novo runtime às 20:51:38 UTC.
  Backend confirmou uma credencial ativa e a anterior revogada.
- `ordax-dev-notebook` conservou sua identidade e não foi usado neste PC.
- Quatro execuções antigas do Autopilot canceladas. Fila consultada após a
  implantação: vazia. Recovery secundário ficou opt-in e com label própria.

## Testes

[CI da implementação](https://github.com/washingtonmsdj/mcp-blender/actions/runs/36188796343):
494 testes Python passaram em Windows e em Linux; cinco testes Deno da Edge
Function passaram; todos os scripts PowerShell passaram no parser.
Os dez testes de setup incluem concorrência, dez repetições, offline, token
ausente/revogado, perda de resposta, binding incorreto e falha de ACL.
`control-plane/tests/device_setup.sql` foi executado transacionalmente com
rollback: idempotência, proprietário, replay de token revogado e permissões.

## Reboot real

O usuário autorizou o reboot após salvar o trabalho. O teste foi preparado com
baseline de boot `2026-09-24T16:52:17.5487410Z` e tarefa
`OrdaX Setup Reboot Verification`, executada no próximo login.
O resultado persistente será `%LOCALAPPDATA%\OrdaX\DevAgent\setup-verification.json`.
O teste exige boot do Windows diferente, supervisor vivo, heartbeat recente e
nenhum runner ativo; a tarefa se desabilita após sucesso.

**Resultado observado: FALHA no retorno automático após reboot.**
O Windows reiniciou em `2026-09-25T21:03:24Z`, diferente da baseline. A tarefa
foi iniciada após login às 21:08 UTC, mas o Agent não voltou: o heartbeat
permaneceu em 21:01:19 UTC e a tarefa de verificação expirou sem gerar sucesso.
O supervisor existia sem processo Agent nem novos registros de inicialização.

Foi necessária intervenção nesta tarefa. Os commits `c90e3a0` e `dfd9533`
retiraram importações de dependências e consulta de identidade da inicialização
de uma instalação já configurada, evitaram autoload de PowerShell.Utility nesse
caminho, adicionaram logs desde a entrada do supervisor e modo NonInteractive.
O ponto interno exato do bloqueio original não foi observado; os logs antigos
começavam somente depois dessas operações. Não tratar a hipótese como diagnóstico
comprovado de uma biblioteca específica.

Depois de atualizar e relançar a tarefa manualmente, o Agent iniciou às 21:21 UTC.
O Control Plane confirmou heartbeat em `2026-09-25T21:21:49.171607Z`, boot ID
`43d34f36-121f-43a1-bc64-b49298332e73`. Os 18 testes de scripts passaram novamente,
assim como o parser PowerShell. A CI das correções está associada ao commit
`dfd9533`. A tarefa de verificação de reboot foi desabilitada para evitar que um
login posterior transforme esta tentativa assistida em falso sucesso.

**A correção ainda precisa de outro reboot autorizado para comprovar retorno
automático. Nenhum segundo reboot foi executado.** O Agent foi recuperado, mas
o critério final de conclusão do projeto permanece pendente.

## Comando único

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\OrdaX\DevAgent\src\scripts\windows\ordax-device-agent-setup.ps1"
```

Para PC novo, o mesmo script pode ser executado a partir da cópia do repositório.
Git, Python e gh ausentes são instalados pelo WinGet; o login pelo navegador
pode exigir a interação do proprietário. Nenhum runner ou grant manual participa.
