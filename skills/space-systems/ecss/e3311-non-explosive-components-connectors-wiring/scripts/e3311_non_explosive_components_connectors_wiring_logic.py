"""Initiator connectors and firing-line wiring.

Anchor: ECSS-E-ST-33-11C clauses 4.10.1 to 4.10.2 -- the non-explosive
components of an initiation subsystem, specifically the connectors and the
wiring that carry firing energy to an initiator. Paraphrased into an
implementable procedure; no standard text is reproduced.

These clauses cover the parts of the initiation chain that hold no energetic
material and are therefore the parts a harness engineer designs. Two
obligations sit behind them.

The electrical one is a budget. The firing circuit has a source voltage and a
source resistance; between it and the bridgewire sit two conductors and a
number of connector contacts, each adding resistance. What arrives at the
bridgewire is a current, and that current has to exceed the all-fire current
with the margin the project set -- not the no-fire current, which is the
opposite bound and belongs to the safety case. The inverse a designer asks for
is the conductor cross-section, or the loop resistance, that delivers it.

The physical one is anti-mismating and segregation. A firing connector that
can mate with a non-firing one is a fault waiting for a night shift, and a
firing line routed with the rest of the harness picks up what the rest of the
harness carries. These are recorded as declared features, and a feature not
declared is treated as absent rather than assumed.
"""

import math

__all__ = [
    "ACCEPTED",
    "MARGIN_SHORT",
    "REJECTED",
    "COPPER_RESISTIVITY_OHM_M",
    "REQUIRED_FEATURES",
    "REL_TOL",
    "validate_positive",
    "validate_non_negative",
    "validate_contact_count",
    "conductor_resistance_ohm",
    "loop_resistance_ohm",
    "delivered_current_a",
    "voltage_drop_v",
    "all_fire_margin",
    "maximum_loop_resistance_ohm",
    "minimum_conductor_area_mm2",
    "missing_features",
    "assess_firing_line",
]

ACCEPTED = "accepted"
MARGIN_SHORT = "margin-short"
REJECTED = "rejected"

# Annealed copper at 20 degrees Celsius, ohm metre.
COPPER_RESISTIVITY_OHM_M = 1.724e-8

# Features the connector and wiring design has to declare. A feature that is
# not declared is absent: an initiation harness is not given the benefit of an
# assumption.
REQUIRED_FEATURES = (
    "keyed_against_mismating",
    "unique_to_firing_circuit",
    "twisted_pair",
    "shielded",
    "shield_bonded_both_ends",
    "segregated_from_other_harness",
    "contacts_rated_for_firing_current",
)

