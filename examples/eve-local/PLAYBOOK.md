# Synthetic Eve fixture playbook

Use synthetic integer inputs and a local fixture token. The app exercises the actual Eve session, typed tool, on-demand skill, event route, eval and client. The model is deterministic `mockModel` and requires no provider key. Run one owner process per development store. No external integrations or deployment are needed.

## Prepare and verify the pinned runtime

Use Node 24 and npm. On a fresh copy run `npm ci`, then run:

```sh
node -e 'const assert = require("node:assert/strict"); for (const version of [require("./package.json").dependencies.eve, require("./package-lock.json").packages["node_modules/eve"].version, require("./node_modules/eve/package.json").version]) assert.equal(version, "1.0.0-rc.9")'
npm run typecheck
EVE_TELEMETRY_DISABLED=1 npm run build
```

The initial scaffold used a caret requirement and installed rc.10 while the fixture targeted rc.9. Require agreement across the manifest, lock, and actual package. The lock points to the registry tarball with an integrity hash. Inspect `node_modules/eve/docs/README.md` and its guides before changing a runtime API. See the [resource index](toolbox/index.json) for authored inputs and supported commands.

## Run the local fixture

Set a synthetic bearer token, choose a free local port, and keep the server in an owned terminal so you can stop it.

```sh
export AGENT_FORGE_FIXTURE_TOKEN="local-fixture-example"
export AGENT_FORGE_FIXTURE_PORT=24731
EVE_TELEMETRY_DISABLED=1 npm run dev -- --host 127.0.0.1 --port "$AGENT_FORGE_FIXTURE_PORT" --no-ui --no-default-extensions
```

In a second terminal use the same two environment values. Build the base URL from the loopback port. Proceed when health reports `status: "ready"`.

```sh
fixture_url="http://127.0.0.1:$AGENT_FORGE_FIXTURE_PORT"
curl --max-time 5 -fsS "$fixture_url/eve/v1/health"
EVE_TELEMETRY_DISABLED=1 EVE_EVAL_AUTH_TOKEN="$AGENT_FORGE_FIXTURE_TOKEN" npm run eval -- --url "$fixture_url" --strict --timeout 30000
```

Eval gates check real tool totals of 13 and 0, controlled rejection of missing input and an out-of-range total, session continuity within one process, and loading of the integer-totals skill. `--json` records actual events for inspection. For the missing input turn, Eve returns the tool input error to the mock model before recording an executed tool call. For the out-of-range sum, inspect `call.settled` for `ACTION_RESULT_FAILED`. Verify the recorded model starts name `eve-mock/agent-forge-total-fixture`.

## Check an event and continue its session

Use a fresh conversation ID for each qualification. Send a stable event ID and record its returned session ID.

```sh
fixture_conversation="sample-$(date +%s)"
fixture_endpoint="$fixture_url/fixture/events/$fixture_conversation"
curl --max-time 16 -sS -w '\n%{http_code}\n' "$fixture_endpoint" \
  -H "Authorization: Bearer $AGENT_FORGE_FIXTURE_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"eventId":"first","values":[4,0,9]}'
```

Require HTTP 200, `status: "completed"`, `outcome: "handled"`, and `reply: "Total: 13"`. Record the session ID and read the session's tool and turn events:

```sh
node scripts/read-session.mjs "$AGENT_FORGE_FIXTURE_PORT" "$fixture_session_id"
```

Repeat with the same event ID and values, then repeat with the same key and different valid values. In this fixture, first delivery wins while the key is remembered. Both retries must settle as `ignored`, without a second turn or total. Eve remembers the last 1,024 keys per session. This is bounded delivery deduplication. For a production requirement to reject payload identity conflicts or reconcile effects, maintain an atomic intent record and authoritative effect readback.

Send a request without bearer auth and expect 401. Send malformed JSON or an invalid integer event under valid auth and expect 400. Read the stream again to confirm rejected requests did not start turns or execute the total tool. A 202 `unobserved` result carries a receipt for follow-up and leaves work uncertain. Reuse the existing operation identity and inspect the recorded session before attempting recovery.

Save the session ID and the SDK's reported `nextIndex`. Stop the owned server and confirm its PID and listener are gone. Leave `.eve/.workflow-data` in place. Restart from the same app path, pinned version, token, and port with an additional `--resume` flag. Confirm the new PID and ready health. Post a new event to the same conversation:

```sh
curl --max-time 16 -sS -w '\n%{http_code}\n' "$fixture_endpoint" \
  -H "Authorization: Bearer $AGENT_FORGE_FIXTURE_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"eventId":"second","values":[2,0,5]}'
node scripts/read-session.mjs "$AGENT_FORGE_FIXTURE_PORT" "$fixture_session_id" "$fixture_next_index"
```

Require the same session ID and independently computed total 7. From the saved cursor, see the new turn without replaying old events. From cursor 0, check the original turn remains present and the new turn follows it. Stop the owned server and verify the listener is gone. This exercise covers idle-session restart on the same version.

