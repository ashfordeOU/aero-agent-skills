#!/usr/bin/env python3
"""Bond strength of the positive and negative contacts of a protection
diode, pulled after the environmental block.

Anchor: ECSS-E-ST-20-08C clause 9.6.11. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause puts mechanical loading on top of environmental loading, and
the order carries the whole meaning. A contact pulled straight off the
line reports the as-built joint. The array flies the joint that thermal
cycling and a humidity soak have already worked on, and only that second
number belongs in a qualification record. So the environmental block is
checked before any force is read, and a lot that was pulled early is
reported as pulled early rather than averaged in with the rest.

Two contacts are assessed, not one. The positive and the negative
contact of a protection diode are laid down by different steps, carry
different bonded areas and release at different loads. The device is
sentenced by whichever lets go first.

A recorded force is not yet a bond strength, for two reasons. The
machine pulls along its own axis, and a grip set a few degrees off the
contact normal puts only the cosine component into the joint while the
rest becomes shear the test was not asking about; and a wide contact
takes more force than a narrow one of identical quality. Resolving onto
the normal and dividing by the bonded area turns the reading into a
number that compares.

Finally, a lot is sentenced from a sample, and a sample too thin to
represent the lot is a sampling finding rather than a bond finding.

The limits below are declared project values, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PULL_POLICY_SITES = ("positive-contact", "negative-contact")

ENVIRONMENTAL_BLOCK_INCOMPLETE = "environmental-block-incomplete"
PULL_DRAGGED_OFF_NORMAL = "pull-dragged-off-normal"
PULL_SAMPLE_NOT_REPRESENTATIVE = "pull-sample-not-representative"
CONTACT_SITES_MISSING = "contact-sites-missing"
BOND_STRENGTH_BELOW_MINIMUM = "bond-strength-below-minimum"
BOND_STRENGTH_DEMONSTRATED = "bond-strength-demonstrated"

DEFAULT_PULL_POLICY = {
    "min_bond_strength_mpa": 4.0,
    "max_off_normal_angle_deg": 15.0,
    "required_thermal_cycles": 10,
    "required_humidity_soak_hours": 24.0,
    "min_sample_fraction": 0.10,
    "required_contacts": PULL_POLICY_SITES,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % name)
    return text


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _contact_tuple(name, value):
    if isinstance(value, str) or not isinstance(value, (list, tuple, set)):
        raise ValueError(
            "%s must be a sequence of contact names, got %r" % (name, value)
        )
    names = tuple(_require_label("%s entry" % name, entry) for entry in value)
    if not names:
        raise ValueError("%s must name at least one contact" % name)
    if len(set(names)) != len(names):
        raise ValueError("%s repeats a contact name: %r" % (name, names))
    return names


def validate_pull_policy(policy):
    """Check the pull policy is complete and internally sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_bond_strength_mpa", policy.get("min_bond_strength_mpa"))
    angle = _require_positive(
        "max_off_normal_angle_deg", policy.get("max_off_normal_angle_deg")
    )
    if angle >= 90.0:
        raise ValueError(
            "max_off_normal_angle_deg %g admits a pull at or past the contact "
            "plane, which puts no load into the joint at all" % angle
        )
    _require_count("required_thermal_cycles", policy.get("required_thermal_cycles"))
    _require_non_negative(
        "required_humidity_soak_hours", policy.get("required_humidity_soak_hours")
    )
    fraction = _require_number(
        "min_sample_fraction", policy.get("min_sample_fraction")
    )
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError(
            "min_sample_fraction %g must sit above zero and at most one"
            % fraction
        )
    _contact_tuple("required_contacts", policy.get("required_contacts"))
    return policy


def validate_environmental_record(record):
    """Read the conditioning a lot went through before anything was pulled."""
    if not isinstance(record, dict):
        raise ValueError("environmental record must be a mapping, got %r" % (record,))
    cycles = _require_count(
        "thermal_cycles_completed", record.get("thermal_cycles_completed")
    )
    hours = _require_non_negative(
        "humidity_soak_hours", record.get("humidity_soak_hours")
    )
    return cycles, hours


def environmental_block_shortfalls(record, policy=DEFAULT_PULL_POLICY):
    """Which parts of the conditioning the lot still owes, as plain notes."""
    validate_pull_policy(policy)
    cycles, hours = validate_environmental_record(record)
    notes = []
    if cycles < int(policy["required_thermal_cycles"]):
        notes.append(
            "the lot completed %d thermal cycles against the %d it owes, so the "
            "pull describes a joint the mission profile has not yet worked on"
            % (cycles, int(policy["required_thermal_cycles"]))
        )
    if not _at_least(hours, float(policy["required_humidity_soak_hours"])):
        notes.append(
            "the humidity soak ran %g h against the %g h it owes, so moisture "
            "had not reached the interface the pull is about to load"
            % (hours, float(policy["required_humidity_soak_hours"]))
        )
    return notes


