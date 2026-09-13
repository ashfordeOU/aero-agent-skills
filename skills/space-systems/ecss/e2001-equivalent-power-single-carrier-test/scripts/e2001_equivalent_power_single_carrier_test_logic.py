#!/usr/bin/env python3
"""Single-carrier equivalent-power multipaction verification logic.

Anchor: ECSS-E-ST-20-01C clause 6.4.3.2 -- multi-frequency multipaction
verification performed with one carrier raised to an equivalent power
level. The clause is paraphrased into an implementable procedure; no
verbatim standard text is reproduced here.

Engineering model
-----------------
Multipaction onset in an RF component is governed by the peak voltage
developed across the critical gap, not by the average power flowing
through it. When N carriers share one gap the envelope voltage reaches
its maximum at the instant every carrier is momentarily in phase, so
the peak envelope voltage is proportional to the sum of the individual
carrier voltages:

    V_peak  proportional to  sum_i sqrt(P_i)

A single continuous-wave carrier reproduces that peak voltage when its
power equals the square of that sum:

    P_equiv = ( sum_i sqrt(P_i) ) ** 2

For N equal carriers of power P this collapses to N**2 * P, which is N
times the total average power of the operational spectrum. The
substitution is therefore exact on peak voltage, conservative on
multipaction onset (a continuous-wave drive never leaves the onset
region, so electron avalanche growth is never dwell-limited) and
markedly over-stressing on dissipation, which is the cost the caller
has to budget for.

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
    "equivalent_single_carrier_power_w",
    "power_ratio_db",
    "carrier_spacing_hz",
    "envelope_repetition_period_s",
    "electron_transit_time_s",
    "gap_crossings_in_dwell",
    "apply_test_margin",
    "thermal_over_test_ratio",
    "assess_drive_capability",
    "assess_single_carrier_equivalent_power_test",
    "categorize_substitution",
    "summarize_report",
]

# Electron avalanche growth needs roughly twenty transits of the gap
# before a multipaction discharge is observable; a continuous-wave
# equivalent drive satisfies this trivially, but the constant is kept
# here so the dwell reasoning is explicit rather than assumed.
MIN_GAP_CROSSINGS = 20

# Relative tolerance used only to absorb floating-point representation
# error on comparisons. It never widens an engineering limit: a value
# that is genuinely above a limit stays above it.
POWER_REL_TOL = 1e-9
SPACING_REL_TOL = 1e-6

_MAX_RESONANT_ORDER = 21


def _is_finite_number(value):
    """True for a real, finite int/float (bool is rejected on purpose)."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _not_above(value, limit, rel_tol=POWER_REL_TOL):
    """value <= limit, absorbing representation error at the boundary.

    A sum of square roots squared back up can land a few units in the
    last place above an exactly equal limit; that is a representation
    artefact, not an exceedance, so it is absorbed here rather than by
    relaxing the limit itself.
    """
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=rel_tol, abs_tol=0.0)


def _not_below(value, limit, rel_tol=POWER_REL_TOL):
    """value >= limit, absorbing representation error at the boundary."""
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=rel_tol, abs_tol=0.0)


def validate_carrier_set(carriers):
    """Normalize and check an operational carrier set.

    Each entry is a mapping with a non-empty string ``id``, a finite
    positive ``power_w`` and a finite positive ``frequency_hz``.
    Returns a new list sorted by frequency then id. Raises ValueError on
    any malformed entry.
    """
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
    """Sum of square-root carrier powers, in sqrt(W).

    Proportional to the peak envelope voltage reached when every carrier
    is momentarily in phase across the critical gap.
    """
    validated = validate_carrier_set(carriers)
    return math.fsum(math.sqrt(item["power_w"]) for item in validated)


def total_average_power_w(carriers):
    """Total average power carried by the operational carrier set."""
    validated = validate_carrier_set(carriers)
    return math.fsum(item["power_w"] for item in validated)


def equivalent_single_carrier_power_w(carriers):
    """Continuous-wave power that reproduces the multi-carrier peak voltage."""
    voltage_sum = envelope_voltage_sum(carriers)
    return voltage_sum * voltage_sum


