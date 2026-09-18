"""Baseline eligibility rules for choosing a microwave die for an application.

Anchor: ECSS-Q-ST-60-12 clause 5.1 (die selection -- the general rules a bare
microwave die satisfies before it may enter a design at all). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the application envelope: operating band, case-temperature range,
   mission total-ionising-dose, required life and the assembly route the die
   has to survive.
2. Validate each candidate die record: part identifier, the process it is
   fabricated on, the supply route it arrives through, and whatever coverage
   data (band, temperature, dose capability, rated life, evaluation status)
   the manufacturer has on record.
3. Grade coverage: how much of the application band the die spans, how much
   temperature margin it holds at each end, how much dose headroom it carries
   and how much rated life it offers.
4. Separate a hard exclusion (data present and insufficient, or a supply route
   that cannot be traced back to the manufacturer) from a recoverable evidence
   gap (a datum simply not on record yet).
5. Group each candidate as eligible, eligible-with-actions or not-eligible,
   score the survivors on a reproducible coverage composite, and rank them.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "REFERENCE_TEMPERATURE_MARGIN_C",
    "SUPPLY_ROUTES",
    "EVALUATION_STATUSES",
    "ASSEMBLY_ROUTES",
    "CATEGORY_ORDER",
    "validate_application",
    "validate_candidate",
    "band_coverage_fraction",
    "temperature_margins_c",
    "dose_headroom",
    "life_headroom",
    "baseline_findings",
    "categorize_candidate",
    "coverage_score",
    "assess_candidate",
    "rank_candidates",
    "assess_die_baseline_selection",
]

# Coverage comparisons are ratios of measured quantities: an exactly covered
# band edge can land a unit in the last place on the wrong side. Absorb the
# representation error here instead of relaxing the engineering envelope.
MARGIN_TOLERANCE = 1e-9

# Temperature margin at which the thermal component of the coverage score
# saturates. It grades comfort, never eligibility -- eligibility is the sign
# of the margin, which is decided separately.
REFERENCE_TEMPERATURE_MARGIN_C = 20.0

SUPPLY_ROUTES = ("foundry-direct", "authorized-distributor", "broker")
EVALUATION_STATUSES = ("qualified", "evaluated", "unevaluated")
ASSEMBLY_ROUTES = ("die-attach-and-wire-bond", "flip-chip", "hermetic-package")
CATEGORY_ORDER = ("eligible", "eligible-with-actions", "not-eligible")


def _number(value, label):
    """Return value as a finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float, or raise."""
    out = _number(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _range(value, label):
    """Return a validated (low, high) pair of finite floats with low <= high."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _number(value[0], "%s lower bound" % label)
    high = _number(value[1], "%s upper bound" % label)
    if low > high:
        raise ValueError("%s lower bound %g exceeds upper bound %g" % (label, low, high))
    return (low, high)


def _optional_range(value, label):
    """Return a validated range, or None when the datum is not on record."""
    if value is None:
        return None
    return _range(value, label)


def _optional_positive(value, label):
    """Return a validated positive float, or None when not on record."""
    if value is None:
        return None
    return _positive(value, label)


def validate_application(application):
    """Return the normalised application envelope the die has to cover."""
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping")
    for key in ("band_ghz", "case_temperature_range_c", "mission_tid_krad",
                "required_life_hours", "assembly_route"):
        if key not in application:
            raise ValueError("application missing required key '%s'" % key)
    band = _range(application["band_ghz"], "application band_ghz")
    if band[0] <= 0.0:
        raise ValueError("application band_ghz must be strictly positive")
    route = application["assembly_route"]
    if route not in ASSEMBLY_ROUTES:
        raise ValueError(
            "assembly_route %r is not one of %s" % (route, ", ".join(ASSEMBLY_ROUTES))
        )
    return {
        "band_ghz": band,
        "case_temperature_range_c": _range(
            application["case_temperature_range_c"], "case_temperature_range_c"
        ),
        "mission_tid_krad": _positive(application["mission_tid_krad"], "mission_tid_krad"),
        "required_life_hours": _positive(
            application["required_life_hours"], "required_life_hours"
        ),
        "assembly_route": route,
    }


