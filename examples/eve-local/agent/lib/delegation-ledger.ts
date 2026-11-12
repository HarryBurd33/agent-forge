import { isAbsolute } from "node:path";
import { DatabaseSync } from "node:sqlite";
import type { BudgetInput, DelegationInput, SpecialistResult } from "./delegation-input.js";

const schema = `
  CREATE TABLE IF NOT EXISTS budgets (
    budget_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL,
    max_depth INTEGER NOT NULL,
    max_concurrency INTEGER NOT NULL,
    max_workers INTEGER NOT NULL,
    ttl_ms INTEGER NOT NULL,
    expires_at_ms INTEGER NOT NULL
  );
  CREATE TABLE IF NOT EXISTS launches (
    budget_id TEXT NOT NULL REFERENCES budgets(budget_id),
    launch_id TEXT NOT NULL,
    identity TEXT NOT NULL,
    parent_session_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('reserved','uncertain','completed','failed')),
    child_session_id TEXT,
    child_delivery_id TEXT,
    result TEXT,
    PRIMARY KEY (budget_id, launch_id),
    UNIQUE (parent_session_id, call_id)
  );
`;

export type Launch = {
  budget_id: string;
  launch_id: string;
  identity: string;
  parent_session_id: string;
  call_id: string;
  state: "reserved" | "uncertain" | "completed" | "failed";
  child_session_id: string | null;
  child_delivery_id: string | null;
  result: string | null;
};

type Budget = {
  max_depth: number;
  max_concurrency: number;
  max_workers: number;
  ttl_ms: number;
  expires_at_ms: number;
};

function transaction<T>(run: (db: DatabaseSync) => T): T {
  const path = process.env.AGENT_FORGE_DELEGATION_DB;
  if (!path || !isAbsolute(path)) throw new Error("Configure an absolute fixture ledger path");
  const db = new DatabaseSync(path);
  try {
    db.exec("PRAGMA busy_timeout = 3000; PRAGMA foreign_keys = ON; BEGIN IMMEDIATE");
    db.exec(schema);
    const result = run(db);
    db.exec("COMMIT");
    return result;
  } finally {
    db.close();
  }
}

function getBudget(db: DatabaseSync, budgetId: string, principal: string): Budget | undefined {
  return db.prepare("SELECT * FROM budgets WHERE budget_id = ? AND principal_id = ?")
    .get(budgetId, principal) as Budget | undefined;
}

function getLaunch(db: DatabaseSync, budgetId: string, launchId: string): Launch | undefined {
  return db.prepare("SELECT * FROM launches WHERE budget_id = ? AND launch_id = ?")
    .get(budgetId, launchId) as Launch | undefined;
}

export function createBudget(budgetId: string, principal: string, limits: BudgetInput) {
  return transaction((db) => {
    const prior = getBudget(db, budgetId, principal);
    if (prior) {
      const matches = prior.max_depth === limits.maxDepth
        && prior.max_concurrency === limits.maxConcurrency
        && prior.max_workers === limits.maxWorkers && prior.ttl_ms === limits.ttlMs;
      return { status: matches ? "existing" : "conflict" };
    }
    const expiresAtMs = Date.now() + limits.ttlMs;
    db.prepare("INSERT INTO budgets VALUES (?, ?, ?, ?, ?, ?, ?)")
      .run(budgetId, principal, limits.maxDepth, limits.maxConcurrency, limits.maxWorkers, limits.ttlMs, expiresAtMs);
    return { status: "created", expiresAtMs };
  });
}

export function reserve(input: DelegationInput, principal: string, parent: string, callId: string) {
  return transaction((db) => {
    const budget = getBudget(db, input.budgetId, principal);
    if (!budget) return { status: "denied", reason: "missing-budget" } as const;
    const identity = JSON.stringify(input);
    const prior = getLaunch(db, input.budgetId, input.launchId);
    if (prior) {
      if (prior.identity !== identity) return { status: "denied", reason: "identity-conflict" } as const;
      return { status: "existing", launch: publicLaunch(prior) } as const;
    }
    if (budget.expires_at_ms <= Date.now()) return { status: "denied", reason: "expired" } as const;
    if (budget.max_depth < 1) return { status: "denied", reason: "depth" } as const;
    if (budget.max_workers < 1 || budget.max_concurrency < 1) {
      return { status: "denied", reason: "disabled" } as const;
    }
    const counts = db.prepare(`
      SELECT COUNT(*) AS used, COUNT(*) FILTER (WHERE state IN ('reserved','uncertain')) AS active
      FROM launches WHERE budget_id = ?
    `).get(input.budgetId) as { used: number; active: number };
    if (counts.used >= budget.max_workers) return { status: "denied", reason: "exhausted" } as const;
    if (counts.active >= budget.max_concurrency) return { status: "denied", reason: "concurrency" } as const;

    db.prepare("INSERT INTO launches VALUES (?, ?, ?, ?, ?, 'reserved', NULL, NULL, NULL)")
      .run(input.budgetId, input.launchId, identity, parent, callId);
    return { status: "reserved" } as const;
  });
}

export function recordChild(parent: string, callId: string, child: string, delivery?: string) {
  if (!process.env.AGENT_FORGE_DELEGATION_DB) return;
  transaction((db) => {
    db.prepare(`
      UPDATE launches SET child_session_id = ?, child_delivery_id = COALESCE(?, child_delivery_id)
      WHERE parent_session_id = ? AND call_id = ?
        AND (child_session_id IS NULL OR child_session_id = ?)
        AND (child_delivery_id IS NULL OR ? IS NULL OR child_delivery_id = ?)
    `).run(child, delivery ?? null, parent, callId, child, delivery ?? null, delivery ?? null);
  });
}

export function settle(parent: string, callId: string, state: "uncertain" | "completed" | "failed", result?: SpecialistResult) {
  return transaction((db) => {
    db.prepare(`
      UPDATE launches SET state = ?, result = ?
      WHERE parent_session_id = ? AND call_id = ? AND state IN ('reserved','uncertain')
    `).run(state, result ? JSON.stringify(result) : null, parent, callId);
    const row = db.prepare("SELECT * FROM launches WHERE parent_session_id = ? AND call_id = ?")
      .get(parent, callId) as Launch | undefined;
    if (!row) throw new Error("Missing launch reservation");
    return publicLaunch(row);
  });
}

export function readLaunch(budget: string, launch: string, principal: string) {
  return transaction((db) => getBudget(db, budget, principal) ? getLaunch(db, budget, launch) : undefined);
}

export function publicLaunch(row: Launch) {
  return {
    status: row.state,
    budgetId: row.budget_id,
    launchId: row.launch_id,
    parentSessionId: row.parent_session_id,
    callId: row.call_id,
    childSessionId: row.child_session_id,
    childDeliveryId: row.child_delivery_id,
    result: row.result ? JSON.parse(row.result) as SpecialistResult : null,
  };
}
