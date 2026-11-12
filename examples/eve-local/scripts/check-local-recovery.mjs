import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [phase, app, portA, portB, beforePath, reportPath, valuesText, expectedText] = process.argv.slice(2);
const token = process.env.AGENT_FORGE_FIXTURE_TOKEN;
assert.ok(token && ["prepare", "restore"].includes(phase) && app && beforePath && reportPath);
assert.ok(portA !== portB && [portA, portB].every((p) => /^\d{1,5}$/.test(p) && Number(p) > 0 && Number(p) <= 65535));
const values = JSON.parse(valuesText);
const expected = Number(expectedText);
const conflictingValues = Array.isArray(values) && values.length === 1 && values[0] === 0 ? [1] : [0];
assert.ok(Array.isArray(values) && values.length && values.every(Number.isSafeInteger));
assert.ok(Number.isSafeInteger(expected) && expectedText !== "");

const resolveApp = createRequire(resolve(app, "package.json"));
const { Client } = await import(pathToFileURL(resolveApp.resolve("eve/client")));
const signal = AbortSignal.timeout(50_000);
const roots = Object.fromEntries([["A", portA], ["B", portB]].map(([origin, port]) => {
  const url = `http://127.0.0.1:${port}`;
  return [origin, { url, client: new Client({ baseUrl: url, auth: { bearer: token } }) }];
}));
const other = (origin) => origin === "A" ? "B" : "A";
const report = { phase, values, expected, status: "running", operations: {}, original: {} };
const options = { follow: false, reconnect: false, startIndex: 0, signal };

function save() {
  writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
}

