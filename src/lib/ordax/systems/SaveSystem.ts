// Save System
export type SaveData = {
  version: string;
  timestamp: number;
  data: Record<string, any>;
};

export class SaveSystem {
  private storageKey: string;
  private version: string = "1.0.0";

  constructor(gameId: string) {
    this.storageKey = `ordax_save_${gameId}`;
  }

  save(data: Record<string, any>): boolean {
    try {
      const saveData: SaveData = {
        version: this.version,
        timestamp: Date.now(),
        data,
      };

      localStorage.setItem(this.storageKey, JSON.stringify(saveData));
      return true;
    } catch (error) {
      console.error("Failed to save:", error);
      return false;
    }
  }

  load(): SaveData | null {
    try {
      const saved = localStorage.getItem(this.storageKey);
      if (!saved) return null;

      const saveData: SaveData = JSON.parse(saved);

      // Version check
      if (saveData.version !== this.version) {
        console.warn("Save version mismatch");
        // Could implement migration here
      }

      return saveData;
    } catch (error) {
      console.error("Failed to load:", error);
      return null;
    }
  }

  delete(): boolean {
    try {
      localStorage.removeItem(this.storageKey);
      return true;
    } catch (error) {
      console.error("Failed to delete save:", error);
      return false;
    }
  }

  exists(): boolean {
    return localStorage.getItem(this.storageKey) !== null;
  }

  // Auto-save functionality
  enableAutoSave(interval: number, getData: () => Record<string, any>) {
    return setInterval(() => {
      this.save(getData());
    }, interval);
  }

  disableAutoSave(intervalId: number) {
    clearInterval(intervalId);
  }

  // Export save to file
  exportToFile(filename: string = "save.json") {
    const saveData = this.load();
    if (!saveData) return;

    const blob = new Blob([JSON.stringify(saveData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Import save from file
  importFromFile(file: File): Promise<boolean> {
    return new Promise((resolve) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const saveData: SaveData = JSON.parse(e.target?.result as string);
          localStorage.setItem(this.storageKey, JSON.stringify(saveData));
          resolve(true);
        } catch (error) {
          console.error("Failed to import save:", error);
          resolve(false);
        }
      };

      reader.onerror = () => resolve(false);
      reader.readAsText(file);
    });
  }
}
