"""Scope decision for the threaded-fastener procurement standard.

Anchor: ECSS-Q-ST-70-46 applicability clause (which threaded fasteners
procured for space hardware the manufacturing and procurement requirements
apply to, and which items fall outside them). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide on the item kind first. A bolt, screw, stud or threaded insert is
   the subject of the standard; a nut or washer is in only as a member of a
   procured fastener set; a rivet, plain pin or clamp has no thread and is
   never in, whatever it is used for.
2. Decide on the application next. Flight hardware is in; ground support
   equipment is in only where the item carries a load path that flight
   hardware depends on, and out otherwise.
3. Parse the thread designation, because the size decides whether the full
   requirement set or a reduced one applies: below the small-size threshold
   the destructive testing a full programme asks for consumes the part.
4. Derive the clause groups that apply from the verdict and the criticality,
   so a non-critical in-scope item is not handed a qualification programme
   it does not owe.
5. Return the verdict, the reason, the parsed thread and the ordered clause
   groups as one record.
"""

import math

__all__ = [
    "PRIMARY_KINDS",
    "SET_MEMBER_KINDS",
    "EXCLUDED_KINDS",
    "APPLICATIONS",
    "CRITICALITIES",
    "SMALL_SIZE_THRESHOLD_MM",
    "COARSE_PITCH_MM",
    "ALL_CLAUSE_GROUPS",
    "item_kinds",
    "coarse_pitch_for",
    "parse_thread_designation",
    "kind_verdict",
    "application_verdict",
    "clause_groups",
    "assess_scope",
]

# Items the standard is written about.
PRIMARY_KINDS = ("bolt", "screw", "stud", "threaded-insert")

# Items in scope only when procured as part of a fastener set.
SET_MEMBER_KINDS = ("nut", "washer", "locking-element")

# Items with no thread; outside the standard whatever they fasten.
EXCLUDED_KINDS = ("rivet", "plain-pin", "clamp", "clip", "bonded-stud", "weld-stud")

APPLICATIONS = ("flight", "ground-support", "test-rig")

CRITICALITIES = ("critical", "major", "minor")

# Below this nominal diameter the destructive part of a full test programme
# consumes the part, so a reduced clause set applies.
SMALL_SIZE_THRESHOLD_MM = 2.5

# ISO metric coarse pitches for the sizes a space fastener schedule uses.
COARSE_PITCH_MM = {
    1.6: 0.35,
    2.0: 0.4,
    2.5: 0.45,
    3.0: 0.5,
    4.0: 0.7,
    5.0: 0.8,
    6.0: 1.0,
    8.0: 1.25,
    10.0: 1.5,
    12.0: 1.75,
    14.0: 2.0,
    16.0: 2.0,
    20.0: 2.5,
    24.0: 3.0,
}

# Clause groups in the order the standard works through them.
ALL_CLAUSE_GROUPS = (
    "specifications",
    "materials",
    "manufacturing",
    "procurement",
    "testing",
    "inspection",
    "acceptance",
    "application",
    "storage",
    "records",
)

# Groups a reduced set drops, because they cannot be run on the part.
_REDUCED_DROPS = ("testing",)

# Groups only a critical item owes in full.
_CRITICAL_ONLY = ("testing",)


def item_kinds():
    """Return the item kinds this scope decision recognises, grouped by verdict."""
    return {
        "primary": tuple(PRIMARY_KINDS),
        "set_member": tuple(SET_MEMBER_KINDS),
        "excluded": tuple(EXCLUDED_KINDS),
    }


