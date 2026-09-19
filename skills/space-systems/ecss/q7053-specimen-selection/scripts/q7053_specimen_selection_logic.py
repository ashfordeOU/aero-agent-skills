"""Representative specimen selection for a sterilization compatibility campaign.

Anchor: the test-item clause of ECSS-Q-ST-70-53, where the materials and
hardware specimens that stand for the flight item are chosen. Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the flight thickness range and every candidate specimen.
2. Group the candidate pool by material family, keeping the unexposed
   controls apart from the specimens that will be exposed.
3. Set aside specimens whose thickness lies outside the flight range.
4. Select the worst-case exposed specimen per family: least capability
   against the dominant stressor of the process, ties broken on identifier.
5. Fill each family up to the minimum replicate count, least capable first,
   and attach one representative control.
6. Report coverage findings: an uncovered family, a family short of
   replicates, a family without a control, and a worst-case specimen sitting
   at or below the applied stressor.
"""

import math

__all__ = [
    "THICKNESS_TOLERANCE_MM",
    "CAPABILITY_TOLERANCE",
    "DEFAULT_MIN_REPLICATES",
    "validate_thickness_range",
    "validate_specimen",
    "validate_pool",
    "is_representative",
    "group_by_family",
    "worst_case_specimen",
    "select_family_set",
    "assess_specimen_set",
]

# A thickness at either end of the flight range is inside it; absorb the
# representation error of the comparison rather than moving the range.
THICKNESS_TOLERANCE_MM = 1e-9
# Same allowance for a capability sitting exactly on the applied stressor.
CAPABILITY_TOLERANCE = 1e-9

# Replicates below this count cannot separate a material effect from a
# preparation effect.
DEFAULT_MIN_REPLICATES = 3


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_thickness_range(flight_min_mm, flight_max_mm):
    """Return the validated (min, max) flight thickness range in millimetres."""
    low = _positive(flight_min_mm, "flight_min_mm")
    high = _positive(flight_max_mm, "flight_max_mm")
    if low > high:
        raise ValueError("flight_min_mm %g exceeds flight_max_mm %g" % (low, high))
    return (low, high)


