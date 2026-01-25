/**
 * Compiler Session Store
 * Persistência de sessões do compilador usando Supabase
 */

export type CompilerPhase = "interpretation" | "plan" | "validation" | "confirmation" | "compilation";

export interface CompilerSessionState {
  sessionId: string;
  userId?: string;
  gameId?: string;
  phase: CompilerPhase;
  interpretationResult?: {
    gameType: string;
    mechanics: string[];
    restrictions: string[];
    objective: string;
  };
  gamePlan?: any;
  validationReport?: any;
  approvedByUser: boolean;
  createdAt: number;
  updatedAt: number;
}

export class CompilerSessionStore {
  private supabaseUrl: string;
  private supabaseKey: string;

  constructor(supabaseUrl: string, supabaseKey: string) {
    this.supabaseUrl = supabaseUrl;
    this.supabaseKey = supabaseKey;
  }

  /**
   * Carrega sessão do banco
   */
  async loadSession(sessionId: string): Promise<CompilerSessionState | null> {
    try {
      const response = await fetch(
        `${this.supabaseUrl}/rest/v1/compiler_sessions?session_id=eq.${sessionId}`,
        {
          headers: {
            apikey: this.supabaseKey,
            Authorization: `Bearer ${this.supabaseKey}`,
          },
        }
      );

      if (!response.ok) {
        console.error("Failed to load session:", response.status);
        return null;
      }

      const data = await response.json();
      if (!data || data.length === 0) return null;

      const row = data[0];
      return {
        sessionId: row.session_id,
        userId: row.user_id,
        gameId: row.game_id,
        phase: row.phase as CompilerPhase,
        interpretationResult: row.interpretation_result,
        gamePlan: row.game_plan,
        validationReport: row.validation_report,
        approvedByUser: row.approved_by_user,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      };
    } catch (error) {
      console.error("Error loading session:", error);
      return null;
    }
  }

  /**
   * Salva sessão no banco
   */
  async saveSession(session: CompilerSessionState): Promise<boolean> {
    try {
      const now = Date.now();
      const payload = {
        session_id: session.sessionId,
        user_id: session.userId,
        game_id: session.gameId,
        phase: session.phase,
        interpretation_result: session.interpretationResult,
        game_plan: session.gamePlan,
        validation_report: session.validationReport,
        approved_by_user: session.approvedByUser,
        created_at: session.createdAt || now,
        updated_at: now,
      };

      const response = await fetch(
        `${this.supabaseUrl}/rest/v1/compiler_sessions`,
        {
          method: "POST",
          headers: {
            apikey: this.supabaseKey,
            Authorization: `Bearer ${this.supabaseKey}`,
            "Content-Type": "application/json",
            Prefer: "resolution=merge-duplicates",
          },
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) {
        console.error("Failed to save session:", response.status, await response.text());
        return false;
      }

      return true;
    } catch (error) {
      console.error("Error saving session:", error);
      return false;
    }
  }

  /**
   * Atualiza sessão existente
   */
  async updateSession(
    sessionId: string,
    updates: Partial<CompilerSessionState>
  ): Promise<boolean> {
    try {
      const now = Date.now();
      const payload: any = {
        updated_at: now,
      };

      if (updates.phase !== undefined) payload.phase = updates.phase;
      if (updates.interpretationResult !== undefined)
        payload.interpretation_result = updates.interpretationResult;
      if (updates.gamePlan !== undefined) payload.game_plan = updates.gamePlan;
      if (updates.validationReport !== undefined)
        payload.validation_report = updates.validationReport;
      if (updates.approvedByUser !== undefined)
        payload.approved_by_user = updates.approvedByUser;
      if (updates.userId !== undefined) payload.user_id = updates.userId;
      if (updates.gameId !== undefined) payload.game_id = updates.gameId;

      const response = await fetch(
        `${this.supabaseUrl}/rest/v1/compiler_sessions?session_id=eq.${sessionId}`,
        {
          method: "PATCH",
          headers: {
            apikey: this.supabaseKey,
            Authorization: `Bearer ${this.supabaseKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) {
        console.error("Failed to update session:", response.status, await response.text());
        return false;
      }

      return true;
    } catch (error) {
      console.error("Error updating session:", error);
      return false;
    }
  }

  /**
   * Deleta sessão
   */
  async deleteSession(sessionId: string): Promise<boolean> {
    try {
      const response = await fetch(
        `${this.supabaseUrl}/rest/v1/compiler_sessions?session_id=eq.${sessionId}`,
        {
          method: "DELETE",
          headers: {
            apikey: this.supabaseKey,
            Authorization: `Bearer ${this.supabaseKey}`,
          },
        }
      );

      return response.ok;
    } catch (error) {
      console.error("Error deleting session:", error);
      return false;
    }
  }

  /**
   * Cria nova sessão
   */
  async createSession(
    sessionId: string,
    userId?: string,
    gameId?: string
  ): Promise<CompilerSessionState> {
    const now = Date.now();
    const session: CompilerSessionState = {
      sessionId,
      userId,
      gameId,
      phase: "interpretation",
      approvedByUser: false,
      createdAt: now,
      updatedAt: now,
    };

    await this.saveSession(session);
    return session;
  }

  /**
   * Obtém ou cria sessão
   */
  async getOrCreateSession(
    sessionId: string,
    isNewGame: boolean,
    userId?: string,
    gameId?: string
  ): Promise<CompilerSessionState> {
    const existing = await this.loadSession(sessionId);

    if (existing && !isNewGame) {
      return existing;
    }

    // Se é novo jogo, criar nova sessão
    return await this.createSession(sessionId, userId, gameId);
  }
}
