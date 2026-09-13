#!/usr/bin/env python3
"""Electrical performance measurement in the SCA acceptance sequence.

Anchor: ECSS-E-ST-20-08C clause 6.3.3. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Every solar cell assembly (SCA) offered for acceptance carries an electrical
performance measurement, and the number written on the data sheet is not the
number the acceptance decision is taken on. The reading is taken under the
conditions the flash bench happened to deliver; the declared minimum belongs
to the reference conditions. Four steps sit between them:

    window      are the bench conditions close enough to reference that a
                translation is an interpolation and not an extrapolation
    correction  translate short-circuit current, open-circuit voltage and
                maximum power to reference irradiance and temperature
    consistency does the corrected triple describe a real operating point --
                a maximum power that cannot sit under its own current and
                voltage envelope is an instrument or transcription fault,
                not a weak assembly
    margin      does the corrected maximum power clear the declared minimum

The lot is then rolled up: the sample has to be large enough for the lot it
speaks for, and the share of assemblies falling out has to stay under the
policy limit. One assembly under the minimum is a part to set aside; a lot
with too many of them is a lot whose acceptance measurement has stopped
being a sampling exercise.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REFERENCE_IRRADIANCE_W_PER_M2 = 1367.0
REFERENCE_TEMPERATURE_C = 25.0

READING_KEYS = (
    "irradiance_w_per_m2",
    "temperature_c",
    "isc_a",
    "voc_v",
    "pmax_w",
)

COEFFICIENT_KEYS = ("isc_a_per_c", "voc_v_per_c", "pmax_w_per_c")

ASSEMBLY_ACCEPTED = "assembly-accepted"
ASSEMBLY_CONDITIONS_OUT_OF_WINDOW = "assembly-conditions-out-of-window"
ASSEMBLY_POINT_INCONSISTENT = "assembly-point-inconsistent"
ASSEMBLY_BELOW_DECLARED_MINIMUM = "assembly-below-declared-minimum"

LOT_ACCEPTED = "acceptance-lot-accepted"
LOT_REJECTED = "acceptance-lot-rejected"

DEFAULT_SCA_ACCEPTANCE_POLICY = {
    "irradiance_window_fraction": 0.10,
    "temperature_window_c": 15.0,
    "min_fill_factor": 0.60,
    "max_fill_factor": 0.90,
    "min_sample_fraction": 0.10,
    "min_sample_count": 5,
    "max_reject_fraction": 0.05,
}

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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A corrected power is a product and a difference of declared numbers, so
    an assembly meant to sit exactly on its declared minimum can land a few
    units in the last place below it. The minimum is never lowered; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _ceil_count(count, fraction):
    """Smallest whole number of articles covering a share of a lot."""
    exact = count * fraction
    floor = math.floor(exact)
    if exact - floor > 1e-9:
        floor += 1
    return int(floor)


def validate_acceptance_policy(policy):
    """Check an acceptance measurement policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "irradiance_window_fraction", policy.get("irradiance_window_fraction")
    )
    _require_positive("temperature_window_c", policy.get("temperature_window_c"))
    low = _require_fraction("min_fill_factor", policy.get("min_fill_factor"))
    high = _require_fraction("max_fill_factor", policy.get("max_fill_factor"))
    if low >= high:
        raise ValueError(
            "policy min_fill_factor must sit below max_fill_factor, got %r and %r"
            % (low, high)
        )
    _require_fraction("min_sample_fraction", policy.get("min_sample_fraction"))
    _require_count("min_sample_count", policy.get("min_sample_count"), 1)
    _require_fraction("max_reject_fraction", policy.get("max_reject_fraction"))
    return policy


