# 🚀 FASE 5 - GUIA RÁPIDO DE USO

## TL;DR

Adicione **game feel** ao seu jogo com 2 linhas:

```typescript
const juice = new JuiceSystem();
const audio = new AudioSystem();

// No update
juice.update(dt, entities, score, gameState);

// No render
juice.render(ctx, entities);
juice.renderUIEffects(ctx, entities, score);
```

---

## 🎨 JUICE SYSTEM

### Setup Básico

```typescript
import { JuiceSystem } from '@/lib/ordax/systems';

const juice = new JuiceSystem();

// Update (automático)
juice.update(dt, entities, scoreSystem, gameState.current);

// Render (automático)
juice.render(ctx, entities);
juice.renderUIEffects(ctx, entities, scoreSystem);
```

### Efeitos Automáticos

JuiceSystem detecta automaticamente:
- ✅ **Dano** - Flash branco + knockback
- ✅ **Morte** - Partículas coloridas
- ✅ **Score** - Animação de +pontos
- ✅ **Game Over** - Fade suave

### Efeitos Manuais

```typescript
// Recoil ao atirar
juice.addShootRecoil(player);

// Morte com partículas
juice.addDeathEffect(enemy);

// Screen shake
juice.addScreenShake(intensity, duration);

// Flash em entidade
juice.addFlashEffect(entity);

// Partículas customizadas
juice.addParticleEffect(x, y, color, count);

// Knockback
juice.addKnockback(entity, force);
```

---

## 🔊 AUDIO SYSTEM

### Setup Básico

```typescript
import { AudioSystem } from '@/lib/ordax/systems';

const audio = new AudioSystem();

// Opcional: Carregar sons
audio.loadSound('shoot', 'laser.mp3');
audio.loadSound('hit', 'hit.mp3');
audio.loadSound('death', 'explosion.mp3');

// Play (com fallback automático)
audio.playShootSound(); // Toca arquivo ou beep
audio.playHitSound();
audio.playDeathSound();
audio.playGameOverSound();
```

### Controles de Volume

```typescript
// Master volume (0-1)
audio.setMasterVolume(0.7);

// SFX volume (0-1)
audio.setSFXVolume(0.8);

// Music volume (0-1)
audio.setMusicVolume(0.5);

// Mute/unmute
audio.setMuted(true);
```

### Beeps Sintéticos

Se não carregar arquivos, usa beeps:
- **Shoot:** 800Hz, 0.05s
- **Hit:** 300Hz, 0.1s
- **Death:** 200Hz, 0.3s
- **Game Over:** 150Hz, 0.5s

---

## 🎮 INTEGRAÇÃO COMPLETA

```typescript
// 1. Criar sistemas
const juice = new JuiceSystem();
const audio = new AudioSystem();

// 2. Setup collision handlers
collision.on('bullet', 'enemy', (bullet, enemy) => {
  combat.handleCollisionDamage(bullet, enemy);
  score.addScore(10);
  
  // Juice!
  juice.addFlashEffect(enemy);
  audio.playHitSound();
});

collision.on('enemy', 'player', (enemy, player) => {
  combat.handleCollisionDamage(enemy, player);
  
  // Juice!
  juice.addKnockback(player, 50);
  juice.addScreenShake(5, 0.15);
  audio.playHitSound();
});

// 3. Update loop
function update(dt) {
  // ... outros sistemas
  
  juice.update(dt, entities, score, gameState.current);
  
  // Detectar tiros
  const bullets = entities.filter(e => e.type === 'bullet' && e.props?._justCreated);
  if (bullets.length > 0) {
    const player = entities.find(e => e.type === 'player');
    juice.addShootRecoil(player);
    audio.playShootSound();
    bullets.forEach(b => delete b.props._justCreated);
  }
  
  // Detectar mortes
  const dead = entities.filter(e => e.props?._justDied);
  dead.forEach(e => {
    juice.addDeathEffect(e);
    audio.playDeathSound();
  });
}

// 4. Render loop
function render(ctx) {
  // Clear
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, 800, 600);
  
  // Entities
  for (const entity of entities) {
    if (entity.type === 'ui' || entity.type === 'controls') continue;
    ctx.fillStyle = entity.props?.color || '#fff';
    ctx.fillRect(entity.x - entity.w/2, entity.y - entity.h/2, entity.w, entity.h);
  }
  
  // Juice effects
  juice.render(ctx, entities);
  
  // UI
  ui.render(ctx, gameState.current, entities, score, timer);
  
  // UI effects
  juice.renderUIEffects(ctx, entities, score);
}
```

