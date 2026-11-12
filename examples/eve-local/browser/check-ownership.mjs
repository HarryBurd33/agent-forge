import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { setTimeout } from "node:timers/promises";
import { pathToFileURL } from "node:url";

const [phase, app, backendPort, firstPort, secondPort, previous, output, valuesText, expectedText] = process.argv.slice(2);
const { Client } = await import(pathToFileURL(createRequire(resolve(app, "package.json")).resolve("eve/client")));
const a = process.env.AGENT_FORGE_BROWSER_TOKEN_A;
const b = process.env.AGENT_FORGE_BROWSER_TOKEN_B;
const operator = process.env.AGENT_FORGE_FIXTURE_TOKEN;
assert.ok(a && b && operator && ["baseline", "prepare", "restore", "capacity", "finalize", "unavailable"].includes(phase));
const values = JSON.parse(valuesText);
const expected = Number(expectedText);
const url = (port) => "http://127.0.0.1:" + port;
const roots = { G1: url(firstPort), G2: url(secondPort), Eve: url(backendPort) };
const client = (root, bearer) => new Client({ baseUrl: roots[root], auth: { bearer } });
const signal = AbortSignal.timeout(40_000);
const report = { phase, values, expected, status: "running", requests: {}, sessions: {} };

async function request(root, path, token, method = "GET", payload) {
  const response = await fetch(roots[root] + path, {
    method, signal, redirect: "error",
    headers: { Authorization: "Bearer " + token, ...(payload === undefined ? {} : { "Content-Type": "application/json" }) },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  const result = { status: response.status, sessionHeader: response.headers.get("x-eve-session-id") };
  if (response.headers.get("content-type")?.includes("application/json")) result.body = await response.json();
  else await response.body?.cancel();
  return result;
}

function minimize(event) {
  const { type, data, meta: { position, at } } = event;
  if (type === "call.started") return { type, data, position, at, turnId: event.scope?.turnId };
  return { type, data, position, at };
}

async function history(root, id, bearer, cursor = 0) {
  const session = client(root, bearer).sessions.attach(id, { streamIndex: cursor });
  const events = [];
  for await (const event of session.stream({ follow: false, reconnect: false, signal })) {
    if (["session.started", "delivery.admitted", "delivery.settled", "model.started", "call.requested", "call.started", "call.settled", "turn.settled"].includes(event.type)
        || (event.type === "content.completed" && event.data.phase === "reply" && event.data.kind === "text")) {
      events.push(minimize(event));
    }
    assert.ok(events.length <= 1000);
  }
  return { cursor: session.state.streamIndex, events };
}

const route = (id) => "/eve/v1/session/" + id;
const totals = ({ events }) => events.filter((event) => event.type === "call.settled"
  && event.data.outcome === "completed" && Number.isSafeInteger(event.data.output?.total)).map((event) => event.data.output.total);

async function denied(root, id, token) {
  const path = route(id);
  return {
    read: await request(root, path + "/stream?follow=false", token),
    resume: await request(root, path, token, "POST", {}),
    send: await request(root, path, token, "POST", { message: "total [99]" }),
    cancel: await request(root, path + "/cancel", token, "POST", { turnId: "turn_0" }),
  };
}

function statusGroup(group, status) {
  assert.deepEqual(Object.values(group).map((item) => item.status), [status, status, status, status]);
}

async function authoritativeDenials(records) {
  for (const [id, item] of Object.entries(records)) {
    const before = await history("Eve", item.sessionId, operator);
    const wrong = await denied(item.other, item.sessionId, item.token === "A" ? b : a);
    const invalid = await denied(item.other, item.sessionId, "invalid-local-fixture-token");
    const unknown = await denied(item.other, "wrun_unknown_fixture_session", item.token === "A" ? a : b);
    const direct = await request("Eve", route(item.sessionId) + "/stream?follow=false", item.token === "A" ? a : b);
    const after = await history("Eve", item.sessionId, operator);
    report.requests[id + "-denials"] = { wrong, invalid, unknown, direct, before, after };
    statusGroup(wrong, 403);
    statusGroup(invalid, 401);
    statusGroup(unknown, 403);
    assert.equal(direct.status, 401);
    assert.deepEqual(after, before);
  }
}

async function exercise(root, other, token, session) {
  const sessionId = session.id;
  const bearer = token === "A" ? a : b;
  const mirrored = client(other, bearer).sessions.attach(sessionId);
  const path = route(sessionId);
  const resume = await request(other, path, bearer, "POST", {});
  assert.ok(resume.status >= 200 && resume.status < 300);
  const first = await mirrored.send("total " + JSON.stringify(values), { signal });
  assert.equal((await first.result({ signal })).reply, "Total: " + expected);
  const before = await history(other, sessionId, bearer);
  assert.deepEqual(totals(before), [expected]);
  const changed = await mirrored.send("total [-3,0,2]", { signal });
  assert.equal((await changed.result({ signal })).reply, "Total: -1");
  const suffix = await history(other, sessionId, bearer, before.cursor);
  assert.deepEqual(totals(suffix), [-1]);
  assert.ok(suffix.events.every((event) => event.position.line >= before.cursor));

  const wait = await client(root, bearer).sessions.attach(sessionId).send("wait", { signal });
  let requested;
  let turnId;
  let cancellation;
  for await (const event of client(other, bearer).sessions.attach(sessionId).stream({ startIndex: suffix.cursor, signal })) {
    if (event.type === "call.requested" && event.data.capability.name === "fixture_wait") requested = event.data.callId;
    if (event.type === "call.started" && event.data.callId === requested) {
      turnId = event.scope?.turnId;
      assert.ok(turnId);
      cancellation = await mirrored.cancel({ turnId, signal });
    }
    if (event.type === "turn.settled" && event.data.turnId === turnId) {
      assert.equal(event.data.outcome, "cancelled");
      assert.equal(event.data.cause?.deliveryId, cancellation.deliveryId);
      break;
    }
  }
  assert.ok(cancellation);
  assert.equal((await wait.result({ signal })).status, "cancelled");
  assert.equal((await cancellation.result({ signal })).outcome, "applied");
  const final = await history("Eve", sessionId, operator);
  assert.deepEqual(totals(final), [expected, -1]);
  assert.ok(final.events.some((event) => event.type === "call.settled" && event.data.callId === requested
    && event.data.outcome === "interrupted"));
  return { root, other, token, sessionId, resume, firstDeliveryId: first.deliveryId, changedDeliveryId: changed.deliveryId,
    waitDeliveryId: wait.deliveryId, cancelDeliveryId: cancellation.deliveryId, turnId, before, suffix, final };
}

async function prepare() {
  const [alice, bob] = await Promise.all([
    client("G1", a).sessions.create({ signal }),
    client("G2", b).sessions.create({ signal }),
  ]);
  assert.notEqual(alice.session.id, bob.session.id);
  report.sessions.A = await exercise("G1", "G2", "A", alice.session);
  report.sessions.B = await exercise("G2", "G1", "B", bob.session);
  await authoritativeDenials(report.sessions);
}

async function restore() {
  const before = JSON.parse(readFileSync(previous, "utf8"));
  assert.equal(before.status, "passed");
  for (const [id, saved] of Object.entries(before.sessions)) {
    const bearer = saved.token === "A" ? a : b;
    const G1 = await history("G1", saved.sessionId, bearer);
    const G2 = await history("G2", saved.sessionId, bearer);
    const Eve = await history("Eve", saved.sessionId, operator);
    const suffix = await history(saved.other, saved.sessionId, bearer, saved.before.cursor);
    assert.deepEqual(G1, saved.final);
    assert.deepEqual(G2, saved.final);
    assert.deepEqual(Eve, saved.final);
    assert.deepEqual(totals(suffix), [-1]);
    report.sessions[id] = { ...saved, restored: { G1, G2, Eve, suffix } };
  }
  await authoritativeDenials(report.sessions);
}

try {
  if (phase === "baseline") {
    const { session } = await client("G1", a).sessions.create({ signal });
    const delivery = await session.send("total " + JSON.stringify(values), { signal });
    assert.equal((await delivery.result({ signal })).reply, "Total: " + expected);
    const path = route(session.id) + "/stream?follow=false";
    report.requests.sameOwner = { origin: await request("G1", path, a), secondary: await request("G2", path, a) };
    report.sessions.A = { sessionId: session.id, history: await history("Eve", session.id, operator) };
    assert.equal(report.requests.sameOwner.origin.status, 200);
    assert.equal(report.requests.sameOwner.secondary.status, 403);
    assert.deepEqual(totals(report.sessions.A.history), [expected]);
    report.status = "stale-observed";
  } else {
    if (phase === "prepare") await prepare();
    if (phase === "restore") await restore();
    if (phase === "capacity") {
      const barrier = Promise.withResolvers();
      const pending = [["G1", a], ["G2", b]].map(([gateway, token]) =>
        barrier.promise.then(() => request(gateway, "/eve/v1/session", token, "POST", { message: "total " + JSON.stringify(values) })));
      barrier.resolve();
      const responses = await Promise.all(pending);
      report.requests.race = responses;
      assert.deepEqual(responses.map((entry) => entry.status).sort(), [202, 503]);
      assert.equal(responses.find((entry) => entry.status === 503).body.code, "fixture_session_limit");
      const sessionId = responses.find((entry) => entry.status === 202).body.sessionId;
      assert.equal(typeof sessionId, "string");
      // A bodyless prewarm receipt need not create a readable workflow stream.
      // Observe this real first-message turn without submitting another message.
      for (let attempt = 0; attempt < 30; attempt++) {
        try {
          const backend = await history("Eve", sessionId, operator);
          if (totals(backend).length) {
            report.sessions.capacity = { sessionId, backend };
            break;
          }
        } catch (error) {
          if (![404, 425].includes(error.status)) throw error;
        }
        await setTimeout(100, undefined, { signal });
      }
      assert.deepEqual(totals(report.sessions.capacity.backend), [expected]);
      const full = await request("G2", "/eve/v1/session", b, "POST", {});
      report.requests.full = full;
      assert.equal(full.status, 503);
      assert.equal(full.body.code, "fixture_session_limit");
    }
    if (phase === "finalize") {
      const response = await request("G2", "/eve/v1/session", b, "POST", { message: "total [23,0,4]" });
      report.requests.create = response;
      assert.equal(response.status, 503);
      assert.equal(response.sessionHeader, null);
      assert.equal(response.body.code, "ownership_unavailable");
      assert.equal(response.body.sessionId, undefined);
    }
    if (phase === "unavailable") {
      const saved = JSON.parse(readFileSync(previous, "utf8"));
      for (const [id, item] of Object.entries(saved.sessions)) {
        const token = item.token === "A" ? a : b;
        const before = await history("Eve", item.sessionId, operator);
        const unavailable = await denied(item.other, item.sessionId, token);
        const after = await history("Eve", item.sessionId, operator);
        report.requests[id] = { before, unavailable, after };
        statusGroup(unavailable, 503);
        assert.ok(Object.values(unavailable).every((entry) => entry.body.code === "ownership_unavailable"));
        assert.deepEqual(after, before);
      }
    }
    report.status = "passed";
  }
} catch (error) {
  report.status = "failed";
  report.error = error.message;
  process.exitCode = 1;
} finally {
  writeFileSync(output, JSON.stringify(report, null, 2) + "\n");
}
