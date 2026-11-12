import { z } from "zod";
import { identifierSchema, valuesSchema } from "./input.js";

export const delegationInput = z.strictObject({
  budgetId: identifierSchema,
  launchId: identifierSchema,
  values: valuesSchema,
  mode: z.enum(["normal", "hold", "uncertain", "unresolved", "probe"]),
});

export const budgetInput = z.strictObject({
  maxDepth: z.number().int().min(0).max(1),
  maxConcurrency: z.number().int().min(0).max(8),
  maxWorkers: z.number().int().min(0).max(20),
  ttlMs: z.number().int().min(1).max(600_000),
});

export const specialistInput = delegationInput.pick({ launchId: true, values: true, mode: true });
export const specialistResult = z.strictObject({
  launchId: identifierSchema,
  total: z.number().int(),
  tools: z.tuple([z.literal("scoped_total")]),
  nestedProbe: z.literal("blocked").optional(),
});

export type DelegationInput = z.infer<typeof delegationInput>;
export type BudgetInput = z.infer<typeof budgetInput>;
export type SpecialistResult = z.infer<typeof specialistResult>;

export function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export function verifiedResult(raw: unknown, input: DelegationInput): SpecialistResult | undefined {
  const parsed = specialistResult.safeParse(raw);
  if (
    parsed.success
    && parsed.data.launchId === input.launchId
    && parsed.data.nestedProbe === (input.mode === "probe" ? "blocked" : undefined)
    && parsed.data.total === input.values.reduce((sum, value) => sum + value, 0)
  ) return parsed.data;
}