def power_ratio_db(numerator_w, denominator_w):
    """Ratio of two powers expressed in decibels."""
    if not _is_finite_number(numerator_w) or float(numerator_w) <= 0.0:
        raise ValueError("numerator_w must be a finite positive power in watts")
    if not _is_finite_number(denominator_w) or float(denominator_w) <= 0.0:
        raise ValueError("denominator_w must be a finite positive power in watts")
    return 10.0 * math.log10(float(numerator_w) / float(denominator_w))


def carrier_spacing_hz(carriers, rel_tol=SPACING_REL_TOL):
    """Uniform carrier spacing of the operational set, in hertz.

    Raises ValueError for a single carrier, for repeated frequencies, or
    when the spacing is not uniform within ``rel_tol``.
    """
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


def envelope_repetition_period_s(carriers, rel_tol=SPACING_REL_TOL):
    """Period between successive coherent envelope peaks, in seconds."""
    return 1.0 / carrier_spacing_hz(carriers, rel_tol=rel_tol)


def electron_transit_time_s(frequency_hz, resonant_order=1):
    """Time for one electron transit of the gap at a resonant order.

    First-order multipaction resonance puts one transit in half an RF
    period; order n (odd) puts one transit in n half periods.
    """
    if not _is_finite_number(frequency_hz) or float(frequency_hz) <= 0.0:
        raise ValueError("frequency_hz must be a finite positive frequency")
    if isinstance(resonant_order, bool) or not isinstance(resonant_order, int):
        raise ValueError("resonant_order must be an odd positive integer")
    if resonant_order < 1 or resonant_order > _MAX_RESONANT_ORDER:
        raise ValueError(
            "resonant_order must lie between 1 and %d" % _MAX_RESONANT_ORDER
        )
    if resonant_order % 2 == 0:
        raise ValueError("resonant_order must be odd (even orders are not resonant)")
    return float(resonant_order) / (2.0 * float(frequency_hz))


def gap_crossings_in_dwell(dwell_s, frequency_hz, resonant_order=1):
    """Number of gap transits an envelope dwell supports.

    An unbounded dwell (a continuous-wave drive) returns math.inf.
    """
    if dwell_s == math.inf:
        return math.inf
    if not _is_finite_number(dwell_s) or float(dwell_s) < 0.0:
        raise ValueError("dwell_s must be a finite non-negative duration or math.inf")
    transit = electron_transit_time_s(frequency_hz, resonant_order)
    return float(dwell_s) / transit


def apply_test_margin(power_w, margin_db):
    """Raise a drive power by the required multipaction verification margin."""
    if not _is_finite_number(power_w) or float(power_w) <= 0.0:
        raise ValueError("power_w must be a finite positive power in watts")
    if not _is_finite_number(margin_db) or float(margin_db) < 0.0:
        raise ValueError("margin_db must be a finite non-negative decibel value")
    return float(power_w) * (10.0 ** (float(margin_db) / 10.0))


def thermal_over_test_ratio(carriers):
    """Equivalent continuous-wave power divided by operational average power.

    Equals the carrier count for an equal-power set; it is the factor by
    which the substitution over-dissipates relative to flight operation.
    """
    average = total_average_power_w(carriers)
    return equivalent_single_carrier_power_w(carriers) / average


def assess_drive_capability(
    required_drive_power_w,
    source_max_power_w,
    component_peak_power_rating_w,
    rel_tol=POWER_REL_TOL,
):
    """Check the drive chain and the component can carry the equivalent drive.

    Returns a list of finding mappings; an empty list means the drive is
    deliverable without damaging the article under verification.
    """
    if not _is_finite_number(required_drive_power_w) or float(required_drive_power_w) <= 0.0:
        raise ValueError("required_drive_power_w must be a finite positive power")
    if not _is_finite_number(source_max_power_w) or float(source_max_power_w) <= 0.0:
        raise ValueError("source_max_power_w must be a finite positive power")
    if (
        not _is_finite_number(component_peak_power_rating_w)
        or float(component_peak_power_rating_w) <= 0.0
    ):
        raise ValueError("component_peak_power_rating_w must be a finite positive power")
    findings = []
    required = float(required_drive_power_w)
    if not _not_above(required, float(source_max_power_w), rel_tol):
        findings.append(
            {
                "code": "equivalent-drive-exceeds-source-capability",
                "required_w": required,
                "limit_w": float(source_max_power_w),
                "detail": "the amplifier chain cannot reach the equivalent drive level",
            }
        )
    if not _not_above(required, float(component_peak_power_rating_w), rel_tol):
        findings.append(
            {
                "code": "equivalent-drive-exceeds-component-rating",
                "required_w": required,
                "limit_w": float(component_peak_power_rating_w),
                "detail": "the equivalent drive would over-stress the article itself",
            }
        )
    return findings


