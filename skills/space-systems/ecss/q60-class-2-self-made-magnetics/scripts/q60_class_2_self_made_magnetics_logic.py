#!/usr/bin/env python3
"""Designing and screening in-house wound magnetic parts for class 2 equipment.

Anchor: ECSS-Q-ST-60C clause 5.6.8 (magnetic parts wound in house for class 2
equipment, designed and screened to recognised practice rather than bought
against a component specification). Paraphrased into an implementable
procedure; no standard text is reproduced.

A self-made part has no procurement history to lean on. Nobody else has
qualified it, nobody else screens it, and the only evidence that will ever
exist is the evidence the project builds. Recognised practice is therefore
both the design rule and the acceptance rule: the winding is sized so the core
never saturates and the insulation never reaches its rating, and the finished
part is screened before it is fitted.

Procedure implemented here
--------------------------
1. Refuse a part with no wire specification, no core specification and no
   qualified winding procedure behind it. There is nothing to assess.
2. Resolve the peak flux density from the volt-second product the winding sees
   and take its utilisation of the core saturation figure.
3. Take the window fill factor the turns and the conductor put in the bobbin,
   and the current density the winding runs at.
4. Resolve the copper loss from the winding resistance at temperature and the
   core loss from the power law, add them, and carry the total across the
   thermal resistance to a hot spot temperature.
5. Take the hot spot margin against the insulation rating less the class 2
   derating.
6. Derive the screening sequence the construction and the flight lot call for,
   compare it with what has been done, and return one disposition.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "CONSTRUCTIONS",
    "INSULATION_CLASS_RATINGS_C",
    "BASE_SCREENING_SEQUENCE",
    "CONSTRUCTION_SCREENING",
    "DEFAULT_MAGNETICS_POLICY",
    "PRACTICE_SATISFIED",
    "SCREENING_OUTSTANDING",
    "DESIGN_NONCONFORMING",
    "MAGNETICS_NOT_ADMISSIBLE",
    "validate_magnetics_policy",
    "validate_magnetics_case",
    "admissibility_gaps",
    "peak_flux_density_t",
    "flux_utilisation",
    "window_fill_factor",
    "winding_current_density",
    "winding_resistance_ohm",
    "copper_loss_w",
    "core_loss_w",
    "temperature_rise_c",
    "hot_spot_temperature_c",
    "hot_spot_margin_c",
    "screening_sequence",
    "assess_class2_self_made_magnetics",
]

CONSTRUCTIONS = ("unpotted", "vacuum-impregnated", "potted")

# Hot spot the insulation system is rated for, before the class derating.
INSULATION_CLASS_RATINGS_C = {
    "class-a": 105.0,
    "class-b": 130.0,
    "class-f": 155.0,
    "class-h": 180.0,
    "class-c": 200.0,
}

BASE_SCREENING_SEQUENCE = (
    "winding-visual-inspection",
    "turns-ratio-and-continuity-check",
    "interwinding-insulation-resistance",
    "interwinding-dielectric-withstanding-voltage-test",
    "magnetics-thermal-cycling-screen",
)

CONSTRUCTION_SCREENING = {
    "unpotted": ("varnish-coverage-verification",),
    "vacuum-impregnated": ("impregnation-penetration-verification",),
    "potted": ("void-free-encapsulation-inspection",),
}

DEFAULT_MAGNETICS_POLICY = {
    # Share of core saturation the peak working flux may reach.
    "max_flux_utilisation": 0.6,
    # Share of the bobbin window the conductor may occupy.
    "max_window_fill": 0.40,
    # Current density the winding may run at, in amperes per square millimetre.
    "max_current_density_a_per_mm2": 4.0,
    # Margin held below the insulation rating at class 2.
    "insulation_derating_c": 15.0,
    # Flight lot below which a destructive sample cannot be drawn.
    "min_lot_for_destructive_sample": 3,
    # Class 2 accepts a trained operator; class 1 demands a certified one.
    "require_certified_operator": False,
    # Copper resistivity at twenty degrees, in ohm metres.
    "copper_resistivity_ohm_m": 1.724e-8,
    # Fractional resistance change of copper per degree.
    "copper_temperature_coefficient": 0.00393,
}

PRACTICE_SATISFIED = "class-2-self-made-magnetics-practice-satisfied"
SCREENING_OUTSTANDING = "class-2-self-made-magnetics-screening-outstanding"
DESIGN_NONCONFORMING = "class-2-self-made-magnetics-design-nonconforming"
MAGNETICS_NOT_ADMISSIBLE = "class-2-self-made-magnetics-not-admissible"

_REFERENCE_TEMPERATURE_C = 20.0
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


def _require_positive_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
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


def validate_magnetics_policy(policy=None):
    """Return a complete class 2 magnetics policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_MAGNETICS_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("magnetics policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_MAGNETICS_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_MAGNETICS_POLICY:
            raise ValueError("unknown magnetics policy key %r" % (key,))
        merged[key] = value
    flux = _require_positive("max_flux_utilisation", merged["max_flux_utilisation"])
    if flux > 1.0:
        raise ValueError("max_flux_utilisation must not exceed 1.0, got %r" % (flux,))
    fill = _require_positive("max_window_fill", merged["max_window_fill"])
    if fill > 1.0:
        raise ValueError("max_window_fill must not exceed 1.0, got %r" % (fill,))
    _require_positive(
        "max_current_density_a_per_mm2", merged["max_current_density_a_per_mm2"]
    )
    _require_non_negative("insulation_derating_c", merged["insulation_derating_c"])
    _require_positive_int(
        "min_lot_for_destructive_sample", merged["min_lot_for_destructive_sample"]
    )
    _require_positive(
        "copper_resistivity_ohm_m", merged["copper_resistivity_ohm_m"]
    )
    _require_positive(
        "copper_temperature_coefficient", merged["copper_temperature_coefficient"]
    )
    if not isinstance(merged["require_certified_operator"], bool):
        raise ValueError("require_certified_operator must be a boolean")
    return merged


def _stated(value):
    return isinstance(value, str) and bool(value.strip())


def admissibility_gaps(case, policy=None):
    """Foundations a self-made part must stand on before it can be assessed."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    resolved = validate_magnetics_policy(policy)
    gaps = []
    if not _stated(case.get("wire_specification")):
        gaps.append("wire-specification")
    if not _stated(case.get("core_specification")):
        gaps.append("core-specification")
    if not _stated(case.get("winding_procedure")):
        gaps.append("qualified-winding-procedure")
    if resolved["require_certified_operator"] and not _stated(
        case.get("operator_certification")
    ):
        gaps.append("certified-winding-operator")
    return tuple(gaps)


def peak_flux_density_t(applied_voltage_v, pulse_duration_s, turns, core_area_mm2):
    """Peak flux density the volt-second product drives the core to, in tesla."""
    voltage = _require_positive("applied_voltage_v", applied_voltage_v)
    duration = _require_positive("pulse_duration_s", pulse_duration_s)
    count = _require_positive_int("turns", turns)
    area_mm2 = _require_positive("core_area_mm2", core_area_mm2)
    area_m2 = area_mm2 * 1.0e-6
    return (voltage * duration) / (count * area_m2)


def flux_utilisation(peak_flux_t, saturation_flux_t):
    """Share of the core saturation figure the peak working flux reaches."""
    peak = _require_non_negative("peak_flux_t", peak_flux_t)
    saturation = _require_positive("saturation_flux_t", saturation_flux_t)
    return peak / saturation


def window_fill_factor(turns, conductor_area_mm2, window_area_mm2):
    """Share of the bobbin window the bare conductor occupies."""
    count = _require_positive_int("turns", turns)
    conductor = _require_positive("conductor_area_mm2", conductor_area_mm2)
    window = _require_positive("window_area_mm2", window_area_mm2)
    return count * conductor / window


def winding_current_density(rms_current_a, conductor_area_mm2):
    """Current density the winding runs at, in amperes per square millimetre."""
    current = _require_non_negative("rms_current_a", rms_current_a)
    conductor = _require_positive("conductor_area_mm2", conductor_area_mm2)
    return current / conductor


def winding_resistance_ohm(
    turns, mean_turn_length_mm, conductor_area_mm2, winding_temperature_c, policy=None
):
    """Winding resistance at temperature, from the length and section of copper."""
    count = _require_positive_int("turns", turns)
    length_mm = _require_positive("mean_turn_length_mm", mean_turn_length_mm)
    conductor = _require_positive("conductor_area_mm2", conductor_area_mm2)
    temperature = _require_number("winding_temperature_c", winding_temperature_c)
    resolved = validate_magnetics_policy(policy)
    length_m = count * length_mm * 1.0e-3
    area_m2 = conductor * 1.0e-6
    cold = resolved["copper_resistivity_ohm_m"] * length_m / area_m2
    factor = 1.0 + resolved["copper_temperature_coefficient"] * (
        temperature - _REFERENCE_TEMPERATURE_C
    )
    if factor <= 0.0:
        raise ValueError(
            "winding_temperature_c %g drives the resistance factor non-positive"
            % temperature
        )
    return cold * factor


def copper_loss_w(rms_current_a, resistance_ohm):
    """Ohmic loss the winding dissipates at its operating resistance."""
    current = _require_non_negative("rms_current_a", rms_current_a)
    resistance = _require_non_negative("resistance_ohm", resistance_ohm)
    return current * current * resistance


def core_loss_w(
    steinmetz_k,
    frequency_khz,
    peak_flux_t,
    core_volume_mm3,
    frequency_exponent,
    flux_exponent,
):
    """Core loss from the power law fitted to the material, in watts.

    The coefficient is quoted as milliwatts per cubic centimetre with the
    frequency in kilohertz and the flux in tesla, so the volume is converted
    from cubic millimetres and the result from milliwatts.
    """
    coefficient = _require_positive("steinmetz_k", steinmetz_k)
    frequency = _require_positive("frequency_khz", frequency_khz)
    flux = _require_positive("peak_flux_t", peak_flux_t)
    volume_mm3 = _require_positive("core_volume_mm3", core_volume_mm3)
    frequency_power = _require_positive("frequency_exponent", frequency_exponent)
    flux_power = _require_positive("flux_exponent", flux_exponent)
    density_mw_per_cm3 = (
        coefficient * frequency ** frequency_power * flux ** flux_power
    )
    volume_cm3 = volume_mm3 / 1000.0
    return density_mw_per_cm3 * volume_cm3 / 1000.0


def temperature_rise_c(total_loss_w, thermal_resistance_c_per_w):
    """Rise the dissipated loss produces across the thermal path."""
    loss = _require_non_negative("total_loss_w", total_loss_w)
    resistance = _require_non_negative(
        "thermal_resistance_c_per_w", thermal_resistance_c_per_w
    )
    return loss * resistance


def hot_spot_temperature_c(ambient_temperature_c, rise_c):
    """Hot spot the winding reaches above the ambient it sits in."""
    ambient = _require_number("ambient_temperature_c", ambient_temperature_c)
    rise = _require_non_negative("rise_c", rise_c)
    return ambient + rise


def hot_spot_margin_c(hot_spot_c, insulation_class, policy=None):
    """Margin the hot spot leaves below the derated insulation rating."""
    hot_spot = _require_number("hot_spot_c", hot_spot_c)
    if insulation_class not in INSULATION_CLASS_RATINGS_C:
        raise ValueError(
            "insulation_class must be one of %s, got %r"
            % (", ".join(sorted(INSULATION_CLASS_RATINGS_C)), insulation_class)
        )
    resolved = validate_magnetics_policy(policy)
    allowed = (
        INSULATION_CLASS_RATINGS_C[insulation_class] - resolved["insulation_derating_c"]
    )
    return allowed - hot_spot


def screening_sequence(case, policy=None):
    """Screening steps the construction and the flight lot call for."""
    validate_magnetics_case(case)
    resolved = validate_magnetics_policy(policy)
    sequence = list(BASE_SCREENING_SEQUENCE)
    for step in CONSTRUCTION_SCREENING[case["construction"]]:
        if step not in sequence:
            sequence.append(step)
    lot = _require_positive_int("flight_lot_size", case["flight_lot_size"])
    if lot >= resolved["min_lot_for_destructive_sample"]:
        sequence.append("destructive-lot-sample-analysis")
    else:
        sequence.append("full-lot-nondestructive-screening")
    return tuple(sequence)


def validate_magnetics_case(case):
    """Check a self-made magnetics case names every field the decision needs."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    if case.get("construction") not in CONSTRUCTIONS:
        raise ValueError(
            "construction must be one of %s, got %r"
            % (", ".join(CONSTRUCTIONS), case.get("construction"))
        )
    if case.get("insulation_class") not in INSULATION_CLASS_RATINGS_C:
        raise ValueError(
            "insulation_class must be one of %s, got %r"
            % (
                ", ".join(sorted(INSULATION_CLASS_RATINGS_C)),
                case.get("insulation_class"),
            )
        )
    for field in (
        "applied_voltage_v",
        "pulse_duration_s",
        "turns",
        "core_area_mm2",
        "saturation_flux_t",
        "conductor_area_mm2",
        "window_area_mm2",
        "rms_current_a",
        "mean_turn_length_mm",
        "winding_temperature_c",
        "steinmetz_k",
        "frequency_khz",
        "core_volume_mm3",
        "frequency_exponent",
        "flux_exponent",
        "thermal_resistance_c_per_w",
        "ambient_temperature_c",
        "flight_lot_size",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    _require_positive_int("turns", case["turns"])
    _require_positive_int("flight_lot_size", case["flight_lot_size"])
    return case


def assess_class2_self_made_magnetics(case, policy=None):
    """Full clause 5.6.8 class 2 self-made magnetics decision with a disposition."""
    validate_magnetics_case(case)
    resolved = validate_magnetics_policy(policy)
    findings = []

    gaps = admissibility_gaps(case, resolved)
    if gaps:
        findings.append(
            "the part stands on no %s" % ", no ".join(gaps)
        )

    peak_flux = peak_flux_density_t(
        case["applied_voltage_v"],
        case["pulse_duration_s"],
        case["turns"],
        case["core_area_mm2"],
    )
    utilisation = flux_utilisation(peak_flux, case["saturation_flux_t"])
    flux_ok = _at_most(utilisation, resolved["max_flux_utilisation"])
    if not flux_ok:
        findings.append(
            "the winding drives the core to %.3f of saturation against a %.3f limit"
            % (utilisation, resolved["max_flux_utilisation"])
        )

    fill = window_fill_factor(
        case["turns"], case["conductor_area_mm2"], case["window_area_mm2"]
    )
    fill_ok = _at_most(fill, resolved["max_window_fill"])
    if not fill_ok:
        findings.append(
            "the conductor fills %.3f of the window against a %.3f limit"
            % (fill, resolved["max_window_fill"])
        )

    density = winding_current_density(
        case["rms_current_a"], case["conductor_area_mm2"]
    )
    density_ok = _at_most(density, resolved["max_current_density_a_per_mm2"])
    if not density_ok:
        findings.append(
            "the winding runs at %.3f A/mm2 against a %.3f A/mm2 limit"
            % (density, resolved["max_current_density_a_per_mm2"])
        )

    resistance = winding_resistance_ohm(
        case["turns"],
        case["mean_turn_length_mm"],
        case["conductor_area_mm2"],
        case["winding_temperature_c"],
        resolved,
    )
    copper = copper_loss_w(case["rms_current_a"], resistance)
    core = core_loss_w(
        case["steinmetz_k"],
        case["frequency_khz"],
        peak_flux,
        case["core_volume_mm3"],
        case["frequency_exponent"],
        case["flux_exponent"],
    )
    total_loss = copper + core
    rise = temperature_rise_c(total_loss, case["thermal_resistance_c_per_w"])
    hot_spot = hot_spot_temperature_c(case["ambient_temperature_c"], rise)
    margin = hot_spot_margin_c(hot_spot, case["insulation_class"], resolved)
    thermal_ok = _at_least(margin, 0.0)
    if not thermal_ok:
        findings.append(
            "the hot spot reaches %.2f C, %.2f C past the derated insulation rating"
            % (hot_spot, -margin)
        )

    sequence = screening_sequence(case, resolved)
    completed = case.get("screening_completed") or ()
    if not isinstance(completed, (list, tuple, set, frozenset)):
        raise ValueError("screening_completed must be a list, tuple or set")
    done = {str(step).strip().lower() for step in completed}
    outstanding = tuple(step for step in sequence if step not in done)
    if outstanding:
        findings.append("the part still owes %s" % ", ".join(outstanding))

    design_ok = flux_ok and fill_ok and density_ok and thermal_ok

    if gaps:
        disposition = MAGNETICS_NOT_ADMISSIBLE
    elif not design_ok:
        disposition = DESIGN_NONCONFORMING
    elif outstanding:
        disposition = SCREENING_OUTSTANDING
    else:
        disposition = PRACTICE_SATISFIED

    return {
        "disposition": disposition,
        "admissible": not gaps,
        "admissibility_gaps": gaps,
        "peak_flux_density_t": peak_flux,
        "flux_utilisation": utilisation,
        "window_fill_factor": fill,
        "current_density_a_per_mm2": density,
        "winding_resistance_ohm": resistance,
        "copper_loss_w": copper,
        "core_loss_w": core,
        "total_loss_w": total_loss,
        "temperature_rise_c": rise,
        "hot_spot_temperature_c": hot_spot,
        "hot_spot_margin_c": margin,
        "screening_sequence": sequence,
        "screening_outstanding": outstanding,
        "findings": findings,
    }
