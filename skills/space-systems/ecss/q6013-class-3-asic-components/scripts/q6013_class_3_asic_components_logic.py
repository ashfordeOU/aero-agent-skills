"""Delegated ASIC development assurance at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.6.2 (the development assurance rules that
apply to application-specific devices used at the lowest assurance class).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the offered device and the mission envelope it has to cover.
2. Close the delegated route where the declared device kind is not one this
   class delegates.
3. Credit each development assurance objective by the strength of the evidence
   offered against it, in exact integer basis points.
4. Refuse all credit for a non-delegable objective resting on evidence weaker
   than the declared minimum strength, and re-open it as an activity.
5. Re-open one named activity per rated envelope axis the mission overruns.
6. Compare credited assurance with the floor by integer cross-multiplication,
   equality counting as met.
"""

__all__ = [
    "DELEGABLE_DEVICE_KINDS",
    "DEVICE_KINDS",
    "EVIDENCE_STRENGTHS",
    "DEFAULT_OBJECTIVES",
    "DEFAULT_ASIC_POLICY",
    "DELEGATED_ASSURANCE_ACCEPTED",
    "DELEGATION_ROUTE_CLOSED",
    "MANDATORY_OBJECTIVE_UNEVIDENCED",
    "RATED_ENVELOPE_SHORTFALL",
    "ASSURANCE_BELOW_FLOOR",
    "validate_asic_policy",
    "validate_objectives",
    "evidence_credit_percent",
    "validate_device",
    "validate_mission_envelope",
    "route_is_delegable",
    "credit_objective",
    "credited_basis_points",
    "envelope_shortfalls",
    "assurance_meets_floor",
    "assess_delegated_asic_assurance",
]

# Device kinds this clause recognises, and the subset whose development
# evidence the lowest assurance class is willing to take on delegation.
DEVICE_KINDS = (
    "catalogue-standard-product",
    "structured-array",
    "gate-array",
    "standard-cell",
    "full-custom",
)
DELEGABLE_DEVICE_KINDS = ("catalogue-standard-product", "structured-array")

# What each strength of evidence is worth, as an integer percentage. Ranks order
# the strengths so a minimum strength can be stated once and compared.
EVIDENCE_STRENGTHS = {
    "independent-audit": {"rank": 3, "credit_percent": 100},
    "third-party-report": {"rank": 2, "credit_percent": 80},
    "supplier-declaration": {"rank": 1, "credit_percent": 50},
    "none": {"rank": 0, "credit_percent": 0},
}

# The development assurance objectives this class weighs, and whether the class
# lets the supplier's own word close them.
DEFAULT_OBJECTIVES = {
    "functional-verification-coverage": {"weight": 25, "non_delegable": True},
    "test-vector-fault-coverage": {"weight": 20, "non_delegable": True},
    "design-rule-compliance": {"weight": 20, "non_delegable": False},
    "technology-and-radiation-data": {"weight": 15, "non_delegable": False},
    "design-review-records": {"weight": 10, "non_delegable": False},
    "configuration-and-change-control": {"weight": 10, "non_delegable": False},
}

DELEGATED_ASSURANCE_ACCEPTED = "delegated-assurance-accepted"
DELEGATION_ROUTE_CLOSED = "delegation-route-closed"
MANDATORY_OBJECTIVE_UNEVIDENCED = "non-delegable-objective-unevidenced"
RATED_ENVELOPE_SHORTFALL = "rated-envelope-shortfall"
ASSURANCE_BELOW_FLOOR = "assurance-below-floor"

DEFAULT_ASIC_POLICY = {
    # Credited assurance the class asks for, as an integer percentage.
    "assurance_floor_percent": 70,
    # Weakest evidence that may close a non-delegable objective.
    "min_strength_non_delegable": "third-party-report",
    # Whether a rated envelope shortfall stops the delegated route.
    "envelope_shortfall_stops": True,
}


