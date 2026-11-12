import { defineAgent } from "eve";
import { mockModel } from "eve/evals";
import { delegationInput, parseJson } from "./lib/delegation-input.js";

export default defineAgent({
  tool: false,
  defaultTools: false,
  model: mockModel({
    modelId: "agent-forge-total-fixture",
    respond({ lastUserMessage, userMessageCount, toolResults, tools }) {
      const message = lastUserMessage ?? "";
      const id = `fixture-${userMessageCount}`;
      const result = toolResults.find((entry) => entry.id === id);

      if (message === "tools") {
        return JSON.stringify(tools.map((tool) => tool.name).sort());
      }

      if (message === "probe agent" || message === "probe specialist"
          || message === "probe catalog-agent" || message === "probe catalog-specialist") {
        if (result) return JSON.stringify({ status: result.isError ? "blocked" : "unexpected-success" });
        const catalog = message.startsWith("probe catalog-");
        const name = message.slice(catalog ? 14 : 6);
        const input = { message: "Synthetic forbidden launch probe" };
        return { toolCalls: [catalog
          ? { name: "eve__tool", input: { name, input }, id }
          : { name, input, id }] };
      }

      if (message.startsWith("delegate ")) {
        if (result) return result.isError ? "Delegation tool failed" : JSON.stringify(result.output);
        const input = delegationInput.safeParse(parseJson(message.slice(9)));
        if (!input.success) return "Invalid delegation input";
        return { toolCalls: [{ name: "delegate_total", input: input.data, id }] };
      }

      if (message === "wait") {
        if (!result) return { toolCalls: [{ name: "fixture_wait", input: {}, id }] };
        return result.isError ? "Wait interrupted" : "Wait completed";
      }

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
