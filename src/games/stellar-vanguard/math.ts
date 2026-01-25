export const clamp = (n: number, min: number, max: number) => Math.max(min, Math.min(max, n));

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export function rand(min: number, max: number) {
  return min + Math.random() * (max - min);
}

export function aabbCircle(
  ax: number,
  ay: number,
  aw: number,
  ah: number,
  cx: number,
  cy: number,
  cr: number,
): boolean {
  // AABB center-based (ax,ay is center)
  const dx = Math.max(Math.abs(cx - ax) - aw / 2, 0);
  const dy = Math.max(Math.abs(cy - ay) - ah / 2, 0);
  return dx * dx + dy * dy <= cr * cr;
}

export function circleCircle(ax: number, ay: number, ar: number, bx: number, by: number, br: number): boolean {
  const dx = bx - ax;
  const dy = by - ay;
  const rr = ar + br;
  return dx * dx + dy * dy <= rr * rr;
}
