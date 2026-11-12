import { randomUUID } from "node:crypto";
import { closeSync, lstatSync, openSync, realpathSync } from "node:fs";
import { dirname, isAbsolute, normalize, resolve } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath, pathToFileURL } from "node:url";

const CAPACITY = 256;
const VERSION = 1;
const APPLICATION = 0x41464f57;
const PRINCIPALS = new Set(["fixture-browser-a", "fixture-browser-b"]);
export const sessionIdPattern = /^[A-Za-z0-9_-]{1,160}$/;
const uuid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const storeSchema = `CREATE TABLE ownership_store (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  store_id TEXT NOT NULL
) STRICT`;
const claimsSchema = `CREATE TABLE ownership_claims (
  claim_id TEXT PRIMARY KEY NOT NULL,
  principal TEXT NOT NULL CHECK (principal IN ('fixture-browser-a','fixture-browser-b')),
  session_id TEXT UNIQUE
) STRICT`;

function require(condition, message) {
  if (!condition) throw new Error(message);
}

function checkedPath(path) {
  require(typeof path === "string" && isAbsolute(path) && normalize(path) === path
    && realpathSync(dirname(path)) === dirname(path), "Use an absolute canonical ownership DB path");
  return path;
}

function fileIdentity(path) {
  const entry = lstatSync(path, { bigint: true });
  require(entry.isFile() && realpathSync(path) === path, "Ownership DB must be a regular non-symlink file");
  require((entry.mode & 0o077n) === 0n, "Ownership DB must be private to its local owner");
  return `${entry.dev}:${entry.ino}`;
}

function connect(path, write = false) {
  const uri = pathToFileURL(path).href + (write ? "?mode=rw" : "?mode=ro");
  return new DatabaseSync(uri, { readOnly: !write, timeout: 1000, allowExtension: false });
}

function metadata(database) {
  require(database.prepare("PRAGMA application_id").get().application_id === APPLICATION
    && database.prepare("PRAGMA user_version").get().user_version === VERSION, "Unsupported ownership DB schema");
  const tables = database.prepare("SELECT name, sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY name").all();
  require(tables.length === 2
    && tables[0].name === "ownership_claims" && tables[0].sql === claimsSchema
    && tables[1].name === "ownership_store" && tables[1].sql === storeSchema, "Ownership DB schema differs");
  const store = database.prepare("SELECT store_id FROM ownership_store WHERE singleton = 1").get();
  require(store && uuid.test(store.store_id), "Invalid ownership store identity");
  return store.store_id;
}

function rows(database) {
  const claims = database.prepare("SELECT claim_id, principal, session_id FROM ownership_claims LIMIT 257").all();
  require(claims.length <= CAPACITY && claims.every((row) =>
    uuid.test(row.claim_id) && PRINCIPALS.has(row.principal)
      && (row.session_id === null || sessionIdPattern.test(row.session_id))), "Invalid ownership claim data");
  return claims;
}

export function initializeOwnership(input) {
  const path = checkedPath(input);
  closeSync(openSync(path, "wx", 0o600));
  const identity = fileIdentity(path);
  const database = connect(path, true);
  try {
    require(fileIdentity(path) === identity, "Ownership DB changed during initialization");
    database.exec(`BEGIN IMMEDIATE; PRAGMA application_id = ${APPLICATION}; PRAGMA user_version = ${VERSION};
      ${storeSchema}; ${claimsSchema};`);
    database.prepare("INSERT INTO ownership_store VALUES (1, ?)").run(randomUUID());
    require(fileIdentity(path) === identity, "Ownership DB changed during initialization");
    database.exec("COMMIT");
  } finally {
    database.close();
  }
  return checkOwnership(path);
}

function inspect(path) {
  const identity = fileIdentity(path);
  const database = connect(path);
  try {
    require(fileIdentity(path) === identity, "Ownership DB was replaced");
    const storeId = metadata(database);
    require(database.prepare("PRAGMA quick_check").get().quick_check === "ok", "Ownership DB integrity check failed");
    const claims = rows(database);
    require(fileIdentity(path) === identity, "Ownership DB was replaced");
    const pending = claims.filter((row) => row.session_id === null).length;
    return { identity, storeId, pending, owned: claims.length - pending };
  } finally {
    database.close();
  }
}

export function checkOwnership(input) {
  const { storeId, pending, owned } = inspect(checkedPath(input));
  return { status: "ready", schemaVersion: VERSION, storeId, pending, owned, capacity: CAPACITY };
}

export function attachOwnership(input) {
  const path = checkedPath(input);
  const { identity, storeId } = inspect(path);
  function assertIdentity() {
    require(fileIdentity(path) === identity, "Ownership DB was replaced");
  }

  function access(write, operation) {
    assertIdentity();
    const database = connect(path, write);
    try {
      assertIdentity();
      if (write) database.exec("BEGIN IMMEDIATE");
      require(metadata(database) === storeId, "Ownership store identity changed");
      const result = operation(database, rows(database));
      assertIdentity();
      if (write) database.exec("COMMIT");
      return result;
    } finally {
      database.close();
    }
  }

  return {
    owner(sessionId) {
      require(sessionIdPattern.test(sessionId), "Invalid session ID");
      return access(false, (_database, claims) => claims.find((claim) => claim.session_id === sessionId)?.principal);
    },
    reserve(principal) {
      require(PRINCIPALS.has(principal), "Invalid owner principal");
      return access(true, (database, claims) => {
        if (claims.length >= CAPACITY) return null;
        const claimId = randomUUID();
        database.prepare("INSERT INTO ownership_claims VALUES (?, ?, NULL)").run(claimId, principal);
        return claimId;
      });
    },
    finalize(claimId, principal, sessionId) {
      require(uuid.test(claimId) && PRINCIPALS.has(principal) && sessionIdPattern.test(sessionId), "Invalid ownership binding");
      access(true, (database, claims) => {
        const claim = claims.find((entry) => entry.claim_id === claimId);
        require(claim?.principal === principal, "Ownership claim conflict");
        if (claim.session_id === sessionId) return;
        require(claim.session_id === null && !claims.some((entry) => entry.session_id === sessionId),
                "Ownership session conflict");
        database.prepare("UPDATE ownership_claims SET session_id = ? WHERE claim_id = ?").run(sessionId, claimId);
      });
    },
  };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  try {
    const [command, path, ...rest] = process.argv.slice(2);
    require(rest.length === 0 && (command === "init" || command === "check"), "Usage: node browser/ownership.mjs init|check ABSOLUTE_PATH");
    console.log(JSON.stringify(command === "init" ? initializeOwnership(path) : checkOwnership(path)));
  } catch (error) {
    console.error(JSON.stringify({ status: "unavailable", error: error.message }));
    process.exitCode = 2;
  }
}
