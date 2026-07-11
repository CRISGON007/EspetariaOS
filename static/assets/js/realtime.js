let realtimeSocket = null;
let realtimeRetry = null;

function notify(title, message, type='info'){
  let container = document.getElementById('toastContainer');
  if(!container){
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('article');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<strong>${title}</strong><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(()=>toast.classList.add('show'),10);
  setTimeout(()=>{
    toast.classList.remove('show');
    setTimeout(()=>toast.remove(),250);
  },6000);
}

function realtimeUrl(){
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/ws`;
}

function connectRealtime(onEvent){
  clearTimeout(realtimeRetry);
  try{
    realtimeSocket = new WebSocket(realtimeUrl());
  }catch(_){
    realtimeRetry = setTimeout(()=>connectRealtime(onEvent),5000);
    return;
  }

  realtimeSocket.addEventListener('open',()=>{
    realtimeSocket.send('ready');
  });

  realtimeSocket.addEventListener('message',event=>{
    try{
      const data = JSON.parse(event.data);
      if(data.event !== 'CONNECTED' && typeof onEvent === 'function'){
        onEvent(data.event, data.payload);
      }
    }catch(_){}
  });

  realtimeSocket.addEventListener('close',()=>{
    realtimeRetry = setTimeout(()=>connectRealtime(onEvent),3000);
  });

  realtimeSocket.addEventListener('error',()=>{
    try{ realtimeSocket.close(); }catch(_){}
  });
}
