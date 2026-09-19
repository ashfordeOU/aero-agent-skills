#!/usr/bin/env python3
"""Generate (and verify) the JetBrains plugin skill catalog (catalog.json).

Reads the repo skills/ tree (leaf SKILL.md frontmatter) and emits a compact
JSON list for the IDE catalog browser. The plugin bundle task copies this
into the plugin resources so the tool window works offline.

WHY --check EXISTS
------------------
The generator was correct and nobody ran it. The bundled catalogue declared
"count": 2685 against a 3,021-leaf tree -- 336 leaves the Marketplace build
shipped without -- and no gate looked. `--check` re-derives the catalogue from
the tree and fails (exit 1) when the committed file is not byte-identical, so
staleness reds in CI instead of shipping to buyers.

  python3 scripts/gen_jetbrains_catalog.py            # regenerate
  python3 scripts/gen_jetbrains_catalog.py --check    # red if stale
  python3 scripts/gen_jetbrains_catalog.py --truncation-report

DESCRIPTION TRUNCATION (open item, deliberately unchanged)
----------------------------------------------------------
Descriptions are cut to DESC_LIMIT characters. That behaviour is preserved
here on purpose -- it is a product decision, not a bug to fix in passing --
but every run now prints how much text the cut costs, so the decision can be
taken on evidence rather than on the assumption that it trims a long tail.
`--truncation-report` prints the worst offenders and the exact lost tail.
"""
import argparse
import json
import pathlib
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]  # scripts/ -> repo root
OUT = REPO / "packages" / "jetbrains-plugin" / "src" / "main" / "resources" / "catalog" / "catalog.json"
SOURCE_URL = "https://github.com/ashfordeOU/aero-agent-skills"

# Leaf depth inside skills/: family/pack/skill/SKILL.md
LEAF_PARTS = 4
DESC_LIMIT = 220


def collect(skills_root):
    """Return (rows, truncations, skipped).

    rows         -- catalogue rows in sorted-path order (the shipped payload)
    truncations  -- [(lost_chars, full_len, row_name, rel_path, lost_tail)]
    skipped      -- [(rel_path, reason)] leaves whose frontmatter would not parse
    """
    rows = []
    truncations = []
    skipped = []
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        rel = skill_md.relative_to(skills_root)
        parts = rel.parts  # family/pack/skill/SKILL.md
        if len(parts) != LEAF_PARTS:
            continue  # leaf only: family/pack/skill
        family, pack, skill = parts[0], parts[1], parts[2]
        rel_path = "/".join(parts[:3])
        try:
            text = skill_md.read_text(encoding="utf-8")
            fm = yaml.safe_load(text.split("---", 2)[1]) or {}
        except Exception as exc:  # noqa: BLE001 - one bad leaf must not abort the build
            skipped.append((rel_path, type(exc).__name__ + ": " + str(exc)))
            continue
        name = fm.get("name") or skill
        full = fm.get("description") or ""
        desc = full[:DESC_LIMIT]
        row_name = pack + "/" + str(name)
        if len(full) > DESC_LIMIT:
            truncations.append((len(full) - DESC_LIMIT, len(full), row_name,
                                rel_path, full[DESC_LIMIT:]))
        rows.append({"name": row_name, "family": family, "description": desc})
    truncations.sort(reverse=True)
    return rows, truncations, skipped


def render(rows):
    """The exact bytes that ship. Keep it compact: the plugin parses the whole
    document with a regex (SkillCatalogPanel.parseCatalog)."""
    return json.dumps({"count": len(rows), "source": SOURCE_URL, "skills": rows})


def truncation_summary(rows, truncations):
    if not truncations:
        return "truncation: 0 of {} descriptions exceed {} chars".format(
            len(rows), DESC_LIMIT)
    lost = sum(t[0] for t in truncations)
    worst = truncations[0]
    pct = 100.0 * len(truncations) / len(rows) if rows else 0.0
    return ("truncation: {} of {} descriptions ({:.1f}%) cut at {} chars; "
            "{} characters dropped in total; longest is {} at {} chars, "
            "losing {}").format(len(truncations), len(rows), pct, DESC_LIMIT,
                                lost, worst[2], worst[1], worst[0])


