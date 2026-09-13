#!/usr/bin/env python3
"""Radio-frequency chain power-handling logic (ECSS-E-ST-20C clause 7.3.2.1).

Deterministic, offline, stdlib only. The standard is cited as the anchor
only; the procedure below is a paraphrase, not standard text.

Scope: establish that each element of a radio-frequency chain sustains the
maximum operating radio-frequency power it sees in the in-orbit vacuum
environment without damage, before any agreed design margin is applied.
"""

import math

# --- domain constants ------------------------------------------------------

RATING_BASES = ("vacuum-substantiated", "ambient-air", "unsubstantiated")

_RATING_BASIS_ALIASES = {
    "vacuum": "vacuum-substantiated",
    "vacuum-substantiated": "vacuum-substantiated",
    "vacuum-qualified": "vacuum-substantiated",
    "air": "ambient-air",
    "ambient": "ambient-air",
    "ambient-air": "ambient-air",
    "none": "unsubstantiated",
    "unknown": "unsubstantiated",
    "unsubstantiated": "unsubstantiated",
}

PRESSURIZATION_STATES = ("vented", "hermetically-sealed")

_PRESSURIZATION_ALIASES = {
    "vented": "vented",
    "vent": "vented",
    "open": "vented",
    "sealed": "hermetically-sealed",
    "hermetic": "hermetically-sealed",
    "hermetically-sealed": "hermetically-sealed",
}

LIMITATION_TYPES = ("thermal", "voltage-breakdown")

_LIMITATION_ALIASES = {
    "thermal": "thermal",
    "thermally-limited": "thermal",
    "average": "thermal",
    "voltage-breakdown": "voltage-breakdown",
    "breakdown": "voltage-breakdown",
    "peak": "voltage-breakdown",
}

# A capability substantiated in ambient air does not transfer to a vented
# element in vacuum; this conservative factor stands in until the element is
# substantiated in the flight medium.
AMBIENT_AIR_VACUUM_DERATING = 0.5

# Absorbs decibel round-trip representation error at an exactly-met limit.
RATING_TOLERANCE = 1e-9


# --- unit helpers ----------------------------------------------------------


def watt_to_dbm(watts):
    """Convert a strictly positive power in watts to dBm."""
    _require_positive(watts, "power")
    return 10.0 * math.log10(watts * 1000.0)


def dbm_to_watt(dbm):
    """Convert a level in dBm to watts."""
    if not _is_real(dbm):
        raise ValueError("level must be a real number, got %r" % (dbm,))
    return 10.0 ** (dbm / 10.0) / 1000.0


def db_to_ratio(db):
    """Convert a decibel figure to a linear power ratio."""
    if not _is_real(db):
        raise ValueError("decibel figure must be a real number, got %r" % (db,))
    return 10.0 ** (db / 10.0)


def ratio_to_db(ratio):
    """Convert a strictly positive linear power ratio to decibels."""
    _require_positive(ratio, "ratio")
    return 10.0 * math.log10(ratio)


def _is_real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_positive(value, label):
    if not _is_real(value):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return float(value)


# --- carrier set -----------------------------------------------------------


def carrier_set_levels(carrier_powers_w):
    """Return (average_w, peak_envelope_w) for a set of simultaneous carriers.

    The average level is the sum of the carrier powers. The peak-envelope
    level is the square of the sum of the carrier voltage amplitudes, which
    for n equal carriers is n times the average.
    """
    if not isinstance(carrier_powers_w, (list, tuple)):
        raise ValueError("carrier set must be a list, got %r" % (carrier_powers_w,))
    if not carrier_powers_w:
        raise ValueError("carrier set must contain at least one carrier")
    amplitude_sum = 0.0
    average = 0.0
    for i, power in enumerate(carrier_powers_w):
        value = _require_positive(power, "carrier[%d] power" % i)
        average += value
        amplitude_sum += math.sqrt(value)
    return average, amplitude_sum * amplitude_sum


def peak_to_average_ratio_db(carrier_powers_w):
    """Decibel ratio of the peak-envelope level to the average level."""
    average, peak = carrier_set_levels(carrier_powers_w)
    return ratio_to_db(peak / average)


# --- element data ----------------------------------------------------------


def normalize_rating_basis(basis):
    """Return the canonical rating-basis token."""
    return _normalize(basis, _RATING_BASIS_ALIASES, RATING_BASES, "rating basis")


def normalize_pressurization(state):
    """Return the canonical pressurization-state token."""
    return _normalize(
        state, _PRESSURIZATION_ALIASES, PRESSURIZATION_STATES, "pressurization state"
    )


def normalize_limitation(limitation):
    """Return the canonical limitation-type token."""
    return _normalize(limitation, _LIMITATION_ALIASES, LIMITATION_TYPES, "limitation type")


