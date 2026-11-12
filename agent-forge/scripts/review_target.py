#!/usr/bin/env python3
"""Resolve a local Git review target and emit its complete patch as JSON."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


DIFF_FLAGS = [
    "--no-ext-diff", "--no-textconv", "--no-color", "--no-relative",
    "--full-index", "--binary", "--find-renames", "--ignore-submodules=none",
    "--submodule=short", "--src-prefix=a/", "--dst-prefix=b/",
]


class TargetError(Exception):
    """A requested review scope could not be resolved."""


class Git:
    def __init__(self, directory: Path):
        self.directory = directory
        self.options = ["-c", "core.fsmonitor=false"]
        self.environment = dict(os.environ)
        for name in (
            "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
            "GIT_PREFIX", "GIT_EXTERNAL_DIFF", "GIT_DIFF_OPTS",
        ):
            self.environment.pop(name, None)
        self.environment.update({
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_ALLOW_PROTOCOL": "",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "LC_ALL": "C",
        })
        self.directory = Path(self.read("rev-parse", "--show-toplevel").rstrip("\n"))

    def run(self, *arguments, allowed=(0,)):
        process = subprocess.run(
            ["git", "--no-pager", *self.options, *arguments],
            cwd=self.directory,
            env=self.environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode not in allowed:
            error = process.stderr.decode("utf-8", "replace").strip()
            raise TargetError(error or f"Git {arguments[0]} failed ({process.returncode})")
        return process

    def read(self, *arguments, allowed=(0,)):
        return self.run(*arguments, allowed=allowed).stdout.decode("utf-8", "surrogateescape")

    def commit(self, ref, *, required=True):
        validate_ref(ref)
        value = self.read(
            "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}",
            allowed=(0, 1),
        ).strip()
        if required and not value:
            raise TargetError(f"Commit or ref unavailable: {ref}")
        return value or None

    def settings(self, key):
        values = self.read("config", "--null", "--get-all", key, allowed=(0, 1))
        return values.split("\0")[:-1]

    def disable_worktree_filters(self):
        keys = self.read(
            "config", "--null", "--name-only", "--get-regexp",
            r"^filter\..*\.(clean|process|required)$", allowed=(0, 1),
        ).split("\0")[:-1]
        for key in sorted(set(keys)):
            if "=" in key:
                raise TargetError("Cannot safely override a configured worktree filter")
            value = "false" if key.endswith(".required") else ""
            self.options.extend(["-c", f"{key}={value}"])
        return sorted({key.rsplit(".", 1)[0][7:] for key in keys})

    def diff(self, arguments, paths, *, root_commit=False):
        command = ["diff-tree", "--root", "-r", "-p", "--no-commit-id"] if root_commit else ["diff"]
        return self.read(*command, *DIFF_FLAGS, *arguments, "--", *paths)


def validate_ref(ref):
    if not ref or ref.startswith("-") or any(char in ref for char in "\0\r\n"):
        raise TargetError(f"Invalid revision: {ref!r}")


def refspec_match(pattern, name):
    if "*" not in pattern:
        return "" if pattern == name else None
    prefix, suffix = pattern.split("*", 1)
    if name.startswith(prefix) and name.endswith(suffix) and len(name) >= len(prefix) + len(suffix):
        return name[len(prefix):len(name) - len(suffix)]
    return None


def configured_upstream(git, branch):
    """Resolve branch config even when refs/heads/<branch> is absent."""
    remotes = git.settings(f"branch.{branch}.remote")
    merges = git.settings(f"branch.{branch}.merge")
    if not remotes or not merges:
        return None
    if len(merges) != 1:
        raise TargetError(f"Several configured merge refs for {branch}")
    remote, merge_ref = remotes[-1], merges[0]
    if remote == ".":
        return merge_ref

    refspecs = git.settings(f"remote.{remote}.fetch")
    for refspec in refspecs:
        if refspec.startswith("^") and refspec_match(refspec[1:], merge_ref) is not None:
            return None

    candidates = set()
    for refspec in refspecs:
        if refspec.startswith("^"):
            continue
        source, separator, destination = refspec.lstrip("+").partition(":")
        if not separator or not destination:
            continue
        match = refspec_match(source, merge_ref)
        if match is not None:
            candidates.add(destination.replace("*", match))
    if len(candidates) > 1:
        raise TargetError(f"Several configured upstream destinations for {branch}")
    return next(iter(candidates), None)


def review_base(git, branch_ref, paths):
    validate_ref(branch_ref)
    branch = branch_ref.removeprefix("refs/heads/")
    if git.run("check-ref-format", f"refs/heads/{branch}", allowed=(0, 1)).returncode:
        raise TargetError(f"Invalid local branch name: {branch_ref!r}")

    local_ref = f"refs/heads/{branch}"
    local = git.commit(local_ref, required=False)
    upstream_ref = configured_upstream(git, branch)
    upstream = git.commit(upstream_ref, required=False) if upstream_ref else None
    comparison_ref, comparison = local_ref, local
    if upstream and (
        local is None
        or (local != upstream and int(git.read("rev-list", "--count", f"{local}..{upstream}")) > 0)
    ):
        comparison_ref, comparison = upstream_ref, upstream
    if comparison is None:
        suffix = f" or configured upstream {upstream_ref}" if upstream_ref else ""
        raise TargetError(f"Unavailable base: {local_ref}{suffix}")

    head = git.commit("HEAD")
    merge_bases = git.read("merge-base", "--all", head, comparison, allowed=(0, 1)).splitlines()
    if len(merge_bases) != 1:
        raise TargetError("Expected one merge base with HEAD. Specify the comparison explicitly.")
    merge_base = merge_bases[0]
    return {
        "local_ref": local_ref,
        "local_commit": local,
        "upstream_ref": upstream_ref,
        "upstream_commit": upstream,
        "comparison_ref": comparison_ref,
        "comparison_commit": comparison,
        "head": head,
        "merge_base": merge_base,
        "patches": {"merge_base_to_worktree": git.diff([merge_base], paths)},
    }


def review_commit(git, ref, parent_index, paths):
    commit = git.commit(ref)
    header, _, _ = git.read("cat-file", "commit", commit).partition("\n\n")
    parents = [line[7:] for line in header.splitlines() if line.startswith("parent ")]
    if len(parents) > 1 and parent_index is None:
        raise TargetError(f"Merge commit has {len(parents)} parents. Select --parent 1 through {len(parents)}.")
    if parent_index is not None and not 1 <= parent_index <= len(parents):
        raise TargetError(f"Invalid --parent {parent_index}: commit has {len(parents)} parents")
    parent = parents[(parent_index or 1) - 1] if parents else None
    arguments = [parent, commit] if parent else [commit]
    return {
        "commit": commit,
        "parents": parents,
        "parent": parent,
        "patches": {"commit": git.diff(arguments, paths, root_commit=parent is None)},
    }


def review_uncommitted(git, paths):
    others = git.read("ls-files", "--others", "--exclude-standard", "-z", "--", *paths)
    return {
        "head": git.commit("HEAD", required=False),
        "patches": {
            "staged": git.diff(["--cached"], paths),
            "unstaged": git.diff([], paths),
        },
        "untracked": others.split("\0")[:-1],
    }


def review_custom(git, from_ref, to_ref, paths):
    if to_ref and not from_ref:
        raise TargetError("--to-ref requires --from-ref")
    if not from_ref:
        if not paths:
            raise TargetError("Specify a path scope or --from-ref")
        return review_uncommitted(git, paths)
    source = git.commit(from_ref)
    target = git.commit(to_ref) if to_ref else None
    arguments = [source, target] if target else [source]
    result = {
        "from_commit": source,
        "to_commit": target,
        "patches": {"custom": git.diff(arguments, paths)},
    }
    if target is None:
        others = git.read("ls-files", "--others", "--exclude-standard", "-z", "--", *paths)
        result["untracked"] = others.split("\0")[:-1]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    modes = parser.add_subparsers(dest="mode", required=True)
    uncommitted = modes.add_parser("uncommitted")
    base = modes.add_parser("base")
    base.add_argument("branch")
    commit = modes.add_parser("commit")
    commit.add_argument("ref")
    commit.add_argument("--parent", type=int)
    custom = modes.add_parser("custom")
    custom.add_argument("--from-ref")
    custom.add_argument("--to-ref")
    for mode in (uncommitted, base, commit, custom):
        mode.add_argument("--path", action="append", default=[], help="Git pathspec relative to repo root")
    args = parser.parse_args(argv)

    try:
        git = Git(args.repo)
        worktree = args.mode in ("uncommitted", "base") or (
            args.mode == "custom" and not args.to_ref
        )
        disabled = git.disable_worktree_filters() if worktree else []
        if args.mode == "base":
            target = review_base(git, args.branch, args.path)
        elif args.mode == "commit":
            target = review_commit(git, args.ref, args.parent, args.path)
        elif args.mode == "custom":
            target = review_custom(git, args.from_ref, args.to_ref, args.path)
        else:
            target = review_uncommitted(git, args.path)
        print(json.dumps({
            "mode": args.mode,
            "repository": str(git.directory),
            "paths": args.path,
            "disabled_worktree_filters": disabled,
            **target,
        }))
        return 0
    except (OSError, TargetError) as error:
        print(json.dumps({"mode": args.mode, "error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
