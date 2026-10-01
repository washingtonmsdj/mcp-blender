# ORDAX Dev — identidade, Cloudflare e provedores de projeto

## Contrato de produto

O ORDAX Dev separa três responsabilidades que não devem ser confundidas:

1. **Identidade ORDAX**
   - é a conta do usuário no produto;
   - hoje é autenticada por Supabase Auth;
   - vincula o usuário aos seus dispositivos, Spaces e grants;
   - não depende de GitHub, GitLab ou outro provedor de código.

2. **Control Plane ORDAX**
   - roda no Cloudflare;
   - publica o MCP remoto usado por ChatGPT e outros clientes compatíveis;
   - roteia apenas chamadas autenticadas para dispositivos/grants autorizados;
   - o usuário não precisa possuir nem autenticar uma conta Cloudflare.

3. **Provedores de projeto**
   - GitHub é um provedor opcional de código/remotos;
   - projetos locais continuam utilizáveis sem GitHub;
   - Git, Blender, Unity e arquivos locais continuam pertencendo ao Runtime no computador do usuário;
   - no futuro outros provedores podem coexistir sem alterar a identidade ORDAX.

## Fluxo canônico

```text
Usuário
  │
  ├─ login → Conta ORDAX (Supabase Auth)
  │             │
  │             └─ vínculo seguro do dispositivo / grants
  │
  ├─ opcional → GitHub / GitLab / outros provedores de projeto
  │
  └─ ChatGPT
       │
       └─ plugin ORDAX Dev
            │
            └─ MCP remoto no Cloudflare
                 │
                 └─ ORDAX Runtime no PC
                      └─ projeto local / Git / Blender / Unity / arquivos
```

## GitHub no ChatGPT

O plugin GitHub do ChatGPT é uma integração separada.

Ele pode ser usado em paralelo para ler ou alterar repositórios hospedados no GitHub, mas **não é a ponte entre ChatGPT e ORDAX Dev**. A ponte do ORDAX é o plugin ORDAX Dev conectado ao MCP remoto do Control Plane.

Não deve existir dependência do tipo:

```text
ChatGPT → plugin GitHub → GitHub → ORDAX Dev
```

O fluxo correto é:

```text
ChatGPT → plugin ORDAX Dev → Cloudflare Control Plane → ORDAX Runtime
```

Quando uma tarefa também precisar do GitHub, o GitHub entra como provedor/repositório, não como identidade principal do ORDAX.

## Regras de implementação

- Nunca usar GitHub OAuth como substituto implícito da Conta ORDAX.
- Não exigir GitHub para abrir ou operar um projeto local.
- Não expor credenciais Cloudflare ao usuário final.
- Manter autenticação do cliente MCP independente da autenticação do Git remoto.
- Autoridade remota deve continuar limitada por device + project + action grants.
- Integrações de provedores devem ser adicionadas como módulos independentes, sem alterar o modelo de identidade ORDAX.
- Credenciais GitHub/GitLab/SSH devem permanecer no computador do usuário; o MCP não pode solicitar `git credential`, ler configuração sensível ou devolver URLs autenticadas sem redação.
- `fetch`/`pull`/`push` podem usar o Git Credential Manager ou SSH local sem enviar o segredo ao Control Plane.
- O plugin GitHub do ChatGPT pode complementar o ORDAX, mas o produto não deve depender dele.

## Estado atual

- Conta ORDAX: implementada com Supabase Auth.
- Control Plane remoto: Cloudflare v3.
- MCP remoto: publicado pelo Control Plane.
- Projetos locais e Git local: suportados pelo Runtime.
- Plugin GitHub do ChatGPT: opcional e independente.
- OAuth GitHub dentro do ORDAX Dev: ainda não é requisito para o fluxo principal; quando implementado, deve ser uma integração de provedor separada.
