const state={project:null,thread:null,models:[],connected:false,busy:false,autonomy:false,agents:[],capabilities:{},mode:"normal",normalChat:null,webBridge:null,webBridgeStartup:null,browserCompanion:null,browserConversation:null,browserMessageFingerprint:"",managedBrowser:null};

function api(){return window.pywebview.api}
function el(id){return document.getElementById(id)}
function unwrap(result){if(!result||!result.ok)throw new Error(result?.summary||"Falha no ORDAX");return result.data}
function setStatus(text,cls=""){el("statusText").textContent=text;el("statusText").className=cls}
function escapeHtml(value){return String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}

function renderMode(){
  const normal=state.mode==="normal";
  for(const node of document.querySelectorAll(".normal-only"))node.classList.toggle("hidden",!normal);
  for(const node of document.querySelectorAll(".agent-only"))node.classList.toggle("hidden",normal);
  el("modeSelect").value=state.mode;
  el("architectureClient").textContent=normal?"ChatGPT normal":"Agent / Responses";
  el("newThreadButton").disabled=normal;
  if(normal){
    state.thread=null;
    const endpoint=state.normalChat?.mcp_endpoint||"";
    el("normalMcpEndpoint").textContent=endpoint;
    el("composerInput").placeholder="Escreva aqui; o Browser Companion envia para a conversa real do ChatGPT Web…";
    if(!state.browserConversation){
      el("threadTitle").textContent="Chat normal via ORDAX";
      renderMessages([]);
    }
    setStatus("Modo Chat normal · Browser Companion + MCP ORDAX.");
  }else{
    el("composerInput").placeholder="Peça para analisar, implementar, testar ou continuar o projeto...";
    setStatus(state.connected?"Modo Agent / Responses · usa cota Work/Codex.":"Conecte o ChatGPT para usar Agent / Responses.");
  }
}

function renderWebBridge(status){
  state.webBridge=status||{};
  const running=!!state.webBridge.running;
  const configured=!!state.webBridge.configured;
  const enabled=!!state.webBridge.enabled;
  const installed=!!state.webBridge.client_installed;
  const daemon=state.webBridge.daemon||{};
  el("webBridgeBadge").textContent=running?"conectado":(enabled?"iniciando":(configured?"parado":"desconectado"));
  el("webBridgeBadge").classList.toggle("success",running);
  el("webBridgeConnectButton").textContent=running
    ?"Web Bridge conectado"
    :(!installed?"Instalar e conectar":"Conectar Web Bridge");
  el("webBridgeConnectButton").disabled=running;
  el("webBridgeStopButton").classList.toggle("hidden",!enabled&&!running);
  const details=[];
  if(state.webBridge.tunnel_id)details.push(state.webBridge.tunnel_id);
  if(installed)details.push("tunnel-client instalado");
  if(state.webBridge.initialized)details.push("profile pronto");
  if(running)details.push("PID "+state.webBridge.pid);
  if(daemon.heartbeat_fresh)details.push("supervisor ativo");
  else if(daemon.state&&daemon.state!=="not-running")details.push("supervisor "+daemon.state);
  el("webBridgeState").textContent=details.length?details.join(" · "):"Web Bridge não configurado.";
  el("webBridgeState").className=running?"success":"muted";
}

function renderWebBridgeStartup(status){
  state.webBridgeStartup=status||{};
  const supported=state.webBridgeStartup.supported!==false;
  const installed=!!state.webBridgeStartup.installed;
  el("webBridgeStartupButton").classList.toggle("hidden",!supported||installed);
  el("webBridgeStartupRemoveButton").classList.toggle("hidden",!supported||!installed);
  el("webBridgeStartupState").textContent=!supported
    ?"Startup automático disponível somente no Windows."
    :(installed?"Inicia com o Windows · "+(state.webBridgeStartup.state||"registrado"):"Não inicia automaticamente com o Windows.");
  el("webBridgeStartupState").className=installed?"success":"muted";
}