def _normalize(value, aliases, canonical, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    resolved = aliases.get(key)
    if resolved is None:
        raise ValueError(
            "unknown %s %r; expected one of %s" % (label, value, ", ".join(canonical))
        )
    return resolved


def vacuum_derating_factor(rating_basis, pressurization):
    """Factor applied to a substantiated capability for the vacuum case.

    Raises ValueError when the basis is unsubstantiated: no effective
    capability can be derived from a number with no provenance.
    """
    basis = normalize_rating_basis(rating_basis)
    state = normalize_pressurization(pressurization)
    if basis == "unsubstantiated":
        raise ValueError(
            "an unsubstantiated capability supports no vacuum-derating factor"
        )
    if basis == "vacuum-substantiated":
        return 1.0
    return 1.0 if state == "hermetically-sealed" else AMBIENT_AIR_VACUUM_DERATING


def effective_capability_w(element):
    """Effective vacuum power-handling capability of one element, in watts."""
    rated = _require_positive(element.get("capability_w"), "element capability")
    factor = vacuum_derating_factor(
        element.get("rating_basis"), element.get("pressurization")
    )
    return rated * factor


def validate_element(element, index=0):
    """Validate one chain element and return its normalized copy."""
    if not isinstance(element, dict):
        raise ValueError("element[%d] must be a mapping, got %r" % (index, element))
    ident = element.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("element[%d] is missing a non-empty 'id'" % index)
    loss = element.get("insertion_loss_db", 0.0)
    if not _is_real(loss):
        raise ValueError("element %r insertion loss must be a real number" % ident)
    if loss < 0:
        raise ValueError(
            "element %r has a negative insertion loss (%r); a passive chain "
            "element cannot add power" % (ident, loss)
        )
    normalized = dict(element)
    normalized["id"] = ident.strip()
    normalized["insertion_loss_db"] = float(loss)
    normalized["rating_basis"] = normalize_rating_basis(element.get("rating_basis"))
    normalized["pressurization"] = normalize_pressurization(
        element.get("pressurization", "vented")
    )
    normalized["limitation"] = normalize_limitation(element.get("limitation"))
    normalized["capability_w"] = _require_positive(
        element.get("capability_w"), "element %r capability" % ident
    )
    return normalized


# --- chain propagation -----------------------------------------------------


def propagate_chain_levels(average_w, peak_w, elements):
    """Return the incident (average, peak) level at each element, in order."""
    _require_positive(average_w, "average drive level")
    _require_positive(peak_w, "peak-envelope drive level")
    if peak_w < average_w and not math.isclose(peak_w, average_w, rel_tol=RATING_TOLERANCE):
        raise ValueError(
            "peak-envelope level (%r W) cannot be below the average level (%r W)"
            % (peak_w, average_w)
        )
    incident = []
    running_average = float(average_w)
    running_peak = float(peak_w)
    for element in elements:
        incident.append((running_average, running_peak))
        attenuation = db_to_ratio(-element["insertion_loss_db"])
        running_average *= attenuation
        running_peak *= attenuation
    return incident


def within_capability(stress_w, capability_w):
    """True when the stressing level is at or below the effective capability.

    Absorbs decibel round-trip representation error at an exactly-met
    capability; it never widens the capability itself.
    """
    if stress_w <= capability_w:
        return True
    return math.isclose(stress_w, capability_w, rel_tol=RATING_TOLERANCE, abs_tol=1e-15)


# --- assessment ------------------------------------------------------------


def assess_element(element, incident_average_w, incident_peak_w):
    """Assess one validated element against its incident levels."""
    findings = []
    stress = (
        incident_average_w
        if element["limitation"] == "thermal"
        else incident_peak_w
    )
    basis = element["rating_basis"]
    capability = None
    ratio_db = None
    if basis == "unsubstantiated":
        findings.append(
            "capability-basis-unsubstantiated: no medium recorded for the "
            "declared capability"
        )
    else:
        if basis == "ambient-air":
            if element["pressurization"] == "vented":
                findings.append(
                    "ambient-air-capability-vented-to-vacuum: capability derated "
                    "pending substantiation in the flight medium"
                )
            elif not str(element.get("seal_evidence", "")).strip():
                findings.append(
                    "hermetic-capability-without-leak-evidence: retained gas is "
                    "not evidenced"
                )
        capability = effective_capability_w(element)
        ratio_db = ratio_to_db(capability / stress)
        if not within_capability(stress, capability):
            findings.append(
                "level-exceeds-effective-capability: %.4g W against %.4g W"
                % (stress, capability)
            )
    return {
        "id": element["id"],
        "limitation": element["limitation"],
        "rating_basis": basis,
        "incident_average_w": incident_average_w,
        "incident_peak_w": incident_peak_w,
        "stress_w": stress,
        "effective_capability_w": capability,
        "capability_ratio_db": ratio_db,
        "findings": findings,
        "compliant": not findings,
    }


def assess_chain_power_handling(carrier_powers_w, elements):
    """Assess a whole radio-frequency chain against clause 7.3.2.1."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError("chain must be a list of elements, got %r" % (elements,))
    if not elements:
        raise ValueError("chain must contain at least one element")
    average_w, peak_w = carrier_set_levels(carrier_powers_w)

    normalized = []
    seen = set()
    for index, element in enumerate(elements):
        item = validate_element(element, index)
        if item["id"] in seen:
            raise ValueError("duplicate element identifier %r" % (item["id"],))
        seen.add(item["id"])
        normalized.append(item)

    incident = propagate_chain_levels(average_w, peak_w, normalized)
    results = [
        assess_element(item, incident[i][0], incident[i][1])
        for i, item in enumerate(normalized)
    ]
    ratios = [
        (r["capability_ratio_db"], r["id"])
        for r in results
        if r["capability_ratio_db"] is not None
    ]
    worst = min(ratios) if ratios else (None, None)
    total_loss_db = sum(item["insertion_loss_db"] for item in normalized)
    return {
        "results": results,
        "average_drive_w": average_w,
        "peak_envelope_drive_w": peak_w,
        "peak_to_average_db": ratio_to_db(peak_w / average_w),
        "total_insertion_loss_db": total_loss_db,
        "worst_capability_ratio_db": worst[0],
        "worst_element_id": worst[1],
        "finding_total": sum(len(r["findings"]) for r in results),
        "compliant": all(r["compliant"] for r in results),
    }
