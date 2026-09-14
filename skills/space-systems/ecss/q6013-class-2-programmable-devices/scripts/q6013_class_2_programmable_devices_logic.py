"""Programmable device handling at the intermediate assurance class.

Anchor: ECSS-Q-ST-60-13C clause 5.6.4 (a one time programmable or a
reprogrammable device on an intermediate assurance part programme carries
handling, programming and verification controls of its own, and the controls
differ with how the configuration is held). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Categorise the declared device family. A part whose configuration can be
   written once, a part that rewrites into non-volatile storage, and a part
   whose configuration lives in volatile storage and is reloaded at every
   power-up are three different handling problems.
2. Derive the control set that category carries at the intermediate class: a
   baseline every programmable part shares, plus the controls specific to the
   category.
3. Name every required control the declared programming record leaves open.
4. For a reprogrammable part, compare the programming cycles already spent
   against the rated endurance derated by the declared fraction, treating an
   exact equality as within the allowance rather than loosening the fraction.
5. For a reprogrammable part, compare the declared configuration retention
   against the mission duration scaled by its margin factor, again absorbing
   the representation error at an exact equality.
6. For a one time part, treat a record reporting more than a single programming
   operation as a contradiction of the family it was declared under.
7. Return one verdict -- handling accepted, accepted with findings, or refused
   -- with the open controls, the cycle ratio, the retention margin and every
   finding behind it.
"""

import math

__all__ = [
    "DEVICE_FAMILIES",
    "ONE_TIME",
    "REPROGRAMMABLE_NON_VOLATILE",
    "REPROGRAMMABLE_VOLATILE",
    "BASELINE_CONTROLS",
    "CATEGORY_CONTROLS",
    "DEFAULT_HANDLING_POLICY",
    "RATIO_TOLERANCE",
    "HANDLING_ACCEPTED",
    "HANDLING_ACCEPTED_WITH_FINDINGS",
    "HANDLING_REFUSED",
    "programmability_category",
    "required_controls",
    "validate_handling_policy",
    "validate_control_list",
    "open_controls",
    "endurance_usage_ratio",
    "endurance_within_allowance",
    "required_retention_years",
    "retention_adequate",
    "assess_programmable_handling",
]

ONE_TIME = "one-time-programmable"
REPROGRAMMABLE_NON_VOLATILE = "reprogrammable-non-volatile"
REPROGRAMMABLE_VOLATILE = "reprogrammable-volatile"

# Declared device family to the handling category it falls in.
DEVICE_FAMILIES = {
    "antifuse-fpga": ONE_TIME,
    "fuse-link-prom": ONE_TIME,
    "otp-eprom": ONE_TIME,
    "flash-fpga": REPROGRAMMABLE_NON_VOLATILE,
    "eeprom-pld": REPROGRAMMABLE_NON_VOLATILE,
    "flash-microcontroller": REPROGRAMMABLE_NON_VOLATILE,
    "sram-fpga": REPROGRAMMABLE_VOLATILE,
    "sram-configured-pld": REPROGRAMMABLE_VOLATILE,
}

# Controls every programmable part carries whatever holds its configuration.
BASELINE_CONTROLS = (
    "programming-equipment-calibration",
    "configuration-identification",
    "post-programming-verification",
    "electrostatic-handling-control",
)

# Controls specific to how the configuration is held.
CATEGORY_CONTROLS = {
    ONE_TIME: (
        "pre-programming-blank-verification",
        "programming-yield-record",
        "no-reprogramming-after-acceptance",
    ),
    REPROGRAMMABLE_NON_VOLATILE: (
        "reprogramming-cycle-log",
        "configuration-retention-assessment",
        "verification-after-each-reprogram",
    ),
    REPROGRAMMABLE_VOLATILE: (
        "configuration-load-integrity-check",
        "configuration-scrubbing-provision",
        "verification-after-each-reprogram",
    ),
}

# A cycle or retention comparison is a ratio of two declared numbers. An exact
# equality can land a few units in the last place on the wrong side; absorb
# that here instead of softening the derating fraction or the margin factor.
RATIO_TOLERANCE = 1e-9

HANDLING_ACCEPTED = "handling-accepted"
HANDLING_ACCEPTED_WITH_FINDINGS = "handling-accepted-with-findings"
HANDLING_REFUSED = "handling-refused"

