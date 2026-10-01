const status=document.getElementById("status");
function show(text,ok=false){status.textContent=text;status.className=ok?"ok":"bad"}
async function refresh(){
  const result=await chrome.runtime.sendMessage({type:"ordax.status"});
  if(result?.ok && result.data?.reachable){
    show(result.data.paired?"ORDAX conectado.":"ORDAX encontrado; falta parear.",!!result.data.paired);
  }else show("ORDAX Dev não encontrado em 127.0.0.1:8775.");
}
document.getElementById("pair").onclick=async()=>{
  const code=document.getElementById("code").value.trim();
  const result=await chrome.runtime.sendMessage({type:"ordax.pair",code});
  if(result?.ok){show("Pareado com sucesso.",true);document.getElementById("code").value=""}
  else show(result?.error||"Falha no pareamento.");
};
document.getElementById("disconnect").onclick=async()=>{
  await chrome.runtime.sendMessage({type:"ordax.disconnect"});
  show("Desconectado.");
};
refresh();
