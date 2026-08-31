#!/usr/bin/env python3
"""SEP-2640 skill delivery logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, sep-2640: gated false,
open specification): SEP-2640 is the MCP working group's Skills
Extension draft - skills are served as resources (skill:// URIs,
resources/read, and directory listing behind the directoryRead
capability). The agentskills.io format stays the canonical content
form; SEP-2640 is an adapter layer for discovery and delivery,
emerging and not yet stable.
"""

import re

KEEP = {"SKILL.md"}


def _kebab(name):
    return bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name or ""))


def check_package(package_files, name, description):
    """Issues preventing SEP-2640 delivery of a skill package. The
    package must carry a conformant SKILL.md at its root."""
    issues = []
    if "SKILL.md" not in set(package_files) & KEEP:
        issues.append("missing SKILL.md at package root")
    if not name:
        issues.append("missing name")
    elif not _kebab(name):
        issues.append("name must be kebab-case (lowercase/numbers/hyphens)")
    if not description:
        issues.append("missing description")
    return issues


def package_conformance(package_files, name, description):
    """Conformance verdict for a skill package."""
    issues = check_package(package_files, name, description)
    status = "conformant" if not issues else "nonconformant"
    return status, issues


def skill_uri(namespace, skill_path):
    """SEP-2640 skill URI: skill://<namespace>/<skill-path>."""
    ns = (namespace or "").strip("/")
    path = (skill_path or "").strip("/")
    if not ns:
        raise ValueError("namespace required for skill URI")
    if not path:
        raise ValueError("skill path required for skill URI")
    return "skill://%s/%s" % (ns, path)


# SEP-2640 delivery model: skills are resources - addressable URIs,
# single-resource read, and directory listing behind directoryRead.
REQUIRED_CAPABILITIES = ("skill-uri", "resources-read", "directory-read")


def delivery_readiness(capabilities):
    """Ready when the MCP server exposes the SEP-2640 delivery model;
    returns (ready, missing)."""
    missing = [c for c in REQUIRED_CAPABILITIES if c not in set(capabilities)]
    return (len(missing) == 0, missing)
