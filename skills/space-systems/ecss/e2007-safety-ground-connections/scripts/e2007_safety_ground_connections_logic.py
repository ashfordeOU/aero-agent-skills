#!/usr/bin/env python3
"""Safety-ground (protective-earth) provision checking for an
electromagnetic-compatibility bench setup.

Anchor: ECSS-E-ST-20-07C clause 5.2.6.4 (paraphrased into an
implementable procedure; no verbatim standard text).

The clause requires the protective-earth provision a unit is given on
the bench to mirror the provision the real installation uses: the same
family of connection, the same terminal count, the same earth-pin
designations. The provision is then graded as a fault path -- sized
adiabatically for the prospective fault-current over the clearing-time,
bounded in path resistance, and kept clear of any signal-return duty.

Offline, deterministic, python3 standard library only.
"""

import math

PROVISION_CATEGORIES = (
    "protective-earth-terminal",
    "protective-earth-pin",
    "mounting-base-bond",
    "unbonded",
)

# conductor family -> adiabatic material constant k, in A*s^0.5/mm^2
CONDUCTOR_FAMILIES = {
    "copper-pvc": 143.0,
    "copper-cross-linked": 176.0,
    "copper-bare": 159.0,
    "aluminium-pvc": 95.0,
}

COPPER_RESISTIVITY_OHM_M = 1.72e-8
DEFAULT_CONDUCTOR_FAMILY = "copper-pvc"
DEFAULT_PATH_LIMIT_OHM = 0.1
REL_TOL = 1e-9


def _mapping(record, label):
    """Return record as a mapping or raise ValueError."""
    if not isinstance(record, dict):
        raise ValueError(
            "%s must be a mapping, got %s" % (label, type(record).__name__)
        )
    return record


def _number(value, label, minimum=None, strict=False):
    """Return value as a finite float, bounded below, or raise ValueError."""
    if value is None:
        raise ValueError("%s is required" % label)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    val = float(value)
    if math.isnan(val) or math.isinf(val):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if strict and val <= minimum:
            raise ValueError("%s must be > %g, got %g" % (label, minimum, val))
        if not strict and val < minimum:
            raise ValueError("%s must be >= %g, got %g" % (label, minimum, val))
    return val


