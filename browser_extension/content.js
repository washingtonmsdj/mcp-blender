(() => {
  if (window.__ORDAX_BROWSER_COMPANION__) return;
  window.__ORDAX_BROWSER_COMPANION__ = true;

  let lastFingerprint = "";
  let sending = false;

  function conversationId() {
    const match = location.pathname.match(/\/c\/([^/?#]+)/);
    return match ? match[1] : null;
  }

  function normalize(text) {
    return String(text || "").replace(/\u00a0/g, " ").replace(/[ \t]+\n/g, "\n").trim();
  }

  function roleFor(node) {
    const direct = node.getAttribute("data-message-author-role");
    if (direct === "user" || direct === "assistant") return direct;
    const author = node.querySelector("[data-message-author-role]");
    const role = author?.getAttribute("data-message-author-role");
    if (role === "user" || role === "assistant") return role;
    const testId = node.getAttribute("data-testid") || "";
    if (/user/i.test(testId)) return "user";
    if (/assistant/i.test(testId)) return "assistant";
    return null;
  }

  function textFor(node) {
    const markdown = node.matches?.(".markdown, [data-message-author-role]")
      ? node
      : (node.querySelector(".markdown, [data-message-author-role]") || node);
    return normalize(markdown.innerText || markdown.textContent || "");
  }

  function collectMessages() {
    const candidates = [
      ...document.querySelectorAll("[data-message-id]"),
      ...document.querySelectorAll("article"),
      ...document.querySelectorAll("[data-testid^='conversation-turn-']")
    ];
    const unique = [];
    const seen = new Set();
    for (const node of candidates) {
      if (!(node instanceof HTMLElement) || seen.has(node)) continue;
      seen.add(node);
      const role = roleFor(node);
      if (!role) continue;
      const text = textFor(node);
      if (!text) continue;
      const key =
        node.getAttribute("data-message-id") ||
        node.getAttribute("data-testid") ||
        node.id ||
        `${role}:${unique.length}:${text.length}:${text.slice(0, 64)}`;
      unique.push({key, role, text});
    }
    return unique.slice(-300);
  }

  function fingerprint(messages) {
    return messages.map(item => `${item.key}:${item.text.length}:${item.text.slice(-32)}`).join("|");
  }

  async function observe() {
    const id = conversationId();
    if (!id) return;
    const messages = collectMessages();
    const fp = fingerprint(messages);
    if (fp && fp !== lastFingerprint) {
      lastFingerprint = fp;
      await chrome.runtime.sendMessage({
        type: "ordax.observe",
        payload: {url: location.href, title: document.title, messages}
      }).catch(() => {});
    }
  }

  function composer() {
    return (
      document.querySelector("#prompt-textarea") ||
      document.querySelector("textarea[placeholder]") ||
      document.querySelector("[contenteditable='true'][role='textbox']")
    );
  }

  function setComposerValue(element, text) {
    element.focus();
    if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement) {
      const descriptor = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value");
      if (descriptor?.set) descriptor.set.call(element, text);
      else element.value = text;
      element.dispatchEvent(new Event("input", {bubbles: true}));
      element.dispatchEvent(new Event("change", {bubbles: true}));
      return;
    }
    element.textContent = text;
    element.dispatchEvent(new InputEvent("input", {
      bubbles: true, inputType: "insertText", data: text
    }));
  }

  function sendButton() {
    return (
      document.querySelector("button[data-testid='send-button']") ||
      document.querySelector("button[aria-label*='Send']") ||
      document.querySelector("button[aria-label*='Enviar']")
    );
  }

  async function sendCommand(command) {
    if (sending) throw new Error("another ORDAX send is in progress");
    sending = true;
    try {
      const input = composer();
      if (!input) throw new Error("ChatGPT composer not found");
      setComposerValue(input, command.text);
      await new Promise(resolve => setTimeout(resolve, 80));
      const button = sendButton();
      if (!button || button.disabled) throw new Error("ChatGPT send button is unavailable");
      button.click();
      await new Promise(resolve => setTimeout(resolve, 150));
      return true;
    } finally {
      sending = false;
    }
  }

  async function pollCommands() {
    const id = conversationId();
    const response = await chrome.runtime.sendMessage({
      type: "ordax.commands",
      conversationId: id
    }).catch(() => null);
    const commands = response?.ok && Array.isArray(response.data) ? response.data : [];
    for (const command of commands) {
      try {
        await sendCommand(command);
        await chrome.runtime.sendMessage({type: "ordax.ack", id: command.id, ok: true});
      } catch (error) {
        await chrome.runtime.sendMessage({
          type: "ordax.ack", id: command.id, ok: false,
          error: String(error?.message || error)
        });
      }
    }
  }

  const observer = new MutationObserver(() => { observe(); });
  observer.observe(document.documentElement, {subtree: true, childList: true, characterData: true});

  setInterval(() => {
    observe();
    pollCommands();
  }, 1200);

  observe();
})();
