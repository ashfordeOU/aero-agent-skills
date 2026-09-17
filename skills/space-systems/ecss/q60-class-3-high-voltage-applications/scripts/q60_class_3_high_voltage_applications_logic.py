#!/usr/bin/env python3
"""Additional provisions for Class 3 parts at high voltage and high power.

Anchor: ECSS-Q-ST-60C clause 6.6.7 (provisions a Class 3 EEE part owes over and
above the ordinary Class 3 rules when it is applied at high voltage or in a
high power microwave chain). Paraphrased into an implementable procedure; no
standard text is reproduced.

High voltage use changes what a rating buys. The part is still a Class 3 part
and still owes everything Class 3 asks, but the application adds a second set
of questions the ordinary rules never put — and which of those questions
governs is decided by the pressure the hardware actually sits at. Near ambient,
the gas is dense and breakdown wants a high field. Around the Paschen minimum,
a few hundred volts across a millimetre is enough, and that band is where a
launch ascent spends several minutes. In hard vacuum there is no gas to break
down at all, and the mechanism that remains is a resonant electron avalanche
between two surfaces.

Procedure implemented here
--------------------------
1. Decide whether the application is admissible at all: a working voltage above
   the part's own rating, or a peak power above its rated power, is not a
   derating question.
2. Resolve the pressure regime, which decides whether the gas breakdown check
   or the multipaction check governs.
3. Take the voltage utilisation against the Class 3 limit.
4. Resolve the gas breakdown voltage across the electrode gap at the stated
   pressure and take the margin the working voltage leaves against it.
5. Derive the clearance and creepage the working voltage calls for at the
   surface condition, and name any shortfall.
6. For a microwave chain, take the frequency-gap product, group it against the
   susceptibility bands, and take the peak power utilisation.
7. Assemble the provisions the application owes, subtract what is held, and
   return one disposition in precedence order.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "ENCLOSURE_FORMS",
    "SURFACE_CONDITIONS",
    "MULTIPACTION_BANDS",
    "PRESSURE_REGIMES",
    "DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY",
    "PASCHEN_AIR_A",
    "PASCHEN_AIR_B",
    "PASCHEN_SECONDARY_EMISSION",
    "PA_PER_TORR",
    "PROVISIONS_SATISFIED",
    "PROVISIONS_OUTSTANDING",
    "DESIGN_NONCONFORMING",
    "APPLICATION_NOT_ADMISSIBLE",
    "validate_high_voltage_policy",
    "validate_high_voltage_case",
    "pressure_regime",
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
    "outstanding_provisions",
    "assess_class3_high_voltage",
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

# Ambient pressure in pascals, ascending; the first regime the pressure falls
# at or below names the governing breakdown mechanism.
PRESSURE_REGIMES = (
    (1.0e-3, "vacuum-regime"),
    (1.0e4, "critical-pressure-band"),
    (float("inf"), "near-ambient-regime"),
)

# Townsend coefficients for air, pressure in torr and gap in centimetres.
PASCHEN_AIR_A = 15.0
PASCHEN_AIR_B = 365.0
PASCHEN_SECONDARY_EMISSION = 0.01
PA_PER_TORR = 133.322

DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY = {
    # Working voltage above which the additional provisions attach at all.
    "high_voltage_threshold_v": 100.0,
    # Working voltage above which partial discharge measurement attaches.
    "partial_discharge_threshold_v": 500.0,
    # Share of the part rating the working voltage may occupy at Class 3.
    "max_voltage_utilisation": 0.7,
    # Ratio of gas breakdown voltage to working voltage demanded.
    "min_paschen_margin": 2.0,
    # Clearance through air demanded, per kilovolt of working voltage.
    "clearance_mm_per_kv": 1.0,
    # Creepage along the surface demanded, per kilovolt of working voltage.
    "creepage_mm_per_kv": 2.5,
    # Share of rated peak power a high power microwave stage may draw.
    "max_microwave_power_utilisation": 0.6,
    # Share of rated peak power above which a thermal analysis attaches.
    "thermal_analysis_power_utilisation": 0.4,
    # Whether a sealed cavity with no vent path is a design finding.
    "require_vent_path": True,
}

PROVISIONS_SATISFIED = "q60-c3-hv-provisions-satisfied"
PROVISIONS_OUTSTANDING = "q60-c3-hv-provisions-outstanding"
DESIGN_NONCONFORMING = "q60-c3-hv-design-nonconforming"
APPLICATION_NOT_ADMISSIBLE = "q60-c3-hv-application-not-admissible"

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
    """Return a complete Class 3 high voltage policy with defaults filled in."""
    if policy is None:
        return dict(DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("high voltage policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_CLASS3_HIGH_VOLTAGE_POLICY:
            raise ValueError("unknown high voltage policy key %r" % (key,))
        merged[key] = value
    for key in (
        "high_voltage_threshold_v",
        "partial_discharge_threshold_v",
        "max_voltage_utilisation",
        "min_paschen_margin",
        "clearance_mm_per_kv",
        "creepage_mm_per_kv",
        "max_microwave_power_utilisation",
        "thermal_analysis_power_utilisation",
    ):
        _require_positive(key, merged[key])
    for key in ("max_voltage_utilisation", "max_microwave_power_utilisation"):
        if merged[key] > 1.0:
            raise ValueError("%s must not exceed 1.0, got %r" % (key, merged[key]))
    if merged["partial_discharge_threshold_v"] < merged["high_voltage_threshold_v"]:
        raise ValueError(
            "partial_discharge_threshold_v must not sit below "
            "high_voltage_threshold_v"
        )
    if (
        merged["thermal_analysis_power_utilisation"]
        > merged["max_microwave_power_utilisation"]
    ):
        raise ValueError(
            "thermal_analysis_power_utilisation must not exceed "
            "max_microwave_power_utilisation"
        )
    if not isinstance(merged["require_vent_path"], bool):
        raise ValueError("require_vent_path must be a boolean")
    return merged


def pressure_regime(pressure_pa):
    """Name the regime the ambient pressure puts the breakdown question in."""
    pressure = _require_non_negative("pressure_pa", pressure_pa)
    for bound, name in PRESSURE_REGIMES:
        if _at_most(pressure, bound):
            return name
    return PRESSURE_REGIMES[-1][1]


def voltage_utilisation(working_voltage_v, rated_voltage_v):
    """Working voltage as a share of the part's own rating."""
    working = _require_non_negative("working_voltage_v", working_voltage_v)
    rated = _require_positive("rated_voltage_v", rated_voltage_v)
    return working / rated


