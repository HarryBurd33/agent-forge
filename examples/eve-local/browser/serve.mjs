import { timingSafeEqual } from "node:crypto";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { attachOwnership, sessionIdPattern as idPattern } from "./ownership.mjs";

// Local shared ownership for two synthetic browser principals.
// Only this gateway receives their credentials. Only it forwards the separate
// fixture operator credential; the Eve backend rejects both browser tokens.
const a = process.env.AGENT_FORGE_BROWSER_TOKEN_A;
const b = process.env.AGENT_FORGE_BROWSER_TOKEN_B;
const operator = process.env.AGENT_FORGE_FIXTURE_TOKEN;
if (![a, b, operator].every((token) => /^[!-~]{12,128}$/.test(token ?? "")) ||
    new Set([a, b, operator]).size !== 3) {
  throw new Error("Set three distinct synthetic fixture tokens (12–128 visible ASCII characters)");
}

function port(name) {
  const value = process.env[name];
  if (!/^\d{1,5}$/.test(value ?? "") || +value < 1024 || +value > 65535) {
    throw new Error("Set a loopback port in " + name);
  }
  return +value;
}

const browserPort = port("AGENT_FORGE_BROWSER_PORT");
const evePort = port("AGENT_FORGE_FIXTURE_PORT");
if (browserPort === evePort) throw new Error("Use distinct gateway and Eve ports");

const ownership = attachOwnership(process.env.AGENT_FORGE_BROWSER_OWNERSHIP_DB);
const html = await readFile(new URL("index.html", import.meta.url));
const app = await readFile(new URL("../dist/fixture-browser/app.js", import.meta.url));
const upstream = "http://127.0.0.1:" + evePort;
const allowedOrigin = "http://127.0.0.1:" + browserPort;
const sessionRoute = /^\/eve\/v1\/session\/([A-Za-z0-9_-]{1,160})(\/(stream|cancel))?$/;

function principal(header) {
  if (typeof header !== "string" || !header.startsWith("Bearer ") || header.length > 135) return;
  const presented = Buffer.from(header.slice(7));
  for (const [id, token] of [["fixture-browser-a", a], ["fixture-browser-b", b]]) {
    const expected = Buffer.from(token);
    if (presented.length === expected.length && timingSafeEqual(presented, expected)) return id;
  }
}

function json(response, status, code) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify({ ok: false, code, error: code }));
}

