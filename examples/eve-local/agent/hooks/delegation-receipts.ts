import { defineHook } from "eve/hooks";
import { recordChild } from "../lib/delegation-ledger.js";

export default defineHook({
  events: {
    "child.opened"(event, ctx) {
      if (event.data.name !== "specialist" || !("callId" in event.data.owner)) return;
      recordChild(ctx.session.id, event.data.owner.callId, event.data.sessionId);
    },
  },
});