def validate_candidate(candidate):
    """Return the normalised candidate die record."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping")
    for key in ("part_id", "process_id", "supply_route"):
        if key not in candidate:
            raise ValueError("candidate missing required key '%s'" % key)
    part_id = candidate["part_id"]
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string")
    process_id = candidate["process_id"]
    if not isinstance(process_id, str) or not process_id.strip():
        raise ValueError("process_id must be a non-empty string")
    supply_route = candidate["supply_route"]
    if supply_route not in SUPPLY_ROUTES:
        raise ValueError(
            "supply_route %r is not one of %s" % (supply_route, ", ".join(SUPPLY_ROUTES))
        )
    status = candidate.get("evaluation_status")
    if status is not None and status not in EVALUATION_STATUSES:
        raise ValueError(
            "evaluation_status %r is not one of %s"
            % (status, ", ".join(EVALUATION_STATUSES))
        )
    traceable = candidate.get("traceable_to_manufacturer", supply_route != "broker")
    if not isinstance(traceable, bool):
        raise ValueError("traceable_to_manufacturer must be a boolean")
    routes = candidate.get("assembly_routes")
    if routes is None:
        routes = list(ASSEMBLY_ROUTES)
    if not isinstance(routes, (list, tuple)) or not routes:
        raise ValueError("assembly_routes must be a non-empty sequence when given")
    for item in routes:
        if item not in ASSEMBLY_ROUTES:
            raise ValueError("assembly route %r is not recognised" % (item,))
    return {
        "part_id": part_id.strip(),
        "process_id": process_id.strip(),
        "supply_route": supply_route,
        "traceable_to_manufacturer": traceable,
        "band_ghz": _optional_range(candidate.get("band_ghz"), "candidate band_ghz"),
        "temperature_range_c": _optional_range(
            candidate.get("temperature_range_c"), "candidate temperature_range_c"
        ),
        "tid_capability_krad": _optional_positive(
            candidate.get("tid_capability_krad"), "tid_capability_krad"
        ),
        "rated_life_hours": _optional_positive(
            candidate.get("rated_life_hours"), "rated_life_hours"
        ),
        "evaluation_status": status,
        "assembly_routes": [str(item) for item in routes],
    }


def band_coverage_fraction(die_band, application_band):
    """Return the fraction of the application band the die band spans (0..1)."""
    die_lo, die_hi = _range(die_band, "die band")
    app_lo, app_hi = _range(application_band, "application band")
    width = app_hi - app_lo
    if width <= 0.0:
        return 1.0 if (die_lo <= app_lo and app_lo <= die_hi) else 0.0
    overlap = min(die_hi, app_hi) - max(die_lo, app_lo)
    if overlap <= 0.0:
        return 0.0
    fraction = overlap / width
    return 1.0 if fraction > 1.0 else fraction


def temperature_margins_c(die_range, application_range):
    """Return (cold_margin, hot_margin) in C; positive means the die encloses."""
    die_lo, die_hi = _range(die_range, "die temperature_range_c")
    app_lo, app_hi = _range(application_range, "application case_temperature_range_c")
    return (app_lo - die_lo, die_hi - app_hi)


def dose_headroom(die_tid_krad, mission_tid_krad):
    """Return the ratio of the die dose capability to the mission dose."""
    capability = _positive(die_tid_krad, "tid_capability_krad")
    mission = _positive(mission_tid_krad, "mission_tid_krad")
    return capability / mission


def life_headroom(rated_life_hours, required_life_hours):
    """Return the ratio of the rated die life to the life the mission needs."""
    rated = _positive(rated_life_hours, "rated_life_hours")
    required = _positive(required_life_hours, "required_life_hours")
    return rated / required


def _finding(code, severity, detail):
    if severity not in ("exclusion", "action"):
        raise ValueError("severity must be 'exclusion' or 'action', got %r" % (severity,))
    return {"code": code, "severity": severity, "detail": detail}


def baseline_findings(candidate, application, controlled_processes, required_dose_factor=1.0):
    """Return the baseline findings raised against one candidate die."""
    die = validate_candidate(candidate)
    app = validate_application(application)
    factor = _positive(required_dose_factor, "required_dose_factor")
    if not isinstance(controlled_processes, (list, tuple)) or not controlled_processes:
        raise ValueError("controlled_processes must be a non-empty sequence of identifiers")
    controlled = set()
    for item in controlled_processes:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("every controlled process identifier must be a non-empty string")
        controlled.add(item.strip())

    findings = []
    if die["process_id"] not in controlled:
        findings.append(_finding(
            "process-not-controlled", "exclusion",
            "process %s is not on the controlled process list" % die["process_id"],
        ))
    if not die["traceable_to_manufacturer"]:
        findings.append(_finding(
            "supply-route-not-traceable", "exclusion",
            "supply route %s carries no traceability to the manufacturer"
            % die["supply_route"],
        ))
    elif die["supply_route"] == "broker":
        findings.append(_finding(
            "supply-route-needs-verification", "action",
            "a traceable broker route still owes an incoming verification plan",
        ))

    if die["band_ghz"] is None:
        findings.append(_finding(
            "band-data-absent", "action", "no operating band is on record for the die",
        ))
    else:
        fraction = band_coverage_fraction(die["band_ghz"], app["band_ghz"])
        if fraction < 1.0 - MARGIN_TOLERANCE:
            findings.append(_finding(
                "band-not-covered", "exclusion",
                "die band covers %.4f of the application band" % fraction,
            ))

    if die["temperature_range_c"] is None:
        findings.append(_finding(
            "temperature-data-absent", "action",
            "no operating temperature range is on record for the die",
        ))
    else:
        cold, hot = temperature_margins_c(
            die["temperature_range_c"], app["case_temperature_range_c"]
        )
        if cold < -MARGIN_TOLERANCE or hot < -MARGIN_TOLERANCE:
            findings.append(_finding(
                "temperature-not-enclosed", "exclusion",
                "temperature margins are %.3f C cold and %.3f C hot" % (cold, hot),
            ))

    if die["tid_capability_krad"] is None:
        findings.append(_finding(
            "dose-data-absent", "action",
            "no total-dose capability is on record for the die",
        ))
    else:
        headroom = dose_headroom(die["tid_capability_krad"], app["mission_tid_krad"])
        if headroom < factor - MARGIN_TOLERANCE:
            findings.append(_finding(
                "dose-headroom-short", "exclusion",
                "dose headroom %.4f is below the required factor %.4f" % (headroom, factor),
            ))

    if die["rated_life_hours"] is None:
        findings.append(_finding(
            "life-data-absent", "action", "no rated life is on record for the die",
        ))
    else:
        headroom = life_headroom(die["rated_life_hours"], app["required_life_hours"])
        if headroom < 1.0 - MARGIN_TOLERANCE:
            findings.append(_finding(
                "life-headroom-short", "exclusion",
                "rated life covers %.4f of the required life" % headroom,
            ))

    if die["evaluation_status"] is None:
        findings.append(_finding(
            "evaluation-status-absent", "action",
            "the evaluation status of the die is not on record",
        ))
    elif die["evaluation_status"] == "unevaluated":
        findings.append(_finding(
            "evaluation-programme-owed", "action",
            "an unevaluated die owes an evaluation programme before design commitment",
        ))

    if app["assembly_route"] not in die["assembly_routes"]:
        findings.append(_finding(
            "assembly-route-unsupported", "exclusion",
            "the die does not support the %s assembly route" % app["assembly_route"],
        ))
    return findings


def categorize_candidate(findings):
    """Group a candidate from its findings into one of the baseline categories."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for item in findings:
        if not isinstance(item, dict) or "severity" not in item:
            raise ValueError("each finding must be a mapping carrying 'severity'")
        severities.add(item["severity"])
    if "exclusion" in severities:
        return "not-eligible"
    if "action" in severities:
        return "eligible-with-actions"
    return "eligible"


