import { defineWorkflowTool } from "eve/tools";
import { delegationInput, parseJson, verifiedResult, type DelegationInput } from "../lib/delegation-input.js";
import { reserve, settle } from "../lib/delegation-ledger.js";

async function reserveLaunch(input: DelegationInput, principal: string, parent: string, callId: string) {
  "use step";
  return reserve(input, principal, parent, callId);
}

async function recordResult(
  parent: string, callId: string, input: DelegationInput, outcome: string, reply: string | null,
) {
  "use step";
  if (outcome !== "completed") return settle(parent, callId, "uncertain");
  const result = verifiedResult(parseJson(reply ?? ""), input);
  if (!result) return settle(parent, callId, "failed");
  if (input.mode === "uncertain") return settle(parent, callId, "uncertain");
  return settle(parent, callId, "completed", result);
}

export default defineWorkflowTool({
  description: "Use a preconfigured fixture budget to delegate one bounded integer total.",
  inputSchema: delegationInput,
  availableInSubagents: false,
  async execute(input, ctx) {
    "use workflow";
    const caller = ctx.session.auth.current;
    if (caller?.authenticator !== "fixture" || caller.principalType !== "service") {
      return { status: "denied", reason: "authority" };
    }
    const parent = ctx.session.id;
    const callId = ctx.callId;
    const decision = await reserveLaunch(input, caller.principalId, parent, callId);
    if (decision.status !== "reserved") return decision;
    // Inject an observation gap immediately after reservation. Leave the slot charged.
    if (input.mode === "unresolved") return await recordResult(parent, callId, input, "unobserved", null);
    try {
      const child = ctx.agent("specialist");
      const delivery = await child.send(JSON.stringify({
        launchId: input.launchId, values: input.values, mode: input.mode,
      }), { signal: ctx.abortSignal });
      const observed = await delivery.result();
      return await recordResult(parent, callId, input, observed.status, observed.reply ?? null);
    } catch {
      return await recordResult(parent, callId, input, "unobserved", null);
    }
  },
});
