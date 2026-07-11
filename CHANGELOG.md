# Changelog

## v0.4.9

### Corrigido
- Corrigido o identificador interno do botão de atualização do painel administrativo.
- O JavaScript procurava `refreshDashboard`, mas o HTML continha `refreshPainel`.
- Esse erro interrompia o `admin.js` antes da carga inicial, do WebSocket e do polling.
- Adicionadas verificações defensivas em elementos da tela.
- Adicionada mensagem visível quando a carga inicial do painel falhar.

### Resultado
- Produtos cadastrados e disponíveis são carregados ao abrir o painel.
- Pedidos e pagamentos atualizam os indicadores.
- Atualização por WebSocket e a cada 10 segundos permanecem ativas.
