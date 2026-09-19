"""Verification planning for the cleanliness requirements of a space product.

Anchor: ECSS-Q-ST-70-01C, verification clause -- deciding, requirement by
requirement, which measurement method substantiates it and at which programme
point the measurement is taken. Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every cleanliness requirement: the contamination kind it controls
   (particulate or molecular), its numeric limit, the accessible surface area
   it applies to, the programme phase it has to hold over and whether the
   surface is criticality-driven.
2. Validate the method catalogue available to the programme. A method carries
   a detection floor in the units of the requirement it can serve, a minimum
   sample area, a directness (a method reading the hardware surface itself
   versus one reading a witness surface standing in for it) and whether it
   yields a number at all or only a qualitative observation.
3. Match methods to requirements. A method is capable only when its detection
   floor sits below the limit by the declared margin factor, its minimum
   sample area fits inside the accessible area, and its kind matches.
4. Place verification points: one after the last cleaning operation of every
   declared milestone the requirement spans, and one at the final milestone
   the surface stays accessible at.
5. Report the plan with per-requirement coverage and an explicit finding list:
   uncovered requirements, requirements carried only by a qualitative look,
   critical requirements carried only by an indirect witness surface, and
   requirements whose last verification point is not the last accessible
   milestone.
"""

import math

__all__ = [
    "DEFAULT_MARGIN_FACTOR",
    "FLOOR_TOLERANCE",
    "KINDS",
    "validate_requirement",
    "validate_method",
    "method_matches_kind",
    "method_is_capable",
    "capable_methods",
    "rank_methods",
    "verification_points",
    "plan_requirement",
    "build_verification_plan",
    "plan_coverage_fraction",
]

# Contamination kinds a cleanliness requirement can control.
KINDS = ("particulate", "molecular")

# A method whose detection floor sits at the limit cannot discriminate a pass
# from a fail, so a capable method has to reach below the limit by this factor.
DEFAULT_MARGIN_FACTOR = 2.0

# Floor-versus-limit is a ratio of measured quantities; absorb representation
# error at the boundary instead of relaxing the margin factor.
FLOOR_TOLERANCE = 1e-9


def _positive(label, value):
    """Return value as a positive finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _text(label, value):
    """Return value as a non-empty stripped string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _milestones(label, value):
    """Return an ordered milestone list with no repeats."""
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("%s must be a non-empty sequence of milestone names" % label)
    names = []
    for index, item in enumerate(value):
        name = _text("%s[%d]" % (label, index), item)
        if name in names:
            raise ValueError("%s repeats milestone %r" % (label, name))
        names.append(name)
    return names