def _clamp_unit(value):
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def coverage_score(candidate, application, required_dose_factor=1.0):
    """Return a reproducible 0..1 composite of how well the die covers the need."""
    die = validate_candidate(candidate)
    app = validate_application(application)
    factor = _positive(required_dose_factor, "required_dose_factor")

    if die["band_ghz"] is None:
        band_part = 0.0
    else:
        band_part = band_coverage_fraction(die["band_ghz"], app["band_ghz"])

    if die["temperature_range_c"] is None:
        thermal_part = 0.0
    else:
        cold, hot = temperature_margins_c(
            die["temperature_range_c"], app["case_temperature_range_c"]
        )
        thermal_part = _clamp_unit(min(cold, hot) / REFERENCE_TEMPERATURE_MARGIN_C)

    if die["tid_capability_krad"] is None:
        dose_part = 0.0
    else:
        dose_part = _clamp_unit(
            dose_headroom(die["tid_capability_krad"], app["mission_tid_krad"]) / (2.0 * factor)
        )

    if die["rated_life_hours"] is None:
        life_part = 0.0
    else:
        life_part = _clamp_unit(
            life_headroom(die["rated_life_hours"], app["required_life_hours"]) / 2.0
        )

    return (band_part + thermal_part + dose_part + life_part) / 4.0


