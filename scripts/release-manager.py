#!/usr/bin/env python3
"""Aero Agent Skills release manager (founder convention 2026-09-03).

RELEASE CONVENTION (founder): every 100 new skills = one MINOR version
bump. v1.0.0 covered skills 1-100; v1.1.0 = 101-200; v1.2.0 = 201-300;
v1.3.0 = 301-400 ... Current count 353 → next release v1.3.0 at 400.

This tool:
  --status        show current leaf count + which release band we're in
  --next          show what the next release tag will be + skills remaining
  --sync          sync package.json + JetBrains + Claude plugin versions to
                  the current band version (call before a release)
  --changelog     print the release notes body from the git log since the
                  last release tag (new leaves + families)

Usage:
  python3 scripts/release-manager.py --status
  python3 scripts/release-manager.py --next
  python3 scripts/release-manager.py --sync --dry-run
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_REPO = "ashfordeOU/aero-agent-skills"   # where releases ship (Ruling 3 gates it)

# Resolve the GitHub CLI once (VEDA-0034). A cron no_agent job spawns with a
# managed PATH that omits /opt/homebrew/bin, so a bare "gh" raised
# FileNotFoundError inside cut_release() and spammed the group every 30m.
# Resolving here lets the cut path print a named failure and exit 1 instead
# of raising, and every call site (cut + parity) shares the resolved path.
GH = shutil.which("gh")

# Publish token (2026-09-10): releases live on the ashfordeOU org repo, which
# the dev account's gh token cannot write (HTTP 403). The org token file is
# the same credential publish-public.sh uses. Resolve it once at import so
# every gh subprocess here is authenticated as the publish account; an
# explicit GH_TOKEN in the environment always wins.
_ORG_TOKEN_FILE = os.path.expanduser("~/.hermes/.gh_pat_ashfordesite.tmp")


def _resolve_publish_token():
    if os.environ.get("GH_TOKEN"):
        return
    try:
        tok = open(_ORG_TOKEN_FILE, encoding="utf-8").read().strip()
    except OSError:
        return
    if tok:
        os.environ["GH_TOKEN"] = tok


_resolve_publish_token()
METRICS = os.path.join(REPO, "docs/metrics.json")
PKG = os.path.join(REPO, "packages/aero-agent-skills/package.json")
PLUGIN_GRADLE = os.path.join(REPO, "packages/jetbrains-plugin/build.gradle.kts")
CLAUDE_PLUGIN = os.path.join(REPO, ".claude-plugin/plugin.json")


def leaf_count():
    m = json.load(open(METRICS))
    return m["leaves"], m


def band_version(leaves):
    """100-skill minor convention: skills 1-100 → 1.0.0, 101-200 → 1.1.0 ...
    (leaves-1) // 100 gives the minor index."""
    minor = (leaves - 1) // 100
    return f"1.{minor}.0"


def current_version():
    """Current band version + the actual published versions."""
    leaves, _ = leaf_count()
    band = band_version(leaves)
    pkg = json.load(open(PKG))["version"]
    return leaves, band, pkg


