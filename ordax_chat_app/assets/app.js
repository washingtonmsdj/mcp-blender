const state={project:null,thread:null,models:[],connected:false,busy:false,autonomy:false,agents:[],capabilities:{},mode:"normal",normalChat:null};

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
    el("threadTitle").textContent="Chat normal via ORDAX";
    renderMessages([]);
    const endpoint=state.normalChat?.mcp_endpoint||"";
    el("normalMcpEndpoint").textContent=endpoint;
    setStatus("Modo Chat normal · usa a cota normal do ChatGPT. Abra o ChatGPT e use o plugin ORDAX.");
  }else{
    setStatus(state.connected?"Modo Agent / Responses · usa cota Work/Codex.":"Conecte o ChatGPT para usar Agent / Responses.");
  }
}

async function openNormalChat(){
  try{
    const data=unwrap(await api().open_normal_chat());
    state.normalChat=data;
    el("normalMcpEndpoint").textContent=data.mcp_endpoint||"";
    setStatus(data.opened?"ChatGPT normal aberto. Use o ORDAX pelo plugin/MCP.":"Abra o ChatGPT e use o plugin ORDAX.","success");
  }catch(err){setStatus(err.message,"error")}
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
  if(state.mode==="normal"){setStatus("No modo Chat normal, envie a mensagem na janela do ChatGPT.","error");return}
  if(state.busy)return;
  const input=el("composerInput");const text=input.value.trim();
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
    state.mode=data.chat_modes?.default||"normal";
    if(data.model_error&&state.mode==="agent")setStatus(data.model_error,"error");
    renderMode();
    await refreshActivity();
    await refreshAutonomy();
    await refreshCapabilities();
  }catch(err){setStatus(err.message,"error")}
}

el("connectButton").onclick=connect;
el("openNormalChatButton").onclick=openNormalChat;
el("modeSelect").onchange=e=>{state.mode=e.target.value;renderMode()};
el("newThreadButton").onclick=createThread;
el("sendButton").onclick=send;
el("refreshActivity").onclick=refreshActivity;
el("newAgentButton").onclick=createAgent;
el("queueWorkButton").onclick=queueWork;
el("autonomyToggle").onclick=toggleAutonomy;
el("computerObserveToggle").onchange=e=>setComputerCapability("computer.observe",e.target.checked);
el("computerInteractToggle").onchange=e=>setComputerCapability("computer.interact",e.target.checked);
el("projectSelect").onchange=async e=>{state.project=e.target.value;state.thread=null;el("threadTitle").textContent="Nova conversa";renderMessages([]);await refreshThreads();await refreshActivity();await refreshAutonomy();await refreshCapabilities()};
el("composerInput").onkeydown=e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}};
window.addEventListener("pywebviewready",bootstrap);
