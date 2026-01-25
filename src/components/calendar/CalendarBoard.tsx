import * as React from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { CalendarDays, Pencil, Plus, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { isoDate, startOfToday } from "@/lib/date";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Card } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

import type { CalendarEvent } from "./types";
import { EventDialog } from "./EventDialog";

function byTimeThenTitle(a: CalendarEvent, b: CalendarEvent) {
  const ta = a.time ?? "";
  const tb = b.time ?? "";
  if (ta !== tb) return ta.localeCompare(tb);
  return a.title.localeCompare(b.title);
}

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export function CalendarBoard() {
  const [selected, setSelected] = React.useState<Date>(startOfToday());
  const [events, setEvents] = React.useState<CalendarEvent[]>([
    {
      id: "seed-1",
      date: isoDate(startOfToday()),
      title: "Planificar la semana",
      time: "10:00",
      notes: "Revisa prioridades y bloquea focus time.",
    },
  ]);

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);

  const dateKey = isoDate(selected);
  const dayLabel = format(selected, "EEEE d 'de' MMMM", { locale: es });

  const dayEvents = React.useMemo(
    () => events.filter((e) => e.date === dateKey).slice().sort(byTimeThenTitle),
    [events, dateKey],
  );

  const editing = React.useMemo(() => (editingId ? events.find((e) => e.id === editingId) : undefined), [events, editingId]);

  function openNew() {
    setEditingId(null);
    setDialogOpen(true);
  }

  function openEdit(id: string) {
    setEditingId(id);
    setDialogOpen(true);
  }

  function upsert(values: { title: string; time?: string; notes?: string }) {
    setEvents((prev) => {
      if (editingId) {
        return prev.map((e) => (e.id === editingId ? { ...e, ...values } : e));
      }
      return [{ id: uid(), date: dateKey, ...values }, ...prev];
    });
  }

  function remove(id: string) {
    setEvents((prev) => prev.filter((e) => e.id !== id));
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
      <Card className="border-border/70 bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60 shadow-elevate">
        <div className="flex items-center justify-between gap-3 p-5">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground shadow-glow">
              <CalendarDays className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm text-muted-foreground">Calendario</p>
              <p className="font-display text-lg leading-none">{format(selected, "MMMM yyyy", { locale: es })}</p>
            </div>
          </div>

          <Button variant="default" size="sm" onClick={openNew}>
            <Plus />
            Nuevo
          </Button>
        </div>

        <div className="px-3 pb-5">
          <Calendar
            mode="single"
            selected={selected}
            onSelect={(d) => d && setSelected(d)}
            className={cn("p-3 pointer-events-auto")}
          />
        </div>
      </Card>

      <Card className="border-border/70 bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60 shadow-elevate">
        <div className="flex flex-wrap items-end justify-between gap-3 p-5">
          <div>
            <h2 className="font-display text-2xl leading-tight">{dayLabel}</h2>
            <p className="text-sm text-muted-foreground">{dayEvents.length ? `${dayEvents.length} evento(s)` : "Sin eventos todavía"}</p>
          </div>
          <Button variant="secondary" size="sm" onClick={openNew}>
            <Plus />
            Añadir
          </Button>
        </div>

        <div className="px-5 pb-5">
          {dayEvents.length === 0 ? (
            <div className="rounded-xl border border-border/70 bg-secondary/60 p-6">
              <p className="font-medium">Tu día está limpio.</p>
              <p className="mt-1 text-sm text-muted-foreground">Crea un evento para empezar a organizarte.</p>
              <div className="mt-4">
                <Button variant="default" onClick={openNew}>
                  <Plus />
                  Crear primer evento
                </Button>
              </div>
            </div>
          ) : (
            <ul className="grid gap-3">
              {dayEvents.map((e) => (
                <li key={e.id} className="group rounded-xl border border-border/70 bg-background/60 p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        {e.time ? (
                          <span className="rounded-md bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground">
                            {e.time}
                          </span>
                        ) : (
                          <span className="rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">Sin hora</span>
                        )}
                        <p className="truncate font-medium">{e.title}</p>
                      </div>
                      {e.notes ? <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{e.notes}</p> : null}
                    </div>

                    <div className="flex shrink-0 items-center gap-1 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100">
                      <Button variant="ghost" size="icon" aria-label="Editar" onClick={() => openEdit(e.id)}>
                        <Pencil />
                      </Button>

                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" aria-label="Eliminar">
                            <Trash2 />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>¿Eliminar evento?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Se eliminará “{e.title}”. Esta acción no se puede deshacer.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancelar</AlertDialogCancel>
                            <AlertDialogAction onClick={() => remove(e.id)}>Eliminar</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>

      <EventDialog
        open={dialogOpen}
        onOpenChange={(o) => {
          setDialogOpen(o);
          if (!o) setEditingId(null);
        }}
        dateLabel={dayLabel}
        initial={editing ? { title: editing.title, time: editing.time, notes: editing.notes } : undefined}
        onSubmit={upsert}
      />
    </div>
  );
}
