"""Over-current protection and harness strain relief for spacecraft mechanisms.

Anchor: ECSS-E-ST-33-01C clauses 4.7.7.6 and 4.7.7.7 (protecting a motor or
actuator circuit against over-current, and protecting the wires that cross a
moving joint against strain). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Size the protection device of each drive circuit. Its rating has to sit
   above the worst-case operating current with margin and below the derated
   capability of the smallest wire it protects, again with margin. When those
   two bounds cross, no rating exists and the wire gauge or the drive has to
   change.
2. Check the stall case. A stalled motor draws far more than its running
   current, so either the protection device interrupts inside the wire's
   thermal withstand time or the wire is sized to carry the stall current
   indefinitely.
3. Size the service loop of every harness crossing a moving joint: the free
   length has to cover the travel without going taut, the bend radius has to
   stay above the cable's minimum, and the resulting conductor strain has to
   stay inside the flexure allowable for the required number of cycles.
"""

import math

__all__ = [
    "CURRENT_TOLERANCE_A",
    "TIME_TOLERANCE_S",
    "STRAIN_TOLERANCE",
    "LENGTH_TOLERANCE_M",
    "DEFAULT_OPERATING_FACTOR",
    "DEFAULT_WIRE_FACTOR",
    "validate_circuit",
    "wire_capacity_a",
    "protection_window_a",
    "grade_protection_rating",
    "stall_findings",
    "validate_crossing",
    "service_loop_length_m",
    "bend_radius_m",
    "conductor_bending_strain",
    "grade_crossing",
    "assess_overcurrent_and_strain",
]

# Comparisons against a limit can land a few ULPs on the wrong side of an
# exact equality. Absorb the representation error here rather than relaxing
# the engineering limit.
CURRENT_TOLERANCE_A = 1e-9
TIME_TOLERANCE_S = 1e-9
STRAIN_TOLERANCE = 1e-12
LENGTH_TOLERANCE_M = 1e-12

# The protection rating sits at least this factor above the worst-case
# operating current, so a nominal duty cycle does not open it.
DEFAULT_OPERATING_FACTOR = 1.5

# ... and at most this fraction of the wire's derated capacity, so the device
# opens before the insulation reaches its temperature limit.
DEFAULT_WIRE_FACTOR = 0.8