def assess_single_carrier_equivalent_power_test(
    carriers,
    source_max_power_w,
    component_peak_power_rating_w,
    margin_db=0.0,
    max_thermal_over_test_ratio=None,
    resonant_order=1,
    rel_tol=POWER_REL_TOL,
):
    """Full clause 6.4.3.2 assessment of a single-carrier substitution.

    Returns a report mapping carrying the derived drive level, the
    over-dissipation the substitution imposes, the dwell reasoning and
    every finding that blocks the substitution.
    """
    validated = validate_carrier_set(carriers)
    if max_thermal_over_test_ratio is not None:
        if (
            not _is_finite_number(max_thermal_over_test_ratio)
            or float(max_thermal_over_test_ratio) < 1.0
        ):
            raise ValueError(
                "max_thermal_over_test_ratio must be a finite value of at least 1.0"
            )
    voltage_sum = math.fsum(math.sqrt(item["power_w"]) for item in validated)
    equivalent_w = voltage_sum * voltage_sum
    average_w = math.fsum(item["power_w"] for item in validated)
    required_w = apply_test_margin(equivalent_w, margin_db)
    over_test = equivalent_w / average_w
    peak_frequency = max(item["frequency_hz"] for item in validated)
    transit_s = electron_transit_time_s(peak_frequency, resonant_order)
    findings = assess_drive_capability(
        required_w, source_max_power_w, component_peak_power_rating_w, rel_tol=rel_tol
    )
    if max_thermal_over_test_ratio is not None and not _not_above(
        over_test, float(max_thermal_over_test_ratio), rel_tol
    ):
        findings.append(
            {
                "code": "thermal-over-test-ratio-exceeds-allowance",
                "required_w": over_test,
                "limit_w": float(max_thermal_over_test_ratio),
                "detail": "continuous-wave dissipation exceeds the accepted over-test factor",
            }
        )
    report = {
        "carrier_count": len(validated),
        "carrier_ids": [item["id"] for item in validated],
        "total_average_power_w": average_w,
        "envelope_voltage_sum_sqrt_w": voltage_sum,
        "equivalent_power_w": equivalent_w,
        "margin_db": float(margin_db),
        "required_drive_power_w": required_w,
        "drive_over_average_db": power_ratio_db(required_w, average_w),
        "thermal_over_test_ratio": over_test,
        "electron_transit_time_s": transit_s,
        "gap_crossings": math.inf,
        "dwell_limited": False,
        "findings": findings,
        "compliant": len(findings) == 0,
    }
    report["verdict"] = categorize_substitution(report)
    return report


def categorize_substitution(report):
    """Categorize a report into an acceptance outcome token."""
    if not isinstance(report, dict) or "findings" not in report:
        raise ValueError("report must be a mapping produced by the assessment function")
    codes = {finding["code"] for finding in report["findings"]}
    if not codes:
        return "single-carrier-equivalent-drive-acceptable"
    if codes == {"thermal-over-test-ratio-exceeds-allowance"}:
        return "single-carrier-equivalent-drive-conditional"
    return "single-carrier-equivalent-drive-not-acceptable"


def summarize_report(report):
    """Render a report as deterministic plain text lines."""
    if not isinstance(report, dict) or "verdict" not in report:
        raise ValueError("report must be a mapping produced by the assessment function")
    lines = [
        "carriers: %d" % report["carrier_count"],
        "average power: %.6g W" % report["total_average_power_w"],
        "equivalent drive: %.6g W" % report["equivalent_power_w"],
        "required drive: %.6g W" % report["required_drive_power_w"],
        "over-test factor: %.6g" % report["thermal_over_test_ratio"],
        "verdict: %s" % report["verdict"],
    ]
    for finding in report["findings"]:
        lines.append("finding: %s" % finding["code"])
    return "\n".join(lines)
