if(user.role==='ADMIN') document.getElementById('adminLink').classList.remove('hidden');

const labels = PT_BR.orderStatus;

let ordersCache = [];

function updateClock(){
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
}

function elapsed(createdAt){
  const diff = Math.max(0, Date.now() - new Date(createdAt).getTime());
  const totalMinutes = Math.floor(diff / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours}h ${minutes}min` : `${minutes} min`;
}

function card(order){
  const actions = [];
  if(order.status === 'RECEIVED'){
    actions.push(`<button class="kds-action received-action" onclick="setStatus(${order.id},'PREPARING')">Iniciar preparo</button>`);
  }
  if(order.status === 'PREPARING'){
    actions.push(`<button class="kds-action preparing-action" onclick="setStatus(${order.id},'READY')">Marcar pronto</button>`);
  }
  if(order.status === 'READY'){
    actions.push(`<button class="kds-action ready-action" onclick="setStatus(${order.id},'DELIVERED')">Entregar pedido</button>`);
  }
  if(order.paymentStatus !== 'PAID' && !['CANCELLED','DELIVERED'].includes(order.status)){
    actions.push(`<button class="kds-action payment-action" onclick="pay(${order.id},'${order.paymentMethod}')">Confirmar pagamento</button>`);
  }
  if(!['DELIVERED','CANCELLED'].includes(order.status)){
    actions.push(`<button class="kds-action cancel-action" onclick="setStatus(${order.id},'CANCELLED')">Cancelar</button>`);
  }

  return `
    <article class="kds-order-card ${order.status.toLowerCase()}">
      <div class="kds-card-header">
        <div>
          <small>Pedido</small>
          <h3>${order.code}</h3>
        </div>
        <span class="elapsed">${elapsed(order.createdAt)}</span>
      </div>

      <div class="customer-block">
        <strong>${order.customer.name}</strong>
        <small>${order.customer.phone}</small>
      </div>

      <ul class="kds-items">
        ${order.items.map(item => `<li><b>${item.quantity}x</b> ${item.name}</li>`).join('')}
      </ul>

      ${order.notes ? `<div class="order-note"><b>Observação:</b> ${order.notes}</div>` : ''}

      <div class="kds-card-footer">
        <div>
          <small>Total</small>
          <strong>${money(order.totalCents)}</strong>
        </div>
        <div>
          <small>Pagamento</small>
          <strong>${paymentStatusLabel(order.paymentStatus)} · ${paymentMethodLabel(order.paymentMethod)}</strong>
        </div>
      </div>

      <div class="kds-card-actions">${actions.join('')}</div>
    </article>
  `;
}

function renderColumn(id, items){
  const container = document.getElementById(id);
  container.innerHTML = items.length
    ? items.map(card).join('')
    : '<div class="column-empty">Nenhum pedido nesta etapa.</div>';
}

async function loadOrders(){
  try{
    const data = await api('/api/staff/orders');
    ordersCache = data.items;

    const received = data.items.filter(o => o.status === 'RECEIVED');
    const preparing = data.items.filter(o => o.status === 'PREPARING');
    const ready = data.items.filter(o => o.status === 'READY');
    const history = data.items.filter(o => ['DELIVERED','CANCELLED'].includes(o.status)).slice(0,12);

    document.getElementById('receivedCount').textContent = received.length;
    document.getElementById('preparingCount').textContent = preparing.length;
    document.getElementById('readyCount').textContent = ready.length;

    document.getElementById('receivedBadge').textContent = received.length;
    document.getElementById('preparingBadge').textContent = preparing.length;
    document.getElementById('readyBadge').textContent = ready.length;
    document.getElementById('historyBadge').textContent = history.length;

    renderColumn('receivedOrders', received);
    renderColumn('preparingOrders', preparing);
    renderColumn('readyOrders', ready);
    renderColumn('historyOrders', history);
  }catch(e){
    ['receivedOrders','preparingOrders','readyOrders','historyOrders'].forEach(id=>{
      document.getElementById(id).innerHTML = `<p class="message">${e.message}</p>`;
    });
  }
}

async function ensureCashOpenForDelivery(){
  const data=await api('/api/staff/cash/current');

  if(data.cash) return true;

  const wantsToOpen=confirm(
    'ATENÇÃO: o caixa ainda não foi aberto.\n\n' +
    'Deseja abrir o caixa agora antes de entregar o pedido?'
  );

  if(!wantsToOpen) return false;

  const value=prompt('Informe o valor inicial do caixa (R$):','0,00');
  if(value===null) return false;

  await api('/api/staff/cash/open',{
    method:'POST',
    body:JSON.stringify({valueCents:toCents(value)})
  });

  notify(
    'Caixa aberto',
    'O caixa foi aberto com sucesso. A entrega pode continuar.',
    'success'
  );

  await loadCash();
  return true;
}

async function setStatus(id,status){
  try{
    const order=ordersCache.find(item=>item.id===id);
    let confirmUnpaidDelivery=false;

    if(status==='DELIVERED'){
      const cashReady=await ensureCashOpenForDelivery();
      if(!cashReady) return;
    }

    if(
      status==='DELIVERED' &&
      order &&
      order.paymentStatus!=='PAID'
    ){
      confirmUnpaidDelivery=confirm(
        'ATENÇÃO: o pagamento deste pedido ainda não foi confirmado.\n\n' +
        'Deseja marcar o pedido como entregue mesmo assim?'
      );

      if(!confirmUnpaidDelivery) return;
    }

    await api(`/api/staff/orders/${id}/status`,{
      method:'PUT',
      body:JSON.stringify({status,confirmUnpaidDelivery})
    });

    if(status==='DELIVERED' && confirmUnpaidDelivery){
      notify(
        'Entrega registrada',
        'O pedido foi entregue sem confirmação de pagamento.',
        'warning'
      );
    }

    await Promise.all([loadOrders(),loadCash()]);
  }catch(e){
    alert(e.message);
  }
}

async function pay(id,defaultMethod){
  const method = prompt('Forma de pagamento: PIX, CASH ou CARD', defaultMethod || 'PIX');
  if(!method) return;
  try{
    await api(`/api/staff/orders/${id}/payment`,{
      method:'POST',
      body:JSON.stringify({method:method.toUpperCase()})
    });
    await Promise.all([loadOrders(),loadCash()]);
  }catch(e){
    alert(e.message);
  }
}

async function loadCash(){
  const data = await api('/api/staff/cash/current');
  const panel = document.getElementById('cashPanel');

  if(!data.cash){
    document.getElementById('cashStatus').textContent = 'Fechado';
    panel.innerHTML = `
      <div class="cash-content">
        <p>Nenhum caixa aberto.</p>
        <button class="primary" onclick="openCash()">Abrir caixa</button>
      </div>`;
    return;
  }

  document.getElementById('cashStatus').textContent = 'Aberto';
  const totals = data.cash.totals || {};
  panel.innerHTML = `
    <div class="cash-content cash-open">
      <div><small>Responsável</small><strong>${data.cash.openedBy}</strong></div>
      <div><small>Fundo inicial</small><strong>${money(data.cash.openingCents)}</strong></div>
      <div><small>PIX</small><strong>${money(totals.PIX || 0)}</strong></div>
      <div><small>Dinheiro</small><strong>${money(totals.CASH || 0)}</strong></div>
      <div><small>Cartão</small><strong>${money(totals.CARD || 0)}</strong></div>
      <button class="danger" onclick="closeCash()">Fechar caixa</button>
    </div>`;
}

function toCents(value){
  return Math.round(Number(String(value).replace(/\./g,'').replace(',','.')) * 100) || 0;
}

async function openCash(){
  const value = prompt('Valor inicial do caixa (R$)','0,00');
  if(value === null) return;
  try{
    await api('/api/staff/cash/open',{
      method:'POST',
      body:JSON.stringify({valueCents:toCents(value)})
    });
    await loadCash();
  }catch(e){
    alert(e.message);
  }
}

async function closeCash(){
  const value = prompt('Valor contado no fechamento (R$)','0,00');
  if(value === null || !confirm('Confirma o fechamento do caixa?')) return;
  try{
    await api('/api/staff/cash/close',{
      method:'POST',
      body:JSON.stringify({valueCents:toCents(value)})
    });
    await loadCash();
  }catch(e){
    alert(e.message);
  }
}

document.getElementById('refresh').addEventListener('click',()=>Promise.all([loadOrders(),loadCash()]));
document.getElementById('toggleCash').addEventListener('click',()=>{
  document.getElementById('cashPanel').classList.toggle('hidden');
});

updateClock();
setInterval(updateClock,1000);
Promise.all([loadOrders(),loadCash()]);
setInterval(loadOrders,10000);

connectRealtime((event,payload)=>{
  if(event==='ORDER_CREATED'){
    notify('Novo pedido',`${payload.code} — ${payload.customer.name}`,'warning');
    loadOrders();
  }else if(event==='ORDER_STATUS_CHANGED'){
    loadOrders();
  }else if(event==='PAYMENT_CONFIRMED'){
    notify('Pagamento confirmado',`${payload.code}`,'success');
    Promise.all([loadOrders(),loadCash()]);
  }
});
