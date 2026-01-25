import { useEffect, useRef } from "react";
import { toast } from "sonner";

type Props = {
  value: string;
  language: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
};

export function CodeEditor({ value, language, onChange, readOnly = false }: Props) {
  const editorRef = useRef<HTMLDivElement>(null);
  const monacoRef = useRef<any>(null);

  useEffect(() => {
    // Monaco Editor will be loaded via CDN
    // For now, use a simple textarea
    // In production, integrate @monaco-editor/react
  }, []);

  return (
    <div className="h-full w-full bg-[#1e1e1e] rounded-lg overflow-hidden">
      <textarea
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        readOnly={readOnly}
        className="w-full h-full p-4 bg-[#1e1e1e] text-white font-mono text-sm resize-none border-none outline-none"
        style={{
          tabSize: 2,
          fontFamily: "JetBrains Mono, Consolas, Monaco, monospace",
        }}
        spellCheck={false}
      />
    </div>
  );
}
