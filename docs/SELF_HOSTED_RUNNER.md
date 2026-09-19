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

## Execução persistente obrigatória

`run.cmd` interativo é permitido apenas para diagnóstico inicial. Não é o estado operacional do OrdaX.

Depois que o runner estiver configurado uma vez com o token temporário do GitHub, instale/hardenize o runner existente como Windows Service:

```powershell
.\scripts\windows\ordax-runner-service.ps1
```

O script:

- reutiliza o runner já configurado; não grava token no repositório;
- instala o serviço somente se ele ainda não existir;
- define inicialização automática;
- configura recuperação pelo Windows Service Control Manager;
- reinicia após falhas em 5 s, 15 s e 30 s;
- inicia o serviço e valida o estado.

O runner passa a existir independentemente de login no Windows. Isso é o canal de recuperação fora do processo do OrdaX Agent.

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

Execute uma vez em PowerShell elevado. O bootstrap configura dois mecanismos independentes:

1. **GitHub Actions runner** como Windows Service automático;
2. **OrdaX Dev Agent** como Scheduled Task no usuário interativo, com restart-on-failure.

O runner de serviço pode recuperar o Agent quando ele cai. O Agent continua rodando na sessão interativa correta para controlar Blender e Unity visíveis.

Para diagnóstico local sem modificar nada:

```powershell
.\scripts\windows\ordax-resilience-status.ps1
```

Um sistema saudável deve mostrar o serviço `actions.runner.*` em `Running/Auto`, a tarefa `OrdaX Dev Agent` instalada e o endpoint local `127.0.0.1:8765/status` respondendo.
