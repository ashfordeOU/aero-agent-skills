#!/usr/bin/env python3
"""Additional provisions for class 2 parts at high voltage and high power.

Anchor: ECSS-Q-ST-60C clause 5.6.7 (provisions a class 2 EEE part owes over
and above the ordinary class 2 rules when it is applied at high voltage or in
a high power microwave chain). Paraphrased into an implementable procedure; no
standard text is reproduced.

High voltage use changes what a rating buys. The part is still a class 2 part
and still owes everything class 2 asks, but the application adds a second set
of questions the ordinary rules never put: how much of the rating the working
voltage occupies, how close the electrode gap sits to gas breakdown at the
pressure the hardware actually sees, whether the insulating surface is long
enough to stop a track forming across it, and — in a microwave chain — whether
the gap and the frequency put the stage inside the band where a resonant
electron avalanche can build.

Procedure implemented here
--------------------------
1. Decide whether the application is admissible at all: a working voltage above
   the part's own rating is not a derating question.
2. Take the voltage utilisation against the class 2 limit.
3. Resolve the gas breakdown voltage across the electrode gap at the ambient
   pressure, and take the margin the working voltage leaves against it.
4. Derive the clearance and creepage the working voltage calls for at the
   surface condition, and name any shortfall.
5. For a microwave chain, take the frequency-gap product, group it against the
   susceptibility band, and take the peak power utilisation.
6. Assemble the provisions the application owes, compare them with what is
   held, and return one disposition in precedence order.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "ENCLOSURE_FORMS",
    "SURFACE_CONDITIONS",
    "MULTIPACTION_BANDS",
    "DEFAULT_HIGH_VOLTAGE_POLICY",
    "PASCHEN_AIR_A",
    "PASCHEN_AIR_B",
    "PROVISIONS_SATISFIED",
    "PROVISIONS_OUTSTANDING",
    "DESIGN_NONCONFORMING",
    "APPLICATION_NOT_ADMISSIBLE",
    "validate_high_voltage_policy",
    "validate_high_voltage_case",
    "voltage_utilisation",
    "paschen_breakdown_voltage_v",
    "paschen_margin",
    "required_clearance_mm",
    "required_creepage_mm",
    "surface_shortfalls_mm",
    "multipaction_fd_product_ghz_mm",
    "multipaction_band",
    "microwave_power_utilisation",
    "required_provisions",
    "assess_class2_high_voltage",
]

ENCLOSURE_FORMS = (
    "open-to-ambient",
    "vented-enclosure",
    "hermetically-sealed",
    "sealed-unvented",
)

# Multiplier on the creepage a clean surface would need. A conformal coat buys
# surface; a contaminated or outgassing surface spends it.
SURFACE_CONDITIONS = {
    "conformally-coated": 0.7,
    "clean-uncoated": 1.0,
    "contamination-exposed": 1.6,
}

# Frequency-gap product in GHz-mm, ascending; the first band the product falls
# at or below names the susceptibility grouping.
MULTIPACTION_BANDS = (
    (10.0, "multipaction-deep-susceptibility"),
    (30.0, "multipaction-susceptibility-band"),
    (100.0, "multipaction-marginal-band"),
    (float("inf"), "multipaction-above-susceptibility-band"),
)

# Townsend coefficients for air, pressure in torr and gap in centimetres.
PASCHEN_AIR_A = 15.0
PASCHEN_AIR_B = 365.0

DEFAULT_HIGH_VOLTAGE_POLICY = {
    # Working voltage above which the additional provisions attach at all.
    "high_voltage_threshold_v": 100.0,
    # Working voltage above which partial discharge measurement attaches.
    "partial_discharge_threshold_v": 500.0,
    # Share of the part rating the working voltage may occupy at class 2.
    "max_voltage_utilisation": 0.6,
    # Ratio of gas breakdown voltage to working voltage demanded.
    "min_paschen_margin": 2.0,
    # Clearance through air demanded, per kilovolt of working voltage.
    "clearance_mm_per_kv": 1.0,
    # Creepage along the surface demanded, per kilovolt of working voltage.
    "creepage_mm_per_kv": 2.5,
    # Share of rated peak power a high power microwave stage may draw.
    "max_microwave_power_utilisation": 0.5,
    # Whether a sealed cavity with no vent path is a design finding.
    "require_vent_path": True,
}

PROVISIONS_SATISFIED = "class-2-high-voltage-provisions-satisfied"
PROVISIONS_OUTSTANDING = "class-2-high-voltage-provisions-outstanding"
DESIGN_NONCONFORMING = "class-2-high-voltage-design-nonconforming"
APPLICATION_NOT_ADMISSIBLE = "class-2-high-voltage-application-not-admissible"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_high_voltage_policy(policy=None):
    """Return a complete class 2 high voltage policy with defaults filled in."""
    if policy is None:
        return dict(DEFAULT_HIGH_VOLTAGE_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("high voltage policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_HIGH_VOLTAGE_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_HIGH_VOLTAGE_POLICY:
            raise ValueError("unknown high voltage policy key %r" % (key,))
        merged[key] = value
    _require_positive("high_voltage_threshold_v", merged["high_voltage_threshold_v"])
    _require_positive(
        "partial_discharge_threshold_v", merged["partial_discharge_threshold_v"]
    )
    utilisation = _require_positive(
        "max_voltage_utilisation", merged["max_voltage_utilisation"]
    )
    if utilisation > 1.0:
        raise ValueError(
            "max_voltage_utilisation must not exceed 1.0, got %r" % (utilisation,)
        )
    margin = _require_number("min_paschen_margin", merged["min_paschen_margin"])
    if margin < 1.0:
        raise ValueError(
            "min_paschen_margin must be at least 1.0, got %r" % (margin,)
        )
    _require_positive("clearance_mm_per_kv", merged["clearance_mm_per_kv"])
    _require_positive("creepage_mm_per_kv", merged["creepage_mm_per_kv"])
    power = _require_positive(
        "max_microwave_power_utilisation", merged["max_microwave_power_utilisation"]
    )
    if power > 1.0:
        raise ValueError(
            "max_microwave_power_utilisation must not exceed 1.0, got %r" % (power,)
        )
    if not isinstance(merged["require_vent_path"], bool):
        raise ValueError("require_vent_path must be a boolean")
    return merged


def voltage_utilisation(working_voltage_v, rated_voltage_v):
    """Share of the part rating the working voltage occupies."""
    working = _require_non_negative("working_voltage_v", working_voltage_v)
    rated = _require_positive("rated_voltage_v", rated_voltage_v)
    return working / rated


def paschen_breakdown_voltage_v(
    pressure_torr, gap_cm, secondary_emission_coefficient=0.01
):
    """Gas breakdown voltage across a uniform gap, from the Townsend form.

    The pressure-gap product must sit on the right of the left-hand asymptote,
    where the denominator is still positive; below it the discharge cannot be
    sustained and the expression has no root, which is a different statement
    from a high breakdown voltage and is reported as such.
    """
    pressure = _require_positive("pressure_torr", pressure_torr)
    gap = _require_positive("gap_cm", gap_cm)
    gamma = _require_positive(
        "secondary_emission_coefficient", secondary_emission_coefficient
    )
    product = pressure * gap
    sustain = math.log(1.0 + 1.0 / gamma)
    denominator = math.log(PASCHEN_AIR_A * product) - math.log(sustain)
    if denominator <= 0.0:
        raise ValueError(
            "pressure-gap product %g torr cm sits left of the sustaining branch"
            % product
        )
    return PASCHEN_AIR_B * product / denominator


def paschen_margin(breakdown_voltage_v, working_voltage_v):
    """Ratio of gas breakdown voltage to the working voltage across the gap."""
    breakdown = _require_positive("breakdown_voltage_v", breakdown_voltage_v)
    working = _require_positive("working_voltage_v", working_voltage_v)
    return breakdown / working


def required_clearance_mm(working_voltage_v, policy=None):
    """Clearance through air the working voltage calls for."""
    working = _require_non_negative("working_voltage_v", working_voltage_v)
    resolved = validate_high_voltage_policy(policy)
    return working / 1000.0 * resolved["clearance_mm_per_kv"]


def required_creepage_mm(working_voltage_v, surface_condition, policy=None):
    """Creepage along the surface the working voltage and surface call for."""
    working = _require_non_negative("working_voltage_v", working_voltage_v)
    if surface_condition not in SURFACE_CONDITIONS:
        raise ValueError(
            "surface_condition must be one of %s, got %r"
            % (", ".join(sorted(SURFACE_CONDITIONS)), surface_condition)
        )
    resolved = validate_high_voltage_policy(policy)
    return (
        working
        / 1000.0
        * resolved["creepage_mm_per_kv"]
        * SURFACE_CONDITIONS[surface_condition]
    )


def surface_shortfalls_mm(
    working_voltage_v,
    surface_condition,
    clearance_mm,
    creepage_mm,
    policy=None,
):
    """How far the built clearance and creepage fall short of what is called for."""
    resolved = validate_high_voltage_policy(policy)
    needed_clearance = required_clearance_mm(working_voltage_v, resolved)
    needed_creepage = required_creepage_mm(
        working_voltage_v, surface_condition, resolved
    )
    built_clearance = _require_positive("clearance_mm", clearance_mm)
    built_creepage = _require_positive("creepage_mm", creepage_mm)
    clearance_ok = _at_least(built_clearance, needed_clearance)
    creepage_ok = _at_least(built_creepage, needed_creepage)
    return {
        "required_clearance_mm": needed_clearance,
        "required_creepage_mm": needed_creepage,
        "clearance_shortfall_mm": max(0.0, needed_clearance - built_clearance),
        "creepage_shortfall_mm": max(0.0, needed_creepage - built_creepage),
        "clearance_ok": clearance_ok,
        "creepage_ok": creepage_ok,
    }


def multipaction_fd_product_ghz_mm(frequency_ghz, gap_mm):
    """Frequency-gap product that places a microwave gap on the susceptibility map."""
    frequency = _require_positive("frequency_ghz", frequency_ghz)
    gap = _require_positive("gap_mm", gap_mm)
    return frequency * gap


def multipaction_band(fd_product_ghz_mm):
    """Susceptibility grouping named by the frequency-gap product."""
    product = _require_positive("fd_product_ghz_mm", fd_product_ghz_mm)
    for bound, name in MULTIPACTION_BANDS:
        if _at_most(product, bound):
            return name
    return MULTIPACTION_BANDS[-1][1]


def microwave_power_utilisation(applied_peak_power_w, rated_peak_power_w):
    """Applied peak power as a share of the rated peak power."""
    applied = _require_non_negative("applied_peak_power_w", applied_peak_power_w)
    rated = _require_positive("rated_peak_power_w", rated_peak_power_w)
    return applied / rated


def validate_high_voltage_case(case):
    """Check a high voltage application case names what the decision needs."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = case.get("part_reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("case must name a part_reference")
    if case.get("enclosure_form") not in ENCLOSURE_FORMS:
        raise ValueError(
            "enclosure_form must be one of %s, got %r"
            % (", ".join(ENCLOSURE_FORMS), case.get("enclosure_form"))
        )
    if case.get("surface_condition") not in SURFACE_CONDITIONS:
        raise ValueError(
            "surface_condition must be one of %s, got %r"
            % (", ".join(sorted(SURFACE_CONDITIONS)), case.get("surface_condition"))
        )
    for field in (
        "rated_voltage_v",
        "working_voltage_v",
        "electrode_gap_mm",
        "ambient_pressure_torr",
        "clearance_mm",
        "creepage_mm",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    if not isinstance(case.get("operates_through_ascent", False), bool):
        raise ValueError("operates_through_ascent must be a boolean")
    if case.get("frequency_ghz") is not None:
        for field in ("applied_peak_power_w", "rated_peak_power_w"):
            if case.get(field) is None:
                raise ValueError(
                    "a microwave case is missing %s" % field
                )
    return case


def required_provisions(case, policy=None):
    """Provisions the application owes beyond the ordinary class 2 rules."""
    validate_high_voltage_case(case)
    resolved = validate_high_voltage_policy(policy)
    working = _require_non_negative("working_voltage_v", case["working_voltage_v"])
    provisions = []
    if not _at_most(working, resolved["high_voltage_threshold_v"]):
        provisions.append("high-voltage-derating-review")
        provisions.append("insulation-resistance-and-dielectric-withstanding-test")
        if not _at_most(working, resolved["partial_discharge_threshold_v"]):
            provisions.append("partial-discharge-measurement")
        if case.get("operates_through_ascent", False):
            provisions.append("corona-inception-demonstration")
        if case["enclosure_form"] == "hermetically-sealed":
            provisions.append("cavity-hermeticity-and-fill-gas-demonstration")
        if case["enclosure_form"] == "vented-enclosure":
            provisions.append("venting-path-demonstration")
    if case.get("frequency_ghz") is not None:
        provisions.append("microwave-power-handling-derating-review")
        product = multipaction_fd_product_ghz_mm(
            case["frequency_ghz"], case["electrode_gap_mm"]
        )
        provisions.append("multipaction-analysis")
        if multipaction_band(product) != "multipaction-above-susceptibility-band":
            provisions.append("multipaction-margin-test")
    ordered = []
    for provision in provisions:
        if provision not in ordered:
            ordered.append(provision)
    return tuple(ordered)


def assess_class2_high_voltage(case, policy=None):
    """Full clause 5.6.7 class 2 high voltage decision with a disposition."""
    validate_high_voltage_case(case)
    resolved = validate_high_voltage_policy(policy)
    findings = []

    rated = _require_positive("rated_voltage_v", case["rated_voltage_v"])
    working = _require_non_negative("working_voltage_v", case["working_voltage_v"])
    utilisation = voltage_utilisation(working, rated)

    admissible = True
    if not _at_most(working, rated):
        findings.append(
            "the working voltage %.1f V sits above the part rating %.1f V"
            % (working, rated)
        )
        admissible = False

    high_voltage_application = not _at_most(
        working, resolved["high_voltage_threshold_v"]
    )

    utilisation_ok = _at_most(utilisation, resolved["max_voltage_utilisation"])
    if high_voltage_application and not utilisation_ok:
        findings.append(
            "the working voltage occupies %.3f of the rating against a %.3f limit"
            % (utilisation, resolved["max_voltage_utilisation"])
        )

    gap_cm = _require_positive("electrode_gap_mm", case["electrode_gap_mm"]) / 10.0
    try:
        breakdown = paschen_breakdown_voltage_v(
            case["ambient_pressure_torr"], gap_cm
        )
        margin = paschen_margin(breakdown, working) if working > 0.0 else float("inf")
        gap_sustains = True
    except ValueError:
        breakdown = None
        margin = float("inf")
        gap_sustains = False
    breakdown_ok = (not gap_sustains) or _at_least(
        margin, resolved["min_paschen_margin"]
    )
    if high_voltage_application and not breakdown_ok:
        findings.append(
            "the gap breaks down at %.1f V, only %.2f times the working voltage"
            % (breakdown, margin)
        )

    surfaces = surface_shortfalls_mm(
        working,
        case["surface_condition"],
        case["clearance_mm"],
        case["creepage_mm"],
        resolved,
    )
    if high_voltage_application and not surfaces["clearance_ok"]:
        findings.append(
            "the clearance is %.3f mm short of what the working voltage calls for"
            % surfaces["clearance_shortfall_mm"]
        )
    if high_voltage_application and not surfaces["creepage_ok"]:
        findings.append(
            "the creepage is %.3f mm short of what the surface condition calls for"
            % surfaces["creepage_shortfall_mm"]
        )

    vent_ok = True
    if (
        high_voltage_application
        and resolved["require_vent_path"]
        and case["enclosure_form"] == "sealed-unvented"
    ):
        findings.append(
            "a sealed cavity with no vent path carries its gas through the "
            "corona window with no way out"
        )
        vent_ok = False

    fd_product = None
    band = None
    power_utilisation = None
    power_ok = True
    if case.get("frequency_ghz") is not None:
        fd_product = multipaction_fd_product_ghz_mm(
            case["frequency_ghz"], case["electrode_gap_mm"]
        )
        band = multipaction_band(fd_product)
        power_utilisation = microwave_power_utilisation(
            case["applied_peak_power_w"], case["rated_peak_power_w"]
        )
        power_ok = _at_most(
            power_utilisation, resolved["max_microwave_power_utilisation"]
        )
        if not power_ok:
            findings.append(
                "the stage draws %.3f of rated peak power against a %.3f limit"
                % (power_utilisation, resolved["max_microwave_power_utilisation"])
            )

    provisions = required_provisions(case, resolved)
    held = case.get("provisions_held") or ()
    if not isinstance(held, (list, tuple, set, frozenset)):
        raise ValueError("provisions_held must be a list, tuple or set")
    held_set = {str(item).strip().lower() for item in held}
    outstanding = tuple(item for item in provisions if item not in held_set)
    if outstanding:
        findings.append(
            "the application still owes %s" % ", ".join(outstanding)
        )

    # Every high voltage term is gated on the application actually being a high
    # voltage one, so the disposition can never turn on a check that raised no
    # finding. The microwave power term is not gated: a high power stage owes it
    # whether or not the voltage crosses the threshold.
    design_ok = power_ok
    if high_voltage_application:
        design_ok = (
            design_ok
            and utilisation_ok
            and breakdown_ok
            and surfaces["clearance_ok"]
            and surfaces["creepage_ok"]
            and vent_ok
        )

    if not admissible:
        disposition = APPLICATION_NOT_ADMISSIBLE
    elif not design_ok:
        disposition = DESIGN_NONCONFORMING
    elif outstanding:
        disposition = PROVISIONS_OUTSTANDING
    else:
        disposition = PROVISIONS_SATISFIED

    return {
        "disposition": disposition,
        "admissible": admissible,
        "high_voltage_application": high_voltage_application,
        "voltage_utilisation": utilisation,
        "breakdown_voltage_v": breakdown,
        "paschen_margin": margin,
        "gap_sustains_a_discharge": gap_sustains,
        "required_clearance_mm": surfaces["required_clearance_mm"],
        "required_creepage_mm": surfaces["required_creepage_mm"],
        "clearance_shortfall_mm": surfaces["clearance_shortfall_mm"],
        "creepage_shortfall_mm": surfaces["creepage_shortfall_mm"],
        "multipaction_fd_product_ghz_mm": fd_product,
        "multipaction_band": band,
        "microwave_power_utilisation": power_utilisation,
        "required_provisions": provisions,
        "outstanding_provisions": outstanding,
        "findings": findings,
    }
