#!/usr/bin/env python3
"""Level-two multicarrier multipaction envelope sweep.

Anchor: ECSS-E-ST-20-01C clause 5.3.2.3.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Physics implemented here
------------------------
An equally spaced, equal-amplitude carrier set beats into a periodic
envelope. The carrier voltages add coherently once per beat period
1/spacing, so the envelope peak power reaches ``N**2`` times the power of
one carrier while the mean total power is only ``N`` times it. A
multipaction discharge, however, does not follow the instantaneous
envelope: free electrons need a minimum number of gap crossings before
the avalanche is established, so the envelope must stay above the
single-carrier breakdown level for at least that long. The level-two
method therefore sweeps candidate pulse widths, reads the single-carrier
breakdown level that the pulsed susceptibility data attaches to each
width, and reports the pair that leaves the least headroom: the
worst-case pulse width and the minimum breakdown level it governs.

Envelope model (normalised voltage, peak = 1)::

    E(t) = | sin(N * pi * spacing * t) / (N * sin(pi * spacing * t)) |

The main lobe of E runs from ``-1/(N*spacing)`` to ``+1/(N*spacing)``,
so no pulse wider than ``2/(N*spacing)`` exists in the envelope at any
non-zero level.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEFAULT_SUSTAINING_CROSSINGS = 20
"""Gap crossings an electron must complete before the avalanche holds."""

_REL_TOL = 1e-9
_ABS_TOL = 1e-15
_SPACING_REL_TOL = 1e-6


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Durations here are differences of reciprocals and margins are sums of
    logarithms, so an exactly-compliant case can land a few ULPs on the
    wrong side. The engineering limit is unchanged; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def gap_crossing_time_s(frequency_hz):
    """Time for one electron transit of a resonant parallel-plate gap.

    At the fundamental resonance the electron crosses in half an RF
    period, so the crossing time is ``1/(2*f)``.
    """
    freq = _require_positive("frequency_hz", frequency_hz)
    return 1.0 / (2.0 * freq)


def sustaining_pulse_width_s(frequency_hz, crossings=DEFAULT_SUSTAINING_CROSSINGS):
    """Shortest envelope pulse able to sustain a discharge at ``frequency_hz``."""
    if isinstance(crossings, bool) or not isinstance(crossings, int):
        raise ValueError("crossings must be an int, got %r" % (crossings,))
    if crossings < 1:
        raise ValueError("crossings must be at least 1, got %d" % crossings)
    return crossings * gap_crossing_time_s(frequency_hz)


def carrier_spacing_hz(carrier_frequencies):
    """Uniform spacing of a carrier comb, rejecting a non-uniform set."""
    if not isinstance(carrier_frequencies, (list, tuple)):
        raise ValueError("carrier_frequencies must be a list or tuple")
    if len(carrier_frequencies) < 2:
        raise ValueError(
            "a multicarrier case needs at least 2 carriers, got %d"
            % len(carrier_frequencies)
        )
    freqs = [_require_positive("carrier frequency", f) for f in carrier_frequencies]
    ordered = sorted(freqs)
    spacing = ordered[1] - ordered[0]
    if spacing <= 0.0:
        raise ValueError("carrier frequencies must be distinct")
    for lower, upper in zip(ordered, ordered[1:]):
        step = upper - lower
        if not math.isclose(step, spacing, rel_tol=_SPACING_REL_TOL):
            raise ValueError(
                "carrier comb is not uniformly spaced: found %g Hz and %g Hz"
                % (spacing, step)
            )
    return spacing


def peak_envelope_power_w(carrier_powers_w):
    """Peak beat power of the carrier set: voltages add, so powers root-sum.

    For ``N`` equal carriers of power ``P`` this returns ``N**2 * P``.
    """
    if not isinstance(carrier_powers_w, (list, tuple)):
        raise ValueError("carrier_powers_w must be a list or tuple")
    if len(carrier_powers_w) < 2:
        raise ValueError(
            "a multicarrier case needs at least 2 carrier powers, got %d"
            % len(carrier_powers_w)
        )
    root_sum = 0.0
    for power in carrier_powers_w:
        root_sum += math.sqrt(_require_positive("carrier power", power))
    return root_sum * root_sum


def main_lobe_base_width_s(n_carriers, spacing_hz):
    """Full width of the envelope main lobe between its first two nulls."""
    if isinstance(n_carriers, bool) or not isinstance(n_carriers, int):
        raise ValueError("n_carriers must be an int, got %r" % (n_carriers,))
    if n_carriers < 2:
        raise ValueError("n_carriers must be at least 2, got %d" % n_carriers)
    spacing = _require_positive("spacing_hz", spacing_hz)
    return 2.0 / (n_carriers * spacing)


def envelope_voltage_ratio(n_carriers, spacing_hz, time_s):
    """Normalised envelope voltage at ``time_s`` from a beat peak (peak = 1)."""
    if isinstance(n_carriers, bool) or not isinstance(n_carriers, int):
        raise ValueError("n_carriers must be an int, got %r" % (n_carriers,))
    if n_carriers < 2:
        raise ValueError("n_carriers must be at least 2, got %d" % n_carriers)
    spacing = _require_positive("spacing_hz", spacing_hz)
    if not _is_finite_number(time_s):
        raise ValueError("time_s must be a finite number, got %r" % (time_s,))
    phase = math.pi * spacing * float(time_s)
    denominator = math.sin(phase)
    if abs(denominator) < 1e-14:
        # Beat peak: every carrier is in phase and the ratio limit is 1.
        return 1.0
    return abs(math.sin(n_carriers * phase) / (n_carriers * denominator))


def envelope_power_ratio_for_pulse_width(n_carriers, spacing_hz, pulse_width_s):
    """Highest envelope power ratio held for at least ``pulse_width_s``.

    The envelope spends ``pulse_width_s`` above the level reached half a
    pulse width either side of a beat peak. A width at or beyond the main
    lobe base width exists at no positive level, which returns 0.0.
    """
    width = _require_non_negative("pulse_width_s", pulse_width_s)
    lobe = main_lobe_base_width_s(n_carriers, spacing_hz)
    if _at_least(width, lobe):
        return 0.0
    ratio = envelope_voltage_ratio(n_carriers, spacing_hz, width / 2.0)
    return ratio * ratio


def normalise_susceptibility_table(table):
    """Validate and order the pulsed single-carrier susceptibility data.

    Each entry maps a pulse width to the single-carrier breakdown power
    measured (or derived) for a pulse of that width.
    """
    if not isinstance(table, (list, tuple)) or not table:
        raise ValueError("susceptibility table must be a non-empty list")
    rows = []
    seen = []
    for entry in table:
        if not isinstance(entry, dict):
            raise ValueError("susceptibility entry must be a mapping, got %r" % (entry,))
        missing = {"pulse_width_s", "breakdown_power_w"} - set(entry)
        if missing:
            raise ValueError(
                "susceptibility entry missing key(s): %s" % ", ".join(sorted(missing))
            )
        width = _require_positive("pulse_width_s", entry["pulse_width_s"])
        power = _require_positive("breakdown_power_w", entry["breakdown_power_w"])
        for previous in seen:
            if math.isclose(previous, width, rel_tol=_REL_TOL):
                raise ValueError("duplicate pulse width %g s in susceptibility table" % width)
        seen.append(width)
        rows.append({"pulse_width_s": width, "breakdown_power_w": power})
    rows.sort(key=lambda row: row["pulse_width_s"])
    return tuple(rows)


def sweep_envelope_pulse_widths(
    carrier_frequencies,
    carrier_powers_w,
    susceptibility_table,
    crossings=DEFAULT_SUSTAINING_CROSSINGS,
):
    """Evaluate every tabulated pulse width against the beat envelope.

    Returns one point per table row carrying the envelope level held for
    that width, whether the width is long enough to sustain a discharge,
    whether the envelope can hold it at all, and the headroom ratio
    (breakdown power divided by the envelope power at that width).
    """
    if not isinstance(carrier_frequencies, (list, tuple)):
        raise ValueError("carrier_frequencies must be a list or tuple")
    if not isinstance(carrier_powers_w, (list, tuple)):
        raise ValueError("carrier_powers_w must be a list or tuple")
    if len(carrier_frequencies) != len(carrier_powers_w):
        raise ValueError(
            "carrier_frequencies (%d) and carrier_powers_w (%d) must be the same length"
            % (len(carrier_frequencies), len(carrier_powers_w))
        )
    spacing = carrier_spacing_hz(carrier_frequencies)
    n_carriers = len(carrier_frequencies)
    peak_power = peak_envelope_power_w(carrier_powers_w)
    centre_frequency = sum(float(f) for f in carrier_frequencies) / n_carriers
    sustaining = sustaining_pulse_width_s(centre_frequency, crossings)
    rows = normalise_susceptibility_table(susceptibility_table)
    points = []
    for row in rows:
        width = row["pulse_width_s"]
        level_ratio = envelope_power_ratio_for_pulse_width(n_carriers, spacing, width)
        envelope_power = peak_power * level_ratio
        reachable = level_ratio > 0.0
        sustains = _at_least(width, sustaining)
        headroom = (
            row["breakdown_power_w"] / envelope_power if reachable else float("inf")
        )
        points.append(
            {
                "pulse_width_s": width,
                "breakdown_power_w": row["breakdown_power_w"],
                "envelope_power_ratio": level_ratio,
                "envelope_power_w": envelope_power,
                "reachable": reachable,
                "sustains": sustains,
                "governing": bool(reachable and sustains),
                "headroom_ratio": headroom,
            }
        )
    return {
        "n_carriers": n_carriers,
        "spacing_hz": spacing,
        "centre_frequency_hz": centre_frequency,
        "peak_envelope_power_w": peak_power,
        "beat_period_s": 1.0 / spacing,
        "gap_crossing_time_s": gap_crossing_time_s(centre_frequency),
        "sustaining_pulse_width_s": sustaining,
        "main_lobe_base_width_s": main_lobe_base_width_s(n_carriers, spacing),
        "points": points,
    }


def worst_case_envelope_point(points):
    """Governing sweep point: least headroom among the sustaining, reachable ones."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("points must be a non-empty list")
    governing = [p for p in points if p.get("governing")]
    if not governing:
        return None
    return min(
        governing, key=lambda p: (p["headroom_ratio"], p["pulse_width_s"])
    )


