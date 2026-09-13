#!/usr/bin/env python3
"""Emission-yield sample cleanliness-policy conformance.

Anchor: ECSS-E-ST-20-01C clause 9.4.1.2 (referenced contamination-control
policy applied to emission-yield samples and to their environment).
Paraphrased into an implementable procedure; no standard text is reproduced.

Secondary-electron-emission yield is a surface property: an adsorbed or
settled overlayer changes the measured yield far more than the bulk
material does. The clause therefore ties the sample and every environment
it passes through to a declared contamination-control policy. This module
implements that check deterministically:

  * categorize each handling step of the chain (preparation, transfer,
    storage, mounting, measurement);
  * derive the cleanliness level the sample sensitivity demands and credit
    a purged or evacuated enclosure against the room level;
  * accrue settled-particle surface obscuration over the whole chain and
    compare it with the sample allowable-obscuration budget;
  * flag a contact step with no tooling control, an uncontrolled
    environment on a sensitive sample, and a missing policy reference or
    missing budget (an absent record is a finding, never a pass).

stdlib only, offline, deterministic.
"""

import math

HANDLING_FAMILIES = (
    "preparation",
    "transfer",
    "storage",
    "mounting",
    "measurement",
)

_FAMILY_KEYWORDS = {
    "preparation": ("clean", "solvent", "rinse", "bake", "polish", "cut", "coat"),
    "transfer": ("transfer", "transport", "ship", "carry", "handover"),
    "storage": ("storage", "store", "desiccator", "cabinet", "dwell", "wait"),
    "mounting": ("mount", "fixture", "clamp", "holder", "bond", "wire"),
    "measurement": ("measure", "pump", "chamber", "irradiate", "scan", "beam"),
}

SENSITIVITY_REQUIRED_ISO_CLASS = {"high": 5, "moderate": 7, "low": 8}

# Deposition credit for an enclosure that is purged or evacuated: the
# sample sees a cleaner micro-environment than the surrounding room.
PURGE_FACTORS = {"none": 1.0, "dry-nitrogen": 0.1, "vacuum": 0.0}
PURGE_CLASS_CREDIT = {"none": 0, "dry-nitrogen": 1, "vacuum": 2}

TOOLING_CONTROLS = (
    "powder-free-gloves",
    "cleanroom-tweezers",
    "vacuum-wand",
    "dedicated-fixture",
)

ISO_CLASS_MIN = 1
ISO_CLASS_MAX = 9
UNCONTROLLED_EQUIVALENT_CLASS = 9
UNCONTROLLED_PENALTY = 10.0

# Still-air settling model, documented here so the result is reproducible:
# obscured fraction of surface area per 24 h at ISO 14644-1 class 5, with
# one decade per cleanliness class either side.
BASE_OBSCURATION_PERCENT_PER_DAY = 2.5e-4
HOURS_PER_DAY = 24.0
BUDGET_ABS_TOL = 1e-12
BUDGET_REL_TOL = 1e-9


def categorize_handling_step(step):
    """Return the handling family of one step of the sample chain.

    An explicit 'family' wins; otherwise the family is derived from the
    step name. A step that matches nothing stays uncategorized and is
    rejected -- it must not silently enter the obscuration accrual.
    """
    if not isinstance(step, dict):
        raise ValueError("handling step must be a mapping, got %r" % (type(step),))
    name = step.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("handling step needs a non-empty 'name'")
    declared = step.get("family")
    if declared is not None:
        if declared not in HANDLING_FAMILIES:
            raise ValueError(
                "step '%s' declares unknown family '%s'" % (name, declared)
            )
        return declared
    low = name.lower()
    for family in HANDLING_FAMILIES:
        for token in _FAMILY_KEYWORDS[family]:
            if token in low:
                return family
    raise ValueError("step '%s' is uncategorized: no handling family matches" % name)


def required_iso_class(sensitivity):
    """Cleanliness class demanded by the yield-sensitivity of the sample."""
    if sensitivity not in SENSITIVITY_REQUIRED_ISO_CLASS:
        raise ValueError(
            "unknown sample sensitivity '%r' (expected high/moderate/low)"
            % (sensitivity,)
        )
    return SENSITIVITY_REQUIRED_ISO_CLASS[sensitivity]


def validate_environment(env):
    """Normalize one environment record used by a handling step."""
    if not isinstance(env, dict):
        raise ValueError("environment must be a mapping, got %r" % (type(env),))
    uncontrolled = bool(env.get("uncontrolled", False))
    purge = env.get("purge", "none")
    if purge not in PURGE_FACTORS:
        raise ValueError("unknown purge medium '%r'" % (purge,))
    if uncontrolled:
        iso_class = UNCONTROLLED_EQUIVALENT_CLASS
    else:
        iso_class = env.get("iso_class")
        if isinstance(iso_class, bool) or not isinstance(iso_class, int):
            raise ValueError("environment needs an integer 'iso_class' 1-9")
        if not ISO_CLASS_MIN <= iso_class <= ISO_CLASS_MAX:
            raise ValueError("iso_class %d outside 1-9" % iso_class)
    return {
        "id": env.get("id", "unnamed-environment"),
        "iso_class": iso_class,
        "purge": purge,
        "uncontrolled": uncontrolled,
    }


