#!/usr/bin/env python3
"""Single-carrier nominal analysis margins -- ECSS-E-ST-20-01C clause 4.6.2.2.

Deterministic, offline, standard-library-only assembly of the analysis-margin
a single-carrier multipactor case owes when it is closed by modelling:

* take the base value of the selected design-analysis-level;
* add an adder for every uncertainty contribution the worst-case model does
  not bound, rejecting a coverage claim the level cannot support;
* add the equipment-type adder;
* subtract the design-heritage credit, withheld when the recurring unit does
  not keep the same manufacturing route;
* hold the assembled figure at the declared floor;
* compare it against the achieved decibel multipactor-margin and report the
  shortfall.

Every number below is a default margin-policy table that a programme replaces
with its declared values; nothing in the module hard-codes a pass.

The clause is cited as the anchor only; no standard text is reproduced.
"""

import math

LEVEL_ONE = "level-one"
LEVEL_TWO = "level-two"
ANALYSIS_LEVELS = (LEVEL_ONE, LEVEL_TWO)

#: Uncertainty contributions budgeted case by case.
MARGIN_CONTRIBUTIONS = (
    "manufacturing-tolerance-spread",
    "secondary-emission-yield-scatter",
    "electromagnetic-field-model-error",
    "power-measurement-uncertainty",
    "temperature-induced-gap-change",
)

#: Contributions whose worst-case coverage can only be substantiated on the
#: detailed numerical-modelling route.
COVERAGE_REQUIRES_LEVEL_TWO = (
    "secondary-emission-yield-scatter",
    "electromagnetic-field-model-error",
)

#: Default margin policy, in decibel throughout.
DEFAULT_MARGIN_POLICY = {
    "base_margin_db": {LEVEL_ONE: 6.0, LEVEL_TWO: 4.0},
    "contribution_adder_db": {
        "manufacturing-tolerance-spread": 1.0,
        "secondary-emission-yield-scatter": 1.5,
        "electromagnetic-field-model-error": 1.0,
        "power-measurement-uncertainty": 0.5,
        "temperature-induced-gap-change": 0.5,
    },
    "equipment_type_adder_db": {
        "waveguide-passive-unit": 0.0,
        "coaxial-passive-unit": 0.5,
        "connector-and-harness-interface": 0.5,
        "antenna-feed-radiating-element": 1.0,
        "active-output-stage": 1.0,
    },
    "heritage_credit_db": {
        "new-design": 0.0,
        "modified-recurring-design": 0.5,
        "qualified-identical-design": 1.0,
    },
    "minimum_margin_db": 3.0,
}

#: Decibel comparison tolerance. The requirement is a sum of adders and the
#: achieved value a base-ten logarithm, so a case sitting exactly on its
#: requirement can land a few units in the last place either side; the
#: tolerance absorbs that without moving the engineering requirement.
MARGIN_TOLERANCE_DB = 1e-9


