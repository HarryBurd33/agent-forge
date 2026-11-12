import assert from "node:assert/strict";
import { Client, ClientError } from "eve/client";

const fixturePort = process.env.AGENT_FORGE_FIXTURE_PORT;
const browserPort = process.env.AGENT_FORGE_BROWSER_PORT;
const a = process.env.AGENT_FORGE_BROWSER_TOKEN_A;
const b = process.env.AGENT_FORGE_BROWSER_TOKEN_B;
const operator = process.env.AGENT_FORGE_FIXTURE_TOKEN;
assert([a, b, operator].every(Boolean));
for (const port of [fixturePort, browserPort]) assert(/^\d{4,5}$/.test(port ?? ""));
const gateway = "http://127.0.0.1:" + browserPort;
const backend = "http://127.0.0.1:" + fixturePort;
const client = (bearer) => new Client({ baseUrl: gateway, auth: { bearer } });
const timeout = () => AbortSignal.timeout(12_000);
const noData = () => AbortSignal.timeout(5_000);

function positions(events) {
  return events.map(({ meta: { position } }) => `${position.line}:${position.index}`);
}
function replies(events) {
  return events.flatMap(({ type, data }) =>
    type === "content.completed" && data.kind === "text" && data.phase === "reply" ? [data.value] : []);
}
function totals(events) {
  return events.flatMap(({ type, data }) =>
    type === "call.settled" && data.outcome === "completed" && data.output?.total !== undefined
      ? [data.output.total] : []);
}
async function collect(stream) {
  const events = [];
  for await (const event of stream) events.push(event);
  return events;
}
async function status(path, token, expected, { method = "GET", body, base = gateway } = {}) {
  const response = await fetch(base + path, {
    method,
    signal: noData(),
    redirect: "error",
    headers: {
      authorization: "Bearer " + token,
      ...(body !== undefined && { "content-type": "application/json" }),
    },
    body,
  });
  assert.equal(response.status, expected);
  await response.body?.cancel();
  return response.status;
}

const page = await fetch(gateway + "/", { signal: noData() });
assert.equal(page.status, 200);
const html = await page.text();
assert.match(html, /Eve browser fixture/);
const script = await fetch(gateway + "/app.js", { signal: noData() });
assert.equal(script.status, 200);
const app = await script.text();
for (const credential of [a, b, operator]) {
  assert(!html.includes(credential));
  assert(!app.includes(credential));
}
const { session } = await client(a).sessions.create({ signal: timeout() });
const first = await client(a).sessions.attach(session.id).send("total [4,0,9]", { signal: timeout() });
assert.equal((await first.result({ signal: timeout() })).reply, "Total: 13");
const before = await collect(session.stream({ follow: false, signal: timeout() }));
assert.deepEqual(totals(before), [13]);
assert.deepEqual(replies(before), ["Total: 13"]);
const saved = session.state;
assert(saved.streamIndex > 0);

const writer = client(a).sessions.attach(saved.sessionId);
const changed = await writer.send("total [2,0,5]", { signal: timeout() });
assert.equal((await changed.result({ signal: timeout() })).reply, "Total: 7");
const resumed = client(a).sessions.attach(saved.sessionId, saved);
const delta = await collect(resumed.stream({ follow: false, signal: timeout() }));
assert.equal(resumed.id, saved.sessionId);
assert(delta.length > 0);
assert(delta.every((event) => event.meta.position.line >= saved.streamIndex));
assert.deepEqual(totals(delta), [7]);
assert.deepEqual(replies(delta), ["Total: 7"]);
assert.equal(new Set(positions([...before, ...delta])).size, before.length + delta.length);

const path = "/eve/v1/session/" + resumed.id;
const prior = await resumed.snapshot({ signal: timeout() });
const denial = {
  wrongToken: await status(path + "/stream?follow=false", "invalid-local-fixture-token", 401),
  wrongOwnerRead: await status(path + "/stream?follow=false", b, 403),
  wrongOwnerResume: await status(path, b, 403, { method: "POST", body: "{}" }),
  wrongOwnerSend: await status(path, b, 403, { method: "POST", body: '{"message":"total [99]"}' }),
  wrongOwnerCancel: await status(path + "/cancel", b, 403, { method: "POST", body: "{}" }),
  directBrowserA: await status(path + "/stream?follow=false", a, 401, { base: backend }),
  directBrowserB: await status(path + "/stream?follow=false", b, 401, { base: backend }),
};
await assert.rejects(() => client(b).sessions.attach(resumed.id).snapshot({ signal: timeout() }),
  (error) => error instanceof ClientError && error.status === 403);
assert.deepEqual(positions((await resumed.snapshot({ signal: timeout() })).events), positions(prior.events));
const bob = await client(b).sessions.create({ message: "total [1,2]", signal: timeout() });
assert.notEqual(bob.session.id, resumed.id);
assert.equal((await bob.delivery.result({ signal: timeout() })).reply, "Total: 3");

const wait = await writer.send("wait", { signal: timeout() });
let waitId;
let waitTurn;
let cancellation;
let stopped;
for await (const event of resumed.stream({ signal: timeout() })) {
  if (event.type === "call.requested" && event.data.capability.name === "fixture_wait") {
    waitId = event.data.callId;
  } else if (event.type === "call.started" && event.data.callId === waitId) {
    waitTurn = event.scope?.turnId;
    assert(waitTurn);
    cancellation = await resumed.cancel({ turnId: waitTurn, signal: timeout() });
  } else if (event.type === "turn.settled" && event.data.turnId === waitTurn) {
    stopped = event.data;
    break;
  }
}
assert(cancellation && stopped);
assert.equal(stopped.outcome, "cancelled");
assert.equal(stopped.cause?.deliveryId, cancellation.deliveryId);
assert.equal((await wait.result({ signal: timeout() })).status, "cancelled");
assert.equal((await cancellation.result({ signal: timeout() })).outcome, "applied");
const after = await resumed.send("total [-3,0,2]", { signal: timeout() });
assert.equal((await after.result({ signal: timeout() })).reply, "Total: -1");

const final = await resumed.snapshot({ signal: timeout() });
const interrupted = final.events.find((event) => event.type === "call.settled" && event.data.callId === waitId);
assert.equal(interrupted?.data.outcome, "interrupted");
assert.deepEqual(totals(final.events), [13, 7, -1]);
assert.deepEqual(replies(final.events), ["Total: 13", "Total: 7", "Total: -1"]);
assert.deepEqual(final.events.flatMap((event) => event.type === "turn.settled" ? [event.data.outcome] : []),
  ["completed", "completed", "cancelled", "completed"]);

console.log(JSON.stringify({
  scope: "SDK and HTTP; actual browser observation is separate",
  session: resumed.id,
  first: { total: 13, cursor: saved.streamIndex },
  changed: { total: 7, firstLine: delta[0].meta.position.line, resumedCursor: prior.session.streamIndex },
  cancel: { turnId: waitTurn, deliveryId: cancellation.deliveryId, turn: stopped.outcome, call: interrupted.data.outcome, reason: interrupted.data.reason },
  afterCancel: { total: -1 },
  denial,
  distinctPrincipalPositive: { total: 3 },
  eventCount: final.events.length,
}, null, 2));
