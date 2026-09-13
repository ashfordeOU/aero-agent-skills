#!/usr/bin/env python3
"""Content audit of a multipactor verification plan.

Anchor: ECSS-E-ST-20-01C clause 4.2.2 (the items the multipactor
verification plan adds to the generic verification plan data item).
Paraphrased into an implementable procedure; no verbatim standard text.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. resolve each declared content entry to a canonical multipactor-specific
   content key and reject an entry nobody can place;
2. decide whether the entry actually adds content: a detailed entry does,
   a placeholder or a bare cross-reference back to the parent verification
   plan data item does not;
3. take the weighted coverage of the required additions and separate the
   missing keys from the ones present in name only;
4. resolve the verification method declared for each multipactor-critical
   item to the extra fields that method owes;
5. audit each item against those fields, including the engineering checks
   that make them meaningful -- a seeded discharge, an independent
   detection pair, a vacuum pressure below the corona regime, a positive
   dwell and a positive analysis margin;
6. compare the weighted completeness with the agreed minimum, absorbing
   floating-point representation error at the boundary;
7. aggregate into a plan-level content verdict.

The content catalogue, weights and vocabularies below are
project-replaceable defaults expressing the clause intent, not a
reproduction of any table of the standard.
"""

import math

# A completeness landing exactly on the agreed minimum is compliant; the
# comparison absorbs floating-point representation error instead of moving
# the engineering requirement.
COVERAGE_REL_TOL = 1e-9
COVERAGE_ABS_TOL = 1e-12

# Above this pressure the discharge of interest is a gas breakdown, not a
# vacuum multipactor discharge.
VACUUM_CEILING_MBAR = 1.0e-4

DEFAULT_MIN_COMPLETENESS = 1.0

# Multipactor-specific additions to the parent verification plan data item.
# key -> (weight, what the entry has to establish)
CONTENT_ITEMS = {
    "multipactor-critical-item-list": (
        1.5,
        "every unit, interface and gap carried into the multipactor assessment",
    ),
    "verification-method-per-item": (
        1.5,
        "the route agreed for each listed item and the reason it applies",
    ),
    "multipactor-margin-policy": (
        1.2,
        "the margin owed by each route and the reference it is taken against",
    ),
    "rf-power-level-and-dwell-duration": (
        1.2,
        "the level each item is driven to and how long it is held there",
    ),
    "vacuum-and-venting-conditions": (
        1.0,
        "the pressure regime and venting history the demonstration runs in",
    ),
    "electron-seeding-provision": (
        1.0,
        "how free electrons are supplied so a discharge can start at all",
    ),
    "detection-method-pair": (
        1.0,
        "the independent global and local methods that witness a discharge",
    ),
    "pass-fail-criteria": (
        1.1,
        "what counts as a discharge and what closes the item",
    ),
    "non-conformance-route": (
        0.8,
        "what happens to an item that discharges during the campaign",
    ),
    "verification-schedule-and-facility": (
        0.7,
        "where and when each demonstration is run",
    ),
}

CONTENT_ALIASES = {
    "critical-item-list": "multipactor-critical-item-list",
    "multipactor-item-list": "multipactor-critical-item-list",
    "method-per-item": "verification-method-per-item",
    "margin-policy": "multipactor-margin-policy",
    "power-and-duration": "rf-power-level-and-dwell-duration",
    "venting-conditions": "vacuum-and-venting-conditions",
    "seeding-provision": "electron-seeding-provision",
    "detection-methods": "detection-method-pair",
    "acceptance-criteria": "pass-fail-criteria",
    "nonconformance-route": "non-conformance-route",
    "schedule-and-facility": "verification-schedule-and-facility",
}

# How a declared entry is written up. Only a detailed entry adds content.
ENTRY_STATES = {
    "detailed": True,
    "placeholder": False,
    "parent-cross-reference": False,
    "to-be-defined": False,
}

VERIFICATION_METHODS = {
    "multipactor-test": (
        "test-power-level-dbm",
        "dwell-duration-minutes",
        "vacuum-pressure-mbar",
        "electron-seeding-source",
        "detection-methods",
    ),
    "multipactor-analysis": (
        "susceptibility-model",
        "secondary-electron-yield-source",
        "gap-geometry-source",
        "analysis-margin-db",
    ),
    "similarity": (
        "reference-equipment-id",
        "delta-justification",
        "heritage-evidence-ref",
    ),
}

METHOD_ALIASES = {
    "test": "multipactor-test",
    "multipactor-test": "multipactor-test",
    "analysis": "multipactor-analysis",
    "multipactor-analysis": "multipactor-analysis",
    "similarity": "similarity",
    "heritage-similarity": "similarity",
}

SEEDING_SOURCES = ("radioactive-source", "ultraviolet-source", "electron-gun")

# Global methods watch the whole path, local ones watch one gap; a valid
# plan names at least two distinct methods.
DETECTION_METHODS = {
    "forward-reverse-power-nulling": "global",
    "close-to-carrier-noise": "global",
    "third-harmonic-detection": "local",
    "electron-current-probe": "local",
    "optical-emission-monitoring": "local",
}