def _count(value, label):
    """Return value as a non-negative integer or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be >= 0, got %d" % (label, value))
    return value


def _at_least(value, floor):
    """True when value meets floor, absorbing float representation error."""
    return value >= floor or math.isclose(value, floor, rel_tol=REL_TOL)


def _at_most(value, ceiling):
    """True when value is under ceiling, absorbing representation error.

    A summed path resistance that lands a few ULPs above a limit it
    physically meets must not be graded as an exceedance; the comparison
    absorbs the representation error rather than widening the limit.
    """
    return value <= ceiling or math.isclose(value, ceiling, rel_tol=REL_TOL)


def _designations(value, label):
    """Return earth-pin designations as a validated list of strings."""
    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list of pin designations" % label)
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "%s entries must be non-empty strings, got %r" % (label, item)
            )
        name = item.strip()
        if name in out:
            raise ValueError("%s repeats designation %r" % (label, name))
        out.append(name)
    return out


def categorize_safety_ground_provision(record):
    """Categorize a safety-ground record into one of PROVISION_CATEGORIES.

    record keys: terminal_studs (int, default 0), earth_pin_designations
    (list of str, default empty), mounting_base_bonded (bool, default False).
    """
    rec = _mapping(record, "safety-ground provision record")
    studs = _count(rec.get("terminal_studs", 0), "terminal_studs")
    pins = _designations(rec.get("earth_pin_designations"),
                         "earth_pin_designations")
    bonded = rec.get("mounting_base_bonded", False)
    if not isinstance(bonded, bool):
        raise ValueError(
            "mounting_base_bonded must be a boolean, got %r" % (bonded,)
        )
    if studs > 0:
        return "protective-earth-terminal"
    if pins:
        return "protective-earth-pin"
    if bonded:
        return "mounting-base-bond"
    return "unbonded"


def required_earth_conductor_area(fault_current_a, clearing_time_s,
                                  conductor_family=DEFAULT_CONDUCTOR_FAMILY):
    """Minimum protective-earth cross-section from the adiabatic relation.

    area_min = fault_current * sqrt(clearing_time) / k, in square millimetres.
    """
    current = _number(fault_current_a, "fault_current_a", minimum=0.0,
                      strict=True)
    duration = _number(clearing_time_s, "clearing_time_s", minimum=0.0,
                       strict=True)
    if conductor_family not in CONDUCTOR_FAMILIES:
        raise ValueError(
            "unknown conductor_family %r; known families: %s"
            % (conductor_family, ", ".join(sorted(CONDUCTOR_FAMILIES)))
        )
    k_factor = CONDUCTOR_FAMILIES[conductor_family]
    return current * math.sqrt(duration) / k_factor


def check_earth_conductor_sizing(area_mm2, fault_current_a, clearing_time_s,
                                 conductor_family=DEFAULT_CONDUCTOR_FAMILY):
    """Grade an installed protective-earth cross-section against the fault."""
    provided = _number(area_mm2, "area_mm2", minimum=0.0, strict=True)
    required = required_earth_conductor_area(
        fault_current_a, clearing_time_s, conductor_family
    )
    adequate = _at_least(provided, required)
    findings = []
    if not adequate:
        findings.append(
            "protective-earth-conductor-undersized: %.4f mm2 installed "
            "against %.4f mm2 required" % (provided, required)
        )
    return {
        "provided_mm2": provided,
        "required_mm2": required,
        "conductor_family": conductor_family,
        "adequate": adequate,
        "findings": findings,
    }


def conductor_resistance(length_m, area_mm2,
                         resistivity_ohm_m=COPPER_RESISTIVITY_OHM_M):
    """Direct-current resistance of a conductor run, in ohm."""
    length = _number(length_m, "length_m", minimum=0.0)
    area = _number(area_mm2, "area_mm2", minimum=0.0, strict=True)
    rho = _number(resistivity_ohm_m, "resistivity_ohm_m", minimum=0.0,
                  strict=True)
    return rho * length / (area * 1.0e-6)


def segment_resistance(segment):
    """Resolve one safety-ground path segment into a resistance in ohm.

    A segment declares either a measured resistance_ohm or a geometry
    (length_m plus area_mm2), never both.
    """
    rec = _mapping(segment, "path segment")
    has_measured = "resistance_ohm" in rec
    has_geometry = "length_m" in rec or "area_mm2" in rec
    if has_measured and has_geometry:
        raise ValueError(
            "path segment declares both a measured resistance and a geometry"
        )
    if has_measured:
        return _number(rec.get("resistance_ohm"), "resistance_ohm",
                       minimum=0.0)
    if has_geometry:
        return conductor_resistance(
            rec.get("length_m"), rec.get("area_mm2"),
            rec.get("resistivity_ohm_m", COPPER_RESISTIVITY_OHM_M),
        )
    raise ValueError(
        "path segment must declare resistance_ohm or length_m plus area_mm2"
    )


def safety_ground_path_resistance(segments):
    """Sum the resistance of every segment of the safety-ground path."""
    if isinstance(segments, dict) or not isinstance(segments, (list, tuple)):
        raise ValueError("segments must be a list of path segments")
    if not segments:
        raise ValueError("safety-ground path must declare at least one segment")
    total = 0.0
    for segment in segments:
        total += segment_resistance(segment)
    return total


def check_path_resistance(total_ohm, limit_ohm=DEFAULT_PATH_LIMIT_OHM):
    """Grade a summed safety-ground path resistance against its limit."""
    total = _number(total_ohm, "total_ohm", minimum=0.0)
    limit = _number(limit_ohm, "limit_ohm", minimum=0.0, strict=True)
    within = _at_most(total, limit)
    findings = []
    if not within:
        findings.append(
            "safety-ground-path-resistance-exceeded: %.6f ohm against "
            "%.6f ohm" % (total, limit)
        )
    return {
        "total_ohm": total,
        "limit_ohm": limit,
        "within_limit": within,
        "findings": findings,
    }


def compare_safety_ground_provision(flight, bench):
    """Compare the bench safety-ground provision against the flight one."""
    flight_category = categorize_safety_ground_provision(flight)
    bench_category = categorize_safety_ground_provision(bench)
    findings = []
    if flight_category == "unbonded":
        findings.append(
            "flight-safety-ground-provision-absent: no protective-earth "
            "connection declared for the installation"
        )
    if bench_category == "unbonded":
        findings.append(
            "bench-safety-ground-provision-absent: no protective-earth "
            "connection declared for the setup"
        )
    if flight_category != bench_category:
        findings.append(
            "safety-ground-provision-mismatch: flight %s against bench %s"
            % (flight_category, bench_category)
        )
        return {
            "flight_category": flight_category,
            "bench_category": bench_category,
            "findings": findings,
        }
    if flight_category == "protective-earth-terminal":
        flight_studs = _count(flight.get("terminal_studs", 0),
                              "terminal_studs")
        bench_studs = _count(bench.get("terminal_studs", 0), "terminal_studs")
        if flight_studs != bench_studs:
            findings.append(
                "protective-earth-terminal-count-mismatch: flight %d against "
                "bench %d" % (flight_studs, bench_studs)
            )
    elif flight_category == "protective-earth-pin":
        flight_pins = set(_designations(flight.get("earth_pin_designations"),
                                        "earth_pin_designations"))
        bench_pins = set(_designations(bench.get("earth_pin_designations"),
                                       "earth_pin_designations"))
        missing = sorted(flight_pins - bench_pins)
        extra = sorted(bench_pins - flight_pins)
        if missing:
            findings.append(
                "protective-earth-pin-missing-on-bench: %s" % ", ".join(missing)
            )
        if extra:
            findings.append(
                "protective-earth-pin-added-on-bench: %s" % ", ".join(extra)
            )
    return {
        "flight_category": flight_category,
        "bench_category": bench_category,
        "findings": findings,
    }


def assess_safety_ground_connections(setup):
    """Full clause 5.2.6.4 safety-ground assessment for one unit."""
    rec = _mapping(setup, "setup")
    unit_id = rec.get("unit_id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("setup requires a non-empty unit_id")
    flight = _mapping(rec.get("flight_provision"), "flight_provision")
    bench = _mapping(rec.get("bench_provision"), "bench_provision")
    comparison = compare_safety_ground_provision(flight, bench)
    findings = list(comparison["findings"])
    conductor = _mapping(rec.get("conductor"), "conductor")
    sizing = check_earth_conductor_sizing(
        conductor.get("area_mm2"),
        rec.get("fault_current_a"),
        rec.get("clearing_time_s"),
        conductor.get("family", DEFAULT_CONDUCTOR_FAMILY),
    )
    findings.extend(sizing["findings"])
    total = safety_ground_path_resistance(rec.get("path_segments"))
    path = check_path_resistance(
        total, rec.get("path_limit_ohm", DEFAULT_PATH_LIMIT_OHM)
    )
    findings.extend(path["findings"])
    shared = rec.get("carries_signal_return", False)
    if not isinstance(shared, bool):
        raise ValueError(
            "carries_signal_return must be a boolean, got %r" % (shared,)
        )
    if shared:
        findings.append(
            "protective-earth-shared-with-signal-return: the safety path "
            "carries intended return current"
        )
    return {
        "unit_id": unit_id,
        "flight_category": comparison["flight_category"],
        "bench_category": comparison["bench_category"],
        "conductor_sizing": sizing,
        "path_resistance": path,
        "findings": findings,
        "mirrors_installation": not findings,
    }
