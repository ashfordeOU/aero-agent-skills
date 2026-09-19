#!/usr/bin/env python3
"""Device database update after detailed design (ECSS-E-ST-20-40C 5.5.5).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The device repository is the hand-over surface between phases. Detailed
design closes by depositing into it everything the following phase needs to
start, and the update is judged by whether the following phase can in fact
start, not by how many items were deposited.

Three failures hide inside a repository that looks full:

* a required input is simply absent. The kind was never deposited, and the
  gap is invisible while the deposit list is read on its own because every
  item in it is legitimate;
* an input is present but not released. A draft or a superseded item reads
  as coverage in a listing and cannot be built against;
* an input is present, released, and older than the design baseline it is
  supposed to carry. It is the hardest of the three to see, because the
  item is perfectly valid -- for a design that no longer exists.

Readiness is therefore a fraction of the required kinds actually satisfied
by a released item at or above the baseline, and a kind satisfied exactly
at the baseline revision counts, since revisions are compared as integer
tuples rather than as numbers.
"""

import math

# Kinds of item a device repository holds.
ITEM_KINDS = (
    "netlist",
    "constraint-set",
    "timing-model",
    "power-model",
    "test-bench",
    "simulation-result",
    "design-report",
    "library-reference",
    "layout-database",
    "test-pattern-set",
    "validation-plan",
)

_KIND_ALIASES = {
    "netlist": "netlist",
    "gate-level netlist": "netlist",
    "constraint-set": "constraint-set",
    "constraints": "constraint-set",
    "sdc": "constraint-set",
    "timing-model": "timing-model",
    "timing model": "timing-model",
    "power-model": "power-model",
    "power model": "power-model",
    "test-bench": "test-bench",
    "testbench": "test-bench",
    "simulation-result": "simulation-result",
    "design-report": "design-report",
    "library-reference": "library-reference",
    "layout-database": "layout-database",
    "gds": "layout-database",
    "test-pattern-set": "test-pattern-set",
    "atpg": "test-pattern-set",
    "validation-plan": "validation-plan",
}

# What each following phase needs before it can start.
REQUIRED_INPUTS = {
    "layout": ("netlist", "constraint-set", "timing-model", "design-report"),
    "manufacturing": (
        "layout-database",
        "test-pattern-set",
        "design-report",
        "library-reference",
    ),
    "validation": ("test-bench", "validation-plan", "timing-model", "power-model"),
}
FOLLOWING_PHASES = tuple(sorted(REQUIRED_INPUTS))

# Deposit states an item can carry.
ITEM_STATES = ("released", "draft", "superseded")

REL_TOL = 1e-12
ABS_TOL = 1e-18

_ITEM_KEYS = ("id", "kind", "revision", "state", "checksum")


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


def normalize_item_kind(value):
    """Fold a repository item kind onto one of the recognised kinds."""
    key = " ".join(_text("kind", value).lower().split())
    if key in _KIND_ALIASES:
        return _KIND_ALIASES[key]
    raise ValueError(
        "unknown repository item kind %r; use one of %s"
        % (value, ", ".join(ITEM_KINDS))
    )


def normalize_state(value):
    """Fold a deposit state onto one of the recognised states."""
    key = " ".join(_text("state", value).lower().replace("_", " ").split())
    aliases = {
        "released": "released",
        "issued": "released",
        "frozen": "released",
        "draft": "draft",
        "work in progress": "draft",
        "wip": "draft",
        "superseded": "superseded",
        "obsolete": "superseded",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown deposit state %r; use one of %s" % (value, ", ".join(ITEM_STATES))
    )


