(()=>{
  const CARD_ID='blenderConnectionCard';
  let busy=false;
  let refreshTimer=null;

  const el=id=>document.getElementById(id);
  const api=async(name,...args)=>{
    const fn=window.pywebview?.api?.[name];
    if(typeof fn!=='function')return{ok:false,summary:`API indisponível: ${name}`};
    try{return await fn(...args)}catch(error){return{ok:false,summary:String(error)}}
  };
  const blenderMode=()=>/^blender\b/i.test((el('previewMeta')?.textContent||'').trim());

  function ensureCard(){
    let card=el(CARD_ID);
    if(card)return card;
    const pane=document.querySelector('.previewPane');
    const toolbar=pane?.querySelector('.previewToolbar');
    if(!pane||!toolbar)return null;
    card=document.createElement('section');
    card.id=CARD_ID;
    card.className='blenderConnectionCard hidden';
    card.setAttribute('aria-live','polite');
    toolbar.insertAdjacentElement('afterend',card);
    return card;
  }

  function button(label,action,{primary=false,pid=null}={}){
    const item=document.createElement('button');
    item.type='button';
    item.textContent=label;
    item.dataset.action=action;
    if(pid!==null)item.dataset.pid=String(pid);
    if(primary)item.classList.add('primary');
    return item;
  }

  function render(connection,summary=''){
    const card=ensureCard();
    if(!card)return;
    if(!blenderMode()||!connection||connection.state==='not_blender'){
      card.classList.add('hidden');
      card.replaceChildren();
      return;
    }
    card.classList.remove('hidden');
    card.replaceChildren();

    const text=document.createElement('div');
    text.className='blenderConnectionText';
    const title=document.createElement('strong');
    const detail=document.createElement('span');
    const actions=document.createElement('div');
    actions.className='blenderConnectionActions';

    const pid=connection.pid?`PID ${connection.pid}`:'';
    if(connection.state==='connected'||connection.state==='adopted'){
      title.textContent=connection.state==='adopted'?'Blender adotado':'Blender conectado';
      detail.textContent=[pid,connection.file].filter(Boolean).join(' · ')||summary||'Companion ORDAX ativo.';
      actions.append(button('Capturar','capture',{primary:true}),button('Reverificar','refresh'));
    }else if(connection.state==='restart_required'){
      title.textContent='Bridge ORDAX pendente';
      detail.textContent='Esta janela foi aberta antes do bridge. Instale agora e reabra somente esta janela uma vez.';
      actions.append(button('Instalar bridge','install',{primary:true}),button('Reverificar','refresh'));
    }else if(connection.state==='ambiguous'){
      title.textContent='Escolha a janela Blender';
      detail.textContent='Há mais de uma janela compatível com este projeto.';
      for(const instance of connection.instances||[]){
        const label=`Adotar PID ${instance.pid}${instance.file?' · '+String(instance.file).split(/[\\/]/).pop():''}`;
        actions.append(button(label,'adopt',{pid:instance.pid,primary:true}));
      }
      actions.append(button('Reverificar','refresh'));
    }else{
      title.textContent='Blender ainda não está aberto';
      detail.textContent='O ORDAX pode abrir uma única sessão conectada para este projeto.';
      if(connection.can_start)actions.append(button('Abrir Blender','start',{primary:true}));
      actions.append(button('Reverificar','refresh'));
    }

    text.append(title,detail);
    card.append(text,actions);
    card.querySelectorAll('[data-action]').forEach(item=>item.addEventListener('click',onAction));
  }

  async function onAction(event){
    if(busy)return;
    const action=event.currentTarget.dataset.action;
    busy=true;
    event.currentTarget.disabled=true;
    try{
      if(action==='capture'){
        if(typeof window.capturePreview==='function')await window.capturePreview();
        else await api('preview_capture');
      }else if(action==='install'){
        const result=await api('blender_install_bridge');
        render(result?.data?.connection,result?.summary);
      }else if(action==='adopt'){
        const result=await api('blender_adopt',Number(event.currentTarget.dataset.pid));
        render(result?.data,result?.summary);
        if(result?.ok&&typeof window.refreshPreview==='function')await window.refreshPreview(true);
      }else if(action==='start'){
        const result=await api('blender_start');
        render(result?.data,result?.summary);
        if(result?.ok&&typeof window.refreshPreview==='function')await window.refreshPreview(true);
      }else{
        await refresh();
      }
    }finally{
      busy=false;
      schedule(80);
    }
  }

  async function refresh(){
    if(busy||!blenderMode()){
      if(!blenderMode())render(null);
      return;
    }
    busy=true;
    try{
      const result=await api('blender_prepare');
      render(result?.data,result?.summary);
    }finally{busy=false}
  }

  function schedule(delay=120){
    clearTimeout(refreshTimer);
    refreshTimer=setTimeout(refresh,delay);
  }

  function start(){
    ensureCard();
    const meta=el('previewMeta');
    const workspace=el('workspace');
    if(meta)new MutationObserver(()=>schedule()).observe(meta,{childList:true,subtree:true,characterData:true});
    if(workspace)new MutationObserver(()=>schedule()).observe(workspace,{attributes:true,attributeFilter:['class']});
    schedule(200);
  }

  window.refreshBlenderConnectionControls=refresh;
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
