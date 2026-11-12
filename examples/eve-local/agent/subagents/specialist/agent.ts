import { defineAgent } from "eve";
import { mockModel } from "eve/evals";
import { parseJson, specialistInput } from "../../lib/delegation-input.js";

export default defineAgent({
  description: "Compute a bounded synthetic integer total through a scoped tool.",
  tool: false,
  defaultTools: false,
  model: mockModel({
    modelId: "agent-forge-scoped-total-fixture",
    respond({ lastUserMessage, toolResults, tools }) {
      const message = lastUserMessage ?? "";
      // Eve rc.9 prepends its specialist instructions to the first caller message.
      const marker = "\nCaller message:\n";
      const start = message.lastIndexOf(marker);
      const payload = start < 0 ? message : message.slice(start + marker.length);
      const input = specialistInput.safeParse(parseJson(payload));
      if (!input.success) return "Invalid specialist input";
      // The workflow sends one message to a fresh specialist session. Eve may
      // assign a different call ID when a step is retried after interruption.
      const result = toolResults.filter((entry) => entry.name === "scoped_total").at(-1);
      const nested = input.data.mode === "probe"
        ? toolResults.filter((entry) => entry.name === "delegate_total").at(-1)
        : undefined;
      if (!result) {
        return { toolCalls: [{ name: "scoped_total", id: "specialist-total", input: input.data }] };
      }
      const expected = input.data.values.reduce((sum, value) => sum + value, 0);
      if (
        result.isError
        || typeof result.output !== "object"
        || result.output === null
        || !("total" in result.output)
        || result.output.total !== expected
      ) {
        return "Specialist tool failed";
      }
      if (input.data.mode === "probe" && !nested) {
        return { toolCalls: [{
          name: "delegate_total",
          id: "nested-probe",
          input: { budgetId: "nested-probe", launchId: "blocked", values: input.data.values, mode: "normal" },
        }] };
      }
      if (nested && !nested.isError) return "Nested dispatch unexpectedly succeeded";
      return JSON.stringify({
        launchId: input.data.launchId,
        total: result.output.total,
        tools: tools.map((tool) => tool.name).sort(),
        ...(nested && { nestedProbe: "blocked" }),
      });
    },
  }),
});
