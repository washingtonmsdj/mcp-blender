const BASE = "http://127.0.0.1:8775";
let token = null;
let browserId = null;

async function load() {
  const stored = await chrome.storage.local.get(["token", "browserId"]);
  token = typeof stored.token === "string" ? stored.token : null;
  browserId = typeof stored.browserId === "string" ? stored.browserId : null;
  if (!browserId) {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    browserId = [...bytes].map(v => v.toString(16).padStart(2, "0")).join("");
    await chrome.storage.local.set({browserId});
  }
}
const ready = load();

async function api(path, options = {}) {
  await ready;
  const headers = {"content-type": "application/json", ...(options.headers || {})};
  if (token) headers.authorization = `Bearer ${token}`;
  const response = await fetch(BASE + path, {...options, headers});
  let body = {};
  try { body = await response.json(); } catch {}
  if (!response.ok) {
    const error = new Error(body.error || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

async function pair(code) {
  await ready;
  const body = await api("/pair", {
    method: "POST",
    body: JSON.stringify({code, browser_id: browserId})
  });
  token = body.token;
  await chrome.storage.local.set({token, browserId});
  return {paired: true, browserId, protocol: body.protocol};
}

async function observe(payload) {
  if (!token) throw new Error("not_paired");
  return api("/events", {
    method: "POST",
    body: JSON.stringify({...payload, browser_id: browserId})
  });
}

async function commands(conversationId) {
  if (!token) return [];
  const body = await api("/commands", {
    headers: {"X-ORDAX-Conversation": conversationId}
  });
  return Array.isArray(body.commands) ? body.commands : [];
}

async function ack(id, ok, error = "") {
  if (!token) return;
  return api("/commands/ack", {
    method: "POST",
    body: JSON.stringify({id, ok, error})
  });
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    try {
      if (message?.type === "ordax.pair") {
        sendResponse({ok: true, data: await pair(String(message.code || ""))});
      } else if (message?.type === "ordax.status") {
        await ready;
        let reachable = false;
        try {
          const hello = await api("/hello");
          reachable = hello?.product === "ORDAX Dev Browser Companion";
        } catch {}
        sendResponse({ok: true, data: {paired: !!token, reachable, browserId}});
      } else if (message?.type === "ordax.observe") {
        sendResponse({ok: true, data: await observe(message.payload || {})});
      } else if (message?.type === "ordax.commands") {
        sendResponse({ok: true, data: await commands(String(message.conversationId || ""))});
      } else if (message?.type === "ordax.ack") {
        sendResponse({ok: true, data: await ack(String(message.id || ""), !!message.ok, String(message.error || ""))});
      } else if (message?.type === "ordax.disconnect") {
        token = null;
        await chrome.storage.local.remove("token");
        sendResponse({ok: true, data: {paired: false}});
      } else {
        sendResponse({ok: false, error: "unsupported_message"});
      }
    } catch (error) {
      if (error?.status === 401) {
        token = null;
        await chrome.storage.local.remove("token");
      }
      sendResponse({ok: false, error: String(error?.message || error)});
    }
  })();
  return true;
});