def validate_reading(reading):
    """Check one bench reading carries every quantity the correction needs."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping, got %r" % (reading,))
    missing = sorted(k for k in READING_KEYS if k not in reading)
    if missing:
        raise ValueError("reading is missing %s" % ", ".join(missing))
    return {
        "irradiance_w_per_m2": _require_positive(
            "irradiance_w_per_m2", reading["irradiance_w_per_m2"]
        ),
        "temperature_c": _require_number("temperature_c", reading["temperature_c"]),
        "isc_a": _require_positive("isc_a", reading["isc_a"]),
        "voc_v": _require_positive("voc_v", reading["voc_v"]),
        "pmax_w": _require_positive("pmax_w", reading["pmax_w"]),
    }


def validate_coefficients(coefficients):
    """Check the declared temperature coefficients of the assembly type."""
    if not isinstance(coefficients, dict):
        raise ValueError("coefficients must be a mapping, got %r" % (coefficients,))
    missing = sorted(k for k in COEFFICIENT_KEYS if k not in coefficients)
    if missing:
        raise ValueError("coefficients are missing %s" % ", ".join(missing))
    return {key: _require_number(key, coefficients[key]) for key in COEFFICIENT_KEYS}


def condition_window_status(reading, policy=DEFAULT_SCA_ACCEPTANCE_POLICY):
    """Are the bench conditions close enough to reference to translate from."""
    validate_acceptance_policy(policy)
    values = validate_reading(reading)
    irradiance_span = REFERENCE_IRRADIANCE_W_PER_M2 * float(
        policy["irradiance_window_fraction"]
    )
    irradiance_offset = abs(
        values["irradiance_w_per_m2"] - REFERENCE_IRRADIANCE_W_PER_M2
    )
    temperature_offset = abs(values["temperature_c"] - REFERENCE_TEMPERATURE_C)
    temperature_span = float(policy["temperature_window_c"])
    irradiance_ok = _at_most(irradiance_offset, irradiance_span)
    temperature_ok = _at_most(temperature_offset, temperature_span)
    findings = []
    if not irradiance_ok:
        findings.append(
            "bench irradiance sits %.1f W/m2 off reference against an allowed %.1f"
            % (irradiance_offset, irradiance_span)
        )
    if not temperature_ok:
        findings.append(
            "bench temperature sits %.1f C off reference against an allowed %.1f"
            % (temperature_offset, temperature_span)
        )
    return {
        "irradiance_offset_w_per_m2": irradiance_offset,
        "allowed_irradiance_offset_w_per_m2": irradiance_span,
        "temperature_offset_c": temperature_offset,
        "allowed_temperature_offset_c": temperature_span,
        "irradiance_in_window": irradiance_ok,
        "temperature_in_window": temperature_ok,
        "in_window": irradiance_ok and temperature_ok,
        "findings": findings,
    }


def correct_to_reference(reading, coefficients):
    """Translate a bench reading to reference irradiance and temperature.

    Current and power scale with irradiance; all three quantities then have
    the declared temperature drift over the offset from reference removed.
    """
    values = validate_reading(reading)
    drift = validate_coefficients(coefficients)
    ratio = REFERENCE_IRRADIANCE_W_PER_M2 / values["irradiance_w_per_m2"]
    offset = values["temperature_c"] - REFERENCE_TEMPERATURE_C
    return {
        "irradiance_ratio": ratio,
        "temperature_offset_c": offset,
        "isc_a": values["isc_a"] * ratio - drift["isc_a_per_c"] * offset,
        "voc_v": values["voc_v"] - drift["voc_v_per_c"] * offset,
        "pmax_w": values["pmax_w"] * ratio - drift["pmax_w_per_c"] * offset,
    }


def point_consistency(corrected, policy=DEFAULT_SCA_ACCEPTANCE_POLICY):
    """Does the corrected triple describe a physically real operating point."""
    validate_acceptance_policy(policy)
    if not isinstance(corrected, dict):
        raise ValueError("corrected point must be a mapping, got %r" % (corrected,))
    missing = sorted(k for k in ("isc_a", "voc_v", "pmax_w") if k not in corrected)
    if missing:
        raise ValueError("corrected point is missing %s" % ", ".join(missing))
    isc = _require_number("isc_a", corrected["isc_a"])
    voc = _require_number("voc_v", corrected["voc_v"])
    pmax = _require_number("pmax_w", corrected["pmax_w"])
    findings = []
    if isc <= 0.0 or voc <= 0.0 or pmax <= 0.0:
        findings.append(
            "the correction leaves a non-positive quantity, so the reading or "
            "the declared drift is wrong"
        )
        return {
            "envelope_w": None,
            "fill_factor": None,
            "min_fill_factor": float(policy["min_fill_factor"]),
            "max_fill_factor": float(policy["max_fill_factor"]),
            "consistent": False,
            "findings": findings,
        }
    envelope = isc * voc
    ratio = pmax / envelope
    low = float(policy["min_fill_factor"])
    high = float(policy["max_fill_factor"])
    consistent = _at_least(ratio, low) and _at_most(ratio, high)
    if not consistent:
        findings.append(
            "the corrected point fills %.4f of its current-voltage envelope, "
            "outside the plausible band %.2f to %.2f" % (ratio, low, high)
        )
    return {
        "envelope_w": envelope,
        "fill_factor": ratio,
        "min_fill_factor": low,
        "max_fill_factor": high,
        "consistent": consistent,
        "findings": findings,
    }


def margin_status(corrected_pmax_w, declared_minimum_pmax_w):
    """Does the corrected maximum power clear the declared minimum."""
    value = _require_number("corrected pmax_w", corrected_pmax_w)
    minimum = _require_positive("declared_minimum_pmax_w", declared_minimum_pmax_w)
    clears = _at_least(value, minimum)
    findings = []
    if not clears:
        findings.append(
            "corrected maximum power %.4f W falls under the declared minimum "
            "%.4f W" % (value, minimum)
        )
    return {
        "corrected_pmax_w": value,
        "declared_minimum_pmax_w": minimum,
        "margin_w": value - minimum,
        "clears_minimum": clears,
        "findings": findings,
    }


def assess_assembly(entry, policy=DEFAULT_SCA_ACCEPTANCE_POLICY):
    """Verdict for one cell assembly measured in the acceptance sequence."""
    validate_acceptance_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))
    identifier = _require_text("identifier", entry.get("identifier"))
    window = condition_window_status(entry.get("reading"), policy)
    corrected = correct_to_reference(entry.get("reading"), entry.get("coefficients"))
    consistency = point_consistency(corrected, policy)
    margin = margin_status(
        corrected["pmax_w"], entry.get("declared_minimum_pmax_w")
    )
    findings = [
        "%s: %s" % (identifier, text)
        for text in list(window["findings"])
        + list(consistency["findings"])
        + list(margin["findings"])
    ]
    record = {
        "identifier": identifier,
        "window": window,
        "corrected": corrected,
        "consistency": consistency,
        "margin": margin,
        "findings": findings,
    }
    if not window["in_window"]:
        record["verdict"] = ASSEMBLY_CONDITIONS_OUT_OF_WINDOW
    elif not consistency["consistent"]:
        record["verdict"] = ASSEMBLY_POINT_INCONSISTENT
    elif not margin["clears_minimum"]:
        record["verdict"] = ASSEMBLY_BELOW_DECLARED_MINIMUM
    else:
        record["verdict"] = ASSEMBLY_ACCEPTED
    record["accepted"] = record["verdict"] == ASSEMBLY_ACCEPTED
    return record


def required_sample_count(lot_size, policy=DEFAULT_SCA_ACCEPTANCE_POLICY):
    """How many assemblies the acceptance measurement has to cover."""
    validate_acceptance_policy(policy)
    size = _require_count("lot_size", lot_size, 1)
    by_share = _ceil_count(size, float(policy["min_sample_fraction"]))
    floor = int(policy["min_sample_count"])
    return min(size, max(floor, by_share))


def assess_acceptance_lot(case, policy=DEFAULT_SCA_ACCEPTANCE_POLICY):
    """Full clause 6.3.3 sweep over one acceptance lot of cell assemblies."""
    validate_acceptance_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    lot_size = _require_count("lot_size", case.get("lot_size"), 1)
    assemblies = case.get("assemblies")
    if not isinstance(assemblies, (list, tuple)) or not assemblies:
        raise ValueError("case assemblies must be a non-empty sequence of mappings")
    if len(assemblies) > lot_size:
        raise ValueError(
            "case measures %d assemblies out of a lot of %d"
            % (len(assemblies), lot_size)
        )
    shared_coefficients = case.get("coefficients")
    shared_minimum = case.get("declared_minimum_pmax_w")
    records = []
    for entry in assemblies:
        if not isinstance(entry, dict):
            raise ValueError("assembly entry must be a mapping, got %r" % (entry,))
        merged = dict(entry)
        if "coefficients" not in merged and shared_coefficients is not None:
            merged["coefficients"] = shared_coefficients
        if "declared_minimum_pmax_w" not in merged and shared_minimum is not None:
            merged["declared_minimum_pmax_w"] = shared_minimum
        records.append(assess_assembly(merged, policy))
    names = [record["identifier"] for record in records]
    repeated = sorted({n for n in names if names.count(n) > 1})
    if repeated:
        raise ValueError("case measures an assembly twice: %s" % ", ".join(repeated))
    grouped = {}
    for record in records:
        grouped.setdefault(record["verdict"], []).append(record["identifier"])
    accepted = [record for record in records if record["accepted"]]
    rejected = [record for record in records if not record["accepted"]]
    required = required_sample_count(lot_size, policy)
    sample_ok = len(records) >= required
    reject_share = len(rejected) / float(len(records))
    limit = float(policy["max_reject_fraction"])
    share_ok = _at_most(reject_share, limit)
    findings = []
    for record in records:
        findings.extend(record["findings"])
    if not sample_ok:
        findings.append(
            "the acceptance measurement covers %d of a required %d assemblies"
            % (len(records), required)
        )
    if not share_ok:
        findings.append(
            "the reject share %.4f exceeds the allowed %.4f" % (reject_share, limit)
        )
    mean_pmax = sum(
        record["corrected"]["pmax_w"] for record in records
    ) / float(len(records))
    return {
        "verdict": LOT_ACCEPTED if sample_ok and share_ok else LOT_REJECTED,
        "lot_size": lot_size,
        "measured_count": len(records),
        "required_sample_count": required,
        "sample_sufficient": sample_ok,
        "assembly_records": records,
        "grouped_by_verdict": grouped,
        "accepted_identifiers": sorted(r["identifier"] for r in accepted),
        "rejected_identifiers": sorted(r["identifier"] for r in rejected),
        "reject_fraction": reject_share,
        "max_reject_fraction": limit,
        "reject_share_within_limit": share_ok,
        "mean_corrected_pmax_w": mean_pmax,
        "findings": findings,
    }
