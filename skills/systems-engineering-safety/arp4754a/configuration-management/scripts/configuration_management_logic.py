"""ARP4754A configuration management of aircraft system requirements and design data.

Pure Python 3, stdlib only. Deterministic and offline. Implements the
configuration management (CM) obligations of ARP4754A for system
development data:

  - Configuration item identification: which artifacts are under CM
    (requirements, design data, verification data, analysis).
  - Baseline creation: a versioned snapshot of a configuration item set.
  - Change control: change request -> impact analysis (affected
    requirements, design elements, verification methods, analyses) ->
    classification (minor vs major per ARP4754A: major when the change
    touches safety-relevant requirements, interfaces, or certification
    data) -> approval -> implementation -> verification.
  - Traceability closure checks: every requirement maps to a design
    element and a verification method; every derived requirement has a
    source.
  - Change history recording.

Standards note: ARP4754A text is proprietary (SAE); this module encodes
the CM process logic only, not the standard text.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

# Configuration item categories that require configuration management per
# ARP4754A: requirements, design data, verification data, analysis.
CONFIGURATION_ITEM_TYPES = ("requirement", "design", "verification", "analysis")

# Change control workflow states.
CHANGE_STATUSES = (
    "SUBMITTED",
    "IMPACT_ANALYSIS",
    "APPROVED",
    "IMPLEMENTED",
    "VERIFIED",
    "REJECTED",
)

# Flags on a change that force a MAJOR classification per ARP4754A.
MAJOR_CHANGE_FLAGS = ("safety_relevant", "interfaces_changed", "certification_data_changed")


def _item_id(item: Any) -> str:
    """Normalize a configuration item reference to its id string."""
    if isinstance(item, str):
        if not item.strip():
            raise ValueError("configuration item id must be a non-empty string")
        return item.strip()
    if isinstance(item, dict):
        iid = item.get("id")
        if not isinstance(iid, str) or not iid.strip():
            raise ValueError("configuration item dict requires a non-empty 'id'")
        return iid.strip()
    raise ValueError(
        "configuration item must be a string id or a dict with an 'id'"
    )


def identify_configuration_items(data: dict) -> list[dict]:
    """Classify which artifacts in a development data set are configuration items.

    Per ARP4754A, requirements, design data, verification data, and
    analysis are placed under configuration management. Other data (e.g.
    meeting minutes, working notes) is not a configuration item.

    Args:
        data: mapping of category name -> list of item ids (or dicts with
            an 'id'). Categories matching CONFIGURATION_ITEM_TYPES are
            configuration items; anything else is ignored.

    Returns:
        Sorted list of dicts {"id", "type", "version"} with version "1.0"
        for each identified configuration item.

    Raises:
        ValueError: data is not a dict, or an item has no valid id.
    """
    if not isinstance(data, dict):
        raise ValueError("data must be a dict of category -> item ids")
    items: list[dict] = []
    for category, entries in data.items():
        if not isinstance(entries, list):
            raise ValueError(
                "category %r must map to a list of item ids" % (category,)
            )
        if category not in CONFIGURATION_ITEM_TYPES:
            continue
        for entry in entries:
            items.append(
                {
                    "id": _item_id(entry),
                    "type": category,
                    "version": "1.0",
                }
            )
    items.sort(key=lambda it: (it["id"], it["type"]))
    return items


def create_baseline(
    items: list,
    name: Optional[str] = None,
    version: str = "1.0",
    baseline_id: str = "B-1",
    created: Optional[str] = None,
) -> dict:
    """Create a versioned baseline snapshot of a configuration item set.

    A baseline freezes the current versions of the configuration items
    (requirements, design data, verification data, analysis) so that
    subsequent changes are tracked against the frozen set.

    Args:
        items: non-empty list of item dicts {"id", ...} or id strings.
            Optional per-item 'type' (default 'requirement') and 'version'
            (default '1.0') are preserved in the snapshot.
        name: baseline name; defaults to "Baseline %s" % baseline_id.
        version: baseline version string (the baseline itself is versioned).
        baseline_id: baseline identifier.
        created: ISO date string; defaults to today. Pass explicitly for
            fully deterministic tests.

    Returns:
        dict with baseline_id, name, version, created, items (sorted by
        id), and item_count.

    Raises:
        ValueError: items is empty/not a list, an item has no valid id, or
            version/baseline_id are empty.
    """
    if not isinstance(items, list) or not items:
        raise ValueError("baseline requires a non-empty list of items")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("baseline version must be a non-empty string")
    if not isinstance(baseline_id, str) or not baseline_id.strip():
        raise ValueError("baseline_id must be a non-empty string")

    snapshot = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each baseline item must be a dict with an 'id'")
        iid = _item_id(item)
        itype = item.get("type", "requirement")
        iver = item.get("version", "1.0")
        if itype not in CONFIGURATION_ITEM_TYPES:
            raise ValueError(
                "unknown configuration item type %r for %r" % (itype, iid)
            )
        snapshot.append({"id": iid, "type": itype, "version": str(iver)})
    snapshot.sort(key=lambda it: (it["id"], it["type"]))

    return {
        "baseline_id": baseline_id,
        "name": name if name else "Baseline %s" % baseline_id,
        "version": version,
        "created": created if created else datetime.date.today().isoformat(),
        "items": snapshot,
        "item_count": len(snapshot),
    }


def _require_change(change: Any) -> dict:
    if not isinstance(change, dict):
        raise ValueError("change must be a dict")
    cid = change.get("id")
    if not isinstance(cid, str) or not cid.strip():
        raise ValueError("change requires a non-empty 'id'")
    return change


def change_impact_analysis(change: dict, trace_map: dict) -> dict:
    """Analyze which configuration items a proposed change affects.

    The change's affected item ids are expanded through the trace map:
    requirements named directly, and any requirement whose design
    elements, verification methods, or analyses are touched, are pulled
    into the impact set.

    Args:
        change: dict with 'id' (change request id), 'affected' (non-empty
            list of item ids: requirements, design elements, verification
            methods, or analyses), and optional flags
            safety_relevant / interfaces_changed / certification_data_changed.
        trace_map: dict with 'requirements' mapping requirement id -> entry
            dict. Entry keys: 'design' (list of design element ids),
            'verification' (list of verification method ids), 'analyses'
            (list of analysis ids), 'safety_critical' (bool).

    Returns:
        dict with change_id, affected_requirements, affected_design,
        affected_verification, affected_analyses (sorted unique lists) and
        safety_relevant (True when any affected requirement is safety
        critical or the change itself is flagged safety_relevant).

    Raises:
        ValueError: change or trace_map malformed, or 'affected' missing/empty.
    """
    change = _require_change(change)
    affected = change.get("affected")
    if not isinstance(affected, list) or not affected:
        raise ValueError("change requires a non-empty 'affected' list")
    if not isinstance(trace_map, dict):
        raise ValueError("trace_map must be a dict")
    reqs = trace_map.get("requirements")
    if not isinstance(reqs, dict):
        raise ValueError("trace_map requires a 'requirements' dict")

    # Normalize every requirement entry.
    for rid, entry in reqs.items():
        if not isinstance(entry, dict):
            raise ValueError("trace_map entry for %r must be a dict" % (rid,))
        for key in ("design", "verification", "analyses"):
            val = entry.get(key, [])
            if not isinstance(val, list):
                raise ValueError(
                    "trace_map entry %r %r must be a list" % (rid, key)
                )

    # Reverse index: item id -> set of requirement ids referencing it.
    reverse = {}  # item id -> set of requirement ids referencing it
    for rid, entry in reqs.items():
        for key in ("design", "verification", "analyses"):
            for iid in entry.get(key, []):
                reverse.setdefault(iid, set()).add(rid)

    req_hits: set[str] = set()
    for iid in affected:
        iid = _item_id({"id": iid})
        if iid in reqs:
            req_hits.add(iid)
        if iid in reverse:
            req_hits.update(reverse[iid])

    affected_reqs = sorted(req_hits)
    design: set[str] = set()
    verification: set[str] = set()
    analyses: set[str] = set()
    safety_relevant = bool(change.get("safety_relevant"))
    for rid in affected_reqs:
        entry = reqs[rid]
        design.update(entry.get("design", []))
        verification.update(entry.get("verification", []))
        analyses.update(entry.get("analyses", []))
        if entry.get("safety_critical"):
            safety_relevant = True

    return {
        "change_id": change["id"],
        "affected_requirements": affected_reqs,
        "affected_design": sorted(design),
        "affected_verification": sorted(verification),
        "affected_analyses": sorted(analyses),
        "safety_relevant": safety_relevant,
    }


def classify_change(impact: dict, change: Optional[dict] = None) -> str:
    """Classify a change as 'major' or 'minor' per ARP4754A.

    A change is MAJOR when it touches safety-relevant requirements,
    external/interface behavior, or certification data (per the ARP4754A
    change classification intent). A change that is safety_relevant,
    interfaces_changed, or certification_data_changed is major regardless
    of scope; otherwise it is minor.

    Args:
        impact: output of change_impact_analysis (or an equivalent dict
            with a 'safety_relevant' key).
        change: optional original change dict carrying the flags
            safety_relevant / interfaces_changed / certification_data_changed.

    Returns:
        "major" or "minor".

    Raises:
        ValueError: impact is not a dict, or change is provided and is not
            a dict.
    """
    if not isinstance(impact, dict):
        raise ValueError("impact must be a dict")
    reasons = []
    if impact.get("safety_relevant"):
        reasons.append("safety-relevant requirement affected")
    if change is not None:
        if not isinstance(change, dict):
            raise ValueError("change must be a dict")
        for flag in MAJOR_CHANGE_FLAGS:
            if change.get(flag):
                reasons.append(flag.replace("_", " "))
    return "major" if reasons else "minor"


def check_traceability_closure(trace_map: dict) -> dict:
    """Check traceability closure of a requirement set.

    Closure per ARP4754A CM/verification practice: every requirement maps
    to at least one design element and at least one verification method,
    and every derived requirement has a source.

    Args:
        trace_map: dict with 'requirements' mapping requirement id -> entry
            dict. Entry keys: 'design' (list), 'verification' (list),
            'derived' (bool), 'source' (str or None).

    Returns:
        dict with 'closed' (bool) and missing_design, missing_verification,
        missing_source (sorted lists of requirement ids).

    Raises:
        ValueError: trace_map is not a dict, 'requirements' is not a dict,
            or a requirement entry is not a dict.
    """
    if not isinstance(trace_map, dict):
        raise ValueError("trace_map must be a dict")
    reqs = trace_map.get("requirements")
    if not isinstance(reqs, dict):
        raise ValueError("trace_map requires a 'requirements' dict")

    missing_design: list[str] = []
    missing_verification: list[str] = []
    missing_source: list[str] = []
    for rid in sorted(reqs):
        entry = reqs[rid]
        if not isinstance(entry, dict):
            raise ValueError("trace_map entry for %r must be a dict" % (rid,))
        if not entry.get("design"):
            missing_design.append(rid)
        if not entry.get("verification"):
            missing_verification.append(rid)
        if entry.get("derived") and not entry.get("source"):
            missing_source.append(rid)

    closed = not (missing_design or missing_verification or missing_source)
    return {
        "closed": closed,
        "missing_design": missing_design,
        "missing_verification": missing_verification,
        "missing_source": missing_source,
    }


def record_change(
    change: dict,
    history: Optional[list] = None,
    date: Optional[str] = None,
) -> dict:
    """Record a change in the change history log.

    Appends one immutable record to the history list and returns it. The
    record captures the change id, description, classification (once the
    change has been through classify_change), and current status.

    Args:
        change: dict with 'id' (change request id); optional 'description',
            'classification', 'status' (default 'SUBMITTED').
        history: list to append to. Created if None; mutated in place so
            the caller keeps the log.
        date: ISO date string; defaults to today. Pass explicitly for
            fully deterministic tests.

    Returns:
        The appended record dict: record_id, change_id, description,
        classification, status, date.

    Raises:
        ValueError: change is not a dict or has no valid id; history is
            provided and is not a list.
    """
    change = _require_change(change)
    if history is not None and not isinstance(history, list):
        raise ValueError("history must be a list")
    if history is None:
        history = []
    status = change.get("status", "SUBMITTED")
    if status not in CHANGE_STATUSES:
        raise ValueError("unknown change status %r" % (status,))
    record = {
        "record_id": len(history) + 1,
        "change_id": change["id"],
        "description": change.get("description", ""),
        "classification": change.get("classification", "UNCATEGORIZED"),
        "status": status,
        "date": date if date else datetime.date.today().isoformat(),
    }
    history.append(record)
    return record
