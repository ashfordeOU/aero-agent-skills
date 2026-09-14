#!/usr/bin/env python3
"""Handling and storage of an electrostatic-discharge-sensitive assembly.

Anchor: ECSS-E-ST-20-08C clause 6.8.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause does not ask whether an assembly is fragile. It asks whether the
handling and storage actually applied to it keep the voltage the assembly can
see below the voltage it is known to survive. That turns into four questions
a record set has to answer.

How sensitive is this assembly?
    The withstand voltage measured against a discharge model puts the
    assembly in a sensitivity band. The band is what decides how many
    controls the handling has to carry, so it is derived, never asserted.

Is the protected area actually protecting?
    Each control has a band of its own, and both ends matter. A ground path
    that is too resistive does not bleed charge; a ground path that is too
    conductive turns an operator into a discharge route and is a personnel
    hazard as well as a component one. A control that is present but out of
    band is not a control.

Does the packaging shield, or only avoid charging?
    Dissipative and low-charging packaging stop the bag itself from becoming
    a source. Neither puts a conductive boundary between the assembly and an
    external field. Only shielding packaging does, and the most sensitive
    bands are the ones that need it.

Does anything left over still fit under the withstand voltage?
    Residual charge on a floating assembly appears as a voltage through its
    own capacitance, V = Q / C. That voltage is compared with the withstand
    voltage, and the shortfall is the finding.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "DISCHARGE_MODELS",
    "SENSITIVITY_BANDS",
    "CONTROL_BANDS",
    "PACKAGING_RANK",
    "HANDLING_COMPLIANT",
    "HANDLING_CONDITIONAL",
    "HANDLING_NON_COMPLIANT",
    "categorize_sensitivity",
    "required_controls",
    "control_verdict",
    "evaluate_controls",
    "packaging_adequacy",
    "residual_voltage_v",
    "decade_decay_time_s",
    "storage_envelope_findings",
    "shelf_life_used_fraction",
    "assess_handling_and_storage",
]

# Discharge models an assembly withstand voltage can be quoted against.
DISCHARGE_MODELS = ("human-body", "machine", "charged-device")

# Ordered sensitivity bands per model: (band name, exclusive upper bound in
# volts, control weight). The last entry of every model carries an infinite
# bound so any positive withstand voltage lands somewhere.
SENSITIVITY_BANDS = {
    "human-body": (
        ("band-0-most-sensitive", 250.0),
        ("band-1-sensitive", 1000.0),
        ("band-2-moderate", 4000.0),
        ("band-3-robust", float("inf")),
    ),
    "machine": (
        ("band-0-most-sensitive", 100.0),
        ("band-1-sensitive", 200.0),
        ("band-2-moderate", 400.0),
        ("band-3-robust", float("inf")),
    ),
    "charged-device": (
        ("band-0-most-sensitive", 125.0),
        ("band-1-sensitive", 250.0),
        ("band-2-moderate", 500.0),
        ("band-3-robust", float("inf")),
    ),
}

BAND_RANK = {
    "band-0-most-sensitive": 0,
    "band-1-sensitive": 1,
    "band-2-moderate": 2,
    "band-3-robust": 3,
}

# Acceptance band for each protected-area control, inclusive at both ends.
# "symmetric" controls are graded on the magnitude of the reading.
CONTROL_BANDS = {
    "operator-ground-path-ohm": {"low": 7.5e5, "high": 3.5e7, "symmetric": False},
    "worksurface-to-ground-ohm": {"low": 1.0e6, "high": 1.0e9, "symmetric": False},
    "floor-footwear-system-ohm": {"low": 1.0e5, "high": 3.5e7, "symmetric": False},
    "tool-to-ground-ohm": {"low": 1.0e5, "high": 1.0e9, "symmetric": False},
    "ionizer-offset-volt": {"low": 0.0, "high": 35.0, "symmetric": True},
    "relative-humidity-percent": {"low": 30.0, "high": 70.0, "symmetric": False},
}

# Controls every handling operation owes, and the extra ones the more
# sensitive bands owe on top.
_BASE_CONTROLS = ("operator-ground-path-ohm", "worksurface-to-ground-ohm")
_EXTRA_BY_RANK = {
    0: ("floor-footwear-system-ohm", "tool-to-ground-ohm",
        "ionizer-offset-volt", "relative-humidity-percent"),
    1: ("floor-footwear-system-ohm", "ionizer-offset-volt",
        "relative-humidity-percent"),
    2: ("relative-humidity-percent",),
    3: (),
}

# Packaging families, least to most protective.
PACKAGING_RANK = {
    "insulative": 0,
    "low-charging": 1,
    "dissipative": 2,
    "shielding": 3,
}

# Minimum packaging family a band may be stored or shipped in.
_MIN_PACKAGING_BY_RANK = {0: 3, 1: 3, 2: 2, 3: 1}

HANDLING_COMPLIANT = "handling-compliant"
HANDLING_CONDITIONAL = "handling-compliant-under-restriction"
HANDLING_NON_COMPLIANT = "handling-not-compliant"

# Band edges are read off instruments and derived limits are products and
# quotients, so a reading that is physically on an edge can land a few units
# in the last place outside it. Absorb that here; the limits stay as written.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _positive(label, value):
    """Return value as a positive finite float, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _real(label, value):
    """Return value as a finite float of any sign, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_least(value, bound):
    """True when value is at or above bound, absorbing representation error."""
    return value > bound or math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, bound):
    """True when value is at or below bound, absorbing representation error."""
    return value < bound or math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def categorize_sensitivity(withstand_v, model="human-body"):
    """Return the sensitivity band an assembly withstand voltage falls in."""
    if model not in SENSITIVITY_BANDS:
        raise ValueError(
            "discharge model must be one of %s, got %r" % (DISCHARGE_MODELS, model)
        )
    voltage = _positive("withstand_v", withstand_v)
    for name, upper in SENSITIVITY_BANDS[model]:
        if voltage < upper:
            return {
                "band": name,
                "rank": BAND_RANK[name],
                "model": model,
                "withstand_v": voltage,
            }
    name = SENSITIVITY_BANDS[model][-1][0]
    return {
        "band": name,
        "rank": BAND_RANK[name],
        "model": model,
        "withstand_v": voltage,
    }


def required_controls(band_rank):
    """Return the control names a sensitivity rank obliges, most sensitive first."""
    if isinstance(band_rank, bool) or not isinstance(band_rank, int):
        raise ValueError("band_rank must be an integer rank, got %r" % (band_rank,))
    if band_rank not in _EXTRA_BY_RANK:
        raise ValueError(
            "band_rank must be one of %s, got %r"
            % (sorted(_EXTRA_BY_RANK), band_rank)
        )
    return tuple(_BASE_CONTROLS) + tuple(_EXTRA_BY_RANK[band_rank])


def control_verdict(name, reading):
    """Grade one protected-area reading against its own acceptance band."""
    if name not in CONTROL_BANDS:
        raise ValueError(
            "unknown control %r; known controls are %s"
            % (name, sorted(CONTROL_BANDS))
        )
    band = CONTROL_BANDS[name]
    value = _real("%s reading" % name, reading)
    graded = abs(value) if band["symmetric"] else value
    if not band["symmetric"] and graded <= 0.0:
        raise ValueError("%s reading must be positive, got %r" % (name, reading))
    below = not _at_least(graded, band["low"])
    above = not _at_most(graded, band["high"])
    if below:
        return {
            "control": name,
            "reading": value,
            "in_band": False,
            "side": "below-band",
            "finding": "%s reads %g, under the %g floor; the path is too "
                       "conductive to be a control" % (name, value, band["low"]),
        }
    if above:
        return {
            "control": name,
            "reading": value,
            "in_band": False,
            "side": "above-band",
            "finding": "%s reads %g, over the %g ceiling; charge is not bled "
                       "away" % (name, value, band["high"]),
        }
    return {
        "control": name,
        "reading": value,
        "in_band": True,
        "side": "in-band",
        "finding": None,
    }


def evaluate_controls(readings, band_rank):
    """Grade a protected-area reading set against the controls a rank obliges."""
    if not isinstance(readings, dict):
        raise ValueError("readings must be a mapping of control name to value")
    needed = required_controls(band_rank)
    graded = []
    missing = []
    out_of_band = []
    for name in needed:
        if name not in readings:
            missing.append(name)
            continue
        verdict = control_verdict(name, readings[name])
        graded.append(verdict)
        if not verdict["in_band"]:
            out_of_band.append(name)
    off_scope = sorted(k for k in readings if k not in needed)
    for name in off_scope:
        if name not in CONTROL_BANDS:
            raise ValueError(
                "reading %r is not a recognised protected-area control" % (name,)
            )
    in_band = len(graded) - len(out_of_band)
    coverage = float(in_band) / float(len(needed))
    findings = []
    for name in missing:
        findings.append(
            "%s is obliged at this sensitivity band and no reading exists" % name
        )
    for verdict in graded:
        if verdict["finding"]:
            findings.append(verdict["finding"])
    return {
        "required": list(needed),
        "graded": graded,
        "missing": missing,
        "out_of_band": out_of_band,
        "off_scope": off_scope,
        "coverage": coverage,
        "findings": findings,
    }


def packaging_adequacy(package_type, band_rank):
    """Decide whether a packaging family is adequate for a sensitivity rank."""
    if package_type not in PACKAGING_RANK:
        raise ValueError(
            "packaging must be one of %s, got %r"
            % (sorted(PACKAGING_RANK), package_type)
        )
    if isinstance(band_rank, bool) or not isinstance(band_rank, int):
        raise ValueError("band_rank must be an integer rank, got %r" % (band_rank,))
    if band_rank not in _MIN_PACKAGING_BY_RANK:
        raise ValueError("band_rank must be one of %s, got %r"
                         % (sorted(_MIN_PACKAGING_BY_RANK), band_rank))
    needed = _MIN_PACKAGING_BY_RANK[band_rank]
    have = PACKAGING_RANK[package_type]
    adequate = have >= needed
    finding = None
    if not adequate:
        finding = (
            "%s packaging does not put a conductive boundary around an assembly "
            "in this band; shielding packaging is obliged" % package_type
        )
    return {
        "packaging": package_type,
        "packaging_rank": have,
        "required_rank": needed,
        "adequate": adequate,
        "finding": finding,
    }


def residual_voltage_v(charge_nc, capacitance_pf):
    """Return the voltage a residual charge makes across the assembly, in volts."""
    charge = _real("charge_nc", charge_nc)
    capacitance = _positive("capacitance_pf", capacitance_pf)
    return (charge * 1.0e-9) / (capacitance * 1.0e-12)


def decade_decay_time_s(resistance_ohm, capacitance_pf):
    """Return the time for a charged surface to fall by one decade, in seconds."""
    resistance = _positive("resistance_ohm", resistance_ohm)
    capacitance = _positive("capacitance_pf", capacitance_pf)
    return resistance * capacitance * 1.0e-12 * math.log(10.0)


def storage_envelope_findings(temperature_c, relative_humidity_percent, envelope):
    """Return findings where a storage condition sits outside its envelope."""
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping")
    for key in ("temperature_c", "relative_humidity_percent"):
        if key not in envelope:
            raise ValueError("envelope missing '%s' limits" % key)
        limits = envelope[key]
        if not isinstance(limits, (list, tuple)) or len(limits) != 2:
            raise ValueError("envelope['%s'] must be a (low, high) pair" % key)
    readings = {
        "temperature_c": _real("temperature_c", temperature_c),
        "relative_humidity_percent": _positive(
            "relative_humidity_percent", relative_humidity_percent
        ),
    }
    findings = []
    for key, value in readings.items():
        low = _real("envelope['%s'] low" % key, envelope[key][0])
        high = _real("envelope['%s'] high" % key, envelope[key][1])
        if low > high:
            raise ValueError("envelope['%s'] low exceeds high" % key)
        if not _at_least(value, low):
            findings.append(
                "stored %s of %g is under the %g floor of the envelope"
                % (key, value, low)
            )
        elif not _at_most(value, high):
            findings.append(
                "stored %s of %g is over the %g ceiling of the envelope"
                % (key, value, high)
            )
    return findings


def shelf_life_used_fraction(days_stored, shelf_life_days):
    """Return the share of the declared storage life already spent."""
    stored = _real("days_stored", days_stored)
    if stored < 0.0:
        raise ValueError("days_stored must not be negative, got %r" % (days_stored,))
    life = _positive("shelf_life_days", shelf_life_days)
    return stored / life


def assess_handling_and_storage(spec):
    """Grade one handling and storage record set for an ESD-sensitive assembly.

    spec keys: withstand_v, optional discharge_model, control_readings,
    packaging, storage_temperature_c, storage_relative_humidity_percent,
    storage_envelope, days_stored, shelf_life_days, optional residual_charge_nc
    and assembly_capacitance_pf.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "withstand_v",
        "control_readings",
        "packaging",
        "storage_temperature_c",
        "storage_relative_humidity_percent",
        "storage_envelope",
        "days_stored",
        "shelf_life_days",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    sensitivity = categorize_sensitivity(
        spec["withstand_v"], spec.get("discharge_model", "human-body")
    )
    rank = sensitivity["rank"]
    controls = evaluate_controls(spec["control_readings"], rank)
    packaging = packaging_adequacy(spec["packaging"], rank)
    storage = storage_envelope_findings(
        spec["storage_temperature_c"],
        spec["storage_relative_humidity_percent"],
        spec["storage_envelope"],
    )
    used = shelf_life_used_fraction(spec["days_stored"], spec["shelf_life_days"])

    findings = list(controls["findings"])
    if packaging["finding"]:
        findings.append(packaging["finding"])
    findings.extend(storage)

    residual = None
    margin = None
    if "residual_charge_nc" in spec or "assembly_capacitance_pf" in spec:
        if "residual_charge_nc" not in spec or "assembly_capacitance_pf" not in spec:
            raise ValueError(
                "residual charge and assembly capacitance are supplied together"
            )
        residual = abs(
            residual_voltage_v(
                spec["residual_charge_nc"], spec["assembly_capacitance_pf"]
            )
        )
        margin = sensitivity["withstand_v"] - residual
        if not _at_most(residual, sensitivity["withstand_v"]):
            findings.append(
                "residual charge leaves %.1f V across the assembly, over its "
                "%.1f V withstand voltage" % (residual, sensitivity["withstand_v"])
            )

    life_spent = not _at_most(used, 1.0)
    if life_spent:
        findings.append(
            "declared storage life is %.1f%% spent; the assembly needs "
            "re-qualification before use" % (used * 100.0)
        )

    blocking = bool(controls["missing"]) or bool(controls["out_of_band"]) \
        or not packaging["adequate"] \
        or (residual is not None and not _at_most(residual, sensitivity["withstand_v"]))
    restricted = bool(storage) or life_spent

    if blocking:
        verdict = HANDLING_NON_COMPLIANT
    elif restricted:
        verdict = HANDLING_CONDITIONAL
    else:
        verdict = HANDLING_COMPLIANT

    return {
        "sensitivity": sensitivity,
        "controls": controls,
        "packaging": packaging,
        "storage_findings": storage,
        "shelf_life_used_fraction": used,
        "residual_voltage_v": residual,
        "withstand_margin_v": margin,
        "verdict": verdict,
        "findings": findings,
    }
