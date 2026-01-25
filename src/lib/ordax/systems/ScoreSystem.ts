// Score System
export type ScoreEvent = {
  type: string;
  points: number;
  timestamp: number;
};

export class ScoreSystem {
  private score: number = 0;
  private highScore: number = 0;
  private multiplier: number = 1;
  private combo: number = 0;
  private comboTimer: number = 0;
  private events: ScoreEvent[] = [];

  addScore(points: number, type: string = "default") {
    const finalPoints = Math.floor(points * this.multiplier);
    this.score += finalPoints;
    
    this.events.push({
      type,
      points: finalPoints,
      timestamp: Date.now(),
    });

    this.combo++;
    this.comboTimer = 2; // 2 seconds combo window

    if (this.score > this.highScore) {
      this.highScore = this.score;
      this.saveHighScore();
    }
  }

  update(dt: number) {
    if (this.comboTimer > 0) {
      this.comboTimer -= dt;
      if (this.comboTimer <= 0) {
        this.combo = 0;
        this.multiplier = 1;
      } else {
        this.multiplier = 1 + Math.floor(this.combo / 5) * 0.5;
      }
    }
  }

  getScore(): number {
    return this.score;
  }

  getHighScore(): number {
    return this.highScore;
  }

  getMultiplier(): number {
    return this.multiplier;
  }

  getCombo(): number {
    return this.combo;
  }

  reset() {
    this.score = 0;
    this.multiplier = 1;
    this.combo = 0;
    this.comboTimer = 0;
    this.events = [];
  }

  private saveHighScore() {
    localStorage.setItem("ordax_highscore", this.highScore.toString());
  }

  loadHighScore() {
    const saved = localStorage.getItem("ordax_highscore");
    if (saved) {
      this.highScore = parseInt(saved, 10);
    }
  }
}
