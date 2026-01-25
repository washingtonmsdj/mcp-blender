-- Tabela de sessões do compilador
CREATE TABLE IF NOT EXISTS compiler_sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT,
  game_id TEXT,
  phase TEXT NOT NULL CHECK (phase IN ('interpretation', 'plan', 'validation', 'confirmation', 'compilation')),
  interpretation_result JSONB,
  game_plan JSONB,
  validation_report JSONB,
  approved_by_user BOOLEAN NOT NULL DEFAULT FALSE,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_compiler_sessions_user_id ON compiler_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_compiler_sessions_game_id ON compiler_sessions(game_id);
CREATE INDEX IF NOT EXISTS idx_compiler_sessions_updated_at ON compiler_sessions(updated_at);

-- Limpar sessões antigas (mais de 7 dias)
CREATE OR REPLACE FUNCTION cleanup_old_compiler_sessions()
RETURNS void AS $$
BEGIN
  DELETE FROM compiler_sessions
  WHERE updated_at < EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days') * 1000;
END;
$$ LANGUAGE plpgsql;
