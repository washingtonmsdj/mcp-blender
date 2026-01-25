// Dialogue System
export type DialogueLine = {
  speaker: string;
  text: string;
  choices?: { text: string; next: number }[];
};

export type Dialogue = {
  id: string;
  lines: DialogueLine[];
  currentLine: number;
  active: boolean;
  onComplete?: () => void;
};

export class DialogueSystem {
  private dialogues: Map<string, Dialogue> = new Map();
  private currentDialogue: string | null = null;

  create(id: string, lines: DialogueLine[], onComplete?: () => void) {
    this.dialogues.set(id, {
      id,
      lines,
      currentLine: 0,
      active: false,
      onComplete,
    });
  }

  start(id: string) {
    const dialogue = this.dialogues.get(id);
    if (!dialogue) return;

    this.currentDialogue = id;
    dialogue.active = true;
    dialogue.currentLine = 0;
  }

  next() {
    if (!this.currentDialogue) return;

    const dialogue = this.dialogues.get(this.currentDialogue);
    if (!dialogue) return;

    dialogue.currentLine++;

    if (dialogue.currentLine >= dialogue.lines.length) {
      this.end();
    }
  }

  choose(choiceIndex: number) {
    if (!this.currentDialogue) return;

    const dialogue = this.dialogues.get(this.currentDialogue);
    if (!dialogue) return;

    const line = dialogue.lines[dialogue.currentLine];
    if (!line.choices || !line.choices[choiceIndex]) return;

    dialogue.currentLine = line.choices[choiceIndex].next;

    if (dialogue.currentLine >= dialogue.lines.length) {
      this.end();
    }
  }

  end() {
    if (!this.currentDialogue) return;

    const dialogue = this.dialogues.get(this.currentDialogue);
    if (!dialogue) return;

    dialogue.active = false;
    dialogue.onComplete?.();
    this.currentDialogue = null;
  }

  getCurrentLine(): DialogueLine | null {
    if (!this.currentDialogue) return null;

    const dialogue = this.dialogues.get(this.currentDialogue);
    if (!dialogue) return null;

    return dialogue.lines[dialogue.currentLine];
  }

  isActive(): boolean {
    return this.currentDialogue !== null;
  }
}
