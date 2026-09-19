"""General mechanical sizing of a mechanism part.

Anchor: ECSS-E-ST-33-01C clause 4.7.5.1 (parts are designed to meet the
required mechanical performance and to withstand all the environments
specified for them, over the design lifetime). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn each load case into a stress state on the chosen section: axial,
   bending and shear, combined into a von Mises value so one number can be
   graded against one allowable.
2. Knock the material allowable down for the environments the part actually
   sees -- temperature, ageing, radiation, surface condition -- before any
   margin is taken, so the environment is in the allowable and not in a
   second, invisible factor.
3. Take yield and ultimate margins separately, each against its own safety
   factor, because the two factors differ and the governing one is not
   always the same case.
4. Accumulate Miner damage over the mission load spectrum against a log-log
   S-N line, so a part with comfortable static margins is still graded for
   the lifetime the clause asks about.
5. Grade the stiffness requirement, since a part can be strong enough and
   still fail its first-mode allocation.
6. Name the governing load case and the governing check, so the design action
   is attached to something.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "KNOCKDOWN_KEYS",
    "axial_stress_pa",
    "bending_stress_pa",
    "shear_stress_pa",
    "von_mises_stress_pa",
    "knocked_down_allowable_pa",
    "margin_of_safety",
    "allowable_cycles",
    "miner_damage",
    "first_mode_margin",
    "assess_part_sizing",
]

# Margins are ratios of measured quantities; an exact zero margin can land a
# few ULPs on either side. Absorb the representation error here rather than by
# relaxing a safety factor.
MARGIN_TOLERANCE = 1e-12

# The environments a mechanism part allowable is knocked down for.
KNOCKDOWN_KEYS = (
    "temperature",
    "ageing",
    "radiation",
    "surface-condition",
)


def _require_real(label, value):
    """Return value as a finite float, refusing anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(label, value):
    """Return value as a strictly positive float."""
    out = _require_real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _require_non_negative(label, value):
    """Return value as a non-negative float."""
    out = _require_real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def axial_stress_pa(axial_load_n, area_m2):
    """Return the direct stress an axial load leaves on a section."""
    load = _require_real("axial_load_n", axial_load_n)
    area = _require_positive("area_m2", area_m2)
    return load / area


def bending_stress_pa(bending_moment_nm, section_modulus_m3):
    """Return the extreme-fibre bending stress on a section."""
    moment = _require_real("bending_moment_nm", bending_moment_nm)
    modulus = _require_positive("section_modulus_m3", section_modulus_m3)
    return moment / modulus


def shear_stress_pa(shear_load_n, shear_area_m2):
    """Return the average shear stress on the shear-carrying area."""
    load = _require_real("shear_load_n", shear_load_n)
    area = _require_positive("shear_area_m2", shear_area_m2)
    return load / area


def von_mises_stress_pa(normal_stress_pa, shear_stress_value_pa=0.0):
    """Combine a normal and a shear stress into one von Mises value."""
    normal = _require_real("normal_stress_pa", normal_stress_pa)
    shear = _require_real("shear_stress_value_pa", shear_stress_value_pa)
    return math.sqrt(normal * normal + 3.0 * shear * shear)


def knocked_down_allowable_pa(allowable_pa, knockdowns=None):
    """Return the material allowable after every environment knockdown.

    A knockdown factor above unity would make an environment strengthen the
    part and is refused; an unrecognised environment name is refused rather
    than dropped silently.
    """
    allowable = _require_positive("allowable_pa", allowable_pa)
    if knockdowns is None:
        return allowable
    if not isinstance(knockdowns, dict):
        raise ValueError("knockdowns must be a mapping of environment to factor")
    out = allowable
    for name, factor in knockdowns.items():
        if name not in KNOCKDOWN_KEYS:
            raise ValueError(
                "unknown environment %r; expected one of %s"
                % (name, ", ".join(KNOCKDOWN_KEYS))
            )
        value = _require_positive("knockdown %r" % (name,), factor)
        if value > 1.0:
            raise ValueError(
                "knockdown %r is %g; an environment cannot raise a material allowable"
                % (name, value)
            )
        out *= value
    return out


def margin_of_safety(allowable_pa, applied_pa, safety_factor):
    """Return the margin of safety, allowable / (applied * factor) - 1."""
    allowable = _require_positive("allowable_pa", allowable_pa)
    applied = _require_positive("applied_pa", applied_pa)
    factor = _require_positive("safety_factor", safety_factor)
    if factor < 1.0:
        raise ValueError("safety_factor must be at least 1.0, got %g" % factor)
    return allowable / (applied * factor) - 1.0


def allowable_cycles(stress_pa, reference_stress_pa, reference_cycles, exponent):
    """Return the allowable cycles at a stress on a log-log S-N line."""
    stress = _require_positive("stress_pa", stress_pa)
    reference_stress = _require_positive("reference_stress_pa", reference_stress_pa)
    cycles = _require_positive("reference_cycles", reference_cycles)
    slope = _require_positive("exponent", exponent)
    return cycles * (reference_stress / stress) ** slope


def miner_damage(spectrum, reference_stress_pa, reference_cycles, exponent):
    """Return the cumulative damage a mission load spectrum accumulates."""
    if not isinstance(spectrum, (list, tuple)) or not spectrum:
        raise ValueError("spectrum must be a non-empty sequence of blocks")
    damage = 0.0
    for index, block in enumerate(spectrum):
        if not isinstance(block, dict):
            raise ValueError("spectrum[%d] must be a mapping" % index)
        for key in ("stress_pa", "cycles"):
            if key not in block:
                raise ValueError("spectrum[%d] missing '%s'" % (index, key))
        applied = _require_non_negative("spectrum[%d] cycles" % index, block["cycles"])
        allowed = allowable_cycles(
            block["stress_pa"], reference_stress_pa, reference_cycles, exponent
        )
        damage += applied / allowed
    return damage


