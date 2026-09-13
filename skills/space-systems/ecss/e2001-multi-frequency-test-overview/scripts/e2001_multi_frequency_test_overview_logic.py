#!/usr/bin/env python3
"""Single-carrier test representing multi-frequency operation.

Anchor: ECSS-E-ST-20-01C clause 6.4.3.1. Paraphrased, implementable
procedure -- no standard text is reproduced.

A unit that carries several carriers in service is frequently verified with
one carrier driven to an equivalent power. Clause 6.4.3.1 is the overview
step that decides whether such a substitution represents the multi-frequency
case at all, and at which level it has to be driven.

The physics the decision rests on:

* N phase-aligned carriers of equal amplitude and uniform spacing produce a
  periodic envelope. Its peak is N times the single-carrier voltage, so the
  peak envelope power is N squared times the per-carrier power, and the
  envelope repeats at the carrier spacing.
* A discharge does not appear the instant the envelope crosses the onset
  threshold. Electrons have to survive a number of gap crossings before the
  avalanche is established; with a first-order resonance each crossing takes
  half a radio-frequency period, so the envelope has to stay above a level
  for roughly that many half-periods before that level can seed a discharge.
* Therefore the correct equivalent single-carrier level is not always the
  peak envelope power. When the envelope peak is narrower than the onset
  time, the representative level is the lower, sustained level whose dwell
  inside one envelope period equals the onset time. It is floored at the
  total average power, which is present continuously.

The module derives that level from the carrier set, applies the verification
margin, and screens the resulting drive against the facility capability and
the thermal rating of the item, because an equivalent continuous drive
dissipates far more than the operational average.

Every public helper validates its inputs and raises ValueError on data that
cannot carry an engineering conclusion. Standard library only, offline,
deterministic.
"""

import math

# --- engineering parameters (project configurable, not standard text) -------

DEFAULT_GAP_CROSSINGS = 20
"""Gap crossings an electron population survives before an avalanche counts."""

CROSSINGS_PER_RF_PERIOD = 2.0
"""First-order resonance: one crossing per half radio-frequency period."""

BISECTION_ITERATIONS = 120
"""Fixed iteration count keeps every derived level bit-reproducible."""

UNIFORM_SPACING_REL_TOL = 1e-6
"""Relative tolerance on carrier spacing before the comb is called uniform."""

EQUAL_POWER_REL_TOL = 1e-6
"""Relative tolerance on carrier power before the comb is called equal."""

REL_TOLERANCE = 1e-9
"""Relative tolerance absorbing floating-point representation error at
limits. It never widens an engineering limit: it only stops a comparison
that is exact in real arithmetic from failing by a few units in the last
place."""

BASIS_PEAK_ENVELOPE = "peak-envelope-power"
BASIS_SUSTAINED_ENVELOPE = "sustained-envelope-level"
BASIS_AVERAGE_FLOOR = "total-average-power-floor"


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


def _require_non_negative(value, label):
    """Return ``value`` as a non-negative float, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _require_carrier_count(value, label):
    """Return an integer carrier count of at least two, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 2:
        raise ValueError("%s must be at least 2, got %r" % (label, value))
    return value


def validate_carrier_set(carriers):
    """Validate a multi-carrier drive and return it sorted by frequency."""
    if not isinstance(carriers, (list, tuple)):
        raise ValueError("carriers must be a sequence of carrier mappings")
    if len(carriers) < 2:
        raise ValueError(
            "a multi-frequency test case needs at least 2 carriers, got %d"
            % len(carriers)
        )
    cleaned = []
    seen = []
    for index, entry in enumerate(carriers):
        if not isinstance(entry, dict):
            raise ValueError("carriers[%d] must be a mapping, got %r" % (index, entry))
        f_hz = _require_positive(
            entry.get("frequency_hz"), "carriers[%d]['frequency_hz']" % index
        )
        p_w = _require_positive(entry.get("power_w"), "carriers[%d]['power_w']" % index)
        for other in seen:
            if math.isclose(f_hz, other, rel_tol=REL_TOLERANCE):
                raise ValueError("duplicate carrier frequency %g Hz" % f_hz)
        seen.append(f_hz)
        cleaned.append({"frequency_hz": f_hz, "power_w": p_w})
    cleaned.sort(key=lambda item: item["frequency_hz"])
    return cleaned


