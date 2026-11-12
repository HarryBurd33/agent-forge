import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { setTimeout } from "node:timers/promises";
import { Client } from "eve/client";

const [port, valuesJson, expectedText] = process.argv.slice(2);
const token = process.env.AGENT_FORGE_FIXTURE_TOKEN;
assert.ok(token && /^\d{1,5}$/.test(port ?? "") && Number(port) > 0 && Number(port) <= 65535,
  "Set AGENT_FORGE_FIXTURE_TOKEN and pass PORT VALUES_JSON EXPECTED_TOTAL");
const values = JSON.parse(valuesJson);
const expected = Number(expectedText);
assert.ok(Array.isArray(values) && values.length > 0 && values.every(Number.isSafeInteger));
assert.ok(Number.isSafeInteger(expected) && expectedText !== "");

const baseUrl = `http://127.0.0.1:${port}`;
const client = new Client({ baseUrl, auth: { bearer: token } });
const signal = AbortSignal.timeout(25_000);
const prefix = `verify-${randomUUID()}`;
const budgetPath = (id) => `/fixture/delegation/budgets/${id}`;
const launchPath = (id, launch) => `${budgetPath(id)}/launches/${launch}`;

async function request(path, method = "GET", body, authorized = true) {
  const headers = { "Content-Type": "application/json" };
  if (authorized) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(baseUrl + path, {
    method, headers, signal, body: body === undefined ? undefined : JSON.stringify(body),
  });
  return { http: response.status, payload: await response.json() };
}

async function budget(label, limits = {}) {
  const id = `${prefix}-${label}`;
  const response = await request(budgetPath(id), "POST", {
    maxDepth: 1, maxConcurrency: 1, maxWorkers: 2, ttlMs: 45_000, ...limits,
  });
  assert.equal(response.payload.status, "created");
  return id;
}

function start(budgetId, launchId, mode = "normal", input = values) {
  const message = "delegate " + JSON.stringify({ budgetId, launchId, mode, values: input });
  return client.sessions.create({ message, signal });
}

async function events(session) {
  const result = [];
  for await (const event of session.stream({ startIndex: 0, follow: false, reconnect: false, signal })) {
    result.push(event);
  }
  return result;
}

async function finished(started) {
  const { session, delivery } = await started;
  const response = await delivery.result({ signal });
  assert.equal(response.status, "completed");
  return { session, result: JSON.parse(response.reply), events: await events(session) };
}

function childEvidence(parent) {
  const opened = parent.events.filter((event) => event.type === "child.opened");
  const sent = parent.events.filter((event) => event.type === "child.sent");
  assert.equal(opened.length, 1);
  assert.equal(sent.length, 1);
  assert.equal(opened[0].data.sessionId, sent[0].data.sessionId);
  assert.equal(opened[0].data.owner.callId, sent[0].data.callId);
  return { opened: opened[0], sent: sent[0] };
}

async function waitForLaunch(path, accept) {
  for (let attempt = 0; attempt < 40; attempt++) {
    const response = await request(path);
    if (accept(response.payload)) return response.payload;
    await setTimeout(75, undefined, { signal });
  }
  assert.fail("Expected launch state was never observed");
}

async function denied(started, reason) {
  const outcome = await finished(started);
  assert.deepEqual(outcome.result, { status: "denied", reason });
  assert.equal(outcome.events.some((event) => event.type === "child.opened"), false);
}

assert.equal((await client.health({ signal })).status, "ready");
const tools = await finished(client.sessions.create({ message: "tools", signal }));
assert.deepEqual(tools.result, ["delegate_total", "eve__skill", "fixture_wait", "total"]);
assert.equal((await request(budgetPath(prefix), "POST", {}, false)).http, 401);
assert.equal((await request(budgetPath(prefix), "POST", { maxDepth: -1 })).http, 400);
await denied(start(prefix, "no-budget"), "missing-budget");
for (const name of ["agent", "specialist", "catalog-agent", "catalog-specialist"]) {
  const probe = await finished(client.sessions.create({ message: `probe ${name}`, signal }));
  assert.deepEqual(probe.result, { status: "blocked" });
  assert.equal(probe.events.some((event) => event.type === "child.opened"), false);
}

