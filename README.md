# EspetariaOS Python v1.0.1

Versão com atualização em tempo real e central de notificações, sem PWA e sem instalação nos aparelhos dos clientes.

## Rotas

- Cliente: `http://IP_DA_TV_BOX:8080/`
- Login: `http://IP_DA_TV_BOX:8080/login`
- Atendente: `http://IP_DA_TV_BOX:8080/atendimento`
- Administrador: `http://IP_DA_TV_BOX:8080/admin`
- Sistema: `http://IP_DA_TV_BOX:8080/sistema`
- Sobre: `http://IP_DA_TV_BOX:8080/sobre`

## Novidades

- WebSocket em `/ws`.
- Pedidos aparecem imediatamente no atendimento e administração.
- Cliente recebe atualização de status e confirmação de pagamento em tempo real.
- Notificações visuais no navegador.
- Reconexão automática do WebSocket.
- Modo demonstração opcional.
- Geração de pedido de teste pelo administrador.
- Sem manifest, service worker ou instalação PWA.
- Mantidos backups, auditoria, painel de sistema e documentação desabilitada em produção.

## Instalação

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip unzip

unzip EspetariaOS_Python_v0.5.3.zip
cd EspetariaOS_Python_v0.5.3

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ESPETARIA_ENV=production python run.py
```

## Modo demonstração

O modo demonstração fica desligado por padrão.

```bash
ESPETARIA_ENV=development ESPETARIA_DEMO=true python run.py
```

Ao entrar como administrador, aparece o botão **Gerar pedido demo**.

## Credenciais iniciais

- Administrador: `admin` / `admin123`
- Atendente: `atendente` / `atendente123`

## Produção

Em produção, mantenha:

```bash
ESPETARIA_ENV=production
ESPETARIA_DEMO=false
```

A documentação `/docs`, `/redoc` e `/openapi.json` fica desativada.


## Correções da v0.5.3

- Removido o botão **Acesso interno** da página pública do cliente.
- Removida a exibição das credenciais iniciais da tela de login.
- `app/main.py` agora pode ser executado diretamente pelo VS Code.
- Adicionadas configurações prontas em `.vscode/launch.json`.

## Executar pelo terminal

Forma recomendada:

```bash
ESPETARIA_ENV=production ESPETARIA_DEMO=false python run.py
```

Também é possível executar diretamente:

```bash
ESPETARIA_ENV=production ESPETARIA_DEMO=false python app/main.py
```

## Executar pelo VS Code

Abra **Executar e Depurar** e escolha:

- `EspetariaOS - Produção`
- `EspetariaOS - Desenvolvimento`

O VS Code usará o interpretador:

```text
.venv/bin/python
```

Observação: `0.0.0.0` é o endereço de escuta do servidor. No navegador da própria TV Box ou computador, use `http://localhost:8080/`. Em outro dispositivo da rede, use o IP real da TV Box, por exemplo `http://192.168.15.20:8080/`.


## Padronização pt-BR da v0.5.3

Os valores técnicos continuam armazenados em inglês no banco e na API para preservar estabilidade, mas a interface passa a exibir rótulos em português.

### Status de pedido

- `RECEIVED` → Recebido
- `PREPARING` → Em preparo
- `READY` → Pronto
- `DELIVERED` → Entregue
- `CANCELLED` → Cancelado

### Pagamentos

- `PENDING` → Pendente
- `PAID` → Pago
- `REFUNDED` → Estornado
- `PIX` → PIX
- `CASH` → Dinheiro
- `CARD` → Cartão

### Serviços e auditoria

Também foram traduzidos os estados dos serviços, perfis de usuário e ações exibidas no painel de auditoria.

Os rótulos foram centralizados em:

```text
static/assets/js/ptbr.js
```


## Correção da v0.5.3

- Corrigida a tradução do status na tela pública de rastreamento.
- Adicionado versionamento às URLs dos arquivos CSS e JavaScript para impedir que o navegador reutilize arquivos antigos em cache.
- Após atualizar, reinicie o servidor e recarregue a página com `Ctrl+Shift+R`.


## Fluxo simplificado da v0.5.3

Primeira preparação:

```bash
chmod +x install.sh start.sh dev.sh testar.sh finalizar_versao.sh
./install.sh
```