# --- carrier-set descriptors ------------------------------------------------


def peak_envelope_power_w(carriers):
    """Power at the instant every carrier adds in phase."""
    cleaned = validate_carrier_set(carriers)
    root_sum = sum(math.sqrt(item["power_w"]) for item in cleaned)
    return root_sum * root_sum


def total_average_power_w(carriers):
    """Power the item carries continuously, independent of envelope phase."""
    cleaned = validate_carrier_set(carriers)
    return sum(item["power_w"] for item in cleaned)


def carrier_spacing_hz(carriers):
    """Smallest spacing in the comb plus whether the comb is uniform."""
    cleaned = validate_carrier_set(carriers)
    spacings = [
        cleaned[i + 1]["frequency_hz"] - cleaned[i]["frequency_hz"]
        for i in range(len(cleaned) - 1)
    ]
    smallest = min(spacings)
    if smallest <= 0.0:
        raise ValueError("carrier spacing collapsed to %g Hz" % smallest)
    uniform = all(
        math.isclose(item, smallest, rel_tol=UNIFORM_SPACING_REL_TOL)
        for item in spacings
    )
    return {"spacing_hz": smallest, "uniform": uniform, "count": len(cleaned)}


def carriers_are_equal_power(carriers):
    """True when every carrier carries the same power to within tolerance."""
    cleaned = validate_carrier_set(carriers)
    reference = cleaned[0]["power_w"]
    return all(
        math.isclose(item["power_w"], reference, rel_tol=EQUAL_POWER_REL_TOL)
        for item in cleaned
    )


# --- envelope model ---------------------------------------------------------


def envelope_power_w(count, p_carrier_w, spacing_hz, t_s):
    """Instantaneous envelope power of a uniform equal-amplitude carrier comb."""
    count = _require_carrier_count(count, "count")
    p_carrier_w = _require_positive(p_carrier_w, "p_carrier_w")
    spacing_hz = _require_positive(spacing_hz, "spacing_hz")
    t_s = _require_non_negative(t_s, "t_s")
    phase = math.pi * spacing_hz * t_s
    denominator = math.sin(phase)
    if abs(denominator) < 1e-12:
        return p_carrier_w * float(count) * float(count)
    ratio = math.sin(count * phase) / denominator
    return p_carrier_w * ratio * ratio


def first_envelope_null_s(count, spacing_hz):
    """Time from the envelope peak to the first null of the main lobe."""
    count = _require_carrier_count(count, "count")
    spacing_hz = _require_positive(spacing_hz, "spacing_hz")
    return 1.0 / (float(count) * spacing_hz)


def dwell_above_level_s(count, p_carrier_w, spacing_hz, level_w):
    """Time the envelope spends above a level within one envelope period."""
    count = _require_carrier_count(count, "count")
    p_carrier_w = _require_positive(p_carrier_w, "p_carrier_w")
    spacing_hz = _require_positive(spacing_hz, "spacing_hz")
    level_w = _require_positive(level_w, "level_w")
    peak = p_carrier_w * float(count) * float(count)
    if level_w > peak and not math.isclose(level_w, peak, rel_tol=REL_TOLERANCE):
        return 0.0
    if math.isclose(level_w, peak, rel_tol=REL_TOLERANCE):
        return 0.0
    lower = 0.0
    upper = first_envelope_null_s(count, spacing_hz)
    for _ in range(BISECTION_ITERATIONS):
        middle = 0.5 * (lower + upper)
        if envelope_power_w(count, p_carrier_w, spacing_hz, middle) > level_w:
            lower = middle
        else:
            upper = middle
    return 2.0 * 0.5 * (lower + upper)