def next_release_info():
    leaves, _ = leaf_count()
    # next boundary at the next multiple of 100
    next_boundary = ((leaves // 100) + 1) * 100
    next_band = band_version(next_boundary)
    remaining = next_boundary - leaves
    return leaves, next_boundary, next_band, remaining


def git_log_since_last_tag():
    """Release notes: commits since the last v* tag (leaf commits named per
    the descriptive-commit fix)."""
    try:
        tags = subprocess.run(
            ["git", "-C", REPO, "tag", "--list", "v*", "--sort=-v:refname"],
            capture_output=True, text=True, timeout=15).stdout.split()
    except Exception:
        tags = []
    if not tags:
        return ""
    last = tags[0]
    out = subprocess.run(
        ["git", "-C", REPO, "log", "--oneline", f"{last}..HEAD"],
        capture_output=True, text=True, timeout=20).stdout
    return out.strip()


def changelog_body():
    leaves, m = leaf_count()
    log = git_log_since_last_tag()
    lines = []
    lines.append(f"## Aero Agent Skills — {band_version(leaves)}")
    lines.append("")
    lines.append(f"**{leaves} verified leaves · {m['live_packs']} packs · "
                 f"{m['families']} families · {m['corpus_tasks']} router tasks**")
    lines.append("")
    if log:
        lines.append("### Changes since last release")
        lines.append("")
        for ln in log.split("\n")[:60]:
            lines.append(f"- {ln[:90]}")
        lines.append("")
    lines.append("### Packages")
    lines.append("- npm CLI + MCP server: `aero-agent-skills`")
    lines.append("- JetBrains Marketplace plugin: Aero Agent Skills (34041)")
    lines.append("- Claude Code plugin + agentskills.io format")
    lines.append("- GitHub: public repo + docs + CI (attest 5/5)")
    return "\n".join(lines)


def sync_versions(dry=False):
    leaves, band, pkg = current_version()
    changes = []
    if pkg != band:
        changes.append(f"package.json: {pkg} -> {band}")
        if not dry:
            d = json.load(open(PKG))
            d["version"] = band
            json.dump(d, open(PKG, "w"), indent=2)
            open(PKG, "a").write("\n")
    # JetBrains gradle: version = "X.Y.Z"
    g = open(PLUGIN_GRADLE).read()
    m = re.search(r'version\s*=\s*"([^"]+)"', g)
    if m and m.group(1) != band:
        changes.append(f"jetbrains build.gradle.kts: {m.group(1)} -> {band}")
        if not dry:
            open(PLUGIN_GRADLE, "w").write(g.replace(m.group(0), f'version = "{band}"', 1))
    # Claude plugin
    if os.path.exists(CLAUDE_PLUGIN):
        c = json.load(open(CLAUDE_PLUGIN))
        if c.get("version") != band:
            changes.append(f"claude plugin.json: {c.get('version')} -> {band}")
            if not dry:
                c["version"] = band
                json.dump(c, open(CLAUDE_PLUGIN, "w"), indent=2)
                open(CLAUDE_PLUGIN, "a").write("\n")
    return changes


def release_check() -> int:
    """Gate: enforce the release convention (founder 2026-09-03).

    The convention (every 100 new skills = one minor bump) lived only in
    prose + this manual tool, so the push battery never saw it and the fast
    lanes drifted: three version files 4 minors stale and a public tag
    (v1.6.0) with no Release object.

    BLOCKING (locally fixable, no publish authority needed):
      1. version files must be at the current band  -> run --sync

    REPORT-ONLY (needs a release decision / founder GO under Ruling 3, so
    it must never silently block a push):
      2. public tag <-> Release parity, via gh when available
      3. the last completed band's release status
    """
    leaves, _ = leaf_count()
    _, band, pkg = current_version()
    problems, notes = [], []

    # 1. version files == current band  (blocking)
    for c in sync_versions(dry=True):
        problems.append(f"version file behind band: {c}  -> run --sync")

    completed = (leaves // 100) * 100
    due_tag = f"v{band_version(completed)}" if completed >= 100 else "v1.0.0"
    repo_tags = subprocess.run(["git", "-C", REPO, "tag", "-l"],
                               capture_output=True, text=True).stdout.split()
    if due_tag in repo_tags:
        notes.append(f"last completed band {due_tag} is tagged")
    else:
        # dev-tree tagging stopped at v1.4.0 by convention (releases are cut
        # on the public repo), so this is a public-side fact, not a dev error.
        notes.append(f"RELEASE STATUS: {due_tag} (last completed band, "
                     f"{completed} skills) is not tagged in the dev tree — "
                     f"releases are cut on the PUBLIC repo (standing GO "
                     f"2026-09-10: auto-cut cron + release-on-milestone; "
                     f"touch ~/.hermes/state/aero-release-HOLD to pause)")

    # 2. public parity (best effort; gh may be unavailable)
    try:
        r = subprocess.run([GH or "gh", "release", "list", "-R", PUBLIC_REPO,
                            "-L", "30", "--json", "tagName"],
                           capture_output=True, text=True, timeout=25)
        if r.returncode == 0:
            rel = {x["tagName"] for x in json.loads(r.stdout or "[]")}
            t = subprocess.run([GH or "gh", "api", f"repos/{PUBLIC_REPO}/git/refs/tags",
                               "--jq", ".[].ref"],
                               capture_output=True, text=True, timeout=25)
            ptags = {x.replace("refs/tags/", "") for x in t.stdout.split()
                     if x.startswith("refs/tags/v")}
            # v1.0.0 is the PRE-CONVENTION launch tag (docs: "the public repo
            # launched at v1.0.0, 330 leaves, pre-convention tag"). It is not a
            # 100-skill milestone, so it must NOT be flagged as a missing
            # release. Only milestone bands (v1.X.0, X>=1) require one.
            PRE_CONVENTION = {"v1.0.0"}
            def _is_milestone(tag):
                m = re.fullmatch(r"v1\.(\d+)\.0", tag)
                return bool(m) and int(m.group(1)) >= 1
            orphans = sorted(t for t in (ptags - rel)
                             if t not in PRE_CONVENTION and _is_milestone(t))
            if orphans:
                notes.append(f"PUBLIC BREACH: tag(s) with no Release: "
                             f"{', '.join(orphans)} — self-heals on the next "
                             f"push (release-on-milestone) or via "
                             f"release-manager.py --auto-cut")
            else:
                notes.append("public tag/Release parity OK")
    except Exception:
        notes.append("public parity: unverified (gh unavailable)")

    print(f"release-law: leaves={leaves} band={band} version-files={pkg} "
          f"last-completed-band={completed} due-tag={due_tag}")
    for n in notes:
        print(f"  · {n}")
    if problems:
        for p in problems:
            print(f"  - {p}")
        print("VERDICT: FAIL — release convention not met (founder 2026-09-03)")
        return 1
    print("VERDICT: PASS — versions at band; release status reported above")
    return 0


GO_FILE = os.path.expanduser("~/.hermes/state/aero-public-publish-GO")
# Auto-release (founder 2026-09-10: "release cuts at every 100 handled
# automatically"). --auto-cut skips the per-release GO gate but honours a
# HOLD kill-switch, so the founder keeps a stop button without gating each
# milestone. The push-triggered workflow is the primary path; this is the
# belt-and-braces path (and the self-heal for a tag with no Release).
HOLD_FILE = os.path.expanduser("~/.hermes/state/aero-release-HOLD")


def cut_release(dry: bool, auto: bool = False) -> int:
    """Create the due milestone Release WITHOUT GitHub Actions.

    Doctrine says release-on-milestone .yml does this automatically, but
    GitHub Actions is blocked account-wide here (every job rejected with
    zero steps, ~2s, no logs), so the rule had no engine and silently
    stopped after v1.5.0. This is the fallback the handover doc already
    sanctions: "Manual fallback: gh release create".

    GO-gated (Ruling 3): refuses to publish unless the founder GO file
    exists. Never publishes on its own.
    """
    leaves, _ = leaf_count()
    completed = (leaves // 100) * 100
    if completed < 100:
        print("cut: no milestone reached yet (leaves < 100)")
        return 0
    tag = "v" + band_version(completed)

    if not GH:
        print(f"cut: gh unavailable on PATH — cannot query or create Releases "
              f"on {PUBLIC_REPO}; install gh or export PATH=/opt/homebrew/bin:$PATH")
        return 1

    r = subprocess.run([GH, "release", "view", tag, "-R", PUBLIC_REPO],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"cut: {tag} already released on {PUBLIC_REPO} — nothing to do")
        return 0

    print(f"cut: {tag} is due ({completed} skills milestone, now {leaves})")
    if auto and os.path.exists(HOLD_FILE):
        print(f"cut: HOLD — auto-release paused by {HOLD_FILE} (remove to resume)")
        return 0
    if dry:
        gated = ("auto (founder standing GO)" if auto else
                 ("GO present" if os.path.exists(GO_FILE) else "HELD: no GO"))
        print(f"cut: WOULD create {tag} on {PUBLIC_REPO} ({gated}) (dry-run)")
        return 0
    if not auto and not os.path.exists(GO_FILE):
        print(f"cut: HELD — publish needs founder GO (Ruling 3).")
        print(f"     authorize with:  touch {GO_FILE}")
        return 1

    print(f"cut: creating {tag} on {PUBLIC_REPO}")
    # Real release notes: the milestone line + the commit log since the last
    # released tag (same generator as --changelog).
    notes = os.path.join(tempfile.gettempdir(), f"aero-release-{tag}.md")
    with open(notes, "w", encoding="utf-8") as fh:
        fh.write(f"Milestone release: {completed} skills reached "
                 f"(convention: every 100 new skills = one minor bump).\n\n"
                 f"{changelog_body()}\n")
    r = subprocess.run(
        [GH, "release", "create", tag, "-R", PUBLIC_REPO,
         "--title", f"Aero Agent Skills {tag}",
         "--notes-file", notes],
        capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--changelog", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="gate: fail if the release convention is not met")
    ap.add_argument("--cut", action="store_true",
                    help="create the due milestone Release locally (GO-gated)")
    ap.add_argument("--auto-cut", dest="auto_cut", action="store_true",
                    help="create the due milestone Release without the "
                         "per-release GO (founder standing GO 2026-09-10; "
                         "honours the aero-release-HOLD kill-switch)")
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    args = ap.parse_args()

    if args.check:
        return release_check()
    if args.cut or args.auto_cut:
        return cut_release(args.dry, auto=args.auto_cut)

    leaves, metrics = leaf_count()
    if args.status or not any([args.next, args.sync, args.changelog]):
        _, band, pkg = current_version()
        print(f"leaves: {leaves}  (band: {band} = skills {((leaves-1)//100)*100+1}-{((leaves-1)//100+1)*100})")
        print(f"npm package.json: {pkg}  |  band version: {band}")
        nb = next_release_info()
        print(f"next release: {nb[2]} at {nb[1]} leaves ({nb[3]} to go)")
    if args.next:
        nb = next_release_info()
        print(f"NEXT RELEASE: {nb[2]} when leaves hit {nb[1]} — {nb[3]} new skills needed (currently {nb[0]})")
    if args.sync:
        changes = sync_versions(dry=args.dry)
        if not changes:
            print("all package versions already at band — nothing to sync")
        else:
            for c in changes:
                print(("DRY-RUN " if args.dry else "") + c)
    if args.changelog:
        print(changelog_body())
    return 0


if __name__ == "__main__":
    sys.exit(main())
