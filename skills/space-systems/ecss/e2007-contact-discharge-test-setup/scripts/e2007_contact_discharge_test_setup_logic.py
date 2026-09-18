#!/usr/bin/env python3
"""Contact discharge test setup, ECSS-E-ST-20-07C clause 5.4.14.3.

Paraphrased procedure, no verbatim standard text. The clause does not
build a bench from nothing: the direct contact discharge arrangement
starts from the standard unit configuration and is modified only where
putting the generator tip onto the unit itself, rather than onto a plane
beside it, demands something different. This module turns that into a
deterministic assessment:

  baseline bands + declared deltas -> the bands this bench is graded on
  realized generator + geometry    -> conforming / deviation / nonconforming
  discharge network + charge level -> peak current, decay, energy, charge
  declared points + surface finish -> contact capable or air only
  return cable length vs path      -> the slack that has to be dressed away

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Band edges and derived quantities are floats, so
# a value that exactly meets a bound can land a few units in the last
# place off it. These absorb representation error only; they never relax
# a band.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# A surface has to be conductive enough for the tip to make a real
# contact; above this the event is an air discharge whatever the
# operator intended.
CONTACT_SURFACE_RESISTANCE_MAX_OHM = 1.0

# Return cable slack beyond this is enough to couple back into the unit
# if it is left coiled next to it, so it is carried with the run.
SLACK_NOTICE_M = 0.5

GENERATOR_MODES = ("contact", "air")
TIP_TYPES = ("contact-tip", "rounded-air-tip")

SURFACE_FINISHES = (
    "anodized",
    "bare-conductive",
    "conductive-plating",
    "insulating-coating",
    "painted",
)
CONTACT_CAPABLE_FINISHES = ("bare-conductive", "conductive-plating")

SETUP_PARAMETERS = (
    "bond_resistance_ohm",
    "discharge_resistance_ohm",
    "generator_return_cable_length_m",
    "insulating_support_thickness_m",
    "return_cable_to_unit_separation_m",
    "storage_capacitance_f",
    "tip_approach_angle_deg",
)

CONFORMING = "conforming"
DECLARED_DEVIATION = "declared-deviation"
NONCONFORMING = "nonconforming"

CONTACT_POINT = "contact-point"
AIR_DISCHARGE_POINT = "air-discharge-point"
NOT_A_DISCHARGE_POINT = "not-a-discharge-point"

VERDICT_CONFORMING = "setup-conforming"
VERDICT_WITH_DEVIATIONS = "setup-conforming-with-deviations"
VERDICT_NONCONFORMING = "setup-nonconforming"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _word(record, key, where, recognized):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str):
        raise ValueError("%s: field %r must be a string, got %r" % (where, key, value))
    token = value.strip().lower()
    if token not in recognized:
        raise ValueError(
            "%s: unrecognized %s %r; recognized: %s"
            % (where, key, value, ", ".join(recognized))
        )
    return token


def _label(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty label" % (where, key))
    return value.strip()


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_band(band, name):
    """Validate one (minimum, maximum) acceptance band and return it."""
    if not isinstance(band, (tuple, list)) or len(band) != 2:
        raise ValueError("%s: band must be a (minimum, maximum) pair" % name)
    low = _scalar(band[0], "%s.minimum" % name)
    high = _scalar(band[1], "%s.maximum" % name)
    if high <= low:
        raise ValueError(
            "%s: band maximum (%g) must exceed its minimum (%g)" % (name, high, low)
        )
    return (low, high)


def apply_setup_deltas(baseline_bands, deltas):
    """Move the baseline bands by the deltas the contact setup declares.

    baseline_bands maps a setup parameter to a (minimum, maximum) pair.
    deltas maps a parameter to {"minimum_delta": x, "maximum_delta": y};
    either key may be omitted. An unknown parameter is refused, and so is
    a delta that collapses or inverts the band it is applied to.
    """
    if not isinstance(baseline_bands, dict) or not baseline_bands:
        raise ValueError("baseline_bands: must be a non-empty mapping")
    if deltas is None:
        deltas = {}
    if not isinstance(deltas, dict):
        raise ValueError("deltas: must be a mapping")

    resolved = {}
    for name, band in baseline_bands.items():
        if name not in SETUP_PARAMETERS:
            raise ValueError(
                "baseline_bands: unknown parameter %r; known: %s"
                % (name, ", ".join(SETUP_PARAMETERS))
            )
        resolved[name] = validate_band(band, name)

    for name, delta in deltas.items():
        if name not in resolved:
            raise ValueError(
                "deltas: %r is not a parameter of this bench; known: %s"
                % (name, ", ".join(sorted(resolved)))
            )
        if not isinstance(delta, dict):
            raise ValueError("deltas[%r]: must be a mapping" % name)
        for key in delta:
            if key not in ("minimum_delta", "maximum_delta"):
                raise ValueError(
                    "deltas[%r]: unknown key %r; use minimum_delta or maximum_delta"
                    % (name, key)
                )
        low, high = resolved[name]
        if "minimum_delta" in delta:
            low = low + _number(delta, "minimum_delta", "deltas[%r]" % name)
        if "maximum_delta" in delta:
            high = high + _number(delta, "maximum_delta", "deltas[%r]" % name)
        if high <= low:
            raise ValueError(
                "deltas[%r]: collapses the band to (%g, %g); a delta may move a "
                "band, not close it" % (name, low, high)
            )
        resolved[name] = (low, high)
    return resolved


def validate_discharge_point(point, index=0):
    """Validate one declared discharge point and return it normalized."""
    where = "discharge_points[%d]" % index
    if not isinstance(point, dict):
        raise ValueError("%s: record must be a mapping" % where)
    point_id = _label(point, "point_id", where)
    finish = _word(point, "surface_finish", where, SURFACE_FINISHES)
    resistance = _number(point, "surface_resistance_ohm", where)
    if resistance < 0.0:
        raise ValueError(
            "%s: surface_resistance_ohm must be >= 0, got %g" % (where, resistance)
        )
    accessible = point.get("accessible", True)
    if not isinstance(accessible, bool):
        raise ValueError("%s: accessible must be true or false" % where)
    intended = _word(point, "intended_application", where, GENERATOR_MODES)
    return {
        "point_id": point_id,
        "surface_finish": finish,
        "surface_resistance_ohm": resistance,
        "accessible": accessible,
        "intended_application": intended,
    }


def categorize_discharge_point(point, index=0):
    """Group a declared point as contact capable, air only, or unusable."""
    record = validate_discharge_point(point, index)
    if not record["accessible"]:
        return NOT_A_DISCHARGE_POINT
    if record["surface_finish"] in CONTACT_CAPABLE_FINISHES and at_most(
        record["surface_resistance_ohm"], CONTACT_SURFACE_RESISTANCE_MAX_OHM
    ):
        return CONTACT_POINT
    return AIR_DISCHARGE_POINT


def group_discharge_points(points):
    """Return {point_id: category} for every declared discharge point."""
    if isinstance(points, (str, bytes)) or not isinstance(points, (list, tuple)):
        raise ValueError("discharge_points: must be a sequence of point records")
    if not points:
        raise ValueError("discharge_points: at least one point must be declared")
    grouped = {}
    for index, point in enumerate(points):
        record = validate_discharge_point(point, index)
        if record["point_id"] in grouped:
            raise ValueError(
                "discharge_points: point_id %r appears twice" % record["point_id"]
            )
        grouped[record["point_id"]] = categorize_discharge_point(point, index)
    return grouped


def validate_bench(config):
    """Validate a realized contact discharge bench and return it normalized."""
    where = "bench"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)

    mode = _word(config, "generator_mode", where, GENERATOR_MODES)
    tip = _word(config, "tip_type", where, TIP_TYPES)

    positive = (
        "charge_voltage_v",
        "discharge_resistance_ohm",
        "generator_return_cable_length_m",
        "insulating_support_thickness_m",
        "return_cable_to_unit_separation_m",
        "return_path_length_m",
        "storage_capacitance_f",
        "tip_approach_angle_deg",
    )
    values = {}
    for key in positive:
        value = _number(config, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        values[key] = value

    if values["tip_approach_angle_deg"] > 180.0:
        raise ValueError(
            "%s: tip_approach_angle_deg must be <= 180, got %g"
            % (where, values["tip_approach_angle_deg"])
        )

    bond = _number(config, "bond_resistance_ohm", where)
    if bond < 0.0:
        raise ValueError("%s: bond_resistance_ohm must be >= 0, got %g" % (where, bond))
    values["bond_resistance_ohm"] = bond

    declared = config.get("declared_deviations", ())
    if isinstance(declared, str) or not isinstance(declared, (tuple, list, set)):
        raise ValueError(
            "%s: declared_deviations must be a sequence of parameter names" % where
        )
    names = set()
    for name in declared:
        if name not in SETUP_PARAMETERS:
            raise ValueError(
                "%s: declared deviation %r is not a graded parameter; graded: %s"
                % (where, name, ", ".join(SETUP_PARAMETERS))
            )
        names.add(name)

    points = config.get("discharge_points")
    values["point_categories"] = group_discharge_points(points)
    values["intended_contact_points"] = tuple(
        sorted(
            validate_discharge_point(p, i)["point_id"]
            for i, p in enumerate(points)
            if validate_discharge_point(p, i)["intended_application"] == "contact"
        )
    )
    values["generator_mode"] = mode
    values["tip_type"] = tip
    values["declared_deviations"] = frozenset(names)
    return values


def categorize_parameter(value, band, declared_deviation=False):
    """Grade one realized parameter against the band that governs it."""
    low, high = validate_band(band, "band")
    measured = _scalar(value, "value")
    if at_least(measured, low) and at_most(measured, high):
        return CONFORMING
    return DECLARED_DEVIATION if bool(declared_deviation) else NONCONFORMING


def band_margin(value, band):
    """Fractional distance from the nearer band edge, negative when outside."""
    low, high = validate_band(band, "band")
    measured = _scalar(value, "value")
    width = high - low
    return min(measured - low, high - measured) / width


def nominal_peak_current_a(charge_voltage_v, discharge_resistance_ohm):
    """First-peak current the discharge network delivers into a short."""
    volts = _scalar(charge_voltage_v, "charge_voltage_v")
    ohms = _scalar(discharge_resistance_ohm, "discharge_resistance_ohm")
    if volts <= 0.0:
        raise ValueError("charge_voltage_v must be > 0, got %g" % volts)
    if ohms <= 0.0:
        raise ValueError("discharge_resistance_ohm must be > 0, got %g" % ohms)
    return volts / ohms


def network_time_constant_s(discharge_resistance_ohm, storage_capacitance_f):
    """Decay constant of the generator network through its discharge resistor."""
    ohms = _scalar(discharge_resistance_ohm, "discharge_resistance_ohm")
    farads = _scalar(storage_capacitance_f, "storage_capacitance_f")
    if ohms <= 0.0:
        raise ValueError("discharge_resistance_ohm must be > 0, got %g" % ohms)
    if farads <= 0.0:
        raise ValueError("storage_capacitance_f must be > 0, got %g" % farads)
    return ohms * farads


def stored_energy_j(storage_capacitance_f, charge_voltage_v):
    """Energy held on the storage capacitor before the event."""
    farads = _scalar(storage_capacitance_f, "storage_capacitance_f")
    volts = _scalar(charge_voltage_v, "charge_voltage_v")
    if farads <= 0.0:
        raise ValueError("storage_capacitance_f must be > 0, got %g" % farads)
    if volts <= 0.0:
        raise ValueError("charge_voltage_v must be > 0, got %g" % volts)
    return 0.5 * farads * volts * volts


def delivered_charge_c(storage_capacitance_f, charge_voltage_v):
    """Charge the event moves out of the storage capacitor."""
    farads = _scalar(storage_capacitance_f, "storage_capacitance_f")
    volts = _scalar(charge_voltage_v, "charge_voltage_v")
    if farads <= 0.0:
        raise ValueError("storage_capacitance_f must be > 0, got %g" % farads)
    if volts <= 0.0:
        raise ValueError("charge_voltage_v must be > 0, got %g" % volts)
    return farads * volts


def return_cable_slack_m(cable_length_m, return_path_length_m):
    """Cable left over once the return path is spanned; negative is too short."""
    cable = _scalar(cable_length_m, "cable_length_m")
    path = _scalar(return_path_length_m, "return_path_length_m")
    if cable <= 0.0:
        raise ValueError("cable_length_m must be > 0, got %g" % cable)
    if path <= 0.0:
        raise ValueError("return_path_length_m must be > 0, got %g" % path)
    return cable - path


def governing_parameter(realized, bands):
    """The graded parameter sitting closest to, or furthest outside, its band."""
    if not isinstance(bands, dict) or not bands:
        raise ValueError("bands: must be a non-empty mapping")
    ranked = []
    for name in sorted(bands):
        if name not in realized:
            raise ValueError("realized: missing graded parameter %r" % name)
        ranked.append((band_margin(realized[name], bands[name]), name))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return ranked[0][1]


def assess_contact_discharge_setup(config, baseline_bands, deltas=None):
    """Full clause 5.4.14.3 assessment of a contact discharge bench."""
    bench = validate_bench(config)
    bands = apply_setup_deltas(baseline_bands, deltas)

    categories = {}
    findings = []
    for name in sorted(bands):
        category = categorize_parameter(
            bench[name], bands[name], name in bench["declared_deviations"]
        )
        categories[name] = category
        if category == NONCONFORMING:
            low, high = bands[name]
            findings.append(
                "%s is %g, outside its band %g to %g and not declared as a deviation"
                % (name, bench[name], low, high)
            )

    if bench["generator_mode"] == "contact" and bench["tip_type"] != "contact-tip":
        findings.append(
            "generator is set for contact application but carries the %s; the "
            "rounded tip cannot make the galvanic contact the mode needs"
            % bench["tip_type"]
        )

    misdeclared = [
        point_id
        for point_id in bench["intended_contact_points"]
        if bench["point_categories"][point_id] != CONTACT_POINT
    ]
    for point_id in misdeclared:
        findings.append(
            "point %s is listed for contact application but its surface grades as "
            "%s, so the event delivered there is not a contact discharge"
            % (point_id, bench["point_categories"][point_id])
        )

    contact_points = sorted(
        point_id
        for point_id, category in bench["point_categories"].items()
        if category == CONTACT_POINT
    )
    if not contact_points:
        findings.append(
            "no declared point grades as contact capable, so this bench has "
            "nothing for the contact mode to be applied to"
        )

    slack = return_cable_slack_m(
        bench["generator_return_cable_length_m"], bench["return_path_length_m"]
    )
    if slack < 0.0 and not math.isclose(slack, 0.0, rel_tol=0.0, abs_tol=ABS_TOL):
        findings.append(
            "return cable is %g m, shorter than the %g m return path, so the "
            "return is being completed through something that was not declared"
            % (bench["generator_return_cable_length_m"], bench["return_path_length_m"])
        )

    peak = nominal_peak_current_a(
        bench["charge_voltage_v"], bench["discharge_resistance_ohm"]
    )
    tau = network_time_constant_s(
        bench["discharge_resistance_ohm"], bench["storage_capacitance_f"]
    )
    energy = stored_energy_j(bench["storage_capacitance_f"], bench["charge_voltage_v"])
    charge = delivered_charge_c(
        bench["storage_capacitance_f"], bench["charge_voltage_v"]
    )

    limitations = []
    deviations = sorted(
        name for name, cat in categories.items() if cat == DECLARED_DEVIATION
    )
    for name in deviations:
        low, high = bands[name]
        limitations.append(
            "%s is %g, outside its band %g to %g but carried as a declared deviation"
            % (name, bench[name], low, high)
        )
    air_points = sorted(
        point_id
        for point_id, category in bench["point_categories"].items()
        if category == AIR_DISCHARGE_POINT
    )
    if air_points:
        limitations.append(
            "%d declared point(s) grade as air only (%s) and are not exposed by "
            "this contact run" % (len(air_points), ", ".join(air_points))
        )
    unusable = sorted(
        point_id
        for point_id, category in bench["point_categories"].items()
        if category == NOT_A_DISCHARGE_POINT
    )
    if unusable:
        limitations.append(
            "%d declared point(s) are not reachable with the unit as configured "
            "(%s)" % (len(unusable), ", ".join(unusable))
        )
    if slack > SLACK_NOTICE_M:
        limitations.append(
            "about %g m of return cable is left over and has to be dressed away "
            "from the unit rather than coiled beside it" % slack
        )

    if findings:
        verdict = VERDICT_NONCONFORMING
    elif deviations:
        verdict = VERDICT_WITH_DEVIATIONS
    else:
        verdict = VERDICT_CONFORMING

    return {
        "bench": bench,
        "bands": bands,
        "categories": categories,
        "point_categories": dict(bench["point_categories"]),
        "contact_points": contact_points,
        "air_discharge_points": air_points,
        "nominal_peak_current_a": peak,
        "network_time_constant_s": tau,
        "stored_energy_j": energy,
        "delivered_charge_c": charge,
        "return_cable_slack_m": slack,
        "governing_parameter": governing_parameter(bench, bands),
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