DEFAULT_HANDLING_POLICY = {
    # Share of the rated endurance a programme may spend before acceptance.
    "endurance_derating_fraction": 0.5,
    # Factor the mission duration is scaled by before retention is compared.
    "retention_margin_factor": 1.5,
    # Open controls tolerated before the record stops being a findings case.
    "max_open_controls": 1,
}


def programmability_category(family):
    """Return the handling category a declared device family falls in."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("device family must be a non-empty string")
    key = family.strip().lower()
    if key not in DEVICE_FAMILIES:
        raise ValueError(
            "unknown device family %r; declare one of %s"
            % (family, ", ".join(sorted(DEVICE_FAMILIES)))
        )
    return DEVICE_FAMILIES[key]


def required_controls(category):
    """Return the control set one handling category carries, in report order."""
    if not isinstance(category, str) or not category.strip():
        raise ValueError("category must be a non-empty string")
    key = category.strip().lower()
    if key not in CATEGORY_CONTROLS:
        raise ValueError(
            "unknown handling category %r; declare one of %s"
            % (category, ", ".join(sorted(CATEGORY_CONTROLS)))
        )
    return BASELINE_CONTROLS + CATEGORY_CONTROLS[key]


def validate_handling_policy(policy=None):
    """Return a complete handling policy, defaults filled in."""
    if policy is None:
        return dict(DEFAULT_HANDLING_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("handling policy must be a mapping")
    merged = dict(DEFAULT_HANDLING_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_HANDLING_POLICY:
            raise ValueError("unknown handling policy key %r" % (key,))
        merged[key] = value
    fraction = merged["endurance_derating_fraction"]
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
        raise ValueError("endurance_derating_fraction must be a real number")
    fraction = float(fraction)
    if not math.isfinite(fraction) or fraction <= 0.0 or fraction > 1.0:
        raise ValueError("endurance_derating_fraction must be finite and in 0..1")
    merged["endurance_derating_fraction"] = fraction
    factor = merged["retention_margin_factor"]
    if not isinstance(factor, (int, float)) or isinstance(factor, bool):
        raise ValueError("retention_margin_factor must be a real number")
    factor = float(factor)
    if not math.isfinite(factor) or factor < 1.0:
        raise ValueError("retention_margin_factor must be finite and at least 1.0")
    merged["retention_margin_factor"] = factor
    cap = merged["max_open_controls"]
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
        raise ValueError("max_open_controls must be a non-negative integer")
    return merged


def validate_control_list(controls, category, label):
    """Return a normalised, duplicate-free tuple of declared control names."""
    known = required_controls(category)
    if controls is None:
        return ()
    if isinstance(controls, str) or not isinstance(controls, (list, tuple)):
        raise ValueError("%s must be a sequence of control names" % label)
    seen = []
    for entry in controls:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("%s carries a non-string control name" % label)
        key = entry.strip().lower()
        if key not in known:
            raise ValueError(
                "%s names %r, which is not a control this category carries"
                % (label, entry)
            )
        if key in seen:
            raise ValueError("%s repeats control %r" % (label, key))
        seen.append(key)
    return tuple(name for name in known if name in seen)


def open_controls(category, declared):
    """Return the required controls a declared record leaves open."""
    present = validate_control_list(declared, category, "declared controls")
    return tuple(name for name in required_controls(category) if name not in present)


def endurance_usage_ratio(cycles_used, rated_endurance_cycles):
    """Return the share of the rated programming endurance already spent."""
    if not isinstance(cycles_used, int) or isinstance(cycles_used, bool):
        raise ValueError("cycles_used must be an integer")
    if cycles_used < 0:
        raise ValueError("cycles_used must be non-negative")
    if not isinstance(rated_endurance_cycles, int) or isinstance(
        rated_endurance_cycles, bool
    ):
        raise ValueError("rated_endurance_cycles must be an integer")
    if rated_endurance_cycles <= 0:
        raise ValueError("rated_endurance_cycles must be positive")
    return float(cycles_used) / float(rated_endurance_cycles)


def endurance_within_allowance(ratio, derating_fraction):
    """Return whether a spent-endurance share sits within its derated allowance."""
    for label, value in (("ratio", ratio), ("derating_fraction", derating_fraction)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    have = float(ratio)
    allowance = float(derating_fraction)
    return have < allowance or math.isclose(
        have, allowance, rel_tol=RATIO_TOLERANCE, abs_tol=RATIO_TOLERANCE
    )


def required_retention_years(mission_years, margin_factor):
    """Return the configuration retention a mission asks a device to hold."""
    for label, value in (("mission_years", mission_years),
                         ("margin_factor", margin_factor)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return float(mission_years) * float(margin_factor)


def retention_adequate(retention_years, mission_years, margin_factor):
    """Return whether declared retention reaches the scaled mission duration."""
    needed = required_retention_years(mission_years, margin_factor)
    if not isinstance(retention_years, (int, float)) or isinstance(
        retention_years, bool
    ):
        raise ValueError("retention_years must be a real number")
    have = float(retention_years)
    if not math.isfinite(have) or have <= 0.0:
        raise ValueError("retention_years must be positive and finite")
    return have > needed or math.isclose(
        have, needed, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    )


def assess_programmable_handling(case):
    """Run the clause 5.6.4 intermediate-class programmable handling assessment.

    case keys: family, optional declared_controls, optional
    programming_cycles_used, optional rated_endurance_cycles, optional
    retention_years, optional mission_years, optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "family" not in case:
        raise ValueError("case missing required key 'family'")
    settings = validate_handling_policy(case.get("policy"))
    category = programmability_category(case["family"])
    missing = open_controls(category, case.get("declared_controls"))

    findings = []
    for name in missing:
        findings.append(
            "%s is required for a %s part and the record leaves it open"
            % (name, category)
        )

    ratio = None
    endurance_ok = True
    retention_margin = None
    retention_ok = True
    cycles = case.get("programming_cycles_used")

    if category == ONE_TIME:
        if cycles is not None:
            if not isinstance(cycles, int) or isinstance(cycles, bool) or cycles < 0:
                raise ValueError("programming_cycles_used must be a non-negative integer")
            if cycles > 1:
                endurance_ok = False
                findings.append(
                    "a one time part reports %d programming operations, which "
                    "contradicts the family it was declared under" % cycles
                )
    else:
        rated = case.get("rated_endurance_cycles")
        if cycles is None or rated is None:
            raise ValueError(
                "a reprogrammable part needs 'programming_cycles_used' and "
                "'rated_endurance_cycles'"
            )
        ratio = endurance_usage_ratio(cycles, rated)
        endurance_ok = endurance_within_allowance(
            ratio, settings["endurance_derating_fraction"]
        )
        if not endurance_ok:
            findings.append(
                "programming endurance spent %.4f of the rated cycles against a "
                "derated allowance of %.4f"
                % (ratio, settings["endurance_derating_fraction"])
            )
        retention_years = case.get("retention_years")
        mission_years = case.get("mission_years")
        if retention_years is None or mission_years is None:
            raise ValueError(
                "a reprogrammable part needs 'retention_years' and 'mission_years'"
            )
        needed = required_retention_years(
            mission_years, settings["retention_margin_factor"]
        )
        retention_ok = retention_adequate(
            retention_years, mission_years, settings["retention_margin_factor"]
        )
        retention_margin = float(retention_years) / needed
        if not retention_ok:
            findings.append(
                "declared configuration retention %.4f years falls short of the "
                "scaled mission duration %.4f years"
                % (float(retention_years), needed)
            )

    over_cap = len(missing) > settings["max_open_controls"]
    if over_cap:
        findings.append(
            "%d required controls are open against an allowance of %d"
            % (len(missing), settings["max_open_controls"])
        )

    if not endurance_ok or not retention_ok or over_cap:
        verdict = HANDLING_REFUSED
    elif missing:
        verdict = HANDLING_ACCEPTED_WITH_FINDINGS
    else:
        verdict = HANDLING_ACCEPTED

    return {
        "category": category,
        "verdict": verdict,
        "required_controls": required_controls(category),
        "open_controls": missing,
        "endurance_usage_ratio": ratio,
        "endurance_within_allowance": endurance_ok,
        "retention_margin": retention_margin,
        "retention_adequate": retention_ok,
        "findings": findings,
    }