def effective_iso_class(env):
    """Class actually seen by the sample after purge/evacuation credit."""
    norm = validate_environment(env)
    if norm["uncontrolled"]:
        return UNCONTROLLED_EQUIVALENT_CLASS
    credited = norm["iso_class"] - PURGE_CLASS_CREDIT[norm["purge"]]
    return max(ISO_CLASS_MIN, credited)


def obscuration_rate_percent_per_day(iso_class, purge="none", uncontrolled=False):
    """Settled-particle area obscuration accrued per 24 h of exposure."""
    if isinstance(iso_class, bool) or not isinstance(iso_class, int):
        raise ValueError("iso_class must be an integer 1-9")
    if not ISO_CLASS_MIN <= iso_class <= ISO_CLASS_MAX:
        raise ValueError("iso_class %d outside 1-9" % iso_class)
    if purge not in PURGE_FACTORS:
        raise ValueError("unknown purge medium '%r'" % (purge,))
    rate = BASE_OBSCURATION_PERCENT_PER_DAY * (10.0 ** (iso_class - 5))
    rate *= PURGE_FACTORS[purge]
    if uncontrolled:
        rate *= UNCONTROLLED_PENALTY
    return rate


def step_obscuration_percent(step):
    """Obscuration contributed by one handling step of the chain."""
    categorize_handling_step(step)
    duration = step.get("duration_h")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise ValueError("step '%s' needs numeric 'duration_h'" % step.get("name"))
    if not math.isfinite(duration) or duration < 0.0:
        raise ValueError(
            "step '%s' duration_h must be finite and non-negative" % step.get("name")
        )
    env = validate_environment(step.get("environment", {}))
    rate = obscuration_rate_percent_per_day(
        env["iso_class"], env["purge"], env["uncontrolled"]
    )
    return rate * (float(duration) / HOURS_PER_DAY)


def accrued_obscuration_percent(steps):
    """Total obscuration accrued across an ordered handling chain."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("handling chain must be a non-empty sequence of steps")
    return math.fsum(step_obscuration_percent(s) for s in steps)


def check_environment_conformance(steps, sensitivity):
    """Findings for steps whose environment is dirtier than the policy allows."""
    required = required_iso_class(sensitivity)
    findings = []
    for step in steps:
        env = validate_environment(step.get("environment", {}))
        seen = effective_iso_class(step.get("environment", {}))
        if env["uncontrolled"]:
            findings.append(
                {
                    "code": "uncontrolled-environment",
                    "step": step.get("name"),
                    "detail": "step runs in an environment with no cleanliness"
                    " control on record",
                }
            )
        elif seen > required:
            findings.append(
                {
                    "code": "environment-below-required-class",
                    "step": step.get("name"),
                    "detail": "effective ISO class %d is dirtier than the"
                    " required class %d" % (seen, required),
                }
            )
    return findings


def check_contact_controls(steps):
    """Findings for contact steps with no declared tooling control."""
    findings = []
    for step in steps:
        if not step.get("contact", False):
            continue
        control = step.get("tooling_control")
        if control is None or (isinstance(control, str) and not control.strip()):
            findings.append(
                {
                    "code": "contact-without-tooling-control",
                    "step": step.get("name"),
                    "detail": "contact step declares no tooling control",
                }
            )
            continue
        if control not in TOOLING_CONTROLS:
            raise ValueError(
                "step '%s' declares unknown tooling control '%r'"
                % (step.get("name"), control)
            )
    return findings


def assess_sample_cleanliness_policy(sample):
    """Full clause 9.4.1.2 conformance report for one emission-yield sample."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping, got %r" % (type(sample),))
    sample_id = sample.get("id")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("sample needs a non-empty 'id'")
    sensitivity = sample.get("sensitivity")
    required = required_iso_class(sensitivity)
    steps = sample.get("steps")
    accrued = accrued_obscuration_percent(steps)

    findings = []
    policy = sample.get("policy_reference")
    if policy is None or (isinstance(policy, str) and not policy.strip()):
        findings.append(
            {
                "code": "policy-reference-missing",
                "step": None,
                "detail": "no contamination-control policy is referenced for"
                " this sample",
            }
        )

    budget = sample.get("allowable_obscuration_percent")
    if budget is None:
        findings.append(
            {
                "code": "obscuration-budget-not-on-record",
                "step": None,
                "detail": "allowable obscuration was never captured; an unset"
                " budget is a finding, not a pass",
            }
        )
    else:
        if isinstance(budget, bool) or not isinstance(budget, (int, float)):
            raise ValueError("allowable_obscuration_percent must be numeric")
        if not math.isfinite(budget) or budget <= 0.0:
            raise ValueError("allowable_obscuration_percent must be positive")
        over = accrued > budget and not math.isclose(
            accrued, float(budget), rel_tol=BUDGET_REL_TOL, abs_tol=BUDGET_ABS_TOL
        )
        if over:
            findings.append(
                {
                    "code": "obscuration-budget-exceeded",
                    "step": None,
                    "detail": "accrued %.6g%% exceeds allowable %.6g%%"
                    % (accrued, budget),
                }
            )

    findings.extend(check_environment_conformance(steps, sensitivity))
    findings.extend(check_contact_controls(steps))

    families = {}
    for step in steps:
        family = categorize_handling_step(step)
        families[family] = families.get(family, 0) + 1

    return {
        "sample": sample_id,
        "sensitivity": sensitivity,
        "required_iso_class": required,
        "step_families": families,
        "accrued_obscuration_percent": accrued,
        "allowable_obscuration_percent": budget,
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not findings,
    }
