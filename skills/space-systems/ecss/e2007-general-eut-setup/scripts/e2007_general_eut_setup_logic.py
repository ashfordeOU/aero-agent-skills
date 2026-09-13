#!/usr/bin/env python3
"""Standard laboratory arrangement of a tested unit for ECSS-E-ST-20-07C
clause 5.2.6.1.

Paraphrased, implementable procedure (no verbatim standard text):

* An electromagnetic measurement is only reproducible if the tested unit,
  its interconnecting harness and every item of support equipment sit in
  the same geometry from one laboratory to the next. The arrangement is
  therefore fixed before the first measurement rather than adjusted while
  results are being taken.
* Every item on the bench is categorized before it is placed: the tested
  unit itself, support equipment that stimulates or monitors it, the
  interconnecting harness, and the coupling networks that feed it. An
  item whose role is not recognized has no defined place in the standard
  arrangement and is rejected.
* The tested unit sits on an insulating standoff of controlled height and
  low relative permittivity above a conductive reference plane, set back
  from the front edge of that plane by a fixed distance, and clear of the
  walls of the shielded enclosure by a stated minimum.
* The reference plane must cover the unit footprint plus a perimeter
  margin on every side; a plane smaller than that turns the plane edge
  into part of the measurement.
* The interconnecting harness runs with a fixed exposed length at a fixed
  height above the reference plane, and the exposed run can never be
  longer than the harness itself.
* Any geometric non-conformance holds the setup: the run does not start
  until the finding list is empty.

Stdlib only, offline, deterministic.
"""

import math

# Named tolerance absorbing binary representation error in millimetre and
# square-metre sums and differences. It is NOT an engineering allowance:
# the configuration limits themselves are never widened.
GEOM_EPS = 1e-9

TESTED_UNIT = "tested-unit"
SUPPORT_EQUIPMENT = "support-equipment"
INTERCONNECTING_HARNESS = "interconnecting-harness"
COUPLING_NETWORK = "coupling-network"

# Bench role -> arrangement category.
ROLE_CATEGORY = {
    "tested-unit": TESTED_UNIT,
    "stimulus-source": SUPPORT_EQUIPMENT,
    "load-simulator": SUPPORT_EQUIPMENT,
    "monitor-instrument": SUPPORT_EQUIPMENT,
    "interconnecting-harness": INTERCONNECTING_HARNESS,
    "coupling-network": COUPLING_NETWORK,
}

