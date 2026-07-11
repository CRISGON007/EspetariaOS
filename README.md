# EspetariaOS Python v0.4.9

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

unzip EspetariaOS_Python_v0.4.9.zip
cd EspetariaOS_Python_v0.4.9

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


## Correções da v0.4.9

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


## Padronização pt-BR da v0.4.9

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


## Correção da v0.4.9

- Corrigida a tradução do status na tela pública de rastreamento.
- Adicionado versionamento às URLs dos arquivos CSS e JavaScript para impedir que o navegador reutilize arquivos antigos em cache.
- Após atualizar, reinicie o servidor e recarregue a página com `Ctrl+Shift+R`.


## Fluxo simplificado da v0.4.9

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
./finalizar_versao.sh v0.4.9
```

O script pedirá confirmações antes de criar o commit, enviar a branch, fazer o merge na `main` e criar a tag.


## Alterações funcionais da v0.4.9

### Rastreamento

O cliente pode consultar usando:

- somente o telefone;
- somente o código do pedido;
- telefone e código juntos.

Quando somente o telefone é informado, o sistema lista até os 20 pedidos mais recentes vinculados ao número.

### Entrega sem pagamento

Quando um pedido está **Pronto** e o pagamento ainda está **Pendente**, o atendente recebe um aviso antes de marcá-lo como **Entregue**.

A entrega só prossegue após confirmação explícita. A ação fica registrada na auditoria.


## Entrega condicionada ao caixa — v0.4.9

Ao marcar um pedido como **Entregue**, o sistema verifica primeiro se existe um caixa aberto.

Caso não exista:

1. O atendente recebe um aviso.
2. Pode escolher abrir o caixa naquele momento.
3. Informa o valor inicial.
4. O sistema abre o caixa e continua o fluxo de entrega.

Se o atendente cancelar, o pedido permanece como **Pronto**.

Depois da verificação do caixa, o sistema ainda verifica se o pagamento foi confirmado. Se estiver pendente, exibe o segundo aviso antes da entrega.


## Correção do painel administrativo — v0.4.9

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


## Fluxo do cliente — v0.4.9

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


## Correção crítica do painel administrativo — v0.4.9

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

A v0.4.9 corrige o identificador e adiciona proteções para que um componente
opcional ausente não interrompa todo o painel.
