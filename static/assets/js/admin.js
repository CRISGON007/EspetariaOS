if(user.role!=='ADMIN') location.href='/atendimento';

let products = [];
let dashboardOrders = [];
const dialog = document.getElementById('productDialog');

const sectionMap = {
  dashboard:'dashboardSection',
  products:'productsSection',
  stock:'stockSection',
  sales:'salesSection',
  customers:'customersSection',
  audit:'auditSection',
  settings:'settingsSection'
};

document.querySelectorAll('.nav-item').forEach(button=>{
  button.addEventListener('click',()=>{
    document.querySelectorAll('.nav-item').forEach(item=>item.classList.remove('active'));
    button.classList.add('active');
    Object.values(sectionMap).forEach(id=>document.getElementById(id).classList.add('hidden'));
    document.getElementById(sectionMap[button.dataset.section]).classList.remove('hidden');
  });
});

async function loadProducts(){
  const data = await api('/api/admin/products');
  products = data.items;
  renderProducts();
  updateDashboard();
}

async function loadDashboardOrders(){
  const data = await api('/api/staff/orders');
  dashboardOrders = data.items;
  updateDashboard();
}

function timelineDuration(order,status){
  return (order.statusTimeline||[])
    .filter(item=>item.status===status)
    .reduce((total,item)=>total+Number(item.durationSeconds||0),0);
}

function completedOrderTotal(order){
  if(order.status!=='DELIVERED')return null;
  return orderTotalSeconds(order);
}

function average(values){
  const valid=values.filter(value=>Number.isFinite(value) && value>=0);
  return valid.length
    ? Math.round(valid.reduce((sum,value)=>sum+value,0)/valid.length)
    : 0;
}

function updateOperationalMetrics(){
  const delivered=dashboardOrders.filter(order=>order.status==='DELIVERED');
  const preparationTimes=delivered
    .map(order=>timelineDuration(order,'PREPARING'))
    .filter(value=>value>0);
  const totalTimes=delivered
    .map(completedOrderTotal)
    .filter(value=>value!==null);

  document.getElementById('dashboardAveragePreparation').textContent=
    formatDuration(average(preparationTimes));
  document.getElementById('dashboardAverageTotal').textContent=
    formatDuration(average(totalTimes));

  if(!totalTimes.length){
    document.getElementById('dashboardFastestOrder').textContent='—';
    document.getElementById('dashboardSlowestOrder').textContent='—';
    return;
  }

  const ordered=delivered
    .map(order=>({order,total:completedOrderTotal(order)}))
    .filter(item=>item.total!==null)
    .sort((a,b)=>a.total-b.total);

  const fastest=ordered[0];
  const slowest=ordered[ordered.length-1];

  document.getElementById('dashboardFastestOrder').innerHTML=
    `${formatDuration(fastest.total)}<small>${fastest.order.code}</small>`;
  document.getElementById('dashboardSlowestOrder').innerHTML=
    `${formatDuration(slowest.total)}<small>${slowest.order.code}</small>`;
}

function updateDashboard(){
  document.getElementById('dashboardProducts').textContent = products.length;
  document.getElementById('dashboardAvailable').textContent =
    products.filter(p=>p.active && p.available).length;

  const active = dashboardOrders.filter(o=>!['DELIVERED','CANCELLED'].includes(o.status));
  document.getElementById('dashboardActiveOrders').textContent = active.length;

  const paidRevenue = dashboardOrders
    .filter(o=>o.paymentStatus==='PAID')
    .reduce((sum,o)=>sum+o.totalCents,0);

  document.getElementById('dashboardRevenue').textContent = money(paidRevenue);

  document.getElementById('dashboardOrders').innerHTML =
    dashboardOrders.slice(0,8).map(order=>`
      <article class="dashboard-order-row">
        <div>
          <strong>${order.code}</strong>
          <small>${order.customer.name}</small>
        </div>
        <span class="status ${order.status}">${orderStatusLabel(order.status)}</span>
        <strong>${money(order.totalCents)}</strong>
      </article>
    `).join('') || '<p>Nenhum pedido registrado.</p>';

  updateOperationalMetrics();
}