def paschen_breakdown_voltage_v(pressure_pa, gap_mm):
    """Gas breakdown voltage across a gap at a stated ambient pressure.

    The Townsend form in torr-centimetres. Below the Paschen minimum the
    denominator stops being positive: there are too few gas molecules in the
    gap to sustain an avalanche at any voltage the design could reach, so the
    breakdown voltage is reported as unbounded rather than as a small number.
    """
    pressure = _require_non_negative("pressure_pa", pressure_pa)
    gap = _require_positive("gap_mm", gap_mm)
    pressure_torr = pressure / PA_PER_TORR
    gap_cm = gap / 10.0
    product = pressure_torr * gap_cm
    if product <= 0.0:
        return math.inf
    denominator = math.log(PASCHEN_AIR_A * product) - math.log(
        math.log(1.0 + 1.0 / PASCHEN_SECONDARY_EMISSION)
    )
    if denominator <= 0.0:
        return math.inf
    return PASCHEN_AIR_B * product / denominator


def paschen_margin(breakdown_voltage_v, working_voltage_v):
    """Ratio of gas breakdown voltage to the working voltage across the gap."""
    working = _require_positive("working_voltage_v", working_voltage_v)
    if breakdown_voltage_v == math.inf:
        return math.inf
    breakdown = _require_non_negative("breakdown_voltage_v", breakdown_voltage_v)
    return breakdown / working


def required_clearance_mm(working_voltage_v, policy=None):
    """Air clearance the working voltage calls for."""
    resolved = validate_high_voltage_policy(policy)
    working = _require_non_negative("working_voltage_v", working_voltage_v)
    return working / 1000.0 * resolved["clearance_mm_per_kv"]


def required_creepage_mm(working_voltage_v, surface_condition, policy=None):
    """Surface creepage the working voltage calls for at this surface."""
    resolved = validate_high_voltage_policy(policy)
    if surface_condition not in SURFACE_CONDITIONS:
        raise ValueError(
            "surface_condition must be one of %s, got %r"
            % (", ".join(sorted(SURFACE_CONDITIONS)), surface_condition)
        )
    working = _require_non_negative("working_voltage_v", working_voltage_v)
    return (
        working
        / 1000.0
        * resolved["creepage_mm_per_kv"]
        * SURFACE_CONDITIONS[surface_condition]
    )


def surface_shortfalls_mm(
    working_voltage_v, clearance_mm, creepage_mm, surface_condition, policy=None
):
    """How far the built clearance and creepage fall short of what is called for."""
    resolved = validate_high_voltage_policy(policy)
    built_clearance = _require_non_negative("clearance_mm", clearance_mm)
    built_creepage = _require_non_negative("creepage_mm", creepage_mm)
    needed_clearance = required_clearance_mm(working_voltage_v, resolved)
    needed_creepage = required_creepage_mm(
        working_voltage_v, surface_condition, resolved
    )
    clearance_ok = _at_least(built_clearance, needed_clearance)
    creepage_ok = _at_least(built_creepage, needed_creepage)
    return {
        "required_clearance_mm": needed_clearance,
        "required_creepage_mm": needed_creepage,
        "clearance_ok": clearance_ok,
        "creepage_ok": creepage_ok,
        "clearance_shortfall_mm": 0.0
        if clearance_ok
        else needed_clearance - built_clearance,
        "creepage_shortfall_mm": 0.0
        if creepage_ok
        else needed_creepage - built_creepage,
    }


