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

  corpus   docs/metrics.json leaves     -- the free product
  evidence router cases gate 5 executes -- the proof for the corpus claim
  release  the newest published tag     -- what a consumer can actually get

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
    except Exception as exc:                       # network, auth, 404
        print("COULD NOT VERIFY publish-health: %s. This is not a pass -- "
              "nothing about the published state was checked." % exc,
              file=sys.stderr)
        return 2

    d_leaves = local.get("leaves")
    p_leaves = pub.get("leaves")
    d_cases = local.get("router_cases", local.get("corpus_tasks"))
    p_cases = pub.get("router_cases", pub.get("corpus_tasks"))
    _, drift = decide(d_leaves, p_leaves, args.tolerance)

    print("================ publish health ================")
    print("  corpus   dev %-6s  public %-6s  drift %+d"
          % (d_leaves, p_leaves, drift))
    print("  evidence dev %-6s  public %-6s" % (d_cases, p_cases))
    print("  release  newest public tag: %s" % (tag or "(none)"))
    print("  tolerance: %d leaves (one release band)" % args.tolerance)
    print("================================================")

    verdict, drift = decide(d_leaves, p_leaves, args.tolerance)
    if verdict == AHEAD:
        print("FAIL publish-health: the PUBLIC repo is ahead of dev by %d "
              "leaves. Someone published out of band, or dev has been reset."
              % -drift, file=sys.stderr)
        return 1
    if verdict == STALE:
        print("FAIL publish-health: public is %d leaves behind dev, past the "
              "%d-leaf tolerance. The publish pipe is broken -- check the "
              "hourly log for the abort, not the gate battery, which grades "
              "the tree and not the shipping path."
              % (drift, args.tolerance), file=sys.stderr)
        return 1

    print("PASS publish-health: public is current within tolerance "
          "(%d leaves behind, %d allowed)." % (drift, args.tolerance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
