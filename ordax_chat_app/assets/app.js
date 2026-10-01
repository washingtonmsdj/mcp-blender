const state={project:null,thread:null,models:[],connected:false,busy:false};

function api(){return window.pywebview.api}
function el(id){return document.getElementById(id)}
function unwrap(result){if(!result||!result.ok)throw new Error(result?.summary||"Falha no ORDAX");return result.data}
function setStatus(text,cls=""){el("statusText").textContent=text;el("statusText").className=cls}
function escapeHtml(value){return String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}

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
    for(const agent of status.agents||[]){
      const card=document.createElement("div");card.className="agent-card";
      card.innerHTML="<strong>"+escapeHtml(agent.name)+"</strong><span>"+escapeHtml(agent.role)+" · "+escapeHtml(agent.state)+"</span>";
      panel.appendChild(card);
    }
    if(!(status.agents||[]).length)panel.innerHTML='<span class="muted">Nenhum agente iniciado.</span>';
    panel.insertAdjacentHTML("beforeend",
      '<div class="metric"><span>Mensagens</span><b>'+Number(status.unread_messages||0)+'</b></div>'+
      '<div class="metric"><span>Fila</span><b>'+Number((status.work_counts||{}).queued||0)+'</b></div>');
  }catch(err){el("agentPanel").innerHTML='<span class="error">'+escapeHtml(err.message)+'</span>'}
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
    if(data.model_error)setStatus(data.model_error,"error");
    else if(!data.account.connected)setStatus("Conecte o ChatGPT para começar.");
    else setStatus("Pronto.");
    await refreshActivity();
  }catch(err){setStatus(err.message,"error")}
}

el("connectButton").onclick=connect;
el("newThreadButton").onclick=createThread;
el("sendButton").onclick=send;
el("refreshActivity").onclick=refreshActivity;
el("projectSelect").onchange=async e=>{state.project=e.target.value;state.thread=null;el("threadTitle").textContent="Nova conversa";renderMessages([]);await refreshThreads();await refreshActivity()};
el("composerInput").onkeydown=e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}};
window.addEventListener("pywebviewready",bootstrap);
