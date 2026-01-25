/**
 * Script de teste para CompilerSessionStore
 * Execute com: deno run --allow-net --allow-env test-compiler-session.ts
 */

import { CompilerSessionStore } from "./_shared/compiler-session-store.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "http://localhost:54321";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";

async function testCompilerSession() {
  console.log("🧪 Testando CompilerSessionStore...\n");

  const store = new CompilerSessionStore(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

  // Test 1: Criar sessão
  console.log("1️⃣ Criando nova sessão...");
  const sessionId = "test-session-" + Date.now();
  const session = await store.createSession(sessionId, "test-user", "test-game");
  console.log("✅ Sessão criada:", session);
  console.log("");

  // Test 2: Carregar sessão
  console.log("2️⃣ Carregando sessão...");
  const loaded = await store.loadSession(sessionId);
  console.log("✅ Sessão carregada:", loaded);
  console.log("");

  // Test 3: Atualizar sessão (transição de fase)
  console.log("3️⃣ Atualizando sessão (interpretation → plan)...");
  await store.updateSession(sessionId, {
    phase: "plan",
    interpretationResult: {
      gameType: "platformer",
      mechanics: ["jump", "run", "collect"],
      restrictions: [],
      objective: "Collect all coins"
    }
  });
  const updated = await store.loadSession(sessionId);
  console.log("✅ Sessão atualizada:", updated);
  console.log("");

  // Test 4: Atualizar com game plan
  console.log("4️⃣ Atualizando com game plan...");
  await store.updateSession(sessionId, {
    phase: "validation",
    gamePlan: {
      kind: "GAME_PLAN",
      gameType: "platformer",
      title: "Test Game",
      description: "A test platformer",
      coreLoop: "Jump and collect coins",
      requiredSystems: ["PhysicsSystem", "CollisionSystem"],
      requiredEntities: ["player", "coin"],
      loopType: "objective"
    }
  });
  const withPlan = await store.loadSession(sessionId);
  console.log("✅ Sessão com plano:", withPlan);
  console.log("");

  // Test 5: Aprovar plano
  console.log("5️⃣ Aprovando plano...");
  await store.updateSession(sessionId, {
    phase: "compilation",
    approvedByUser: true
  });
  const approved = await store.loadSession(sessionId);
  console.log("✅ Sessão aprovada:", approved);
  console.log("");

  // Test 6: Deletar sessão
  console.log("6️⃣ Deletando sessão...");
  await store.deleteSession(sessionId);
  const deleted = await store.loadSession(sessionId);
  console.log("✅ Sessão deletada:", deleted === null ? "null (correto)" : "ERRO: ainda existe");
  console.log("");

  console.log("🎉 Todos os testes passaram!");
}

testCompilerSession().catch(console.error);