def meets_threshold(value, minimum):
    """Threshold comparison that absorbs representation error only."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be numeric, got %r" % (value,))
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool):
        raise ValueError("minimum must be numeric, got %r" % (minimum,))
    return float(value) >= float(minimum) or math.isclose(
        float(value), float(minimum), rel_tol=COVERAGE_REL_TOL, abs_tol=COVERAGE_ABS_TOL
    )


def canonical_content_key(raw):
    """Resolve a declared content heading to a catalogue key."""
    if not isinstance(raw, str):
        raise ValueError("content key must be a string, got %r" % (raw,))
    key = raw.strip().lower().replace(" ", "-").replace("_", "-")
    if not key:
        raise ValueError("content key must not be empty")
    key = CONTENT_ALIASES.get(key, key)
    if key not in CONTENT_ITEMS:
        raise ValueError(
            "unrecognized plan content key %r; known: %s"
            % (raw, ", ".join(sorted(CONTENT_ITEMS)))
        )
    return key


def canonical_method(raw):
    """Resolve a declared verification route to a catalogue method."""
    if not isinstance(raw, str):
        raise ValueError("verification method must be a string, got %r" % (raw,))
    key = raw.strip().lower()
    if not key:
        raise ValueError("verification method must not be empty")
    key = METHOD_ALIASES.get(key, key)
    if key not in VERIFICATION_METHODS:
        raise ValueError(
            "unrecognized verification method %r; known: %s"
            % (raw, ", ".join(sorted(VERIFICATION_METHODS)))
        )
    return key


def required_fields_for_method(method):
    """Extra fields the plan owes for one verification route."""
    return VERIFICATION_METHODS[canonical_method(method)]


def evaluate_content_entry(entry):
    """Decide whether one declared entry adds multipactor-specific content."""
    if not isinstance(entry, dict):
        raise ValueError("content entry must be a mapping, got %r" % (entry,))
    key = canonical_content_key(entry.get("key"))
    state = entry.get("state", "detailed")
    if not isinstance(state, str):
        raise ValueError("entry state must be a string, got %r" % (state,))
    state = state.strip().lower()
    if state not in ENTRY_STATES:
        raise ValueError(
            "unrecognized entry state %r; known: %s"
            % (state, ", ".join(sorted(ENTRY_STATES)))
        )
    adds = ENTRY_STATES[state]
    findings = []
    if state == "parent-cross-reference":
        findings.append(
            "entry %s only points back at the parent verification plan data item; "
            "clause 4.2.2 asks for the multipactor-specific addition" % key
        )
    elif not adds:
        findings.append("entry %s is %s and adds no content yet" % (key, state))
    return {
        "key": key,
        "state": state,
        "adds_content": adds,
        "weight": CONTENT_ITEMS[key][0],
        "purpose": CONTENT_ITEMS[key][1],
        "findings": findings,
    }


def audit_content_coverage(entries):
    """Weighted coverage of the required multipactor-specific additions."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("content entries must be a list of records")
    seen = {}
    findings = []
    for index, entry in enumerate(entries):
        try:
            evaluated = evaluate_content_entry(entry)
        except ValueError as exc:
            raise ValueError("content entry[%d]: %s" % (index, exc))
        if evaluated["key"] in seen:
            raise ValueError("content key %r declared twice" % evaluated["key"])
        seen[evaluated["key"]] = evaluated
        findings.extend(evaluated["findings"])
    total_weight = sum(weight for weight, _ in CONTENT_ITEMS.values())
    covered_weight = 0.0
    present = []
    name_only = []
    missing = []
    for key in CONTENT_ITEMS:
        evaluated = seen.get(key)
        if evaluated is None:
            missing.append(key)
            findings.append(
                "required addition %s is absent from the plan (%s)"
                % (key, CONTENT_ITEMS[key][1])
            )
        elif evaluated["adds_content"]:
            covered_weight += evaluated["weight"]
            present.append(key)
        else:
            name_only.append(key)
    fraction = covered_weight / total_weight
    return {
        "present": present,
        "name_only": name_only,
        "missing": missing,
        "covered_weight": covered_weight,
        "total_weight": total_weight,
        "fraction": fraction,
        "findings": findings,
    }


def validate_seeding_source(source):
    """A multipactor test only counts when the electron population is seeded."""
    if not isinstance(source, str):
        raise ValueError("seeding source must be a string, got %r" % (source,))
    key = source.strip().lower()
    if key not in SEEDING_SOURCES:
        raise ValueError(
            "unrecognized electron seeding source %r; known: %s"
            % (source, ", ".join(SEEDING_SOURCES))
        )
    return key