def _require_real(name, value):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    value = _require_real(name, value)
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    """Return value as a non-negative finite float or raise ValueError."""
    value = _require_real(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _policy_section(policy, key):
    """Resolve one section of the margin policy, defaulting section by section."""
    if policy is None:
        return DEFAULT_MARGIN_POLICY[key]
    if not isinstance(policy, dict):
        raise ValueError("margin policy must be a mapping, got %r" % (policy,))
    if key not in policy:
        return DEFAULT_MARGIN_POLICY[key]
    section = policy[key]
    if key == "minimum_margin_db":
        return _require_non_negative("minimum_margin_db", section)
    if not isinstance(section, dict):
        raise ValueError("margin policy section %r must be a mapping" % (key,))
    return section


def nominal_base_margin_db(level, policy=None):
    """Base analysis-margin owed by a design-analysis-level."""
    if level not in ANALYSIS_LEVELS:
        raise ValueError(
            "unrecognized design-analysis-level %r; expected one of %s"
            % (level, ", ".join(ANALYSIS_LEVELS))
        )
    table = _policy_section(policy, "base_margin_db")
    if level not in table:
        raise ValueError("margin policy declares no base value for %r" % (level,))
    return _require_non_negative("base margin for %s" % level, table[level])


def contribution_adder_db(contribution, policy=None):
    """Adder carried by one unbounded uncertainty contribution."""
    if contribution not in MARGIN_CONTRIBUTIONS:
        raise ValueError(
            "unrecognized contribution %r; expected one of %s"
            % (contribution, ", ".join(MARGIN_CONTRIBUTIONS))
        )
    table = _policy_section(policy, "contribution_adder_db")
    if contribution not in table:
        raise ValueError(
            "margin policy declares no adder for contribution %r" % (contribution,)
        )
    return _require_non_negative("adder for %s" % contribution, table[contribution])


def contribution_budget_db(coverage, level, policy=None):
    """Sum the adders of every contribution the worst-case model does not bound.

    ``coverage`` maps each contribution to a boolean: True when an explicit
    worst-case run bounds it. Every contribution needs a statement, and a
    coverage claim the level cannot support is rejected with its adder
    retained.
    """
    if level not in ANALYSIS_LEVELS:
        raise ValueError(
            "unrecognized design-analysis-level %r; expected one of %s"
            % (level, ", ".join(ANALYSIS_LEVELS))
        )
    if not isinstance(coverage, dict):
        raise ValueError("coverage must be a mapping, got %r" % (coverage,))
    unknown = [key for key in coverage if key not in MARGIN_CONTRIBUTIONS]
    if unknown:
        raise ValueError(
            "unrecognized contribution(s) in coverage: %s" % ", ".join(sorted(unknown))
        )
    missing = [c for c in MARGIN_CONTRIBUTIONS if c not in coverage]
    if missing:
        raise ValueError(
            "no coverage statement on record for: %s" % ", ".join(missing)
        )

    breakdown = {}
    rejected = []
    total = 0.0
    for contribution in MARGIN_CONTRIBUTIONS:
        claimed = coverage[contribution]
        if not isinstance(claimed, bool):
            raise ValueError(
                "coverage statement for %r must be a boolean, got %r"
                % (contribution, claimed)
            )
        bounded = claimed
        if claimed and level == LEVEL_ONE and contribution in COVERAGE_REQUIRES_LEVEL_TWO:
            bounded = False
            rejected.append(contribution)
        adder = 0.0 if bounded else contribution_adder_db(contribution, policy)
        breakdown[contribution] = adder
        total += adder
    return {
        "total_db": total,
        "breakdown": breakdown,
        "rejected_coverage_claims": rejected,
    }


def equipment_type_adder_db(equipment_type, policy=None):
    """Adder carried by the hardware category of the gap."""
    table = _policy_section(policy, "equipment_type_adder_db")
    if not isinstance(equipment_type, str):
        raise ValueError(
            "equipment type must be a string, got %r" % (equipment_type,)
        )
    key = equipment_type.strip().lower()
    if key not in table:
        raise ValueError(
            "unrecognized equipment type %r; expected one of %s"
            % (equipment_type, ", ".join(sorted(table)))
        )
    return _require_non_negative("equipment adder for %s" % key, table[key])


def heritage_credit_db(category, same_manufacturing_route=True, policy=None):
    """Credit returned by design heritage, withheld on a changed route.

    Returns a pair: the credit granted and a finding string (empty when the
    credit was granted as declared).
    """
    table = _policy_section(policy, "heritage_credit_db")
    if not isinstance(category, str):
        raise ValueError("heritage category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if key not in table:
        raise ValueError(
            "unrecognized heritage category %r; expected one of %s"
            % (category, ", ".join(sorted(table)))
        )
    if not isinstance(same_manufacturing_route, bool):
        raise ValueError(
            "same_manufacturing_route must be a boolean, got %r"
            % (same_manufacturing_route,)
        )
    declared = _require_non_negative("heritage credit for %s" % key, table[key])
    if declared > 0.0 and not same_manufacturing_route:
        return 0.0, (
            "heritage credit of %.2f decibel withheld: %r keeps the drawing "
            "but not the manufacturing route" % (declared, key)
        )
    return declared, ""


def required_analysis_margin_db(case, policy=None):
    """Assemble the analysis-margin one single-carrier case owes."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    level = case.get("analysis_level")
    base = nominal_base_margin_db(level, policy)
    budget = contribution_budget_db(case.get("coverage", {}), level, policy)
    equipment = equipment_type_adder_db(case.get("equipment_type"), policy)
    credit, credit_finding = heritage_credit_db(
        case.get("heritage", "new-design"),
        case.get("same_manufacturing_route", True),
        policy,
    )
    floor = _policy_section(policy, "minimum_margin_db")
    if isinstance(floor, dict):
        raise ValueError("minimum_margin_db must be a number, not a mapping")
    floor = _require_non_negative("minimum_margin_db", floor)

    raw = base + budget["total_db"] + equipment - credit
    if raw >= floor - MARGIN_TOLERANCE_DB:
        required = raw
        floor_applied = False
    else:
        required = floor
        floor_applied = True

    findings = []
    for contribution in budget["rejected_coverage_claims"]:
        findings.append(
            "worst-case coverage claimed for %s cannot be substantiated on "
            "the chart route; adder retained" % contribution
        )
    if credit_finding:
        findings.append(credit_finding)

    return {
        "analysis_level": level,
        "base_margin_db": base,
        "contribution_total_db": budget["total_db"],
        "contribution_breakdown": budget["breakdown"],
        "equipment_adder_db": equipment,
        "heritage_credit_db": credit,
        "assembled_margin_db": raw,
        "floor_db": floor,
        "floor_applied": floor_applied,
        "required_margin_db": required,
        "findings": findings,
    }


def achieved_analysis_margin_db(threshold_power_w, operating_power_w):
    """Decibel distance from the operating point up to the multipactor
    threshold."""
    threshold_power_w = _require_positive("threshold_power_w", threshold_power_w)
    operating_power_w = _require_positive("operating_power_w", operating_power_w)
    return 10.0 * math.log10(threshold_power_w / operating_power_w)


def power_limit_for_required_margin_w(threshold_power_w, required_margin_db):
    """Highest operating carrier-power that still holds the required margin."""
    threshold_power_w = _require_positive("threshold_power_w", threshold_power_w)
    required_margin_db = _require_non_negative("required_margin_db", required_margin_db)
    return threshold_power_w / (10.0 ** (required_margin_db / 10.0))


def assess_analysis_margin_case(case, policy=None):
    """Grade one case against its assembled analysis-margin requirement."""
    requirement = required_analysis_margin_db(case, policy)
    achieved = achieved_analysis_margin_db(
        case.get("threshold_power_w"), case.get("operating_power_w")
    )
    required = requirement["required_margin_db"]
    compliant = achieved >= required - MARGIN_TOLERANCE_DB
    shortfall = 0.0 if compliant else required - achieved
    findings = list(requirement["findings"])
    if not compliant:
        findings.append(
            "analysis-margin shortfall of %.3f decibel against the assembled "
            "requirement of %.3f decibel" % (shortfall, required)
        )
    record = dict(requirement)
    record.update(
        {
            "identifier": case.get("identifier", "unnamed-case"),
            "achieved_margin_db": achieved,
            "shortfall_db": shortfall,
            "allowed_power_w": power_limit_for_required_margin_w(
                case.get("threshold_power_w"), required
            ),
            "compliant": compliant,
            "findings": findings,
        }
    )
    return record


def summarize_margin_register(cases, policy=None):
    """Roll a unit's cases up into one analysis-margin register."""
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty list of mappings")
    records = [assess_analysis_margin_case(c, policy) for c in cases]
    non_compliant = [r["identifier"] for r in records if not r["compliant"]]
    floor_driven = [r["identifier"] for r in records if r["floor_applied"]]
    return {
        "case_count": len(records),
        "compliant_count": sum(1 for r in records if r["compliant"]),
        "non_compliant": non_compliant,
        "floor_driven": floor_driven,
        "worst_shortfall_db": max(r["shortfall_db"] for r in records),
        "highest_requirement_db": max(r["required_margin_db"] for r in records),
        "unit_compliant": not non_compliant,
        "records": records,
    }
