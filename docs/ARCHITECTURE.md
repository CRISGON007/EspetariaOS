# Arquitetura v0.4.0

```text
Navegadores
   | HTTP/JSON
   | WebSocket
   v
FastAPI + Uvicorn
   |
SQLite
```

## Tempo real

A rota `/ws` transmite:

- `ORDER_CREATED`
- `ORDER_STATUS_CHANGED`
- `PAYMENT_CONFIRMED`

Os navegadores reconectam automaticamente em caso de queda.

## Aplicativo instalado

Não há PWA, service worker, manifest ou aplicativo para instalação nos aparelhos dos clientes. O uso permanece exclusivamente pelo navegador.