def normalize_phase(value):
    """Fold the name of the following phase onto a recognised phase."""
    key = " ".join(_text("phase", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    aliases = {
        "layout": "layout",
        "place-and-route": "layout",
        "manufacturing": "manufacturing",
        "fabrication": "manufacturing",
        "validation": "validation",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown following phase %r; use one of %s"
        % (value, ", ".join(FOLLOWING_PHASES))
    )


def required_inputs_for(phase):
    """The item kinds the named following phase needs before it can start."""
    return REQUIRED_INPUTS[normalize_phase(phase)]


def parse_revision(value):
    """Parse a dotted revision onto a tuple of integers for exact comparison."""
    text = _text("revision", value)
    parts = text.split(".")
    resolved = []
    for part in parts:
        token = part.strip()
        if not token or not token.isdigit():
            raise ValueError(
                "revision %r must be dotted non-negative integers, e.g. 2.1.0" % value
            )
        resolved.append(int(token))
    return tuple(resolved)


def compare_revisions(left, right):
    """Return -1, 0 or 1 comparing two dotted revisions of any depth."""
    a = parse_revision(left)
    b = parse_revision(right)
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    if a < b:
        return -1
    return 0 if a == b else 1


def is_at_or_above_baseline(revision, baseline):
    """True when an item carries the design baseline or something later."""
    return compare_revisions(revision, baseline) >= 0


def validate_repository(entries):
    """Check the deposited items and return them resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("repository must be a list of deposited items")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("items[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ITEM_KEYS))
        if unknown:
            raise ValueError(
                "items[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "kind", "revision"):
            if key not in entry:
                raise ValueError("items[%d] missing key: %s" % (index, key))
        item_id = _text("items[%d].id" % index, entry["id"])
        if item_id in seen:
            raise ValueError("duplicate repository item id %r" % item_id)
        seen.add(item_id)
        resolved.append(
            {
                "id": item_id,
                "kind": normalize_item_kind(entry["kind"]),
                "revision": _text("items[%d].revision" % index, entry["revision"]),
                "state": normalize_state(entry.get("state", "released")),
                "checksum": _text(
                    "items[%d].checksum" % index,
                    entry.get("checksum", ""),
                    allow_empty=True,
                ),
            }
        )
        parse_revision(resolved[-1]["revision"])
    return resolved


def usable_items(items, baseline):
    """Items a following phase can actually build against, grouped by kind."""
    grouped = {}
    for item in items:
        if item["state"] != "released":
            continue
        if not is_at_or_above_baseline(item["revision"], baseline):
            continue
        grouped.setdefault(item["kind"], []).append(item["id"])
    return {kind: sorted(ids) for kind, ids in grouped.items()}


def readiness(items, phase, baseline):
    """Fraction of the following phase's required kinds that is usable."""
    required = required_inputs_for(phase)
    if not required:
        raise ValueError("phase %r declares no required input" % phase)
    usable = usable_items(items, baseline)
    satisfied = sum(1 for kind in required if usable.get(kind))
    return satisfied / len(required)


def assess_database_update(repository, phase, baseline, readiness_goal=1.0):
    """Full 5.5.5 assessment of one device repository update.

    Returns the usable items grouped by kind, the readiness reached, the
    findings and the verdict.
    """
    items = validate_repository(repository)
    if not items:
        raise ValueError("the repository update must deposit at least one item")
    phase = normalize_phase(phase)
    baseline = _text("baseline", baseline)
    parse_revision(baseline)
    readiness_goal = _fraction("readiness_goal", readiness_goal)

    required = required_inputs_for(phase)
    usable = usable_items(items, baseline)
    findings = []

    for item in items:
        if not item["checksum"]:
            findings.append(
                {
                    "code": "item-without-integrity-record",
                    "item": item["id"],
                    "detail": "%s carries no checksum, so the deposit cannot be "
                    "shown to be the artefact it claims" % item["id"],
                }
            )
        if item["state"] == "draft":
            findings.append(
                {
                    "code": "item-not-released",
                    "item": item["id"],
                    "detail": "%s is deposited as a draft and cannot be built "
                    "against" % item["id"],
                }
            )
        elif item["state"] == "superseded":
            findings.append(
                {
                    "code": "item-superseded",
                    "item": item["id"],
                    "detail": "%s is marked superseded and still sits in the "
                    "repository" % item["id"],
                }
            )
        elif not is_at_or_above_baseline(item["revision"], baseline):
            findings.append(
                {
                    "code": "item-behind-design-baseline",
                    "item": item["id"],
                    "revision": item["revision"],
                    "baseline": baseline,
                    "detail": "%s is released at %s, behind the %s design baseline"
                    % (item["id"], item["revision"], baseline),
                }
            )

    for kind in required:
        if usable.get(kind):
            continue
        present = [i["id"] for i in items if i["kind"] == kind]
        if present:
            findings.append(
                {
                    "code": "required-input-present-but-unusable",
                    "kind": kind,
                    "items": sorted(present),
                    "detail": "the %s phase needs a %s and the repository holds "
                    "one, but not released at or above the baseline"
                    % (phase, kind),
                }
            )
        else:
            findings.append(
                {
                    "code": "required-input-missing",
                    "kind": kind,
                    "detail": "the %s phase needs a %s and the repository holds "
                    "none" % (phase, kind),
                }
            )

    reached = readiness(items, phase, baseline)
    if not (
        reached > readiness_goal
        or math.isclose(reached, readiness_goal, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    ):
        findings.append(
            {
                "code": "readiness-goal-missed",
                "achieved": reached,
                "goal": readiness_goal,
                "detail": "the repository reaches %.1f %% readiness against a "
                "%.1f %% goal" % (100.0 * reached, 100.0 * readiness_goal),
            }
        )

    return {
        "phase": phase,
        "baseline": baseline,
        "item_count": len(items),
        "required_inputs": list(required),
        "usable_by_kind": usable,
        "readiness": reached,
        "missing_inputs": sorted(kind for kind in required if not usable.get(kind)),
        "deposits_beyond_need": sorted(
            {i["kind"] for i in items} - set(required)
        ),
        "findings": findings,
        "ready": not findings,
    }
