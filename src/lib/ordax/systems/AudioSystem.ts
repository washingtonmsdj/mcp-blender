// Audio System - Sound effects and music (with fallback)
export type Sound = {
  id: string;
  src: string;
  volume: number;
  loop: boolean;
};

export type Music = {
  id: string;
  src: string;
  volume: number;
  loop: boolean;
};

export class AudioSystem {
  private sounds: Map<string, HTMLAudioElement> = new Map();
  private music: Map<string, HTMLAudioElement> = new Map();
  private masterVolume: number = 0.7;
  private sfxVolume: number = 0.8;
  private musicVolume: number = 0.5;
  private muted: boolean = false;
  private audioContext: AudioContext | null = null;
  private audioContextAttempted: boolean = false;

  constructor() {
    // Defer AudioContext creation until first use
    this.audioContextAttempted = false;
  }

  private ensureAudioContext() {
    if (this.audioContextAttempted) return;
    this.audioContextAttempted = true;

    // Try to create audio context (may fail in some browsers)
    try {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    } catch (e) {
      // Only log once
      console.warn("AudioContext not available, audio will be silent");
    }
  }

  // Load sound
  loadSound(id: string, src: string, volume: number = 1.0) {
    this.ensureAudioContext();
    try {
      const audio = new Audio(src);
      audio.volume = volume * this.sfxVolume * this.masterVolume;
      this.sounds.set(id, audio);
    } catch (e) {
      // Silently fail - audio is optional
    }
  }

  // Load music
  loadMusic(id: string, src: string, volume: number = 1.0, loop: boolean = true) {
    this.ensureAudioContext();
    try {
      const audio = new Audio(src);
      audio.volume = volume * this.musicVolume * this.masterVolume;
      audio.loop = loop;
      this.music.set(id, audio);
    } catch (e) {
      // Silently fail - audio is optional
    }
  }

  // Play sound
  playSound(id: string, volume: number = 1.0) {
    if (this.muted) return;

    const sound = this.sounds.get(id);
    if (sound) {
      try {
        sound.currentTime = 0;
        sound.volume = volume * this.sfxVolume * this.masterVolume;
        sound.play().catch(() => {
          // Silently fail - user may not have interacted with page yet
        });
      } catch (e) {
        // Silently fail
      }
    }
  }

  // Play music
  playMusic(id: string) {
    if (this.muted) return;

    const music = this.music.get(id);
    if (music) {
      try {
        music.play().catch(() => {
          // Silently fail
        });
      } catch (e) {
        // Silently fail
      }
    }
  }

  // Stop music
  stopMusic(id: string) {
    const music = this.music.get(id);
    if (music) {
      try {
        music.pause();
        music.currentTime = 0;
      } catch (e) {
        // Silently fail
      }
    }
  }

  // Set master volume
  setMasterVolume(volume: number) {
    this.masterVolume = Math.max(0, Math.min(1, volume));
    this.updateAllVolumes();
  }

  // Set SFX volume
  setSFXVolume(volume: number) {
    this.sfxVolume = Math.max(0, Math.min(1, volume));
    this.updateAllVolumes();
  }

  // Set music volume
  setMusicVolume(volume: number) {
    this.musicVolume = Math.max(0, Math.min(1, volume));
    this.updateAllVolumes();
  }

  // Mute/unmute
  setMuted(muted: boolean) {
    this.muted = muted;
    if (muted) {
      this.sounds.forEach((sound) => (sound.volume = 0));
      this.music.forEach((music) => (music.volume = 0));
    } else {
      this.updateAllVolumes();
    }
  }

  private updateAllVolumes() {
    this.sounds.forEach((sound) => {
      sound.volume = this.sfxVolume * this.masterVolume;
    });
    this.music.forEach((music) => {
      music.volume = this.musicVolume * this.masterVolume;
    });
  }

  // Generate simple beep sound (fallback when no audio files)
  playBeep(frequency: number = 440, duration: number = 0.1) {
    if (this.muted || !this.audioContext) return;

    try {
      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      oscillator.frequency.value = frequency;
      oscillator.type = "square";

      gainNode.gain.setValueAtTime(this.sfxVolume * this.masterVolume * 0.1, this.audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);

      oscillator.start(this.audioContext.currentTime);
      oscillator.stop(this.audioContext.currentTime + duration);
    } catch (e) {
      // Silently fail
    }
  }

  // Convenience methods with fallback beeps
  playShootSound() {
    this.playSound("shoot");
    if (!this.sounds.has("shoot")) {
      this.playBeep(800, 0.05);
    }
  }

  playHitSound() {
    this.playSound("hit");
    if (!this.sounds.has("hit")) {
      this.playBeep(300, 0.1);
    }
  }

  playDeathSound() {
    this.playSound("death");
    if (!this.sounds.has("death")) {
      this.playBeep(200, 0.3);
    }
  }

  playGameOverSound() {
    this.playSound("gameOver");
    if (!this.sounds.has("gameOver")) {
      this.playBeep(150, 0.5);
    }
  }

  // Clear all
  clear() {
    this.sounds.forEach((sound) => {
      sound.pause();
      sound.currentTime = 0;
    });
    this.music.forEach((music) => {
      music.pause();
      music.currentTime = 0;
    });
    this.sounds.clear();
    this.music.clear();
  }
}
