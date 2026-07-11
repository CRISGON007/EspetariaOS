# EspetariaOS Python v0.4.3

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

unzip EspetariaOS_Python_v0.4.3.zip
cd EspetariaOS_Python_v0.4.3

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


## Correções da v0.4.3

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


## Padronização pt-BR da v0.4.3

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


## Correção da v0.4.3

- Corrigida a tradução do status na tela pública de rastreamento.
- Adicionado versionamento às URLs dos arquivos CSS e JavaScript para impedir que o navegador reutilize arquivos antigos em cache.
- Após atualizar, reinicie o servidor e recarregue a página com `Ctrl+Shift+R`.
