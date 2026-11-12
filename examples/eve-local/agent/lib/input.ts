import { z } from "zod";

export const valuesSchema = z.array(z.number().int().min(-1_000_000).max(1_000_000)).min(1).max(64);
export const identifierSchema = z.string().regex(/^[a-zA-Z0-9_-]{1,64}$/);
