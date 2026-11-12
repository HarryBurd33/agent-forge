import { defineChannel, POST } from "eve/channels";
import { routeAuth } from "eve/channels/auth";
import { z } from "zod";
import { fixtureAuth } from "../lib/fixture-auth.js";
import { identifierSchema, valuesSchema } from "../lib/input.js";

const eventSchema = z.strictObject({ eventId: identifierSchema, values: valuesSchema });

async function readBoundedJson(request: Request): Promise<unknown> {
  const reader = request.body?.getReader();
  if (!reader) throw new Error("Expected a JSON body");

  const decoder = new TextDecoder("utf-8", { fatal: true });
  let body = "";
  let byteCount = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) return JSON.parse(body + decoder.decode());
      byteCount += value.byteLength;
      if (byteCount > 4096) throw new RangeError("Event exceeds 4096 bytes");
      body += decoder.decode(value, { stream: true });
    }
  } finally {
    void reader.cancel().catch(() => {});
  }
}

export default defineChannel({
  turnPolicy: "queue",
  routes: [
    POST("/fixture/events/:conversationId", async (request, { from, params }) => {
      const auth = await routeAuth(request, fixtureAuth);
      if (auth instanceof Response) return auth;

      const conversation = identifierSchema.safeParse(params.conversationId);
      if (!conversation.success) {
        return Response.json({ error: "Invalid conversation ID" }, { status: 400 });
      }

      let json: unknown;
      try {
        json = await readBoundedJson(request);
      } catch (error) {
        return error instanceof RangeError
          ? Response.json({ error: "Event exceeds 4096 bytes" }, { status: 413 })
          : Response.json({ error: "Invalid JSON" }, { status: 400 });
      }

      const event = eventSchema.safeParse(json);
      if (!event.success) {
        return Response.json({ error: "Invalid event" }, { status: 400 });
      }

      const delivery = await from(`${auth.principalId}:${conversation.data}`).send(
        `total ${JSON.stringify(event.data.values)}`,
        { auth, idempotencyKey: `fixture:${event.data.eventId}` },
      );
      try {
        const result = await delivery.result({ signal: AbortSignal.timeout(12_000) });
        return Response.json(result, { status: result.status === "failed" ? 500 : 200 });
      } catch {
        return Response.json({
          sessionId: delivery.sessionId,
          deliveryId: delivery.deliveryId,
          status: "unobserved",
        }, { status: 202 });
      }
    }),
  ],
});
