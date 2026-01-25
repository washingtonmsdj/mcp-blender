import * as React from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

import type { CalendarEvent } from "./types";

const Schema = z.object({
  title: z.string().min(1, "Ponle un título"),
  time: z
    .string()
    .optional()
    .refine((v) => !v || /^([01]\d|2[0-3]):[0-5]\d$/.test(v), {
      message: "Usa formato HH:MM",
    }),
  notes: z.string().optional(),
});

type Values = z.infer<typeof Schema>;

export function EventDialog({
  open,
  onOpenChange,
  dateLabel,
  initial,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dateLabel: string;
  initial?: Pick<CalendarEvent, "title" | "time" | "notes">;
  onSubmit: (values: Values) => void;
}) {
  const form = useForm<Values>({
    resolver: zodResolver(Schema),
    defaultValues: {
      title: initial?.title ?? "",
      time: initial?.time ?? "",
      notes: initial?.notes ?? "",
    },
  });

  React.useEffect(() => {
    form.reset({
      title: initial?.title ?? "",
      time: initial?.time ?? "",
      notes: initial?.notes ?? "",
    });
  }, [initial, form, open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="font-display">{initial ? "Editar evento" : "Nuevo evento"}</DialogTitle>
          <DialogDescription>
            {dateLabel}. Añade un título y, si quieres, una hora y notas.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            className="grid gap-4"
            onSubmit={form.handleSubmit((values) => {
              onSubmit({
                ...values,
                time: values.time?.trim() ? values.time.trim() : undefined,
                notes: values.notes?.trim() ? values.notes.trim() : undefined,
              });
              onOpenChange(false);
            })}
          >
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Título</FormLabel>
                  <FormControl>
                    <Input placeholder="Ej: Reunión con Ana" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="time"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Hora (opcional)</FormLabel>
                  <FormControl>
                    <Input inputMode="numeric" placeholder="09:30" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Notas (opcional)</FormLabel>
                  <FormControl>
                    <Textarea rows={4} placeholder="Detalles, links, etc." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="gap-2 sm:gap-2">
              <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
                Cancelar
              </Button>
              <Button type="submit" variant="default">
                Guardar
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