def validate_requirement(requirement):
    """Return a normalised cleanliness requirement record."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    for key in ("id", "kind", "limit", "area_m2", "milestones"):
        if key not in requirement:
            raise ValueError("requirement missing required key '%s'" % key)
    kind = _text("requirement['kind']", requirement["kind"]).lower()
    if kind not in KINDS:
        raise ValueError("requirement kind must be one of %s, got %r" % (KINDS, kind))
    final = requirement.get("final_accessible_milestone")
    milestones = _milestones("requirement['milestones']", requirement["milestones"])
    if final is None:
        final = milestones[-1]
    else:
        final = _text("requirement['final_accessible_milestone']", final)
        if final not in milestones:
            raise ValueError(
                "final accessible milestone %r is not in the milestone list" % final
            )
    return {
        "id": _text("requirement['id']", requirement["id"]),
        "kind": kind,
        "limit": _positive("requirement['limit']", requirement["limit"]),
        "area_m2": _positive("requirement['area_m2']", requirement["area_m2"]),
        "milestones": milestones,
        "final_accessible_milestone": final,
        "critical": bool(requirement.get("critical", False)),
    }


def validate_method(method):
    """Return a normalised verification-method record."""
    if not isinstance(method, dict):
        raise ValueError("method must be a mapping")
    for key in ("name", "kinds", "detection_floor", "min_sample_area_m2"):
        if key not in method:
            raise ValueError("method missing required key '%s'" % key)
    kinds_value = method["kinds"]
    if isinstance(kinds_value, str):
        kinds_value = [kinds_value]
    if not isinstance(kinds_value, (list, tuple)) or not kinds_value:
        raise ValueError("method['kinds'] must be a non-empty sequence")
    kinds = []
    for index, item in enumerate(kinds_value):
        kind = _text("method['kinds'][%d]" % index, item).lower()
        if kind not in KINDS:
            raise ValueError("method kind must be one of %s, got %r" % (KINDS, kind))
        if kind not in kinds:
            kinds.append(kind)
    quantitative = bool(method.get("quantitative", True))
    floor = method["detection_floor"]
    if quantitative:
        floor = _positive("method['detection_floor']", floor)
    else:
        # A qualitative observation reports no number; its floor is meaningless
        # and is carried as infinity so it can never satisfy a numeric limit.
        floor = math.inf
    return {
        "name": _text("method['name']", method["name"]),
        "kinds": kinds,
        "detection_floor": floor,
        "min_sample_area_m2": _positive(
            "method['min_sample_area_m2']", method["min_sample_area_m2"]
        ),
        "quantitative": quantitative,
        "direct": bool(method.get("direct", True)),
    }


def method_matches_kind(method, requirement):
    """Return True when the method measures the contamination kind required."""
    return requirement["kind"] in method["kinds"]


def method_is_capable(method, requirement, margin_factor=DEFAULT_MARGIN_FACTOR):
    """Return True when the method can substantiate the requirement numerically."""
    margin = _positive("margin_factor", margin_factor)
    if margin < 1.0:
        raise ValueError("margin_factor must be at least 1.0, got %r" % (margin_factor,))
    if not method_matches_kind(method, requirement):
        return False
    if not method["quantitative"]:
        return False
    if method["min_sample_area_m2"] > requirement["area_m2"] * (1.0 + FLOOR_TOLERANCE):
        return False
    needed = requirement["limit"] / margin
    return method["detection_floor"] <= needed * (1.0 + FLOOR_TOLERANCE)


def capable_methods(methods, requirement, margin_factor=DEFAULT_MARGIN_FACTOR):
    """Return the methods able to substantiate the requirement."""
    if not isinstance(methods, (list, tuple)) or not methods:
        raise ValueError("methods must be a non-empty sequence")
    records = [validate_method(item) for item in methods]
    return [item for item in records if method_is_capable(item, requirement, margin_factor)]


def rank_methods(methods, requirement, margin_factor=DEFAULT_MARGIN_FACTOR):
    """Return capable methods best first: direct before indirect, then lowest floor."""
    candidates = capable_methods(methods, requirement, margin_factor)
    return sorted(
        candidates,
        key=lambda item: (0 if item["direct"] else 1, item["detection_floor"], item["name"]),
    )


def verification_points(requirement):
    """Return the milestone names a verification measurement is placed at."""
    milestones = requirement["milestones"]
    final = requirement["final_accessible_milestone"]
    points = list(milestones[: milestones.index(final) + 1])
    return points


def plan_requirement(requirement, methods, margin_factor=DEFAULT_MARGIN_FACTOR):
    """Return the plan entry for one cleanliness requirement."""
    record = validate_requirement(requirement)
    ranked = rank_methods(methods, record, margin_factor)
    all_methods = [validate_method(item) for item in methods]
    of_kind = [item for item in all_methods if method_matches_kind(item, record)]
    findings = []
    selected = ranked[0] if ranked else None
    if selected is None:
        if not of_kind:
            findings.append(
                "requirement %s has no method measuring %s contamination"
                % (record["id"], record["kind"])
            )
        elif all(not item["quantitative"] for item in of_kind):
            findings.append(
                "requirement %s is carried only by a qualitative observation and "
                "cannot substantiate a numeric limit" % record["id"]
            )
        elif all(
            item["min_sample_area_m2"] > record["area_m2"] * (1.0 + FLOOR_TOLERANCE)
            for item in of_kind
            if item["quantitative"]
        ):
            findings.append(
                "requirement %s has no method whose minimum sample area fits the "
                "%.4g m2 accessible surface" % (record["id"], record["area_m2"])
            )
        else:
            findings.append(
                "requirement %s has no method reaching below its limit by the "
                "margin factor %.3g" % (record["id"], float(margin_factor))
            )
    elif record["critical"] and all(not item["direct"] for item in ranked):
        findings.append(
            "critical requirement %s is carried only by an indirect witness "
            "surface; add a direct measurement on the hardware" % record["id"]
        )
    points = verification_points(record)
    if points[-1] != record["final_accessible_milestone"]:
        findings.append(
            "requirement %s has no verification point at its last accessible "
            "milestone %s" % (record["id"], record["final_accessible_milestone"])
        )
    return {
        "requirement_id": record["id"],
        "kind": record["kind"],
        "limit": record["limit"],
        "selected_method": selected["name"] if selected else None,
        "alternate_methods": [item["name"] for item in ranked[1:]],
        "verification_points": points,
        "covered": selected is not None and not findings,
        "findings": findings,
    }


def build_verification_plan(spec):
    """Return the cleanliness verification plan for a set of requirements.

    spec keys: requirements (sequence of requirement mappings), methods
    (sequence of method mappings), optional margin_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("requirements", "methods"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    requirements = spec["requirements"]
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("spec['requirements'] must be a non-empty sequence")
    margin = spec.get("margin_factor", DEFAULT_MARGIN_FACTOR)
    entries = [plan_requirement(item, spec["methods"], margin) for item in requirements]
    seen = []
    for entry in entries:
        if entry["requirement_id"] in seen:
            raise ValueError("duplicate requirement id %r" % entry["requirement_id"])
        seen.append(entry["requirement_id"])
    findings = []
    for entry in entries:
        findings.extend(entry["findings"])
    return {
        "entries": entries,
        "coverage_fraction": plan_coverage_fraction(entries),
        "uncovered": [item["requirement_id"] for item in entries if not item["covered"]],
        "findings": findings,
        "complete": not findings,
    }


def plan_coverage_fraction(entries):
    """Return the fraction of plan entries carrying a capable method and no finding."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence")
    covered = 0
    for entry in entries:
        if not isinstance(entry, dict) or "covered" not in entry:
            raise ValueError("each entry must be a mapping carrying 'covered'")
        if entry["covered"]:
            covered += 1
    return covered / float(len(entries))
