#!/usr/bin/env python3
"""Reverse current-voltage record of a photovoltaic cell assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.14.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The process this clause describes is narrow and easy to carry out wrongly.
An assembly that has no protection diode coupled to the cell itself will be
driven backwards by the rest of its string, so its reverse current-voltage
behaviour has to be on record. An assembly whose diode sits across the cell
never sees more than a diode drop of reverse voltage, so the record buys
nothing -- the exemption turns on where the diode is, not on whether one
exists anywhere in the circuit. A string-level or section-level diode
protects the string, not the cell, and leaves the assembly in scope.

The sweep itself has to be taken under illumination. In the dark an
assembly is only a junction, and the reverse curve of a junction is not the
curve of an illuminated cell being pushed backwards by its neighbours: the
photocurrent the string forces through it is exactly the quantity of
interest, and it is absent from a dark sweep.

What makes a sweep usable:

    monotone        reverse voltage magnitudes strictly increasing, so the
                    record is a curve and not a scatter of revisits
    extent          it reaches the reverse voltage the requirement names,
                    rather than stopping at the first interesting point
    resolution      no voltage step wider than the requirement allows, so
                    the breakdown knee falls between measured points rather
                    than being straddled by one long chord
    dissipation     the peak of voltage times current, which is the number
                    the thermal case downstream actually consumes

Standard library only, offline, deterministic.
"""

import math

__all__ = [
    "COMPARISON_ABSOLUTE_TOLERANCE",
    "COMPARISON_RELATIVE_TOLERANCE",
    "DIODE_COUPLINGS",
    "assess_assembly",
    "assess_reverse_bias_process",
    "is_illuminated",
    "largest_voltage_step",
    "normalize_coupling",
    "peak_dissipation",
    "record_is_required",
    "sweep_extent_v",
    "validate_requirement",
    "validate_sweep",
    "validate_sweep_point",
]

# Voltages and currents arrive as scaled instrument readings, so a value
# physically equal to a limit can land a few ULPs on the wrong side. Absorb
# that here rather than moving any requirement.
COMPARISON_RELATIVE_TOLERANCE = 1e-12
COMPARISON_ABSOLUTE_TOLERANCE = 1e-12

# Where the protection diode sits -> whether that placement exempts the
# assembly from carrying a reverse current-voltage record. Only a diode
# coupled to the cell itself clamps the cell's own reverse voltage.
DIODE_COUPLINGS = {
    "cell-coupled-protection-diode": True,
    "string-coupled-protection-diode": False,
    "section-coupled-protection-diode": False,
    "no-protection-diode": False,
}


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _close(left, right):
    """Return True when two measured quantities are equal within tolerance."""
    return math.isclose(
        left,
        right,
        rel_tol=COMPARISON_RELATIVE_TOLERANCE,
        abs_tol=COMPARISON_ABSOLUTE_TOLERANCE,
    )


def _at_or_below(value, limit):
    """Return True when value stays at or under limit, tolerating equality."""
    return value < limit or _close(value, limit)


def _at_or_above(value, limit):
    """Return True when value reaches limit, tolerating equality."""
    return value > limit or _close(value, limit)


def normalize_coupling(coupling):
    """Return a recognized protection-diode placement, refusing anything else."""
    if not isinstance(coupling, str):
        raise ValueError("diode_coupling must be a string, got %r" % (coupling,))
    cleaned = coupling.strip().lower()
    if cleaned not in DIODE_COUPLINGS:
        raise ValueError(
            "unrecognized diode_coupling %r; recognized: %s"
            % (coupling, ", ".join(sorted(DIODE_COUPLINGS)))
        )
    return cleaned


def record_is_required(coupling):
    """Return True when the placement leaves the assembly owing a record."""
    return not DIODE_COUPLINGS[normalize_coupling(coupling)]