DEFAULT_SETUP_SPEC = {
    "standoff_height_mm": 50.0,
    "standoff_height_tolerance_mm": 5.0,
    "standoff_max_relative_permittivity": 1.4,
    "front_edge_setback_mm": 100.0,
    "front_edge_setback_tolerance_mm": 10.0,
    "min_enclosure_wall_clearance_mm": 1000.0,
    "min_item_separation_mm": 100.0,
    "ground_plane_perimeter_margin_mm": 100.0,
    "harness_exposed_length_mm": 2000.0,
    "harness_exposed_length_tolerance_mm": 50.0,
    "harness_routing_height_mm": 50.0,
    "harness_routing_height_tolerance_mm": 5.0,
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _not_above(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=GEOM_EPS)


def _at_least(value, floor_value):
    """True when value reaches floor_value, absorbing representation error."""
    return value >= floor_value or math.isclose(
        value, floor_value, rel_tol=0.0, abs_tol=GEOM_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard arrangement specification."""
    spec = dict(DEFAULT_SETUP_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_SETUP_SPEC:
            raise ValueError("unrecognized setup specification key %r" % (key,))
        spec[key] = _require_number(value, "spec %r" % key)
    return spec


def categorize_bench_item(item):
    """Map one bench item to its arrangement category."""
    if not isinstance(item, dict):
        raise ValueError("bench item must be a mapping, got %r" % (item,))
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("bench item needs a non-empty 'name', got %r" % (name,))
    role = item.get("role")
    if role not in ROLE_CATEGORY:
        raise ValueError(
            "bench item %r has unrecognized role %r (expected one of %s)"
            % (name, role, ", ".join(sorted(ROLE_CATEGORY)))
        )
    return ROLE_CATEGORY[role]


def categorize_bench(items):
    """Categorize an entire bench, rejecting a bench without a tested unit."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("bench items must be a non-empty sequence")
    categorized = []
    names = []
    for item in items:
        category = categorize_bench_item(item)
        categorized.append({"name": item["name"], "role": item["role"], "category": category})
        names.append(item["name"])
    if len(set(names)) != len(names):
        raise ValueError("bench item names must be unique, got %r" % (names,))
    units = [c for c in categorized if c["category"] == TESTED_UNIT]
    if len(units) != 1:
        raise ValueError(
            "the standard arrangement holds exactly one tested unit, found %d" % len(units)
        )
    return categorized


def check_dimension(label, measured_mm, nominal_mm, tolerance_mm):
    """Two-sided band check on a placement dimension."""
    if not isinstance(label, str) or not label.strip():
        raise ValueError("dimension label must be a non-empty string, got %r" % (label,))
    measured_mm = _require_number(measured_mm, "%s measured_mm" % label)
    nominal_mm = _require_number(nominal_mm, "%s nominal_mm" % label)
    tolerance_mm = _require_number(tolerance_mm, "%s tolerance_mm" % label)
    if tolerance_mm < 0.0:
        raise ValueError("%s tolerance_mm must not be negative, got %r" % (label, tolerance_mm))
    deviation = abs(measured_mm - nominal_mm)
    return {
        "label": label,
        "measured_mm": measured_mm,
        "nominal_mm": nominal_mm,
        "tolerance_mm": tolerance_mm,
        "deviation_mm": deviation,
        "compliant": _not_above(deviation, tolerance_mm),
    }


def check_minimum(label, measured_mm, minimum_mm):
    """One-sided floor check on a clearance or separation."""
    if not isinstance(label, str) or not label.strip():
        raise ValueError("clearance label must be a non-empty string, got %r" % (label,))
    measured_mm = _require_number(measured_mm, "%s measured_mm" % label)
    minimum_mm = _require_number(minimum_mm, "%s minimum_mm" % label)
    if minimum_mm < 0.0:
        raise ValueError("%s minimum_mm must not be negative, got %r" % (label, minimum_mm))
    return {
        "label": label,
        "measured_mm": measured_mm,
        "minimum_mm": minimum_mm,
        "shortfall_mm": max(0.0, minimum_mm - measured_mm),
        "compliant": _at_least(measured_mm, minimum_mm),
    }


def required_ground_plane_area_m2(length_mm, width_mm, perimeter_margin_mm):
    """Reference-plane area needed for a footprint plus a margin on all sides."""
    length_mm = _require_number(length_mm, "length_mm")
    width_mm = _require_number(width_mm, "width_mm")
    perimeter_margin_mm = _require_number(perimeter_margin_mm, "perimeter_margin_mm")
    if length_mm <= 0.0 or width_mm <= 0.0:
        raise ValueError(
            "footprint dimensions must be positive, got %r x %r" % (length_mm, width_mm)
        )
    if perimeter_margin_mm < 0.0:
        raise ValueError(
            "perimeter_margin_mm must not be negative, got %r" % (perimeter_margin_mm,)
        )
    return ((length_mm + 2.0 * perimeter_margin_mm) * (width_mm + 2.0 * perimeter_margin_mm)) / 1.0e6


def check_ground_plane(available_area_m2, required_area_m2):
    """Confirm the reference plane on the bench covers the required area."""
    available_area_m2 = _require_number(available_area_m2, "available_area_m2")
    required_area_m2 = _require_number(required_area_m2, "required_area_m2")
    if available_area_m2 <= 0.0:
        raise ValueError(
            "available_area_m2 must be positive, got %r" % (available_area_m2,)
        )
    if required_area_m2 <= 0.0:
        raise ValueError("required_area_m2 must be positive, got %r" % (required_area_m2,))
    return {
        "label": "reference-plane-area",
        "available_area_m2": available_area_m2,
        "required_area_m2": required_area_m2,
        "shortfall_m2": max(0.0, required_area_m2 - available_area_m2),
        "compliant": _at_least(available_area_m2, required_area_m2),
    }


def check_standoff(standoff, spec=None):
    """Check the insulating standoff height and its dielectric character."""
    spec = resolve_spec(spec)
    if not isinstance(standoff, dict):
        raise ValueError("standoff must be a mapping, got %r" % (standoff,))
    height = _require_number(standoff.get("height_mm"), "standoff height_mm")
    if height <= 0.0:
        raise ValueError("standoff height_mm must be positive, got %r" % (height,))
    permittivity = _require_number(
        standoff.get("relative_permittivity"), "standoff relative_permittivity"
    )
    if permittivity < 1.0:
        raise ValueError(
            "standoff relative_permittivity cannot be below unity, got %r" % (permittivity,)
        )
    height_check = check_dimension(
        "standoff-height",
        height,
        spec["standoff_height_mm"],
        spec["standoff_height_tolerance_mm"],
    )
    cap = spec["standoff_max_relative_permittivity"]
    return {
        "height": height_check,
        "relative_permittivity": permittivity,
        "permittivity_cap": cap,
        "low_permittivity": _not_above(permittivity, cap),
    }


def check_harness_routing(harness, spec=None):
    """Check exposed harness length and routing height above the plane."""
    spec = resolve_spec(spec)
    if not isinstance(harness, dict):
        raise ValueError("harness must be a mapping, got %r" % (harness,))
    total = _require_number(harness.get("total_length_mm"), "harness total_length_mm")
    exposed = _require_number(harness.get("exposed_length_mm"), "harness exposed_length_mm")
    height = _require_number(harness.get("routing_height_mm"), "harness routing_height_mm")
    if total <= 0.0:
        raise ValueError("harness total_length_mm must be positive, got %r" % (total,))
    if exposed <= 0.0:
        raise ValueError("harness exposed_length_mm must be positive, got %r" % (exposed,))
    if not _not_above(exposed, total):
        raise ValueError(
            "harness exposed_length_mm (%r) exceeds total_length_mm (%r)" % (exposed, total)
        )
    if height < 0.0:
        raise ValueError("harness routing_height_mm must not be negative, got %r" % (height,))
    return {
        "exposed_length": check_dimension(
            "harness-exposed-length",
            exposed,
            spec["harness_exposed_length_mm"],
            spec["harness_exposed_length_tolerance_mm"],
        ),
        "routing_height": check_dimension(
            "harness-routing-height",
            height,
            spec["harness_routing_height_mm"],
            spec["harness_routing_height_tolerance_mm"],
        ),
        "stowed_length_mm": total - exposed,
    }


def required_bench_length_mm(footprints_mm, separation_mm, perimeter_margin_mm):
    """Bench run needed to seat every item with the required separations."""
    if not isinstance(footprints_mm, (list, tuple)) or not footprints_mm:
        raise ValueError("footprints_mm must be a non-empty sequence")
    separation_mm = _require_number(separation_mm, "separation_mm")
    perimeter_margin_mm = _require_number(perimeter_margin_mm, "perimeter_margin_mm")
    if separation_mm < 0.0:
        raise ValueError("separation_mm must not be negative, got %r" % (separation_mm,))
    if perimeter_margin_mm < 0.0:
        raise ValueError(
            "perimeter_margin_mm must not be negative, got %r" % (perimeter_margin_mm,)
        )
    total = 0.0
    for i, value in enumerate(footprints_mm):
        value = _require_number(value, "footprints_mm[%d]" % i)
        if value <= 0.0:
            raise ValueError("footprints_mm[%d] must be positive, got %r" % (i, value))
        total += value
    total += separation_mm * (len(footprints_mm) - 1)
    total += 2.0 * perimeter_margin_mm
    return total


def setup_readiness(findings):
    """Gate token for the finding list of one arrangement."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "ready-for-measurement" if not findings else "hold-setup"


def evaluate_setup(config):
    """End-to-end clause 5.2.6.1 arrangement check for one bench."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    for key in ("items", "tested_unit_footprint_mm", "standoff", "harness"):
        if key not in config:
            raise ValueError("config missing required key %r" % (key,))
    spec = resolve_spec(config.get("spec"))
    bench = categorize_bench(config["items"])
    footprint = config["tested_unit_footprint_mm"]
    if not isinstance(footprint, (list, tuple)) or len(footprint) != 2:
        raise ValueError(
            "tested_unit_footprint_mm must be a (length, width) pair, got %r" % (footprint,)
        )
    required_area = required_ground_plane_area_m2(
        footprint[0], footprint[1], spec["ground_plane_perimeter_margin_mm"]
    )
    plane = check_ground_plane(
        _require_number(config.get("ground_plane_area_m2"), "ground_plane_area_m2"),
        required_area,
    )
    setback = check_dimension(
        "front-edge-setback",
        _require_number(config.get("front_edge_setback_mm"), "front_edge_setback_mm"),
        spec["front_edge_setback_mm"],
        spec["front_edge_setback_tolerance_mm"],
    )
    wall = check_minimum(
        "enclosure-wall-clearance",
        _require_number(config.get("enclosure_wall_clearance_mm"), "enclosure_wall_clearance_mm"),
        spec["min_enclosure_wall_clearance_mm"],
    )
    separation = check_minimum(
        "item-separation",
        _require_number(config.get("item_separation_mm"), "item_separation_mm"),
        spec["min_item_separation_mm"],
    )
    standoff = check_standoff(config["standoff"], config.get("spec"))
    harness = check_harness_routing(config["harness"], config.get("spec"))

    findings = []
    if not plane["compliant"]:
        findings.append("reference plane smaller than the footprint plus its perimeter margin")
    for check in (setback, standoff["height"], harness["exposed_length"], harness["routing_height"]):
        if not check["compliant"]:
            findings.append("%s outside the arrangement band" % check["label"])
    for check in (wall, separation):
        if not check["compliant"]:
            findings.append("%s below the arrangement minimum" % check["label"])
    if not standoff["low_permittivity"]:
        findings.append("standoff dielectric above the permitted relative permittivity")
    if not any(c["category"] == INTERCONNECTING_HARNESS for c in bench):
        findings.append("no interconnecting harness on the arrangement record")

    return {
        "bench": bench,
        "reference_plane": plane,
        "front_edge_setback": setback,
        "enclosure_wall_clearance": wall,
        "item_separation": separation,
        "standoff": standoff,
        "harness": harness,
        "required_plane_area_m2": required_area,
        "findings": findings,
        "status": setup_readiness(findings),
        "ready": not findings,
    }
