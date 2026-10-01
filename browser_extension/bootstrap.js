(() => {
  const params = new URLSearchParams(location.search);
  const code = String(params.get("code") || "").trim();
  if (!/^\d{8}$/.test(code)) {
    document.body.textContent = "Invalid ORDAX pairing code.";
    return;
  }
  chrome.runtime.sendMessage({type: "ordax.pair", code}).then(result => {
    if (result?.ok) {
      location.replace("https://chatgpt.com/");
    } else {
      document.body.textContent = "ORDAX pairing failed: " + String(result?.error || "unknown error");
    }
  }).catch(error => {
    document.body.textContent = "ORDAX pairing failed: " + String(error?.message || error);
  });
})();