def validate_detection_methods(methods):
    """At least two distinct recognized detection methods, ideally mixed."""
    if not isinstance(methods, (list, tuple)):
        raise ValueError("detection methods must be a list")
    resolved = []
    for item in methods:
        if not isinstance(item, str):
            raise ValueError("detection method must be a string, got %r" % (item,))
        key = item.strip().lower()
        if key not in DETECTION_METHODS:
            raise ValueError(
                "unrecognized detection method %r; known: %s"
                % (item, ", ".join(sorted(DETECTION_METHODS)))
            )
        if key not in resolved:
            resolved.append(key)
    findings = []
    if len(resolved) < 2:
        findings.append(
            "only %d distinct detection method(s) declared; a single detector "
            "cannot separate a discharge from an instrument artefact" % len(resolved)
        )
    scopes = {DETECTION_METHODS[key] for key in resolved}
    if len(resolved) >= 2 and len(scopes) < 2:
        findings.append(
            "both detection methods are %s; pair a global method with a local one"
            % scopes.pop()
        )
    return {"methods": resolved, "scopes": sorted(scopes), "findings": findings}


def _require_text(fields, name, findings):
    value = fields.get(name)
    if value is None:
        return False
    if not isinstance(value, str) or not value.strip():
        raise ValueError("field %r must be a non-empty string" % name)
    return True


def _require_number(fields, name):
    value = fields.get(name)
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("field %r must be numeric, got %r" % (name, value))
    if math.isnan(float(value)) or math.isinf(float(value)):
        raise ValueError("field %r must be a finite number" % name)
    return float(value)


def audit_item_entry(item):
    """Audit one multipactor-critical item against its method's extra fields."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("item has no identifier")
    identifier = identifier.strip()
    method = canonical_method(item.get("method"))
    fields = item.get("fields", {})
    if not isinstance(fields, dict):
        raise ValueError("item %s fields must be a mapping" % identifier)
    findings = []
    missing = []
    for name in required_fields_for_method(method):
        if name not in fields or fields.get(name) is None:
            missing.append(name)
            findings.append("item %s: %s missing for a %s route" % (identifier, name, method))
    if method == "multipactor-test":
        if "electron-seeding-source" not in missing:
            validate_seeding_source(fields["electron-seeding-source"])
        if "detection-methods" not in missing:
            detection = validate_detection_methods(fields["detection-methods"])
            findings.extend("item %s: %s" % (identifier, f) for f in detection["findings"])
        dwell = _require_number(fields, "dwell-duration-minutes")
        if dwell is not None:
            if dwell < 0:
                raise ValueError("item %s: dwell duration must not be negative" % identifier)
            if dwell == 0:
                findings.append("item %s: a zero dwell demonstrates nothing" % identifier)
        pressure = _require_number(fields, "vacuum-pressure-mbar")
        if pressure is not None:
            if pressure <= 0:
                raise ValueError("item %s: vacuum pressure must be positive" % identifier)
            if pressure > VACUUM_CEILING_MBAR:
                findings.append(
                    "item %s: %.2e mbar sits above the vacuum ceiling; that regime "
                    "demonstrates gas breakdown, not multipactor" % (identifier, pressure)
                )
        _require_number(fields, "test-power-level-dbm")
    elif method == "multipactor-analysis":
        margin = _require_number(fields, "analysis-margin-db")
        if margin is not None and margin <= 0:
            findings.append(
                "item %s: a non-positive analysis margin closes nothing" % identifier
            )
        for name in ("susceptibility-model", "secondary-electron-yield-source",
                     "gap-geometry-source"):
            _require_text(fields, name, findings)
    else:
        for name in required_fields_for_method(method):
            _require_text(fields, name, findings)
    return {
        "id": identifier,
        "method": method,
        "missing_fields": missing,
        "findings": findings,
        "compliant": not findings,
    }


def assess_plan_content(plan, minimum_completeness=DEFAULT_MIN_COMPLETENESS):
    """Plan-level verdict on the clause 4.2.2 additions."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    if not isinstance(minimum_completeness, (int, float)) or isinstance(
        minimum_completeness, bool
    ):
        raise ValueError("minimum completeness must be numeric")
    if not 0.0 <= float(minimum_completeness) <= 1.0:
        raise ValueError("minimum completeness must lie in [0, 1]")
    coverage = audit_content_coverage(plan.get("content_entries", ()))
    items = plan.get("items", ())
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list of records")
    audited = [audit_item_entry(item) for item in items]
    identifiers = [entry["id"] for entry in audited]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate multipactor-critical item identifier")
    findings = list(coverage["findings"])
    for entry in audited:
        findings.extend(entry["findings"])
    if not audited:
        findings.append(
            "no multipactor-critical item is carried by the plan; the addition "
            "required by clause 4.2.2 is an item list, not an empty heading"
        )
    complete = meets_threshold(coverage["fraction"], minimum_completeness)
    return {
        "coverage": coverage,
        "items": audited,
        "item_count": len(audited),
        "completeness": coverage["fraction"],
        "minimum_completeness": float(minimum_completeness),
        "meets_completeness": complete,
        "findings": findings,
        "compliant": complete and not findings,
    }
