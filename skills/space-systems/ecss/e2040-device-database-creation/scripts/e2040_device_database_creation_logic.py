#!/usr/bin/env python3
"""Design database creation (ECSS-E-ST-20-40C clause 5.4.4).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The clause puts a repository of design inputs between the design and
verification phase and the detailed design phase. The repository holds
entries; the detailed design activities declare what they read. The
useful checks run between the two:

* an entry carries a category, a version and a state. The state decides
  whether anything may be built on it, and a draft read as released is
  the failure the repository exists to prevent;
* a superseded entry names its successor, and the successor has to be
  held. A supersession pointing nowhere marks an entry do-not-use with
  no instruction on what to use;
* demand comes from the activities. An input declared and not held is a
  gap the repository cannot see by looking at itself;
* an entry nobody declares stays visible: it is either a forgotten
  declaration or a dead input, and both are worth reporting;
* readiness is the fraction of declared demands met by a released
  entry. A threshold met exactly is met, so the comparison absorbs
  representation error rather than failing on the last bit of a
  division.
"""

import math

RELEASED = "released"
DRAFT = "draft"
OBSOLETE = "obsolete"
SUPERSEDED = "superseded"
ENTRY_STATES = (RELEASED, DRAFT, OBSOLETE, SUPERSEDED)
USABLE_STATES = (RELEASED,)
_STATE_ALIASES = {
    "released": RELEASED,
    "release": RELEASED,
    "approved": RELEASED,
    "issued": RELEASED,
    "baselined": RELEASED,
    "draft": DRAFT,
    "preliminary": DRAFT,
    "working": DRAFT,
    "obsolete": OBSOLETE,
    "withdrawn": OBSOLETE,
    "cancelled": OBSOLETE,
    "superseded": SUPERSEDED,
    "replaced": SUPERSEDED,
}

INPUT_CATEGORIES = (
    "requirement-baseline",
    "architecture-model",
    "technology-library",
    "design-constraint",
    "tool-configuration",
    "heritage-data",
)
_CATEGORY_ALIASES = {
    "requirement-baseline": "requirement-baseline",
    "requirements": "requirement-baseline",
    "requirement baseline": "requirement-baseline",
    "architecture-model": "architecture-model",
    "architecture": "architecture-model",
    "architecture model": "architecture-model",
    "technology-library": "technology-library",
    "library": "technology-library",
    "cell library": "technology-library",
    "technology library": "technology-library",
    "design-constraint": "design-constraint",
    "constraints": "design-constraint",
    "design constraint": "design-constraint",
    "tool-configuration": "tool-configuration",
    "tools": "tool-configuration",
    "tool configuration": "tool-configuration",
    "heritage-data": "heritage-data",
    "heritage": "heritage-data",
    "heritage data": "heritage-data",
}

REL_TOL = 1e-12
ABS_TOL = 1e-18

