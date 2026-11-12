import { defineTool } from "eve/tools";
import { z } from "zod";
import { valuesSchema } from "../lib/input.js";

export default defineTool({
  description: "Sum 1–64 bounded integers. The absolute total must be at most 1,000,000.",
  inputSchema: z.strictObject({ values: valuesSchema }),
  execute({ values }) {
    const total = values.reduce((sum, value) => sum + value, 0);
    if (Math.abs(total) > 1_000_000) {
      throw new Error("Total exceeds the fixture range");
    }
    return { total };
  },
});
