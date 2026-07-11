# Checklist de testes — EspetariaOS v0.5.5

Use um banco separado durante a validação:

```bash
./install.sh
./dev.sh
```

## Cliente

- [ ] Catálogo abre em `/`.
- [ ] Busca e filtro de categorias funcionam.
- [ ] Produto é adicionado e removido do carrinho.
- [ ] Cadastro com nome e telefone funciona.
- [ ] Pedido é criado.
- [ ] Rastreamento funciona somente com telefone.
- [ ] Rastreamento funciona somente com código.
- [ ] Rastreamento funciona com telefone e código preenchidos.
- [ ] Status aparece em português.
- [ ] Atualização por WebSocket aparece sem recarregar a página.
- [ ] A página pública não exibe link de acesso interno.

## Login e segurança

- [ ] `/login` não exibe credenciais iniciais.
- [ ] Login de administrador funciona.
- [ ] Login de atendente funciona.
- [ ] Usuário e senha inválidos são rejeitados.

## Atendimento

- [ ] Novo pedido aparece imediatamente.
- [ ] Status avança: Recebido → Em preparo → Pronto → Entregue.
- [ ] Ao entregar com o caixa fechado, o sistema exibe um aviso.
- [ ] O aviso permite abrir o caixa informando o valor inicial.
- [ ] Ao cancelar a abertura do caixa, o pedido permanece como Pronto.
- [ ] Ao entregar sem pagamento confirmado, o sistema exibe um aviso.
- [ ] É possível cancelar o aviso e manter o pedido como Pronto.
- [ ] É possível confirmar conscientemente a entrega sem pagamento.
- [ ] Pagamento pode ser confirmado.
- [ ] Abertura e fechamento do caixa funcionam.

## Administração e sistema

- [ ] CRUD de produtos funciona.
- [ ] Dashboard abre.
- [ ] `/sistema` exibe CPU, memória e disco.
- [ ] Backup pode ser criado e baixado.
- [ ] `/docs` retorna 404 em produção.

## Finalização no GitHub

Após aprovar todos os testes:

```bash
./finalizar_versao.sh v0.5.5
```

O script executa os testes automatizados, cria a branch de release, registra o commit,
envia ao GitHub e, mediante confirmação, integra na `main` e cria a tag.


## Atualização do painel administrativo

- [ ] Novo pedido aparece no painel administrativo sem recarregar a página.
- [ ] Alteração de status aparece no painel administrativo.
- [ ] Confirmação de pagamento atualiza o faturamento registrado.
- [ ] O painel se atualiza em até 10 segundos mesmo após falha do WebSocket.
- [ ] O console do navegador não exibe `connectRealtime is not defined`.


## Fluxo após finalizar o pedido

- [ ] Após criar o pedido, o botão muda para **Consultar pedido**.
- [ ] Ao clicar, o carrinho fecha e a tela de consulta abre.
- [ ] A consulta é executada automaticamente com o pedido recém-criado.
- [ ] Com a tela de consulta aberta, mudança de status atualiza o resultado automaticamente.
- [ ] Com a tela de consulta aberta, confirmação de pagamento atualiza o resultado automaticamente.
- [ ] Ao adicionar um novo produto, o botão volta para **Finalizar pedido**.

## Instalação

- [ ] `./install.sh` instala `uvicorn[standard]`.
- [ ] O terminal não mostra `No supported WebSocket library detected`.
- [ ] A conexão `/ws` é aceita.


## Correção do painel administrativo

- [ ] Ao abrir `/admin`, os totais de produtos são carregados imediatamente.
- [ ] O botão **Atualizar** funciona sem erro.
- [ ] Novo pedido atualiza pedidos ativos e a lista de pedidos.
- [ ] Pagamento confirmado atualiza o faturamento.
- [ ] Cadastro, edição e disponibilidade de produto atualizam os indicadores.
- [ ] A atualização periódica ocorre a cada 10 segundos.
- [ ] O console não mostra `Cannot read properties of null`.

## Caixa e vendas
- [ ] Sangria e suprimento funcionam.
- [ ] Indicadores diários atualizam.
- [ ] Consulta de vendas e CSV funcionam.


## Correções de ambiente da v0.5.5

- [ ] `./install.sh` termina sem exigir `wsproto`.
- [ ] `websockets` é validado corretamente.
- [ ] `./testar.sh` encontra o pacote `app`.
- [ ] O teste do banco é concluído.
- [ ] A aplicação FastAPI é importada.
- [ ] Após login novo, o painel administrativo abre sem respostas 401.


## Validação do carrinho

- [ ] Nome vazio exibe mensagem específica.
- [ ] Nome muito curto exibe mensagem específica.
- [ ] Telefone vazio exibe mensagem específica.
- [ ] Telefone inválido exibe mensagem específica.
- [ ] Forma de pagamento não selecionada exibe mensagem específica.
- [ ] Campos inválidos ficam destacados.
- [ ] O foco vai para o primeiro campo inválido.
- [ ] A mensagem desaparece após corrigir o campo.
- [ ] Observação continua opcional.


## Máscara e validação do telefone

- [ ] Celular com 11 dígitos fica no formato `(11)98765-4321`.
- [ ] Telefone fixo com 10 dígitos fica no formato `(11)3234-5678`.
- [ ] Letras e símbolos digitados são ignorados.
- [ ] A entrada é limitada a 11 dígitos.
- [ ] DDD inexistente é rejeitado.
- [ ] Número com todos os dígitos iguais é rejeitado.
- [ ] Telefone salvo é exibido formatado ao reabrir o carrinho.
- [ ] Campo de rastreamento também aplica a máscara.
- [ ] A busca funciona com telefone formatado.

## Tempo por status nas consultas de vendas
- [ ] Cada resultado exibe **Tempo em cada status**.
- [ ] Os tempos de Recebido, Em preparo, Pronto e Entregue aparecem quando aplicáveis.
- [ ] O status atual continua contando.
- [ ] Pedidos antigos abrem sem erro.


## Tempo total e indicadores

- [ ] Pedido entregue exibe `Total:` ao lado do status Entregue.
- [ ] A soma corresponde aos tempos de todos os status.
- [ ] Pedido não entregue exibe `Tempo decorrido`.
- [ ] Até 15 minutos aparece em verde.
- [ ] Entre 15 e 25 minutos aparece em amarelo.
- [ ] Acima de 25 minutos aparece em vermelho.
- [ ] Painel mostra tempo médio de preparo.
- [ ] Painel mostra tempo médio total.
- [ ] Painel mostra pedido mais rápido.
- [ ] Painel mostra pedido mais demorado.
