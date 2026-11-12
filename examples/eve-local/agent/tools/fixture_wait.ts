import { setTimeout } from "node:timers/promises";
import { defineTool } from "eve/tools";
import { z } from "zod";

export default defineTool({
  description: "Wait locally without effects to qualify cancellation.",
  inputSchema: z.strictObject({}),
  async execute(_input, ctx) {
    await setTimeout(30_000, undefined, { signal: ctx.abortSignal });
    return { waited: true };
  },
});
