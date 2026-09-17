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

## Primeira execução

Para o primeiro teste, rode o runner de forma interativa:

```powershell
.\run.cmd
```

Isso mantém o mesmo perfil de usuário do Windows que já possui a ativação do Unity.

Depois que a validação estiver funcionando, o runner pode ser convertido em serviço usando a conta Windows adequada.

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