def _clean_token(value, label):
    """Return a non-empty lowercase token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def coarse_pitch_for(diameter_mm):
    """Return the ISO metric coarse pitch tabulated for a nominal diameter."""
    if not isinstance(diameter_mm, (int, float)) or isinstance(diameter_mm, bool):
        raise ValueError("diameter_mm must be a real number, got %r" % (diameter_mm,))
    diameter = float(diameter_mm)
    if not math.isfinite(diameter) or diameter <= 0.0:
        raise ValueError("diameter_mm must be positive and finite, got %r" % (diameter_mm,))
    for tabulated, pitch in sorted(COARSE_PITCH_MM.items()):
        if math.isclose(diameter, tabulated, rel_tol=0.0, abs_tol=1e-9):
            return pitch
    raise ValueError(
        "no coarse pitch is tabulated for M%g; state the pitch explicitly" % diameter
    )


def parse_thread_designation(designation):
    """Return the nominal diameter and pitch of a metric thread designation.

    Accepts 'M6' (coarse pitch taken from the table) and 'M6x0.75' (fine
    pitch stated). The separator may be 'x' or '*'.
    """
    token = _clean_token(designation, "designation").replace(" ", "")
    if not token.startswith("m"):
        raise ValueError(
            "thread designation %r is not a metric designation; it must start with M"
            % (designation,)
        )
    body = token[1:].replace("*", "x")
    if not body:
        raise ValueError("thread designation %r carries no size" % (designation,))
    parts = body.split("x")
    if len(parts) > 2:
        raise ValueError("thread designation %r has more than one pitch" % (designation,))
    try:
        diameter = float(parts[0])
    except ValueError:
        raise ValueError(
            "thread designation %r has a non-numeric diameter" % (designation,)
        )
    if not math.isfinite(diameter) or diameter <= 0.0:
        raise ValueError("thread diameter in %r must be positive" % (designation,))
    if len(parts) == 1:
        pitch = coarse_pitch_for(diameter)
        stated = False
    else:
        try:
            pitch = float(parts[1])
        except ValueError:
            raise ValueError("thread designation %r has a non-numeric pitch" % (designation,))
        if not math.isfinite(pitch) or pitch <= 0.0:
            raise ValueError("thread pitch in %r must be positive" % (designation,))
        if pitch >= diameter:
            raise ValueError(
                "pitch %g mm is not smaller than the diameter %g mm in %r"
                % (pitch, diameter, designation)
            )
        stated = True
    return {
        "designation": "M%g" % diameter if not stated else "M%gx%g" % (diameter, pitch),
        "nominal_diameter_mm": diameter,
        "pitch_mm": pitch,
        "pitch_stated": stated,
        "small_size": diameter < SMALL_SIZE_THRESHOLD_MM,
    }


def kind_verdict(kind, procured_as_set=False):
    """Return the scope verdict the item kind alone produces."""
    token = _clean_token(kind, "kind")
    if not isinstance(procured_as_set, bool):
        raise ValueError("procured_as_set must be a boolean")
    if token in PRIMARY_KINDS:
        return ("in-scope", "%s is a threaded fastener the standard is written about" % token)
    if token in SET_MEMBER_KINDS:
        if procured_as_set:
            return (
                "in-scope-as-set-member",
                "%s is in scope because it is procured as part of a fastener set" % token,
            )
        return (
            "out-of-scope",
            "%s is in scope only when procured as part of a fastener set" % token,
        )
    if token in EXCLUDED_KINDS:
        return ("out-of-scope", "%s carries no thread the standard can control" % token)
    raise ValueError(
        "unknown item kind %r; recognised kinds are %s"
        % (kind, ", ".join(sorted(PRIMARY_KINDS + SET_MEMBER_KINDS + EXCLUDED_KINDS)))
    )


def application_verdict(application, carries_flight_load=False):
    """Return the scope verdict the application produces."""
    token = _clean_token(application, "application")
    if token not in APPLICATIONS:
        raise ValueError(
            "unknown application %r; recognised applications are %s"
            % (application, ", ".join(APPLICATIONS))
        )
    if not isinstance(carries_flight_load, bool):
        raise ValueError("carries_flight_load must be a boolean")
    if token == "flight":
        return ("in-scope", "the item is installed on flight hardware")
    if carries_flight_load:
        return (
            "in-scope",
            "the item is %s but sits in a load path flight hardware depends on" % token,
        )
    return ("out-of-scope", "%s hardware carrying no flight load path" % token)


def clause_groups(verdict, criticality, small_size=False):
    """Return the ordered clause groups an in-scope item owes."""
    if verdict not in ("in-scope", "in-scope-as-set-member"):
        return ()
    token = _clean_token(criticality, "criticality")
    if token not in CRITICALITIES:
        raise ValueError(
            "unknown criticality %r; recognised values are %s"
            % (criticality, ", ".join(CRITICALITIES))
        )
    if not isinstance(small_size, bool):
        raise ValueError("small_size must be a boolean")
    groups = []
    for group in ALL_CLAUSE_GROUPS:
        if small_size and group in _REDUCED_DROPS:
            continue
        if token == "minor" and group in _CRITICAL_ONLY:
            continue
        groups.append(group)
    return tuple(groups)


def assess_scope(item):
    """Run the full applicability decision for one procurement item.

    item keys: kind, application, criticality, optional thread_designation,
    procured_as_set and carries_flight_load.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("kind", "application", "criticality"):
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)
    kind_result, kind_reason = kind_verdict(
        item["kind"], item.get("procured_as_set", False)
    )
    application_result, application_reason = application_verdict(
        item["application"], item.get("carries_flight_load", False)
    )
    thread = None
    if "thread_designation" in item and item["thread_designation"] is not None:
        thread = parse_thread_designation(item["thread_designation"])
    reasons = [kind_reason, application_reason]
    if kind_result == "out-of-scope" or application_result == "out-of-scope":
        verdict = "out-of-scope"
    else:
        verdict = kind_result
    small = bool(thread["small_size"]) if thread else False
    groups = clause_groups(verdict, item["criticality"], small)
    findings = []
    if verdict == "out-of-scope":
        findings.append(
            "item is outside ECSS-Q-ST-70-46: %s"
            % (kind_reason if kind_result == "out-of-scope" else application_reason)
        )
    if verdict != "out-of-scope" and thread is None:
        findings.append(
            "no thread designation was given, so the small-size reduced set could not be judged"
        )
    if small and verdict != "out-of-scope":
        findings.append(
            "nominal diameter is below %g mm; the destructive test group is dropped and "
            "acceptance rests on process control and inspection"
            % SMALL_SIZE_THRESHOLD_MM
        )
    return {
        "verdict": verdict,
        "kind_verdict": kind_result,
        "application_verdict": application_result,
        "reasons": reasons,
        "thread": thread,
        "criticality": _clean_token(item["criticality"], "criticality"),
        "clause_groups": list(groups),
        "findings": findings,
        "in_scope": verdict != "out-of-scope",
    }
