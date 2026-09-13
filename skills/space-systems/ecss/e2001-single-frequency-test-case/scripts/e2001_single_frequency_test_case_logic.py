#!/usr/bin/env python3
"""Single multipactor test frequency selection -- ECSS-E-ST-20-01C clause 6.4.2.

Paraphrased, implementable procedure (no standard text is reproduced):

Clause 6.4.2 governs the choice of the one radio-frequency point at which a
single-frequency multipactor test is run. The choice is not free: it has to
land on the worst case of the hardware inside its declared operating band,
and the worst case depends on how the component stores energy.

Two field responses are distinguished, and they lead to opposite choices:

* non-resonant-field hardware (a waveguide run, a coaxial line, a
  connector, a transition) has no internal voltage build-up, so the peak
  field per unit input power is flat across the band and the worst case is
  set purely by the frequency-gap product. Since the multipactor onset
  threshold tracks that product for a fixed critical gap, the low band edge
  is the worst case, taken at the drift-allowance-shifted low edge.
* resonant-field hardware (a cavity filter, an output multiplexer, a
  dielectric-resonator filter) concentrates voltage at its resonances, so
  the worst case is the frequency at which the voltage-magnification of the
  critical gap peaks, read from the measured or modelled field map. Because
  tuning and thermal drift move that resonance, the drift window around the
  selected point is checked against the declared band.

The selected point is then re-expressed as a frequency-gap product and
checked against the validated span of the susceptibility map in use, and the
single point is tested for sufficiency against the band it has to represent.

Every public helper validates its inputs and raises ValueError on data that
cannot carry an engineering conclusion. Standard library only, offline,
deterministic.
"""

import math

# --- engineering parameters (project configurable, not standard text) -------

NON_RESONANT_TYPES = frozenset(
    {
        "waveguide-run",
        "coaxial-line",
        "connector",
        "waveguide-transition",
        "rotary-joint",
        "antenna-feed-horn",
        "waveguide-switch",
    }
)

RESONANT_TYPES = frozenset(
    {
        "cavity-filter",
        "output-multiplexer",
        "input-multiplexer",
        "diplexer",
        "dielectric-resonator-filter",
        "resonant-coupler",
    }
)

DEFAULT_DRIFT_FRACTION = 0.002
"""Tuning and thermal drift allowance on a resonance, as a fraction."""

SUSCEPTIBILITY_MAP_LOW_GHZ_MM = 0.1
SUSCEPTIBILITY_MAP_HIGH_GHZ_MM = 100.0
"""Validated span of the frequency-gap product chart the assessment reads."""

HZ_M_PER_GHZ_MM = 1.0e6
"""One GHz.mm expressed in Hz.m."""

REL_TOLERANCE = 1e-9
"""Relative tolerance absorbing floating-point representation error at band
edges. It never widens an engineering limit: it only stops a comparison that
is exact in real arithmetic from failing by a few units in the last place."""


# --- validation helpers -----------------------------------------------------


def _require_positive(value, label):
    """Return ``value`` as a float, or raise ValueError when unusable."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return value


def _require_fraction(value, label):
    """Return a non-negative fraction below 1.0, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0.0 or value >= 1.0:
        raise ValueError("%s must lie in [0.0, 1.0), got %r" % (label, value))
    return value


def validate_operating_band(f_low_hz, f_high_hz):
    """Validate a declared operating band and return it as a float pair."""
    low = _require_positive(f_low_hz, "f_low_hz")
    high = _require_positive(f_high_hz, "f_high_hz")
    if high < low:
        raise ValueError(
            "operating band is inverted: f_high_hz %g below f_low_hz %g" % (high, low)
        )
    return low, high


def categorize_field_response(component_type):
    """Return 'resonant-field' or 'non-resonant-field' for a component type."""
    if not isinstance(component_type, str):
        raise ValueError("component_type must be a string, got %r" % (component_type,))
    key = component_type.strip().lower()
    if key in RESONANT_TYPES:
        return "resonant-field"
    if key in NON_RESONANT_TYPES:
        return "non-resonant-field"
    raise ValueError(
        "unrecognized component_type %r; declare it as one of the resonant-field "
        "types (%s) or non-resonant-field types (%s)"
        % (
            component_type,
            ", ".join(sorted(RESONANT_TYPES)),
            ", ".join(sorted(NON_RESONANT_TYPES)),
        )
    )


# --- gap and field-map handling --------------------------------------------


