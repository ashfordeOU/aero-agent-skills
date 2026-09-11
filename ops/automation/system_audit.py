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

import pathlib

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

# Publish single-writer lock (VEDA-0037). Every token the wiring needs, mapped
# to why its absence is a failure — the audit must name the broken piece.
PUBLISH_LOCK_HOST_STATE = os.path.join(".hermes", "state")
PUBLISH_LOCK_REQUIRED = {
    "AERO_PUBLISH_LOCK_FILE": "the lock path is not overridable (AERO_PUBLISH_GO_FILE convention)",
    "AERO_PUBLISH_LOCK_TIMEOUT": "the lock wait is not a bounded named constant",
    "exec 9>": "no flock-on-fd lock — the shared mirror has no mutual exclusion",
    "command -v flock": "no explicit handling when flock(1) is unavailable",
    "LOCK_BUSY_EXIT": "the lock-busy exit code is not named",
}
# The ACTUAL mirror mutations, as commands — never a prose marker: the file's
# header comments say "reset --hard" too, so a bare substring search reports
# the lock as taken AFTER the mirror (a false FAIL) and hides real drift.
PUBLISH_MIRROR_MUTATIONS = (
    'git -C "$MIRROR" reset --hard',
    'find "$MIRROR" -mindepth 1',
    'cp -a "$EXPORT/." "$MIRROR/"',
)

# Crons that constitute the machine (substring match on the job name).
REQUIRED_CRONS = {
    "Team Relay": "wave planner/dispatcher (path A)",
    "Aero night CCD lane dispatch": "quiet-window CCD dispatch (path B)",
    "Aero lane harvest": "verify + close CCD lanes",
    "Aero release cut": "auto-cut due 100-milestones",
    "Aero public freshness": "public/site lag alarm",
    "Aero system audit": "this audit",
}

# Explicit registry of intentionally-paused required crons. A DISABLED cron
# is only ever silenced from FAIL if it is named here — the registry's
# absence, emptiness or corruption must never silence a real break.
PAUSE_REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "paused-crons.json")

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


# ------------------------------------------------- 1b. publish single-writer
def check_publish_single_writer():
    """The public publish must own a single-writer lock before the mirror.

    VEDA-0037: publish-public.sh mutates ONE shared mirror clone
    (reset --hard -> find -delete -> cp -a -> commit -> push) and nothing
    serialised its callers — the launchd StartInterval only stops the timer
    overlapping ITSELF. Two runs fought over that worktree on 2026-09-10, the
    setup for the silent FALSE no-op of VEDA-0033 (public repo left behind the
    dev tree while every gate stayed green). This keeps the WIRING from
    rotting: a lock taken AFTER the mirror phase protects nothing, and a lock
    path inside the repo would be committed and exported. Deterministic and
    offline — source analysis of publish-public.sh only, no git, no network.
    """
    publish = os.path.join(ROOT, "ops", "automation", "publish-public.sh")
    if not os.path.isfile(publish):
        fail("publish-lock", "ops/automation/publish-public.sh missing — cannot verify the mirror lock")
        return
    with open(publish, encoding="utf-8") as fh:
        body = fh.read()

    # A missing token is a FAIL, never a clean bill of health: a script whose
    # lock cannot be read must not audit as PASS (silent-skip class).
    for token, why in PUBLISH_LOCK_REQUIRED.items():
        if token not in body:
            fail("publish-lock", f"{why} ({token!r} absent from publish-public.sh)")
            return

    missing = [m for m in PUBLISH_MIRROR_MUTATIONS if m not in body]
    if missing:
        fail("publish-lock", f"mirror mutations not found ({', '.join(missing)}) — lock ordering cannot be verified")
        return
    locked_at = body.index("exec 9>")
    first_mutation = min(body.index(m) for m in PUBLISH_MIRROR_MUTATIONS)
    if locked_at > first_mutation:
        fail("publish-lock", "the single-writer lock is taken AFTER the first mirror mutation — it protects nothing")
        return
    if 'exit "$LOCK_BUSY_EXIT"' not in body:
        fail("publish-lock", "the lock-busy path does not exit non-zero — a silent skip of the publish is possible")
        return

    # The lock must live OUTSIDE the repo (host-local state): inside it the
    # lock file would be committed, exported and shipped to the public repo.
    m = re.search(r"AERO_PUBLISH_LOCK_FILE:-(\S+?)\}", body)
    if not m:
        fail("publish-lock", "cannot read the default lock path from publish-public.sh")
        return
    lock_path = m.group(1).replace("$HOME", os.path.expanduser("~"))
    if lock_path.startswith(ROOT):
        fail("publish-lock", f"default lock path is inside the repo: {lock_path}")
        return
    if PUBLISH_LOCK_HOST_STATE not in lock_path:
        fail("publish-lock", f"default lock path is not host-local state ({PUBLISH_LOCK_HOST_STATE}): {lock_path}")
        return
    note(f"publish-lock: single-writer flock before the mirror, host-local ({lock_path})")


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


