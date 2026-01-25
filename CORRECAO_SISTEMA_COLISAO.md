# Correção do Sistema de Colisão

## Problema Identificado

O `CollisionSystem` estava **implementado mas não integrado** no `OrdaxCanvas.tsx`:

1. ❌ Sistema de colisão existia mas nunca era instanciado
2. ❌ Nenhuma detecção de colisão entre player e inimigos/asteroides
3. ❌ Objetos passavam através do player sem efeito

## Solução Implementada

### 1. Integração do CollisionSystem no Canvas

```typescript
// Importado o sistema
import { CollisionSystem } from "@/lib/ordax/systems/CollisionSystem";

// Criado ref para instância do sistema
const collisionSystemRef = useRef<CollisionSystem>(new CollisionSystem());

// Verificação se o jogo usa colisão
const hasCollisionSystem = spec.systems.includes("CollisionSystem");
```

### 2. Callbacks de Colisão Configurados

```typescript
// Player vs Enemy
collision.on("player", "enemy", (player, enemy) => {
  const spawned = spawnedRef.current.find(s => s.id === enemy.id);
  if (spawned && !spawned.dead) {
    spawned.dead = true;
    toast.error("💥 Colisão! Game Over");
  }
});

// Player vs Asteroid
collision.on("player", "asteroid", (player, asteroid) => {
  const spawned = spawnedRef.current.find(s => s.id === asteroid.id);
  if (spawned && !spawned.dead) {
    spawned.dead = true;
    toast.error("💥 Colisão com asteroide!");
  }
});
```

### 3. Detecção Ativa no Loop de Jogo

```typescript
// A cada frame, verifica colisões
if (running && hasCollisionSystem && p && initialPlayer) {
  const allEntities: OrdaxEntity[] = [
    { ...initialPlayer, x: p.x, y: p.y, type: "player" },
    ...spawnedRef.current.map(s => ({
      id: s.id,
      type: s.type,
      x: s.x,
      y: s.y,
      w: s.w,
      h: s.h,
    }))
  ];
  collisionSystemRef.current.update(allEntities);
}
```

### 4. Melhorias Visuais

- ✅ Objetos colididos são marcados como `dead` e removidos
- ✅ Toast notification quando há colisão
- ✅ Indicador visual no HUD: "✓ Collision System Active"
- ✅ Suporte para diferentes tipos (enemy, asteroid)

## Como Funciona

### Algoritmo AABB (Axis-Aligned Bounding Box)

O sistema usa detecção de colisão retangular:

```typescript
// Verifica se dois retângulos se sobrepõem
a.x - a.w/2 < b.x + b.w/2 &&
a.x + a.w/2 > b.x - b.w/2 &&
a.y - a.h/2 < b.y + b.h/2 &&
a.y + a.h/2 > b.y - b.h/2
```

### Fluxo de Colisão

1. **Update Loop**: A cada frame, `collisionSystemRef.current.update(allEntities)` é chamado
2. **Detecção**: Sistema verifica todas as entidades contra todas (O(n²))
3. **Callback**: Quando colisão detectada, chama callbacks registrados
4. **Resposta**: Callback marca objeto como `dead` e mostra toast
5. **Limpeza**: Objetos mortos são filtrados no próximo frame

## Tipos de Colisão Suportados

- `player` vs `enemy` - Colisão fatal
- `player` vs `asteroid` - Colisão com asteroide
- Extensível para outros tipos (bullet vs enemy, etc.)

## Testando

1. Acesse: http://localhost:8082/workspace
2. Gere um jogo de nave (ex: "jogo de nave espacial com asteroides")
3. Verifique no HUD: "✓ Collision System Active"
4. Mova a nave com WASD/Arrows
5. Colida com um asteroide → Toast "💥 Colisão com asteroide!"
6. Asteroide desaparece após colisão

## Próximas Melhorias (Opcional)

- [ ] Sistema de vidas (3 colisões antes de game over)
- [ ] Partículas de explosão na colisão
- [ ] Som de colisão (AudioSystem)
- [ ] Invencibilidade temporária após colisão
- [ ] Colisão de projéteis (bullet vs enemy)
- [ ] Score ao destruir inimigos