function renderProducts(){
  const query = document.getElementById('productSearch').value.toLowerCase();
  document.getElementById('productRows').innerHTML =
    products
      .filter(product=>`${product.name} ${product.category}`.toLowerCase().includes(query))
      .map(product=>`
        <tr>
          <td><strong>${product.name}</strong><br><small>${product.description || ''}</small></td>
          <td>${product.category}</td>
          <td>${money(product.price_cents)}</td>
          <td>${product.stock_controlled?product.stock_quantity:'—'}</td>
          <td><span class="availability ${product.active?'on':'off'}">${product.active?'Ativo':'Inativo'}</span></td>
          <td><span class="availability ${product.available?'on':'off'}">${product.available?'Disponível':'Indisponível'}</span></td>
          <td>
            <div class="actions">
              <button class="small" onclick="editProduct(${product.id})">Editar</button>
              <button class="danger" onclick="removeProduct(${product.id})">Excluir</button>
            </div>
          </td>
        </tr>
      `).join('');
}

function toggleProductStockFields(){
  const controlled=document.getElementById('productStockControlled')?.checked;
  document.getElementById('productStockFields')?.classList.toggle('hidden',!controlled);
}
function clearProductStockErrors(){
  ['productStockQuantity','productMinimumStock'].forEach(id=>{
    document.getElementById(id)?.classList.remove('invalid-field');
    const error=document.getElementById(`${id}Error`);
    if(error)error.textContent='';
  });
}
function validateProductStock(){
  clearProductStockErrors();
  if(!document.getElementById('productStockControlled')?.checked)return true;
  const qf=document.getElementById('productStockQuantity');
  const mf=document.getElementById('productMinimumStock');
  const qtxt=qf.value.trim(), mtxt=mf.value.trim();
  const q=Number(qtxt), m=Number(mtxt);
  const errors=[];
  if(qtxt===''||!Number.isInteger(q)||q<0)errors.push([qf,document.getElementById('productStockQuantityError'),'Informe a quantidade disponível para venda.']);
  if(mtxt===''||!Number.isInteger(m)||m<0)errors.push([mf,document.getElementById('productMinimumStockError'),'Informe a quantidade mínima do produto.']);
  errors.forEach(([field,error,message])=>{field.classList.add('invalid-field');if(error)error.textContent=message;});
  if(errors.length){
    errors[0][0].focus();
    document.getElementById('productMessage').textContent='Preencha os campos obrigatórios do estoque.';
    return false;
  }
  return true;
}
document.getElementById('productStockControlled')?.addEventListener('change',toggleProductStockFields);
['productStockQuantity','productMinimumStock'].forEach(id=>{
  document.getElementById(id)?.addEventListener('input',()=>{
    document.getElementById(id)?.classList.remove('invalid-field');
    const error=document.getElementById(`${id}Error`);
    if(error)error.textContent='';
  });
});

function openForm(product=null){
  document.getElementById('productDialogTitle').textContent =
    product ? 'Editar produto' : 'Novo produto';
  document.getElementById('productId').value = product?.id || '';
  document.getElementById('productName').value = product?.name || '';
  document.getElementById('productCategory').value = product?.category || 'Espetos';
  document.getElementById('productDescription').value = product?.description || '';
  document.getElementById('productPrice').value =
    product ? (product.price_cents / 100).toFixed(2).replace('.',',') : '';
  document.getElementById('productActive').checked = product?.active ?? true;
  document.getElementById('productAvailable').checked = product?.available ?? true;
  document.getElementById('productCost').value=product?(product.cost_cents/100).toFixed(2).replace('.',','):'';
  document.getElementById('productStockControlled').checked=product?.stock_controlled??false;
  document.getElementById('productStockQuantity').value=product?.stock_quantity??0;
  document.getElementById('productMinimumStock').value=product?.minimum_stock??0;
  clearProductStockErrors();
  toggleProductStockFields();
  document.getElementById('productMessage').textContent = '';
  dialog.showModal();
}

function editProduct(id){
  openForm(products.find(product=>product.id===id));
}

async function removeProduct(id){
  if(!confirm('Excluir ou desativar este produto?')) return;
  try{
    await api(`/api/admin/products/${id}`,{method:'DELETE'});
    await loadProducts();
  }catch(e){
    alert(e.message);
  }
}

document.getElementById('newProduct')?.addEventListener('click',()=>openForm());
document.getElementById('productSearch')?.addEventListener('input',renderProducts);
document.getElementById('refreshDashboard')?.addEventListener(
  'click',
  ()=>Promise.all([loadProducts(),loadDashboardOrders()])
);