def environmental_block_complete(record, policy=DEFAULT_PULL_POLICY):
    """True when the conditioning owed before the pull was finished."""
    return not environmental_block_shortfalls(record, policy)


def normal_force_n(pull_force_n, off_normal_angle_deg):
    """The component of a recorded pull that acted along the contact normal."""
    force = _require_positive("pull_force_n", pull_force_n)
    angle = _require_non_negative("off_normal_angle_deg", off_normal_angle_deg)
    if angle >= 90.0:
        raise ValueError(
            "a pull %g deg off the contact normal lies in the contact plane and "
            "loads the joint in shear, not in tension" % angle
        )
    return force * math.cos(math.radians(angle))


def off_normal_within_allowance(off_normal_angle_deg, policy=DEFAULT_PULL_POLICY):
    """True when the grip sat close enough to the contact normal to be read."""
    validate_pull_policy(policy)
    angle = _require_non_negative("off_normal_angle_deg", off_normal_angle_deg)
    return _at_most(angle, float(policy["max_off_normal_angle_deg"]))


def bond_strength_mpa(normal_force_value_n, bonded_area_mm2):
    """Normal force spread over the bonded area it was carried by."""
    force = _require_positive("normal_force_value_n", normal_force_value_n)
    area = _require_positive("bonded_area_mm2", bonded_area_mm2)
    return force / area


def contact_bond_strength_mpa(pull_force_n, off_normal_angle_deg, bonded_area_mm2):
    """A raw machine reading turned into a comparable bond strength."""
    return bond_strength_mpa(
        normal_force_n(pull_force_n, off_normal_angle_deg), bonded_area_mm2
    )


def bond_strength_sufficient(strength_mpa, policy=DEFAULT_PULL_POLICY):
    """True when a bond strength reaches the declared minimum."""
    validate_pull_policy(policy)
    strength = _require_positive("strength_mpa", strength_mpa)
    return _at_least(strength, float(policy["min_bond_strength_mpa"]))


def validate_contact_pull(contact):
    """Read one contact pull: which contact, what force, what angle, what area."""
    if not isinstance(contact, dict):
        raise ValueError("contact must be a mapping, got %r" % (contact,))
    name = _require_label("contact name", contact.get("contact"))
    force = _require_positive("pull_force_n on %s" % name, contact.get("pull_force_n"))
    angle = _require_non_negative(
        "off_normal_angle_deg on %s" % name, contact.get("off_normal_angle_deg")
    )
    area = _require_positive(
        "bonded_area_mm2 on %s" % name, contact.get("bonded_area_mm2")
    )
    return name, force, angle, area


def missing_contacts(presented, policy=DEFAULT_PULL_POLICY):
    """Required contacts the device record does not carry, in policy order."""
    validate_pull_policy(policy)
    seen = set(_contact_tuple("presented", presented))
    return tuple(
        name for name in policy["required_contacts"] if name not in seen
    )


def weaker_contact(contact_records):
    """The contact that releases first, which sentences the device."""
    if not isinstance(contact_records, (list, tuple)) or not contact_records:
        raise ValueError("at least one contact record is needed to sentence a device")
    return min(contact_records, key=lambda entry: entry["bond_strength_mpa"])


def sample_fraction(pulled_count, lot_size):
    """Share of the lot that was actually put on the machine."""
    pulled = _require_count("pulled_count", pulled_count)
    lot = _require_count("lot_size", lot_size)
    if lot == 0:
        raise ValueError("a lot of zero devices cannot be sampled")
    if pulled > lot:
        raise ValueError(
            "%d devices were pulled from a lot of %d, so the lot size or the "
            "sample is misrecorded" % (pulled, lot)
        )
    return float(pulled) / float(lot)


def sample_representative(pulled_count, lot_size, policy=DEFAULT_PULL_POLICY):
    """True when the pulled sample reaches the share the policy asks of the lot."""
    validate_pull_policy(policy)
    fraction = sample_fraction(pulled_count, lot_size)
    return _at_least(fraction, float(policy["min_sample_fraction"]))