def critical_gap(gaps):
    """Return the smallest declared gap, which drives the lowest threshold."""
    if not isinstance(gaps, (list, tuple)) or not gaps:
        raise ValueError("gaps must be a non-empty sequence of gap mappings")
    seen = set()
    best = None
    for index, entry in enumerate(gaps):
        if not isinstance(entry, dict):
            raise ValueError("gaps[%d] must be a mapping, got %r" % (index, entry))
        identifier = entry.get("identifier")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("gaps[%d] needs a non-empty 'identifier'" % index)
        identifier = identifier.strip()
        if identifier in seen:
            raise ValueError("duplicate gap identifier %r" % identifier)
        seen.add(identifier)
        gap_m = _require_positive(entry.get("gap_m"), "gaps[%d]['gap_m']" % index)
        if best is None or gap_m < best[1] or (
            math.isclose(gap_m, best[1], rel_tol=REL_TOLERANCE) and identifier < best[0]
        ):
            best = (identifier, gap_m)
    return {"identifier": best[0], "gap_m": best[1]}


def frequency_gap_product_ghz_mm(f_hz, gap_m):
    """Frequency-gap product in GHz.mm for a frequency and a gap."""
    f_hz = _require_positive(f_hz, "f_hz")
    gap_m = _require_positive(gap_m, "gap_m")
    return f_hz * gap_m / HZ_M_PER_GHZ_MM


def susceptibility_map_findings(
    product_ghz_mm,
    map_low_ghz_mm=SUSCEPTIBILITY_MAP_LOW_GHZ_MM,
    map_high_ghz_mm=SUSCEPTIBILITY_MAP_HIGH_GHZ_MM,
):
    """Report a frequency-gap product that falls outside the validated chart."""
    product_ghz_mm = _require_positive(product_ghz_mm, "product_ghz_mm")
    low = _require_positive(map_low_ghz_mm, "map_low_ghz_mm")
    high = _require_positive(map_high_ghz_mm, "map_high_ghz_mm")
    if high <= low:
        raise ValueError(
            "susceptibility map span is inverted: %g not above %g" % (high, low)
        )
    findings = []
    if product_ghz_mm < low and not math.isclose(
        product_ghz_mm, low, rel_tol=REL_TOLERANCE
    ):
        findings.append(
            "frequency-gap product %.4g GHz.mm sits below the validated chart span "
            "starting at %.4g GHz.mm" % (product_ghz_mm, low)
        )
    if product_ghz_mm > high and not math.isclose(
        product_ghz_mm, high, rel_tol=REL_TOLERANCE
    ):
        findings.append(
            "frequency-gap product %.4g GHz.mm sits above the validated chart span "
            "ending at %.4g GHz.mm" % (product_ghz_mm, high)
        )
    return findings


def peak_magnification_frequency(response_map, f_low_hz, f_high_hz):
    """Frequency of the largest voltage-magnification inside the declared band.

    Ties are broken toward the lower frequency, which is the conservative
    choice because the threshold falls with the frequency-gap product.
    """
    low, high = validate_operating_band(f_low_hz, f_high_hz)
    if not isinstance(response_map, (list, tuple)) or not response_map:
        raise ValueError(
            "response_map must be a non-empty sequence for resonant-field hardware"
        )
    best_f = None
    best_m = None
    for index, entry in enumerate(response_map):
        if not isinstance(entry, dict):
            raise ValueError("response_map[%d] must be a mapping, got %r" % (index, entry))
        f_hz = _require_positive(
            entry.get("frequency_hz"), "response_map[%d]['frequency_hz']" % index
        )
        magnification = _require_positive(
            entry.get("voltage_magnification"),
            "response_map[%d]['voltage_magnification']" % index,
        )
        below = f_hz < low and not math.isclose(f_hz, low, rel_tol=REL_TOLERANCE)
        above = f_hz > high and not math.isclose(f_hz, high, rel_tol=REL_TOLERANCE)
        if below or above:
            raise ValueError(
                "response_map[%d] frequency %g Hz lies outside the declared band "
                "%g Hz to %g Hz" % (index, f_hz, low, high)
            )
        if (
            best_m is None
            or magnification > best_m
            or (
                math.isclose(magnification, best_m, rel_tol=REL_TOLERANCE)
                and f_hz < best_f
            )
        ):
            best_f, best_m = f_hz, magnification
    return {"frequency_hz": best_f, "voltage_magnification": best_m}


def drift_window_hz(f_hz, drift_fraction=DEFAULT_DRIFT_FRACTION):
    """Frequency window a tuning and thermal drift allowance opens around a point."""
    f_hz = _require_positive(f_hz, "f_hz")
    drift = _require_fraction(drift_fraction, "drift_fraction")
    return f_hz * (1.0 - drift), f_hz * (1.0 + drift)


# --- selection --------------------------------------------------------------