def validate_specimen(specimen):
    """Return a validated specimen record.

    Keys: id, family, thickness_mm, capability; optional is_control, lot.
    """
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping")
    for key in ("id", "family", "thickness_mm", "capability"):
        if key not in specimen:
            raise ValueError("specimen missing required key '%s'" % key)
    identifier = specimen["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("specimen id must be a non-empty string")
    family = specimen["family"]
    if not isinstance(family, str) or not family.strip():
        raise ValueError("specimen %s family must be a non-empty string" % identifier)
    is_control = specimen.get("is_control", False)
    if not isinstance(is_control, bool):
        raise ValueError("specimen %s is_control must be a boolean" % identifier)
    lot = specimen.get("lot")
    if lot is not None and (not isinstance(lot, str) or not lot.strip()):
        raise ValueError("specimen %s lot must be a non-empty string when given" % identifier)
    return {
        "id": identifier.strip(),
        "family": family.strip().lower(),
        "thickness_mm": _positive(
            specimen["thickness_mm"], "specimen %s thickness_mm" % identifier
        ),
        "capability": _positive(
            specimen["capability"], "specimen %s capability" % identifier
        ),
        "is_control": is_control,
        "lot": lot.strip() if isinstance(lot, str) else None,
    }


def validate_pool(pool):
    """Return the validated candidate pool, rejecting a duplicated identifier."""
    if not isinstance(pool, (list, tuple)) or not pool:
        raise ValueError("pool must be a non-empty sequence of specimen records")
    records = [validate_specimen(item) for item in pool]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("duplicated specimen id %r in the pool" % record["id"])
        seen.add(record["id"])
    return records


def is_representative(thickness_mm, flight_range, tolerance=THICKNESS_TOLERANCE_MM):
    """Return whether a thickness lies inside the flight range."""
    low, high = flight_range
    value = _positive(thickness_mm, "thickness_mm")
    tol = float(tolerance)
    return (value >= low - tol) and (value <= high + tol)


def group_by_family(records):
    """Return {family: {'exposed': [...], 'controls': [...]}} for the pool."""
    grouped = {}
    for record in records:
        bucket = grouped.setdefault(record["family"], {"exposed": [], "controls": []})
        if record["is_control"]:
            bucket["controls"].append(record)
        else:
            bucket["exposed"].append(record)
    return grouped


def worst_case_specimen(candidates):
    """Return the least capable candidate; the identifier breaks a tie."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("candidates must be a non-empty sequence")
    worst = None
    for record in candidates:
        if not isinstance(record, dict) or "capability" not in record or "id" not in record:
            raise ValueError("each candidate must carry 'capability' and 'id'")
        if worst is None:
            worst = record
            continue
        if math.isclose(record["capability"], worst["capability"], rel_tol=1e-12, abs_tol=0.0):
            if record["id"] < worst["id"]:
                worst = record
        elif record["capability"] < worst["capability"]:
            worst = record
    return worst


def select_family_set(exposed, controls, min_replicates=DEFAULT_MIN_REPLICATES):
    """Return the selected exposed specimens and the control for one family."""
    if not isinstance(min_replicates, int) or isinstance(min_replicates, bool):
        raise ValueError("min_replicates must be an integer")
    if min_replicates < 1:
        raise ValueError("min_replicates must be at least 1, got %d" % min_replicates)
    ordered = sorted(exposed, key=lambda record: (record["capability"], record["id"]))
    selected = ordered[:min_replicates]
    control = None
    if controls:
        control = sorted(controls, key=lambda record: record["id"])[0]
    return {"exposed": selected, "control": control}


def assess_specimen_set(spec):
    """Build the campaign specimen set and report what it does not cover.

    spec keys: families (required by the bill of materials), pool,
    flight_min_mm, flight_max_mm, applied_stressor; optional min_replicates.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("families", "pool", "flight_min_mm", "flight_max_mm", "applied_stressor"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    families = spec["families"]
    if not isinstance(families, (list, tuple)) or not families:
        raise ValueError("families must be a non-empty sequence")
    required = []
    for family in families:
        if not isinstance(family, str) or not family.strip():
            raise ValueError("every required family must be a non-empty string")
        required.append(family.strip().lower())
    flight_range = validate_thickness_range(spec["flight_min_mm"], spec["flight_max_mm"])
    applied = _positive(spec["applied_stressor"], "applied_stressor")
    min_replicates = spec.get("min_replicates", DEFAULT_MIN_REPLICATES)
    records = validate_pool(spec["pool"])
    representative = []
    set_aside = []
    for record in records:
        if is_representative(record["thickness_mm"], flight_range):
            representative.append(record)
        else:
            set_aside.append(record)
    grouped = group_by_family(representative)
    selection = {}
    findings = []
    for family in required:
        bucket = grouped.get(family, {"exposed": [], "controls": []})
        if not bucket["exposed"]:
            selection[family] = {"exposed": [], "control": None, "worst_case": None}
            findings.append("material family %s has no representative exposed specimen" % family)
            continue
        chosen = select_family_set(bucket["exposed"], bucket["controls"], min_replicates)
        worst = worst_case_specimen(bucket["exposed"])
        selection[family] = {
            "exposed": chosen["exposed"],
            "control": chosen["control"],
            "worst_case": worst,
        }
        if len(chosen["exposed"]) < min_replicates:
            findings.append(
                "material family %s carries %d representative exposed specimens against "
                "the %d replicates required" % (family, len(chosen["exposed"]), min_replicates)
            )
        if chosen["control"] is None:
            findings.append("material family %s has no unexposed control" % family)
        elif worst["lot"] is not None and chosen["control"]["lot"] != worst["lot"]:
            findings.append(
                "material family %s control %s is not from the worst-case lot %s"
                % (family, chosen["control"]["id"], worst["lot"])
            )
        if worst["capability"] <= applied + CAPABILITY_TOLERANCE:
            findings.append(
                "worst-case specimen %s of family %s sits at or below the applied "
                "stressor %g" % (worst["id"], family, applied)
            )
    for record in set_aside:
        findings.append(
            "specimen %s thickness %g mm is outside the flight range [%g, %g] and is set aside"
            % (record["id"], record["thickness_mm"], flight_range[0], flight_range[1])
        )
    covered = [family for family in required if selection[family]["exposed"]]
    return {
        "flight_range_mm": flight_range,
        "applied_stressor": applied,
        "min_replicates": min_replicates,
        "selection": selection,
        "set_aside": set_aside,
        "covered_families": covered,
        "complete": len(covered) == len(required) and not findings,
        "findings": findings,
    }