def multipaction_fd_product_ghz_mm(frequency_ghz, gap_mm):
    """Frequency-gap product, the coordinate the susceptibility bands sit on."""
    frequency = _require_positive("frequency_ghz", frequency_ghz)
    gap = _require_positive("gap_mm", gap_mm)
    return frequency * gap


def multipaction_band(fd_product_ghz_mm):
    """Group a frequency-gap product against the susceptibility bands."""
    product = _require_positive("fd_product_ghz_mm", fd_product_ghz_mm)
    for bound, name in MULTIPACTION_BANDS:
        if _at_most(product, bound):
            return name
    return MULTIPACTION_BANDS[-1][1]


def microwave_power_utilisation(peak_power_w, rated_peak_power_w):
    """Applied peak power as a share of the stage's rated peak power."""
    peak = _require_non_negative("peak_power_w", peak_power_w)
    rated = _require_positive("rated_peak_power_w", rated_peak_power_w)
    return peak / rated


def validate_high_voltage_case(case):
    """Check a high voltage case names every field the decision needs."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    for field in (
        "working_voltage_v",
        "rated_voltage_v",
        "electrode_gap_mm",
        "ambient_pressure_pa",
        "clearance_mm",
        "creepage_mm",
        "surface_condition",
        "enclosure_form",
        "provisions_held",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    if case["surface_condition"] not in SURFACE_CONDITIONS:
        raise ValueError(
            "surface_condition must be one of %s, got %r"
            % (", ".join(sorted(SURFACE_CONDITIONS)), case["surface_condition"])
        )
    if case["enclosure_form"] not in ENCLOSURE_FORMS:
        raise ValueError(
            "enclosure_form must be one of %s, got %r"
            % (", ".join(ENCLOSURE_FORMS), case["enclosure_form"])
        )
    if not isinstance(case["provisions_held"], (list, tuple, set, frozenset)):
        raise ValueError("provisions_held must be a list, tuple or set")
    if case.get("microwave_chain"):
        for field in ("frequency_ghz", "peak_power_w", "rated_peak_power_w"):
            if case.get(field) is None:
                raise ValueError("a microwave chain case is missing %s" % field)
    return case


def required_provisions(case, policy=None):
    """The provisions this application owes over the ordinary Class 3 rules."""
    validate_high_voltage_case(case)
    resolved = validate_high_voltage_policy(policy)
    working = _require_non_negative("working_voltage_v", case["working_voltage_v"])
    owed = []
    if _at_least(working, resolved["high_voltage_threshold_v"]):
        owed.append("high-voltage-design-review")
        owed.append("insulation-coordination-analysis")
    if _at_least(working, resolved["partial_discharge_threshold_v"]):
        owed.append("partial-discharge-measurement")
    regime = pressure_regime(case["ambient_pressure_pa"])
    if regime == "critical-pressure-band" and _at_least(
        working, resolved["high_voltage_threshold_v"]
    ):
        owed.append("corona-inception-test")
    if case["enclosure_form"] == "sealed-unvented":
        owed.append("vent-path-analysis")
    if case["surface_condition"] == "contamination-exposed":
        owed.append("insulation-material-outgassing-data")
    if case.get("microwave_chain"):
        product = multipaction_fd_product_ghz_mm(
            case["frequency_ghz"], case["electrode_gap_mm"]
        )
        band = multipaction_band(product)
        if band in (
            "multipaction-deep-susceptibility",
            "multipaction-susceptibility-band",
        ):
            owed.append("multipaction-analysis")
        if band == "multipaction-deep-susceptibility":
            owed.append("multipaction-test")
        utilisation = microwave_power_utilisation(
            case["peak_power_w"], case["rated_peak_power_w"]
        )
        if _at_least(utilisation, resolved["thermal_analysis_power_utilisation"]):
            owed.append("high-power-thermal-analysis")
    ordered = []
    for provision in owed:
        if provision not in ordered:
            ordered.append(provision)
    return tuple(ordered)


def outstanding_provisions(case, policy=None):
    """Provisions the application owes and does not hold."""
    owed = required_provisions(case, policy)
    held = set()
    for provision in case["provisions_held"]:
        if not isinstance(provision, str):
            raise ValueError("every held provision must be a string")
        held.add(provision.strip().lower())
    return tuple(provision for provision in owed if provision not in held)


def assess_class3_high_voltage(case, policy=None):
    """Full clause 6.6.7 Class 3 high voltage decision with a disposition."""
    validate_high_voltage_case(case)
    resolved = validate_high_voltage_policy(policy)
    findings = []

    working = _require_non_negative("working_voltage_v", case["working_voltage_v"])
    rated = _require_positive("rated_voltage_v", case["rated_voltage_v"])
    utilisation = voltage_utilisation(working, rated)
    over_rating = not _at_most(utilisation, 1.0)
    if over_rating:
        findings.append(
            "the working voltage sits above the part rating at %.3f of it"
            % utilisation
        )

    power_utilisation = None
    power_over_rating = False
    band = None
    fd_product = None
    if case.get("microwave_chain"):
        power_utilisation = microwave_power_utilisation(
            case["peak_power_w"], case["rated_peak_power_w"]
        )
        power_over_rating = not _at_most(power_utilisation, 1.0)
        if power_over_rating:
            findings.append(
                "the stage draws %.3f of its rated peak power" % power_utilisation
            )
        fd_product = multipaction_fd_product_ghz_mm(
            case["frequency_ghz"], case["electrode_gap_mm"]
        )
        band = multipaction_band(fd_product)

    regime = pressure_regime(case["ambient_pressure_pa"])
    breakdown = paschen_breakdown_voltage_v(
        case["ambient_pressure_pa"], case["electrode_gap_mm"]
    )
    margin = paschen_margin(breakdown, working) if working > 0.0 else math.inf
    gas_governs = regime != "vacuum-regime"
    margin_ok = (not gas_governs) or _at_least(margin, resolved["min_paschen_margin"])
    if not margin_ok:
        findings.append(
            "the gap breaks down at %.1f V, only %.2f times the working voltage"
            % (breakdown, margin)
        )

    utilisation_ok = _at_most(utilisation, resolved["max_voltage_utilisation"])
    if not over_rating and not utilisation_ok:
        findings.append(
            "the working voltage occupies %.3f of the rating, above the Class 3 "
            "limit" % utilisation
        )

    surfaces = surface_shortfalls_mm(
        working,
        case["clearance_mm"],
        case["creepage_mm"],
        case["surface_condition"],
        resolved,
    )
    if not surfaces["clearance_ok"]:
        findings.append(
            "the clearance is %.3f mm short of what the working voltage calls for"
            % surfaces["clearance_shortfall_mm"]
        )
    if not surfaces["creepage_ok"]:
        findings.append(
            "the creepage is %.3f mm short of what this surface calls for"
            % surfaces["creepage_shortfall_mm"]
        )

    power_ok = True
    if power_utilisation is not None and not power_over_rating:
        power_ok = _at_most(
            power_utilisation, resolved["max_microwave_power_utilisation"]
        )
        if not power_ok:
            findings.append(
                "the stage draws %.3f of rated peak power, above the Class 3 limit"
                % power_utilisation
            )

    vent_ok = True
    if resolved["require_vent_path"] and case["enclosure_form"] == "sealed-unvented":
        vent_ok = False
        findings.append("the cavity is sealed with no vent path")

    outstanding = outstanding_provisions(case, resolved)
    if outstanding:
        findings.append("the application owes %s" % ", ".join(outstanding))

    design_ok = (
        margin_ok
        and utilisation_ok
        and surfaces["clearance_ok"]
        and surfaces["creepage_ok"]
        and power_ok
        and vent_ok
    )

    if over_rating or power_over_rating:
        disposition = APPLICATION_NOT_ADMISSIBLE
    elif not design_ok:
        disposition = DESIGN_NONCONFORMING
    elif outstanding:
        disposition = PROVISIONS_OUTSTANDING
    else:
        disposition = PROVISIONS_SATISFIED

    return {
        "disposition": disposition,
        "satisfied": disposition == PROVISIONS_SATISFIED,
        "pressure_regime": regime,
        "gas_breakdown_governs": gas_governs,
        "voltage_utilisation": utilisation,
        "breakdown_voltage_v": breakdown,
        "paschen_margin": margin,
        "paschen_margin_ok": margin_ok,
        "required_clearance_mm": surfaces["required_clearance_mm"],
        "required_creepage_mm": surfaces["required_creepage_mm"],
        "clearance_ok": surfaces["clearance_ok"],
        "creepage_ok": surfaces["creepage_ok"],
        "multipaction_fd_product_ghz_mm": fd_product,
        "multipaction_band": band,
        "microwave_power_utilisation": power_utilisation,
        "microwave_power_ok": power_ok,
        "vent_path_ok": vent_ok,
        "required_provisions": required_provisions(case, resolved),
        "outstanding_provisions": outstanding,
        "findings": findings,
    }
