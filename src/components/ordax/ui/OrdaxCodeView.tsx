import { useMemo } from "react";

type Lang = "ts" | "json" | "md";

function escapeHtml(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;");
}

function highlight(code: string, lang: Lang) {
  // Lightweight, deterministic, no deps. Not a full parser (by design for v1).
  const raw = escapeHtml(code);

  // comments first
  let s = raw
    .replace(/(\/\/.*$)/gm, '<span class="text-code-muted">$1</span>')
    .replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="text-code-muted">$1</span>');

  // strings
  s = s.replace(/([`'"])(?:\\.|(?!\1)[^\\])*\1/g, '<span class="text-code-str">$&</span>');

  // numbers
  s = s.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="text-code-num">$1</span>');

  if (lang === "md") {
    s = s
      .replace(/^(#+\s.*)$/gm, '<span class="text-code-fn">$1</span>')
      .replace(/\*\*(.*?)\*\*/g, '<span class="text-code-key">**$1**</span>');
    return s;
  }

  // keywords
  const kw =
    lang === "json"
      ? /(\b(true|false|null)\b)/g
      : /(\b(const|let|var|type|interface|class|extends|implements|return|export|import|from|new|function|async|await|if|else|for|while|switch|case|break|continue|try|catch|throw)\b)/g;
  s = s.replace(kw, '<span class="text-code-key">$1</span>');

  // function-ish identifiers
  if (lang === "ts") {
    s = s.replace(/\b([A-Za-z_$][\w$]*)(?=\()/g, '<span class="text-code-fn">$1</span>');
  }

  return s;
}

export default function OrdaxCodeView({ code, language }: { code: string; language: Lang }) {
  const html = useMemo(() => highlight(code, language), [code, language]);
  return (
    <pre className="min-h-full bg-code-bg/65 p-3 text-sm leading-relaxed text-code-fg">
      <code
        className="block whitespace-pre"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </pre>
  );
}
