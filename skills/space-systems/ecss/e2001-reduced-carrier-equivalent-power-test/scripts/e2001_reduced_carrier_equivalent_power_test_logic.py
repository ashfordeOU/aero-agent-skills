#!/usr/bin/env python3
"""Reduced-carrier equivalent-power multipaction verification logic.

Anchor: ECSS-E-ST-20-01C clause 6.4.3.3 -- multi-frequency multipaction
verification run with fewer carriers, each raised so the retained set
still delivers an equivalent drive. The clause is paraphrased into an
implementable procedure; no verbatim standard text is reproduced here.

Engineering model
-----------------
Peak envelope voltage across the critical gap scales with the sum of
the individual carrier voltages, i.e. with the sum of square-root
carrier powers. A reduced set of M carriers reproduces the operational
peak when each retained carrier carries

    P_reduced = ( sum_i sqrt(P_i) / M ) ** 2

so the retained set draws only 1/M of the average power that a single
equivalent continuous-wave carrier would demand, which is why the
reduced route survives bench limits that defeat clause 6.4.3.2.

Matching the peak is necessary but not sufficient. The envelope of M
equal carriers spaced by df is the Dirichlet kernel

    V(t) / V_peak = | sin(M*pi*df*t) / (M * sin(pi*df*t)) |

which touches its peak only briefly and repeats every 1/df. Multipaction
needs roughly twenty electron transits of the gap while the envelope
stays above the multipaction onset voltage, so the dwell of the main
lobe above that onset -- not merely the peak value -- decides whether a
reduced set is a valid stand-in. Fewer carriers at the same spacing
widen the main lobe, so the reduction is normally more severe on dwell;
widening the spacing at the same time can silently reverse that, which
is the case this module exists to catch.

Only the python3 standard library is used; every function is offline
and deterministic.
"""

import math

__all__ = [
    "MIN_GAP_CROSSINGS",
    "POWER_REL_TOL",
    "SPACING_REL_TOL",
    "validate_carrier_set",
    "envelope_voltage_sum",
    "total_average_power_w",
    "validate_reduction_count",
    "reduced_carrier_power_w",
    "reduced_set_average_power_w",
    "carrier_spacing_hz",
    "onset_voltage_ratio",
    "envelope_amplitude_ratio",
    "envelope_dwell_above_ratio_s",
    "electron_transit_time_s",
    "gap_crossings_in_dwell",
    "power_ratio_db",
    "assess_reduced_carrier_equivalent_power_test",
    "categorize_reduction",
    "summarize_report",
]

# Electron avalanche growth needs roughly twenty transits of the gap
# while the envelope stays above the multipaction onset voltage.
MIN_GAP_CROSSINGS = 20

POWER_REL_TOL = 1e-9
SPACING_REL_TOL = 1e-6
_DWELL_REL_TOL = 1e-9
_BISECTION_STEPS = 200
_MAX_RESONANT_ORDER = 21
_DEFAULT_MARGIN_DB = 6.0


def _is_finite_number(value):
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _not_below(value, limit, rel_tol=_DWELL_REL_TOL):
    """value >= limit, absorbing representation error at the boundary."""
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=rel_tol, abs_tol=0.0)


