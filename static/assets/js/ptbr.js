const PT_BR = Object.freeze({
  orderStatus: {
    RECEIVED: 'Recebido',
    PREPARING: 'Em preparo',
    READY: 'Pronto',
    DELIVERED: 'Entregue',
    CANCELLED: 'Cancelado'
  },
  paymentStatus: {
    PENDING: 'Pendente',
    PAID: 'Pago',
    CANCELLED: 'Cancelado',
    REFUNDED: 'Estornado'
  },
  paymentMethod: {
    PIX: 'PIX',
    CASH: 'Dinheiro',
    CARD: 'Cartão'
  },
  serviceStatus: {
    ONLINE: 'Online',
    OFFLINE: 'Offline',
    MANUAL: 'Manual',
    NOT_CONFIGURED: 'Não configurado'
  },
  auditAction: {
    LOGIN_SUCCESS: 'Login realizado',
    LOGIN_FAILED: 'Tentativa de login inválida',
    ORDER_CREATED: 'Pedido criado',
    ORDER_STATUS_CHANGED: 'Status do pedido alterado',
    PAYMENT_CONFIRMED: 'Pagamento confirmado',
    CASH_OPENED: 'Caixa aberto',
    CASH_CLOSED: 'Caixa fechado',
    PRODUCT_CREATED: 'Produto cadastrado',
    PRODUCT_UPDATED: 'Produto atualizado',
    PRODUCT_DELETED_OR_DISABLED: 'Produto excluído ou desativado',
    BACKUP_CREATED: 'Backup criado',
    DEMO_ORDER_CREATED: 'Pedido de demonstração criado',
    UNPAID_ORDER_DELIVERED: 'Pedido entregue sem pagamento confirmado',
    CASH_REQUIRED_FOR_DELIVERY: 'Entrega bloqueada por caixa fechado'
  }
});

function orderStatusLabel(value){
  return PT_BR.orderStatus[value] || value || '';
}

function paymentStatusLabel(value){
  return PT_BR.paymentStatus[value] || value || '';
}

function paymentMethodLabel(value){
  return PT_BR.paymentMethod[value] || value || '';
}

function serviceStatusLabel(value){
  return PT_BR.serviceStatus[value] || value || '';
}

function auditActionLabel(value){
  return PT_BR.auditAction[value] || value || '';
}
