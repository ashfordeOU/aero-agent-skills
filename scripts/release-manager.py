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
import subprocess
import sys

REPO = os.path.expanduser("~/AeroSkills")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--changelog", action="store_true")
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    args = ap.parse_args()

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