def first_mode_margin(achieved_hz, required_hz):
    """Return the fractional margin of a first mode over its requirement."""
    achieved = _require_positive("achieved_hz", achieved_hz)
    required = _require_positive("required_hz", required_hz)
    return achieved / required - 1.0


def _margin_ok(value):
    """Return True when a margin is non-negative within the named tolerance."""
    return value > 0.0 or math.isclose(value, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)


def assess_part_sizing(spec):
    """Run the full clause 4.7.5.1 part sizing assessment.

    spec keys: area_m2, section_modulus_m3, shear_area_m2, load_cases (list of
    {name, axial_load_n, bending_moment_nm, shear_load_n}), yield_allowable_pa,
    ultimate_allowable_pa, yield_factor, ultimate_factor; optional knockdowns,
    spectrum, reference_stress_pa, reference_cycles, sn_exponent, damage_limit,
    first_mode_hz, required_first_mode_hz.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "area_m2",
        "section_modulus_m3",
        "shear_area_m2",
        "load_cases",
        "yield_allowable_pa",
        "ultimate_allowable_pa",
        "yield_factor",
        "ultimate_factor",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    knockdowns = spec.get("knockdowns")
    yield_allowable = knocked_down_allowable_pa(spec["yield_allowable_pa"], knockdowns)
    ultimate_allowable = knocked_down_allowable_pa(
        spec["ultimate_allowable_pa"], knockdowns
    )
    if ultimate_allowable < yield_allowable:
        raise ValueError(
            "ultimate allowable %g Pa is below the yield allowable %g Pa"
            % (ultimate_allowable, yield_allowable)
        )

    cases = spec["load_cases"]
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("load_cases must be a non-empty sequence")

    findings = []
    records = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError("load_cases[%d] must be a mapping" % index)
        for key in ("name", "axial_load_n", "bending_moment_nm", "shear_load_n"):
            if key not in case:
                raise ValueError("load_cases[%d] missing '%s'" % (index, key))
        normal = (
            axial_stress_pa(case["axial_load_n"], spec["area_m2"])
            + bending_stress_pa(case["bending_moment_nm"], spec["section_modulus_m3"])
        )
        shear = shear_stress_pa(case["shear_load_n"], spec["shear_area_m2"])
        equivalent = von_mises_stress_pa(normal, shear)
        if equivalent <= 0.0:
            raise ValueError(
                "load_cases[%d] '%s' produces no stress; it is not a load case"
                % (index, case["name"])
            )
        yield_margin = margin_of_safety(yield_allowable, equivalent, spec["yield_factor"])
        ultimate_margin = margin_of_safety(
            ultimate_allowable, equivalent, spec["ultimate_factor"]
        )
        record = {
            "name": case["name"],
            "normal_stress_pa": normal,
            "shear_stress_pa": shear,
            "von_mises_stress_pa": equivalent,
            "yield_margin_of_safety": yield_margin,
            "ultimate_margin_of_safety": ultimate_margin,
        }
        records.append(record)
        if not _margin_ok(yield_margin):
            findings.append(
                "case '%s' yield margin of safety is %+.3f" % (record["name"], yield_margin)
            )
        if not _margin_ok(ultimate_margin):
            findings.append(
                "case '%s' ultimate margin of safety is %+.3f"
                % (record["name"], ultimate_margin)
            )

    damage = None
    if "spectrum" in spec:
        for key in ("reference_stress_pa", "reference_cycles", "sn_exponent"):
            if key not in spec:
                raise ValueError("a fatigue check needs '%s' alongside 'spectrum'" % key)
        damage = miner_damage(
            spec["spectrum"], spec["reference_stress_pa"], spec["reference_cycles"],
            spec["sn_exponent"],
        )
        limit = _require_positive("damage_limit", spec.get("damage_limit", 0.5))
        if damage > limit and not math.isclose(damage, limit, rel_tol=1e-12, abs_tol=0.0):
            findings.append(
                "cumulative damage over the mission spectrum is %.4g against a %.4g "
                "limit" % (damage, limit)
            )

    stiffness_margin = None
    if "first_mode_hz" in spec or "required_first_mode_hz" in spec:
        if "first_mode_hz" not in spec or "required_first_mode_hz" not in spec:
            raise ValueError(
                "a stiffness check needs both first_mode_hz and required_first_mode_hz"
            )
        stiffness_margin = first_mode_margin(
            spec["first_mode_hz"], spec["required_first_mode_hz"]
        )
        if not _margin_ok(stiffness_margin):
            findings.append(
                "first mode is %.4g Hz against a %.4g Hz requirement"
                % (float(spec["first_mode_hz"]), float(spec["required_first_mode_hz"]))
            )

    governing_case = min(
        records,
        key=lambda r: min(r["yield_margin_of_safety"], r["ultimate_margin_of_safety"]),
    )
    if governing_case["yield_margin_of_safety"] <= governing_case["ultimate_margin_of_safety"]:
        governing_check = "yield"
        worst = governing_case["yield_margin_of_safety"]
    else:
        governing_check = "ultimate"
        worst = governing_case["ultimate_margin_of_safety"]

    return {
        "yield_allowable_pa": yield_allowable,
        "ultimate_allowable_pa": ultimate_allowable,
        "load_cases": records,
        "governing_case": governing_case["name"],
        "governing_check": governing_check,
        "worst_margin_of_safety": worst,
        "cumulative_damage": damage,
        "first_mode_margin": stiffness_margin,
        "compliant": not findings,
        "findings": findings,
    }