def _positive(label, value):
    """Return value as a positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def _fraction(label, value):
    """Return value as a float in (0, 1] or raise ValueError."""
    number = _positive(label, value)
    if number > 1.0:
        raise ValueError("%s must not exceed unity, got %r" % (label, value))
    return number


def wire_capacity_a(single_wire_rating_a, bundle_derating=1.0, altitude_derating=1.0):
    """Return the derated current capacity of a wire inside its harness."""
    rating = _positive("single_wire_rating_a", single_wire_rating_a)
    bundle = _fraction("bundle_derating", bundle_derating)
    altitude = _fraction("altitude_derating", altitude_derating)
    return rating * bundle * altitude


def validate_circuit(circuit):
    """Return a normalised drive-circuit record.

    Required keys: id, operating_current_a, stall_current_a,
    wire_rating_a, protection_rating_a, protection_trip_time_s,
    wire_withstand_time_s. Optional: bundle_derating, altitude_derating,
    wire_carries_stall (bool).
    """
    if not isinstance(circuit, dict):
        raise ValueError("circuit must be a mapping")
    for key in ("id", "operating_current_a", "stall_current_a", "wire_rating_a",
                "protection_rating_a", "protection_trip_time_s", "wire_withstand_time_s"):
        if key not in circuit:
            raise ValueError("circuit missing required key '%s'" % key)
    identifier = circuit["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("circuit id must be a non-empty string")
    record = {
        "id": identifier.strip(),
        "operating_current_a": _positive("operating_current_a", circuit["operating_current_a"]),
        "stall_current_a": _positive("stall_current_a", circuit["stall_current_a"]),
        "wire_rating_a": _positive("wire_rating_a", circuit["wire_rating_a"]),
        "protection_rating_a": _positive("protection_rating_a", circuit["protection_rating_a"]),
        "protection_trip_time_s": _positive(
            "protection_trip_time_s", circuit["protection_trip_time_s"]
        ),
        "wire_withstand_time_s": _positive(
            "wire_withstand_time_s", circuit["wire_withstand_time_s"]
        ),
        "bundle_derating": _fraction("bundle_derating", circuit.get("bundle_derating", 1.0)),
        "altitude_derating": _fraction(
            "altitude_derating", circuit.get("altitude_derating", 1.0)
        ),
        "wire_carries_stall": bool(circuit.get("wire_carries_stall", False)),
    }
    if record["stall_current_a"] < record["operating_current_a"]:
        raise ValueError(
            "circuit '%s': stall current %g A is below the operating current %g A"
            % (record["id"], record["stall_current_a"], record["operating_current_a"])
        )
    return record


def protection_window_a(circuit, operating_factor=DEFAULT_OPERATING_FACTOR,
                        wire_factor=DEFAULT_WIRE_FACTOR):
    """Return the (lower, upper) rating window a protection device must sit in."""
    record = validate_circuit(circuit)
    low_factor = _positive("operating_factor", operating_factor)
    high_factor = _fraction("wire_factor", wire_factor)
    if low_factor < 1.0:
        raise ValueError("operating_factor must be at least unity, got %r" % (operating_factor,))
    capacity = wire_capacity_a(
        record["wire_rating_a"], record["bundle_derating"], record["altitude_derating"]
    )
    return (record["operating_current_a"] * low_factor, capacity * high_factor)


def grade_protection_rating(circuit, operating_factor=DEFAULT_OPERATING_FACTOR,
                            wire_factor=DEFAULT_WIRE_FACTOR):
    """Return the protection-device sizing record for one drive circuit."""
    record = validate_circuit(circuit)
    low, high = protection_window_a(circuit, operating_factor, wire_factor)
    rating = record["protection_rating_a"]
    findings = []
    window_exists = high > low or math.isclose(
        high, low, rel_tol=0.0, abs_tol=CURRENT_TOLERANCE_A
    )
    if not window_exists:
        findings.append(
            "%s: no rating satisfies both bounds (lower %.4f A above upper %.4f A); "
            "the wire gauge or the drive current has to change"
            % (record["id"], low, high)
        )
    above_low = rating > low or math.isclose(rating, low, rel_tol=0.0, abs_tol=CURRENT_TOLERANCE_A)
    below_high = rating < high or math.isclose(
        rating, high, rel_tol=0.0, abs_tol=CURRENT_TOLERANCE_A
    )
    if not above_low:
        findings.append(
            "%s: protection rating %.4f A sits below the %.4f A lower bound; nominal duty "
            "will open it" % (record["id"], rating, low)
        )
    if not below_high:
        findings.append(
            "%s: protection rating %.4f A sits above the %.4f A the derated wire supports; "
            "the wire fails before the device opens" % (record["id"], rating, high)
        )
    return {
        "id": record["id"],
        "lower_bound_a": low,
        "upper_bound_a": high,
        "rating_a": rating,
        "window_exists": window_exists,
        "compliant": window_exists and above_low and below_high,
        "findings": findings,
    }


def stall_findings(circuit):
    """Return the stall-case findings for one drive circuit."""
    record = validate_circuit(circuit)
    findings = []
    if record["wire_carries_stall"]:
        capacity = wire_capacity_a(
            record["wire_rating_a"], record["bundle_derating"], record["altitude_derating"]
        )
        supports = capacity > record["stall_current_a"] or math.isclose(
            capacity, record["stall_current_a"], rel_tol=0.0, abs_tol=CURRENT_TOLERANCE_A
        )
        if not supports:
            findings.append(
                "%s: declared to carry stall indefinitely, but the derated wire supports "
                "%.4f A against a %.4f A stall"
                % (record["id"], capacity, record["stall_current_a"])
            )
        return findings
    interrupts = (
        record["protection_trip_time_s"] < record["wire_withstand_time_s"]
        or math.isclose(
            record["protection_trip_time_s"], record["wire_withstand_time_s"],
            rel_tol=0.0, abs_tol=TIME_TOLERANCE_S,
        )
    )
    if not interrupts:
        findings.append(
            "%s: protection trips in %.4g s against a %.4g s wire withstand time; the "
            "insulation reaches its limit first"
            % (record["id"], record["protection_trip_time_s"], record["wire_withstand_time_s"])
        )
    if record["stall_current_a"] < record["protection_rating_a"]:
        findings.append(
            "%s: stall current %.4f A never reaches the %.4f A protection rating, so a "
            "stall is not interrupted at all"
            % (record["id"], record["stall_current_a"], record["protection_rating_a"])
        )
    return findings


def service_loop_length_m(travel_m, slack_factor=1.25):
    """Return the free harness length a moving joint's travel calls for."""
    travel = _positive("travel_m", travel_m)
    factor = _positive("slack_factor", slack_factor)
    if factor < 1.0:
        raise ValueError("slack_factor must be at least unity, got %r" % (slack_factor,))
    return travel * factor


