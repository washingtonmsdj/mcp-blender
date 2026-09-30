(()=>{
  let mounted=false;
  let connectedEmail='';

  function setGlobalStatus(message){
    if(typeof window.setStatus==='function')window.setStatus(message);
    else{
      const node=document.getElementById('globalStatus');
      if(node)node.textContent=message||'';
    }
  }

  function createDialog(){
    const overlay=document.createElement('div');
    overlay.id='accountOverlay';
    overlay.className='accountOverlay hidden';
    overlay.innerHTML=`
      <section class="accountDialog" role="dialog" aria-modal="true" aria-labelledby="accountDialogTitle">
        <div class="accountDialogHead">
          <div class="brandMark">O</div>
          <div class="accountDialogTitle">
            <div class="eyebrow">CONEXÃO SEGURA</div>
            <h2 id="accountDialogTitle">Conectar conta ORDAX</h2>
            <p>Vincule este computador à sua conta para que clientes autorizados encontrem o ORDAX Runtime.</p>
          </div>
          <button id="accountClose" class="accountClose" type="button" aria-label="Fechar">×</button>
        </div>
        <form id="accountForm" class="accountForm" autocomplete="on">
          <label>E-mail
            <input id="accountEmail" class="accountInput" type="email" autocomplete="username" maxlength="320" required>
          </label>
          <label>Senha
            <input id="accountPassword" class="accountInput" type="password" autocomplete="current-password" maxlength="2048" required>
          </label>
          <div class="accountActions">
            <button id="accountSubmit" class="primary" type="submit">Conectar computador</button>
            <button id="accountCancel" class="subtleButton" type="button">Cancelar</button>
          </div>
        </form>
        <div class="accountSecurity">A senha é enviada diretamente ao Supabase Auth por este aplicativo local. O Worker ORDAX não recebe nem armazena a senha. O JWT de login é usado apenas durante o vínculo e não é persistido pelo Studio.</div>
        <div id="accountStatus" class="accountStatus" aria-live="polite"></div>
      </section>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  function mount(){
    if(mounted)return;
    const appbar=document.querySelector('.appbar');
    const runtime=document.getElementById('runtimePill');
    if(!appbar||!runtime)return;
    mounted=true;

    const button=document.createElement('button');
    button.id='accountButton';
    button.type='button';
    button.className='accountButton';
    button.textContent='Conectar conta';
    button.title='Conectar este computador à conta ORDAX';
    appbar.insertBefore(button,runtime);

    const overlay=createDialog();
    const form=document.getElementById('accountForm');
    const email=document.getElementById('accountEmail');
    const password=document.getElementById('accountPassword');
    const submit=document.getElementById('accountSubmit');
    const status=document.getElementById('accountStatus');

    const close=()=>{
      overlay.classList.add('hidden');
      password.value='';
      status.textContent='';
      status.className='accountStatus';
    };
    const open=()=>{
      overlay.classList.remove('hidden');
      requestAnimationFrame(()=>email.focus());
    };

    button.onclick=open;
    document.getElementById('accountClose').onclick=close;
    document.getElementById('accountCancel').onclick=close;
    overlay.addEventListener('click',event=>{if(event.target===overlay)close()});
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!overlay.classList.contains('hidden'))close()});

    form.addEventListener('submit',async event=>{
      event.preventDefault();
      const accountEmail=email.value.trim();
      const accountPassword=password.value;
      if(!accountEmail||!accountPassword)return;

      submit.disabled=true;
      status.className='accountStatus';
      status.innerHTML='<span class="accountSpinner"></span>Autenticando e vinculando este computador…';
      setGlobalStatus('Conectando conta ORDAX...');

      let result;
      try{
        if(!window.pywebview?.api?.connect_product_account){
          result={ok:false,summary:'Esta edição do Studio não expõe conexão de conta.'};
        }else{
          result=await window.pywebview.api.connect_product_account(accountEmail,accountPassword);
        }
      }catch(error){
        result={ok:false,summary:String(error)};
      }finally{
        password.value='';
        submit.disabled=false;
      }

      if(!result?.ok){
        status.className='accountStatus error';
        status.textContent=result?.summary||'Não foi possível conectar a conta ORDAX.';
        setGlobalStatus('Conta ORDAX não conectada');
        return;
      }

      connectedEmail=result.data?.email||accountEmail;
      button.textContent='Conta conectada';
      button.classList.add('connected');
      button.title=connectedEmail?`Conectado como ${connectedEmail}`:'Conta ORDAX conectada';
      status.className='accountStatus success';
      status.textContent=connectedEmail?`Computador vinculado a ${connectedEmail}.`:'Computador vinculado à conta ORDAX.';
      setGlobalStatus('ORDAX conectado à conta');
      setTimeout(close,900);
    });
  }

  window.addEventListener('pywebviewready',mount);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(mount,0));
  else setTimeout(mount,0);
})();