def multipaction_margin_db(breakdown_power_w, operating_power_w):
    """Margin of the breakdown level over the operating level, in decibel."""
    breakdown = _require_positive("breakdown_power_w", breakdown_power_w)
    operating = _require_positive("operating_power_w", operating_power_w)
    return 10.0 * math.log10(breakdown / operating)


def assess_level_two_multicarrier(
    carrier_frequencies,
    carrier_powers_w,
    susceptibility_table,
    required_margin_db,
    crossings=DEFAULT_SUSTAINING_CROSSINGS,
):
    """Full level-two envelope sweep with a verdict and findings."""
    required = _require_non_negative("required_margin_db", required_margin_db)
    sweep = sweep_envelope_pulse_widths(
        carrier_frequencies, carrier_powers_w, susceptibility_table, crossings
    )
    points = sweep["points"]
    findings = []
    for point in points:
        if not point["sustains"]:
            findings.append(
                "susceptibility row at %.3e s is shorter than the sustaining "
                "pulse width %.3e s and cannot substantiate a level-two case"
                % (point["pulse_width_s"], sweep["sustaining_pulse_width_s"])
            )
        elif not point["reachable"]:
            findings.append(
                "susceptibility row at %.3e s exceeds the envelope main lobe "
                "base width %.3e s; the beat never holds a pulse that long"
                % (point["pulse_width_s"], sweep["main_lobe_base_width_s"])
            )
    worst = worst_case_envelope_point(points)
    result = dict(sweep)
    result["required_margin_db"] = required
    result["findings"] = findings
    if worst is None:
        result.update(
            {
                "verdict": "no-sustaining-envelope-pulse",
                "worst_case_pulse_width_s": None,
                "governing_breakdown_power_w": None,
                "minimum_breakdown_peak_power_w": None,
                "margin_db": None,
                "compliant": True,
            }
        )
        findings.append(
            "no tabulated pulse width is both long enough to sustain a "
            "discharge and short enough for the beat envelope to hold"
        )
        return result
    margin = multipaction_margin_db(
        worst["breakdown_power_w"], worst["envelope_power_w"]
    )
    compliant = _at_least(margin, required)
    result.update(
        {
            "verdict": "margin-met" if compliant else "margin-not-met",
            "worst_case_pulse_width_s": worst["pulse_width_s"],
            "governing_breakdown_power_w": worst["breakdown_power_w"],
            "minimum_breakdown_peak_power_w": worst["headroom_ratio"]
            * sweep["peak_envelope_power_w"],
            "margin_db": margin,
            "compliant": compliant,
        }
    )
    if not compliant:
        findings.append(
            "worst-case pulse width %.3e s leaves %.3f dB against a required "
            "%.3f dB" % (worst["pulse_width_s"], margin, required)
        )
    return result
