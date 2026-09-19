"""Agreement assessment for the final device Support and Maintenance Plan.

Anchor: ECSS-E-ST-20-40C clause 5.8.3 (validation, qualification and
acceptance phase -- agreeing the definitive plan for supporting and
maintaining the device after delivery). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve which support commitments the device owes from its type: an IP
   core has no test equipment to retain and no spares to hold, so demanding
   them manufactures a finding that is not there.
2. Check each commitment covers the contracted support period, and report
   the shortfall in months for the ones that do not.
3. Find the binding constraint: the shortest commitment caps the plan
   whatever the other commitments promise.
4. Compare the technology obsolescence horizon with the support period, and
   treat a declared mitigation as what lifts the horizon out of the cap.
5. Check the agreed anomaly response time against the contracted maximum.
6. Return the effective support period the plan can really deliver, the
   coverage ratio against what was asked, and a three-way disposition.
"""

import math

__all__ = [
    "COMMITMENT_APPLICABILITY",
    "COVERAGE_TOLERANCE",
    "DEVICE_TYPES",
    "DISPOSITIONS",
    "OBSOLESCENCE_MITIGATIONS",
    "validate_device_type",
    "owed_commitments",
    "validate_commitment",
    "validate_support_period",
    "coverage_shortfalls",
    "binding_constraint",
    "obsolescence_assessment",
    "response_time_shortfall",
    "effective_support_months",
    "assess_final_support_maintenance_plan",
]

# The coverage ratio is a ratio of whole months, so an exact unity is normally
# exact; the tolerance is here for the case where the caller supplies a
# fractional period, and keeps the comparison from turning on the last bit.
COVERAGE_TOLERANCE = 1e-9

DEVICE_TYPES = ("asic", "fpga", "ip-core")

# Which support commitments each device type owes after delivery.
COMMITMENT_APPLICABILITY = {
    "design-database-retention": ("asic", "fpga", "ip-core"),
    "tool-and-licence-retention": ("asic", "fpga", "ip-core"),
    "competence-retention": ("asic", "fpga", "ip-core"),
    "obsolescence-monitoring": ("asic", "fpga", "ip-core"),
    "anomaly-response": ("asic", "fpga", "ip-core"),
    "test-equipment-retention": ("asic", "fpga"),
    "spares-availability": ("asic", "fpga"),
}

OBSOLESCENCE_MITIGATIONS = (
    "last-time-buy",
    "alternative-source",
    "technology-retarget",
    "extended-storage",
)

DISPOSITIONS = ("agreed", "agreed-with-shortfall", "not-agreeable")


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    return stripped