def select_test_frequency(spec):
    """Select the single multipactor test frequency for one component.

    ``spec`` keys: component_type, f_low_hz, f_high_hz, gaps, optionally
    response_map (required for resonant-field hardware) and drift_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    response = categorize_field_response(spec.get("component_type"))
    low, high = validate_operating_band(spec.get("f_low_hz"), spec.get("f_high_hz"))
    gap = critical_gap(spec.get("gaps"))
    drift = _require_fraction(
        spec.get("drift_fraction", DEFAULT_DRIFT_FRACTION), "drift_fraction"
    )
    findings = []
    if response == "non-resonant-field":
        if spec.get("response_map"):
            findings.append(
                "response_map supplied for non-resonant-field hardware is not used "
                "by the selection; the low band edge governs"
            )
        selected = low * (1.0 - drift)
        basis = "lowest-frequency-gap-product"
        magnification = None
    else:
        peak = peak_magnification_frequency(spec.get("response_map"), low, high)
        selected = peak["frequency_hz"]
        magnification = peak["voltage_magnification"]
        basis = "peak-voltage-magnification"
        window_low, window_high = drift_window_hz(selected, drift)
        if window_low < low and not math.isclose(window_low, low, rel_tol=REL_TOLERANCE):
            findings.append(
                "drift window reaches %.6g Hz, below the declared band edge %.6g Hz; "
                "the worst-case resonance can sit outside the tested point" % (window_low, low)
            )
        if window_high > high and not math.isclose(
            window_high, high, rel_tol=REL_TOLERANCE
        ):
            findings.append(
                "drift window reaches %.6g Hz, above the declared band edge %.6g Hz; "
                "the worst-case resonance can sit outside the tested point"
                % (window_high, high)
            )
    product = frequency_gap_product_ghz_mm(selected, gap["gap_m"])
    findings.extend(susceptibility_map_findings(product))
    return {
        "response": response,
        "basis": basis,
        "frequency_hz": selected,
        "voltage_magnification": magnification,
        "critical_gap": gap,
        "frequency_gap_product_ghz_mm": product,
        "drift_fraction": drift,
        "band_low_hz": low,
        "band_high_hz": high,
        "findings": findings,
    }


def single_frequency_sufficiency(
    selected_hz, f_low_hz, f_high_hz, coverage_ratio_low, coverage_ratio_high
):
    """Check that one selected point covers the band it has to represent."""
    selected_hz = _require_positive(selected_hz, "selected_hz")
    low, high = validate_operating_band(f_low_hz, f_high_hz)
    ratio_low = _require_positive(coverage_ratio_low, "coverage_ratio_low")
    ratio_high = _require_positive(coverage_ratio_high, "coverage_ratio_high")
    if ratio_high < ratio_low:
        raise ValueError(
            "coverage_ratio_high %g must not be below coverage_ratio_low %g"
            % (ratio_high, ratio_low)
        )
    covered_low = selected_hz * ratio_low
    covered_high = selected_hz * ratio_high
    findings = []
    if covered_low > low and not math.isclose(covered_low, low, rel_tol=REL_TOLERANCE):
        findings.append(
            "single point leaves the low band edge uncovered: covered from %.6g Hz, "
            "band starts at %.6g Hz" % (covered_low, low)
        )
    if covered_high < high and not math.isclose(covered_high, high, rel_tol=REL_TOLERANCE):
        findings.append(
            "single point leaves the high band edge uncovered: covered to %.6g Hz, "
            "band ends at %.6g Hz" % (covered_high, high)
        )
    return {
        "covered_low_hz": covered_low,
        "covered_high_hz": covered_high,
        "sufficient": not findings,
        "findings": findings,
    }


def frequency_selection_record(spec, coverage_ratio_low=None, coverage_ratio_high=None):
    """Full clause 6.4.2 record: selection, sufficiency and the verdict."""
    selection = select_test_frequency(spec)
    findings = list(selection["findings"])
    sufficiency = None
    if coverage_ratio_low is not None or coverage_ratio_high is not None:
        if coverage_ratio_low is None or coverage_ratio_high is None:
            raise ValueError(
                "coverage_ratio_low and coverage_ratio_high are supplied together"
            )
        sufficiency = single_frequency_sufficiency(
            selection["frequency_hz"],
            selection["band_low_hz"],
            selection["band_high_hz"],
            coverage_ratio_low,
            coverage_ratio_high,
        )
        findings.extend(sufficiency["findings"])
    return {
        "selection": selection,
        "sufficiency": sufficiency,
        "findings": findings,
        "single_frequency_test_case_valid": not findings,
    }


def summarize_selection(record):
    """Render a selection record as ordered human-readable lines."""
    if not isinstance(record, dict) or "selection" not in record:
        raise ValueError("record must be the mapping returned by frequency_selection_record")
    selection = record["selection"]
    lines = [
        "response: %s (basis %s)" % (selection["response"], selection["basis"]),
        "selected test frequency: %.6g Hz" % selection["frequency_hz"],
        "critical gap: %s at %.6g m" % (
            selection["critical_gap"]["identifier"],
            selection["critical_gap"]["gap_m"],
        ),
        "frequency-gap product: %.4g GHz.mm"
        % selection["frequency_gap_product_ghz_mm"],
        "verdict: %s"
        % (
            "single-frequency test case valid"
            if record["single_frequency_test_case_valid"]
            else "single-frequency test case not established"
        ),
    ]
    lines.extend("finding: %s" % item for item in record["findings"])
    return lines
