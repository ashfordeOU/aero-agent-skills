"""Selection of a validated semiconductor process and the foundry operating it.

Anchor: ECSS-Q-ST-60-12 clause 5.2 (choosing the monolithic-microwave process
and the foundry line that runs it). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the process option: identifiers, technology, validation status and
   reference, the age of that validation, whether the process has changed since
   it was granted, the geometry and voltage capability, the passive elements
   offered, the process-monitor evidence, the declared production horizon and
   the line certification.
2. Validate the design need: the highest frequency the circuit works at, the
   supply rail, the passive elements the topology needs, the programme horizon
   and the acceptance thresholds for capability and monitor coverage.
3. Derive the usable frequency of the process from its gate length and a
   technology constant, and compare it with the design need.
4. Form the process-capability index of each monitored parameter from its
   monitor statistics and compare the weakest with the acceptance threshold.
5. Weigh validation currency, a process change since validation, the supply
   continuity horizon and the line certification.
6. Separate a hard exclusion from a recoverable action, group the option as
   selectable, selectable-with-actions or not-selectable, score it on a
   reproducible composite, and rank the options.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "TECHNOLOGY_FREQUENCY_CONSTANT_GHZ_UM",
    "VALIDATION_STATUSES",
    "CATEGORY_ORDER",
    "max_usable_frequency_ghz",
    "process_capability_index",
    "weakest_capability",
    "validation_currency",
    "supply_continuity_margin_years",
    "validate_process_option",
    "validate_design_need",
    "process_findings",
    "categorize_option",
    "option_score",
    "assess_process_option",
    "rank_process_options",
    "assess_foundry_process_selection",
]

# Frequency, capability and horizon comparisons are ratios of measured
# quantities. An exactly adequate option can land a unit in the last place on
# the wrong side; absorb that here, never by relaxing the acceptance value.
MARGIN_TOLERANCE = 1e-9

# Usable frequency scales roughly inversely with gate length; the constant is
# the technology-specific proportionality in GHz*um used for first-cut process
# screening, not a substitute for the foundry's own model data.
TECHNOLOGY_FREQUENCY_CONSTANT_GHZ_UM = {
    "gaas-phemt": 9.0,
    "gaas-mhemt": 12.0,
    "gan-hemt": 7.5,
    "inp-hemt": 15.0,
    "sige-bicmos": 6.0,
}

VALIDATION_STATUSES = ("validated", "in-validation", "not-validated")
CATEGORY_ORDER = ("selectable", "selectable-with-actions", "not-selectable")


def _number(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _number(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _non_negative(value, label):
    out = _number(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def max_usable_frequency_ghz(gate_length_um, technology):
    """Return the first-cut usable frequency of a process from its geometry."""
    length = _positive(gate_length_um, "gate_length_um")
    if technology not in TECHNOLOGY_FREQUENCY_CONSTANT_GHZ_UM:
        raise ValueError(
            "technology %r is not one of %s"
            % (technology, ", ".join(sorted(TECHNOLOGY_FREQUENCY_CONSTANT_GHZ_UM)))
        )
    return TECHNOLOGY_FREQUENCY_CONSTANT_GHZ_UM[technology] / length


def process_capability_index(mean, sigma, lower_limit, upper_limit):
    """Return the one-sided-worst capability index of a monitored parameter."""
    mu = _number(mean, "mean")
    sd = _positive(sigma, "sigma")
    low = _number(lower_limit, "lower_limit")
    high = _number(upper_limit, "upper_limit")
    if low >= high:
        raise ValueError("lower_limit %g must be below upper_limit %g" % (low, high))
    return min(high - mu, mu - low) / (3.0 * sd)


def weakest_capability(monitor_statistics):
    """Return (parameter, index) for the monitored parameter with the least capability."""
    if not isinstance(monitor_statistics, dict) or not monitor_statistics:
        raise ValueError("monitor_statistics must be a non-empty mapping")
    worst_name = None
    worst_value = None
    for name in sorted(monitor_statistics):
        entry = monitor_statistics[name]
        if not isinstance(entry, dict):
            raise ValueError("monitor entry %r must be a mapping" % (name,))
        for key in ("mean", "sigma", "lower_limit", "upper_limit"):
            if key not in entry:
                raise ValueError("monitor entry %r missing '%s'" % (name, key))
        index = process_capability_index(
            entry["mean"], entry["sigma"], entry["lower_limit"], entry["upper_limit"]
        )
        if worst_value is None or index < worst_value:
            worst_name = name
            worst_value = index
    return (worst_name, worst_value)


def validation_currency(status, age_months, validity_months, process_change_since_validation):
    """Return whether the process validation is current, and why it is not."""
    if status not in VALIDATION_STATUSES:
        raise ValueError(
            "validation status %r is not one of %s" % (status, ", ".join(VALIDATION_STATUSES))
        )
    if not isinstance(process_change_since_validation, bool):
        raise ValueError("process_change_since_validation must be a boolean")
    validity = _positive(validity_months, "validity_months")
    if status != "validated":
        return {"current": False, "reason": "status-" + status}
    if process_change_since_validation:
        return {"current": False, "reason": "process-changed-since-validation"}
    if age_months is None:
        return {"current": False, "reason": "validation-age-absent"}
    age = _non_negative(age_months, "age_months")
    if age > validity + MARGIN_TOLERANCE:
        return {"current": False, "reason": "validation-stale"}
    return {"current": True, "reason": "validation-current"}


def supply_continuity_margin_years(production_horizon_years, programme_horizon_years):
    """Return the years by which the declared production horizon outlasts the programme."""
    horizon = _non_negative(production_horizon_years, "production_horizon_years")
    programme = _positive(programme_horizon_years, "programme_horizon_years")
    return horizon - programme


def validate_process_option(option):
    """Return the normalised foundry-and-process option record."""
    if not isinstance(option, dict):
        raise ValueError("option must be a mapping")
    for key in ("process_id", "foundry_id", "technology", "validation_status",
                "gate_length_um", "breakdown_voltage_v"):
        if key not in option:
            raise ValueError("option missing required key '%s'" % key)
    technology = option["technology"]
    if technology not in TECHNOLOGY_FREQUENCY_CONSTANT_GHZ_UM:
        raise ValueError("technology %r is not recognised" % (technology,))
    status = option["validation_status"]
    if status not in VALIDATION_STATUSES:
        raise ValueError("validation_status %r is not recognised" % (status,))
    change = option.get("process_change_since_validation", False)
    if not isinstance(change, bool):
        raise ValueError("process_change_since_validation must be a boolean")
    passives = option.get("passives", [])
    if not isinstance(passives, (list, tuple)):
        raise ValueError("passives must be a sequence")
    monitor_lots = option.get("monitor_lots")
    if monitor_lots is not None:
        if not isinstance(monitor_lots, int) or isinstance(monitor_lots, bool):
            raise ValueError("monitor_lots must be an integer")
        if monitor_lots < 0:
            raise ValueError("monitor_lots must be non-negative")
    reference = option.get("validation_reference")
    if reference is not None and (not isinstance(reference, str) or not reference.strip()):
        raise ValueError("validation_reference must be a non-empty string when given")
    certification = option.get("line_certification")
    if certification is not None and (
            not isinstance(certification, str) or not certification.strip()):
        raise ValueError("line_certification must be a non-empty string when given")
    age = option.get("validation_age_months")
    horizon = option.get("production_horizon_years")
    return {
        "process_id": _identifier(option["process_id"], "process_id"),
        "foundry_id": _identifier(option["foundry_id"], "foundry_id"),
        "technology": technology,
        "validation_status": status,
        "validation_reference": reference.strip() if isinstance(reference, str) else None,
        "validation_age_months": None if age is None else _non_negative(
            age, "validation_age_months"),
        "process_change_since_validation": change,
        "gate_length_um": _positive(option["gate_length_um"], "gate_length_um"),
        "breakdown_voltage_v": _positive(option["breakdown_voltage_v"], "breakdown_voltage_v"),
        "passives": [_identifier(p, "passive element") for p in passives],
        "monitor_lots": monitor_lots,
        "monitor_statistics": option.get("monitor_statistics"),
        "production_horizon_years": None if horizon is None else _non_negative(
            horizon, "production_horizon_years"),
        "line_certification": (
            certification.strip() if isinstance(certification, str) else None),
    }


def _monitor_lot_threshold(value):
    """Return a validated non-negative integer lot-count threshold."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("min_monitor_lots must be an integer, got %r" % (value,))
    if value < 0:
        raise ValueError("min_monitor_lots must be non-negative, got %r" % (value,))
    return value