_ENTRY_KEYS = ("id", "category", "version", "state", "successor", "source")
_ACTIVITY_KEYS = ("id", "inputs")
_DATABASE_REQUIRED_KEYS = ("entries", "activities")
_DATABASE_OPTIONAL_KEYS = ("readiness_threshold",)


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_readiness_threshold(achieved, threshold):
    """True when achieved readiness reaches the threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_state(value):
    """Fold an entry state spelling onto one of the four recognised states."""
    key = " ".join(_text("state", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-") if key.replace(" ", "-") in _STATE_ALIASES else key
    if key in _STATE_ALIASES:
        return _STATE_ALIASES[key]
    raise ValueError(
        "unknown entry state %r; use one of %s" % (value, ", ".join(ENTRY_STATES))
    )


def normalize_category(value):
    """Fold an input category spelling onto a recognised category."""
    key = " ".join(_text("category", value).lower().replace("_", " ").split())
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    hyphenated = key.replace(" ", "-")
    if hyphenated in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[hyphenated]
    raise ValueError(
        "unknown input category %r; use one of %s"
        % (value, ", ".join(INPUT_CATEGORIES))
    )


def is_usable_state(state):
    """True when an activity may build on an entry in this state."""
    return normalize_state(state) in USABLE_STATES


def validate_entries(records):
    """Check the repository entries and return them resolved in declared order."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("entries must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_ENTRY_KEYS))
        if unknown:
            raise ValueError(
                "entries[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "category", "state"):
            if key not in record:
                raise ValueError("entries[%d] missing key: %s" % (index, key))
        entry_id = _text("entries[%d].id" % index, record["id"])
        if entry_id in seen:
            raise ValueError("duplicate entry id %r" % entry_id)
        seen.add(entry_id)
        resolved.append(
            {
                "id": entry_id,
                "category": normalize_category(record["category"]),
                "version": _text(
                    "entries[%d].version" % index,
                    record.get("version", ""),
                    allow_empty=True,
                ),
                "state": normalize_state(record["state"]),
                "successor": _text(
                    "entries[%d].successor" % index,
                    record.get("successor", ""),
                    allow_empty=True,
                ),
                "source": _text(
                    "entries[%d].source" % index,
                    record.get("source", ""),
                    allow_empty=True,
                ),
            }
        )
    held = {entry["id"] for entry in resolved}
    for entry in resolved:
        if entry["state"] == SUPERSEDED:
            if not entry["successor"]:
                raise ValueError(
                    "entry %r is superseded and names no successor" % entry["id"]
                )
            if entry["successor"] not in held:
                raise ValueError(
                    "entry %r names successor %r, which the repository does not hold"
                    % (entry["id"], entry["successor"])
                )
            if entry["successor"] == entry["id"]:
                raise ValueError("entry %r supersedes itself" % entry["id"])
    return resolved


def validate_activities(records):
    """Check the detailed design activities and the inputs each declares."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("activities must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("activities[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_ACTIVITY_KEYS))
        if unknown:
            raise ValueError(
                "activities[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in record:
            raise ValueError("activities[%d] missing key: id" % index)
        activity_id = _text("activities[%d].id" % index, record["id"])
        if activity_id in seen:
            raise ValueError("duplicate activity id %r" % activity_id)
        seen.add(activity_id)
        inputs = record.get("inputs", [])
        if isinstance(inputs, str) or not isinstance(inputs, (list, tuple)):
            raise ValueError("activities[%d].inputs must be a list" % index)
        declared = []
        for position, name in enumerate(inputs):
            text = _text("activities[%d].inputs[%d]" % (index, position), name)
            if text not in declared:
                declared.append(text)
        resolved.append({"id": activity_id, "inputs": declared})
    return resolved


def declared_demands(activities):
    """Every (activity, input) pair the detailed design declares it reads."""
    return [(a["id"], name) for a in activities for name in a["inputs"]]


def missing_inputs(entries, activities):
    """Declared inputs the repository does not hold, as (activity, input)."""
    held = {entry["id"] for entry in entries}
    return sorted(
        (activity, name)
        for activity, name in declared_demands(activities)
        if name not in held
    )


def unstable_inputs(entries, activities):
    """Held inputs an activity reads while their state is not usable."""
    by_id = {entry["id"]: entry for entry in entries}
    out = []
    for activity, name in declared_demands(activities):
        entry = by_id.get(name)
        if entry is not None and entry["state"] not in USABLE_STATES:
            out.append((activity, name, entry["state"]))
    return sorted(out)


def orphan_entries(entries, activities):
    """Entry ids no detailed design activity declares it reads."""
    declared = {name for _, name in declared_demands(activities)}
    return sorted(entry["id"] for entry in entries if entry["id"] not in declared)


def database_readiness(entries, activities):
    """Fraction of declared demands met by a held entry in a usable state."""
    demands = declared_demands(activities)
    if not demands:
        raise ValueError("database_readiness needs at least one declared input")
    by_id = {entry["id"]: entry for entry in entries}
    met = 0
    for _, name in demands:
        entry = by_id.get(name)
        if entry is not None and entry["state"] in USABLE_STATES:
            met += 1
    return met / len(demands)


def evaluate_design_database(database):
    """Full clause 5.4.4 assessment of one design input repository.

    Returns the readiness reached, the gaps, the findings and the verdict.
    """
    if not isinstance(database, dict):
        raise ValueError(
            "database must be a mapping of entries, activities and a threshold"
        )
    known = set(_DATABASE_REQUIRED_KEYS) | set(_DATABASE_OPTIONAL_KEYS)
    unknown = sorted(set(database) - known)
    if unknown:
        raise ValueError("unknown database keys: %s" % ", ".join(unknown))
    absent = [key for key in _DATABASE_REQUIRED_KEYS if key not in database]
    if absent:
        raise ValueError("database missing required keys: %s" % ", ".join(absent))

    entries = validate_entries(database["entries"])
    activities = validate_activities(database["activities"])
    if not activities:
        raise ValueError("database must carry at least one detailed design activity")
    if not declared_demands(activities):
        raise ValueError("no activity declares an input, so nothing can be assessed")

    findings = []
    for entry in entries:
        if not entry["version"]:
            findings.append(
                {
                    "code": "entry-without-version",
                    "entry": entry["id"],
                    "detail": "entry %s carries no version, so a reader cannot say "
                    "which one it built on" % entry["id"],
                }
            )

    for activity, name in missing_inputs(entries, activities):
        findings.append(
            {
                "code": "declared-input-not-held",
                "activity": activity,
                "input": name,
                "detail": "activity %s declares input %r, which the repository does "
                "not hold" % (activity, name),
            }
        )

    for activity, name, state in unstable_inputs(entries, activities):
        findings.append(
            {
                "code": "unstable-input-read",
                "activity": activity,
                "input": name,
                "state": state,
                "detail": "activity %s reads %r while it is %s, so the input can "
                "move under work already done on it" % (activity, name, state),
            }
        )

    for entry_id in orphan_entries(entries, activities):
        findings.append(
            {
                "code": "entry-declared-by-no-activity",
                "entry": entry_id,
                "detail": "entry %s is held and no activity declares it" % entry_id,
            }
        )

    readiness = database_readiness(entries, activities)
    threshold = database.get("readiness_threshold")
    if threshold is not None:
        threshold_value = _fraction("readiness_threshold", threshold)
        if not meets_readiness_threshold(readiness, threshold_value):
            findings.append(
                {
                    "code": "readiness-below-threshold",
                    "achieved": readiness,
                    "threshold": threshold_value,
                    "detail": "repository readiness reaches %.1f %% against a "
                    "%.1f %% threshold" % (100.0 * readiness, 100.0 * threshold_value),
                }
            )

    return {
        "entry_count": len(entries),
        "activity_count": len(activities),
        "demand_count": len(declared_demands(activities)),
        "missing_inputs": missing_inputs(entries, activities),
        "unstable_inputs": unstable_inputs(entries, activities),
        "orphan_entries": orphan_entries(entries, activities),
        "readiness": readiness,
        "findings": findings,
        "acceptable": not findings,
    }