async function request(origin, path, method = "GET", body) {
  const response = await fetch(roots[origin].url + path, {
    method, signal,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return { http: response.status, value: await response.json() };
}

const budgetPath = (id) => `/fixture/delegation/budgets/${id}`;
const launchPath = (id, launch) => `${budgetPath(id)}/launches/${launch}`;
const inspect = (origin, id, launch) => request(origin, launchPath(id, launch));
const reconcile = (origin, id, launch) => request(origin, launchPath(id, launch) + "/reconcile", "POST");

async function grant(id, limits = {}) {
  const result = await request("A", budgetPath(id), "POST", {
    maxDepth: 1, maxConcurrency: 1, maxWorkers: 1, ttlMs: 300_000, ...limits,
  });
  assert.equal(result.value.status, "created");
}

function minimized(event) {
  const { type, data, meta: { at, position } } = event;
  const scope = event.scope === undefined ? {} : { scope: event.scope };
  if (type === "turn.started") return { type, data: { turnId: data.turnId }, at, position, ...scope };
  return { type, data, at, position, ...scope };
}

async function facts(session) {
  const result = [];
  for await (const event of session.stream(options)) {
    if ([
      "session.started", "child.opened", "child.sent", "call.requested", "call.started", "call.settled",
      "delivery.admitted", "delivery.settled", "turn.started", "turn.settled", "model.started",
    ].includes(event.type) || (
      event.type === "content.completed" && event.data.phase === "reply" && event.data.kind === "text"
    )) result.push(event);
    assert.ok(result.length <= 1000, "Fixture event limit exceeded");
  }
  return result;
}

async function launch(origin, budgetId, launchId, mode = "normal", input = values, session) {
  session ??= (await roots[origin].client.sessions.create({ signal })).session;
  const startedAt = Date.now();
  const delivery = await session.send("delegate " + JSON.stringify({ budgetId, launchId, mode, values: input }), { signal });
  const acceptedAt = Date.now();
  const outcome = await delivery.result({ signal });
  const settledAt = Date.now();
  assert.equal(outcome.status, "completed");
  return { origin, budgetId, launchId, mode, values: input, sessionId: session.id, parentDeliveryId: delivery.deliveryId,
           startedAt, acceptedAt, settledAt, outcome: JSON.parse(outcome.reply), events: (await facts(session)).map(minimized) };
}

async function childWitness(run) {
  const session = roots[run.origin].client.sessions.attach(run.sessionId);
  const events = await facts(session);
  const opened = events.filter((event) => event.type === "child.opened");
  const sent = events.filter((event) => event.type === "child.sent");
  assert.equal(opened.length, 1);
  assert.equal(sent.length, 1);
  assert.equal(opened[0].data.sessionId, sent[0].data.sessionId);
  assert.equal(opened[0].data.owner.callId, sent[0].data.callId);
  const child = await facts(session.agent(opened[0]));
  const called = child.filter((event) => event.type === "call.requested" && event.data.capability.name === "scoped_total");
  assert.equal(called.length, 1);
  assert.deepEqual(called[0].data.input.values, run.values);
  assert.equal(called[0].data.input.launchId, run.launchId);
  const settled = child.filter((event) => event.type === "call.settled" && event.data.callId === called[0].data.callId);
  assert.equal(settled.length, 1);
  assert.equal(settled[0].data.outcome, "completed");
  assert.deepEqual(settled[0].data.output, { total: expected });
  assert.ok(child.some((event) => event.type === "delivery.settled" && event.data.deliveryId === sent[0].data.childDeliveryId
    && event.data.outcome === "handled"));
  assert.equal(child.filter((event) => event.type === "child.opened").length, 0);
  return {
    parent: events.map(minimized), child: child.map(minimized),
    handles: { parentSessionId: session.id, parentDeliveryId: run.parentDeliveryId,
      callId: sent[0].data.callId, childSessionId: sent[0].data.sessionId, childDeliveryId: sent[0].data.childDeliveryId },
  };
}

function noChild(run) {
  assert.ok(run.events.every((event) => event.type !== "child.opened" && event.type !== "child.sent"));
}

function denied(run, reason) {
  noChild(run);
  assert.deepEqual(run.outcome, { status: "denied", reason });
}

async function unchangedPending(run, origin) {
  const before = await inspect(run.origin, run.budgetId, run.launchId);
  const observed = await reconcile(origin, run.budgetId, run.launchId);
  const after = await inspect(run.origin, run.budgetId, run.launchId);
  report.operations[`${phase}-pending-${run.launchId}-${origin}`] = { before, observed, after };
  assert.equal(before.http, 200);
  assert.equal(before.value.status, "uncertain");
  assert.equal(observed.http, 202);
  assert.deepEqual(observed.value, before.value);
  assert.deepEqual(after, before);
}

async function recover(run, witness) {
  const original = witness.handles;
  const committed = await reconcile(run.origin, run.budgetId, run.launchId);
  const foreign = await inspect(other(run.origin), run.budgetId, run.launchId);
  const repeated = await reconcile(run.origin, run.budgetId, run.launchId);
  report.operations[`${phase}-recover-${run.launchId}`] = { committed, foreign, repeated };
  assert.equal(committed.http, 200);
  assert.equal(committed.value.status, "completed");
  for (const field of ["parentSessionId", "callId", "childSessionId", "childDeliveryId"]) {
    assert.equal(committed.value[field], original[field]);
  }
  assert.deepEqual(committed.value.result, { launchId: run.launchId, total: expected, tools: ["scoped_total"] });
  assert.deepEqual(foreign, committed);
  assert.deepEqual(repeated, committed);
}

async function prepare() {
  await grant("race");
  const barrier = Promise.withResolvers();
  const sessions = await Promise.all(Object.values(roots).map(({ client }) => client.sessions.create({ signal })));
  const concurrent = sessions.map(({ session }, index) => barrier.promise.then(() =>
    launch(index ? "B" : "A", "race", index ? "right" : "left", "hold", values, session)));
  report.operations.barrierAt = Date.now();
  barrier.resolve();
  const attempts = await Promise.all(concurrent);
  report.operations.race = attempts;
  const opened = attempts.filter((item) => item.events.some((event) => event.type === "child.opened"));
  if (opened.length !== 1) {
    report.operations.raceChildren = await Promise.all(opened.map(childWitness));
    save();
  }
  assert.equal(opened.length, 1, "Shared admission must open exactly one real child");
  assert.ok(Math.max(...attempts.map((run) => run.startedAt)) <= Math.min(...attempts.map((run) => run.settledAt)));
  const winner = opened[0];
  const loser = attempts.find((item) => item.origin !== winner.origin);
  denied(loser, "exhausted");
  assert.equal(winner.outcome.status, "completed");
  assert.deepEqual(winner.outcome.result, { launchId: winner.launchId, total: expected, tools: ["scoped_total"] });
  report.original.completed = { run: winner, witness: await childWitness(winner) };
  const originalReceipt = await inspect(winner.origin, "race", winner.launchId);
  assert.deepEqual(await inspect(loser.origin, "race", winner.launchId), originalReceipt);
  report.operations.completedReceipt = originalReceipt;

  await grant("zero", { maxWorkers: 0 });
  await grant("depth", { maxDepth: 0 });
  for (const origin of ["A", "B"]) {
    for (const [id, reason] of [["zero", "disabled"], ["depth", "depth"], ["absent", "missing-budget"], ["race", "exhausted"]]) {
      const run = await launch(origin, id, `denied-${origin}`);
      report.operations[`${origin}-${id}`] = run;
      denied(run, reason);
    }
  }

  const replay = await launch(loser.origin, "race", winner.launchId, winner.mode);
  report.operations.completedReplay = replay;
  noChild(replay);
  assert.deepEqual(replay.outcome, { status: "existing", launch: originalReceipt.value });
  const conflict = await launch(loser.origin, "race", winner.launchId, winner.mode, conflictingValues);
  report.operations.completedConflict = conflict;
  denied(conflict, "identity-conflict");

  for (const id of ["origin-demo", "restore-uncertain"]) {
    await grant(id);
    const pending = await launch("A", id, id, "uncertain");
    assert.equal(pending.outcome.status, "uncertain");
    const witness = await childWitness(pending);
    report.original[id] = { run: pending, witness };
    await unchangedPending(pending, "B");
    if (id === "origin-demo") await recover(pending, witness);
    else {
      const repeat = await launch("B", id, id, "uncertain");
      report.operations.pendingReplay = repeat;
      noChild(repeat);
      assert.equal(repeat.outcome.status, "existing");
      assert.equal(repeat.outcome.launch.status, "uncertain");
      assert.equal(repeat.outcome.launch.childSessionId, witness.handles.childSessionId);
      const changed = await launch("B", id, id, "uncertain", conflictingValues);
      report.operations.pendingConflict = changed;
      denied(changed, "identity-conflict");
    }
  }

  await grant("unresolved");
  const unresolved = await launch("A", "unresolved", "unresolved", "unresolved");
  assert.equal(unresolved.outcome.status, "uncertain");
  assert.equal(unresolved.outcome.childSessionId, null);
  noChild(unresolved);
  report.original.unresolved = { run: unresolved };
  for (const origin of ["A", "B"]) await unchangedPending(unresolved, origin);
  const duplicate = await launch("B", "unresolved", "unresolved", "unresolved");
  noChild(duplicate);
  assert.equal(duplicate.outcome.status, "existing");
  assert.equal(duplicate.outcome.launch.childSessionId, null);
  report.operations.unresolvedReplay = duplicate;
  const charged = await launch("B", "unresolved", "cannot-admit");
  denied(charged, "exhausted");
  report.operations.unresolvedCharged = charged;
}

async function restore() {
  const before = JSON.parse(readFileSync(beforePath, "utf8"));
  assert.equal(before.status, "passed");
  assert.deepEqual(before.values, values);
  assert.equal(before.expected, expected);
  const completed = before.original.completed;
  for (const origin of ["A", "B"]) {
    const receipt = await inspect(origin, completed.run.budgetId, completed.run.launchId);
    assert.deepEqual(receipt, before.operations.completedReceipt);
    report.operations[`restored-completed-${origin}`] = receipt;
  }
  for (const id of ["completed", "origin-demo", "restore-uncertain"]) {
    const saved = before.original[id];
    const actual = await childWitness(saved.run);
    assert.deepEqual(actual, saved.witness);
    report.original[id] = { handles: actual.handles, parent: actual.parent, child: actual.child };
  }
  const unresolved = before.original.unresolved.run;
  const unresolvedFacts = (await facts(roots.A.client.sessions.attach(unresolved.sessionId))).map(minimized);
  assert.deepEqual(unresolvedFacts, unresolved.events);
  report.original.unresolved = unresolvedFacts;
  const pending = before.original["restore-uncertain"];
  await unchangedPending(pending.run, "B");
  await recover(pending.run, pending.witness);
  assert.deepEqual(await childWitness(pending.run), pending.witness);
  for (const origin of ["A", "B"]) await unchangedPending(unresolved, origin);
}

try {
  await Promise.all(Object.values(roots).map(async ({ client }) => assert.equal((await client.health({ signal })).status, "ready")));
  await (phase === "prepare" ? prepare() : restore());
  report.status = "passed";
} catch (error) {
  report.status = "failed";
  report.error = error instanceof Error ? error.message : String(error);
  process.exitCode = 1;
} finally {
  save();
}