## Check one schedule dispatch

While the local dev server is running, send one POST to `$fixture_url/eve/v1/dev/schedules/fixture-total`. Use the returned session ID with `scripts/read-session.mjs` and look for tool output 3 and the settled reply `Total: 3`. The development trigger performs one dispatch. Hosted cadence, crash recovery during an effect, external exactly-once delivery, sandbox isolation, and model quality each require separate qualification.

## Verify scoped child launches with a shared budget

Use the same pinned local fixture and bearer token. Before starting its dev server, set a ledger path inside the fixture's ignored state directory. Preserve this path and `.eve/.workflow-data` for any later readback. Choose a fresh ledger path for an unrelated run.

```sh
mkdir -p .eve
export AGENT_FORGE_DELEGATION_DB="$PWD/.eve/delegation.sqlite"
EVE_TELEMETRY_DISABLED=1 npm run dev -- --host 127.0.0.1 --port "$AGENT_FORGE_FIXTURE_PORT" --no-ui --no-default-extensions
```

After the ready health check, run this from the second terminal with the same fixture token and port:

```sh
node scripts/check-delegation.mjs "$AGENT_FORGE_FIXTURE_PORT" '[4,0,9]' 13
node scripts/check-delegation.mjs "$AGENT_FORGE_FIXTURE_PORT" '[2,0,5]' 7
```

The script makes new budget IDs each time and takes the independently expected integer as an argument. It checks real scoped child sessions and calls, root-to-child identity, parent integration, two root sessions competing for one active slot, zero and depth denial, missing and invalid budgets, exhaustion, and forbidden launch attempts. It reads a committed child result from the original handle after the workflow withholds its integration receipt and the original caller leaves its result unread and verifies that a duplicate stays within the original reservation. It also reserves one launch and injects an observation gap before the first send. An absent child receipt leaves that reservation pending and the slot consumed. The mock child parser reads the caller payload after Eve rc.9's specialist preamble.

For manual inspection, POST an authenticated limit grant to `/fixture/delegation/budgets/<budgetId>` with JSON fields `maxDepth`, `maxConcurrency`, `maxWorkers`, and `ttlMs`. The grant is immutable. In a root SDK session, send `delegate {"budgetId":"example","launchId":"first","values":[4,0,9],"mode":"normal"}`. The fixture also supports `hold` for overlap, `uncertain` for a withheld result after the child's recorded completion, `unresolved` for an observation gap before send, and `probe` for a blocked nested launch attempt.

Inspect the returned parent session and call IDs, and match `child.opened` and `child.sent` in the parent stream. Read the child stream through the SDK using the `child.opened` event. The root and child should expose the tools tested by the check script. To reconcile a pending launch, use an authenticated POST to `/fixture/delegation/budgets/<budgetId>/launches/<launchId>/reconcile`. The route reads the same parent and child histories without sending another message. HTTP 202 preserves unresolved state. A completed recovery records the original child session and delivery IDs. A different payload under an existing launch key conflicts.

Stop the dev server and verify its process and listener exited. This fixture enforces count, depth and concurrency at one local admission gate. It does not measure strict shared model token or dollar caps. The deliberate gaps cover child completion before integration and reservation before send. Active-child recovery after a server crash, provider effects and distributed enforcement require separate tests.

## Qualify the local browser client (check-browser)

Keep one Eve process and one gateway process for this fixture copy. Use the same Node 24 / locked Eve install verified above. The browser bundle also pins Rolldown 1.2.16; generated `dist/` is disposable.

1. In the Eve terminal, use an isolated checkout, choose two free loopback ports, set three distinct synthetic fixture tokens, build the UI, then run Eve in the foreground. Run the gateway in a second terminal with the same environment (repeat the exports there). Replace the placeholder values with distinct synthetic tokens of at least 12 visible ASCII characters and no spaces. Use the operator token only in the terminals; the browser takes only a browser token. The fixture explicitly selects just-bash 3.6.0 with automatic installation disabled for root and child; sandbox initialization fails when the pinned dependency is missing, without installing it or changing the manifest.

   ```sh
   export AGENT_FORGE_FIXTURE_PORT=24731 AGENT_FORGE_BROWSER_PORT=24732
   export AGENT_FORGE_FIXTURE_TOKEN="<synthetic operator token>"
   export AGENT_FORGE_BROWSER_TOKEN_A="<synthetic Alice token>"
   export AGENT_FORGE_BROWSER_TOKEN_B="<synthetic Bob token>"
   npm run browser:build
   EVE_TELEMETRY_DISABLED=1 node node_modules/eve/bin/eve.js dev --host 127.0.0.1 --port "$AGENT_FORGE_FIXTURE_PORT" --no-ui --no-default-extensions
   ```

   In the gateway terminal, wait for ready health, then run the gateway in the foreground:

   ```sh
   curl -fsS --max-time 5 "http://127.0.0.1:$AGENT_FORGE_FIXTURE_PORT/eve/v1/health"
   node browser/serve.mjs
   ```