document.getElementById('saveProduct')?.addEventListener('click',async()=>{
  const id = document.getElementById('productId').value;
  const rawPrice = document.getElementById('productPrice').value
    .replace(/\./g,'')
    .replace(',','.');

  const body = {
    name:document.getElementById('productName').value,
    category:document.getElementById('productCategory').value,
    description:document.getElementById('productDescription').value,
    priceCents:Math.round(Number(rawPrice)*100),
    active:document.getElementById('productActive').checked,
    available:document.getElementById('productAvailable').checked,
    costCents:Math.round(Number(document.getElementById('productCost').value.replace(/\./g,'').replace(',','.')||0)*100),
    stockControlled:document.getElementById('productStockControlled').checked,
    stockQuantity:Number(document.getElementById('productStockQuantity').value||0),
    minimumStock:Number(document.getElementById('productMinimumStock').value||0)
  };

  const message = document.getElementById('productMessage');

  try{
    await api(
      id ? `/api/admin/products/${id}` : '/api/admin/products',
      {
        method:id ? 'PUT' : 'POST',
        body:JSON.stringify(body)
      }
    );
    dialog.close();
    await loadProducts();
  }catch(e){
    message.textContent = e.message;
  }
});

Promise.all([loadProducts(),loadDashboardOrders()]).catch(error=>{
  console.error('Falha ao carregar o painel administrativo:',error);
  const container=document.getElementById('dashboardOrders');
  if(container){
    container.innerHTML=`<p class="message">Não foi possível atualizar o painel: ${error.message}</p>`;
  }
});

async function configureDemo(){
  try{
    const data=await api('/api/admin/demo/status');
    const button=document.getElementById('demoOrder');
    if(data.enabled){
      button.classList.remove('hidden');
      button.addEventListener('click',async()=>{
        try{
          const order=await api('/api/admin/demo/order',{method:'POST'});
          notify('Pedido de demonstração',`${order.code} criado.`,'success');
          await loadDashboardOrders();
        }catch(e){alert(e.message)}
      });
    }
  }catch(_){}
}
configureDemo();


const ADMIN_REFRESH_INTERVAL_MS = 10000;

async function refreshAdminData(){
  try{
    await Promise.all([loadProducts(),loadDashboardOrders()]);
  }catch(e){
    console.error('Falha ao atualizar o painel administrativo:',e);
  }
}

connectRealtime((event,payload)=>{
  if(['ORDER_CREATED','ORDER_STATUS_CHANGED','PAYMENT_CONFIRMED'].includes(event)){
    const messages={
      ORDER_CREATED:['Novo pedido',`${payload.code} — ${payload.customer.name}`,'warning'],
      ORDER_STATUS_CHANGED:['Pedido atualizado',`${payload.code}: ${orderStatusLabel(payload.status)}`,'info'],
      PAYMENT_CONFIRMED:['Pagamento confirmado',payload.code,'success']
    };
    const [title,message,type]=messages[event];
    notify(title,message,type);
    refreshAdminData();
  }
});

setInterval(refreshAdminData,ADMIN_REFRESH_INTERVAL_MS);

function saleParams(){const p=new URLSearchParams();const v={code:document.getElementById('saleCode')?.value.trim(),customer:document.getElementById('saleCustomer')?.value.trim(),phone:document.getElementById('salePhone')?.value.trim(),status:document.getElementById('saleStatus')?.value,payment_method:document.getElementById('salePaymentMethod')?.value,payment_status:document.getElementById('salePaymentStatus')?.value,start_date:document.getElementById('saleStartDate')?.value,end_date:document.getElementById('saleEndDate')?.value};Object.entries(v).forEach(([k,x])=>{if(x)p.set(k,x)});return p}
function formatDuration(seconds){const total=Math.max(0,Number(seconds||0)),h=Math.floor(total/3600),m=Math.floor((total%3600)/60),s=Math.floor(total%60);if(h>0)return `${h}h ${m}min`;if(m>0)return `${m}min ${s}s`;return `${s}s`}
function orderTotalSeconds(order){
  return (order.statusTimeline||[]).reduce(
    (total,item)=>total+Number(item.durationSeconds||0),
    0
  );
}

function totalTimeClass(seconds){
  if(seconds<=15*60)return 'excellent';
  if(seconds<=25*60)return 'attention';
  return 'late';
}