def _not_above(value, limit, rel_tol=POWER_REL_TOL):
    """value <= limit, absorbing representation error at the boundary."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=rel_tol, abs_tol=0.0)


def validate_carrier_set(carriers):
    """Normalize and check an operational carrier set (see clause anchor)."""
    if not isinstance(carriers, (list, tuple)):
        raise ValueError("carrier set must be a list or tuple of carrier mappings")
    if len(carriers) == 0:
        raise ValueError("carrier set is empty; at least one carrier is required")
    seen_ids = set()
    normalized = []
    for index, carrier in enumerate(carriers):
        if not isinstance(carrier, dict):
            raise ValueError("carrier at position %d is not a mapping" % index)
        carrier_id = carrier.get("id")
        if not isinstance(carrier_id, str) or not carrier_id.strip():
            raise ValueError("carrier at position %d needs a non-empty string id" % index)
        carrier_id = carrier_id.strip()
        if carrier_id in seen_ids:
            raise ValueError("duplicate carrier id %r in carrier set" % carrier_id)
        seen_ids.add(carrier_id)
        power = carrier.get("power_w")
        if not _is_finite_number(power) or float(power) <= 0.0:
            raise ValueError("carrier %r needs a finite positive power_w" % carrier_id)
        frequency = carrier.get("frequency_hz")
        if not _is_finite_number(frequency) or float(frequency) <= 0.0:
            raise ValueError("carrier %r needs a finite positive frequency_hz" % carrier_id)
        normalized.append(
            {
                "id": carrier_id,
                "power_w": float(power),
                "frequency_hz": float(frequency),
            }
        )
    normalized.sort(key=lambda item: (item["frequency_hz"], item["id"]))
    return normalized


def envelope_voltage_sum(carriers):
    """Sum of square-root carrier powers, proportional to peak envelope voltage."""
    validated = validate_carrier_set(carriers)
    return math.fsum(math.sqrt(item["power_w"]) for item in validated)


def total_average_power_w(carriers):
    """Total average power carried by the operational carrier set."""
    validated = validate_carrier_set(carriers)
    return math.fsum(item["power_w"] for item in validated)


def validate_reduction_count(carriers, reduced_count):
    """Check a proposed retained-carrier count against the operational set."""
    validated = validate_carrier_set(carriers)
    if isinstance(reduced_count, bool) or not isinstance(reduced_count, int):
        raise ValueError("reduced_count must be a positive integer")
    if reduced_count < 1:
        raise ValueError("reduced_count must be at least 1")
    if reduced_count >= len(validated):
        raise ValueError(
            "reduced_count %d does not reduce a set of %d carriers"
            % (reduced_count, len(validated))
        )
    return len(validated)


def reduced_carrier_power_w(carriers, reduced_count):
    """Per-carrier drive that keeps the reduced set at the operational peak."""
    validate_reduction_count(carriers, reduced_count)
    per_carrier_voltage = envelope_voltage_sum(carriers) / float(reduced_count)
    return per_carrier_voltage * per_carrier_voltage


def reduced_set_average_power_w(carriers, reduced_count):
    """Total average power the reduced set draws from the bench."""
    return reduced_carrier_power_w(carriers, reduced_count) * float(reduced_count)


def carrier_spacing_hz(carriers, rel_tol=SPACING_REL_TOL):
    """Uniform carrier spacing of a set, in hertz."""
    validated = validate_carrier_set(carriers)
    if len(validated) < 2:
        raise ValueError("carrier spacing needs at least two carriers")
    if not _is_finite_number(rel_tol) or float(rel_tol) <= 0.0:
        raise ValueError("rel_tol must be a finite positive fraction")
    gaps = []
    for lower, upper in zip(validated, validated[1:]):
        gap = upper["frequency_hz"] - lower["frequency_hz"]
        if gap <= 0.0:
            raise ValueError(
                "carriers %r and %r share a frequency; spacing is undefined"
                % (lower["id"], upper["id"])
            )
        gaps.append(gap)
    reference = gaps[0]
    for gap in gaps[1:]:
        if not math.isclose(gap, reference, rel_tol=float(rel_tol), abs_tol=0.0):
            raise ValueError(
                "carrier set is not uniformly spaced (%g Hz vs %g Hz)" % (gap, reference)
            )
    return reference


def onset_voltage_ratio(margin_db=_DEFAULT_MARGIN_DB):
    """Multipaction onset voltage as a fraction of the peak envelope voltage.

    A power margin of m dB puts the peak 10**(m/20) above the onset in
    voltage, so the onset sits at 10**(-m/20) of the peak.
    """
    if not _is_finite_number(margin_db) or float(margin_db) < 0.0:
        raise ValueError("margin_db must be a finite non-negative decibel value")
    return 10.0 ** (-float(margin_db) / 20.0)


def envelope_amplitude_ratio(n_carriers, normalized_offset):
    """Envelope magnitude relative to its peak at a normalized time offset.

    ``normalized_offset`` is time multiplied by carrier spacing, so one
    unit is one envelope repetition period.
    """
    if isinstance(n_carriers, bool) or not isinstance(n_carriers, int):
        raise ValueError("n_carriers must be a positive integer")
    if n_carriers < 1:
        raise ValueError("n_carriers must be at least 1")
    if not _is_finite_number(normalized_offset):
        raise ValueError("normalized_offset must be a finite number")
    offset = float(normalized_offset)
    denominator = math.sin(math.pi * offset)
    if abs(denominator) < 1e-12:
        return 1.0
    return abs(math.sin(n_carriers * math.pi * offset) / (n_carriers * denominator))


def envelope_dwell_above_ratio_s(n_carriers, spacing_hz, threshold_ratio):
    """Time per envelope period spent above a fraction of the peak.

    A single carrier is continuous-wave, so its dwell is unbounded and
    math.inf is returned. For two or more carriers the main lobe of the
    envelope is solved by bisection between the peak and the first null.
    """
    if isinstance(n_carriers, bool) or not isinstance(n_carriers, int):
        raise ValueError("n_carriers must be a positive integer")
    if n_carriers < 1:
        raise ValueError("n_carriers must be at least 1")
    if not _is_finite_number(spacing_hz) or float(spacing_hz) <= 0.0:
        raise ValueError("spacing_hz must be a finite positive frequency")
    if not _is_finite_number(threshold_ratio):
        raise ValueError("threshold_ratio must be a finite fraction")
    ratio = float(threshold_ratio)
    if not 0.0 < ratio < 1.0:
        raise ValueError("threshold_ratio must lie strictly between 0 and 1")
    if n_carriers == 1:
        return math.inf
    low = 0.0
    high = 1.0 / float(n_carriers)
    for _ in range(_BISECTION_STEPS):
        mid = 0.5 * (low + high)
        if envelope_amplitude_ratio(n_carriers, mid) > ratio:
            low = mid
        else:
            high = mid
        if high - low < 1e-16:
            break
    half_width = 0.5 * (low + high)
    return 2.0 * half_width / float(spacing_hz)


def electron_transit_time_s(frequency_hz, resonant_order=1):
    """Time for one electron transit of the gap at a resonant order."""
    if not _is_finite_number(frequency_hz) or float(frequency_hz) <= 0.0:
        raise ValueError("frequency_hz must be a finite positive frequency")
    if isinstance(resonant_order, bool) or not isinstance(resonant_order, int):
        raise ValueError("resonant_order must be an odd positive integer")
    if resonant_order < 1 or resonant_order > _MAX_RESONANT_ORDER:
        raise ValueError("resonant_order must lie between 1 and %d" % _MAX_RESONANT_ORDER)
    if resonant_order % 2 == 0:
        raise ValueError("resonant_order must be odd (even orders are not resonant)")
    return float(resonant_order) / (2.0 * float(frequency_hz))


def gap_crossings_in_dwell(dwell_s, frequency_hz, resonant_order=1):
    """Number of gap transits an envelope dwell supports."""
    if dwell_s == math.inf:
        return math.inf
    if not _is_finite_number(dwell_s) or float(dwell_s) < 0.0:
        raise ValueError("dwell_s must be a finite non-negative duration or math.inf")
    return float(dwell_s) / electron_transit_time_s(frequency_hz, resonant_order)


def power_ratio_db(numerator_w, denominator_w):
    """Ratio of two powers expressed in decibels."""
    if not _is_finite_number(numerator_w) or float(numerator_w) <= 0.0:
        raise ValueError("numerator_w must be a finite positive power in watts")
    if not _is_finite_number(denominator_w) or float(denominator_w) <= 0.0:
        raise ValueError("denominator_w must be a finite positive power in watts")
    return 10.0 * math.log10(float(numerator_w) / float(denominator_w))


def assess_reduced_carrier_equivalent_power_test(
    carriers,
    reduced_count,
    reduced_spacing_hz=None,
    margin_db=_DEFAULT_MARGIN_DB,
    source_max_power_per_carrier_w=None,
    resonant_order=1,
):
    """Full clause 6.4.3.3 assessment of a reduced-carrier substitution.

    Returns a report mapping with the per-carrier drive, the envelope
    dwell of both configurations, the electron-gap-crossing counts they
    support, and every finding that blocks the reduction.
    """
    validated = validate_carrier_set(carriers)
    operational_count = validate_reduction_count(carriers, reduced_count)
    operational_spacing = carrier_spacing_hz(validated)
    if reduced_spacing_hz is None:
        spacing = operational_spacing
    else:
        if not _is_finite_number(reduced_spacing_hz) or float(reduced_spacing_hz) <= 0.0:
            raise ValueError("reduced_spacing_hz must be a finite positive frequency")
        spacing = float(reduced_spacing_hz)
    ratio = onset_voltage_ratio(margin_db)
    voltage_sum = math.fsum(math.sqrt(item["power_w"]) for item in validated)
    per_carrier_w = (voltage_sum / float(reduced_count)) ** 2
    reduced_average_w = per_carrier_w * float(reduced_count)
    operational_average_w = math.fsum(item["power_w"] for item in validated)
    governing_frequency = max(item["frequency_hz"] for item in validated)

    operational_dwell = envelope_dwell_above_ratio_s(
        operational_count, operational_spacing, ratio
    )
    reduced_dwell = envelope_dwell_above_ratio_s(reduced_count, spacing, ratio)
    operational_crossings = gap_crossings_in_dwell(
        operational_dwell, governing_frequency, resonant_order
    )
    reduced_crossings = gap_crossings_in_dwell(
        reduced_dwell, governing_frequency, resonant_order
    )

    findings = []
    reconstructed = float(reduced_count) * math.sqrt(per_carrier_w)
    if not math.isclose(reconstructed, voltage_sum, rel_tol=POWER_REL_TOL, abs_tol=0.0):
        findings.append(
            {
                "code": "reduced-set-does-not-reproduce-peak-envelope-voltage",
                "detail": "retained carriers do not sum back to the operational peak",
            }
        )
    if not _not_below(reduced_crossings, float(MIN_GAP_CROSSINGS)):
        findings.append(
            {
                "code": "insufficient-electron-gap-crossings",
                "detail": "envelope dwell is too short for avalanche growth",
                "value": reduced_crossings,
                "limit": float(MIN_GAP_CROSSINGS),
            }
        )
    if not _not_below(reduced_crossings, operational_crossings):
        findings.append(
            {
                "code": "reduced-dwell-less-severe-than-operational",
                "detail": "the reduction shortens the dwell the article actually sees",
                "value": reduced_crossings,
                "limit": operational_crossings,
            }
        )
    if source_max_power_per_carrier_w is not None:
        if (
            not _is_finite_number(source_max_power_per_carrier_w)
            or float(source_max_power_per_carrier_w) <= 0.0
        ):
            raise ValueError(
                "source_max_power_per_carrier_w must be a finite positive power"
            )
        if not _not_above(per_carrier_w, float(source_max_power_per_carrier_w)):
            findings.append(
                {
                    "code": "reduced-carrier-drive-exceeds-source-capability",
                    "detail": "a retained carrier needs more drive than the bench delivers",
                    "value": per_carrier_w,
                    "limit": float(source_max_power_per_carrier_w),
                }
            )
    if reduced_count == 1:
        findings.append(
            {
                "code": "reduction-degenerates-to-single-carrier",
                "detail": "one retained carrier is the clause 6.4.3.2 case, not 6.4.3.3",
            }
        )

    report = {
        "operational_carrier_count": operational_count,
        "reduced_carrier_count": reduced_count,
        "operational_spacing_hz": operational_spacing,
        "reduced_spacing_hz": spacing,
        "onset_voltage_ratio": ratio,
        "margin_db": float(margin_db),
        "envelope_voltage_sum_sqrt_w": voltage_sum,
        "reduced_carrier_power_w": per_carrier_w,
        "reduced_set_average_power_w": reduced_average_w,
        "operational_average_power_w": operational_average_w,
        "drive_saving_db": power_ratio_db(voltage_sum * voltage_sum, reduced_average_w),
        "operational_dwell_s": operational_dwell,
        "reduced_dwell_s": reduced_dwell,
        "operational_gap_crossings": operational_crossings,
        "reduced_gap_crossings": reduced_crossings,
        "findings": findings,
        "compliant": len(findings) == 0,
    }
    report["verdict"] = categorize_reduction(report)
    return report


def categorize_reduction(report):
    """Categorize a report into an acceptance outcome token."""
    if not isinstance(report, dict) or "findings" not in report:
        raise ValueError("report must be a mapping produced by the assessment function")
    codes = {finding["code"] for finding in report["findings"]}
    if not codes:
        return "reduced-carrier-equivalent-drive-acceptable"
    if codes == {"reduction-degenerates-to-single-carrier"}:
        return "reduced-carrier-equivalent-drive-out-of-scope"
    return "reduced-carrier-equivalent-drive-not-acceptable"


def summarize_report(report):
    """Render a report as deterministic plain text lines."""
    if not isinstance(report, dict) or "verdict" not in report:
        raise ValueError("report must be a mapping produced by the assessment function")
    lines = [
        "operational carriers: %d" % report["operational_carrier_count"],
        "retained carriers: %d" % report["reduced_carrier_count"],
        "per-carrier drive: %.6g W" % report["reduced_carrier_power_w"],
        "retained set average: %.6g W" % report["reduced_set_average_power_w"],
        "retained gap crossings: %.6g" % report["reduced_gap_crossings"],
        "verdict: %s" % report["verdict"],
    ]
    for finding in report["findings"]:
        lines.append("finding: %s" % finding["code"])
    return "\n".join(lines)
