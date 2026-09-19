# Self-hosted runner para Blender + Unity

O runner é a ponte entre o GitHub e os programas instalados no Windows.

## Pré-requisitos

Na máquina que executará Blender/Unity:

- Git;
- PowerShell;
- Python 3.11+;
- Blender, se os tools de Blender forem usados;
- Unity Hub + a versão usada pelo projeto;
- Unity ativado para o usuário Windows que executará o runner.

Teste local:

```powershell
.\scripts\windows\toolchain-status.ps1 -RequireUnity
```

Para exigir Blender também:

```powershell
.\scripts\windows\toolchain-status.ps1 -RequireUnity -RequireBlender
```

## Registrar o runner

No GitHub, abra:

Settings > Actions > Runners > New self-hosted runner

Escolha Windows / x64 e execute exatamente os comandos temporários mostrados pelo GitHub.

O token de registro é temporário. Não grave esse token no repositório, em issues ou em arquivos .env.

## Execução persistente

`run.cmd` interativo é adequado para diagnóstico e para o primeiro registro do runner.

No Windows, o modo serviço é escolhido durante a configuração oficial do runner. Se o runner já foi configurado sem serviço, a documentação do GitHub exige remover/reconfigurar o runner e escolher service mode; o OrdaX não tenta contornar esse fluxo.

Depois que um serviço oficial `actions.runner.*` existir, use:

```powershell
.\scripts\windows\ordax-runner-service.ps1
```

Esse script apenas endurece o serviço já suportado pelo GitHub:

- inicialização automática;
- recovery pelo Windows Service Control Manager;
- restart após 5 s, 15 s e 30 s;
- validação de estado.

O GitHub runner é uma segunda camada de recuperação/CI. A disponibilidade normal do OrdaX Agent não depende dele.

## Testar o toolchain

No repositório mcp-blender:

Actions > Toolchain smoke > Run workflow

O job mostra os caminhos detectados para Unity e Blender.

## Validar o HORDAX

No repositório mcp-blender:

Actions > Validate HORDAX in Unity > Run workflow

Por padrão o workflow usa:

```text
dev/weapon-crowd-systems
```

Ele faz checkout isolado do HORDAX dentro do workspace do runner. Não usa nem altera seu clone pessoal.

## Critérios de falha

A validação falha quando:

- o processo do Unity retorna código diferente de zero;
- o log contém erro C#;
- o método executeMethod não existe;
- HORDAX.EditorTools.CiValidation encontra erro bloqueante nos dados.

O log do Unity é publicado como artifact por 14 dias.

## Segurança

Mantenha workflows de self-hosted runner restritos a acionamento confiável. Não execute código de pull requests externos ou não confiáveis nessa máquina.

Não armazene no repositório:

- token do runner;
- PAT;
- credenciais GitHub;
- chaves de API;
- dados de licença.


## Bootstrap de resiliência

A instalação recomendada para a máquina OrdaX é:

```powershell
.\scripts\windows\ordax-resilience-install.ps1
```

O bootstrap instala/atualiza o **OrdaX Dev Agent** como Scheduled Task do usuário interativo, com restart-on-failure e launcher auto-recuperável.

Por padrão ele não reconfigura o GitHub runner. Se um runner oficial já estiver configurado como Windows Service, use `-HardenRunnerService` para aplicar a política adicional de recovery:

```powershell
.\scripts\windows\ordax-resilience-install.ps1 -HardenRunnerService
```

O Agent continua rodando na sessão interativa correta para controlar Blender e Unity visíveis.

Para diagnóstico local sem modificar nada:

```powershell
.\scripts\windows\ordax-resilience-status.ps1
```

Um sistema saudável deve mostrar o serviço `actions.runner.*` em `Running/Auto`, a tarefa `OrdaX Dev Agent` instalada e o endpoint local `127.0.0.1:8765/status` respondendo.
