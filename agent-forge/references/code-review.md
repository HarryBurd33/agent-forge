# Review a specified code change

A review request authorizes inspection. Keep the worktree, index, refs, and remote review surfaces read-only. Perform the review yourself and return findings to the requester. Editing, committing, pushing, posting, delegation, and repair belong to separately authorized work.

## Resolve the target

Read applicable `AGENTS.md`, including path-specific instructions for changed files. Resolve and record the actual comparison before evaluating the patch.

- **Uncommitted changes** include both index versus HEAD and working tree versus index. Read both so an unstaged change that reverses a staged change cannot hide either. Enumerate and read relevant untracked, non-ignored files. If the branch is unborn, inspect the staged additions, working tree changes, and untracked inventory.
- **Base branch** uses its local tip unless the configured upstream has commits the local tip lacks, including when the branches diverged. If the local branch is absent, explicitly resolve its configured upstream. Use existing local refs. Compute the merge base with HEAD and read the entire tracked diff from that commit, including the tracked worktree if present. If comparison refs or the merge base cannot be resolved, report the target gap.
- **Commit** uses the commit's delta against its parent, or the empty tree for a root commit. A merge may need its mainline parent or separately requested parent comparisons. State the selected parent and why it represents the requested change. Ask for the parent when it materially changes the review and the supplied intent does not settle it.
- **Custom** uses the requested commits, worktree, paths, or supplied patch. Follow the specified scope and record any unavailable portions.

The optional Python 3.9+ [Git helper](../scripts/review_target.py) returns JSON containing resolved metadata, whole patch strings, and paths for untracked files that need separate inspection. For example:

```sh
python3 scripts/review_target.py --repo /path/to/repo uncommitted
python3 scripts/review_target.py --repo /path/to/repo base main
python3 scripts/review_target.py --repo /path/to/repo commit HEAD --parent 1
python3 scripts/review_target.py --repo /path/to/repo custom --from-ref release --to-ref HEAD --path src/
```

Use an output surface that preserves the complete result. If output or context truncates it, read it in verified path groups and reconcile all groups against the changed-file inventory. Treat untracked and binary contents, submodule revisions, and missing Git objects as explicit inspection needs. The helper lists any external worktree filters it disabled. If filters affect a reviewed path, compare that path with the intended normalization in an isolated context. The helper selects and prints Git data. Use code inspection to determine defects.

## Inspect the change

Read every in-scope hunk and enough unchanged context, tests, and callers to trace the affected behavior. Continue after the first finding. Account for input ranges, expected compatibility, lifecycle, error paths, and authority when the change affects them. Review relevant tests and reproduce scenarios with read-only checks. State the verification gap when a check requires changing files or producing external effects.

Report a defect when the reviewed change introduced it, it has a demonstrable triggering case and meaningful impact, it admits a concrete fix, and the author would likely act on it. Omit existing defects, unsupported hypotheses, intentional behavior, and style preferences. Keep reading unrelated hunks in scope after confirming a defect. Combine symptoms with the same cause when a single finding identifies the fix.

## Return findings

Lead with all qualifying issues in severity order. Use one entry per issue, with a short imperative title and a tight path and line anchor overlapping the diff. For example, `[P2] Preserve zero balances — src/billing.py:42`. Follow with the triggering conditions, affected code path, and actual consequence. Use inline review annotations when the host supports them and they are part of the requested reply surface.

- **P0** applies to a critical failure that blocks release generally.
- **P1** applies to an urgent defect to fix next.
- **P2** applies to an ordinary actionable defect.
- **P3** applies to a low-impact issue that warrants a fix.

When the completed review has no qualifying issues, begin with `No findings.` Follow the findings or that sentence with a brief overall assessment and any material coverage gaps. An unavailable target or incomplete inspection is a scope limitation. State what could be reviewed and what evidence is missing.
