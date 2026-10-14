# ORDAX Studio — conceito v3: foco, contas e criação

Atualizado em 3 de outubro de 2026. Evolução da v2 conforme a orientação do usuário: aparência de app premium, gerenciamento de múltiplas contas mais claro, chat à esquerda e prévia à direita.

A imagem é uma proposta visual. Conversas, conexões, arquivos e estados são ilustrativos; não comprovam integração executável.

## Diagnóstico da v2

- A identidade da conta aparecia em três lugares: aba, seletor e menu aberto.
- A lista de abas misturava serviço, conta e navegação de páginas.
- O menu flutuante encobria a conversa.
- A barra de endereço e os controles de navegação consumiam espaço recorrente.
- O chat, principal ponto de interação do usuário, estava à direita e disputava espaço com controles do navegador.

## Organização da v3

A hierarquia passa a ser **projeto → serviço → conta → conversa**. As contas ficam em uma lista persistente na lateral contextual do Studio, agrupadas por serviço. A barra lateral global e a barra de status do prototipo-ordax-os permanecem.

A área principal se divide entre conversa à esquerda e prévia à direita, com divisor ajustável. O cabeçalho da conversa mantém “ChatGPT · Pessoal” visível para identificar a conta destinatária.

| Elemento | Comportamento pretendido |
| --- | --- |
| Grupo ChatGPT / Grok | Organiza as contas por serviço e mostra a quantidade cadastrada |
| Conta Pessoal selecionada | Define qual sessão e histórico estão visíveis |
| Conta Trabalho respondendo | Indica atividade observada em outra sessão |
| Conta Pesquisa pronta | Indica uma sessão disponível, sem geração em curso |
| Ver conversa | Leva à sessão que está respondendo sem encerrar a atual |
| Conectar conta | Permite escolher serviço, nomear a conta e iniciar seu login |
| Gerenciar | Centraliza renomear, ordenar e administrar conexões |
| Conversas recentes | Mostra apenas o histórico da conta selecionada |
| Anexar ao chat | Compartilha contexto com a conversa selecionada mediante ação do usuário |
| Chat + prévia | Oferece modos de foco e disposição da área de trabalho |

## Regras de UX para múltiplas contas

1. **Foco e atividade são estados distintos.** Selecionar uma conta muda a apresentação, sem encerrar outras sessões ou significar que todas estão gerando.
2. **Identidade antes da ação.** Serviço e apelido da conta ficam visíveis junto à conversa para evitar envio à sessão errada.
3. **Históricos separados.** A troca de conta restaura sua conversa e rascunho próprios. Não mistura mensagens, anexos ou contexto automaticamente.
4. **Estados baseados em evidência.** “Respondendo” deve refletir atividade observada; login expirado, conexão indisponível e sessão pronta precisam de estados próprios.
5. **Notificações discretas.** Uma resposta de outra sessão gera um aviso acessível, sem trocar o foco ou interromper o texto em edição.
6. **Escala sem uma faixa infinita de abas.** Com muitas contas, a lateral deve oferecer busca, favoritos e grupos recolhíveis. O conceito demonstra três contas, sem estabelecer limite.
7. **Nomes reconhecíveis.** O usuário pode nomear suas contas por finalidade, como Pessoal, Trabalho ou Pesquisa. O provedor continua explícito no grupo.
8. **Identidade do sistema preservada.** A conta do OS em “Espaço pessoal” é distinta das sessões dos sites.

## Acabamento premium

- Uma única estrutura de navegação para as sessões.
- Controles técnicos de navegador fora do fluxo principal.
- Menos cabeçalhos, menus sobrepostos e indicadores repetidos.
- Tipografia e alinhamento consistentes com o sistema visual grafite/glacial do prototipo-ordax-os.
- Cena ampla à direita e campo de mensagem acessível à esquerda.
- Compartilhamento de contexto perto da prévia e identificação do destinatário junto ao chat.

## Limite de implementação

O app administra o contêiner, a disposição e os perfis; cada provedor mantém sua própria página e autenticação. Remover a barra de endereço da apresentação principal não significa substituir o site por uma API ou prometer controle uniforme do conteúdo de todos os provedores.

A implementação deve validar login, isolamento de sessão, persistência de rascunhos e continuidade das páginas em segundo plano no host escolhido. Não deve inferir uma capacidade pronta a partir do mockup.

## Entregáveis

- Imagem: `ordax-studio-concept-v3.png`.
- Prompt completo: `ordax-studio-concept-v3.prompt.txt`.
- Referência de edição: `ordax-studio-concept-v2.png`.
- Método: ferramenta integrada de edição de imagens.
- Verificação visual: chat à esquerda; prévia à direita; três contas visíveis agrupadas por serviço; identificação da conta ativa; aviso de atividade em segundo plano; ausência de abas/endereços de navegador; identidade e estrutura do OS preservadas.

Esta entrega contém o conceito e sua análise. A interface executável não foi alterada.