def count_leaves():
    """Return (pack_leaves, family_indexes).

    The AUTHORITATIVE leaf count is pack leaves at
    skills/<family>/<pack>/<leaf>/SKILL.md - what metrics.json, the built
    manifest, the router and the site all count. Each family ALSO carries an
    index SKILL.md at skills/<family>/SKILL.md; those are structure, never
    leaves, and must not be double-counted (they caused a false audit alarm
    on 2026-09-10: raw 772 vs authoritative 760).
    """
    base = pathlib.Path(ROOT) / "skills"
    if not base.is_dir():
        return 0, 0
    families = [d for d in sorted(base.iterdir()) if d.is_dir()]
    pack_leaves = 0
    for fam in families:
        for pack in sorted(p for p in fam.iterdir() if p.is_dir()):
            pack_leaves += len(list(fam.glob(f"{pack.name}/*/SKILL.md")))
    indexes = sum(1 for fam in families if (fam / "SKILL.md").is_file())
    return pack_leaves, indexes


def check_structure(leaves: int, indexes: int):
    """Structure invariants.

    1. docs/metrics.json must agree with the leaves actually on disk. Nothing
       checked this before 2026-09-10, so published numbers could drift stale
       while every gate stayed green (the drift class this audit exists for).
    2. Each family carries exactly one index SKILL.md.
    """
    mf = os.path.join(ROOT, "docs", "metrics.json")
    if not os.path.exists(mf):
        fail("structure", "docs/metrics.json missing")
    else:
        try:
            declared = int(json.load(open(mf)).get("leaves", -1))
        except Exception:  # noqa: BLE001
            declared = -1
        if declared != leaves:
            fail("structure",
                 f"docs/metrics.json says {declared} leaves but {leaves} exist "
                 f"— stale metrics (run `make visuals`)")
        else:
            note(f"structure: metrics.json matches disk ({leaves} leaves)")

    base = pathlib.Path(ROOT) / "skills"
    fam_count = len([d for d in base.iterdir() if d.is_dir()]) if base.is_dir() else 0
    if indexes != fam_count:
        fail("structure",
             f"{fam_count} families but {indexes} family index SKILL.md "
             f"(each family needs exactly one)")
    else:
        note(f"structure: {indexes} family indexes present")


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
        m = re.search(r'"leaves":\s*(\d+)', txt)
        return int(m.group(1)) if m else None
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
def read_pause_registry() -> dict:
    """Read PAUSE_REGISTRY -> {cron name: entry dict}.

    Never raises: a missing file, empty file, bad JSON or wrong shape all
    resolve to {} (no pauses on record) — the registry can only silence a
    failure by explicitly naming the cron, never by being absent or broken.
    """
    try:
        with open(PAUSE_REGISTRY, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(data, dict):
        return {}
    pauses = data.get("pauses")
    if not isinstance(pauses, list):
        return {}
    out = {}
    for entry in pauses:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            out[entry["name"]] = entry
    return out


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

    pauses = read_pause_registry()
    present = 0
    paused = 0
    enabled = 0
    for want, role in REQUIRED_CRONS.items():
        line = next((l for l in names if want in l.split("|")[0]), None)
        if line is None:
            fail("crons", f"missing cron '{want}' ({role})")
            continue
        present += 1
        is_disabled = line.endswith("|False")
        pause_entry = pauses.get(want)
        if is_disabled and pause_entry is None:
            fail("crons", f"cron '{want}' is DISABLED ({role})")
        elif is_disabled and pause_entry is not None:
            paused += 1
            note(f"crons: cron '{want}' is DISABLED but intentionally paused "
                 f"({role}) — {pause_entry.get('reason', 'no reason on record')} "
                 f"(since {pause_entry.get('since', 'unknown')})")
        elif not is_disabled and pause_entry is not None:
            enabled += 1
            note(f"crons: cron '{want}' is ENABLED but still in the pause "
                 f"registry — pause lifted, remove its entry from "
                 f"{PAUSE_REGISTRY}")
        else:
            enabled += 1
    if not any(f.startswith("crons:") for f in failures):
        note(f"crons: {present}/{len(REQUIRED_CRONS)} required jobs present "
             f"({paused} intentionally paused, {enabled} enabled)")


def main():
    quiet = "--quiet" in sys.argv
    token = gh_token()

    check_dev_tree()
    check_publish_single_writer()
    check_gates()
    leaves, indexes = count_leaves()
    check_structure(leaves, indexes)
    check_corpus_coverage(leaves)
    check_ecss_and_ccd()
    check_releases(token)
    check_public_and_site(leaves, token)
    check_topics(token)
    check_crons()

    if not quiet:
        print("AERO SYSTEM AUDIT")
        print(f"  leaves: {leaves} pack (+{indexes} family indexes)")
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
