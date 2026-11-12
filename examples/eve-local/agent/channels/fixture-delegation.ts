import { defineChannel, GET, POST } from "eve/channels";
import { routeAuth } from "eve/channels/auth";
import type { SessionStreamEvent } from "eve/client";
import { budgetInput, delegationInput, parseJson, verifiedResult } from "../lib/delegation-input.js";
import { createBudget, publicLaunch, readLaunch, recordChild, settle } from "../lib/delegation-ledger.js";
import { fixtureAuth } from "../lib/fixture-auth.js";
import { readBoundedJson } from "../lib/http-input.js";
import { identifierSchema } from "../lib/input.js";

const budgets = "/fixture/delegation/budgets/:budgetId";
const launches = `${budgets}/launches/:launchId`;

async function authorize(request: Request, budgetId: unknown, launchId?: unknown) {
  const auth = await routeAuth(request, fixtureAuth);
  if (auth instanceof Response) return auth;
  if (!process.env.AGENT_FORGE_DELEGATION_DB) {
    return Response.json({ status: "ledger-unavailable" }, { status: 503 });
  }
  if (!identifierSchema.safeParse(budgetId).success
      || (launchId !== undefined && !identifierSchema.safeParse(launchId).success)) {
    return Response.json({ status: "invalid-identifier" }, { status: 400 });
  }
  return auth;
}

function isEvent<T extends SessionStreamEvent["type"]>(
  event: SessionStreamEvent, type: T,
): event is Extract<SessionStreamEvent, { type: T }> {
  return event.type === type;
}

async function collect(stream: AsyncIterable<SessionStreamEvent>) {
  const events: SessionStreamEvent[] = [];
  for await (const event of stream) {
    events.push(event);
    if (events.length > 10_000) throw new Error("Session evidence exceeded fixture limit");
  }
  return events;
}

export default defineChannel({
  routes: [
    POST(budgets, async (request, { params }) => {
      const auth = await authorize(request, params.budgetId);
      if (auth instanceof Response) return auth;
      let payload: unknown;
      try {
        payload = await readBoundedJson(request);
      } catch {
        return Response.json({ status: "invalid-body" }, { status: 400 });
      }
      const parsed = budgetInput.safeParse(payload);
      if (!parsed.success) return Response.json({ status: "invalid-budget" }, { status: 400 });
      const result = createBudget(params.budgetId, auth.principalId, parsed.data);
      return Response.json(result, { status: result.status === "conflict" ? 409 : 200 });
    }),
    GET(launches, async (request, { params }) => {
      const auth = await authorize(request, params.budgetId, params.launchId);
      if (auth instanceof Response) return auth;
      const row = readLaunch(params.budgetId, params.launchId, auth.principalId);
      if (!row) return Response.json({ status: "unknown" }, { status: 404 });
      return Response.json(publicLaunch(row));
    }),
    POST(`${launches}/reconcile`, async (request, { attachSession, params }) => {
      const auth = await authorize(request, params.budgetId, params.launchId);
      if (auth instanceof Response) return auth;
      const row = readLaunch(params.budgetId, params.launchId, auth.principalId);
      if (!row) return Response.json({ status: "unknown" }, { status: 404 });
      const pending = () => Response.json(publicLaunch(row), { status: 202 });
      if (row.state === "completed" || row.state === "failed") return Response.json(publicLaunch(row));

      const options = { follow: false, signal: AbortSignal.timeout(4000) };
      try {
        const parent = await collect(attachSession(row.parent_session_id).stream(options));
        const opened = parent.filter((event) => isEvent(event, "child.opened")).filter((event) => event.data.name === "specialist" && "callId" in event.data.owner
          && event.data.owner.callId === row.call_id);
        const sent = parent.filter((event) => isEvent(event, "child.sent")).filter((event) => event.data.callId === row.call_id);
        if (opened.length !== 1 || sent.length !== 1) return pending();

        const { sessionId, childDeliveryId } = sent[0].data;
        if (opened[0].data.sessionId !== sessionId
            || (row.child_session_id && row.child_session_id !== sessionId)
            || (row.child_delivery_id && row.child_delivery_id !== childDeliveryId)) {
          return Response.json({ status: "handle-conflict" }, { status: 409 });
        }
        recordChild(row.parent_session_id, row.call_id, sessionId, childDeliveryId);

        const child = await collect(attachSession(sessionId).stream(options));
        const delivery = child.filter((event) => isEvent(event, "delivery.settled"))
          .find((event) => event.data.deliveryId === childDeliveryId);
        if (!delivery || !delivery.data.turnId) return pending();
        const turn = child.filter((event) => isEvent(event, "turn.settled"))
          .find((event) => event.data.turnId === delivery.data.turnId);
        if (!turn) return pending();
        if (turn.data.outcome !== "completed") {
          return Response.json(settle(row.parent_session_id, row.call_id, "failed"));
        }

        const reply = child.filter((event) => isEvent(event, "content.completed")).find((event) => event.scope?.turnId === delivery.data.turnId
          && event.data.phase === "reply" && event.data.kind === "text");
        if (!reply) return pending();
        const result = verifiedResult(
          parseJson(String(reply.data.value)), delegationInput.parse(JSON.parse(row.identity)),
        );
        return Response.json(result
          ? settle(row.parent_session_id, row.call_id, "completed", result)
          : settle(row.parent_session_id, row.call_id, "failed"));
      } catch {
        return pending();
      }
    }),
  ],
});