2. Open `http://127.0.0.1:24732/` (or the chosen gateway port). Enter the Alice token, click **New session**, and send `total [4,0,9]`. Verify **Agent: Total: 13** and **Server turn: completed**. Copy the session ID and note the cursor.
3. Click **Disconnect stream**. Send the changed input `total [2,0,5]` and observe the acceptance receipt. The transcript remains unchanged while detached. Click **Attach or reconnect** without changing the token or ID. Verify the same session, connection from the saved nonzero cursor, and exactly one reply each for 13 and 7. Reload the page only if you are testing replay: type the token and saved ID, and attach. Reload rebuilds history from cursor zero; the in-memory cursor is retained only while the page stays open.
4. Send `wait`. When **Tool: fixture_wait started** appears, click **Cancel server turn** within 30 seconds. Keep the reader connected. Require **Tool: fixture_wait interrupted** and **Server turn: cancelled**, and no **Agent: Wait completed**. The wait has no external effect. A cancel submission alone is only an accepted control; the durable terminal event proves what happened.
5. Replace the token with Bob's while leaving Alice's session ID in place and attach. Require HTTP 403 and an empty conversation. Bob can create and read his own session. An invalid token gets 401. Run the SDK cross-check in another terminal with the same environment to independently check guarded server cancellation, both changed totals, a distinct Bob session, and rejection of Bob's read, prepare, send and cancel requests for Alice's session:

   ```sh
   node browser/verify.mjs
   ```

6. Stop the gateway and Eve in their respective foreground terminals. Confirm neither selected port listens (e.g. with `lsof -nP -iTCP:"$AGENT_FORGE_BROWSER_PORT" -iTCP:"$AGENT_FORGE_FIXTURE_PORT" -sTCP:LISTEN`). Do not stop an unrelated process if a chosen port is occupied.

The gateway only forwards text-session creation, owner-scoped stream/prepare/send, and owner-scoped cancellation with an explicit turn ID. A bearer proves identity at the gateway; the gateway checks an application-owned session record before forwarding. Eve's private trace audience and its backend bearer alone do not enforce this browser ownership rule. Eve sees requests from the local operator service; Alice and Bob are identities at the gateway. Neither browser bearer authenticates directly to the Eve backend. The gateway does not expose the operator token, other Eve routes, or cross-origin browser access. Credentials stay in runtime environment or browser memory, and are not bundled.

The ownership file is local ignored runtime data in `.eve/fixture-browser-owners.json`. The gateway writes a same-directory temporary file and renames it over the ownership file before acknowledging create. An ordinary gateway restart reads the ownership file. Keep the previous app source and the ignored ownership file separate when rolling back; stop the one owner before restoring source, and preserve ownership records for sessions already admitted. After a lost create response or interrupted record write, inspect the exact receipt, the recorded binding and Eve session before deciding whether to retry. Do not guess an owner or infer successful creation from an unconfirmed attempt. This assumes one gateway owner, a private fixture directory, and an unchanged Eve store and operator configuration. It does not qualify concurrent replicas, lost storage, abrupt interruption, or protection against someone with access to the local operator, runtime files or process. A request that loses its create receipt may have created a session; retain that uncertainty and reconcile evidence before retrying. Do not use this fixture as production authentication or expose it beyond loopback.

## Keep development dependencies fixed

The first combined run let Eve choose its default local sandbox. On session preparation it installed an optional just-bash package and rewrote the manifest/lock. This fixture now pins just-bash 3.6.0 and selects it explicitly in both sandbox definitions with `autoInstall: false`. Verify Eve, just-bash and Rolldown against the manifest, lock and installed packages before running. Compare package.json and package-lock.json hashes again after the runtime checks. A missing dependency is a setup failure; do not silently install a moving version during a run.

just-bash supplies a virtual filesystem for this local fixture. It provides neither native process isolation nor network isolation. The fixture's authored tools run in the application process and keep their own scoped contracts. No hostile sandbox or deployment boundary is qualified here.

## Saved recovery lesson

The specialist mock uses a fresh one-message session per launch. After an interrupted step, Eve can assign a new call ID. Match the latest result for the actual scoped tool and validate it against that message's input; a literal original call-ID lookup ignored a successful recovery result and caused repeated work.

One qualified same-version local test killed the owned Eve process after `scoped_total` started but before it settled, then resumed the same store without a new message. The original call was abandoned, one retry returned14, and the original parent integrated14 once. Readback returned that result from the same consumed reservation. Fresh inputs14 and7 then passed `check-delegation`. For a new deployment, separately reproduce the interruption boundary and inspect original session, delivery, call and ledger evidence. Pure tools may run again after interruption; protected effects need resource-side idempotency and authoritative reconciliation. Keep unresolved state consumed. Do not infer migrations or external-effect guarantees from this arithmetic fixture.