def validate_design_need(need):
    """Return the normalised design need the process has to satisfy."""
    if not isinstance(need, dict):
        raise ValueError("need must be a mapping")
    for key in ("max_frequency_ghz", "supply_voltage_v", "programme_horizon_years"):
        if key not in need:
            raise ValueError("need missing required key '%s'" % key)
    passives = need.get("required_passives", [])
    if not isinstance(passives, (list, tuple)):
        raise ValueError("required_passives must be a sequence")
    return {
        "max_frequency_ghz": _positive(need["max_frequency_ghz"], "max_frequency_ghz"),
        "supply_voltage_v": _positive(need["supply_voltage_v"], "supply_voltage_v"),
        "breakdown_factor": _positive(need.get("breakdown_factor", 2.0), "breakdown_factor"),
        "required_passives": [_identifier(p, "required passive") for p in passives],
        "programme_horizon_years": _positive(
            need["programme_horizon_years"], "programme_horizon_years"),
        "min_capability_index": _positive(
            need.get("min_capability_index", 1.33), "min_capability_index"),
        "min_monitor_lots": _monitor_lot_threshold(need.get("min_monitor_lots", 3)),
        "validation_validity_months": _positive(
            need.get("validation_validity_months", 36.0), "validation_validity_months"),
    }


def _finding(code, severity, detail):
    if severity not in ("exclusion", "action"):
        raise ValueError("severity must be 'exclusion' or 'action', got %r" % (severity,))
    return {"code": code, "severity": severity, "detail": detail}