def print_truncation_report(rows, truncations, limit=10):
    print(truncation_summary(rows, truncations))
    if not truncations:
        return
    losses = sorted(t[0] for t in truncations)
    print("  median loss {} chars, min {}, max {}".format(
        losses[len(losses) // 2], losses[0], losses[-1]))
    print("  worst {} entries:".format(min(limit, len(truncations))))
    for lost, full_len, _row_name, rel_path, tail in truncations[:limit]:
        print("    {}  {} chars, loses {}".format(rel_path, full_len, lost))
        ell = "..." if len(tail) > 160 else ""
        print("      lost tail: {}{}".format(tail[:160], ell))


def diff_report(on_disk_text, fresh_text, fresh_rows):
    """Human-readable reasons the committed catalogue is not the fresh one."""
    notes = []
    try:
        old = json.loads(on_disk_text)
    except Exception as exc:  # noqa: BLE001
        return ["committed catalogue is not valid JSON ({}: {})".format(
            type(exc).__name__, exc)]
    old_rows = old.get("skills") or []
    notes.append("committed count field {!r} vs computed {}".format(
        old.get("count"), len(fresh_rows)))
    notes.append("committed rows {} vs computed {}".format(
        len(old_rows), len(fresh_rows)))
    fresh_by_name = {r["name"]: r for r in fresh_rows}
    old_by_name = {r.get("name"): r for r in old_rows}
    missing = sorted(set(fresh_by_name) - set(old_by_name))
    extra = sorted(n for n in set(old_by_name) - set(fresh_by_name) if n)
    if missing:
        notes.append("{} leaves in the tree are NOT in the committed catalogue, e.g. {}".format(
            len(missing), ", ".join(missing[:5])))
    if extra:
        notes.append("{} catalogue rows no longer exist in the tree, e.g. {}".format(
            len(extra), ", ".join(extra[:5])))
    if not missing and not extra:
        changed = [n for n in sorted(fresh_by_name)
                   if old_by_name[n].get("description") != fresh_by_name[n]["description"]
                   or old_by_name[n].get("family") != fresh_by_name[n]["family"]]
        if changed:
            notes.append("{} rows differ in family/description, e.g. {}".format(
                len(changed), ", ".join(changed[:5])))
        elif on_disk_text != fresh_text:
            notes.append("row set matches but the serialized bytes differ "
                         "(ordering, duplicate names, or formatting)")
    return notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="do not write; exit 1 if the committed catalogue is stale")
    ap.add_argument("--truncation-report", action="store_true",
                    help="print the worst description truncations and exit 0")
    args = ap.parse_args(argv)

    skills_root = REPO / "skills"
    if not skills_root.is_dir():
        print("FAIL jetbrains-catalog: no skills/ tree under the repo root",
              file=sys.stderr)
        return 1

    rows, truncations, skipped = collect(skills_root)
    fresh = render(rows)

    if args.truncation_report:
        print_truncation_report(rows, truncations)
        return 0

    for rel_path, reason in skipped:
        print("WARN jetbrains-catalog: skipped {} ({})".format(rel_path, reason),
              file=sys.stderr)

    if args.check:
        if not OUT.exists():
            print("FAIL jetbrains-catalog: catalog.json is missing; run "
                  "`python3 scripts/gen_jetbrains_catalog.py`", file=sys.stderr)
            return 1
        on_disk = OUT.read_text(encoding="utf-8")
        if on_disk == fresh:
            print("PASS jetbrains-catalog: catalog.json is current ({} leaves)".format(
                len(rows)))
            print(truncation_summary(rows, truncations))
            return 0
        print("FAIL jetbrains-catalog: the bundled catalogue is STALE - the IDE "
              "plugin would ship a catalogue that does not match the tree.",
              file=sys.stderr)
        for note in diff_report(on_disk, fresh, rows):
            print("  - " + note, file=sys.stderr)
        print("  fix: python3 scripts/gen_jetbrains_catalog.py", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(fresh, encoding="utf-8")
    print("wrote catalog.json ({} skills)".format(len(rows)))
    print(truncation_summary(rows, truncations))
    return 0


if __name__ == "__main__":
    sys.exit(main())