async function bodyOf(request) {
  let bytes = 0;
  const chunks = [];
  for await (const chunk of request.iterator({ destroyOnReturn: false })) {
    bytes += chunk.length;
    if (bytes > 4096) return undefined;
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

function validMessage(body) {
  return typeof body.message === "string" && body.message.length > 0 && body.message.length <= 512;
}

function validBody(body, cancelRoute) {
  if (!body || typeof body !== "object" || Array.isArray(body)) return false;
  const keys = Object.keys(body);
  if (cancelRoute) return keys.length === 1 && typeof body.turnId === "string" && idPattern.test(body.turnId);
  return keys.length === 0 || (keys.length === 1 && keys[0] === "message" && validMessage(body));
}

async function handle(request, response) {
  response.setHeader("Cache-Control", "no-store");
  response.setHeader("X-Content-Type-Options", "nosniff");
  if (request.headers.host !== "127.0.0.1:" + browserPort ||
      (request.headers.origin && request.headers.origin !== allowedOrigin)) {
    return json(response, 403, "origin_forbidden");
  }

  const url = new URL(request.url, allowedOrigin);
  if (url.origin !== allowedOrigin) return json(response, 403, "origin_forbidden");
  if (request.method === "GET" && ["/", "/app.js"].includes(url.pathname) && !url.search) {
    response.setHeader("Content-Security-Policy", "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
    response.setHeader("Referrer-Policy", "no-referrer");
    const isPage = url.pathname === "/";
    response.writeHead(200, { "Content-Type": isPage ? "text/html; charset=utf-8" : "text/javascript; charset=utf-8" });
    response.end(isPage ? html : app);
    return;
  }

  const create = request.method === "POST" && url.pathname === "/eve/v1/session" && !url.search;
  const match = sessionRoute.exec(url.pathname);
  const stream = request.method === "GET" && match?.[3] === "stream";
  const write = request.method === "POST" && match && match[3] !== "stream" && !url.search;
  if (!create && !stream && !write) return json(response, 404, "fixture_route_missing");

  const caller = principal(request.headers.authorization);
  if (!caller) {
    response.setHeader("WWW-Authenticate", 'Bearer realm="local browser fixture"');
    return json(response, 401, "unauthorized");
  }
  if (!create) {
    try {
      if (ownership.owner(match[1]) !== caller) return json(response, 403, "session_forbidden");
    } catch {
      return json(response, 503, "ownership_unavailable");
    }
  }
  for (const [key, value] of url.searchParams) {
    if (url.searchParams.getAll(key).length !== 1 ||
        !(key === "follow" && /^(true|false)$/.test(value) ||
          key === "startIndex" && /^-?\d{1,9}$/.test(value) ||
          key === "includeTailIndex" && value === "1")) {
      return json(response, 400, "fixture_query_not_supported");
    }
  }

  const abort = new AbortController();
  response.once("close", () => abort.abort());
  const headers = new Headers({ authorization: "Bearer " + operator });
  let body;
  if (request.method === "POST") {
    body = await bodyOf(request);
    if (!body) return json(response, 413, "fixture_body_too_large");
    let parsed;
    try {
      parsed = body.length === 0 ? {} : JSON.parse(body.toString("utf8"));
    } catch {
      return json(response, 400, "fixture_body_not_supported");
    }
    if (!validBody(parsed, match?.[3] === "cancel")) return json(response, 400, "fixture_body_not_supported");
    headers.set("content-type", "application/json");
  }

  let claim;
  try {
    if (create) {
      claim = ownership.reserve(caller);
      if (claim === null) return json(response, 503, "fixture_session_limit");
    } else if (request.method === "POST" && ownership.owner(match[1]) !== caller) {
      return json(response, 403, "session_forbidden");
    }
  } catch {
    return json(response, 503, "ownership_unavailable");
  }

  const result = await fetch(upstream + url.pathname + url.search, {
    method: request.method,
    headers,
    body,
    signal: create ? AbortSignal.any([abort.signal, AbortSignal.timeout(15_000)]) : abort.signal,
    redirect: "error",
  });

  if (create) {
    if (!result.ok) {
      await result.body?.cancel();
      return json(response, 502, "fixture_create_unconfirmed");
    }
    const payload = await result.json();
    const sessionHeader = result.headers.get("x-eve-session-id");
    if (typeof payload?.sessionId !== "string" || !idPattern.test(payload.sessionId)
        || (sessionHeader !== null && sessionHeader !== payload.sessionId)) {
      return json(response, 502, "fixture_session_identity_error");
    }
    try {
      ownership.finalize(claim, caller, payload.sessionId);
    } catch {
      return json(response, 503, "ownership_unavailable");
    }
    response.setHeader("Content-Type", "application/json; charset=utf-8");
    if (sessionHeader !== null) response.setHeader("x-eve-session-id", sessionHeader);
    response.writeHead(result.status);
    response.end(JSON.stringify(payload));
    return;
  }

  const contentType = result.headers.get("content-type");
  if (contentType) response.setHeader("Content-Type", contentType);
  for (const header of ["x-eve-session-id", "x-eve-stream-format", "x-eve-stream-tail-index", "x-eve-stream-version", "retry-after"]) {
    const value = result.headers.get(header);
    if (value !== null) response.setHeader(header, value);
  }
  response.writeHead(result.status);
  if (result.body) await pipeline(Readable.fromWeb(result.body), response, { signal: abort.signal });
  else response.end();
}

const server = createServer((request, response) => {
  void handle(request, response).catch(() => {
    if (response.destroyed) return;
    if (response.headersSent) response.destroy();
    else json(response, 502, "fixture_upstream_unavailable");
  });
});
server.listen(browserPort, "127.0.0.1", () => console.log("Browser fixture: " + allowedOrigin));
for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => {
    server.close();
    server.closeAllConnections();
  });
}
