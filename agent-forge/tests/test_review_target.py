import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CASE = Path(__file__).resolve().parents[1]
SCRIPT = Path(os.environ.get(
    "AGENT_FORGE_REVIEW_TARGET",
    CASE / "scripts" / "review_target.py",
))


class ReviewTargetTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Review Fixture")
        self.git("config", "user.email", "review-fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.autocrlf", "false")
        self.write("alpha.txt", "base-alpha\n")
        self.write("beta.txt", "base-beta\n")
        self.git("add", ".")
        self.git("commit", "-qm", "root")
        self.root = self.git("rev-parse", "HEAD")

    def git(self, *args):
        process = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        return process.stdout.strip()

    def write(self, path, text):
        (self.repo / path).write_text(text)

    def commit_all(self, title):
        self.git("add", ".")
        self.git("commit", "-qm", title)
        return self.git("rev-parse", "HEAD")

    def snapshot(self):
        return {
            path.relative_to(self.repo): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.repo.rglob("*")
            if path.is_file()
        }

    def review(self, *args, returncode=0):
        before = self.snapshot()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(result.returncode, returncode, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_uncommitted_preserves_both_stages_and_untracked(self):
        self.write("alpha.txt", "index-alpha\n")
        self.git("add", "alpha.txt")
        self.write("alpha.txt", "base-alpha\n")
        self.write("new file.txt", "untracked\n")
        self.write(".git/info/exclude", "ignored.txt\n")
        self.write("ignored.txt", "ignored\n")

        output = self.review("uncommitted")
        self.assertIn("+index-alpha\n", output["patches"]["staged"])
        self.assertIn("+base-alpha\n", output["patches"]["unstaged"])
        self.assertEqual(output["untracked"], ["new file.txt"])
        scoped = self.review("custom", "--path", "new file.txt")
        self.assertEqual(scoped["untracked"], ["new file.txt"])
        self.assertEqual(scoped["patches"], {"staged": "", "unstaged": ""})

    def test_unborn_index_and_clean_commit(self):
        self.git("checkout", "--orphan", "new")
        self.git("rm", "-qf", "alpha.txt", "beta.txt")
        self.write("seed.txt", "new root\n")
        self.git("add", "seed.txt")
        output = self.review("uncommitted")
        self.assertIsNone(output["head"])
        self.assertIn("+new root\n", output["patches"]["staged"])
        self.git("commit", "-qm", "new root")
        self.assertEqual(self.review("uncommitted")["patches"], {"staged": "", "unstaged": ""})

    def test_base_uses_ahead_configured_upstream_and_merge_base(self):
        self.git("remote", "add", "mirror", "https://example.invalid/repo.git")
        self.git("config", "remote.mirror.fetch", "+refs/heads/*:refs/tracking/mirror/*")
        self.git("config", "branch.main.remote", "mirror")
        self.git("config", "branch.main.merge", "refs/heads/trunk")
        self.git("checkout", "-qb", "upstream-work")
        self.write("beta.txt", "upstream-beta\n")
        upstream = self.commit_all("upstream improvement")
        self.git("update-ref", "refs/tracking/mirror/trunk", upstream)
        self.git("checkout", "-qb", "feature")
        self.write("alpha.txt", "feature-alpha\n")
        head = self.commit_all("feature")
        self.git("checkout", "-q", "--detach", upstream)
        self.write("beta.txt", "upstream-later\n")
        later = self.commit_all("later upstream improvement")
        self.git("update-ref", "refs/tracking/mirror/trunk", later)
        self.git("checkout", "-q", "feature")

        output = self.review("base", "main")
        self.assertEqual(output["local_commit"], self.root)
        self.assertEqual(output["head"], head)
        self.assertEqual(output["comparison_commit"], later)
        self.assertEqual(output["merge_base"], upstream)
        self.assertIn("+feature-alpha\n", output["patches"]["merge_base_to_worktree"])
        self.assertNotIn("beta.txt", output["patches"]["merge_base_to_worktree"])

        self.git("update-ref", "-d", "refs/heads/main")
        fallback = self.review("base", "refs/heads/main")
        self.assertIsNone(fallback["local_commit"])
        self.assertEqual(fallback["comparison_ref"], "refs/tracking/mirror/trunk")
        self.assertEqual(fallback["patches"], output["patches"])
        self.git("update-ref", "-d", "refs/tracking/mirror/trunk")
        self.assertIn("Unavailable base", self.review("base", "main", returncode=2)["error"])

    def test_upstream_selected_if_it_has_unmerged_commits(self):
        self.git("checkout", "-qb", "other")
        self.write("beta.txt", "other-beta\n")
        other = self.commit_all("other")
        self.git("checkout", "-q", "main")
        self.write("alpha.txt", "local-alpha\n")
        local = self.commit_all("local")
        self.git("config", "branch.main.remote", ".")
        self.git("config", "branch.main.merge", "refs/heads/other")
        result = self.review("base", "main")
        self.assertEqual(result["upstream_commit"], other)
        self.assertEqual(result["comparison_commit"], other)
        self.assertEqual(result["local_commit"], local)
        self.assertEqual(result["merge_base"], self.root)
        self.git("config", "branch.main.merge", "refs/heads/ancestor")
        self.git("branch", "ancestor", self.root)
        self.assertEqual(self.review("base", "main")["comparison_commit"], local)

    def test_commit_root_merge_parent_and_custom_scope(self):
        initial = self.review("commit", self.root)
        self.assertEqual(initial["parents"], [])
        self.assertIn("+base-alpha\n", initial["patches"]["commit"])
        self.assertIn("+base-beta\n", initial["patches"]["commit"])

        self.git("checkout", "-qb", "side")
        self.write("alpha.txt", "side-alpha\n")
        self.commit_all("side")
        self.git("checkout", "-q", "main")
        self.write("beta.txt", "main-beta\n")
        first_parent = self.commit_all("main")
        self.git("merge", "-q", "--no-ff", "-m", "merge", "side")
        self.assertIn("Select --parent", self.review("commit", "HEAD", returncode=2)["error"])
        result = self.review("commit", "HEAD", "--parent", "1")
        self.assertEqual(result["parent"], first_parent)
        self.assertIn("+side-alpha\n", result["patches"]["commit"])
        self.assertNotIn("beta.txt", result["patches"]["commit"])
        scoped = self.review("custom", "--from-ref", self.root, "--to-ref", "HEAD", "--path", "beta.txt")
        self.assertIn("+main-beta\n", scoped["patches"]["custom"])
        self.assertNotIn("alpha.txt", scoped["patches"]["custom"])
        self.assertIn("Invalid revision", self.review("commit", "--", "--ref-placeholder", returncode=2)["error"])

    def test_shallow_boundary_reports_missing_parent(self):
        self.write("alpha.txt", "later-alpha\n")
        head = self.commit_all("new tip")
        self.write(".git/shallow", f"{head}\n")
        # Remove the loose parent object to represent a depth-one checkout.
        (self.repo / ".git" / "objects" / self.root[:2] / self.root[2:]).unlink()
        result = self.review("commit", "HEAD", returncode=2)
        self.assertIn(self.root, result["error"])

    def test_external_diff_textconv_and_clean_filter_stay_disabled(self):
        self.write(".gitattributes", "alpha.txt diff=fixture filter=fixture\n")
        self.commit_all("attributes")
        marker = "sh -c 'touch unexpected-external-command'"
        self.git("config", "diff.external", marker)
        self.git("config", "diff.fixture.command", marker)
        self.git("config", "diff.fixture.textconv", marker)
        self.git("config", "filter.fixture.clean", marker)
        self.git("config", "filter.fixture.required", "true")
        self.git("config", "filter.ambient.clean", marker)
        self.write("alpha.txt", "replacement\n")

        output = self.review("uncommitted")
        self.assertTrue({"fixture", "ambient"}.issubset(output["disabled_worktree_filters"]))
        self.assertIn("+replacement\n", output["patches"]["unstaged"])
        self.assertFalse((self.repo / "unexpected-external-command").exists())


if __name__ == "__main__":
    unittest.main()
