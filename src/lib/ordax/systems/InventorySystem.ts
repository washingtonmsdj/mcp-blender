// Inventory System
export type Item = {
  id: string;
  name: string;
  description: string;
  icon?: string;
  stackable: boolean;
  maxStack: number;
  quantity: number;
  properties?: Record<string, any>;
};

export type InventorySlot = {
  index: number;
  item: Item | null;
};

export class InventorySystem {
  private slots: InventorySlot[] = [];
  private maxSlots: number;

  constructor(maxSlots: number = 20) {
    this.maxSlots = maxSlots;
    for (let i = 0; i < maxSlots; i++) {
      this.slots.push({ index: i, item: null });
    }
  }

  addItem(item: Item): boolean {
    // Try to stack with existing item
    if (item.stackable) {
      for (const slot of this.slots) {
        if (
          slot.item &&
          slot.item.id === item.id &&
          slot.item.quantity < slot.item.maxStack
        ) {
          const space = slot.item.maxStack - slot.item.quantity;
          const toAdd = Math.min(space, item.quantity);
          slot.item.quantity += toAdd;
          item.quantity -= toAdd;

          if (item.quantity === 0) return true;
        }
      }
    }

    // Find empty slot
    const emptySlot = this.slots.find((s) => s.item === null);
    if (emptySlot) {
      emptySlot.item = { ...item };
      return true;
    }

    return false; // Inventory full
  }

  removeItem(itemId: string, quantity: number = 1): boolean {
    let remaining = quantity;

    for (const slot of this.slots) {
      if (slot.item && slot.item.id === itemId) {
        const toRemove = Math.min(remaining, slot.item.quantity);
        slot.item.quantity -= toRemove;
        remaining -= toRemove;

        if (slot.item.quantity === 0) {
          slot.item = null;
        }

        if (remaining === 0) return true;
      }
    }

    return remaining === 0;
  }

  hasItem(itemId: string, quantity: number = 1): boolean {
    let count = 0;

    for (const slot of this.slots) {
      if (slot.item && slot.item.id === itemId) {
        count += slot.item.quantity;
      }
    }

    return count >= quantity;
  }

  getItem(itemId: string): Item | null {
    for (const slot of this.slots) {
      if (slot.item && slot.item.id === itemId) {
        return slot.item;
      }
    }
    return null;
  }

  getSlots(): InventorySlot[] {
    return this.slots;
  }

  clear() {
    for (const slot of this.slots) {
      slot.item = null;
    }
  }

  moveItem(fromIndex: number, toIndex: number): boolean {
    if (fromIndex < 0 || fromIndex >= this.maxSlots) return false;
    if (toIndex < 0 || toIndex >= this.maxSlots) return false;

    const temp = this.slots[fromIndex].item;
    this.slots[fromIndex].item = this.slots[toIndex].item;
    this.slots[toIndex].item = temp;

    return true;
  }
}
