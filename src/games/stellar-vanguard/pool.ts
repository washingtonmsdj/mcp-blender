export class Pool<T extends { alive: boolean }>
{
  private items: T[] = [];
  private nextId = 1;

  constructor(private factory: (id: number) => T) {}

  spawn(init: (o: T) => void): T {
    const obj = this.items.find((x) => !x.alive) ?? this.create();
    obj.alive = true;
    init(obj);
    return obj;
  }

  all(): T[] {
    return this.items;
  }

  clear() {
    for (const it of this.items) it.alive = false;
  }

  private create() {
    const o = this.factory(this.nextId++);
    this.items.push(o);
    return o;
  }
}