---

## 🎯 EFEITOS DISPONÍVEIS

### Visual

| Efeito | Trigger | Duração | Intensidade |
|--------|---------|---------|-------------|
| Flash | Dano | 0.1s | Branco 70% |
| Particles | Morte | 0.5s | 8-12 partículas |
| Screen Shake | Tiro/Hit/Morte | 0.05-0.3s | 2-10px |
| Health Blink | Dano | 0.2s | Vermelho 30% |
| Score Anim | +Pontos | 0.5s | Scale 1.2x |
| Game Over Fade | Game Over | 0.5s | Alpha 0.8 |

### Auditivo

| Som | Frequência | Duração | Trigger |
|-----|-----------|---------|---------|
| Shoot | 800Hz | 0.05s | Atirar |
| Hit | 300Hz | 0.1s | Colisão |
| Death | 200Hz | 0.3s | Morte |
| Game Over | 150Hz | 0.5s | Game Over |

---

## 🔧 CUSTOMIZAÇÃO

### Ajustar Intensidade

```typescript
// Screen shake mais forte
juice.addScreenShake(15, 0.5); // Default: 5, 0.15

// Mais partículas
juice.addParticleEffect(x, y, color, 20); // Default: 8

// Knockback mais forte
juice.addKnockback(entity, 100); // Default: 50
```

### Ajustar Suavidade

```typescript
// Em JuiceSystem.ts, linha ~80
const lerpFactor = 0.15; // Menor = mais suave, maior = mais snappy
```

### Ajustar Bounds

```typescript
// Em JuiceSystem.ts, linha ~100
const bounds = { 
  width: 800, 
  height: 600, 
  padding: 20 // Distância da borda
};
```

---

## 🐛 TROUBLESHOOTING

### Efeitos não aparecem
```typescript
// Certifique-se de chamar render
juice.render(ctx, entities);
juice.renderUIEffects(ctx, entities, score);
```

### Áudio não toca
```typescript
// Normal! AudioContext precisa de interação do usuário
// Adicione um botão "Start" que chama:
audio.playBeep(440, 0.1); // Ativa AudioContext
```

### Movimento muito suave/robótico
```typescript
// Ajuste lerpFactor em JuiceSystem.ts
const lerpFactor = 0.15; // Padrão
const lerpFactor = 0.05; // Mais suave
const lerpFactor = 0.30; // Mais snappy
```

### Screen shake muito forte
```typescript
// Reduza intensidade
juice.addScreenShake(2, 0.1); // Sutil
juice.addScreenShake(5, 0.15); // Médio (padrão)
juice.addScreenShake(10, 0.3); // Forte
```

---

## 📊 COMPARAÇÃO

### Sem Juice (Fase 4)
```typescript
// Update
physics.update(dt, entities);
collision.update(entities);
combat.update(dt, entities);

// Render
for (const entity of entities) {
  ctx.fillRect(entity.x, entity.y, entity.w, entity.h);
}
```

### Com Juice (Fase 5)
```typescript
// Update
physics.update(dt, entities);
collision.update(entities);
combat.update(dt, entities);
juice.update(dt, entities, score, gameState); // +1 linha

// Render
for (const entity of entities) {
  ctx.fillRect(entity.x, entity.y, entity.w, entity.h);
}
juice.render(ctx, entities); // +1 linha
juice.renderUIEffects(ctx, entities, score); // +1 linha
```

**Resultado:** +3 linhas = Game feel profissional!

---

## ✅ CHECKLIST DE INTEGRAÇÃO

- [ ] Importar `JuiceSystem` e `AudioSystem`
- [ ] Criar instâncias
- [ ] Chamar `juice.update()` no game loop
- [ ] Chamar `juice.render()` no render loop
- [ ] Chamar `juice.renderUIEffects()` no render loop
- [ ] Adicionar `audio.playShootSound()` ao atirar
- [ ] Adicionar `audio.playHitSound()` em colisões
- [ ] Adicionar `audio.playDeathSound()` em mortes
- [ ] Testar e ajustar intensidades

---

## 🎯 RESULTADO ESPERADO

Após integração:
- ✅ Movimento suave e natural
- ✅ Feedback visual em todas ações
- ✅ Feedback auditivo funcional
- ✅ Jogo parece vivo
- ✅ Nenhum contrato quebrado
- ✅ Todos testes passando

**Tempo de integração:** ~5 minutos  
**Impacto no game feel:** 🚀 Enorme!
