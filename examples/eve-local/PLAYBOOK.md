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
