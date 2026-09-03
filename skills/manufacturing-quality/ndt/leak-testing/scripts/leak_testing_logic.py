"""Leak testing math for aerospace parts and systems (pure stdlib, deterministic).

Plan and evaluate a leak test on a fuel tank, accumulator, valve or sealed
enclosure: leak rate from a pressure decay or vacuum decay measurement, the
test time a gauge resolution needs to catch a target leak, helium to air
conversion and back, immersion bubble leak rate, leak test method
recommendation from required sensitivity and access, and disposition of the
part against the maximum allowable leak rate.

All module constants are documented typical values; the approved procedure
governs the real acceptance criteria. No network, no external packages.
"""

import math

# Module constants (documented typical values).
M_HE = 4.003              # molar mass of helium-4, g/mol
M_AIR = 28.97             # molar mass of air, g/mol
BAR_TO_ATM = 0.986923     # one bar expressed in standard atmospheres
STD_TEMP_K = 293.15       # standard temperature for scc (20 C)
MS_THRESHOLD = 1e-6       # scc/s at or below which a helium mass spectrometer hood applies
SNIFFER_THRESHOLD = 1e-5  # scc/s ceiling for helium sniffer localization
BUBBLE_THRESHOLD = 1e-2   # scc/s ceiling for bubble (immersion) testing
HELIUM_MS_MIN_DETECT_SCCS = 1e-9  # typical helium mass spectrometer floor, scc/s He
REVIEW_RATIO = 1.25       # measured over allowable ratio above which reject is clear
GAS_CONVERSION = math.sqrt(M_HE / M_AIR)  # molecular-flow He to air factor

VALID_METHODS = (
    "pressure-decay",
    "vacuum-decay",
    "bubble",
    "helium-sniffer",
    "helium-mass-spectrometer-hood",
)


def _require_finite_positive(value, name):
    """Raise ValueError unless value is a positive finite number."""
    if value is None or not math.isfinite(value) or value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _decay_rate_sccs(volume_L, dP_bar, time_s, temp_K):
    """Shared decay math: q = V_cc * dP_atm / time_s * (STD_TEMP_K / temp_K).

    dP in bar converted to atm (BAR_TO_ATM), volume in L converted to cc.
    Returns the leak rate in scc/s at standard temperature.
    """
    _require_finite_positive(volume_L, "volume_L")
    _require_finite_positive(time_s, "time_s")
    _require_finite_positive(temp_K, "temp_K")
    if dP_bar is None or not math.isfinite(dP_bar) or dP_bar < 0:
        raise ValueError("dP_bar must be non-negative, got %r" % (dP_bar,))
    volume_cc = volume_L * 1000.0
    dP_atm = dP_bar * BAR_TO_ATM
    return volume_cc * dP_atm / time_s * (STD_TEMP_K / temp_K)


def pressure_decay_rate(volume_L, dP_bar, time_s, temp_K=STD_TEMP_K):
    """Leak rate in scc/s from a pressure decay test on an enclosed volume.

    volume_L is the part internal volume, dP_bar the measured pressure drop
    over time_s. ValueError on volume <= 0, time <= 0, temp <= 0, dP < 0.
    """
    return _decay_rate_sccs(volume_L, dP_bar, time_s, temp_K)


def vacuum_decay_rate(chamber_volume_L, dP_bar, time_s, temp_K=STD_TEMP_K):
    """Leak rate in scc/s from a vacuum decay (pressure rise) test.

    Same decay math as pressure_decay_rate; the vocabulary names the vacuum
    chamber test in which dP_bar is the pressure rise in the evacuated
    chamber over time_s. ValueError on the same non-physical inputs.
    """
    return _decay_rate_sccs(chamber_volume_L, dP_bar, time_s, temp_K)


def gauge_resolution_time(volume_L, gauge_res_bar, target_sccs, temp_K=STD_TEMP_K):
    """Seconds needed so a target leak produces a drop above the gauge resolution.

    Inverts the decay equation: t = V_cc * dP_atm / target. gauge_res_bar is
    the smallest pressure increment the gauge reads, target_sccs the smallest
    leak that must be caught. ValueError on non-positive volume, resolution,
    target or temperature.
    """
    _require_finite_positive(volume_L, "volume_L")
    _require_finite_positive(gauge_res_bar, "gauge_res_bar")
    _require_finite_positive(target_sccs, "target_sccs")
    _require_finite_positive(temp_K, "temp_K")
    volume_cc = volume_L * 1000.0
    dP_atm = gauge_res_bar * BAR_TO_ATM
    return volume_cc * dP_atm / target_sccs * (STD_TEMP_K / temp_K)


def helium_to_air(q_he_sccs):
    """Convert a helium leak to the equivalent air leak (molecular flow).

    q_air = q_he * sqrt(M_HE / M_AIR). Molecular flow is the documented
    typical relation; viscous flow sits closer to the viscosity ratio.
    ValueError on a negative helium leak.
    """
    if q_he_sccs is None or not math.isfinite(q_he_sccs) or q_he_sccs < 0:
        raise ValueError("q_he_sccs must be non-negative, got %r" % (q_he_sccs,))
    return q_he_sccs * GAS_CONVERSION


def air_to_helium(q_air_sccs):
    """Convert an air leak to the equivalent helium leak (inverse of helium_to_air)."""
    if q_air_sccs is None or not math.isfinite(q_air_sccs) or q_air_sccs < 0:
        raise ValueError("q_air_sccs must be non-negative, got %r" % (q_air_sccs,))
    return q_air_sccs / GAS_CONVERSION


