"""Radiation verification of a sensitive lowest-assurance commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 6.3.8 (radiation verification testing of
sensitive commercial parts at the lowest assurance category, where the
verification may rest on thinner evidence than an irradiation of the flight
lot itself). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Triage the part for radiation sensitivity: a technology family in the
   sensitive register is sensitive whatever the dose, and any family becomes
   sensitive once the mission dose passes the screening threshold. A part that
   is neither owes nothing at this category.
2. Scale the mission dose into a required capability: multiplied by the
   declared radiation design margin, and multiplied again by the penalty the
   evidence tier carries, so thinner evidence has to clear a higher bar.
3. Compare the declared or tested total dose capability against that
   requirement, with a capability landing exactly on the requirement counted
   as meeting it.
4. Read the destructive single-event question in the same pass. A family that
   can be destroyed by a single particle is never waived on a total dose
   margin, and a missing threshold is a rejection rather than an unknown.
5. Return one verdict: not radiation sensitive, verified, lot radiation test
   required, evidence insufficient, or rejected, with every reason named.
"""

import math

__all__ = [
    "SENSITIVE_TECHNOLOGY_FAMILIES",
    "DESTRUCTIVE_SEE_FAMILIES",
    "EVIDENCE_TIER_PENALTY",
    "REPLACEABLE_EVIDENCE_TIERS",
    "DEFAULT_RADIATION_DESIGN_MARGIN",
    "DEFAULT_SENSITIVITY_THRESHOLD_KRAD",
    "DOSE_TOLERANCE",
    "radiation_sensitivity",
    "evidence_tier_penalty",
    "required_capability_krad",
    "total_dose_verdict",
    "destructive_see_status",
    "assess_class3_radiation_verification",
]

# Families whose response to accumulated dose is known to move enough that the
# question is asked whatever the mission dose turns out to be.
SENSITIVE_TECHNOLOGY_FAMILIES = (
    "cmos-digital-logic",
    "sram-memory",
    "flash-memory",
    "linear-bipolar",
    "optocoupler",
    "power-mosfet",
    "dc-dc-converter",
)

# Families where a single particle can destroy the part. A dose margin says
# nothing about this, so the check runs separately and is never waived.
DESTRUCTIVE_SEE_FAMILIES = (
    "cmos-digital-logic",
    "sram-memory",
    "power-mosfet",
    "dc-dc-converter",
)

# How much further a capability has to reach when the evidence behind it is
# not an irradiation of the lot that will fly.
EVIDENCE_TIER_PENALTY = {
    "flight-lot-irradiation": 1.0,
    "similar-lot-irradiation": 1.5,
    "manufacturer-declared-capability": 2.0,
}

# Tiers whose shortfall can be answered by testing the lot rather than by
# rejecting the part outright.
REPLACEABLE_EVIDENCE_TIERS = (
    "similar-lot-irradiation",
    "manufacturer-declared-capability",
)

DEFAULT_RADIATION_DESIGN_MARGIN = 2.0
DEFAULT_SENSITIVITY_THRESHOLD_KRAD = 1.0

# Dose and LET comparisons land on their limit exactly in the normal case;
# absorb representation error here rather than by moving the limit.
DOSE_TOLERANCE = 1e-9


