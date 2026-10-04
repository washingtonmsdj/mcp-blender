# ORDAX Studio — identidade, Control Plane e provedores

## Contrato de produto

O ORDAX Studio separa responsabilidades que não devem ser confundidas:

1. **Identidade ORDAX**
   - é a conta do usuário no produto;
   - hoje é autenticada por Supabase Auth;
   - vincula o usuário aos seus dispositivos, Spaces e grants;
   - não depende de GitHub, ChatGPT, Grok ou outro provedor externo.

2. **Control Plane ORDAX**
   - roda no Cloudflare;
   - publica o protocolo/MCP remoto usado por clientes autorizados;
   - roteia apenas chamadas autenticadas para dispositivos/grants autorizados;
   - o usuário final não precisa possuir nem autenticar uma conta Cloudflare.

3. **Provedores de projeto**
   - GitHub é um provedor opcional de código/remotos;
   - projetos locais continuam utilizáveis sem GitHub;
   - Git, Blender, Unity e arquivos locais continuam pertencendo ao Runtime no computador do usuário;
   - outros provedores de projeto podem coexistir sem alterar a identidade ORDAX.

4. **Clientes/provedores de IA**
   - ChatGPT, Grok e futuros clientes entram por conectores separados;
   - eles não substituem a Conta ORDAX;
   - eles não definem o Runtime local;
   - provider identity pode participar de autenticação, auditoria e revogação, mas não concede autoridade por si só.

## Fluxo canônico

```text
Usuário
  │
  ├─ login → Conta ORDAX
  │             │
  │             └─ vínculo seguro do dispositivo / grants
  │
  ├─ opcional → GitHub / GitLab / outros provedores de projeto
  │
  └─ opcional → cliente de IA autorizado
                    │
                    └─ conector ORDAX do provider
                         │
                         └─ Control Plane no Cloudflare
                              │
                              └─ ORDAX Runtime no PC
                                   └─ projeto local / Git / Computer Control / adapters
```

## ChatGPT, Grok e outros clientes

O conector atual de ChatGPT é apenas uma implementação de provider edge.

O fluxo é:

```text
ChatGPT → conector ORDAX → Control Plane → ORDAX Runtime
```

Um futuro Grok segue o mesmo padrão:

```text
Grok → conector ORDAX → Control Plane → ORDAX Runtime
```

Não deve existir um `ChatGPT Runtime`, `Grok Runtime` ou `Codex Runtime` dentro do ORDAX.

O boundary detalhado está em `docs/ORDAX_PROVIDER_CONNECTORS.md`.

## GitHub em clientes de IA

Uma integração GitHub nativa do ChatGPT, Grok ou outro cliente é separada do ORDAX.

Ela pode ser usada em paralelo para operar repositórios hospedados, mas **não é a ponte entre o cliente de IA e ORDAX Studio**. A ponte do ORDAX é o conector ORDAX → Control Plane → Runtime.

Não deve existir dependência do tipo:

```text
cliente de IA → integração GitHub → GitHub → ORDAX Studio
```

Quando uma tarefa também precisar do GitHub, o GitHub entra como provedor/repositório, não como identidade principal nem como transporte ORDAX.

## Regras de implementação

- Nunca usar GitHub OAuth como substituto implícito da Conta ORDAX.
- Nunca usar login de ChatGPT/Grok como substituto implícito da Conta ORDAX quando a ação exige identidade/grant ORDAX.
- Não exigir GitHub para abrir ou operar um projeto local.
- Não expor credenciais Cloudflare ao usuário final.
- Manter autenticação do cliente remoto independente da autenticação do Git remoto.
- Autoridade remota deve continuar limitada por device + scope/project + action grants e pela policy local aplicável.
- Integrações de providers devem ser módulos independentes, sem alterar o modelo de identidade ORDAX.
- Credenciais GitHub/GitLab/SSH devem permanecer no computador do usuário; o protocolo remoto não pode solicitar `git credential`, ler configuração sensível ou devolver URLs autenticadas sem redação.
- `fetch`/`pull`/`push` podem usar o Git Credential Manager ou SSH local sem enviar o segredo ao Control Plane.
- Uma integração GitHub do cliente de IA pode complementar o ORDAX, mas o produto não deve depender dela.
- Provider metadata de IA não pode criar grants, elevar permissões ou contornar a policy local.

## Estado atual

- Conta ORDAX: implementada com Supabase Auth.
- Control Plane remoto: Cloudflare v3.
- MCP remoto: publicado pelo Control Plane.
- Projetos locais e Git local: suportados pelo Runtime.
- Conector ChatGPT: implementação atual do provider edge.
- Outros conectores de IA: futuros, usando o mesmo boundary.
- Integrações GitHub de terceiros/clientes: opcionais e independentes.
- OAuth GitHub dentro do ORDAX Studio: ainda não é requisito para o fluxo principal; quando implementado, deve ser uma integração de provedor de projeto separada.