Testar:

```bash
./testar.sh
./dev.sh
```

Depois de concluir os testes manuais:

```bash
./finalizar_versao.sh v0.5.3
```

O script pedirá confirmações antes de criar o commit, enviar a branch, fazer o merge na `main` e criar a tag.


## Alterações funcionais da v0.5.3

### Rastreamento

O cliente pode consultar usando:

- somente o telefone;
- somente o código do pedido;
- telefone e código juntos.

Quando somente o telefone é informado, o sistema lista até os 20 pedidos mais recentes vinculados ao número.

### Entrega sem pagamento

Quando um pedido está **Pronto** e o pagamento ainda está **Pendente**, o atendente recebe um aviso antes de marcá-lo como **Entregue**.

A entrega só prossegue após confirmação explícita. A ação fica registrada na auditoria.


## Entrega condicionada ao caixa — v0.5.3

Ao marcar um pedido como **Entregue**, o sistema verifica primeiro se existe um caixa aberto.

Caso não exista:

1. O atendente recebe um aviso.
2. Pode escolher abrir o caixa naquele momento.
3. Informa o valor inicial.
4. O sistema abre o caixa e continua o fluxo de entrega.

Se o atendente cancelar, o pedido permanece como **Pronto**.

Depois da verificação do caixa, o sistema ainda verifica se o pagamento foi confirmado. Se estiver pendente, exibe o segundo aviso antes da entrega.


## Correção do painel administrativo — v0.5.3

O painel administrativo passa a atualizar automaticamente quando ocorre:

- criação de pedido;
- mudança de status;
- confirmação de pagamento.

A correção reorganiza a ordem de carregamento dos scripts para que
`realtime.js` seja carregado antes de `admin.js`.

Também foi adicionado um mecanismo de segurança que atualiza o painel a cada
10 segundos, mesmo que o WebSocket seja interrompido temporariamente.

Após atualizar a versão, reinicie o servidor e recarregue o navegador com:

```text
Ctrl + Shift + R
```


## Fluxo do cliente — v0.5.3

Depois que o pedido é criado:

1. O botão **Finalizar pedido** muda para **Consultar pedido**.
2. Ao clicar, o carrinho é fechado.
3. A tela de rastreamento é aberta.
4. O telefone e o código são preenchidos automaticamente.
5. O resultado da consulta é carregado automaticamente.

Enquanto a tela de rastreamento permanecer aberta, alterações de status e
confirmações de pagamento recebidas por WebSocket atualizam o pedido sem que o
cliente precise clicar novamente.

Ao adicionar um novo produto ao carrinho, o botão retorna ao modo
**Finalizar pedido**.

## WebSocket

O projeto agora utiliza:

```text
uvicorn[standard]==0.50.2
```

O script `install.sh` valida `websockets` e `wsproto` depois da instalação.


## Correção crítica do painel administrativo — v0.5.3

O painel não atualizava porque o botão visível **Atualizar** tinha o identificador
interno `refreshPainel`, enquanto o JavaScript procurava `refreshDashboard`.

Isso gerava um erro semelhante a:

```text
Cannot read properties of null (reading 'addEventListener')
```

A execução do `admin.js` era interrompida antes de:

- carregar os produtos;
- carregar os pedidos;
- conectar o WebSocket;
- iniciar a atualização periódica.

A v0.5.3 corrige o identificador e adiciona proteções para que um componente
opcional ausente não interrompa todo o painel.


## v0.5.3
Caixa ampliado, indicadores administrativos, consulta de vendas e exportação CSV.


## Correções da v0.5.3

O Uvicorn precisa de pelo menos um backend de WebSocket. O projeto utiliza
`websockets`, instalado por `uvicorn[standard]`. O pacote `wsproto` é uma
alternativa e não precisa estar instalado simultaneamente.

O `testar.sh` agora define automaticamente a raiz do projeto no `PYTHONPATH`,
evitando `ModuleNotFoundError: No module named 'app'`.

Depois de atualizar:

```bash
./install.sh
./testar.sh
./dev.sh
```

Se o navegador mostrar respostas `401 Unauthorized`, apague a sessão antiga:

```javascript
localStorage.clear()
```

