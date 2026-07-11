if(user.role !== 'ADMIN') location.href = '/atendimento';

function bytes(value){
  const units=['B','KB','MB','GB','TB'];
  let size=Number(value||0), i=0;
  while(size>=1024 && i<units.length-1){size/=1024;i++}
  return `${size.toFixed(i?1:0)} ${units[i]}`;
}
function uptime(seconds){
  const d=Math.floor(seconds/86400);
  const h=Math.floor((seconds%86400)/3600);
  const m=Math.floor((seconds%3600)/60);
  return `${d}d ${h}h ${m}min`;
}
function service(label,status){
  const ok=status==='ONLINE';
  return `<article class="service-item"><span class="service-dot ${ok?'online':'neutral'}"></span><div><strong>${label}</strong><small>${serviceStatusLabel(status)}</small></div></article>`;
}
async function loadStatus(){
  const data=await api('/api/admin/system/status');
  const s=data.system, d=data.database;
  document.getElementById('systemCards').innerHTML=`
    <article class="dashboard-card"><span>CPU</span><strong>${s.cpuPercent}%</strong><small>${s.cpuCount} núcleos lógicos</small></article>
    <article class="dashboard-card"><span>Memória</span><strong>${s.memory.percent}%</strong><small>${bytes(s.memory.used)} de ${bytes(s.memory.total)}</small></article>
    <article class="dashboard-card"><span>Disco</span><strong>${s.disk.percent}%</strong><small>${bytes(s.disk.free)} livres</small></article>
    <article class="dashboard-card"><span>Temperatura</span><strong>${s.temperatureC===null?'N/D':s.temperatureC+' °C'}</strong><small>${s.hostname}</small></article>
    <article class="dashboard-card"><span>Uptime do serviço</span><strong>${uptime(s.serviceUptimeSeconds)}</strong><small>Versão ${s.version}</small></article>
    <article class="dashboard-card"><span>Clientes</span><strong>${d.customers}</strong><small>${d.orders} pedidos registrados</small></article>
    <article class="dashboard-card"><span>Produtos disponíveis</span><strong>${d.availableProducts}</strong><small>${d.products} cadastrados</small></article>
    <article class="dashboard-card"><span>Banco SQLite</span><strong>${bytes(s.databaseSize)}</strong><small>${s.databasePath}</small></article>`;
  const services=data.services;
  document.getElementById('services').innerHTML=
    service('API',services.api)+service('Banco de dados',services.database)+
    service('Interface web',services.webInterface)+service('PIX',services.pixIntegration)+
    service('Impressora',services.printer);
}
async function loadBackups(){
  const data=await api('/api/admin/system/backups');
  document.getElementById('backups').innerHTML=data.items.length?data.items.map(item=>`
    <article class="dashboard-order-row">
      <div><strong>${item.name}</strong><small>${new Date(item.createdAt).toLocaleString('pt-BR')}</small></div>
      <span>${bytes(item.size)}</span>
      <button class="small" onclick="downloadBackup('${item.name}')">Baixar</button>
    </article>`).join(''):'<p>Nenhum backup criado.</p>';
}
async function loadLogs(){
  const data=await api('/api/admin/system/logs?limit=100');
  document.getElementById('auditLogs').innerHTML=data.items.length?data.items.map(item=>`
    <article class="audit-row">
      <time>${new Date(item.created_at).toLocaleString('pt-BR')}</time>
      <strong>${auditActionLabel(item.action)}</strong>
      <span>${item.user_name||'Sistema'}</span>
      <p>${item.details||''}</p>
    </article>`).join(''):'<p>Nenhum evento registrado.</p>';
}
async function downloadBackup(name){
  const response=await fetch(`/api/admin/system/backups/${encodeURIComponent(name)}`,{
    headers:{Authorization:`Bearer ${token}`}
  });
  if(!response.ok){const d=await response.json();alert(d.detail||'Erro.');return}
  const blob=await response.blob();
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;link.download=name;link.click();
  URL.revokeObjectURL(url);
}
document.getElementById('createBackup').addEventListener('click',async()=>{
  try{
    const result=await api('/api/admin/system/backups',{method:'POST'});
    alert(`Backup criado: ${result.name}`);
    await Promise.all([loadBackups(),loadLogs()]);
  }catch(e){alert(e.message)}
});
document.getElementById('refreshSystem').addEventListener('click',()=>Promise.all([loadStatus(),loadBackups(),loadLogs()]));
Promise.all([loadStatus(),loadBackups(),loadLogs()]);

connectRealtime((event,payload)=>{
  if(event==='ORDER_CREATED') notify('Novo pedido recebido',payload.code,'warning');
  if(event==='PAYMENT_CONFIRMED') notify('Pagamento confirmado',payload.code,'success');
});


const SYSTEM_REFRESH_INTERVAL_MS = 15000;
setInterval(
  ()=>Promise.all([loadStatus(),loadBackups(),loadLogs()]),
  SYSTEM_REFRESH_INTERVAL_MS
);