def assess_candidate(candidate, application, controlled_processes, required_dose_factor=1.0):
    """Return the full baseline record for one candidate die."""
    die = validate_candidate(candidate)
    findings = baseline_findings(
        candidate, application, controlled_processes, required_dose_factor
    )
    return {
        "part_id": die["part_id"],
        "process_id": die["process_id"],
        "supply_route": die["supply_route"],
        "category": categorize_candidate(findings),
        "coverage_score": coverage_score(candidate, application, required_dose_factor),
        "findings": findings,
        "exclusions": [f for f in findings if f["severity"] == "exclusion"],
        "actions": [f for f in findings if f["severity"] == "action"],
    }


def rank_candidates(records):
    """Return the records ordered by category, then coverage score, then part id."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each record must be a mapping")
        for key in ("category", "coverage_score", "part_id"):
            if key not in record:
                raise ValueError("record missing required key '%s'" % key)
        if record["category"] not in CATEGORY_ORDER:
            raise ValueError("unrecognised category %r" % (record["category"],))
    return sorted(
        records,
        key=lambda r: (
            CATEGORY_ORDER.index(r["category"]),
            -float(r["coverage_score"]),
            r["part_id"],
        ),
    )


def assess_die_baseline_selection(spec):
    """Run the full clause 5.1 baseline die-selection assessment.

    spec keys: application, candidates, controlled_processes, and optionally
    required_dose_factor (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("application", "candidates", "controlled_processes"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    candidates = spec["candidates"]
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("spec['candidates'] must be a non-empty sequence")
    factor = _positive(spec.get("required_dose_factor", 1.0), "required_dose_factor")

    records = [
        assess_candidate(
            candidate, spec["application"], spec["controlled_processes"], factor
        )
        for candidate in candidates
    ]
    seen = set()
    for record in records:
        if record["part_id"] in seen:
            raise ValueError("duplicate part_id %r in the candidate set" % record["part_id"])
        seen.add(record["part_id"])

    ranked = rank_candidates(records)
    shortlist = [r for r in ranked if r["category"] != "not-eligible"]
    recommended = None
    for record in ranked:
        if record["category"] == "eligible":
            recommended = record
            break
    counts = {name: 0 for name in CATEGORY_ORDER}
    for record in records:
        counts[record["category"]] += 1
    return {
        "records": records,
        "ranked": ranked,
        "shortlist": shortlist,
        "recommended": recommended,
        "counts": counts,
        "open_actions": sum(len(r["actions"]) for r in shortlist),
        "clean": bool(shortlist) and all(not r["actions"] for r in shortlist),
    }
