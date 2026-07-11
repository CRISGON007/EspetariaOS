let products=[],cart=new Map();const $=id=>document.getElementById(id);const money=c=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(c/100);const esc=v=>{const d=document.createElement('div');d.textContent=v??'';return d.innerHTML};
async function loadProducts(){const r=await fetch('/api/products');products=(await r.json()).items||[];const cats=[...new Set(products.map(p=>p.category))].sort();$('category').innerHTML='<option value="">Todas as categorias</option>'+cats.map(c=>`<option>${c}</option>`).join('');renderProducts()}
function renderProducts(){const q=$('search').value.toLowerCase(),cat=$('category').value;$('products').innerHTML=products.filter(p=>(!cat||p.category===cat)&&(`${p.name} ${p.description}`.toLowerCase().includes(q))).map(p=>`<article class="product-card"><span class="status">${esc(p.category)}</span><h3>${esc(p.name)}</h3><p>${esc(p.description)}</p><div class="summary"><span class="price">${money(p.price_cents)}</span><button class="primary" onclick="add(${p.id})">Adicionar</button></div></article>`).join('')||'<p>Nenhum produto encontrado.</p>'}
function add(id){cart.set(id,(cart.get(id)||0)+1);updateCart()}function change(id,d){const n=(cart.get(id)||0)+d;n<=0?cart.delete(id):cart.set(id,n);updateCart();renderCart()}function total(){return [...cart].reduce((s,[id,q])=>s+products.find(p=>p.id===id).price_cents*q,0)}
function updateCart(){const n=[...cart.values()].reduce((a,b)=>a+b,0);$('cartCount').textContent=`${n} ${n===1?'item':'itens'}`;$('cartTotal').textContent=money(total())}
function renderCart(){$('cartItems').innerHTML=[...cart].map(([id,q])=>{const p=products.find(x=>x.id===id);return `<div class="cart-row"><div><strong>${esc(p.name)}</strong><br><small>${money(p.price_cents)} cada</small></div><div class="qty"><button type="button" class="small" onclick="change(${id},-1)">−</button><b>${q}</b><button type="button" class="small" onclick="change(${id},1)">+</button></div><span class="price">${money(p.price_cents*q)}</span></div>`}).join('')||'<p>Carrinho vazio.</p>';$('cartDialogTotal').textContent=money(total())}
$('search').addEventListener('input',renderProducts);$('category').addEventListener('change',renderProducts);$('openCart').addEventListener('click',()=>{renderCart();$('customerName').value=localStorage.getItem('customer_name')||'';$('customerPhone').value=localStorage.getItem('customer_phone')||'';$('cartDialog').showModal()});$('openTrack').addEventListener('click',()=>{$('trackPhone').value=localStorage.getItem('customer_phone')||'';$('trackDialog').showModal()});
$('finishOrder').addEventListener('click',async()=>{const m=$('cartMessage');m.textContent='';if(!cart.size){m.textContent='Adicione um produto.';return}const name=$('customerName').value.trim(),phone=$('customerPhone').value.trim();try{const r=await fetch('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({customer:{name,phone},paymentMethod:$('paymentMethod').value,notes:$('orderNotes').value,items:[...cart].map(([productId,quantity])=>({productId,quantity}))})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Erro.');localStorage.setItem('customer_name',name);localStorage.setItem('customer_phone',phone);cart.clear();updateCart();m.className='message success';m.innerHTML=`Pedido criado: <strong>${d.code}</strong><br>Total: ${money(d.totalCents)}`;$('trackPhone').value=phone;$('trackCode').value=d.code}catch(e){m.className='message';m.textContent=e.message}});
$('trackOrder').addEventListener('click',async()=>{const out=$('trackResult');try{const r=await fetch(`/api/orders/track?phone=${encodeURIComponent($('trackPhone').value)}&code=${encodeURIComponent($('trackCode').value)}`);const o=await r.json();if(!r.ok)throw new Error(o.detail||'Não encontrado.');out.innerHTML=`<article class="order-card"><h3>${o.code}</h3><span class="status ${o.status}">${PT_BR.orderStatus[o.status] || "Status desconhecido"}</span><p>${esc(o.customer.name)}</p><ul>${o.items.map(i=>`<li>${i.quantity}x ${esc(i.name)}</li>`).join('')}</ul><p class="price">${money(o.totalCents)}</p></article>`}catch(e){out.innerHTML=`<p class="message">${e.message}</p>`}});loadProducts();

connectRealtime((event,payload)=>{
  if(event==='ORDER_STATUS_CHANGED'){
    const savedPhone=(localStorage.getItem('customer_phone')||'').replace(/\D/g,'');
    if(payload?.customer?.phone===savedPhone){
      notify('Atualização do pedido',`${payload.code}: ${orderStatusLabel(payload.status)}`,'success');
      if(document.getElementById('trackCode')?.value===payload.code){
        document.getElementById('trackOrder')?.click();
      }
    }
  }
  if(event==='PAYMENT_CONFIRMED'){
    const savedPhone=(localStorage.getItem('customer_phone')||'').replace(/\D/g,'');
    if(payload?.customer?.phone===savedPhone){
      notify('Pagamento confirmado',`Pedido ${payload.code}`,'success');
    }
  }
});
