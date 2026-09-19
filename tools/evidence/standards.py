#!/usr/bin/env python3
"""The standards editions a verdict was issued against.

A conformance verdict is meaningless without saying which edition of which
document it was measured against, so the record binds one entry per standard
in scope: the designation, the publisher, the revision token that the
designation itself carries, and the issue and date.

What this module will not do is invent an issue or a date.  The corpus's
standards map records id, title, family, publisher, status, domain,
applicability and gating - it has no issue field and no date field.  So every
entry is emitted with issue and issue_date present and explicitly null, and
with edition_binding set to "unbound" plus the reason.  An empty string or a
zero would read as a recorded value; a null beside a stated reason reads as
what it is, which is a gap someone has to close.

To close it, drop a standards-editions.json beside this module (see
standards-editions.example.json for the shape).  Entries found there are
merged in and marked "bound", and the overlay file is itself bound into the
record by digest so a later change to an edition claim is visible.

Only bibliographic identity is copied into a record: designation, title,
publisher, family, gating flag.  No clause text, no table, no applicability
prose ever enters an evidence record.
"""

import os
import re

from . import canonical, frontmatter

STANDARDS_SPEC = "aero-evidence-standards/1"
MAP_REF = "standards-map.yaml"
OVERLAY_FILENAME = "standards-editions.json"

_FIELDS = ("id", "name", "family", "publisher", "status", "gated", "domain")
_DESIGNATION_REVISION = re.compile(r"^([A-Za-z]+[- ]?\d+[A-Za-z0-9.-]*?)([A-Z])$")


def load_map(root):
    """Read standards-map.yaml.  Returns (entries_by_id, file_digest)."""
    path = os.path.join(root, MAP_REF)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    meaningful = [
        line
        for line in text.split("\n")
        if line.strip() and not line.lstrip().startswith("#")
    ]
    parsed = frontmatter.parse_block(meaningful, 0)
    entries = {}
    for item in parsed.get("standards") or []:
        if isinstance(item, dict) and item.get("id"):
            entries[str(item["id"])] = item
    return entries, canonical.digest_bytes(text.encode("utf-8"))


def load_overlay(module_dir=None):
    """Read the optional edition overlay.  Returns (mapping, binding_block)."""
    base = module_dir or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, OVERLAY_FILENAME)
    if not os.path.isfile(path):
        return {}, {
            "ref": "tools/evidence/" + OVERLAY_FILENAME,
            "present": False,
            "digest": None,
        }
    import json

    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    data = json.loads(raw)
    editions = data.get("editions") or {}
    return editions, {
        "ref": "tools/evidence/" + OVERLAY_FILENAME,
        "present": True,
        "digest": canonical.digest_bytes(raw.encode("utf-8")),
        "overlay_version": data.get("overlay_version"),
    }


def designation_of(title):
    """The short designation a title leads with, e.g. 'ARP4754A: ...'."""
    if not title:
        return None
    head = str(title).split(":", 1)[0].strip()
    return head or None


def revision_token(designation):
    """The revision letter a designation carries in its own name, if any."""
    if not designation:
        return None
    match = _DESIGNATION_REVISION.match(designation.replace(" ", ""))
    return match.group(2) if match else None


def entry_for(standard_id, entries, overlay):
    """Build one standards_in_scope entry."""
    raw = entries.get(standard_id)
    if raw is None:
        return {
            "id": standard_id,
            "resolved": False,
            "reason": "id does not resolve in " + MAP_REF,
            "issue": None,
            "issue_date": None,
            "edition_binding": "unresolved",
        }
    identity = {key: raw.get(key) for key in _FIELDS if raw.get(key) is not None}
    designation = designation_of(raw.get("name"))
    edition = overlay.get(standard_id) or {}
    issue = edition.get("issue")
    issue_date = edition.get("issue_date")
    if issue is not None or issue_date is not None:
        binding = "bound"
        source = "tools/evidence/" + OVERLAY_FILENAME
    else:
        binding = "unbound"
        source = MAP_REF + " records no issue or date field for any standard"
    return {
        "id": standard_id,
        "resolved": True,
        "designation": designation,
        "title": raw.get("name"),
        "publisher": raw.get("publisher"),
        "family": raw.get("family"),
        "status": raw.get("status"),
        "gated": bool(raw.get("gated")),
        "revision_token": revision_token(designation),
        "issue": issue,
        "issue_date": issue_date,
        "edition_binding": binding,
        "edition_source": source,
        "map_entry_digest": canonical.digest(identity),
    }


def in_scope(root, standard_ids, module_dir=None):
    """Return the standards block for a record body."""
    entries, map_digest = load_map(root)
    overlay, overlay_binding = load_overlay(module_dir)
    scoped = [entry_for(sid, entries, overlay) for sid in sorted(set(standard_ids))]
    unbound = [e["id"] for e in scoped if e.get("edition_binding") != "bound"]
    return {
        "spec": STANDARDS_SPEC,
        "map": {
            "ref": MAP_REF,
            "digest": map_digest,
            "entry_count": len(entries),
        },
        "editions_overlay": overlay_binding,
        "in_scope": scoped,
        "edition_gaps": unbound,
    }
