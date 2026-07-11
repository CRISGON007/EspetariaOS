if(user.role!=='ADMIN') location.href='/atendimento';

let products = [];
let dashboardOrders = [];
const dialog = document.getElementById('productDialog');

const sectionMap = {
  dashboard:'dashboardSection',
  products:'productsSection',
  customers:'customersSection',
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

document.getElementById('newProduct').addEventListener('click',()=>openForm());
document.getElementById('productSearch').addEventListener('input',renderProducts);
document.getElementById('refreshDashboard').addEventListener('click',()=>Promise.all([loadProducts(),loadDashboardOrders()]));

document.getElementById('saveProduct').addEventListener('click',async()=>{
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
    available:document.getElementById('productAvailable').checked
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

Promise.all([loadProducts(),loadDashboardOrders()]);

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
connectRealtime((event,payload)=>{
  if(['ORDER_CREATED','ORDER_STATUS_CHANGED','PAYMENT_CONFIRMED'].includes(event)){
    if(event==='ORDER_CREATED') notify('Novo pedido',`${payload.code} — ${payload.customer.name}`,'warning');
    loadDashboardOrders();
  }
});
configureDemo();
