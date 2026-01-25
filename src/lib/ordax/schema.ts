import { z } from "zod";
import type { OrdaxSpec } from "@/lib/ordax/types";

export const ordaxGameTypeSchema = z.enum(["platformer", "topdown", "shooter", "puzzle", "racing", "sports", "unknown"]);

export const ordaxEntitySchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1),
  x: z.number(),
  y: z.number(),
  w: z.number().positive(),
  h: z.number().positive(),
  props: z.record(z.unknown()).optional(),
});

const ordaxVisualThemeSchema = z
  .object({
    background: z.string().min(1).optional(),
    primary: z.string().min(1).optional(),
    accent: z.string().min(1).optional(),
    font: z.string().min(1).optional(),
  })
  .optional();

const ordaxBackgroundLayerSchema = z.object({
  type: z.enum(["starfield", "gradient", "nebula", "solid"]),
  parallax: z.number().min(0).max(1).optional(),
  density: z.number().min(0).optional(),
  speedY: z.number().optional(),
});

const ordaxBackgroundSchema = z
  .object({
    layers: z.array(ordaxBackgroundLayerSchema).min(1),
  })
  .optional();

const ordaxAudioSchema = z
  .object({
    music: z.string().min(1).optional(),
    sounds: z
      .object({
        collision: z.string().min(1).optional(),
        score: z.string().min(1).optional(),
        gameOver: z.string().min(1).optional(),
        jump: z.string().min(1).optional(),
        shoot: z.string().min(1).optional(),
      })
      .optional(),
  })
  .optional();

export const ordaxSpecSchema: z.ZodType<OrdaxSpec> = z.object({
  gameType: ordaxGameTypeSchema,
  title: z.string().min(1),
  description: z.string().min(1),
  systems: z.array(z.string().min(1)),
  visual: z
    .object({
      theme: ordaxVisualThemeSchema,
      background: ordaxBackgroundSchema,
    })
    .optional(),
  audio: ordaxAudioSchema,
  scene: z.object({
    gravity: z.object({ x: z.number(), y: z.number() }),
    entities: z.array(ordaxEntitySchema),
  }),
}) as unknown as z.ZodType<OrdaxSpec>;
