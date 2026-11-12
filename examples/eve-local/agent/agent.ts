import { defineAgent } from "eve";
import { mockModel } from "eve/evals";

export default defineAgent({
  model: mockModel({
    modelId: "agent-forge-total-fixture",
    respond({ lastUserMessage, userMessageCount, toolResults }) {
      const message = lastUserMessage ?? "";
      const id = `fixture-${userMessageCount}`;
      const result = toolResults.find((entry) => entry.id === id);

      if (message === "skill") {
        if (!result) {
          return { toolCalls: [{ name: "eve__skill", input: { name: "integer-totals" }, id }] };
        }
        return result.isError ? "Skill error" : `Loaded skill: ${JSON.stringify(result.output)}`;
      }

      if (result) {
        if (result.isError) return "Total rejected";
        const output = result.output;
        if (typeof output === "object" && output !== null && "total" in output) {
          return `Total: ${output.total}`;
        }
        return "Unexpected tool output";
      }

      if (message === "invalid") {
        return { toolCalls: [{ name: "total", input: {}, id }] };
      }
      if (message.startsWith("total ")) {
        return { toolCalls: [{ name: "total", input: { values: JSON.parse(message.slice(6)) }, id }] };
      }
      return "Unsupported fixture message";
    },
  }),
});