function statusTimelineHtml(order){
  const timeline=order.statusTimeline||[];

  if(!timeline.length){
    return '<span class="timeline-empty">Histórico indisponível</span>';
  }

  const totalSeconds=orderTotalSeconds(order);
  const finished=order.status==='DELIVERED';
  const totalLabel=finished?'Tempo total do pedido':'Tempo decorrido';

  return `
    <div class="status-timeline">
      ${timeline.map(item=>{
        const deliveredTotal=item.status==='DELIVERED'
          ? `<span class="delivered-total">Total: ${formatDuration(totalSeconds)}</span>`
          : '';

        return `
          <div class="timeline-item ${item.current?'current':''}">
            <div class="timeline-status-line">
              <span class="status ${item.status}">
                ${orderStatusLabel(item.status)}
              </span>
              ${deliveredTotal}
            </div>
            <strong>${formatDuration(item.durationSeconds)}</strong>
            <small>
              ${new Date(item.enteredAt).toLocaleString('pt-BR')}
              ${item.current?' · atual':''}
            </small>
          </div>
        `;
      }).join('')}
    </div>
    <div class="order-total-time ${totalTimeClass(totalSeconds)}">
      <span>⏱ ${totalLabel}</span>
      <strong>${formatDuration(totalSeconds)}</strong>
    </div>
  `;
}

async function loadSales(){const d=await api(`/api/admin/sales?${saleParams()}`);document.getElementById('salesCount').textContent=`${d.count} ${d.count===1?'venda':'vendas'}`;document.getElementById('salesResults').innerHTML=d.items.length?d.items.map(o=>`<article class="sales-result-card"><div class="sales-result-header"><div><strong>${o.code}</strong><small>${o.customer.name} · ${o.customer.phone}</small></div><span class="status ${o.status}">${orderStatusLabel(o.status)}</span><span>${paymentStatusLabel(o.paymentStatus)} · ${paymentMethodLabel(o.paymentMethod)}</span><strong>${money(o.totalCents)}</strong></div><div class="sales-status-times"><h4>Tempo em cada status</h4>${statusTimelineHtml(o)}</div></article>`).join(''):'<p>Nenhuma venda encontrada.</p>'}
document.getElementById('searchSales')?.addEventListener('click',loadSales);document.getElementById('exportSales')?.addEventListener('click',()=>{fetch(`/api/admin/sales/export.csv?${saleParams()}`,{headers:{Authorization:`Bearer ${token}`}}).then(r=>r.blob()).then(b=>{const u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download='vendas.csv';a.click();URL.revokeObjectURL(u)})});loadSales();

function formatPhone(value){const d=String(value||'').replace(/\D/g,'');if(d.length===11)return `(${d.slice(0,2)})${d.slice(2,7)}-${d.slice(7)}`;if(d.length===10)return `(${d.slice(0,2)})${d.slice(2,6)}-${d.slice(6)}`;return value||''}
async function loadCustomers(){try{const q=document.getElementById('customerSearch')?.value.trim()||'',d=await api(`/api/admin/customers?query=${encodeURIComponent(q)}`);document.getElementById('customerCount').textContent=`${d.count} ${d.count===1?'cliente':'clientes'}`;document.getElementById('customerResults').innerHTML=d.items.length?d.items.map(c=>`<article class="customer-card"><div><strong>${c.name}</strong><small>${formatPhone(c.phone)}</small></div><div class="customer-stat"><span>Pedidos</span><strong>${c.orderCount}</strong></div><div class="customer-stat"><span>Total pago</span><strong>${money(c.paidTotalCents)}</strong></div><div class="customer-stat"><span>Último pedido</span><strong>${c.lastOrderAt?new Date(c.lastOrderAt).toLocaleString('pt-BR'):'Nenhum'}</strong></div></article>`).join(''):'<p>Nenhum cliente encontrado.</p>'}catch(e){document.getElementById('customerResults').innerHTML=`<p class="message">${e.message}</p>`}}
function auditParams(){const p=new URLSearchParams(),v={action:document.getElementById('auditAction')?.value,user_name:document.getElementById('auditUser')?.value.trim(),start_date:document.getElementById('auditStartDate')?.value,end_date:document.getElementById('auditEndDate')?.value};Object.entries(v).forEach(([k,x])=>{if(x)p.set(k,x)});return p}
async function loadAudit(){try{const d=await api(`/api/admin/audit?${auditParams()}`);document.getElementById('auditCount').textContent=`${d.count} ${d.count===1?'evento':'eventos'}`;document.getElementById('auditResults').innerHTML=d.items.length?d.items.map(i=>`<article class="audit-row"><time>${new Date(i.created_at).toLocaleString('pt-BR')}</time><strong>${auditActionLabel(i.action)}</strong><span>${i.user_name||'Sistema'}</span><p>${i.details||''}</p></article>`).join(''):'<p>Nenhum evento encontrado.</p>'}catch(e){document.getElementById('auditResults').innerHTML=`<p class="message">${e.message}</p>`}}
document.getElementById('searchCustomers')?.addEventListener('click',loadCustomers);document.getElementById('customerSearch')?.addEventListener('keydown',e=>{if(e.key==='Enter')loadCustomers()});document.getElementById('searchAudit')?.addEventListener('click',loadAudit);loadCustomers();loadAudit();