def assess_protection_diode_pull(case, policy=DEFAULT_PULL_POLICY):
    """Full clause 9.6.11 pull assessment over one presented diode sample."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_pull_policy(policy)

    findings = []
    device_records = []
    result = {
        "thermal_cycles_completed": None,
        "humidity_soak_hours": None,
        "sample_fraction": None,
        "device_records": device_records,
        "weakest_bond_strength_mpa": None,
        "mean_bond_strength_mpa": None,
        "missing_contacts": (),
        "findings": findings,
    }

    environmental = case.get("environmental")
    if environmental is None:
        raise ValueError("case is missing an environmental record")
    cycles, hours = validate_environmental_record(environmental)
    result["thermal_cycles_completed"] = cycles
    result["humidity_soak_hours"] = hours

    shortfalls = environmental_block_shortfalls(environmental, policy)
    if shortfalls:
        findings.extend(shortfalls)
        result["verdict"] = ENVIRONMENTAL_BLOCK_INCOMPLETE
        return result

    devices = case.get("devices")
    if not isinstance(devices, (list, tuple)):
        raise ValueError("case is missing a devices record")
    if not devices:
        raise ValueError("no diode was pulled, so there is nothing to assess")

    lot_size = _require_count("lot_size", case.get("lot_size"))
    result["sample_fraction"] = sample_fraction(len(devices), lot_size)

    seen_devices = set()
    off_normal = []
    absent = []
    weak = []
    for device in devices:
        if not isinstance(device, dict):
            raise ValueError("device must be a mapping, got %r" % (device,))
        identifier = _require_label("device id", device.get("id"))
        if identifier in seen_devices:
            raise ValueError("duplicate device id %r in the record" % identifier)
        seen_devices.add(identifier)

        contacts = device.get("contacts")
        if not isinstance(contacts, (list, tuple)) or not contacts:
            raise ValueError("device %s presents no contact pull" % identifier)

        contact_records = []
        names = []
        for contact in contacts:
            name, force, angle, area = validate_contact_pull(contact)
            if name in names:
                raise ValueError("device %s repeats the contact %r" % (identifier, name))
            names.append(name)
            if not off_normal_within_allowance(angle, policy):
                off_normal.append("%s/%s at %g deg" % (identifier, name, angle))
            contact_records.append(
                {
                    "contact": name,
                    "pull_force_n": force,
                    "off_normal_angle_deg": angle,
                    "normal_force_n": normal_force_n(force, angle),
                    "bonded_area_mm2": area,
                    "bond_strength_mpa": contact_bond_strength_mpa(force, angle, area),
                }
            )

        gap = missing_contacts(names, policy)
        if gap:
            absent.extend("%s/%s" % (identifier, name) for name in gap)

        weakest = weaker_contact(contact_records)
        sufficient = bond_strength_sufficient(weakest["bond_strength_mpa"], policy)
        if not sufficient:
            weak.append((identifier, weakest))
        device_records.append(
            {
                "id": identifier,
                "contacts": contact_records,
                "weaker_contact": weakest["contact"],
                "bond_strength_mpa": weakest["bond_strength_mpa"],
                "sufficient": sufficient,
            }
        )

    strengths = [entry["bond_strength_mpa"] for entry in device_records]
    result["weakest_bond_strength_mpa"] = min(strengths)
    result["mean_bond_strength_mpa"] = sum(strengths) / len(strengths)

    if off_normal:
        findings.append(
            "%d pull(s) were dragged past the off-normal allowance (%s), so the "
            "force that reached the joint is not the force the machine reported"
            % (len(off_normal), ", ".join(off_normal))
        )
        result["verdict"] = PULL_DRAGGED_OFF_NORMAL
        return result

    if absent:
        result["missing_contacts"] = tuple(absent)
        findings.append(
            "%d required contact(s) were never pulled (%s), so those joints carry "
            "no strength evidence" % (len(absent), ", ".join(absent))
        )
        result["verdict"] = CONTACT_SITES_MISSING
        return result

    if not sample_representative(len(devices), lot_size, policy):
        findings.append(
            "%d device(s) were pulled from a lot of %d, %.1f per cent, below the "
            "share the policy asks before a lot may be sentenced"
            % (len(devices), lot_size, result["sample_fraction"] * 100.0)
        )
        result["verdict"] = PULL_SAMPLE_NOT_REPRESENTATIVE
        return result

    if weak:
        for identifier, weakest in weak:
            findings.append(
                "device %s releases at %.3g MPa on its %s, below the declared "
                "minimum, and the device is sentenced by that contact"
                % (identifier, weakest["bond_strength_mpa"], weakest["contact"])
            )
        result["verdict"] = BOND_STRENGTH_BELOW_MINIMUM
        return result

    result["verdict"] = BOND_STRENGTH_DEMONSTRATED
    return result
