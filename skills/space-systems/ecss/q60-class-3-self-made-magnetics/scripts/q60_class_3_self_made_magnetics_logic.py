#!/usr/bin/env python3
"""In-house wound magnetic parts for Class 3 equipment, to recognised practice.

Anchor: ECSS-Q-ST-60C clause 6.6.8 (a magnetic part wound in house for Class 3
equipment is designed and screened to a recognised practice rather than bought
against a component specification). Paraphrased into an implementable
procedure; no standard text is reproduced.

A self-made part has no procurement history to lean on, so the evidence is
built rather than inherited. Class 3 relaxes who may hold the needle and how
much of the lot has to be sacrificed; it does not relax whether a wire
specification, a core specification, a qualified winding procedure and a named
recognised practice exist. Without those four there is nothing to assess.

Procedure implemented here
--------------------------
1. Name the foundations the part does not stand on. If any is missing the part
   is not admissible and the design numbers are not worth computing.
2. Resolve the peak flux density from the volt-second product, the turns and
   the core section, and take its utilisation of the core saturation figure.
3. Take the window fill factor and the winding current density.
4. Resolve the winding resistance at its declared operating temperature, take
   the copper loss, take the core loss from the material power law at the
   working flux and frequency, and add them.
5. Carry the total loss across the thermal path to a rise, add the ambient,
   and take the margin against the insulation temperature index less the Class
   3 derating. Check the declared winding temperature is not below the hot spot
   the losses it produced actually reach.
6. Price the dielectric withstand voltage the working voltage calls for and
   compare it with what the insulation system is rated to stand.
7. Derive the screening sequence from the construction and the flight lot size
   and subtract what has been done.
8. Return one disposition in precedence order.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "REQUIRED_FOUNDATIONS",
    "CONSTRUCTION_FORMS",
    "INSULATION_TEMPERATURE_INDEX_C",
    "BASE_SCREENING_SEQUENCE",
    "COPPER_TEMPERATURE_COEFFICIENT",
    "DEFAULT_CLASS3_MAGNETICS_POLICY",
    "PRACTICE_SATISFIED",
    "SCREENING_OUTSTANDING",
    "DESIGN_NONCONFORMING",
    "PART_NOT_ADMISSIBLE",
    "validate_magnetics_policy",
    "validate_magnetics_case",
    "foundation_gaps",
    "peak_flux_density_t",
    "saturation_utilisation",
    "window_fill_factor",
    "current_density_a_per_mm2",
    "winding_resistance_ohm",
    "copper_loss_w",
    "core_loss_w",
    "temperature_rise_k",
    "derated_insulation_limit_c",
    "hot_spot_margin_k",
    "required_dielectric_withstand_v",
    "screening_sequence",
    "outstanding_screening",
    "assess_class3_self_made_magnetics",
]

# What has to exist before a self-made part can be assessed at all. Class 3
# widens who may write and sign each one; it does not remove any of them.
REQUIRED_FOUNDATIONS = (
    "wire-specification",
    "core-specification",
    "qualified-winding-procedure",
    "recognised-practice-reference",
)

# Construction form -> the screening step that form adds over the base
# sequence, because that form hides something the base sequence cannot see.
CONSTRUCTION_FORMS = {
    "toroidal-wound": "winding-integrity-inspection",
    "bobbin-wound": "bobbin-seating-inspection",
    "potted-assembly": "radiographic-inspection",
    "tape-wound-core": "core-gap-verification",
}

# Insulation system -> temperature index in degrees Celsius.
INSULATION_TEMPERATURE_INDEX_C = {
    "class-a": 105.0,
    "class-b": 130.0,
    "class-f": 155.0,
    "class-h": 180.0,
}

BASE_SCREENING_SEQUENCE = (
    "visual-inspection",
    "electrical-parameter-measurement",
    "insulation-resistance-test",
    "dielectric-withstand-test",
    "reduced-thermal-cycling",
)

# Copper resistivity gains roughly four parts in a thousand per kelvin.
COPPER_TEMPERATURE_COEFFICIENT = 0.00393

DEFAULT_CLASS3_MAGNETICS_POLICY = {
    # Share of the core saturation figure the working flux may occupy.
    "max_saturation_utilisation": 0.8,
    # Share of the winding window the conductor may occupy.
    "max_window_fill_factor": 0.4,
    # Current density the winding may run at, in amperes per square millimetre.
    "max_current_density_a_per_mm2": 6.0,
    # Kelvin held back from the insulation temperature index at Class 3.
    "insulation_derating_k": 25.0,
    # Kelvin of margin demanded between hot spot and the derated limit.
    "min_hot_spot_margin_k": 10.0,
    # Dielectric withstand voltage demanded: twice working plus this offset.
    "dielectric_offset_v": 1000.0,
    # Reference temperature the cold winding resistance is stated at.
    "resistance_reference_temperature_c": 20.0,
    # Smallest flight lot that can spare a part for destructive analysis.
    "destructive_sample_lot_floor": 5,
    # Whether a named recognised practice reference is a foundation.
    "require_recognised_practice_reference": True,
}

PRACTICE_SATISFIED = "q60-c3-magnetics-practice-satisfied"
SCREENING_OUTSTANDING = "q60-c3-magnetics-screening-outstanding"
DESIGN_NONCONFORMING = "q60-c3-magnetics-design-nonconforming"
PART_NOT_ADMISSIBLE = "q60-c3-magnetics-part-not-admissible"

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
    """Return a complete Class 3 magnetics policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_CLASS3_MAGNETICS_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("magnetics policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_CLASS3_MAGNETICS_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_CLASS3_MAGNETICS_POLICY:
            raise ValueError("unknown magnetics policy key %r" % (key,))
        merged[key] = value
    for key in (
        "max_saturation_utilisation",
        "max_window_fill_factor",
        "max_current_density_a_per_mm2",
        "insulation_derating_k",
        "min_hot_spot_margin_k",
        "dielectric_offset_v",
    ):
        _require_positive(key, merged[key])
    _require_number(
        "resistance_reference_temperature_c",
        merged["resistance_reference_temperature_c"],
    )
    for key in ("max_saturation_utilisation", "max_window_fill_factor"):
        if merged[key] > 1.0:
            raise ValueError("%s must not exceed 1.0, got %r" % (key, merged[key]))
    _require_positive_int(
        "destructive_sample_lot_floor", merged["destructive_sample_lot_floor"]
    )
    if not isinstance(merged["require_recognised_practice_reference"], bool):
        raise ValueError("require_recognised_practice_reference must be a boolean")
    return merged


def foundation_gaps(case, policy=None):
    """Foundations a self-made part does not stand on."""
    resolved = validate_magnetics_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    held = case.get("foundations_held", ())
    if not isinstance(held, (list, tuple, set, frozenset)):
        raise ValueError("foundations_held must be a list, tuple or set")
    folded = set()
    for foundation in held:
        if not isinstance(foundation, str):
            raise ValueError("every foundation must be a string")
        folded.add(foundation.strip().lower())
    missing = []
    for foundation in REQUIRED_FOUNDATIONS:
        if (
            foundation == "recognised-practice-reference"
            and not resolved["require_recognised_practice_reference"]
        ):
            continue
        if foundation not in folded:
            missing.append(foundation)
    return tuple(missing)


def peak_flux_density_t(volt_seconds, turns, core_area_mm2):
    """Peak flux density from the volt-second product, turns and core section.

    The flux the core sees is set by the applied voltage times the time it is
    applied, not by the current the winding carries.
    """
    product = _require_positive("volt_seconds", volt_seconds)
    turn_count = _require_positive_int("turns", turns)
    area_mm2 = _require_positive("core_area_mm2", core_area_mm2)
    area_m2 = area_mm2 * 1.0e-6
    return product / (turn_count * area_m2)


def saturation_utilisation(peak_flux_t, saturation_flux_t):
    """Working flux as a share of the core's saturation figure."""
    peak = _require_non_negative("peak_flux_t", peak_flux_t)
    saturation = _require_positive("saturation_flux_t", saturation_flux_t)
    return peak / saturation


def window_fill_factor(turns, conductor_mm2, window_mm2):
    """Share of the winding window the bare conductor occupies."""
    turn_count = _require_positive_int("turns", turns)
    conductor = _require_positive("conductor_mm2", conductor_mm2)
    window = _require_positive("window_mm2", window_mm2)
    return turn_count * conductor / window


def current_density_a_per_mm2(winding_current_a, conductor_mm2):
    """Current density the winding runs at."""
    current = _require_non_negative("winding_current_a", winding_current_a)
    conductor = _require_positive("conductor_mm2", conductor_mm2)
    return current / conductor


def winding_resistance_ohm(cold_resistance_ohm, winding_temperature_c, policy=None):
    """Winding resistance at its operating temperature."""
    resolved = validate_magnetics_policy(policy)
    cold = _require_positive("cold_resistance_ohm", cold_resistance_ohm)
    temperature = _require_number("winding_temperature_c", winding_temperature_c)
    reference = resolved["resistance_reference_temperature_c"]
    factor = 1.0 + COPPER_TEMPERATURE_COEFFICIENT * (temperature - reference)
    if factor <= 0.0:
        raise ValueError(
            "winding_temperature_c is below the range copper resistivity is "
            "modelled over, got %r" % (winding_temperature_c,)
        )
    return cold * factor


def copper_loss_w(winding_current_a, resistance_ohm):
    """Resistive loss in the winding at its operating temperature."""
    current = _require_non_negative("winding_current_a", winding_current_a)
    resistance = _require_positive("resistance_ohm", resistance_ohm)
    return current * current * resistance


def core_loss_w(
    steinmetz_k, steinmetz_alpha, steinmetz_beta, frequency_khz, peak_flux_t, volume_cm3
):
    """Core loss from the material power law, in watts.

    steinmetz_k is stated in milliwatts per cubic centimetre at one kilohertz
    and one tesla; the result is converted to watts.
    """
    k = _require_positive("steinmetz_k", steinmetz_k)
    alpha = _require_positive("steinmetz_alpha", steinmetz_alpha)
    beta = _require_positive("steinmetz_beta", steinmetz_beta)
    frequency = _require_positive("frequency_khz", frequency_khz)
    flux = _require_positive("peak_flux_t", peak_flux_t)
    volume = _require_positive("volume_cm3", volume_cm3)
    milliwatts = k * math.pow(frequency, alpha) * math.pow(flux, beta) * volume
    return milliwatts / 1000.0


def temperature_rise_k(total_loss_w, thermal_resistance_k_per_w):
    """Rise the total loss produces across the thermal path."""
    loss = _require_non_negative("total_loss_w", total_loss_w)
    resistance = _require_positive(
        "thermal_resistance_k_per_w", thermal_resistance_k_per_w
    )
    return loss * resistance


def derated_insulation_limit_c(insulation_system, policy=None):
    """Temperature index of the insulation system less the Class 3 derating."""
    resolved = validate_magnetics_policy(policy)
    if insulation_system not in INSULATION_TEMPERATURE_INDEX_C:
        raise ValueError(
            "insulation_system must be one of %s, got %r"
            % (
                ", ".join(sorted(INSULATION_TEMPERATURE_INDEX_C)),
                insulation_system,
            )
        )
    return (
        INSULATION_TEMPERATURE_INDEX_C[insulation_system]
        - resolved["insulation_derating_k"]
    )


def hot_spot_margin_k(hot_spot_c, insulation_system, policy=None):
    """Kelvin between the hot spot and the derated insulation limit."""
    hot_spot = _require_number("hot_spot_c", hot_spot_c)
    return derated_insulation_limit_c(insulation_system, policy) - hot_spot


def required_dielectric_withstand_v(working_voltage_v, policy=None):
    """Withstand voltage the working voltage calls for."""
    resolved = validate_magnetics_policy(policy)
    working = _require_non_negative("working_voltage_v", working_voltage_v)
    return 2.0 * working + resolved["dielectric_offset_v"]


def screening_sequence(construction_form, flight_lot_size, policy=None):
    """Screening steps a self-made part of this construction and lot owes."""
    resolved = validate_magnetics_policy(policy)
    if construction_form not in CONSTRUCTION_FORMS:
        raise ValueError(
            "construction_form must be one of %s, got %r"
            % (", ".join(sorted(CONSTRUCTION_FORMS)), construction_form)
        )
    lot = _require_positive_int("flight_lot_size", flight_lot_size)
    sequence = list(BASE_SCREENING_SEQUENCE)
    sequence.append(CONSTRUCTION_FORMS[construction_form])
    if lot >= resolved["destructive_sample_lot_floor"]:
        sequence.append("destructive-sample-analysis")
    else:
        # A lot below the floor has no part to give up, so the whole lot is
        # screened instead of one of it being destroyed.
        sequence.append("full-lot-screening-in-lieu-of-sample")
    ordered = []
    for step in sequence:
        if step not in ordered:
            ordered.append(step)
    return tuple(ordered)


def outstanding_screening(construction_form, flight_lot_size, steps_done, policy=None):
    """Screening steps owed and not yet done."""
    owed = screening_sequence(construction_form, flight_lot_size, policy)
    if not isinstance(steps_done, (list, tuple, set, frozenset)):
        raise ValueError("steps_done must be a list, tuple or set")
    done = set()
    for step in steps_done:
        if not isinstance(step, str):
            raise ValueError("every screening step must be a string")
        done.add(step.strip().lower())
    return tuple(step for step in owed if step not in done)


def validate_magnetics_case(case):
    """Check a self-made magnetics case names every field the decision needs."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    for field in (
        "volt_seconds",
        "turns",
        "core_area_mm2",
        "saturation_flux_t",
        "conductor_mm2",
        "window_mm2",
        "winding_current_a",
        "cold_resistance_ohm",
        "winding_temperature_c",
        "steinmetz_k",
        "steinmetz_alpha",
        "steinmetz_beta",
        "frequency_khz",
        "core_volume_cm3",
        "thermal_resistance_k_per_w",
        "ambient_temperature_c",
        "insulation_system",
        "insulation_withstand_rating_v",
        "working_voltage_v",
        "construction_form",
        "flight_lot_size",
        "screening_done",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    if case["insulation_system"] not in INSULATION_TEMPERATURE_INDEX_C:
        raise ValueError(
            "insulation_system must be one of %s, got %r"
            % (
                ", ".join(sorted(INSULATION_TEMPERATURE_INDEX_C)),
                case["insulation_system"],
            )
        )
    if case["construction_form"] not in CONSTRUCTION_FORMS:
        raise ValueError(
            "construction_form must be one of %s, got %r"
            % (", ".join(sorted(CONSTRUCTION_FORMS)), case["construction_form"])
        )
    return case


def assess_class3_self_made_magnetics(case, policy=None):
    """Full clause 6.6.8 Class 3 self-made magnetics decision with a disposition."""
    validate_magnetics_case(case)
    resolved = validate_magnetics_policy(policy)
    findings = []

    gaps = foundation_gaps(case, resolved)
    if gaps:
        findings.append("the part stands on no %s" % ", no ".join(gaps))

    peak_flux = peak_flux_density_t(
        case["volt_seconds"], case["turns"], case["core_area_mm2"]
    )
    flux_utilisation = saturation_utilisation(peak_flux, case["saturation_flux_t"])
    flux_ok = _at_most(flux_utilisation, resolved["max_saturation_utilisation"])
    if not flux_ok:
        findings.append(
            "the working flux occupies %.3f of core saturation" % flux_utilisation
        )

    fill = window_fill_factor(
        case["turns"], case["conductor_mm2"], case["window_mm2"]
    )
    fill_ok = _at_most(fill, resolved["max_window_fill_factor"])
    if not fill_ok:
        findings.append("the bare conductor already fills %.3f of the window" % fill)

    density = current_density_a_per_mm2(
        case["winding_current_a"], case["conductor_mm2"]
    )
    density_ok = _at_most(density, resolved["max_current_density_a_per_mm2"])
    if not density_ok:
        findings.append("the winding runs at %.2f A/mm2" % density)

    resistance = winding_resistance_ohm(
        case["cold_resistance_ohm"], case["winding_temperature_c"], resolved
    )
    copper = copper_loss_w(case["winding_current_a"], resistance)
    core = core_loss_w(
        case["steinmetz_k"],
        case["steinmetz_alpha"],
        case["steinmetz_beta"],
        case["frequency_khz"],
        peak_flux,
        case["core_volume_cm3"],
    )
    total_loss = copper + core
    rise = temperature_rise_k(total_loss, case["thermal_resistance_k_per_w"])
    hot_spot = _require_number(
        "ambient_temperature_c", case["ambient_temperature_c"]
    ) + rise
    margin = hot_spot_margin_k(hot_spot, case["insulation_system"], resolved)
    margin_ok = _at_least(margin, resolved["min_hot_spot_margin_k"])
    if not margin_ok:
        findings.append(
            "the hot spot reaches %.1f C, %.1f K from the derated insulation limit"
            % (hot_spot, margin)
        )

    reference_ok = _at_least(case["winding_temperature_c"], hot_spot)
    if not reference_ok:
        findings.append(
            "the winding resistance was taken at %.1f C, below the %.1f C hot spot "
            "its own losses reach"
            % (case["winding_temperature_c"], hot_spot)
        )

    required_withstand = required_dielectric_withstand_v(
        case["working_voltage_v"], resolved
    )
    withstand_ok = _at_least(
        _require_non_negative(
            "insulation_withstand_rating_v", case["insulation_withstand_rating_v"]
        ),
        required_withstand,
    )
    if not withstand_ok:
        findings.append(
            "the insulation system stands %.0f V against the %.0f V the working "
            "voltage calls for"
            % (case["insulation_withstand_rating_v"], required_withstand)
        )

    owed = screening_sequence(
        case["construction_form"], case["flight_lot_size"], resolved
    )
    outstanding = outstanding_screening(
        case["construction_form"],
        case["flight_lot_size"],
        case["screening_done"],
        resolved,
    )
    if outstanding:
        findings.append("the part still owes %s" % ", ".join(outstanding))

    design_ok = (
        flux_ok
        and fill_ok
        and density_ok
        and margin_ok
        and reference_ok
        and withstand_ok
    )

    if gaps:
        disposition = PART_NOT_ADMISSIBLE
    elif not design_ok:
        disposition = DESIGN_NONCONFORMING
    elif outstanding:
        disposition = SCREENING_OUTSTANDING
    else:
        disposition = PRACTICE_SATISFIED

    return {
        "disposition": disposition,
        "satisfied": disposition == PRACTICE_SATISFIED,
        "foundation_gaps": gaps,
        "peak_flux_t": peak_flux,
        "saturation_utilisation": flux_utilisation,
        "flux_ok": flux_ok,
        "window_fill_factor": fill,
        "fill_ok": fill_ok,
        "current_density_a_per_mm2": density,
        "current_density_ok": density_ok,
        "winding_resistance_ohm": resistance,
        "copper_loss_w": copper,
        "core_loss_w": core,
        "total_loss_w": total_loss,
        "temperature_rise_k": rise,
        "hot_spot_c": hot_spot,
        "derated_insulation_limit_c": derated_insulation_limit_c(
            case["insulation_system"], resolved
        ),
        "hot_spot_margin_k": margin,
        "hot_spot_margin_ok": margin_ok,
        "resistance_reference_ok": reference_ok,
        "required_withstand_v": required_withstand,
        "withstand_ok": withstand_ok,
        "screening_sequence": owed,
        "outstanding_screening": outstanding,
        "findings": findings,
    }
