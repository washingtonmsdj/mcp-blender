// Game State System - Manages game states (START, PLAYING, GAME_OVER)
import type { OrdaxEntity } from "../types";

export type GameState = "START" | "PLAYING" | "PAUSED" | "GAME_OVER";

export type GameStateEvent = {
  from: GameState;
  to: GameState;
  timestamp: number;
};

export class GameStateSystem {
  private currentState: GameState = "START";
  private stateHistory: GameStateEvent[] = [];
  private gameStartTime: number = 0;
  private gameEndTime: number = 0;

  get current(): GameState {
    return this.currentState;
  }

  update(dt: number, entities: OrdaxEntity[]) {
    switch (this.currentState) {
      case "START":
        // Waiting for player to start
        break;

      case "PLAYING":
        this.updatePlaying(entities);
        break;

      case "PAUSED":
        // Game is paused, no updates
        break;

      case "GAME_OVER":
        // Game is over, waiting for restart
        break;
    }
  }

  private updatePlaying(entities: OrdaxEntity[]) {
    // Check lose condition: player health <= 0
    const player = entities.find((e) => e.type === "player");
    if (player && player.props) {
      const health = player.props.health || 0;
      if (health <= 0) {
        this.transitionTo("GAME_OVER");
      }
    }
  }

  // Transition to new state
  transitionTo(newState: GameState) {
    if (this.currentState === newState) return;

    const event: GameStateEvent = {
      from: this.currentState,
      to: newState,
      timestamp: Date.now(),
    };

    this.stateHistory.push(event);
    this.currentState = newState;

    // Handle state entry
    this.onStateEnter(newState);
  }

  private onStateEnter(state: GameState) {
    switch (state) {
      case "START":
        this.gameStartTime = 0;
        this.gameEndTime = 0;
        break;

      case "PLAYING":
        this.gameStartTime = Date.now();
        this.gameEndTime = 0;
        break;

      case "GAME_OVER":
        this.gameEndTime = Date.now();
        break;
    }
  }

  // Start game
  start() {
    this.transitionTo("PLAYING");
  }

  // Pause game
  pause() {
    if (this.currentState === "PLAYING") {
      this.transitionTo("PAUSED");
    }
  }

  // Resume game
  resume() {
    if (this.currentState === "PAUSED") {
      this.transitionTo("PLAYING");
    }
  }

  // Restart game
  restart(entities: OrdaxEntity[]) {
    // Reset player health
    const player = entities.find((e) => e.type === "player");
    if (player && player.props) {
      player.props.health = player.props.maxHealth || 100;
      player.x = 400;
      player.y = 300;
      player.props.vx = 0;
      player.props.vy = 0;
    }

    // Remove all enemies and bullets
    for (let i = entities.length - 1; i >= 0; i--) {
      const entity = entities[i];
      if (entity.type === "enemy" || entity.type === "bullet") {
        entities.splice(i, 1);
      }
    }

    // Reset spawners
    const spawners = entities.filter((e) => e.type === "spawner");
    for (const spawner of spawners) {
      if (spawner.props) {
        spawner.props.enemiesSpawned = 0;
        spawner.props.currentWave = 1;
      }
    }

    // Transition to START
    this.transitionTo("START");
  }

  // Get game duration
  getGameDuration(): number {
    if (this.gameStartTime === 0) return 0;
    const endTime = this.gameEndTime || Date.now();
    return (endTime - this.gameStartTime) / 1000;
  }

  // Get state history
  getStateHistory(): GameStateEvent[] {
    return [...this.stateHistory];
  }

  // Check if playing
  isPlaying(): boolean {
    return this.currentState === "PLAYING";
  }

  // Check if game over
  isGameOver(): boolean {
    return this.currentState === "GAME_OVER";
  }

  // Reset
  reset() {
    this.currentState = "START";
    this.stateHistory = [];
    this.gameStartTime = 0;
    this.gameEndTime = 0;
  }
}
