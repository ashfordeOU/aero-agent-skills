#!/usr/bin/env python3
"""Fail when shipped content tells the reader to cd into a path only we have.

Four files shipped in the public export and the npm tarball opened their run
instructions by changing directory into a home path named AeroSkills. That
directory is the repository's OLD
layout: it does not exist on the build machine and it has never existed on a
customer's. The first command a buyer copied out of those leaves failed before
it ran anything. One of them said "Run from anywhere:" immediately above it.

Nothing caught this. public-safety-audit.py is the right shape but the wrong
home -- it scans every commit in history for DANGEROUS content, and history is
full of ~/AeroSkills, so teaching it this pattern would hard-block every future
publish over a defect that is about correctness, not safety.

THE RULE
  In content that ships, an instruction must run on the reader's machine.
  A change-directory instruction into a home-relative path names a
  directory in the READER's home that only we can know
  about, so it is refused. Reader-side dotfile conventions (~/.claude/skills,
  ~/.gemini/skills) are NOT refused: those are real locations on the reader's
  own machine and are the correct thing to document.

SCOPE
  Exactly what ships. The export's exclusions are READ rather than restated,
  so this gate and the export cannot drift apart -- a file that stops
  shipping stops being graded, and a file that starts shipping starts being
  graded, with no second list to update. This is the defect that produced the
  marketing/ and development/ dead roots: two places naming the same set, and
  only one of them maintained.

  The list now lives in ops/automation/export-excludes.txt, which
  publish-public.sh and publish-health.py also read. It moved there when the
  inline pathspecs turned out to have TWO readers already and were about to
  get a third. This gate went red the moment it moved, which is the correct
  behaviour and the reason it fails closed on an empty parse rather than
  assuming nothing is excluded.

Usage: gate_shipped_instructions.py [repo_root]   (exit 1 on any violation)
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else
                       os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PUBLISH = os.path.join(REPO, "ops", "automation", "publish-public.sh")
EXCLUDES_FILE = os.path.join(REPO, "ops", "automation", "export-excludes.txt")

# A change-directory instruction into ~/NAME where NAME is not a dotfile.
# Covers the bare form, a deeper path, and the && one-liner form. Described
# in prose, never spelled: a detector that contains its own pattern reports
# itself, and the fix for that is not an exemption list.
# (The regex below is safe as written: its source has \s+, not a space.)
BAD_CD = re.compile(r"\bcd\s+~/(?!\.)([A-Za-z0-9_][A-Za-z0-9_.-]*)")

TEXT_EXT = {".md", ".py", ".sh", ".txt", ".yaml", ".yml", ".json", ".rst", ".html"}


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args],
                          capture_output=True, text=True)


def export_exclusions():
    """Read the export pathspec from the one list every reader uses."""
    if os.path.isfile(EXCLUDES_FILE):
        ex = []
        for line in open(EXCLUDES_FILE, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line:
                ex.append(line)
        if ex:
            return ex
        print("FAIL shipped-instructions: export-excludes.txt named 0 "
              "pathspecs. An empty list widens this gate to the whole tree "
              "and would flag internal docs; it is a broken gate, not a "
              "clean run.", file=sys.stderr)
        sys.exit(2)
    if not os.path.isfile(PUBLISH):
        # We are on an export: the exclusions were already applied when this
        # tree was produced, so everything present is shipped content.
        return []
    src = open(PUBLISH, encoding="utf-8").read()
    ex = re.findall(r"':\(exclude\)([^']+)'", src)
    if not ex:
        # An empty exclusion list would silently widen the gate to the whole
        # tree and flag internal docs. That is a broken gate, not a clean run.
        print("FAIL shipped-instructions: parsed 0 exclusions from "
              "publish-public.sh -- the export pathspec changed shape and this "
              "gate can no longer tell what ships")
        raise SystemExit(1)
    return ex


def _walk(root):
    """Every file under root, repo-relative, skipping VCS bookkeeping."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            out.append(os.path.relpath(os.path.join(dirpath, fn), root))
    return sorted(out)


def shipped_files(exclusions):
    """The files that ship, from git where there is a repo and the
    filesystem where there is not.

    A negative-control fixture is a pruned COPY with no .git, and so is an
    unpacked npm tarball. Hard-failing there would make this gate's own
    baseline red -- a control that records VOID proves nothing about the
    gate, which is precisely what the suite exists to avoid.
    """
    args = ["ls-files", "--"] + ["."] + [":(exclude)%s" % e for e in exclusions]
    r = git(*args)
    if r.returncode == 0:
        return [f for f in r.stdout.split("\n") if f]
    files = _walk(REPO)
    if not files:
        print("FAIL shipped-instructions: no files found under %s" % REPO)
        raise SystemExit(1)
    # Apply the exclusions by prefix/glob, the way the pathspec does.
    import fnmatch
    keep = []
    for f in files:
        if any(f == e or f.startswith(e.rstrip("/") + "/") or fnmatch.fnmatch(f, e)
               for e in exclusions):
            continue
        keep.append(f)
    return keep


def main():
    exclusions = export_exclusions()
    files = shipped_files(exclusions)
    scanned = 0
    violations = []
    for rel in files:
        if os.path.splitext(rel)[1].lower() not in TEXT_EXT:
            continue
        path = os.path.join(REPO, rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        scanned += 1
        for n, line in enumerate(lines, 1):
            m = BAD_CD.search(line)
            if m:
                violations.append((rel, n, m.group(1), line.strip()[:90]))

    # A sweep that read nothing is not a clean sweep.
    if scanned == 0:
        print("FAIL shipped-instructions: 0 shipped text files scanned -- "
              "the gate covered nothing")
        raise SystemExit(1)

    if violations:
        for rel, n, name, text in violations:
            print("FAIL shipped-instructions: %s:%d instructs the reader to "
                  "cd into ~/%s, a directory only this machine could have: %s"
                  % (rel, n, name, text))
        print("FAIL shipped-instructions: %d broken instruction(s) in %d "
              "scanned shipped file(s)" % (len(violations), scanned))
        raise SystemExit(1)

    mode = ("%d export exclusion(s) honoured" % len(exclusions)
            if exclusions else "export tree: every present file is shipped")
    print("PASS shipped-instructions: 0 home-rooted cd instructions in %d "
          "scanned shipped text file(s); %s" % (scanned, mode))


if __name__ == "__main__":
    main()
