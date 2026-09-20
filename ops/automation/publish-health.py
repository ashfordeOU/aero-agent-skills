#!/usr/bin/env python3
"""Is what we built actually what is published?

Why this exists
---------------
On 2026-09-19 the public repo sat 18 hours and 672 leaves behind dev while
every dev gate stayed green. Three separate faults had each aborted the
hourly publish, and nothing reported any of them: a failing publish writes a
line to a log and exits, and the gate battery grades the TREE, never the
shipping path. "It is published" was an assumption the harness never checked.

This checks it. It is deliberately NOT part of `make validate`: validate is
offline and deterministic by contract, and this needs the network. It is the
release layer's check, not the corpus layer's.

The layers it compares, and deliberately does not conflate:

  content  every file, by git blob sha  -- the decisive one
  corpus   docs/metrics.json leaves     -- the free product
  evidence router cases gate 5 executes -- the proof for the corpus claim
  release  the newest published tag     -- what a consumer can actually get
  pipe     the last publish attempt     -- did the shipping path even run

WHY A LEAF COUNT WAS NOT ENOUGH (2026-09-20)
--------------------------------------------
Three consecutive hourly publishes aborted at public-ci-parity and pushed
nothing. This check printed "public is current within tolerance (0 leaves
behind)" through all three, and it was telling the truth about the only
thing it measured: the change had added six FILES and zero LEAVES. A
population count cannot see content, and the files it could not see
included the contract three repositories were about to be gated on.

So the decisive comparison is now per-file, by git blob sha -- content
addressing, so a sha equal on both sides means the bytes are equal, with no
download. And the pipe reports its own outcome: publish-public.sh writes an
attempt record on EVERY exit path, so "the publish never ran" and "the
publish ran and the trees match" stop looking identical from here.

A consumer sees the PUBLIC numbers. Dev being ahead is normal for minutes and
a defect for days, so the tolerance is a band: one 100-leaf band of drift is
in-flight work; more than that means the pipe is broken.

Exit status
-----------
    0  verified: public content is current within tolerance
    1  verified STALE: public is behind -- the publish pipe is broken
    2  COULD NOT VERIFY (no gh, no network, API refused)

2 is not a pass. A check that cannot run must not report success -- that is
the same rule the negative-control battery follows, and the reason this
script exists at all.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUBLIC_REPO = "ashfordeOU/aero-agent-skills"
METRICS = os.path.join(REPO, "docs", "metrics.json")
DEFAULT_TOLERANCE = 100          # one release band


def gh_bin():
    for c in (shutil.which("gh"), "/opt/homebrew/bin/gh", "/usr/local/bin/gh"):
        if c and os.path.exists(c):
            return c
    return None


def local_metrics():
    with open(METRICS, encoding="utf-8") as fh:
        m = json.load(fh)
    return m


def public_metrics(gh):
    """docs/metrics.json as the public repo currently serves it."""
    r = subprocess.run(
        [gh, "api", "repos/%s/contents/docs/metrics.json" % PUBLIC_REPO,
         "--jq", ".content"],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "gh failed").strip().splitlines()[-1])
    import base64
    return json.loads(base64.b64decode(r.stdout.strip()))


def newest_public_tag(gh):
    r = subprocess.run(
        [gh, "api", "repos/%s/tags" % PUBLIC_REPO, "--jq", ".[0].name"],
        capture_output=True, text=True, timeout=30)
    return r.stdout.strip() if r.returncode == 0 else None


EXCLUDES_FILE = os.path.join(REPO, "ops", "automation", "export-excludes.txt")
# Per repository, matching publish-public.sh. Four copies of that script
# exist on a dev machine and a shared filename let one corpus read the
# other's outcome -- caught by a record whose dev_head was not a commit in
# this repository at all.
STATE_FILE = os.environ.get(
    "AERO_PUBLISH_STATE_FILE",
    os.path.join(os.path.expanduser("~"), ".hermes", "state",
                 "aero-publish-last-%s.json" % os.path.basename(REPO)))

# Written INTO the export by publish-public.sh, AFTER the archive is
# extracted -- so the public copy is generated content that may differ from
# (or have no) dev-side counterpart. Excluded from all three buckets, not
# just "extra": .ci-native is tracked in dev AND rewritten at export, so
# comparing it reports a difference on every single run.
GENERATED_AT_EXPORT = {".ci-native", ".release-hold"}


def export_excludes(path=EXCLUDES_FILE):
    """The pathspecs publish-public.sh excludes. One file, two readers."""
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                out.append(line)
    return out


def dev_tree():
    """path -> blob sha for everything the export WOULD carry.

    `git ls-files -s` with the very same `:(exclude)` pathspecs the export
    uses, so git does the matching and this file does not reimplement
    pathspec semantics. Verified equal to `git archive | tar -t` file-for-
    file (14889 both ways) when the shared list was introduced.
    """
    excludes = export_excludes()
    if not excludes:
        raise RuntimeError(
            "export-excludes.txt named no pathspecs, so the comparison set "
            "would include the internal ops record and every publish would "
            "look broken")
    argv = ["git", "ls-files", "-s", "--", "."] + \
           [":(exclude)%s" % e for e in excludes]
    r = subprocess.run(argv, cwd=REPO, capture_output=True, text=True,
                       timeout=120)
    if r.returncode != 0:
        raise RuntimeError("git ls-files failed: %s"
                           % (r.stderr or "").strip()[-200:])
    tree = {}
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 2:
            tree[path] = parts[1]
    return tree


def public_tree(gh):
    """path -> blob sha, as the public repo currently holds it.

    A TRUNCATED response is refused rather than compared. Comparing against
    a truncated tree would report thousands of files as missing -- a false
    alarm indistinguishable from the real one this check exists to raise.
    """
    r = subprocess.run(
        [gh, "api", "repos/%s/git/trees/main?recursive=1" % PUBLIC_REPO],
        capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "gh failed").strip().splitlines()[-1])
    doc = json.loads(r.stdout)
    if doc.get("truncated"):
        raise RuntimeError(
            "the public tree listing came back TRUNCATED, so a file-level "
            "comparison would be meaningless here")
    return {e["path"]: e["sha"] for e in doc.get("tree", [])
            if e.get("type") == "blob"}


def compare_trees(dev, public):
    """What the public repo is missing, holding differently, or holding extra."""
    dev = {k: v for k, v in dev.items() if k not in GENERATED_AT_EXPORT}
    public = {k: v for k, v in public.items()
              if k not in GENERATED_AT_EXPORT}
    missing = sorted(p for p in dev if p not in public)
    differing = sorted(p for p in dev
                       if p in public and dev[p] != public[p])
    extra = sorted(p for p in public if p not in dev)
    return {"missing": missing, "differing": differing, "extra": extra}


def last_attempt(path=STATE_FILE, repo=None):
    """The publish's own record of its last run, or None.

    A record that names a DIFFERENT repository is discarded rather than
    read. Four copies of publish-public.sh live on a dev machine -- two dev
    trees and two public mirrors, which are clones of the exports -- and the
    first version of this used one shared filename for all of them. The
    symptom was a record whose `dev_head` was not a commit in this
    repository at all, which took a while to recognise precisely because
    nothing in the record said who wrote it. Now it does.
    """
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (ValueError, OSError):
        return None
    if not isinstance(doc, dict):
        return None
    named = doc.get("repo")
    mine = os.path.basename(repo or REPO)
    if named and named != mine:
        return None
    return doc


def head_sha():
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                       capture_output=True, text=True, timeout=30)
    return r.stdout.strip() if r.returncode == 0 else None


def decide_content(drift, attempt, dev_head):
    """(verdict, why). Pure, so the interesting cases are testable offline.

    in-flight   the trees differ and dev has committed since the last
                publish attempt -- expected, this is the hour between a
                commit and the next hourly run
    broken      the pipe reported a failure, or it reported success and the
                trees still differ
    unexplained the trees differ and there is no attempt record to say why
    ok          no drift
    """
    n = len(drift["missing"]) + len(drift["differing"]) + len(drift["extra"])
    if attempt and attempt.get("outcome") == "failed":
        return "broken", ("the last publish attempt FAILED (exit %s) at: %s"
                          % (attempt.get("exit_status"),
                             attempt.get("stage") or "unrecorded"))
    if n == 0:
        return "ok", "public holds exactly what the export would carry"
    if attempt and attempt.get("outcome") in ("held", "skipped-lock"):
        return "in-flight", ("%d file(s) differ; the last attempt was %s, "
                             "which is not a failure"
                             % (n, attempt.get("outcome")))
    if attempt and dev_head and attempt.get("dev_head") != dev_head:
        return "in-flight", ("%d file(s) differ and dev has committed since "
                             "the last publish attempt -- the next run "
                             "carries them" % n)
    if attempt:
        return "broken", ("%d file(s) differ and the last publish attempt "
                          "reported success over this very commit" % n)
    return "unexplained", ("%d file(s) differ and no publish attempt record "
                           "exists to say why" % n)


# ---------------------------------------------------------------- decision
# Pure, so it can be tested without a network. The scanner that cannot be
# tested offline is the one that rots.
OK, STALE, AHEAD = "ok", "stale", "ahead"


def decide(dev_leaves, public_leaves, tolerance=DEFAULT_TOLERANCE):
    """(verdict, drift). drift is dev - public; positive means public lags."""
    if dev_leaves is None or public_leaves is None:
        raise ValueError("both leaf counts are required")
    drift = dev_leaves - public_leaves
    if drift < 0:
        return AHEAD, drift
    if drift > tolerance:
        return STALE, drift
    return OK, drift


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tolerance", type=int, default=DEFAULT_TOLERANCE,
                    help="leaves of drift tolerated before this fails "
                         "(default one 100-leaf band)")
    args = ap.parse_args(argv)

    gh = gh_bin()
    if gh is None:
        print("COULD NOT VERIFY publish-health: gh is not on PATH. This is "
              "not a pass -- nothing about the published state was checked.",
              file=sys.stderr)
        return 2

    local = local_metrics()
    try:
        pub = public_metrics(gh)
        tag = newest_public_tag(gh)
        drift = compare_trees(dev_tree(), public_tree(gh))
    except Exception as exc:                       # network, auth, 404
        print("COULD NOT VERIFY publish-health: %s. This is not a pass -- "
              "nothing about the published state was checked." % exc,
              file=sys.stderr)
        return 2

    attempt = last_attempt()
    content_verdict, content_why = decide_content(drift, attempt, head_sha())

    d_leaves = local.get("leaves")
    p_leaves = pub.get("leaves")
    d_cases = local.get("router_cases", local.get("corpus_tasks"))
    p_cases = pub.get("router_cases", pub.get("corpus_tasks"))
    _, leaf_drift = decide(d_leaves, p_leaves, args.tolerance)

    n_drift = sum(len(drift[k]) for k in ("missing", "differing", "extra"))
    print("================ publish health ================")
    print("  content  %d file(s) differ  (missing %d, changed %d, extra %d)"
          % (n_drift, len(drift["missing"]), len(drift["differing"]),
             len(drift["extra"])))
    print("  pipe     last attempt: %s"
          % (("%s at %s" % (attempt.get("outcome"),
                            attempt.get("attempted_at")))
             if attempt else "no record written yet"))
    print("  corpus   dev %-6s  public %-6s  drift %+d"
          % (d_leaves, p_leaves, leaf_drift))
    print("  evidence dev %-6s  public %-6s" % (d_cases, p_cases))
    print("  release  newest public tag: %s" % (tag or "(none)"))
    print("  tolerance: %d leaves (one release band)" % args.tolerance)
    print("================================================")

    # Content first. It is the decisive comparison and the one whose absence
    # let three failed publishes read as healthy.
    if content_verdict in ("broken", "unexplained"):
        print("FAIL publish-health: %s." % content_why, file=sys.stderr)
        for label, key in (("missing from public", "missing"),
                           ("different in public", "differing"),
                           ("present only in public", "extra")):
            paths = drift[key]
            if paths:
                print("  %s (%d):" % (label, len(paths)), file=sys.stderr)
                for path in paths[:10]:
                    print("    %s" % path, file=sys.stderr)
                if len(paths) > 10:
                    print("    ... and %d more" % (len(paths) - 10),
                          file=sys.stderr)
        print("  Check the hourly log for the abort. The gate battery grades "
              "the TREE and never the shipping path.", file=sys.stderr)
        return 1
    if content_verdict == "in-flight":
        print("PENDING publish-health: %s." % content_why)

    verdict, leaf_drift = decide(d_leaves, p_leaves, args.tolerance)
    if verdict == AHEAD:
        print("FAIL publish-health: the PUBLIC repo is ahead of dev by %d "
              "leaves. Someone published out of band, or dev has been reset."
              % -leaf_drift, file=sys.stderr)
        return 1
    if verdict == STALE:
        print("FAIL publish-health: public is %d leaves behind dev, past the "
              "%d-leaf tolerance. The publish pipe is broken -- check the "
              "hourly log for the abort, not the gate battery, which grades "
              "the tree and not the shipping path."
              % (leaf_drift, args.tolerance), file=sys.stderr)
        return 1

    if content_verdict == "in-flight":
        print("PASS publish-health: nothing is broken; %d file(s) are waiting "
              "for the next run." % n_drift)
        return 0
    print("PASS publish-health: public holds exactly what the export would "
          "carry (%d file(s) compared by blob sha), and the last publish "
          "attempt was %s."
          % (len(dev_tree()), attempt.get("outcome") if attempt else "unrecorded"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
