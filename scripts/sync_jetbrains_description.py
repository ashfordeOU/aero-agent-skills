#!/usr/bin/env python3
"""Sync the JetBrains storefront description to the catalog the plugin ships.

The Marketplace page description is overwritten from build.gradle.kts on every
publish, so a hardcoded number there is a marketing claim that silently goes
stale: it read "330+ verified skills" while the shipped catalog held 1439, and
listed 8 of the 12 families. Both figures now come from the SAME catalog.json
the plugin ships, so the storefront and the in-IDE browser cannot disagree.

Run AFTER scripts/gen_jetbrains_catalog.py and BEFORE the gradle build.
Idempotent. Refuses rather than writing a zero or a placeholder.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "packages/jetbrains-plugin/src/main/resources/catalog/catalog.json")
GRADLE = os.path.join(ROOT, "packages/jetbrains-plugin/build.gradle.kts")

# Families whose display name is not just the slug with hyphens removed.
LABELS = {
    "gnc-autonomy": "GNC/autonomy",
    "systems-engineering-safety": "systems engineering and safety",
    "cross-cutting": "cross-cutting",
}

BULLET_RE = re.compile(
    r"<li><b>[^<]*?verified skills</b> across .*?</li>", re.DOTALL
)


def label(slug):
    return LABELS.get(slug, slug.replace("-", " "))


def describe(catalog_path):
    """-> (count, family_list_prose). Raises on anything that would ship a lie."""
    with open(catalog_path) as fh:
        data = json.load(fh)
    count = data.get("count")
    skills = data.get("skills") or []
    if not isinstance(count, int) or count < 1:
        raise ValueError("catalog count is missing or not a positive integer")
    if count != len(skills):
        raise ValueError(
            "catalog count %d disagrees with %d skill entries" % (count, len(skills))
        )
    # case-insensitive: plain sorted() puts "GNC/autonomy" before "aerodynamics"
    fams = sorted({label(s["family"]) for s in skills if s.get("family")}, key=str.lower)
    if not fams:
        raise ValueError("catalog has no family fields")
    if len(fams) == 1:
        prose = fams[0]
    else:
        prose = ", ".join(fams[:-1]) + ", and " + fams[-1]
    return count, prose


def render(count, prose):
    return "<li><b>{:,} verified skills</b> across {}</li>".format(count, prose)


def main():
    count, prose = describe(CATALOG)
    with open(GRADLE) as fh:
        src = fh.read()
    if not BULLET_RE.search(src):
        print("FAIL sync-jetbrains-description: skills bullet not found in build.gradle.kts")
        return 1
    new = BULLET_RE.sub(render(count, prose), src, count=1)
    if new == src:
        print("OK  sync-jetbrains-description: already at {:,} skills, {} families".format(
            count, prose.count(",") + 1))
        return 0
    tmp = GRADLE + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(new)
    os.replace(tmp, GRADLE)  # atomic: the hourly publish job reads this tree
    print("OK  sync-jetbrains-description: description now says {:,} verified skills".format(count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