def _positive(label, value):
    """Return value as a finite, strictly positive float."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _real(label, value):
    """Return value as a finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _non_negative(label, value):
    """Return value as a finite, non-negative float."""
    out = _real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _text(label, value):
    """Return a stripped, lower-cased, non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower()


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (label, value))
    return value


def _at_least(value, bound):
    """Return whether value reaches bound, counting an exact landing as reached."""
    return value > bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=DOSE_TOLERANCE)


def radiation_sensitivity(
    technology_family,
    mission_dose_krad,
    threshold_krad=DEFAULT_SENSITIVITY_THRESHOLD_KRAD,
    register=SENSITIVE_TECHNOLOGY_FAMILIES,
):
    """Return whether the part is treated as radiation sensitive at this category.

    Two independent routes into sensitivity: the technology family sits in the
    register, or the mission dose reaches the screening threshold. Either one
    is enough.
    """
    family = _text("technology_family", technology_family)
    dose = _non_negative("mission_dose_krad", mission_dose_krad)
    threshold = _positive("threshold_krad", threshold_krad)
    names = {_text("register entry", item) for item in register}
    in_register = family in names
    dose_reaches_threshold = _at_least(dose, threshold)
    return {
        "technology_family": family,
        "mission_dose_krad": dose,
        "threshold_krad": threshold,
        "in_register": in_register,
        "dose_reaches_threshold": dose_reaches_threshold,
        "sensitive": in_register or dose_reaches_threshold,
    }


def evidence_tier_penalty(tier, penalties=EVIDENCE_TIER_PENALTY):
    """Return the multiplier the named evidence tier carries."""
    name = _text("evidence tier", tier)
    table = {_text("penalty key", key): _positive("penalty[%s]" % key, value)
             for key, value in penalties.items()}
    if name not in table:
        raise ValueError(
            "unknown evidence tier %r; known tiers are %s"
            % (tier, ", ".join(sorted(table)))
        )
    if table[name] < 1.0:
        raise ValueError("evidence tier penalty must be at least 1.0, got %g" % table[name])
    return table[name]


def required_capability_krad(
    mission_dose_krad, design_margin=DEFAULT_RADIATION_DESIGN_MARGIN, tier="flight-lot-irradiation"
):
    """Return the total dose capability the part has to reach.

    Mission dose multiplied by the declared radiation design margin and again
    by the penalty the evidence tier carries. Plain multiplication only, so
    the same inputs give the same requirement on every platform.
    """
    dose = _non_negative("mission_dose_krad", mission_dose_krad)
    margin = _positive("design_margin", design_margin)
    if margin < 1.0:
        raise ValueError("design_margin must be at least 1.0, got %g" % margin)
    penalty = evidence_tier_penalty(tier)
    return {
        "mission_dose_krad": dose,
        "design_margin": margin,
        "evidence_tier": _text("evidence tier", tier),
        "evidence_penalty": penalty,
        "required_krad": dose * margin * penalty,
    }


def total_dose_verdict(capability_krad, required_krad):
    """Return whether a declared or tested capability meets the requirement.

    A capability landing exactly on the requirement meets it; the tolerance
    absorbs representation error only and does not move the requirement.
    """
    capability = _non_negative("capability_krad", capability_krad)
    required = _non_negative("required_krad", required_krad)
    return {
        "capability_krad": capability,
        "required_krad": required,
        "shortfall_krad": max(0.0, required - capability),
        "meets_requirement": _at_least(capability, required),
    }


def destructive_see_status(
    technology_family,
    data_available,
    threshold_let=None,
    environment_let=None,
    families=DESTRUCTIVE_SEE_FAMILIES,
):
    """Return the destructive single-event status of the part.

    A family outside the destructive register is cleared without data. A
    family inside it is cleared only on a threshold that reaches the
    environment, and a missing threshold is a refusal rather than an unknown.
    """
    family = _text("technology_family", technology_family)
    available = _flag("data_available", data_available)
    names = {_text("destructive family", item) for item in families}
    susceptible = family in names
    if not susceptible:
        return {
            "technology_family": family,
            "susceptible": False,
            "data_available": available,
            "threshold_let": None,
            "environment_let": None,
            "cleared": True,
            "reason": "family is not in the destructive single-event register",
        }
    if not available:
        return {
            "technology_family": family,
            "susceptible": True,
            "data_available": False,
            "threshold_let": None,
            "environment_let": None,
            "cleared": False,
            "reason": "no destructive single-event data for a susceptible family",
        }
    if threshold_let is None or environment_let is None:
        raise ValueError(
            "threshold_let and environment_let are required when data_available is True"
        )
    threshold = _non_negative("threshold_let", threshold_let)
    environment = _non_negative("environment_let", environment_let)
    cleared = _at_least(threshold, environment)
    return {
        "technology_family": family,
        "susceptible": True,
        "data_available": True,
        "threshold_let": threshold,
        "environment_let": environment,
        "margin_let": threshold - environment,
        "cleared": cleared,
        "reason": (
            "threshold reaches the environment"
            if cleared
            else "threshold %.3f does not reach the environment %.3f" % (threshold, environment)
        ),
    }


def assess_class3_radiation_verification(spec):
    """Run the full clause 6.3.8 radiation verification of one part.

    spec keys: technology_family, mission_dose_krad, evidence_tier,
    capability_krad, see_data_available, and optional design_margin,
    sensitivity_threshold_krad, see_threshold_let and see_environment_let.
    The evidence tier may be given as "none" when no radiation evidence at all
    was offered.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "technology_family",
        "mission_dose_krad",
        "evidence_tier",
        "capability_krad",
        "see_data_available",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    sensitivity = radiation_sensitivity(
        spec["technology_family"],
        spec["mission_dose_krad"],
        spec.get("sensitivity_threshold_krad", DEFAULT_SENSITIVITY_THRESHOLD_KRAD),
    )
    tier = _text("evidence_tier", spec["evidence_tier"])
    findings = []
    if not sensitivity["sensitive"]:
        return {
            "sensitivity": sensitivity,
            "evidence_tier": tier,
            "requirement": None,
            "total_dose": None,
            "destructive_see": None,
            "accepted": True,
            "verdict": "not-radiation-sensitive",
            "findings": [],
        }
    see = destructive_see_status(
        spec["technology_family"],
        spec["see_data_available"],
        spec.get("see_threshold_let"),
        spec.get("see_environment_let"),
    )
    if not see["cleared"]:
        findings.append("destructive single-event check not cleared: %s" % see["reason"])
    if tier == "none":
        findings.append("no radiation evidence was offered for a sensitive part")
        return {
            "sensitivity": sensitivity,
            "evidence_tier": tier,
            "requirement": None,
            "total_dose": None,
            "destructive_see": see,
            "accepted": False,
            "verdict": "rejected" if not see["cleared"] else "evidence-insufficient",
            "findings": findings,
        }
    requirement = required_capability_krad(
        sensitivity["mission_dose_krad"],
        spec.get("design_margin", DEFAULT_RADIATION_DESIGN_MARGIN),
        tier,
    )
    dose = total_dose_verdict(spec["capability_krad"], requirement["required_krad"])
    if not dose["meets_requirement"]:
        findings.append(
            "total dose capability %.3f krad falls %.3f krad short of the required %.3f krad"
            % (dose["capability_krad"], dose["shortfall_krad"], dose["required_krad"])
        )
    replaceable = {_text("replaceable tier", item) for item in REPLACEABLE_EVIDENCE_TIERS}
    if not see["cleared"]:
        verdict = "rejected"
    elif dose["meets_requirement"]:
        verdict = "verified"
    elif tier in replaceable:
        verdict = "lot-radiation-test-required"
    else:
        verdict = "rejected"
    return {
        "sensitivity": sensitivity,
        "evidence_tier": tier,
        "requirement": requirement,
        "total_dose": dose,
        "destructive_see": see,
        "accepted": verdict == "verified",
        "verdict": verdict,
        "findings": findings,
    }