def process_findings(option, need):
    """Return the findings raised against one foundry-and-process option."""
    process = validate_process_option(option)
    want = validate_design_need(need)
    findings = []

    currency = validation_currency(
        process["validation_status"], process["validation_age_months"],
        want["validation_validity_months"], process["process_change_since_validation"],
    )
    if not currency["current"]:
        if currency["reason"] == "status-not-validated":
            findings.append(_finding(
                "process-not-validated", "exclusion",
                "the process carries no validation at all",
            ))
        elif currency["reason"] == "process-changed-since-validation":
            findings.append(_finding(
                "process-changed-since-validation", "exclusion",
                "the process changed after validation and owes a re-qualification",
            ))
        elif currency["reason"] == "status-in-validation":
            findings.append(_finding(
                "validation-in-progress", "action",
                "validation is open; the design cannot be committed until it closes",
            ))
        elif currency["reason"] == "validation-stale":
            findings.append(_finding(
                "validation-stale", "action",
                "the validation is older than the validity window and owes a refresh",
            ))
        else:
            findings.append(_finding(
                "validation-age-absent", "action",
                "the age of the process validation is not on record",
            ))
    if process["validation_reference"] is None:
        findings.append(_finding(
            "validation-reference-absent", "action",
            "no validation reference document is on record",
        ))

    usable = max_usable_frequency_ghz(process["gate_length_um"], process["technology"])
    if usable < want["max_frequency_ghz"] - MARGIN_TOLERANCE:
        findings.append(_finding(
            "frequency-capability-short", "exclusion",
            "usable frequency %.4f GHz is below the required %.4f GHz"
            % (usable, want["max_frequency_ghz"]),
        ))

    required_breakdown = want["supply_voltage_v"] * want["breakdown_factor"]
    if process["breakdown_voltage_v"] < required_breakdown - MARGIN_TOLERANCE:
        findings.append(_finding(
            "breakdown-voltage-short", "exclusion",
            "breakdown voltage %.4f V is below the required %.4f V"
            % (process["breakdown_voltage_v"], required_breakdown),
        ))

    offered = set(process["passives"])
    for element in want["required_passives"]:
        if element not in offered:
            findings.append(_finding(
                "passive-element-absent", "exclusion",
                "the process design kit does not offer %s" % element,
            ))

    if process["monitor_statistics"] is None:
        findings.append(_finding(
            "monitor-data-absent", "action",
            "no process-monitor statistics are on record",
        ))
    else:
        name, index = weakest_capability(process["monitor_statistics"])
        if index < want["min_capability_index"] - MARGIN_TOLERANCE:
            findings.append(_finding(
                "capability-index-short", "exclusion",
                "weakest monitored parameter %s has capability %.4f, below %.4f"
                % (name, index, want["min_capability_index"]),
            ))
    if process["monitor_lots"] is None:
        findings.append(_finding(
            "monitor-lot-count-absent", "action",
            "the number of monitored lots is not on record",
        ))
    elif process["monitor_lots"] < want["min_monitor_lots"]:
        findings.append(_finding(
            "monitor-lot-count-short", "action",
            "%d monitored lots is below the %d the acceptance needs"
            % (process["monitor_lots"], want["min_monitor_lots"]),
        ))

    if process["production_horizon_years"] is None:
        findings.append(_finding(
            "production-horizon-absent", "action",
            "no declared production horizon is on record",
        ))
    else:
        margin = supply_continuity_margin_years(
            process["production_horizon_years"], want["programme_horizon_years"]
        )
        if margin < -MARGIN_TOLERANCE:
            findings.append(_finding(
                "supply-continuity-short", "action",
                "the production horizon falls %.3f years short of the programme"
                % (-margin,),
            ))

    if process["line_certification"] is None:
        findings.append(_finding(
            "line-certification-absent", "action",
            "no quality certification is on record for the foundry line",
        ))
    return findings