def bubble_leak_rate(bubble_diameter_mm, bubbles_per_s):
    """Leak rate in scc/s from an immersion bubble observation.

    Per bubble volume = (4/3) * pi * (d/2)^3 with d in cm (diameter in mm
    divided by 10), rate = per bubble volume in cc times bubbles per second.
    ValueError on negative diameter or negative bubble count.
    """
    if bubble_diameter_mm is None or not math.isfinite(bubble_diameter_mm) or bubble_diameter_mm < 0:
        raise ValueError("bubble_diameter_mm must be non-negative, got %r" % (bubble_diameter_mm,))
    if bubbles_per_s is None or not math.isfinite(bubbles_per_s) or bubbles_per_s < 0:
        raise ValueError("bubbles_per_s must be non-negative, got %r" % (bubbles_per_s,))
    radius_cm = bubble_diameter_mm / 10.0 / 2.0
    volume_cc = (4.0 / 3.0) * math.pi * radius_cm ** 3
    return volume_cc * bubbles_per_s


def method_recommendation(required_sensitivity_sccs, access_both_sides,
                          need_localization, part_pressure_capable):
    """Recommend the leak test method from sensitivity and access.

    Returns (method, rationale). Deterministic priority chain with the module
    thresholds:
      1. helium mass spectrometer hood when sensitivity <= MS_THRESHOLD (1e-6);
      2. helium sniffer when localization is needed and sensitivity <=
         SNIFFER_THRESHOLD (1e-5);
      3. pressure decay when only one side is accessible and the part holds
         pressure; vacuum decay when only one side is accessible and the part
         cannot take internal pressure but can be evacuated (documented
         assumption: the decay branch picks pressure or vacuum by the part
         pressure capability);
      4. bubble (immersion) when localization is needed and sensitivity <=
         BUBBLE_THRESHOLD (1e-2);
      5. else pressure decay.
    ValueError on a non-positive required sensitivity.
    """
    _require_finite_positive(required_sensitivity_sccs, "required_sensitivity_sccs")
    if required_sensitivity_sccs <= MS_THRESHOLD:
        return ("helium-mass-spectrometer-hood",
                "required sensitivity %.1e scc/s is at or below the 1e-6 scc/s "
                "hood threshold; a helium mass spectrometer resolves leaks down "
                "to about %g scc/s He" % (required_sensitivity_sccs, HELIUM_MS_MIN_DETECT_SCCS))
    if need_localization and required_sensitivity_sccs <= SNIFFER_THRESHOLD:
        return ("helium-sniffer",
                "localization needed and required sensitivity %.1e scc/s is at "
                "or below the 1e-5 scc/s sniffer threshold" % required_sensitivity_sccs)
    if not access_both_sides:
        if part_pressure_capable:
            return ("pressure-decay",
                    "only one side accessible and the part holds pressure, so "
                    "a decay test on the sealed internal volume fits")
        return ("vacuum-decay",
                "only one side accessible and the part cannot take internal "
                "pressure, so an evacuated-chamber decay test fits")
    if need_localization and required_sensitivity_sccs <= BUBBLE_THRESHOLD:
        return ("bubble",
                "localization needed and required sensitivity %.1e scc/s is at "
                "or below the 1e-2 scc/s bubble immersion threshold" % required_sensitivity_sccs)
    return ("pressure-decay",
            "no tighter constraint applies, so pressurize the sealed volume "
            "and watch the pressure decay")


def disposition(measured_sccs, max_allowable_sccs, method):
    """Disposition a measured leak rate against the maximum allowable.

    Returns dict {verdict, margin_db}: accept when measured <= max_allowable;
    reject when measured exceeds max_allowable and the ratio measured over
    allowable exceeds REVIEW_RATIO (1.25); review in the band in between.
    margin_db = 10 * log10(max_allowable / measured), positive on accept.
    ValueError on non-positive allowable, negative measured, unknown method.
    """
    _require_finite_positive(max_allowable_sccs, "max_allowable_sccs")
    if measured_sccs is None or not math.isfinite(measured_sccs) or measured_sccs < 0:
        raise ValueError("measured_sccs must be non-negative, got %r" % (measured_sccs,))
    if method not in VALID_METHODS:
        raise ValueError("unknown method %r, expected one of %s"
                         % (method, ", ".join(VALID_METHODS)))
    margin_db = 10.0 * math.log10(max_allowable_sccs / measured_sccs) \
        if measured_sccs > 0 else float("inf")
    if measured_sccs <= max_allowable_sccs:
        verdict = "accept"
    elif measured_sccs > REVIEW_RATIO * max_allowable_sccs:
        verdict = "reject"
    else:
        verdict = "review"
    return {"verdict": verdict, "margin_db": margin_db}


def helium_ms_verdict(detected_sccs_he, limit_sccs_air,
                      method="helium-mass-spectrometer-hood"):
    """Acceptance verdict from a helium mass spectrometer reading.

    Converts the detected helium leak to the air-equivalent leak with
    helium_to_air, then dispositions it against the air limit with
    disposition. Returns the disposition dict.
    """
    air_equivalent = helium_to_air(detected_sccs_he)
    return disposition(air_equivalent, limit_sccs_air, method)


def summarize(volume_L, dP_bar, time_s, max_allowable_sccs,
              method="pressure-decay", temp_K=STD_TEMP_K):
    """One-call summary for a decay test: leak rate plus disposition.

    Returns dict {leak_rate_sccs, method, verdict, margin_db}.
    """
    rate = pressure_decay_rate(volume_L, dP_bar, time_s, temp_K)
    outcome = disposition(rate, max_allowable_sccs, method)
    return {"leak_rate_sccs": rate, "method": method,
            "verdict": outcome["verdict"], "margin_db": outcome["margin_db"]}
