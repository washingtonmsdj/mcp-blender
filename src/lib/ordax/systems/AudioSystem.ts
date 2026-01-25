// Audio System
export type Sound = {
  id: string;
  url: string;
  audio: HTMLAudioElement;
  volume: number;
  loop: boolean;
};

export type Music = {
  id: string;
  url: string;
  audio: HTMLAudioElement;
  volume: number;
};

export class AudioSystem {
  private sounds: Map<string, Sound> = new Map();
  private music: Map<string, Music> = new Map();
  private currentMusic: string | null = null;
  private masterVolume: number = 1.0;
  private musicVolume: number = 0.7;
  private sfxVolume: number = 1.0;

  // Load sound
  loadSound(id: string, url: string, loop: boolean = false): Promise<void> {
    return new Promise((resolve, reject) => {
      const audio = new Audio(url);
      audio.loop = loop;
      
      audio.addEventListener("canplaythrough", () => {
        this.sounds.set(id, {
          id,
          url,
          audio,
          volume: 1.0,
          loop,
        });
        resolve();
      });

      audio.addEventListener("error", () => {
        reject(new Error(`Failed to load sound: ${url}`));
      });

      audio.load();
    });
  }

  // Load music
  loadMusic(id: string, url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const audio = new Audio(url);
      audio.loop = true;
      
      audio.addEventListener("canplaythrough", () => {
        this.music.set(id, {
          id,
          url,
          audio,
          volume: 1.0,
        });
        resolve();
      });

      audio.addEventListener("error", () => {
        reject(new Error(`Failed to load music: ${url}`));
      });

      audio.load();
    });
  }

  // Play sound
  playSound(id: string, volume: number = 1.0) {
    const sound = this.sounds.get(id);
    if (!sound) return;

    const audio = sound.audio.cloneNode() as HTMLAudioElement;
    audio.volume = volume * this.sfxVolume * this.masterVolume;
    audio.play().catch((e) => console.warn("Failed to play sound:", e));
  }

  // Play music
  playMusic(id: string, fadeIn: boolean = false) {
    const music = this.music.get(id);
    if (!music) return;

    // Stop current music
    if (this.currentMusic) {
      this.stopMusic(true);
    }

    this.currentMusic = id;
    music.audio.volume = fadeIn ? 0 : music.volume * this.musicVolume * this.masterVolume;
    music.audio.play().catch((e) => console.warn("Failed to play music:", e));

    if (fadeIn) {
      this.fadeIn(music.audio, music.volume * this.musicVolume * this.masterVolume, 1000);
    }
  }

  // Stop music
  stopMusic(fadeOut: boolean = false) {
    if (!this.currentMusic) return;

    const music = this.music.get(this.currentMusic);
    if (!music) return;

    if (fadeOut) {
      this.fadeOut(music.audio, 1000, () => {
        music.audio.pause();
        music.audio.currentTime = 0;
      });
    } else {
      music.audio.pause();
      music.audio.currentTime = 0;
    }

    this.currentMusic = null;
  }

  // Pause music
  pauseMusic() {
    if (!this.currentMusic) return;

    const music = this.music.get(this.currentMusic);
    if (music) {
      music.audio.pause();
    }
  }

  // Resume music
  resumeMusic() {
    if (!this.currentMusic) return;

    const music = this.music.get(this.currentMusic);
    if (music) {
      music.audio.play().catch((e) => console.warn("Failed to resume music:", e));
    }
  }

  // Set volumes
  setMasterVolume(volume: number) {
    this.masterVolume = Math.max(0, Math.min(1, volume));
    this.updateVolumes();
  }

  setMusicVolume(volume: number) {
    this.musicVolume = Math.max(0, Math.min(1, volume));
    this.updateVolumes();
  }

  setSfxVolume(volume: number) {
    this.sfxVolume = Math.max(0, Math.min(1, volume));
  }

  private updateVolumes() {
    if (this.currentMusic) {
      const music = this.music.get(this.currentMusic);
      if (music) {
        music.audio.volume = music.volume * this.musicVolume * this.masterVolume;
      }
    }
  }

  // Fade in
  private fadeIn(audio: HTMLAudioElement, targetVolume: number, duration: number) {
    const steps = 20;
    const stepDuration = duration / steps;
    const volumeStep = targetVolume / steps;
    let currentStep = 0;

    const interval = setInterval(() => {
      currentStep++;
      audio.volume = Math.min(targetVolume, volumeStep * currentStep);

      if (currentStep >= steps) {
        clearInterval(interval);
      }
    }, stepDuration);
  }

  // Fade out
  private fadeOut(audio: HTMLAudioElement, duration: number, callback?: () => void) {
    const steps = 20;
    const stepDuration = duration / steps;
    const startVolume = audio.volume;
    const volumeStep = startVolume / steps;
    let currentStep = 0;

    const interval = setInterval(() => {
      currentStep++;
      audio.volume = Math.max(0, startVolume - volumeStep * currentStep);

      if (currentStep >= steps) {
        clearInterval(interval);
        callback?.();
      }
    }, stepDuration);
  }

  // Cleanup
  dispose() {
    this.stopMusic();
    this.sounds.clear();
    this.music.clear();
  }
}