def categorize_option(findings):
    """Group an option from its findings into one of the selection categories."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for item in findings:
        if not isinstance(item, dict) or "severity" not in item:
            raise ValueError("each finding must be a mapping carrying 'severity'")
        severities.add(item["severity"])
    if "exclusion" in severities:
        return "not-selectable"
    if "action" in severities:
        return "selectable-with-actions"
    return "selectable"


def _clamp_unit(value):
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def option_score(option, need):
    """Return a reproducible 0..1 composite of how well the option fits the need."""
    process = validate_process_option(option)
    want = validate_design_need(need)
    usable = max_usable_frequency_ghz(process["gate_length_um"], process["technology"])
    frequency_part = _clamp_unit(usable / (2.0 * want["max_frequency_ghz"]))
    voltage_part = _clamp_unit(
        process["breakdown_voltage_v"]
        / (2.0 * want["supply_voltage_v"] * want["breakdown_factor"])
    )
    if process["monitor_statistics"] is None:
        capability_part = 0.0
    else:
        _, index = weakest_capability(process["monitor_statistics"])
        capability_part = _clamp_unit(index / (2.0 * want["min_capability_index"]))
    if process["production_horizon_years"] is None:
        continuity_part = 0.0
    else:
        continuity_part = _clamp_unit(
            process["production_horizon_years"] / (2.0 * want["programme_horizon_years"])
        )
    return (frequency_part + voltage_part + capability_part + continuity_part) / 4.0


def assess_process_option(option, need):
    """Return the full clause 5.2 record for one foundry-and-process option."""
    process = validate_process_option(option)
    findings = process_findings(option, need)
    return {
        "process_id": process["process_id"],
        "foundry_id": process["foundry_id"],
        "technology": process["technology"],
        "option_id": "%s/%s" % (process["foundry_id"], process["process_id"]),
        "category": categorize_option(findings),
        "score": option_score(option, need),
        "findings": findings,
        "exclusions": [f for f in findings if f["severity"] == "exclusion"],
        "actions": [f for f in findings if f["severity"] == "action"],
    }


def rank_process_options(records):
    """Return the records ordered by category, then score, then option identifier."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each record must be a mapping")
        for key in ("category", "score", "option_id"):
            if key not in record:
                raise ValueError("record missing required key '%s'" % key)
        if record["category"] not in CATEGORY_ORDER:
            raise ValueError("unrecognised category %r" % (record["category"],))
    return sorted(
        records,
        key=lambda r: (
            CATEGORY_ORDER.index(r["category"]), -float(r["score"]), r["option_id"]
        ),
    )


def assess_foundry_process_selection(spec):
    """Run the full clause 5.2 foundry-and-process selection assessment.

    spec keys: need (the design need) and options (the candidate
    foundry-and-process pairings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("need", "options"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    options = spec["options"]
    if not isinstance(options, (list, tuple)) or not options:
        raise ValueError("spec['options'] must be a non-empty sequence")
    records = [assess_process_option(option, spec["need"]) for option in options]
    seen = set()
    for record in records:
        if record["option_id"] in seen:
            raise ValueError("duplicate option %r in the option set" % record["option_id"])
        seen.add(record["option_id"])
    ranked = rank_process_options(records)
    shortlist = [r for r in ranked if r["category"] != "not-selectable"]
    recommended = None
    for record in ranked:
        if record["category"] == "selectable":
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