def _months(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number of months, got %r" % (label, value))
    months = float(value)
    if not math.isfinite(months):
        raise ValueError("%s must be finite" % label)
    if months < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return months


def validate_device_type(device_type):
    """Return the normalised device type."""
    text = _text(device_type, "device type").lower()
    if text not in DEVICE_TYPES:
        raise ValueError(
            "device type %r is not one of %s" % (device_type, ", ".join(DEVICE_TYPES))
        )
    return text


def owed_commitments(device_type):
    """Return the sorted support commitments this device type owes."""
    dtype = validate_device_type(device_type)
    return sorted(
        name for name, types in COMMITMENT_APPLICABILITY.items() if dtype in types
    )


def validate_support_period(months):
    """Return the contracted post-delivery support period in months."""
    period = _months(months, "required_support_months")
    if period <= 0.0:
        raise ValueError("required_support_months must be positive, got %r" % (months,))
    return period


def validate_commitment(record):
    """Return a normalised support-commitment record."""
    if not isinstance(record, dict):
        raise ValueError("commitment record must be a mapping, got %r" % (record,))
    name = _text(record.get("name"), "commitment name").lower()
    if name not in COMMITMENT_APPLICABILITY:
        raise ValueError(
            "commitment %r is not a support and maintenance commitment; expected one of %s"
            % (name, ", ".join(sorted(COMMITMENT_APPLICABILITY)))
        )
    coverage = _months(record.get("coverage_months"), "commitment %s coverage_months" % name)
    agreed = record.get("customer_agreed", False)
    if not isinstance(agreed, bool):
        raise ValueError("commitment %s customer_agreed must be a boolean" % name)
    response_days = record.get("response_time_days")
    if response_days is not None:
        if not isinstance(response_days, (int, float)) or isinstance(response_days, bool):
            raise ValueError("commitment %s response_time_days must be a real number" % name)
        response_days = float(response_days)
        if not math.isfinite(response_days) or response_days <= 0.0:
            raise ValueError(
                "commitment %s response_time_days must be positive and finite" % name
            )
    if name == "anomaly-response" and response_days is None:
        raise ValueError("the anomaly-response commitment must state a response time")
    return {
        "name": name,
        "coverage_months": coverage,
        "customer_agreed": agreed,
        "response_time_days": response_days,
    }


def coverage_shortfalls(commitments, required_support_months, device_type):
    """Return the per-commitment coverage picture against the support period."""
    period = validate_support_period(required_support_months)
    owed = owed_commitments(device_type)
    if not isinstance(commitments, (list, tuple)):
        raise ValueError("commitments must be a sequence")
    checked = [validate_commitment(item) for item in commitments]
    names = [c["name"] for c in checked]
    if len(set(names)) != len(names):
        raise ValueError("the same commitment is declared twice")
    present = {c["name"]: c for c in checked}
    missing = sorted(name for name in owed if name not in present)
    not_owed = sorted(name for name in present if name not in owed)
    shortfalls = {}
    for name in owed:
        if name not in present:
            continue
        gap = period - present[name]["coverage_months"]
        if gap > 0.0:
            shortfalls[name] = gap
    unagreed = sorted(
        name for name in owed if name in present and not present[name]["customer_agreed"]
    )
    return {
        "owed": owed,
        "present": present,
        "missing": missing,
        "declared_but_not_owed": not_owed,
        "shortfall_months": shortfalls,
        "unagreed": unagreed,
        "required_support_months": period,
    }


def binding_constraint(coverage_report):
    """Return the commitment that caps the plan, and the months it caps it to."""
    if not isinstance(coverage_report, dict) or "present" not in coverage_report:
        raise ValueError("coverage_report must be the mapping returned by coverage_shortfalls")
    owed = coverage_report["owed"]
    present = coverage_report["present"]
    live = [(present[name]["coverage_months"], name) for name in owed if name in present]
    if not live:
        raise ValueError("no owed commitment is declared, so nothing binds the plan")
    live.sort()
    months, name = live[0]
    return {"commitment": name, "coverage_months": months}


def obsolescence_assessment(horizon_months, required_support_months, mitigations=None):
    """Return whether the technology horizon caps the support period."""
    horizon = _months(horizon_months, "obsolescence_horizon_months")
    period = validate_support_period(required_support_months)
    declared = []
    for item in mitigations or []:
        name = _text(item, "obsolescence mitigation").lower()
        if name not in OBSOLESCENCE_MITIGATIONS:
            raise ValueError(
                "obsolescence mitigation %r is not recognised; expected one of %s"
                % (item, ", ".join(OBSOLESCENCE_MITIGATIONS))
            )
        declared.append(name)
    if len(set(declared)) != len(declared):
        raise ValueError("the same obsolescence mitigation is declared twice")
    exposed = horizon < period and not math.isclose(
        horizon, period, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    return {
        "horizon_months": horizon,
        "mitigations": sorted(set(declared)),
        "horizon_below_support_period": exposed,
        "mitigation_required": exposed,
        "mitigation_declared": bool(declared),
        "caps_support": exposed and not declared,
    }


def response_time_shortfall(coverage_report, maximum_response_days):
    """Return how far the agreed anomaly response time misses the contracted one."""
    if not isinstance(coverage_report, dict) or "present" not in coverage_report:
        raise ValueError("coverage_report must be the mapping returned by coverage_shortfalls")
    if not isinstance(maximum_response_days, (int, float)) or isinstance(
        maximum_response_days, bool
    ):
        raise ValueError("maximum_response_days must be a real number")
    limit = float(maximum_response_days)
    if not math.isfinite(limit) or limit <= 0.0:
        raise ValueError("maximum_response_days must be positive and finite")
    record = coverage_report["present"].get("anomaly-response")
    if record is None:
        return None
    agreed = record["response_time_days"]
    if agreed <= limit or math.isclose(agreed, limit, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE):
        return 0.0
    return agreed - limit


def effective_support_months(coverage_report, obsolescence_report):
    """Return the support period the plan can really deliver."""
    if not isinstance(obsolescence_report, dict) or "caps_support" not in obsolescence_report:
        raise ValueError(
            "obsolescence_report must be the mapping returned by obsolescence_assessment"
        )
    if coverage_report.get("missing"):
        # A commitment that was never made cannot be relied on for any month.
        return 0.0
    months = binding_constraint(coverage_report)["coverage_months"]
    if obsolescence_report["caps_support"]:
        months = min(months, obsolescence_report["horizon_months"])
    return months


def assess_final_support_maintenance_plan(spec):
    """Run the full clause 5.8.3 support and maintenance plan assessment.

    spec keys: device_type, required_support_months, commitments,
    obsolescence_horizon_months, maximum_response_days; optional
    obsolescence_mitigations.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "device_type",
        "required_support_months",
        "commitments",
        "obsolescence_horizon_months",
        "maximum_response_days",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    device_type = validate_device_type(spec["device_type"])
    coverage = coverage_shortfalls(
        spec["commitments"], spec["required_support_months"], device_type
    )
    obsolescence = obsolescence_assessment(
        spec["obsolescence_horizon_months"],
        coverage["required_support_months"],
        spec.get("obsolescence_mitigations"),
    )
    response_gap = response_time_shortfall(coverage, spec["maximum_response_days"])
    effective = effective_support_months(coverage, obsolescence)
    ratio = effective / coverage["required_support_months"]

    findings = []
    if coverage["missing"]:
        findings.append(
            "commitment(s) a %s device owes are absent from the plan: %s"
            % (device_type, ", ".join(coverage["missing"]))
        )
    if coverage["declared_but_not_owed"]:
        findings.append(
            "commitment(s) declared that a %s device does not owe: %s"
            % (device_type, ", ".join(coverage["declared_but_not_owed"]))
        )
    for name in sorted(coverage["shortfall_months"]):
        findings.append(
            "commitment %s covers %.1f months short of the %.1f month support period"
            % (name, coverage["shortfall_months"][name], coverage["required_support_months"])
        )
    if coverage["unagreed"]:
        findings.append(
            "commitment(s) not agreed by the customer: %s" % ", ".join(coverage["unagreed"])
        )
    if obsolescence["mitigation_required"] and not obsolescence["mitigation_declared"]:
        findings.append(
            "technology obsolescence horizon of %.1f months falls inside the %.1f month "
            "support period and no mitigation is declared"
            % (obsolescence["horizon_months"], coverage["required_support_months"])
        )
    if response_gap:
        findings.append(
            "agreed anomaly response time exceeds the contracted maximum by %.1f day(s)"
            % response_gap
        )

    covered = math.isclose(ratio, 1.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE) or ratio > 1.0
    if not covered or coverage["missing"] or coverage["unagreed"]:
        disposition = "not-agreeable"
    elif findings:
        disposition = "agreed-with-shortfall"
    else:
        disposition = "agreed"

    return {
        "device_type": device_type,
        "required_support_months": coverage["required_support_months"],
        "effective_support_months": effective,
        "coverage_ratio": ratio,
        "binding_constraint": binding_constraint(coverage) if not coverage["missing"] else None,
        "shortfall_months": coverage["shortfall_months"],
        "obsolescence": obsolescence,
        "response_time_shortfall_days": response_gap,
        "disposition": disposition,
        "findings": findings,
    }
