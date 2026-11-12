import { Client } from "eve/client";

const [port, sessionId, cursor] = process.argv.slice(2);
const token = process.env.AGENT_FORGE_FIXTURE_TOKEN;
if (!token || !/^\d{1,5}$/.test(port ?? "") || !/^wrun_[a-zA-Z0-9]+$/.test(sessionId ?? "")) {
  throw new Error("Set AGENT_FORGE_FIXTURE_TOKEN and pass PORT SESSION_ID [CURSOR]");
}
const startIndex = cursor === undefined ? 0 : Number(cursor);
if (!Number.isSafeInteger(startIndex) || startIndex < 0 || Number(port) < 1 || Number(port) > 65535) {
  throw new Error("Expected a valid port and nonnegative cursor");
}
const client = new Client({
  baseUrl: `http://127.0.0.1:${port}`,
  auth: { bearer: token },
});
const session = client.sessions.attach(sessionId, { streamIndex: startIndex });
const evidenceTypes = new Set([
  "session.started", "session.ended", "delivery.admitted", "delivery.settled",
  "turn.started", "turn.settled", "call.requested", "call.settled",
]);
const events = [];
for await (const event of session.stream({
  follow: false,
  reconnect: false,
  signal: AbortSignal.timeout(8000),
})) {
  if (evidenceTypes.has(event.type) || (
    event.type === "content.completed" && event.data.kind === "text" && event.data.phase === "reply"
  )) {
    const { type, data, scope, meta: { position } } = event;
    events.push({ type, data, scope, meta: { position } });
  }
}
console.log(JSON.stringify({ sessionId, startIndex, nextIndex: session.state.streamIndex, events }));
