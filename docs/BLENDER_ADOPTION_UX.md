# ORDAX Studio — Blender adoption UX

## Objetivo

O ORDAX Studio deve reutilizar uma janela Blender já aberta sempre que isso puder ser feito com segurança. Ele não pode abrir uma segunda janela apenas porque o companion não respondeu.

## Estados do Preview

| Estado | Significado | Ação principal |
| --- | --- | --- |
| `connected` | Companion ORDAX já está vivo na janela correta | Capturar / trabalhar |
| `adopted` | Uma janela aberta foi associada ao projeto nesta sessão | Capturar / trabalhar |
| `ambiguous` | Mais de uma janela corresponde ao projeto | Escolher PID explicitamente |
| `restart_required` | Há Blender aberto, mas sem bridge ORDAX ativo | Instalar bridge e reabrir aquela janela uma vez |
| `idle` | Nenhuma janela Blender está aberta | Abrir Blender pelo ORDAX |

## Regra de segurança

`blender.live_start` continua fail-closed. Se existir qualquer processo Blender unmanaged e não houver uma janela adotável correspondente ao projeto, o ORDAX se recusa a abrir outra instância.

O Studio não usa injeção de processo, shell arbitrário nem automação de teclado para anexar código a um Blender unmanaged. A adoção acontece pelo add-on leve `ORDAX Studio Bridge`, instalado no perfil do Blender e carregado em lançamentos futuros.

## Primeiro uso

1. O Studio detecta Blender aberto sem bridge e entra em `restart_required`.
2. **Instalar bridge** sincroniza o add-on e a configuração de projetos.
3. A janela já aberta deve ser reaberta uma única vez para que o Blender carregue o add-on.
4. A partir daí, aberturas manuais são descobertas automaticamente e podem ser adotadas sem abrir uma segunda janela.

## Múltiplas janelas

O ORDAX nunca escolhe silenciosamente entre múltiplas janelas do mesmo projeto. O estado `ambiguous` lista os candidatos e exige um PID explícito.

## Contrato WebView

A shell do Studio expõe:

- `blender_prepare()` — resolve o estado atual sem abrir nova janela;
- `blender_install_bridge()` — instala/sincroniza o bridge e reavalia o estado;
- `blender_instances()` — lista janelas descobertas e processos unmanaged;
- `blender_adopt(pid)` — adota uma janela específica;
- `blender_start()` — abre Blender somente através do contrato protegido `blender.live_start`.

O componente `blender-connection.js` traduz esse contrato para ações contextuais no painel direito de Preview.