def multipactor_onset_time_s(f_rf_hz, crossings=DEFAULT_GAP_CROSSINGS):
    """Time an envelope has to persist before it can seed a discharge."""
    f_rf_hz = _require_positive(f_rf_hz, "f_rf_hz")
    if isinstance(crossings, bool) or not isinstance(crossings, int):
        raise ValueError("crossings must be an integer, got %r" % (crossings,))
    if crossings < 1:
        raise ValueError("crossings must be at least 1, got %d" % crossings)
    return float(crossings) / (CROSSINGS_PER_RF_PERIOD * f_rf_hz)


def sustained_envelope_level_w(
    count, p_carrier_w, spacing_hz, onset_time_s
):
    """Envelope level whose dwell equals the onset time, floored at the average."""
    count = _require_carrier_count(count, "count")
    p_carrier_w = _require_positive(p_carrier_w, "p_carrier_w")
    spacing_hz = _require_positive(spacing_hz, "spacing_hz")
    onset_time_s = _require_positive(onset_time_s, "onset_time_s")
    peak = p_carrier_w * float(count) * float(count)
    average = p_carrier_w * float(count)
    widest_dwell = 2.0 * first_envelope_null_s(count, spacing_hz)
    if onset_time_s >= widest_dwell and not math.isclose(
        onset_time_s, widest_dwell, rel_tol=REL_TOLERANCE
    ):
        return average
    lower = peak * 1e-15
    upper = peak
    for _ in range(BISECTION_ITERATIONS):
        middle = 0.5 * (lower + upper)
        if dwell_above_level_s(count, p_carrier_w, spacing_hz, middle) > onset_time_s:
            lower = middle
        else:
            upper = middle
    level = 0.5 * (lower + upper)
    return max(level, average)


# --- equivalent single-carrier drive ---------------------------------------


def equivalent_single_carrier_power_w(
    carriers, f_test_hz, margin_db=0.0, crossings=DEFAULT_GAP_CROSSINGS
):
    """Equivalent single-carrier drive representing the multi-carrier case."""
    cleaned = validate_carrier_set(carriers)
    f_test_hz = _require_positive(f_test_hz, "f_test_hz")
    if isinstance(margin_db, bool) or not isinstance(margin_db, (int, float)):
        raise ValueError("margin_db must be a real number, got %r" % (margin_db,))
    margin_db = float(margin_db)
    if margin_db < 0.0:
        raise ValueError("margin_db must not be negative, got %r" % (margin_db,))
    peak = peak_envelope_power_w(cleaned)
    average = total_average_power_w(cleaned)
    comb = carrier_spacing_hz(cleaned)
    onset = multipactor_onset_time_s(f_test_hz, crossings)
    notes = []
    if comb["uniform"] and carriers_are_equal_power(cleaned):
        level = sustained_envelope_level_w(
            comb["count"], cleaned[0]["power_w"], comb["spacing_hz"], onset
        )
        if math.isclose(level, average, rel_tol=REL_TOLERANCE):
            basis = BASIS_AVERAGE_FLOOR
            notes.append(
                "envelope peak is shorter than the onset time at every level; the "
                "representative drive falls back to the total average power"
            )
        elif math.isclose(level, peak, rel_tol=1e-6):
            basis = BASIS_PEAK_ENVELOPE
        else:
            basis = BASIS_SUSTAINED_ENVELOPE
    else:
        level = peak
        basis = BASIS_PEAK_ENVELOPE
        notes.append(
            "carrier comb is not uniform-and-equal-amplitude; the closed-form "
            "envelope does not apply and the peak envelope power is used"
        )
    drive = level * 10.0 ** (margin_db / 10.0)
    return {
        "basis": basis,
        "representative_level_w": level,
        "equivalent_drive_w": drive,
        "peak_envelope_power_w": peak,
        "total_average_power_w": average,
        "onset_time_s": onset,
        "carrier_count": comb["count"],
        "spacing_hz": comb["spacing_hz"],
        "margin_db": margin_db,
        "notes": notes,
    }


