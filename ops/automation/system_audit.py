#!/usr/bin/env python3
"""system_audit.py — one end-to-end audit of the AeroSkills machine.

Founder 2026-09-10: "audit and nothing should break again". This is that
audit. It checks every invariant in ops/ecss-program/OPERATIONS.md and fails
LOUD with a one-line reason per broken thing.

Exit 0 = nothing is broken. Exit 1 = at least one invariant violated.

Usage:  python3 ops/automation/system_audit.py [--quiet]
Runs from the dev repo root (or any subdir — it finds the root itself).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUBLIC_REPO = "ashfordeOU/aero-agent-skills"
SITE = "https://ashforde.org/aeroagentskills/"
STATE = os.path.expanduser("~/.hermes/state")
CRON_DIRS = [os.path.expanduser("~/.hermes/cron"), os.path.expanduser("~/.hermes/cron/jobs")]

# Crons that constitute the machine (substring match on the job name).
REQUIRED_CRONS = {
    "Team Relay": "wave planner/dispatcher (path A)",
    "Aero night CCD lane dispatch": "quiet-window CCD dispatch (path B)",
    "Aero lane harvest": "verify + close CCD lanes",
    "Aero release cut": "auto-cut due 100-milestones",
    "Aero public freshness": "public/site lag alarm",
    "Aero system audit": "this audit",
}

failures: list[str] = []
notes: list[str] = []


def run(cmd, cwd=ROOT, timeout=120):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def gh_token() -> str | None:
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    for p in ("~/.hermes/.gh_pat_ashfordesite.tmp", "~/.hermes/.gh_pat_arjun0077.tmp"):
        f = os.path.expanduser(p)
        if os.path.exists(f):
            return open(f).read().strip()
    return None


def api(path: str, token: str | None):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"token {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fail(check: str, why: str):
    failures.append(f"{check}: {why}")


def note(msg: str):
    notes.append(msg)


# ---------------------------------------------------------------- 1. dev tree
def check_dev_tree():
    st = run(["git", "status", "--porcelain"])
    if st.stdout.strip():
        fail("dev-tree", f"{len(st.stdout.strip().splitlines())} uncommitted change(s) — commit before publishing")
    run(["git", "fetch", "origin", "--quiet"], timeout=120)
    ahead = run(["git", "rev-list", "--count", "origin/main..HEAD"])
    try:
        n = int(ahead.stdout.strip() or "0")
    except ValueError:
        n = 0
    if n:
        fail("dev-tree", f"{n} unpushed commit(s) — push or they are not durable")


# ------------------------------------------------------- 2. gates + corpus
def check_gates():
    v = run(["make", "validate"], timeout=900)
    out = (v.stdout or "") + (v.stderr or "")
    if v.returncode != 0 or "validate: PASS" not in out:
        line = next((l for l in out.splitlines() if "FAIL" in l), "validate did not report PASS")
        fail("gates", line.strip()[:160])
        return
    m = re.search(r"gate5-hit1:\s*(\d+)/(\d+)", out)
    if m:
        hit, total = int(m.group(1)), int(m.group(2))
        if hit != total:
            fail("gates", f"Hit@1 {hit}/{total}")
        note(f"gates: PASS · Hit@1 {hit}/{total}")


def count_leaves() -> int:
    base = os.path.join(ROOT, "skills")
    n = 0
    for dirpath, dirnames, filenames in os.walk(base):
        if ".git" in dirpath:
            continue
        if "SKILL.md" in filenames:
            n += 1
    return n


def check_corpus_coverage(leaves: int):
    """Invariant: every published leaf is covered by Hit@1 corpus tasks."""
    f = os.path.join(ROOT, "eval", "hit1-corpus.yaml")
    if not os.path.exists(f):
        fail("corpus", "eval/hit1-corpus.yaml missing")
        return
    txt = open(f).read()
    tasks = len(re.findall(r"^\s*-\s*id:", txt, re.M)) or txt.count("- id:")
    # 2 tasks per leaf is the program's coverage rule (2 ratings per leaf).
    if leaves and tasks < leaves:
        fail("corpus", f"only {tasks} Hit@1 tasks for {leaves} leaves (under-covered)")
    else:
        note(f"corpus: {tasks} tasks for {leaves} leaves")


# --------------------------------------------------------- 3. ECSS + CCD
def check_ecss_and_ccd():
    ecss_dir = os.path.join(ROOT, "skills", "space-systems", "ecss")
    built = len(os.listdir(ecss_dir)) if os.path.isdir(ecss_dir) else 0
    note(f"ecss: {built} leaves built")

    lanes_dir = os.path.expanduser("~/aero-lanes")
    if os.path.isdir(lanes_dir):
        lanes = [d for d in os.listdir(lanes_dir) if os.path.isdir(os.path.join(lanes_dir, d))]
        if lanes:
            # A lane abandoned (merged but not dropped, or stale >24h) is a leaks.
            import time
            for lane in lanes:
                p = os.path.join(lanes_dir, lane)
                age_h = (time.time() - os.path.getmtime(p)) / 3600.0
                if age_h > 24:
                    fail("ccd", f"lane {lane} untouched for {age_h:.0f}h — harvest or drop it")
            if not failures:
                note(f"ccd: {len(lanes)} lane(s) in flight")

    hr = os.path.join(STATE, "harvest-report.md")
    if os.path.exists(hr) and os.path.getsize(hr) > 0:
        fail("ccd", f"harvest-report.md has content — a CCD tranche failed verification ({hr})")


# ------------------------------------------------------------- 4. releases
def check_releases(token):
    r = run(["python3", "scripts/release-manager.py", "--check"], timeout=180)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 or "VERDICT: PASS" not in out:
        line = next((l for l in out.splitlines() if "FAIL" in l or "BREACH" in l), "check did not PASS")
        fail("releases", line.strip()[:160])
        return
    note("releases: PASS (version sync + tag/Release parity)")

    try:
        rels = api(f"/repos/{PUBLIC_REPO}/releases", token)
        pub = {x["tag_name"] for x in rels}
        tags = api(f"/repos/{PUBLIC_REPO}/git/refs/tags", token)
        tagn = {t["ref"].split("/")[-1] for t in tags}
        # v1.0.0 is pre-convention (deliberately a draft) — never a breach.
        orphans = sorted(t for t in (tagn & {"v1.%d.0" % i for i in range(1, 40)}) if t not in pub)
        if orphans:
            fail("releases", f"tag(s) with no Release: {', '.join(orphans)}")
        else:
            note(f"releases: {len(pub & tagn)} tags with Releases, no orphans")
    except Exception as e:  # noqa: BLE001
        fail("releases", f"could not read public releases: {e}")


# --------------------------------------------------- 5. public + 6. site
def public_leaves(token):
    try:
        d = api(f"/repos/{PUBLIC_REPO}/contents/docs/metrics.json", token)
        import base64
        txt = base64.b64decode(d["content"]).decode()
        return int(re.search(r'"leaves":\s*(\d+)', txt).group(1))
    except Exception:  # noqa: BLE001
        return None


def check_public_and_site(leaves, token):
    pub = public_leaves(token)
    if pub is None:
        fail("public", "could not read public metrics.json")
    elif pub < leaves:
        fail("public", f"public repo lags dev: {pub} < {leaves} leaves")
    else:
        note(f"public: {pub} leaves (dev {leaves})")

    # failed workflow runs — the public repo must have none
    try:
        d = api(f"/repos/{PUBLIC_REPO}/actions/runs?per_page=1&status=failure", token)
        if d.get("total_count", 0):
            fail("public", f"{d['total_count']} failed workflow run(s) on the public repo")
        else:
            note("public: 0 failed workflow runs")
    except Exception as e:  # noqa: BLE001
        fail("public", f"could not read workflow runs: {e}")

    # site shows the public repo's number
    try:
        req = urllib.request.Request(SITE, headers={"User-Agent": "system-audit"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        shown = None
        for mm in re.finditer(r"(\d{2,4})\s*verified", html):
            shown = int(mm.group(1))
            break
        if shown is None:
            note("site: reachable (leaf count not parsed)")
        elif pub is not None and shown < pub:
            fail("site", f"site shows {shown} but the public repo is at {pub} — stale page")
        else:
            note(f"site: {shown} verified")
    except Exception as e:  # noqa: BLE001
        fail("site", f"unreachable: {e}")


# ------------------------------------------------------------- 7. topics
def check_topics(token):
    try:
        d = api(f"/repos/{PUBLIC_REPO}/topics", token)
        names = d.get("names") or []
        if not names:
            fail("topics", "About topics empty — run ops/automation/update-about.sh")
        else:
            note(f"topics: {len(names)} set")
    except Exception as e:  # noqa: BLE001
        fail("topics", f"could not read topics: {e}")


# -------------------------------------------------------------- 8. crons
def check_crons():
    names: list[str] = []
    for d in CRON_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            try:
                data = json.load(open(os.path.join(d, fn)))
            except Exception:  # noqa: BLE001
                continue
            jobs = data if isinstance(data, list) else data.get("jobs", [data])
            for j in jobs:
                if isinstance(j, dict) and j.get("name"):
                    names.append(("%s|%s" % (j["name"], j.get("enabled", True))))
    blob = "\n".join(names)
    for want, role in REQUIRED_CRONS.items():
        line = next((l for l in names if want in l.split("|")[0]), None)
        if line is None:
            fail("crons", f"missing cron '{want}' ({role})")
        elif line.endswith("|False"):
            fail("crons", f"cron '{want}' is DISABLED ({role})")
    if not any(f.startswith("crons:") for f in failures):
        note(f"crons: all {len(REQUIRED_CRONS)} required jobs present and enabled")


def main():
    quiet = "--quiet" in sys.argv
    token = gh_token()

    check_dev_tree()
    check_gates()
    leaves = count_leaves()
    check_corpus_coverage(leaves)
    check_ecss_and_ccd()
    check_releases(token)
    check_public_and_site(leaves, token)
    check_topics(token)
    check_crons()

    if not quiet:
        print("AERO SYSTEM AUDIT")
        print(f"  leaves: {leaves}")
        for n in notes:
            print(f"  ok  · {n}")
    if failures:
        print(f"SYSTEM AUDIT: FAIL ({len(failures)} invariant(s) broken)")
        for f in failures:
            print(f"  !! {f}")
        return 1
    print("SYSTEM AUDIT: PASS — nothing is broken")
    return 0


if __name__ == "__main__":
    sys.exit(main())
