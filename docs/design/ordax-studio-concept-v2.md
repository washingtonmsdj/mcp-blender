# ORDAX Studio — conceito v2: navegador e múltiplas contas

Atualizado em 3 de outubro de 2026 a partir da concept v1 e da orientação do usuário.

A imagem é uma proposta visual. Os sites, conversas, perfis e estados exibidos são ilustrativos; a imagem não comprova login, integração ou execução simultânea.

## Mudança principal

O navegador interno ocupa a área principal à direita, junto à prévia e aos arquivos do projeto. O usuário interage com o site do ChatGPT dentro dessa área. A estrutura visual do prototipo-ordax-os permanece: barra lateral do sistema, título do Studio, grafite/azul glacial, Inter e barra de status inferior.

## Recursos representados

- Abas abertas simultaneamente: ChatGPT · Pessoal, ChatGPT · Trabalho e Grok · Pessoal.
- Barra de endereço, voltar, avançar, atualizar e nova aba.
- Seleção de perfil por aba.
- Menu “Contas abertas”, indicando “Nesta aba” e “Em outra aba”.
- Ações “Adicionar conta” e “Gerenciar perfis”.
- Controle “Dividir” para uma futura apresentação lado a lado de páginas.
- Prévia do projeto visível junto ao chat, com divisor ajustável.
- Campo de mensagem amplo dentro da página do ChatGPT.
- Ação explícita de compartilhamento de contexto do projeto.

## Requisitos para a futura implementação

As contas dos sites pertencem a perfis de navegação distintos da identidade do OS. Cada perfil precisa conservar cookies, armazenamento e sessão próprios. Abas do mesmo perfil podem compartilhar sua sessão; perfis diferentes do mesmo domínio devem permanecer isolados.

Alternar a aba ou o perfil visível deve preservar as outras sessões abertas. Manter sessões concorrentes não significa iniciar pedidos, enviar mensagens ou consumir serviços automaticamente.

O chat representado é uma página do provedor dentro do navegador. A implementação precisa validar o login e o funcionamento de cada site no host escolhido. Compartilhar arquivos ou contexto é uma ação do usuário e não implica leitura automática de todas as conversas ou controle irrestrito da página.

## Entregáveis e validação

- Imagem: `ordax-studio-concept-v2.png`.
- Prompt: `ordax-studio-concept-v2.prompt.txt`.
- Referência visual: `ordax-studio-concept-v1.png`.
- Método: edição pela ferramenta integrada de geração de imagens.
- Inspeção visual: três abas legíveis; duas contas de ChatGPT; Grok; troca de conta; barra de endereço; campo de mensagem visível; prévia junto ao navegador; identidade do OS preservada.

A interface executável do aplicativo não foi modificada nesta entrega.