def is_illuminated(irradiance_w_m2, minimum_w_m2):
    """Return True when the sweep irradiance reaches the declared minimum."""
    measured = _non_negative(irradiance_w_m2, "irradiance_w_m2")
    floor = _positive(minimum_w_m2, "min_irradiance_w_m2")
    return _at_or_above(measured, floor)


def validate_sweep_point(point, label="point"):
    """Return one reverse sweep point as a validated magnitude pair."""
    if not isinstance(point, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("reverse_voltage_v", "reverse_current_a"):
        if key not in point:
            raise ValueError("%s missing required key '%s'" % (label, key))
    return {
        "reverse_voltage_v": _non_negative(
            point["reverse_voltage_v"], "%s reverse_voltage_v" % label
        ),
        "reverse_current_a": _non_negative(
            point["reverse_current_a"], "%s reverse_current_a" % label
        ),
    }


def validate_sweep(points):
    """Return the sweep as validated points, strictly advancing in voltage."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be a sequence of sweep points")
    if len(points) < 2:
        raise ValueError("a sweep needs at least two points, got %d" % len(points))
    validated = []
    for index, point in enumerate(points):
        record = validate_sweep_point(point, "points[%d]" % index)
        if validated:
            previous = validated[-1]["reverse_voltage_v"]
            current = record["reverse_voltage_v"]
            if _close(current, previous):
                raise ValueError(
                    "points[%d] repeats the reverse voltage %g V"
                    % (index, current)
                )
            if current < previous:
                raise ValueError(
                    "points[%d] steps back from %g V to %g V; the sweep must "
                    "advance in reverse voltage" % (index, previous, current)
                )
        validated.append(record)
    return validated


def largest_voltage_step(points):
    """Return the widest reverse-voltage gap between consecutive points."""
    validated = validate_sweep(points)
    widest = 0.0
    for index in range(1, len(validated)):
        step = (
            validated[index]["reverse_voltage_v"]
            - validated[index - 1]["reverse_voltage_v"]
        )
        if step > widest:
            widest = step
    return widest


def sweep_extent_v(points):
    """Return the largest reverse voltage the sweep actually reached."""
    validated = validate_sweep(points)
    return validated[-1]["reverse_voltage_v"]


def peak_dissipation(points):
    """Return the sweep point at which the assembly dissipated the most."""
    validated = validate_sweep(points)
    best = None
    for record in validated:
        power = record["reverse_voltage_v"] * record["reverse_current_a"]
        if best is None or power > best["power_w"]:
            best = {
                "reverse_voltage_v": record["reverse_voltage_v"],
                "reverse_current_a": record["reverse_current_a"],
                "power_w": power,
            }
    return best


def validate_requirement(requirement):
    """Return the sweep requirement as validated positive quantities."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    for key in ("min_irradiance_w_m2", "required_extent_v", "max_step_v"):
        if key not in requirement:
            raise ValueError("requirement missing required key '%s'" % key)
    return {
        "min_irradiance_w_m2": _positive(
            requirement["min_irradiance_w_m2"], "min_irradiance_w_m2"
        ),
        "required_extent_v": _positive(
            requirement["required_extent_v"], "required_extent_v"
        ),
        "max_step_v": _positive(requirement["max_step_v"], "max_step_v"),
    }


def assess_assembly(assembly, requirement):
    """Return the record status of one assembly against the sweep requirement.

    assembly keys: assembly_id, diode_coupling; optional sweep, itself a
    mapping of irradiance_w_m2 and points.
    """
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping")
    for key in ("assembly_id", "diode_coupling"):
        if key not in assembly:
            raise ValueError("assembly missing required key '%s'" % key)
    assembly_id = assembly["assembly_id"]
    if not isinstance(assembly_id, str) or not assembly_id.strip():
        raise ValueError("assembly_id must be a non-empty string")
    assembly_id = assembly_id.strip()
    coupling = normalize_coupling(assembly["diode_coupling"])
    wanted = validate_requirement(requirement)
    required = record_is_required(coupling)

    outcome = {
        "assembly_id": assembly_id,
        "diode_coupling": coupling,
        "record_required": required,
        "record_present": False,
        "illuminated": None,
        "irradiance_w_m2": None,
        "extent_v": None,
        "largest_step_v": None,
        "peak_dissipation": None,
        "findings": [],
    }

    sweep = assembly.get("sweep")
    if sweep is None:
        if required:
            outcome["findings"].append(
                "assembly %s carries a %s and owes a reverse current-voltage "
                "record, and none was taken" % (assembly_id, coupling)
            )
        return outcome
    if not isinstance(sweep, dict):
        raise ValueError("assembly %s sweep must be a mapping" % assembly_id)
    for key in ("irradiance_w_m2", "points"):
        if key not in sweep:
            raise ValueError(
                "assembly %s sweep missing required key '%s'" % (assembly_id, key)
            )

    points = validate_sweep(sweep["points"])
    irradiance = _non_negative(
        sweep["irradiance_w_m2"], "assembly %s irradiance_w_m2" % assembly_id
    )
    outcome["record_present"] = True
    outcome["irradiance_w_m2"] = irradiance
    outcome["illuminated"] = is_illuminated(
        irradiance, wanted["min_irradiance_w_m2"]
    )
    outcome["extent_v"] = sweep_extent_v(points)
    outcome["largest_step_v"] = largest_voltage_step(points)
    outcome["peak_dissipation"] = peak_dissipation(points)

    if not outcome["illuminated"]:
        outcome["findings"].append(
            "assembly %s was swept at %g W/m2, under the %g W/m2 the record "
            "needs; a dark reverse curve is not the illuminated one"
            % (assembly_id, irradiance, wanted["min_irradiance_w_m2"])
        )
    if not _at_or_above(outcome["extent_v"], wanted["required_extent_v"]):
        outcome["findings"].append(
            "assembly %s reached %g V of reverse voltage, short of the %g V "
            "required" % (assembly_id, outcome["extent_v"],
                          wanted["required_extent_v"])
        )
    if not _at_or_below(outcome["largest_step_v"], wanted["max_step_v"]):
        outcome["findings"].append(
            "assembly %s stepped %g V between points, wider than the %g V that "
            "resolves the knee" % (assembly_id, outcome["largest_step_v"],
                                   wanted["max_step_v"])
        )
    return outcome


def assess_reverse_bias_process(spec):
    """Run the full clause 6.4.3.14.2 process check over a set of assemblies.

    spec keys: assemblies, requirement.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("assemblies", "requirement"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    assemblies = spec["assemblies"]
    if not isinstance(assemblies, (list, tuple)) or not assemblies:
        raise ValueError("assemblies must be a non-empty sequence")
    requirement = validate_requirement(spec["requirement"])

    seen = set()
    outcomes = []
    for assembly in assemblies:
        outcome = assess_assembly(assembly, requirement)
        if outcome["assembly_id"] in seen:
            raise ValueError(
                "duplicate assembly_id %r in assemblies" % outcome["assembly_id"]
            )
        seen.add(outcome["assembly_id"])
        outcomes.append(outcome)

    findings = []
    for outcome in outcomes:
        findings.extend(outcome["findings"])

    required_ids = [o["assembly_id"] for o in outcomes if o["record_required"]]
    recorded_ids = [
        o["assembly_id"] for o in outcomes
        if o["record_required"] and o["record_present"]
    ]
    exempt_ids = [o["assembly_id"] for o in outcomes if not o["record_required"]]

    return {
        "requirement": requirement,
        "assemblies": outcomes,
        "required_ids": tuple(required_ids),
        "recorded_ids": tuple(recorded_ids),
        "exempt_ids": tuple(exempt_ids),
        "records_required": len(required_ids),
        "records_taken": len(recorded_ids),
        "findings": findings,
        "passed": not findings,
    }