let stockData={summary:{},products:[],movements:[]};const stockDialog=document.getElementById('stockDialog');
function stockSituation(p){if(!p.stock_controlled)return ['Sem controle','off'];if(p.stock_quantity<=0)return ['Sem estoque','off'];if(p.stock_quantity<=p.minimum_stock)return ['Estoque baixo','warning'];return ['Normal','on']}
async function loadStock(){try{stockData=await api('/api/admin/stock');const x=stockData.summary||{};document.getElementById('stockControlledCount').textContent=x.controlledProducts||0;document.getElementById('stockUnitsCount').textContent=x.totalUnits||0;document.getElementById('stockLowCount').textContent=x.lowStockProducts||0;document.getElementById('stockOutCount').textContent=x.outOfStockProducts||0;document.getElementById('stockValue').textContent=money(x.stockValueCents||0);const ps=(stockData.products||[]).filter(p=>p.stock_controlled);document.getElementById('stockProductRows').innerHTML=ps.length?ps.map(p=>{const [l,c]=stockSituation(p);return `<tr><td><strong>${p.name}</strong><br><small>${p.category}</small></td><td>${p.stock_quantity}</td><td>${p.minimum_stock}</td><td><span class="availability ${c}">${l}</span></td><td><button class="small" onclick="openStockMovement(${p.id})">Movimentar</button></td></tr>`}).join(''):'<tr><td colspan="5">Nenhum produto controlado.</td></tr>';document.getElementById('stockMovementRows').innerHTML=(stockData.movements||[]).length?stockData.movements.map(i=>`<article class="stock-movement-row"><div><strong>${i.product_name}</strong><small>${new Date(i.created_at).toLocaleString('pt-BR')}</small></div><span class="stock-type ${i.movement_type}">${stockMovementLabel(i.movement_type)}</span><strong class="${i.quantity>=0?'stock-positive':'stock-negative'}">${i.quantity>=0?'+':''}${i.quantity}</strong><span>Saldo: ${i.balance_after}</span><p>${i.reason||''}</p></article>`).join(''):'<p>Nenhuma movimentação.</p>'}catch(e){document.getElementById('stockMovementRows').innerHTML=`<p class="message">${e.message}</p>`}}
function openStockMovement(id){const p=(stockData.products||[]).find(x=>x.id===id);if(!p)return;document.getElementById('stockProductId').value=id;document.getElementById('stockProductName').textContent=`${p.name} — saldo: ${p.stock_quantity}`;document.getElementById('stockMovementType').value='ENTRY';document.getElementById('stockMovementQuantity').value='';document.getElementById('stockMovementReason').value='';stockDialog.showModal()}
document.getElementById('saveStockMovement')?.addEventListener('click',async()=>{const t=document.getElementById('stockMovementType').value;let q=Number(document.getElementById('stockMovementQuantity').value||0);if(t==='LOSS')q=-Math.abs(q);try{await api('/api/admin/stock/movements',{method:'POST',body:JSON.stringify({productId:Number(document.getElementById('stockProductId').value),quantity:q,movementType:t,reason:document.getElementById('stockMovementReason').value})});stockDialog.close();await Promise.all([loadStock(),loadProducts()]);notify('Estoque atualizado','Movimentação registrada.','success')}catch(e){document.getElementById('stockMovementMessage').textContent=e.message}});document.getElementById('refreshStock')?.addEventListener('click',loadStock);loadStock();connectRealtime(event=>{if(event==='STOCK_UPDATED'||event==='ORDER_CREATED'){loadStock();loadProducts()}});