def validate_asic_policy(policy=None):
    """Return a complete assurance policy, defaults filled in."""
    if policy is None:
        return dict(DEFAULT_ASIC_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("asic policy must be a mapping")
    merged = dict(DEFAULT_ASIC_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_ASIC_POLICY:
            raise ValueError("unknown asic policy key %r" % (key,))
        merged[key] = value
    floor = merged["assurance_floor_percent"]
    if not isinstance(floor, int) or isinstance(floor, bool):
        raise ValueError("assurance_floor_percent must be an integer, got %r" % (floor,))
    if not 0 <= floor <= 100:
        raise ValueError("assurance_floor_percent must lie in 0..100")
    if merged["min_strength_non_delegable"] not in EVIDENCE_STRENGTHS:
        raise ValueError(
            "unknown min_strength_non_delegable %r"
            % (merged["min_strength_non_delegable"],)
        )
    if not isinstance(merged["envelope_shortfall_stops"], bool):
        raise ValueError("envelope_shortfall_stops must be a boolean")
    return merged


def validate_objectives(objectives=None):
    """Return a validated objective catalogue keyed by objective name."""
    if objectives is None:
        return {name: dict(entry) for name, entry in DEFAULT_OBJECTIVES.items()}
    if not isinstance(objectives, dict) or not objectives:
        raise ValueError("the objective catalogue must be a non-empty mapping")
    validated = {}
    for name, entry in objectives.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("each objective needs a non-empty name")
        if not isinstance(entry, dict):
            raise ValueError("objective %s must be described by a mapping" % (name,))
        weight = entry.get("weight")
        if not isinstance(weight, int) or isinstance(weight, bool):
            raise ValueError("objective %s needs an integer weight" % (name.strip(),))
        if weight <= 0:
            raise ValueError("objective %s needs a positive weight" % (name.strip(),))
        flag = entry.get("non_delegable", False)
        if not isinstance(flag, bool):
            raise ValueError("objective %s has a non-boolean non_delegable" % (name.strip(),))
        validated[name.strip()] = {"weight": weight, "non_delegable": flag}
    return validated


def evidence_credit_percent(strength):
    """Return the integer credit percentage a strength of evidence carries."""
    if not isinstance(strength, str) or not strength.strip():
        raise ValueError("evidence strength must be a non-empty token")
    name = strength.strip()
    if name not in EVIDENCE_STRENGTHS:
        raise ValueError("unknown evidence strength %r" % (strength,))
    return EVIDENCE_STRENGTHS[name]["credit_percent"]


def _strength_rank(strength):
    if not isinstance(strength, str) or strength.strip() not in EVIDENCE_STRENGTHS:
        raise ValueError("unknown evidence strength %r" % (strength,))
    return EVIDENCE_STRENGTHS[strength.strip()]["rank"]


def validate_device(device):
    """Return a normalised device declaration."""
    if not isinstance(device, dict):
        raise ValueError("the device declaration must be a mapping")
    reference = device.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("the device declaration needs a non-empty 'reference'")
    kind = device.get("kind")
    if not isinstance(kind, str) or kind.strip() not in DEVICE_KINDS:
        raise ValueError("unknown device kind %r" % (kind,))
    normalised = {"reference": reference.strip(), "kind": kind.strip()}
    for field in ("rated_temp_min_c", "rated_temp_max_c", "rated_total_dose_krad"):
        value = device.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(
                "device %s needs an integer '%s'; a rated envelope stated in prose "
                "cannot be compared" % (normalised["reference"], field)
            )
        normalised[field] = value
    if normalised["rated_temp_max_c"] <= normalised["rated_temp_min_c"]:
        raise ValueError(
            "device %s has a rated temperature range that does not open"
            % (normalised["reference"],)
        )
    if normalised["rated_total_dose_krad"] < 0:
        raise ValueError(
            "device %s has a negative rated total dose" % (normalised["reference"],)
        )
    return normalised


def validate_mission_envelope(envelope):
    """Return a normalised mission envelope."""
    if not isinstance(envelope, dict):
        raise ValueError("the mission envelope must be a mapping")
    normalised = {}
    for field in ("temp_min_c", "temp_max_c", "total_dose_krad"):
        value = envelope.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("the mission envelope needs an integer '%s'" % field)
        normalised[field] = value
    if normalised["temp_max_c"] <= normalised["temp_min_c"]:
        raise ValueError("the mission temperature range does not open")
    if normalised["total_dose_krad"] < 0:
        raise ValueError("the mission total dose must not be negative")
    return normalised


def route_is_delegable(kind):
    """Return whether this class takes a device kind's evidence on delegation."""
    if not isinstance(kind, str) or kind.strip() not in DEVICE_KINDS:
        raise ValueError("unknown device kind %r" % (kind,))
    return kind.strip() in DELEGABLE_DEVICE_KINDS


def credit_objective(name, entry, strength, min_strength):
    """Return the credit one objective earns, and why it earned that much."""
    if not isinstance(entry, dict) or "weight" not in entry:
        raise ValueError("objective %s is not a validated catalogue entry" % (name,))
    percent = evidence_credit_percent(strength)
    refused = False
    if entry["non_delegable"] and _strength_rank(strength) < _strength_rank(min_strength):
        percent = 0
        refused = True
    return {
        "objective": name,
        "weight": entry["weight"],
        "strength": strength.strip(),
        "credit_percent": percent,
        "basis_points": entry["weight"] * percent,
        "refused": refused,
        "non_delegable": entry["non_delegable"],
    }


def credited_basis_points(credits, objectives):
    """Return the credited and total basis points across the catalogue."""
    if not isinstance(credits, (list, tuple)) or not credits:
        raise ValueError("credits must be a non-empty sequence")
    if not isinstance(objectives, dict) or not objectives:
        raise ValueError("objectives must be a non-empty mapping")
    credited = sum(item["basis_points"] for item in credits)
    total = sum(entry["weight"] for entry in objectives.values()) * 100
    return {"credited": credited, "total": total}


def envelope_shortfalls(device, envelope):
    """Return one named activity per rated envelope axis the mission overruns."""
    rated = validate_device(device)
    mission = validate_mission_envelope(envelope)
    shortfalls = []
    if mission["temp_min_c"] < rated["rated_temp_min_c"]:
        shortfalls.append({
            "axis": "temperature-low-end",
            "activity": "cold-end-application-uprating",
            "rated": rated["rated_temp_min_c"],
            "required": mission["temp_min_c"],
        })
    if mission["temp_max_c"] > rated["rated_temp_max_c"]:
        shortfalls.append({
            "axis": "temperature-high-end",
            "activity": "hot-end-application-uprating",
            "rated": rated["rated_temp_max_c"],
            "required": mission["temp_max_c"],
        })
    if mission["total_dose_krad"] > rated["rated_total_dose_krad"]:
        shortfalls.append({
            "axis": "total-dose",
            "activity": "application-total-dose-testing",
            "rated": rated["rated_total_dose_krad"],
            "required": mission["total_dose_krad"],
        })
    return shortfalls


def assurance_meets_floor(credited, total, floor_percent):
    """Return whether credited/total reaches the floor, in integers only."""
    for name, value in (("credited", credited), ("total", total),
                        ("floor_percent", floor_percent)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (name, value))
    if total <= 0:
        raise ValueError("total must be positive")
    if credited < 0 or credited > total:
        raise ValueError("credited must lie between zero and the total")
    if not 0 <= floor_percent <= 100:
        raise ValueError("floor_percent must lie in 0..100")
    # Cross-multiplied: a device landing exactly on the floor is admitted, and
    # admitted identically on every machine.
    return credited * 100 >= floor_percent * total


def assess_delegated_asic_assurance(case):
    """Run the clause 6.6.2 assessment over an offered application-specific device.

    case keys: device (declaration), mission (envelope), evidence (mapping of
    objective name to evidence strength), optional objectives, optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("device", "mission", "evidence"):
        if key not in case:
            raise ValueError("case missing required key %r" % (key,))
    settings = validate_asic_policy(case.get("policy"))
    objectives = validate_objectives(case.get("objectives"))
    device = validate_device(case["device"])
    mission = validate_mission_envelope(case["mission"])

    evidence = case["evidence"]
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping of objective to strength")
    for name in evidence:
        if name not in objectives:
            raise ValueError("evidence offered against unknown objective %r" % (name,))

    findings = []
    delegable = route_is_delegable(device["kind"])
    if not delegable:
        findings.append(
            "device %s is a %s; this class does not take that kind on delegated "
            "evidence" % (device["reference"], device["kind"])
        )
        return {
            "verdict": DELEGATION_ROUTE_CLOSED,
            "device_reference": device["reference"],
            "device_kind": device["kind"],
            "route_delegable": False,
            "credited_basis_points": 0,
            "total_basis_points": sum(e["weight"] for e in objectives.values()) * 100,
            "credited_fraction": 0.0,
            "assurance_floor_percent": settings["assurance_floor_percent"],
            "assurance_meets_floor": False,
            "refused_objectives": sorted(objectives),
            "reopened_activities": sorted(objectives),
            "envelope_shortfalls": [],
            "per_objective": [],
            "accepted": False,
            "findings": findings,
        }

    credits = []
    refused = []
    reopened = []
    for name in sorted(objectives):
        strength = evidence.get(name, "none")
        item = credit_objective(
            name, objectives[name], strength, settings["min_strength_non_delegable"]
        )
        credits.append(item)
        if item["refused"]:
            refused.append(name)
            reopened.append(name)
            findings.append(
                "objective %s is not delegable and rests on %s; no credit is taken "
                "and the activity re-opens" % (name, item["strength"])
            )
        elif item["credit_percent"] == 0:
            findings.append(
                "objective %s carries no evidence and earns no credit" % (name,)
            )

    totals = credited_basis_points(credits, objectives)
    shortfalls = envelope_shortfalls(case["device"], case["mission"])
    for shortfall in shortfalls:
        reopened.append(shortfall["activity"])
        findings.append(
            "the mission %s of %d overruns the rated %d; activity %s re-opens"
            % (shortfall["axis"], shortfall["required"], shortfall["rated"],
               shortfall["activity"])
        )

    floor_met = assurance_meets_floor(
        totals["credited"], totals["total"], settings["assurance_floor_percent"]
    )
    if not floor_met:
        findings.append(
            "credited assurance %d of %d basis points falls below the %d per cent floor"
            % (totals["credited"], totals["total"], settings["assurance_floor_percent"])
        )

    if refused:
        verdict = MANDATORY_OBJECTIVE_UNEVIDENCED
    elif shortfalls and settings["envelope_shortfall_stops"]:
        verdict = RATED_ENVELOPE_SHORTFALL
    elif not floor_met:
        verdict = ASSURANCE_BELOW_FLOOR
    else:
        verdict = DELEGATED_ASSURANCE_ACCEPTED

    return {
        "verdict": verdict,
        "device_reference": device["reference"],
        "device_kind": device["kind"],
        "route_delegable": True,
        "credited_basis_points": totals["credited"],
        "total_basis_points": totals["total"],
        "credited_fraction": float(totals["credited"]) / float(totals["total"]),
        "assurance_floor_percent": settings["assurance_floor_percent"],
        "assurance_meets_floor": floor_met,
        "refused_objectives": refused,
        "reopened_activities": reopened,
        "envelope_shortfalls": shortfalls,
        "per_objective": credits,
        "accepted": verdict == DELEGATED_ASSURANCE_ACCEPTED,
        "findings": findings,
    }