def assess_test_feasibility(p_equivalent_w, facility_max_w, thermal_rating_w):
    """Screen an equivalent drive against facility and thermal limits."""
    p_equivalent_w = _require_positive(p_equivalent_w, "p_equivalent_w")
    facility_max_w = _require_positive(facility_max_w, "facility_max_w")
    thermal_rating_w = _require_positive(thermal_rating_w, "thermal_rating_w")
    findings = []
    if p_equivalent_w > facility_max_w and not math.isclose(
        p_equivalent_w, facility_max_w, rel_tol=REL_TOLERANCE
    ):
        findings.append(
            "equivalent drive %.6g W exceeds the facility capability %.6g W"
            % (p_equivalent_w, facility_max_w)
        )
    if p_equivalent_w > thermal_rating_w and not math.isclose(
        p_equivalent_w, thermal_rating_w, rel_tol=REL_TOLERANCE
    ):
        findings.append(
            "equivalent drive %.6g W exceeds the continuous thermal rating %.6g W; "
            "a duty-cycled or true multi-carrier run is needed"
            % (p_equivalent_w, thermal_rating_w)
        )
    return {"feasible": not findings, "findings": findings}


def multi_frequency_test_overview(spec):
    """Full clause 6.4.3.1 record: basis, equivalent drive, feasibility, verdict.

    ``spec`` keys: carriers, f_test_hz, optionally margin_db, crossings,
    facility_max_w and thermal_rating_w.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    equivalent = equivalent_single_carrier_power_w(
        spec.get("carriers"),
        spec.get("f_test_hz"),
        spec.get("margin_db", 0.0),
        spec.get("crossings", DEFAULT_GAP_CROSSINGS),
    )
    findings = list(equivalent["notes"])
    feasibility = None
    facility = spec.get("facility_max_w")
    thermal = spec.get("thermal_rating_w")
    if facility is not None or thermal is not None:
        if facility is None or thermal is None:
            raise ValueError(
                "facility_max_w and thermal_rating_w are supplied together"
            )
        feasibility = assess_test_feasibility(
            equivalent["equivalent_drive_w"], facility, thermal
        )
        findings.extend(feasibility["findings"])
    over_test_ratio = (
        equivalent["equivalent_drive_w"] / equivalent["total_average_power_w"]
    )
    return {
        "equivalent": equivalent,
        "feasibility": feasibility,
        "over_test_ratio": over_test_ratio,
        "findings": findings,
        "single_carrier_substitution_valid": not findings,
    }


def summarize_overview(record):
    """Render an overview record as ordered human-readable lines."""
    if not isinstance(record, dict) or "equivalent" not in record:
        raise ValueError(
            "record must be the mapping returned by multi_frequency_test_overview"
        )
    equivalent = record["equivalent"]
    lines = [
        "carriers: %d spaced %.6g Hz apart"
        % (equivalent["carrier_count"], equivalent["spacing_hz"]),
        "peak envelope power: %.6g W, total average power: %.6g W"
        % (equivalent["peak_envelope_power_w"], equivalent["total_average_power_w"]),
        "basis: %s at %.6g W" % (equivalent["basis"], equivalent["representative_level_w"]),
        "equivalent single-carrier drive: %.6g W (margin %.1f dB)"
        % (equivalent["equivalent_drive_w"], equivalent["margin_db"]),
        "over-test ratio against the operational average: %.3f"
        % record["over_test_ratio"],
        "verdict: %s"
        % (
            "single-carrier substitution valid"
            if record["single_carrier_substitution_valid"]
            else "single-carrier substitution not established"
        ),
    ]
    lines.extend("finding: %s" % item for item in record["findings"])
    return lines