await denied(start(await budget("depth", { maxDepth: 0 }), "blocked"), "depth");
await denied(start(await budget("zero", { maxWorkers: 0 }), "blocked"), "disabled");
await denied(start(await budget("zero-active", { maxConcurrency: 0 }), "blocked"), "disabled");

const scoped = await finished(start(await budget("nested"), "nested", "probe"));
assert.equal(scoped.result.status, "completed");
assert.deepEqual(scoped.result.result, { launchId: "nested", total: expected, tools: ["scoped_total"], nestedProbe: "blocked" });
const nested = await events(scoped.session.agent(childEvidence(scoped).opened));
assert.equal(nested.some((event) => event.type === "child.opened"), false);

const unresolvedBudget = await budget("unresolved");
const unresolved = await finished(start(unresolvedBudget, "missing", "unresolved"));
assert.equal(unresolved.result.status, "uncertain");
assert.equal(unresolved.result.childSessionId, null);
assert.equal(unresolved.events.some((event) => event.type === "child.opened"), false);
const missingPath = launchPath(unresolvedBudget, "missing") + "/reconcile";
assert.equal((await request(missingPath, "POST")).http, 202);
const unresolvedReplay = await finished(start(unresolvedBudget, "missing", "unresolved"));
assert.equal(unresolvedReplay.result.launch.status, "uncertain");
assert.equal(unresolvedReplay.events.some((event) => event.type === "child.opened"), false);
await denied(start(unresolvedBudget, "another"), "concurrency");

const shared = await budget("shared");
const held = finished(start(shared, "first", "hold"));
await waitForLaunch(launchPath(shared, "first"), (row) => row.status === "reserved" && row.childSessionId);
await denied(start(shared, "blocked"), "concurrency");
const first = await held;
const { opened, sent } = childEvidence(first);
assert.equal(first.result.status, "completed");
assert.deepEqual(first.result.result, { launchId: "first", total: expected, tools: ["scoped_total"] });
assert.equal(first.result.childSessionId, opened.data.sessionId);
const child = await events(first.session.agent(opened));
assert.ok(child.some((event) => event.type === "call.requested" && event.data.capability.name === "scoped_total"));
assert.ok(child.some((event) => event.type === "call.settled" && event.data.output?.total === expected));
assert.ok(child.some((event) => event.type === "delivery.settled" && event.data.deliveryId === sent.data.childDeliveryId));
assert.equal(child.some((event) => event.type === "child.opened"), false);

// Keep the admitted caller session but deliberately leave its delivery result unread.
const { session: pendingSession } = await start(shared, "pending", "uncertain");
const pending = await waitForLaunch(launchPath(shared, "pending"), (row) => row.status === "uncertain");
assert.equal(pending.result, null);
const original = childEvidence({ events: await events(pendingSession) });
const replay = await finished(start(shared, "pending", "uncertain"));
assert.equal(replay.result.status, "existing");
assert.equal(replay.result.launch.status, "uncertain");
assert.equal(replay.events.some((event) => event.type === "child.opened"), false);
await denied(start(shared, "pending", "uncertain", [...values, 1]), "identity-conflict");
await denied(start(shared, "spent"), "exhausted");

const reconcile = launchPath(shared, "pending") + "/reconcile";
const recovered = await request(reconcile, "POST");
assert.equal(recovered.http, 200);
assert.equal(recovered.payload.status, "completed");
assert.equal(recovered.payload.childSessionId, original.opened.data.sessionId);
assert.equal(recovered.payload.childDeliveryId, original.sent.data.childDeliveryId);
assert.deepEqual(recovered.payload.result, { launchId: "pending", total: expected, tools: ["scoped_total"] });
assert.deepEqual(await request(reconcile, "POST"), recovered);
console.log(JSON.stringify({
  status: "passed", budgetId: shared, values, expected, parentSessionId: first.session.id,
  childSessionId: opened.data.sessionId, childDeliveryId: sent.data.childDeliveryId,
  reconciled: recovered.payload,
}));