# Relative tolerance for comparisons against a bound, so a design sized to land
# exactly on its margin is graded the same way on every platform.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive value."""
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_non_negative(value, name="value"):
    """Return a value of zero or more."""
    number = _validate_number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_contact_count(value, name="contacts"):
    """Return a contact count of zero or more."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count" % name)
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def conductor_resistance_ohm(
    length_m, area_mm2, resistivity_ohm_m=COPPER_RESISTIVITY_OHM_M
):
    """Return the resistance of one conductor run."""
    length = validate_positive(length_m, "length_m")
    area = validate_positive(area_mm2, "area_mm2")
    resistivity = validate_positive(resistivity_ohm_m, "resistivity_ohm_m")
    return resistivity * length / (area * 1e-6)


def loop_resistance_ohm(
    length_m,
    area_mm2,
    contacts=2,
    contact_resistance_ohm=0.0,
    resistivity_ohm_m=COPPER_RESISTIVITY_OHM_M,
):
    """Return the round-trip resistance of a firing line.

    Both the outgoing and the return conductor are counted; a budget built on a
    single conductor run understates the loop by half.
    """
    per_conductor = conductor_resistance_ohm(length_m, area_mm2, resistivity_ohm_m)
    count = validate_contact_count(contacts)
    contact = validate_non_negative(contact_resistance_ohm, "contact_resistance_ohm")
    return 2.0 * per_conductor + count * contact


def delivered_current_a(
    source_voltage_v, source_resistance_ohm, loop_ohm, bridgewire_ohm
):
    """Return the current that reaches the bridgewire."""
    voltage = validate_positive(source_voltage_v, "source_voltage_v")
    source = validate_non_negative(source_resistance_ohm, "source_resistance_ohm")
    loop = validate_non_negative(loop_ohm, "loop_ohm")
    bridge = validate_positive(bridgewire_ohm, "bridgewire_ohm")
    return voltage / (source + loop + bridge)


def voltage_drop_v(current_a, resistance_ohm):
    """Return the voltage lost across a resistance at a current."""
    current = validate_non_negative(current_a, "current_a")
    resistance = validate_non_negative(resistance_ohm, "resistance_ohm")
    return current * resistance


def all_fire_margin(delivered_a, all_fire_a):
    """Return delivered current as a multiple of the all-fire current."""
    delivered = validate_non_negative(delivered_a, "delivered_a")
    all_fire = validate_positive(all_fire_a, "all_fire_a")
    return delivered / all_fire


def maximum_loop_resistance_ohm(
    source_voltage_v,
    source_resistance_ohm,
    bridgewire_ohm,
    all_fire_a,
    margin=1.5,
):
    """Return the largest loop resistance that still fires with margin.

    None means no loop resistance works: even a perfect zero-ohm harness does
    not deliver the required current, so the source or the initiator has to
    change rather than the wiring.
    """
    voltage = validate_positive(source_voltage_v, "source_voltage_v")
    source = validate_non_negative(source_resistance_ohm, "source_resistance_ohm")
    bridge = validate_positive(bridgewire_ohm, "bridgewire_ohm")
    all_fire = validate_positive(all_fire_a, "all_fire_a")
    factor = validate_positive(margin, "margin")
    target_current = factor * all_fire
    total_allowed = voltage / target_current
    allowed = total_allowed - source - bridge
    if allowed < 0.0:
        return None
    return allowed


def minimum_conductor_area_mm2(
    length_m,
    source_voltage_v,
    source_resistance_ohm,
    bridgewire_ohm,
    all_fire_a,
    margin=1.5,
    contacts=2,
    contact_resistance_ohm=0.0,
    resistivity_ohm_m=COPPER_RESISTIVITY_OHM_M,
):
    """Return the smallest conductor cross-section that fires with margin.

    None means the contacts alone already spend the resistance budget, or the
    source cannot deliver the current at any cross-section.
    """
    length = validate_positive(length_m, "length_m")
    resistivity = validate_positive(resistivity_ohm_m, "resistivity_ohm_m")
    count = validate_contact_count(contacts)
    contact = validate_non_negative(contact_resistance_ohm, "contact_resistance_ohm")
    allowed_loop = maximum_loop_resistance_ohm(
        source_voltage_v, source_resistance_ohm, bridgewire_ohm, all_fire_a, margin
    )
    if allowed_loop is None:
        return None
    allowed_conductors = allowed_loop - count * contact
    if allowed_conductors <= 0.0:
        return None
    return 2.0 * resistivity * length / (allowed_conductors * 1e-6)


def missing_features(declared):
    """Return the required connector and wiring features not declared true."""
    if not isinstance(declared, dict):
        raise ValueError("declared must be a mapping of feature names to booleans")
    missing = []
    for feature in REQUIRED_FEATURES:
        value = declared.get(feature, False)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean, got %r" % (feature, value))
        if not value:
            missing.append(feature)
    return missing


def assess_firing_line(
    length_m,
    area_mm2,
    source_voltage_v,
    source_resistance_ohm,
    bridgewire_ohm,
    all_fire_a,
    declared_features,
    margin=1.5,
    contacts=2,
    contact_resistance_ohm=0.0,
    resistivity_ohm_m=COPPER_RESISTIVITY_OHM_M,
):
    """Grade an initiator connector and firing-line wiring design."""
    factor = validate_positive(margin, "margin")
    loop = loop_resistance_ohm(
        length_m, area_mm2, contacts, contact_resistance_ohm, resistivity_ohm_m
    )
    delivered = delivered_current_a(
        source_voltage_v, source_resistance_ohm, loop, bridgewire_ohm
    )
    achieved = all_fire_margin(delivered, all_fire_a)
    absent = missing_features(declared_features)
    tolerance = REL_TOL * factor
    findings = []
    if achieved < 1.0 - REL_TOL:
        findings.append(
            "firing line delivers %.6g A against an all-fire current of %.6g A; "
            "the initiator is not reached at all"
            % (delivered, float(all_fire_a))
        )
    elif achieved < factor - tolerance:
        findings.append(
            "firing line delivers %.6g times the all-fire current against a "
            "required margin of %.6g" % (achieved, factor)
        )
    if achieved < factor - tolerance:
        allowed = maximum_loop_resistance_ohm(
            source_voltage_v, source_resistance_ohm, bridgewire_ohm, all_fire_a, factor
        )
        area_needed = minimum_conductor_area_mm2(
            length_m,
            source_voltage_v,
            source_resistance_ohm,
            bridgewire_ohm,
            all_fire_a,
            factor,
            contacts,
            contact_resistance_ohm,
            resistivity_ohm_m,
        )
        if allowed is None or area_needed is None:
            findings.append(
                "no conductor cross-section reaches the margin at this source "
                "and initiator; the firing circuit itself has to change"
            )
        else:
            findings.append(
                "a loop resistance of at most %.6g ohm, which is a conductor of "
                "at least %.6g mm2 over this run, reaches the margin"
                % (allowed, area_needed)
            )
    for feature in absent:
        findings.append(
            "connector and wiring design does not declare %s" % feature
        )
    if absent or achieved < 1.0 - REL_TOL:
        verdict = REJECTED
    elif achieved < factor - tolerance:
        verdict = MARGIN_SHORT
    else:
        verdict = ACCEPTED
    return {
        "loop_resistance_ohm": loop,
        "delivered_current_a": delivered,
        "all_fire_current_a": float(all_fire_a),
        "all_fire_margin": achieved,
        "required_margin": factor,
        "harness_voltage_drop_v": voltage_drop_v(delivered, loop),
        "maximum_loop_resistance_ohm": maximum_loop_resistance_ohm(
            source_voltage_v, source_resistance_ohm, bridgewire_ohm, all_fire_a, factor
        ),
        "minimum_conductor_area_mm2": minimum_conductor_area_mm2(
            length_m,
            source_voltage_v,
            source_resistance_ohm,
            bridgewire_ohm,
            all_fire_a,
            factor,
            contacts,
            contact_resistance_ohm,
            resistivity_ohm_m,
        ),
        "missing_features": absent,
        "verdict": verdict,
        "findings": findings,
    }