async function rolloverNormalChat(){
  if(state.mode!=="normal"){setStatus("Troque para Chat normal para usar o handoff.","error");return}
  const summary=el("handoffSummary").value.trim();
  const nextAction=el("handoffNextAction").value.trim();
  if(!summary){setStatus("Informe o resumo antes de abrir a nova conversa.","error");return}
  const project=state.project||el("projectSelect").value||"";
  const parts=[
    "Continue este trabalho no ORDAX.",
    project?("Projeto: "+project):"",
    "",
    "Resumo do contexto anterior:",
    summary,
    nextAction?("\nPróxima ação: "+nextAction):"",
    "",
    "Use o ORDAX/MCP já autorizado para verificar o estado real do projeto antes de executar alterações."
  ].filter(Boolean);
  try{
    const data=unwrap(await api().browser_companion_new_chat(parts.join("\n")));
    state.browserConversation=null;
    state.browserMessageFingerprint="";
    el("threadTitle").textContent="Aguardando nova conversa…";
    renderMessages([]);
    setStatus(data.opened
      ?"Nova conversa aberta; o Browser Companion enviará o handoff automaticamente."
      :"Handoff enfileirado; abra o ChatGPT para continuar.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function createHandoff(){
  const project=state.project||el("projectSelect").value;
  const summary=el("handoffSummary").value.trim();
  const nextAction=el("handoffNextAction").value.trim();
  if(!project){setStatus("Selecione um projeto.","error");return}
  if(!summary){setStatus("Informe um resumo para o Handoff.","error");return}
  try{
    const data=unwrap(await api().handoff_create(project,summary,nextAction,24));
    el("handoffId").value=data.handoff_id||"";
    el("handoffState").textContent=(data.handoff_id||"")+" · expira "+(data.expires_at||"");
    el("handoffState").className="success";
    setStatus("Handoff criado. Use esse ID em uma conversa nova do ChatGPT.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function loadHandoff(){
  const project=state.project||el("projectSelect").value;
  const id=el("handoffId").value.trim();
  if(!project||!id){setStatus("Selecione o projeto e informe o Handoff ID.","error");return}
  try{
    const data=unwrap(await api().handoff_get(project,id));
    el("handoffSummary").value=data.summary||"";
    el("handoffNextAction").value=data.next_action||"";
    const parts=[
      data.handoff_id||"",
      data.summary||"",
      data.next_action?("Próximo: "+data.next_action):"",
      data.expires_at?("Expira: "+data.expires_at):""
    ].filter(Boolean);
    el("handoffState").textContent=parts.join(" · ");
    el("handoffState").className="success";
    setStatus("Handoff carregado.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function refreshWebBridgeStartup(){
  try{renderWebBridgeStartup(unwrap(await api().web_bridge_startup_status()))}
  catch(err){el("webBridgeStartupState").textContent=err.message;el("webBridgeStartupState").className="error"}
}

async function installWebBridgeStartup(){
  try{
    const data=unwrap(await api().web_bridge_install_startup());
    renderWebBridgeStartup({...data,supported:true});
    await refreshWebBridge();
    setStatus("Web Bridge configurado para iniciar com o Windows.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function uninstallWebBridgeStartup(){
  try{
    const data=unwrap(await api().web_bridge_uninstall_startup());
    renderWebBridgeStartup({...data,supported:true});
    setStatus("Inicialização automática do Web Bridge removida.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function refreshWebBridge(){
  try{renderWebBridge(unwrap(await api().web_bridge_status()))}
  catch(err){el("webBridgeState").textContent=err.message;el("webBridgeState").className="error"}
}

async function connectWebBridge(){
  const tunnelId=el("webBridgeTunnelId").value.trim();
  const apiKey=el("webBridgeApiKey").value.trim();
  if(!tunnelId){setStatus("Informe o Tunnel ID (tunnel_...).","error");return}
  if(!apiKey && !state.webBridge?.configured){setStatus("Informe a Runtime API key.","error");return}
  try{
    setStatus("Configurando ORDAX Web Bridge…");
    if(apiKey){
      renderWebBridge(unwrap(await api().web_bridge_configure(tunnelId,apiKey)));
      el("webBridgeApiKey").value="";
    }
    if(!state.webBridge?.client_installed){
      setStatus("Instalando tunnel-client oficial da OpenAI…");
      renderWebBridge(unwrap(await api().web_bridge_install()));
    }
    setStatus("Validando e conectando Secure MCP Tunnel…");
    renderWebBridge(unwrap(await api().web_bridge_start()));
    setStatus("ORDAX Web Bridge conectado.","success");
  }catch(err){
    await refreshWebBridge();
    setStatus(err.message,"error");
  }
}

async function stopWebBridge(){
  try{
    renderWebBridge(unwrap(await api().web_bridge_stop()));
    setStatus("ORDAX Web Bridge parado.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function openWebBridgeTunnels(){
  try{unwrap(await api().web_bridge_open_tunnels())}
  catch(err){setStatus(err.message,"error")}
}

async function openWebBridgeApiKeys(){
  try{unwrap(await api().web_bridge_open_api_keys())}
  catch(err){setStatus(err.message,"error")}
}

async function openNormalChat(){
  try{
    const data=unwrap(await api().open_normal_chat());
    state.normalChat=data;
    el("normalMcpEndpoint").textContent=data.mcp_endpoint||"";
    setStatus(data.opened?"ChatGPT normal aberto. Use o ORDAX pelo plugin/MCP.":"Abra o ChatGPT e use o plugin ORDAX.","success");
  }catch(err){setStatus(err.message,"error")}
}

function renderManagedChatBrowser(status){
  state.managedBrowser=status||{};
  const running=!!state.managedBrowser.running;
  el("managedChatBrowserStartButton").classList.toggle("hidden",running);
  el("managedChatBrowserStopButton").classList.toggle("hidden",!running);
  const parts=[];
  if(running)parts.push("ativo");
  if(state.managedBrowser.pid)parts.push("PID "+state.managedBrowser.pid);
  if(state.managedBrowser.browser)parts.push(state.managedBrowser.browser.split(/[\\/]/).pop());
  if(state.managedBrowser.profile_dir)parts.push("perfil persistente");
  el("managedChatBrowserState").textContent=parts.length?parts.join(" · "):"Navegador dedicado parado.";
  el("managedChatBrowserState").className=running?"success":"muted";
}

async function startManagedChatBrowser(){
  try{
    const data=unwrap(await api().managed_chat_browser_start());
    renderManagedChatBrowser(data);
    setStatus("ChatGPT dedicado aberto com o Browser Companion carregado.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function stopManagedChatBrowser(){
  try{
    const data=unwrap(await api().managed_chat_browser_stop());
    renderManagedChatBrowser(data);
    setStatus("Navegador dedicado fechado.","success");
  }catch(err){setStatus(err.message,"error")}
}

function renderBrowserCompanion(status){
  state.browserCompanion=status||{};
  const paired=Number(state.browserCompanion.paired_clients||0)>0;
  el("browserCompanionBadge").textContent=paired?"pareado":"aguardando";
  el("browserCompanionBadge").classList.toggle("success",paired);
  const parts=[
    state.browserCompanion.start_error?("erro: "+state.browserCompanion.start_error):null,
    state.browserCompanion.running?"serviço local ativo":null,
    paired?(state.browserCompanion.paired_clients+" navegador(es) pareado(s)"):null,
    Number(state.browserCompanion.conversations||0)?(state.browserCompanion.conversations+" conversa(s) anexada(s)"):null
  ].filter(Boolean);
  el("browserCompanionState").textContent=parts.length?parts.join(" · "):"Extensão ainda não pareada.";
  el("browserCompanionState").className=state.browserCompanion.start_error?"error":"muted";
}

async function openBrowserCompanionExtensions(){
  try{unwrap(await api().browser_companion_open_extensions_page())}
  catch(err){setStatus(err.message,"error")}
}

async function openBrowserCompanionFolder(){
  try{
    const data=unwrap(await api().browser_companion_open_extension_folder());
    setStatus("Pasta da extensão aberta: "+data.path,"success");
  }catch(err){setStatus(err.message,"error")}
}

async function pairBrowserCompanion(){
  try{
    const data=unwrap(await api().browser_companion_pair());
    renderBrowserCompanion(unwrap(await api().browser_companion_status()));
    const box=el("browserCompanionPairCode");
    box.textContent=data.code;
    box.classList.remove("hidden");
    setStatus("Digite este código na extensão ORDAX Browser Companion: "+data.code,"success");
  }catch(err){setStatus(err.message,"error")}
}

function renderBrowserConversations(items){
  const list=el("threadList");list.innerHTML="";
  for(const conversation of items||[]){
    const item=document.createElement("div");
    item.className="thread"+(conversation.id===state.browserConversation?" active":"");
    item.textContent=conversation.title||("ChatGPT · "+conversation.id.slice(0,8));
    item.title=conversation.url||"";
    item.onclick=()=>openBrowserConversation(conversation.id);
    list.appendChild(item);
  }
  if(!(items||[]).length){
    list.innerHTML='<span class="muted">Abra uma conversa no ChatGPT Web e pareie a extensão.</span>';
  }
}

async function refreshBrowserCompanion(){
  try{
    const status=unwrap(await api().browser_companion_status());
    renderBrowserCompanion(status);
    if(state.mode==="normal"){
      renderBrowserConversations(unwrap(await api().browser_companion_conversations()));
    }
  }catch(err){
    el("browserCompanionState").textContent=err.message;
    el("browserCompanionState").className="error";
  }
}

function browserMessagesFingerprint(messages){
  return (messages||[]).map(item=>String(item.key||"")+":"+String(item.text||"").length+":"+String(item.text||"").slice(-48)).join("|");
}

async function refreshBrowserConversationMessages(){
  if(state.mode!=="normal"||!state.browserConversation)return;
  try{
    const messages=unwrap(await api().browser_companion_messages(state.browserConversation));
    const fingerprint=browserMessagesFingerprint(messages);
    if(fingerprint!==state.browserMessageFingerprint){
      state.browserMessageFingerprint=fingerprint;
      renderMessages(messages);
    }
  }catch(err){}
}

async function openBrowserConversation(id){
  state.browserConversation=id;
  const conversations=unwrap(await api().browser_companion_conversations());
  const current=(conversations||[]).find(item=>item.id===id);
  el("threadTitle").textContent=current?.title||"ChatGPT Web";
  const messages=unwrap(await api().browser_companion_messages(id));
  state.browserMessageFingerprint=browserMessagesFingerprint(messages);
  renderMessages(messages);
  renderBrowserConversations(conversations);
  setStatus("Conversa real do ChatGPT Web anexada ao ORDAX.","success");
}

async function sendBrowserMessage(text){
  if(!state.browserConversation){
    setStatus("Abra uma conversa no ChatGPT Web e selecione-a no ORDAX.","error");
    return false;
  }
  unwrap(await api().browser_companion_send(state.browserConversation,text));
  appendMessage("user",text);
  setStatus("Mensagem enviada ao Browser Companion…");
  return true;
}


async function refreshOrdaxAccount(){
  const card=el("ordaxAccountCard");
  if(!card)return;
  try{
    if(!api().ordax_device_status){card.classList.add("hidden");return}
    const result=await api().ordax_device_status();
    if(!result?.ok)throw new Error(result?.summary||"Falha ao verificar dispositivo ORDAX");
    const data=result.data||{};
    card.classList.remove("hidden");
    el("ordaxDeviceState").textContent=data.enrolled
      ?(data.control_plane_configured?"Dispositivo inscrito · Control Plane pronto":"Dispositivo inscrito · Control Plane pendente")
      :"Dispositivo ainda não inscrito";
    el("ordaxAccountButton").disabled=!data.enrolled||!data.control_plane_configured;
  }catch(err){
    card.classList.remove("hidden");
    el("ordaxDeviceState").textContent=err.message;
  }
}

function openOrdaxAccount(){
  el("ordaxAccountDialog").classList.remove("hidden");
  el("ordaxAccountStatus").textContent="A senha não é armazenada pelo ORDAX Dev.";
  setTimeout(()=>el("ordaxAccountEmail").focus(),0);
}

function closeOrdaxAccount(){
  el("ordaxAccountDialog").classList.add("hidden");
  el("ordaxAccountPassword").value="";
}

async function connectOrdaxAccount(){
  const email=el("ordaxAccountEmail").value.trim();
  const password=el("ordaxAccountPassword").value;
  if(!email||!password){el("ordaxAccountStatus").textContent="Informe e-mail e senha.";return}
  const button=el("ordaxAccountSubmit");
  button.disabled=true;
  el("ordaxAccountStatus").textContent="Autenticando e vinculando este computador…";
  try{
    const result=await api().connect_ordax_account(email,password);
    if(!result?.ok)throw new Error(result?.summary||"Não foi possível conectar a conta ORDAX.");
    const connectedEmail=result.data?.email||email;
    el("ordaxDeviceState").textContent="Conta vinculada · "+connectedEmail;
    el("ordaxAccountButton").textContent="Conectada";
    el("ordaxAccountStatus").textContent="Computador vinculado com segurança.";
    setStatus("Conta ORDAX conectada.","success");
    setTimeout(closeOrdaxAccount,700);
  }catch(err){
    el("ordaxAccountStatus").textContent=err.message;
    setStatus("Conta ORDAX não conectada.","error");
  }finally{
    el("ordaxAccountPassword").value="";
    button.disabled=false;
  }
}

function renderAccount(account){
  state.connected=!!account.connected;
  el("connectButton").classList.toggle("hidden",state.connected);
  const card=el("accountCard");
  card.classList.toggle("hidden",!state.connected);
  if(state.connected){
    const a=account.account||{};
    card.innerHTML="<strong>"+escapeHtml(a.name||"ChatGPT conectado")+"</strong><span>"+escapeHtml(a.email||"Plano ChatGPT")+"</span>";
  }
}

function renderProjects(projects,preferred){
  const select=el("projectSelect");select.innerHTML="";
  for(const p of projects){
    const option=document.createElement("option");option.value=p.slug;option.textContent=p.slug;select.appendChild(option);
  }
  state.project=preferred||projects[0]?.slug||null;
  if(state.project)select.value=state.project;
}

function renderModels(models){
  state.models=models||[];
  const select=el("modelSelect");select.innerHTML="";
  for(const m of state.models){
    const option=document.createElement("option");option.value=m.id;option.textContent=m.display_name||m.id;select.appendChild(option);
  }
}

function renderThreads(threads){
  const list=el("threadList");list.innerHTML="";
  for(const thread of threads||[]){
    const item=document.createElement("div");
    item.className="thread"+(thread.id===state.thread?" active":"");
    item.textContent=thread.title||"Nova conversa";
    item.onclick=()=>openThread(thread.id);
    list.appendChild(item);
  }
}

function renderMessages(messages){
  const box=el("messages");box.innerHTML="";
  if(!messages?.length){
    box.innerHTML='<div class="empty-state"><h2>Desenvolva conversando.</h2><p>Peça para analisar, implementar, testar ou continuar o projeto.</p></div>';
    return;
  }
  for(const msg of messages)appendMessage(msg.role,msg.text,false);
  box.scrollTop=box.scrollHeight;
}

function appendMessage(role,text,scroll=true){
  const box=el("messages");
  const empty=box.querySelector(".empty-state");if(empty)empty.remove();
  const div=document.createElement("div");div.className="message "+role;
  div.innerHTML='<span class="role">'+(role==="user"?"Você":"ORDAX")+'</span><div class="body"></div>';
  div.querySelector(".body").textContent=text;
  box.appendChild(div);
  if(scroll)box.scrollTop=box.scrollHeight;
  return div;
}

async function refreshThreads(){
  if(state.mode==="normal"){
    renderBrowserConversations(unwrap(await api().browser_companion_conversations()));
    return;
  }
  if(!state.project)return;
  renderThreads(unwrap(await api().threads(state.project)));
}

async function refreshActivity(){
  if(!state.project)return;
  try{
    const status=unwrap(await api().orchestrator_status(state.project));
    const panel=el("agentPanel");panel.innerHTML="";
    state.agents=status.agents||[];
    const agentSelect=el("agentSelect");agentSelect.innerHTML="";
    for(const agent of state.agents){
      const card=document.createElement("div");card.className="agent-card";
      card.innerHTML="<strong>"+escapeHtml(agent.name)+"</strong><span>"+escapeHtml(agent.role)+" · "+escapeHtml(agent.state)+"</span>";
      panel.appendChild(card);
      const option=document.createElement("option");option.value=agent.id;option.textContent=agent.name+" · "+agent.role;agentSelect.appendChild(option);
    }
    if(!(status.agents||[]).length)panel.innerHTML='<span class="muted">Nenhum agente iniciado.</span>';
    panel.insertAdjacentHTML("beforeend",
      '<div class="metric"><span>Mensagens</span><b>'+Number(status.unread_messages||0)+'</b></div>'+
      '<div class="metric"><span>Fila</span><b>'+Number((status.work_counts||{}).queued||0)+'</b></div>');
  }catch(err){el("agentPanel").innerHTML='<span class="error">'+escapeHtml(err.message)+'</span>'}
}

async function refreshCapabilities(){
  if(!state.project)return;
  try{
    const caps=unwrap(await api().capability_status(state.project));
    state.capabilities=caps||{};
    el("computerObserveToggle").checked=!!state.capabilities["computer.observe"];
    el("computerInteractToggle").checked=!!state.capabilities["computer.interact"];
    const enabled=[];
    if(state.capabilities["computer.observe"])enabled.push("ver tela");
    if(state.capabilities["computer.interact"])enabled.push("controlar");
    el("computerCapabilityState").textContent=enabled.length
      ? "Permitido neste projeto: "+enabled.join(" + ")+"."
      : "Desativado por padrão.";
    el("computerCapabilityState").className="muted";
  }catch(err){
    el("computerCapabilityState").textContent=err.message;
    el("computerCapabilityState").className="error";
  }
}

async function setComputerCapability(capability,enabled){
  if(!state.project)return;
  try{
    const data=unwrap(await api().capability_set(state.project,capability,enabled));
    state.capabilities=data.capabilities||{};
    await refreshCapabilities();
    setStatus((enabled?"Permissão ativada: ":"Permissão revogada: ")+capability,"success");
  }catch(err){
    await refreshCapabilities();
    setStatus(err.message,"error");
  }
}

async function refreshAutonomy(){
  try{
    const status=unwrap(await api().autonomy_status());
    state.autonomy=!!status.running;
    el("autonomyToggle").textContent=state.autonomy?"Parar 24/7":"Iniciar 24/7";
    const details=[];
    if(status.model)details.push(status.model);
    if((status.project_slugs||[]).length)details.push((status.project_slugs||[]).join(", "));
    if(status.completed_runs)details.push(status.completed_runs+" execução(ões)");
    if(status.last_error)details.push("erro: "+status.last_error);
    el("autonomyState").textContent=(state.autonomy?"Supervisor ativo":"Supervisor parado")+(details.length?" · "+details.join(" · "):".");
    el("autonomyState").className=status.last_error?"error":"muted";
  }catch(err){
    el("autonomyState").textContent=err.message;el("autonomyState").className="error";
  }
}

async function createAgent(){
  if(!state.project)return;
  const name=window.prompt("Nome do agente","Worker");
  if(!name)return;
  const role=window.prompt("Função do agente","implementation worker");
  if(!role)return;
  try{
    unwrap(await api().orchestrator_agent_create(state.project,name,role,null));
    await refreshActivity();
    await refreshAutonomy();
    await refreshCapabilities();
  }catch(err){setStatus(err.message,"error")}
}

async function queueWork(){
  if(!state.project)return;
  const agentId=el("agentSelect").value;
  const title=el("workTitle").value.trim();
  const instruction=el("workInstruction").value.trim();
  if(!agentId){setStatus("Crie ou selecione um agente.","error");return}
  if(!title||!instruction){setStatus("Informe título e instrução da tarefa.","error");return}
  try{
    unwrap(await api().orchestrator_work_enqueue(state.project,agentId,title,instruction,50));
    el("workTitle").value="";el("workInstruction").value="";
    await refreshActivity();
    setStatus("Tarefa adicionada à fila.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function toggleAutonomy(){
  const model=el("modelSelect").value;
  if(state.mode==="normal"){
    setStatus("Autonomia 24/7 não usa a cota do chat normal. Selecione Agent / Responses ou outro provider.","error");
    return;
  }
  if(!state.connected){setStatus("Conecte o ChatGPT primeiro.","error");return}
  if(!model){setStatus("Selecione um modelo.","error");return}
  try{
    if(state.autonomy)unwrap(await api().autonomy_stop());
    else unwrap(await api().autonomy_start(state.project,model));
    await refreshAutonomy();
    await refreshActivity();
  }catch(err){setStatus(err.message,"error")}
}

async function openThread(id){
  const data=unwrap(await api().open_thread(id));
  state.thread=id;
  el("threadTitle").textContent=data.thread.title||"Conversa";
  el("modelSelect").value=data.thread.model;
  renderMessages(data.messages);
  await refreshThreads();
  await refreshActivity();
  setStatus("Pronto · "+data.thread.project_slug);
}

async function createThread(){
  if(state.mode==="normal"){setStatus("No modo Chat normal, a conversa acontece no próprio ChatGPT.","error");return}
  if(!state.connected){setStatus("Conecte sua conta ChatGPT primeiro.","error");return}
  if(!state.project){setStatus("Selecione um projeto.","error");return}
  const model=el("modelSelect").value;
  if(!model){setStatus("Nenhum modelo disponível.","error");return}
  const thread=unwrap(await api().create_thread(state.project,model));
  await refreshThreads();await openThread(thread.id);
}

async function send(){
  if(state.busy)return;
  const input=el("composerInput");const text=input.value.trim();
  if(state.mode==="normal"){
    if(!text)return;
    state.busy=true;el("sendButton").disabled=true;input.value="";
    try{
      await sendBrowserMessage(text);
      setTimeout(()=>openBrowserConversation(state.browserConversation),1200);
    }catch(err){setStatus(err.message,"error")}
    finally{state.busy=false;el("sendButton").disabled=false;input.focus()}
    return;
  }
  if(!text)return;
  if(!state.thread){await createThread();if(!state.thread)return}
  state.busy=true;el("sendButton").disabled=true;input.value="";
  appendMessage("user",text);
  const pending=appendMessage("assistant","Trabalhando…");pending.classList.add("pending");
  setStatus("Agente executando ferramentas…");
  try{
    const result=unwrap(await api().send_message(state.thread,text));
    pending.querySelector(".body").textContent=result.text||"Concluído.";
    pending.classList.remove("pending");
    const run=el("runPanel");run.classList.remove("muted");
    run.innerHTML=
      '<div class="metric"><span>Tool calls</span><b>'+Number(result.tool_calls||0)+'</b></div>'+
      '<div class="metric"><span>Rounds</span><b>'+Number(result.model_rounds||0)+'</b></div>'+
      '<div class="metric"><span>Contexto</span><b>'+(result.session_rotated?"nova sessão":"atual")+'</b></div>';
    if(result.compaction_error){
      run.insertAdjacentHTML("beforeend",'<div class="error">Compactação: '+escapeHtml(result.compaction_error)+'</div>');
    }
    setStatus(result.session_rotated?"Concluído · contexto renovado automaticamente":"Concluído","success");
    const data=unwrap(await api().open_thread(state.thread));el("threadTitle").textContent=data.thread.title;
    await refreshThreads();await refreshActivity();
  }catch(err){
    pending.querySelector(".body").textContent="Erro: "+err.message;pending.classList.remove("pending");pending.classList.add("error");
    setStatus(err.message,"error");
  }finally{
    state.busy=false;el("sendButton").disabled=false;input.focus();
  }
}

async function connect(){
  setStatus("Abrindo login do ChatGPT…");
  try{
    const data=unwrap(await api().connect_chatgpt());
    renderAccount({connected:true,account:data.account});
    renderModels(data.models);
    setStatus("ChatGPT conectado.","success");
  }catch(err){setStatus(err.message,"error")}
}

async function bootstrap(){
  try{
    const data=unwrap(await api().bootstrap());
    renderAccount(data.account);
    renderProjects(data.projects||[],data.default_project);
    renderModels(data.models||[]);
    renderThreads(data.threads||[]);
    state.normalChat=data.chat_modes?.normal||null;
    state.webBridge=state.normalChat?.web_bridge||null;
    state.browserCompanion=state.normalChat?.browser_companion||null;
    state.managedBrowser=state.normalChat?.managed_browser||null;
    state.mode=data.chat_modes?.default||"normal";
    if(data.model_error&&state.mode==="agent")setStatus(data.model_error,"error");
    renderMode();
    renderWebBridge(state.webBridge||{});
    renderBrowserCompanion(state.browserCompanion||{});
    renderManagedChatBrowser(state.managedBrowser||{});
    await refreshBrowserCompanion();
    await refreshWebBridgeStartup();
    await refreshOrdaxAccount();
    await refreshActivity();
    await refreshAutonomy();
    await refreshCapabilities();
  }catch(err){setStatus(err.message,"error")}
}

el("ordaxAccountButton").onclick=openOrdaxAccount;
el("ordaxAccountClose").onclick=closeOrdaxAccount;
el("ordaxAccountSubmit").onclick=connectOrdaxAccount;
el("ordaxAccountDialog").onclick=e=>{if(e.target===el("ordaxAccountDialog"))closeOrdaxAccount()};
el("connectButton").onclick=connect;
el("openNormalChatButton").onclick=openNormalChat;
el("webBridgeConnectButton").onclick=connectWebBridge;
el("webBridgeStopButton").onclick=stopWebBridge;
el("webBridgeTunnelsButton").onclick=openWebBridgeTunnels;
el("webBridgeApiKeysButton").onclick=openWebBridgeApiKeys;
el("browserCompanionPairButton").onclick=pairBrowserCompanion;
el("managedChatBrowserStartButton").onclick=startManagedChatBrowser;
el("managedChatBrowserStopButton").onclick=stopManagedChatBrowser;
el("browserCompanionExtensionsButton").onclick=openBrowserCompanionExtensions;
el("browserCompanionFolderButton").onclick=openBrowserCompanionFolder;
el("webBridgeStartupButton").onclick=installWebBridgeStartup;
el("webBridgeStartupRemoveButton").onclick=uninstallWebBridgeStartup;
el("handoffCreateButton").onclick=createHandoff;
el("normalChatRolloverButton").onclick=rolloverNormalChat;
el("handoffLoadButton").onclick=loadHandoff;
el("modeSelect").onchange=async e=>{state.mode=e.target.value;state.thread=null;state.browserConversation=null;renderMode();await refreshThreads()};
el("newThreadButton").onclick=createThread;
el("sendButton").onclick=send;
el("refreshActivity").onclick=refreshActivity;
el("newAgentButton").onclick=createAgent;
el("queueWorkButton").onclick=queueWork;
el("autonomyToggle").onclick=toggleAutonomy;
el("computerObserveToggle").onchange=e=>setComputerCapability("computer.observe",e.target.checked);
el("computerInteractToggle").onchange=e=>setComputerCapability("computer.interact",e.target.checked);
el("projectSelect").onchange=async e=>{state.project=e.target.value;state.thread=null;if(state.mode!=="normal"){el("threadTitle").textContent="Nova conversa";renderMessages([])}await refreshThreads();await refreshActivity();await refreshAutonomy();await refreshCapabilities()};
el("composerInput").onkeydown=e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}};
window.addEventListener("pywebviewready",bootstrap);

setInterval(refreshBrowserConversationMessages,1200);
setInterval(()=>{if(state.mode==="normal")refreshBrowserCompanion()},5000);
