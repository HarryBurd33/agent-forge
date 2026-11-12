import { Client, ClientError, type ClientSession, type SessionStreamEvent } from "eve/client";

function element<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

const token = element<HTMLInputElement>("token");
const id = element<HTMLInputElement>("session");
const message = element<HTMLInputElement>("message");
const status = element("status");
const cursor = element("cursor");
const transcript = element("transcript");
const open = element<HTMLButtonElement>("new");
const attach = element<HTMLButtonElement>("connect");
const disconnect = element<HTMLButtonElement>("disconnect");
const send = element<HTMLButtonElement>("send");
const cancel = element<HTMLButtonElement>("cancel");

type Context = {
  session: ClientSession;
  writer: ClientSession;
  verified: boolean;
  pending: boolean;
  activeTurn?: string;
  activeWait?: string;
  reader?: AbortController;
  cancelPending?: boolean;
  seen: Set<string>;
  waitCalls: Set<string>;
};
let current: Context | undefined;
let generation = 0;

function controls() {
  const ready = current?.verified === true;
  const connected = current?.reader !== undefined;
  send.disabled = !ready || !!current?.activeTurn || !!current?.pending;
  disconnect.disabled = !connected;
  cancel.disabled = !connected || !current?.activeWait || !!current.cancelPending;
  cursor.textContent = "Cursor: " + (current?.session.state.streamIndex ?? "—");
}

function append(text: string) {
  const row = document.createElement("li");
  row.textContent = text;
  transcript.append(row);
}

function accept(ctx: Context, event: SessionStreamEvent) {
  const { line, index } = event.meta.position;
  const key = `${line}:${index}`;
  if (ctx.seen.has(key)) return;
  ctx.seen.add(key);

  if (event.type === "turn.started") {
    ctx.activeTurn = event.data.turnId;
  } else if (event.type === "delivery.consumed") {
    const text = event.data.parts.flatMap((part) => part.kind === "text" ? [part.text] : []).join("");
    if (text) append("You: " + text);
  } else if (event.type === "call.requested" && event.data.capability.name === "fixture_wait") {
    ctx.waitCalls.add(event.data.callId);
  } else if (event.type === "call.started" && ctx.waitCalls.has(event.data.callId)) {
    ctx.activeWait = event.scope?.turnId;
    append("Tool: fixture_wait started");
  } else if (event.type === "call.settled" && ctx.waitCalls.delete(event.data.callId)) {
    ctx.activeWait = undefined;
    append("Tool: fixture_wait " + event.data.outcome);
  } else if (event.type === "content.completed" &&
             event.data.kind === "text" && event.data.phase === "reply" &&
             !event.data.interrupted && typeof event.data.value === "string") {
    append("Agent: " + event.data.value);
  } else if (event.type === "turn.settled") {
    if (event.data.turnId === ctx.activeTurn) {
      ctx.activeTurn = undefined;
      ctx.activeWait = undefined;
      ctx.cancelPending = false;
    }
    append("Server turn: " + event.data.outcome);
  }
}

function problem(error: unknown) {
  return error instanceof ClientError ? "Request denied or failed (HTTP " + error.status + ")." : "Connection or request failed.";
}

function reset() {
  generation += 1;
  current?.reader?.abort();
  current = undefined;
  transcript.replaceChildren();
  status.textContent = "Disconnected.";
  controls();
  return generation;
}

function follow(ctx: Context) {
  if (ctx.reader) return;
  const reader = new AbortController();
  ctx.reader = reader;
  const index = ctx.session.state.streamIndex;
  status.textContent = "Connecting from cursor " + index + "…";
  controls();
  void (async () => {
    try {
      // A bounded catch-up also confirms access when reconnecting at the tail.
      const receive = (event: SessionStreamEvent) => {
        if (current !== ctx || ctx.reader !== reader) return;
        accept(ctx, event);
        controls();
      };
      for await (const event of ctx.session.stream({ follow: false, signal: reader.signal })) receive(event);
      if (current !== ctx || ctx.reader !== reader) return;
      ctx.verified = true;
      status.textContent = "Connected from cursor " + index + ".";
      controls();
      for await (const event of ctx.session.stream({ signal: reader.signal })) receive(event);
      if (current === ctx && ctx.reader === reader) {
        ctx.verified = false;
        status.textContent = "Session stream ended.";
      }
    } catch (error) {
      if (current === ctx && ctx.reader === reader && !reader.signal.aborted) {
        ctx.verified = false;
        status.textContent = problem(error);
      }
    } finally {
      if (current === ctx && ctx.reader === reader) {
        ctx.reader = undefined;
        controls();
      }
    }
  })();
}

async function connect(create: boolean) {
  const credential = token.value;
  if (!credential || (!create && !id.value)) {
    status.textContent = "Enter the fixture token and, to attach, a session ID.";
    return;
  }
  if (!create && current?.session.id === id.value) {
    follow(current);
    return;
  }
  const version = reset();
  status.textContent = create ? "Creating session…" : "Attaching session…";
  try {
    const client = new Client({ baseUrl: location.origin, auth: { bearer: credential } });
    const session = create ? (await client.sessions.create()).session : client.sessions.attach(id.value);
    if (version !== generation) return;
    id.value = session.id;
    current = { session, writer: client.sessions.attach(session.id), verified: create, pending: false, seen: new Set(), waitCalls: new Set() };
    follow(current);
  } catch (error) {
    if (version === generation) status.textContent = problem(error);
  }
}

token.addEventListener("input", reset);
id.addEventListener("input", reset);
open.addEventListener("click", () => void connect(true));
attach.addEventListener("click", () => void connect(false));
disconnect.addEventListener("click", () => {
  if (!current) return;
  current.reader?.abort();
  current.reader = undefined;
  status.textContent = "Stream disconnected. The server session remains open.";
  controls();
});

element("message-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const ctx = current;
  if (!ctx || send.disabled || !message.value.trim()) return;
  ctx.pending = true;
  controls();
  try {
    const delivery = await ctx.writer.send(message.value);
    if (current !== ctx) return;
    message.value = "";
    status.textContent = "Message accepted by server.";
    // Wait for the receipt independently so a paused reader cannot leave Send
    // disabled forever. Keep receipt reads on the separate writer handle:
    // rc.9 advances that handle's cursor on delivery.result().
    await delivery.result({ signal: AbortSignal.timeout(45_000) });
  } catch (error) {
    if (current === ctx) status.textContent = problem(error);
  } finally {
    ctx.pending = false;
    if (current === ctx) controls();
  }
});

cancel.addEventListener("click", async () => {
  const ctx = current;
  if (!ctx?.activeWait || cancel.disabled) return;
  ctx.cancelPending = true;
  controls();
  try {
    await ctx.session.cancel({ turnId: ctx.activeWait });
    // The stream will display the authoritative turn.settled outcome.
  } catch (error) {
    ctx.cancelPending = false;
    if (current === ctx) {
      status.textContent = problem(error);
      controls();
    }
  }
});
