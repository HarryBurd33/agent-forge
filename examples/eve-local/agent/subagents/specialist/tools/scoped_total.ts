import { setTimeout } from "node:timers/promises";
import { defineTool } from "eve/tools";
import { specialistInput } from "../../../lib/delegation-input.js";

export default defineTool({
  description: "Compute the synthetic specialist total with no external effects.",
  inputSchema: specialistInput,
  async execute({ values, mode }, ctx) {
    if (mode === "hold") await setTimeout(4000, undefined, { signal: ctx.abortSignal });
    return { total: values.reduce((sum, value) => sum + value, 0) };
  },
});