def bend_radius_m(free_length_m, wrap_angle_rad):
    """Return the bend radius a free length takes over a wrap angle."""
    length = _positive("free_length_m", free_length_m)
    angle = _positive("wrap_angle_rad", wrap_angle_rad)
    if angle > 2.0 * math.pi:
        raise ValueError("wrap_angle_rad must not exceed one full turn, got %r" % (wrap_angle_rad,))
    return length / angle


def conductor_bending_strain(cable_diameter_m, radius_m):
    """Return the outer-fibre strain of a conductor bent to a radius."""
    diameter = _positive("cable_diameter_m", cable_diameter_m)
    radius = _positive("radius_m", radius_m)
    return diameter / (2.0 * radius + diameter)


def validate_crossing(crossing):
    """Return a normalised moving-joint harness-crossing record.

    Required keys: id, travel_m, free_length_m, cable_diameter_m,
    min_bend_radius_m, wrap_angle_rad, allowable_strain, cycles_required,
    cycles_qualified.
    """
    if not isinstance(crossing, dict):
        raise ValueError("crossing must be a mapping")
    for key in ("id", "travel_m", "free_length_m", "cable_diameter_m", "min_bend_radius_m",
                "wrap_angle_rad", "allowable_strain", "cycles_required", "cycles_qualified"):
        if key not in crossing:
            raise ValueError("crossing missing required key '%s'" % key)
    identifier = crossing["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("crossing id must be a non-empty string")
    for key in ("cycles_required", "cycles_qualified"):
        if not isinstance(crossing[key], int) or isinstance(crossing[key], bool):
            raise ValueError("%s must be an integer count" % key)
        if crossing[key] < 1:
            raise ValueError("%s must be at least one" % key)
    return {
        "id": identifier.strip(),
        "travel_m": _positive("travel_m", crossing["travel_m"]),
        "free_length_m": _positive("free_length_m", crossing["free_length_m"]),
        "cable_diameter_m": _positive("cable_diameter_m", crossing["cable_diameter_m"]),
        "min_bend_radius_m": _positive("min_bend_radius_m", crossing["min_bend_radius_m"]),
        "wrap_angle_rad": _positive("wrap_angle_rad", crossing["wrap_angle_rad"]),
        "allowable_strain": _positive("allowable_strain", crossing["allowable_strain"]),
        "cycles_required": crossing["cycles_required"],
        "cycles_qualified": crossing["cycles_qualified"],
        "slack_factor": _positive("slack_factor", crossing.get("slack_factor", 1.25)),
    }


def grade_crossing(crossing):
    """Return the strain-relief grading of one harness crossing a moving joint."""
    record = validate_crossing(crossing)
    required_length = service_loop_length_m(record["travel_m"], record["slack_factor"])
    radius = bend_radius_m(record["free_length_m"], record["wrap_angle_rad"])
    strain = conductor_bending_strain(record["cable_diameter_m"], radius)
    findings = []
    length_ok = record["free_length_m"] > required_length or math.isclose(
        record["free_length_m"], required_length, rel_tol=0.0, abs_tol=LENGTH_TOLERANCE_M
    )
    radius_ok = radius > record["min_bend_radius_m"] or math.isclose(
        radius, record["min_bend_radius_m"], rel_tol=0.0, abs_tol=LENGTH_TOLERANCE_M
    )
    strain_ok = strain < record["allowable_strain"] or math.isclose(
        strain, record["allowable_strain"], rel_tol=0.0, abs_tol=STRAIN_TOLERANCE
    )
    cycles_ok = record["cycles_qualified"] >= record["cycles_required"]
    if not length_ok:
        findings.append(
            "%s: free length %.4f m is short of the %.4f m the travel calls for; the harness "
            "goes taut at end of travel"
            % (record["id"], record["free_length_m"], required_length)
        )
    if not radius_ok:
        findings.append(
            "%s: bend radius %.4f m is tighter than the %.4f m cable minimum"
            % (record["id"], radius, record["min_bend_radius_m"])
        )
    if not strain_ok:
        findings.append(
            "%s: conductor strain %.6f exceeds the %.6f flexure allowable"
            % (record["id"], strain, record["allowable_strain"])
        )
    if not cycles_ok:
        findings.append(
            "%s: qualified to %d flexure cycles against %d required"
            % (record["id"], record["cycles_qualified"], record["cycles_required"])
        )
    return {
        "id": record["id"],
        "required_length_m": required_length,
        "bend_radius_m": radius,
        "strain": strain,
        "length_ok": length_ok,
        "radius_ok": radius_ok,
        "strain_ok": strain_ok,
        "cycles_ok": cycles_ok,
        "compliant": length_ok and radius_ok and strain_ok and cycles_ok,
        "findings": findings,
    }


def assess_overcurrent_and_strain(spec):
    """Run the full clause 4.7.7.6 / 4.7.7.7 protection and strain assessment.

    spec keys: circuits (non-empty sequence), crossings (sequence, may be
    empty). Optional: operating_factor, wire_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("circuits", "crossings"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    circuits = spec["circuits"]
    if not isinstance(circuits, (list, tuple)) or not circuits:
        raise ValueError("spec['circuits'] must be a non-empty sequence")
    crossings = spec["crossings"]
    if not isinstance(crossings, (list, tuple)):
        raise ValueError("spec['crossings'] must be a sequence")
    findings = []
    circuit_records = []
    seen = set()
    for circuit in circuits:
        sizing = grade_protection_rating(
            circuit,
            spec.get("operating_factor", DEFAULT_OPERATING_FACTOR),
            spec.get("wire_factor", DEFAULT_WIRE_FACTOR),
        )
        if sizing["id"] in seen:
            raise ValueError("duplicate circuit id '%s'" % sizing["id"])
        seen.add(sizing["id"])
        stall = stall_findings(circuit)
        sizing = dict(sizing)
        sizing["stall_findings"] = stall
        sizing["findings"] = list(sizing["findings"]) + list(stall)
        sizing["compliant"] = not sizing["findings"]
        circuit_records.append(sizing)
        findings.extend(sizing["findings"])
    crossing_records = []
    for crossing in crossings:
        graded = grade_crossing(crossing)
        crossing_records.append(graded)
        findings.extend(graded["findings"])
    return {
        "circuits": circuit_records,
        "crossings": crossing_records,
        "findings": findings,
        "compliant": not findings,
    }
