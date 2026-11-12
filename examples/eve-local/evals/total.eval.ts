import { defineEval } from "eve/evals";
import { equals, includes } from "eve/evals/expect";

export default defineEval({
  timeoutMs: 30_000,
  async test(t) {
    const first = await t.send("total [4,0,9]");
    first.calledTool("total");
    t.check(first.reply, equals("Total: 13"));

    const second = await first.session.send("total [0]");
    second.calledTool("total");
    t.check(second.sessionId, equals(first.sessionId));
    t.check(second.reply, equals("Total: 0"));

    const invalid = await first.session.send("invalid");
    t.check(invalid.reply, equals("Total rejected"));

    const rangeError = await first.session.send("total [1000000,1]");
    t.check(rangeError.reply, equals("Total rejected"));

    const skill = await first.session.send("skill");
    skill.calledSkill("integer-totals");
    t.check(skill.reply, includes("integer-total-procedure"));
  },
});
