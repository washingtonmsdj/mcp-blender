from __future__ import annotations

import json
import os
import webbrowser

import webview

from .openai_tunnel import OpenAITunnelManager

PLATFORM_TUNNELS_URL = "https://platform.openai.com/settings/organization/tunnels"
PLATFORM_KEYS_URL = "https://platform.openai.com/settings/organization/api-keys"
CHATGPT_CONNECTORS_URL = "https://chatgpt.com/#settings/Connectors"


class OpenAITunnelApi:
    def __init__(self):
        self.manager = OpenAITunnelManager()

    def status(self) -> dict:
        return {"ok": True, "data": self.manager.status()}

    def connect(self, tunnel_id: str, runtime_api_key: str) -> dict:
        try:
            data = self.manager.setup(tunnel_id, runtime_api_key)
            return {"ok": True, "summary": "ChatGPT conectado ao ORDAX Studio", "data": data}
        except Exception as error:
            return {"ok": False, "summary": str(error), "data": {}}

    def open_tunnels(self) -> dict:
        webbrowser.open(PLATFORM_TUNNELS_URL)
        return {"ok": True}

    def open_api_keys(self) -> dict:
        webbrowser.open(PLATFORM_KEYS_URL)
        return {"ok": True}

    def open_chatgpt_connectors(self) -> dict:
        webbrowser.open(CHATGPT_CONNECTORS_URL)
        return {"ok": True}


HTML = r"""
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ORDAX Studio — Conectar ChatGPT</title>
<style>
:root{color-scheme:dark;font-family:Inter,system-ui,Segoe UI,sans-serif;background:#080f19;color:#e2ebf7}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 20% 0,#142640 0,#080f19 46%,#050a11 100%)}
.shell{width:min(720px,calc(100vw - 32px));padding:34px;border:1px solid #243249;border-radius:24px;background:#0b1523;box-shadow:0 30px 90px #0008}
.eyebrow{font-size:12px;letter-spacing:.18em;color:#8e9db4}.title{font-size:30px;font-weight:420;margin:10px 0 8px}.lead{color:#9eacc0;line-height:1.55;margin:0 0 26px}
.status{display:flex;gap:10px;align-items:center;padding:14px 16px;border:1px solid #243249;border-radius:14px;background:#111e30;margin-bottom:22px}.dot{width:9px;height:9px;border-radius:50%;background:#66758a}.dot.ok{background:#91d5b4}.dot.warn{background:#e4c98f}
label{display:block;font-size:12px;color:#9ba9bd;margin:14px 0 7px}.input{width:100%;padding:13px 14px;border:1px solid #2c3c55;border-radius:12px;background:#080f19;color:#e2ebf7;outline:none}.input:focus{border-color:#6d8fbf}
.row{display:flex;gap:12px;margin-top:18px;flex-wrap:wrap}.btn{border:1px solid #31435e;background:#111e30;color:#dce8f8;border-radius:11px;padding:11px 15px;cursor:pointer}.btn.primary{background:#d1e4ff;color:#172b47;border-color:#d1e4ff}.btn:disabled{opacity:.5;cursor:not-allowed}
.help{margin-top:22px;padding-top:18px;border-top:1px solid #1f2c3f;color:#8392a8;font-size:12px;line-height:1.55}.msg{min-height:22px;margin-top:14px;font-size:13px;color:#9fb5d2}.msg.error{color:#f0a9a9}.security{margin-top:20px;border-left:3px solid #496c98;padding:10px 14px;color:#9fb0c6;font-size:12px;line-height:1.5;background:#0a1320}
</style>
</head>
<body>
<div class="shell">
  <div class="eyebrow">ORDAX STUDIO · CHATGPT</div>
  <div class="title">Conectar esta estação</div>
  <p class="lead">Configure uma vez. Depois o ORDAX mantém o Secure MCP Tunnel ativo no login do Windows e o ChatGPT acessa somente as ferramentas MCP autorizadas.</p>
  <div class="status"><span id="dot" class="dot"></span><div><div id="statusTitle">Verificando…</div><div id="statusMeta" style="font-size:12px;color:#8493a8;margin-top:3px"></div></div></div>
  <label for="tunnel">Tunnel ID</label>
  <input id="tunnel" class="input" autocomplete="off" placeholder="tunnel_0123456789abcdef…">
  <label for="key">Runtime API key</label>
  <input id="key" class="input" type="password" autocomplete="new-password" placeholder="A chave não será salva em texto puro">
  <div class="row">
    <button id="connect" class="btn primary" onclick="connectOrdax()">Conectar ChatGPT</button>
    <button class="btn" onclick="pywebview.api.open_tunnels()">Abrir Tunnels</button>
    <button class="btn" onclick="pywebview.api.open_api_keys()">Abrir API Keys</button>
    <button class="btn" onclick="pywebview.api.open_chatgpt_connectors()">Abrir Connectors</button>
  </div>
  <div id="message" class="msg"></div>
  <div class="security">A runtime API key é protegida com DPAPI do Windows e não é gravada em configuração, logs ou repositório. O túnel é outbound-only; nenhuma porta de entrada é aberta no PC.</div>
  <div class="help">Use o mesmo <b>Tunnel ID</b> criado no OpenAI Platform e selecionado no conector do ChatGPT. O ORDAX fixa e verifica o SHA-256 do binário oficial antes da instalação.</div>
</div>
<script>
const el=id=>document.getElementById(id);
async function refreshStatus(){
  const result=await pywebview.api.status(); const s=result.data||{};
  el('tunnel').value=s.tunnel_id||el('tunnel').value||'';
  const ready=!!(s.configured&&s.task_installed&&s.runtime_running);
  const partial=!!s.configured;
  el('dot').className='dot '+(ready?'ok':partial?'warn':'');
  el('statusTitle').textContent=ready?'Conectado e ativo':partial?'Configurado — iniciando/recuperando':'Ainda não configurado';
  el('statusMeta').textContent=s.tunnel_id?`${s.tunnel_id} · ${s.client_version||''}`:'Secure MCP Tunnel não configurado';
}
async function connectOrdax(){
  const tunnel=el('tunnel').value.trim(), key=el('key').value.trim(), button=el('connect'), msg=el('message');
  msg.className='msg'; msg.textContent='Validando binário oficial, perfil e conexão…'; button.disabled=true;
  try{
    const result=await pywebview.api.connect(tunnel,key); el('key').value='';
    if(!result.ok){throw new Error(result.summary||'Falha na configuração');}
    msg.textContent=result.summary||'Configuração concluída'; await refreshStatus();
  }catch(error){el('key').value='';msg.className='msg error';msg.textContent=error.message||String(error);}
  finally{button.disabled=false;}
}
window.addEventListener('pywebviewready',refreshStatus);
</script>
</body>
</html>
"""


def main() -> None:
    if os.name != "nt":
        raise SystemExit("ORDAX ChatGPT connector setup is supported on Windows only")
    api = OpenAITunnelApi()
    webview.create_window(
        "ORDAX Studio — Conectar ChatGPT",
        html=HTML,
        js_api=api,
        width=780,
        height=720,
        min_size=(660, 620),
        background_color="#080f19",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
