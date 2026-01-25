import type { UpgradeId } from "./types";

export type UpgradeDef = {
  id: UpgradeId;
  name: string;
  desc: string;
  baseCost: number;
  maxLevel: number;
};

export const UPGRADES: UpgradeDef[] = [
  { id: "double_shot", name: "Tiro Duplo", desc: "Dispara 2 projéteis paralelos.", baseCost: 35, maxLevel: 1 },
  { id: "spread", name: "Spread", desc: "Dispara leque (3 projéteis).", baseCost: 55, maxLevel: 2 },
  { id: "guided", name: "Mísseis Guiados", desc: "Projéteis levemente teleguiados.", baseCost: 65, maxLevel: 2 },
  { id: "shield", name: "Escudo", desc: "Ganha escudo permanente.", baseCost: 50, maxLevel: 3 },
  { id: "regen", name: "Regen", desc: "Regenera escudo lentamente.", baseCost: 60, maxLevel: 2 },
  { id: "fire_rate", name: "Cadência", desc: "Aumenta tiros/segundo.", baseCost: 45, maxLevel: 3 },
  { id: "special_cd", name: "Especial +", desc: "Reduz cooldown do especial.", baseCost: 55, maxLevel: 3 },
  { id: "bomb_plus", name: "Bomba +", desc: "Aumenta o número de bombas.", baseCost: 70, maxLevel: 2 },
];

export function costFor(id: UpgradeId, level: number, baseCost: number) {
  // custo cresce suavemente para manter loop de gasto
  return Math.round(baseCost * (1 + 0.55 * level));
}