ou simplesmente use o botão **Sair** e faça login novamente.


## Validação do carrinho — v0.5.3

Antes de criar o pedido, o sistema valida individualmente:

- nome completo;
- telefone com DDD;
- forma de pagamento.

Cada campo incompleto ou inválido recebe uma mensagem própria e destaque visual.
O cursor é direcionado automaticamente ao primeiro campo que precisa ser
corrigido. O campo de observação permanece opcional.


## Telefone brasileiro — v0.5.3

Os campos de telefone agora aplicam máscara automaticamente:

```text
Celular: (11)98765-4321
Fixo:    (11)3234-5678
```

A interface aceita apenas os primeiros 11 dígitos, ignora caracteres não
numéricos e valida o DDD. No banco de dados, o telefone continua armazenado
sem formatação, por exemplo `11987654321`.


## Indicadores de tempo — v0.7.2

Em **Consultas > Vendas**, o status **Entregue** mostra também o tempo total do
pedido, calculado pela soma de todas as etapas.

Classificação visual:

- até 15 minutos: verde;
- de 15 a 25 minutos: amarelo;
- acima de 25 minutos: vermelho.

O painel administrativo também mostra tempo médio de preparo, tempo médio
total, pedido mais rápido e pedido mais demorado.

## Gestão administrativa — v0.7.2
Consulta de clientes, auditoria filtrável e backup automático diário.

## Backup automático e retenção — v0.7.2
Na inicialização, o sistema cria o backup do dia quando necessário e mantém apenas os 30 mais recentes.

```bash
ESPETARIA_BACKUP_RETENTION=30
```

## Estoque — v0.7.2
Controle opcional, baixa automática, devolução no cancelamento e histórico de movimentações.

## Cadastro de estoque — v0.7.2
Ao ativar **Controlar estoque deste produto**, o administrador informa a
quantidade disponível para venda e a quantidade mínima. Ao atingir o mínimo,
o painel sinaliza estoque baixo; ao zerar, o item fica indisponível.


## Estabilização — v0.7.2

Esta versão corrige o teste de retenção de backups sem remover os testes de
produtos, estoque, telefone, pedidos, clientes, status e rastreamento.

Execute:

```bash
./install.sh && ./testar.sh && ./dev.sh
```

O servidor somente será iniciado quando todos os testes anteriores forem
concluídos com sucesso.

## Financeiro — v0.8.0
O painel administrativo possui cadastro de despesas e resumo de receita,
despesas e saldo.

Publicação no GitHub:
```bash
./publicar_git.sh v0.8.0
```


## Correção da v0.8.1

A exclusão de despesas agora retorna HTTP 200 com:

```json
{"ok": true}
```

Isso corrige o erro de inicialização:

```text
AssertionError: Status code 204 must not have a response body
```


## Relatórios gerenciais — v0.9.0

A área **Relatórios** consolida indicadores de vendas, operação e financeiro
por período. O relatório pode ser exportado para CSV.

Publicação no GitHub:

```bash
./publicar_git.sh v0.9.0
```


## Correções operacionais — v0.9.1

O relógio do pedido é interrompido quando o status chega a **Entregue** ou
**Cancelado**. A auditoria também passa a listar automaticamente todas as ações
disponíveis no sistema.

Publicação:

```bash
./publicar_git.sh v0.9.1
```


## Pagamento e caixa — v0.9.2

Ao clicar em **Confirmar pagamento** com o caixa fechado, o sistema pergunta se
o atendente deseja abrir o caixa. O pagamento somente pode ser confirmado
depois que a abertura for concluída.

Publicação:

```bash
./publicar_git.sh v0.9.2
```

## Versão estável v1.0.0
```bash
./diagnostico.sh
sudo ./instalar_servico.sh
./atualizar_producao.sh
./publicar_git.sh v1.0.0
```
Consulte `GUIA_PRODUCAO_v1.0.0.md`.


## Ajustes de navegação — v1.0.1

No Painel Administrativo, a navegação superior passa a mostrar:

```text
Painel de pedidos | Sistema | Sobre | Sair
```

No Painel de Pedidos, o botão **Administração** é disponibilizado exclusivamente
para usuários com perfil Administrador.
