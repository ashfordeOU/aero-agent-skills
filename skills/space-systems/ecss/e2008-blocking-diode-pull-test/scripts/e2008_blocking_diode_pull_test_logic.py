#!/usr/bin/env python3
"""Interconnector adherence on blocking diode contacts, assessed by pulling.

Anchor: ECSS-E-ST-20-08C clause 12.6.16. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The interconnector is the ribbon that carries the string current off the
blocking diode, and it is welded or soldered onto the diode's
metallised contact. The pull test takes hold of that ribbon and pulls
until something lets go. What the test is trying to learn is how strong
the bond is -- and the single most common way to get that wrong is to
pull until the ribbon itself breaks and then write the breaking force
down as the bond strength.

So a pull record is only a bond measurement when the bond is what
released. Four things can give way:

    the bond interface   the ribbon comes off the contact; this is the
                         measurement the clause wants
    the ribbon           the ribbon fractures away from the joint; the
                         bond never failed, so its strength is only
                         known to be at least the force reached
    the metallisation    the metallisation lifts off the die with the
                         ribbon still attached to it; the contact
                         finish failed, not the weld
    the die              the semiconductor itself fractures; the part
                         is gone and the pull proved nothing about the
                         joint

The ribbon case is not a failure of the test, it is a censored reading.
If the ribbon broke at or above the force the bond was required to
reach, the bond is proven to be at least that strong and the device
passes on a lower bound. If it broke below that force, nothing is
proven and the pull has to be repeated on a device whose ribbon can
carry the required load.

The ribbon's own capacity is computable: its cross-section times the
tensile strength of the material it is made of. Comparing the force
reached against that capacity gives a utilisation, and a pull that ran
past most of the ribbon's capacity was always going to end in the
ribbon whatever the bond was worth.

The pull direction matters too. A grip dragged off the contact normal
puts only the cosine of its angle into the joint along the axis the
requirement is written for, and the rest goes into peeling it. Past a
declared angle the reading is not comparable with the requirement at
all and the record is refused.

Force alone does not compare across contact sizes, so the normal force
is also divided by the bonded area that carried it, which is the stress
the joint actually saw.

Both polarities carry a ribbon, so a device sentenced from one contact
is sentenced from half the evidence.

The policy below is a declared project policy, not a physical constant;
a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REVIEW = "review"
REJECT = "reject"
PULL_DISPOSITIONS = (ACCEPT, REVIEW, REJECT)

PULL_INCOMPLETE = "pull-incomplete"

BOND_INTERFACE = "bond-interface"
RIBBON_FRACTURE = "ribbon-fracture"
METALLIZATION_LIFT = "metallization-lift"
DIE_FRACTURE = "die-fracture"
FAILURE_MODES = (
    BOND_INTERFACE,
    RIBBON_FRACTURE,
    METALLIZATION_LIFT,
    DIE_FRACTURE,
)

ANODE = "anode"
CATHODE = "cathode"
REQUIRED_POLARITIES = (ANODE, CATHODE)

_SEVERITY_ORDER = {ACCEPT: 0, REVIEW: 1, REJECT: 2}

DEFAULT_PULL_POLICY = {
    "min_pull_force_n": 4.0,
    "min_bond_stress_mpa": 8.0,
    "max_pull_angle_deg": 15.0,
    "ribbon_utilisation_ceiling": 0.80,
    "review_margin_factor": 1.25,
    "min_sample_fraction": 0.10,
    "max_failing_device_fraction": 0.05,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A normal force carries a cosine, a bond stress is a quotient of two
    measured quantities and a utilisation is a quotient of a force
    against a product of three, so a value that should land exactly on
    its limit can evaluate a few units in the last place past it -- and
    the cosine is not correctly rounded, so it lands differently on
    different machines. The limit is never moved; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit under the same representation tolerance."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_pull_policy(policy):
    """Check a pull policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("policy min_pull_force_n", policy.get("min_pull_force_n"))
    _require_positive("policy min_bond_stress_mpa", policy.get("min_bond_stress_mpa"))
    angle = _require_number(
        "policy max_pull_angle_deg", policy.get("max_pull_angle_deg")
    )
    if angle < 0.0 or angle >= 90.0:
        raise ValueError(
            "policy max_pull_angle_deg must sit between zero and ninety degrees; "
            "at ninety the pull puts nothing into the joint along the axis the "
            "requirement is written for, got %r" % (angle,)
        )
    ceiling = _require_fraction(
        "policy ribbon_utilisation_ceiling",
        policy.get("ribbon_utilisation_ceiling"),
    )
    if ceiling <= 0.0:
        raise ValueError(
            "policy ribbon_utilisation_ceiling must be above zero; a ceiling of "
            "zero calls every pull a ribbon-limited one"
        )
    factor = policy.get("review_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "policy review_margin_factor must be at least one, got %r" % (factor,)
        )
    sample = _require_fraction(
        "policy min_sample_fraction", policy.get("min_sample_fraction")
    )
    if sample <= 0.0:
        raise ValueError(
            "policy min_sample_fraction must be above zero; a lot cannot be "
            "sentenced from no devices at all"
        )
    _require_fraction(
        "policy max_failing_device_fraction",
        policy.get("max_failing_device_fraction"),
    )
    return policy


def interconnector_capacity_n(interconnector):
    """The force the ribbon itself can carry before it fractures.

    Its cross-section in square millimetres times the tensile strength
    of its material in megapascals, which is newtons.
    """
    if not isinstance(interconnector, dict):
        raise ValueError(
            "interconnector must be a mapping, got %r" % (interconnector,)
        )
    width = _require_positive("width_mm", interconnector.get("width_mm"))
    thickness = _require_positive(
        "thickness_mm", interconnector.get("thickness_mm")
    )
    strength = _require_positive(
        "tensile_strength_mpa", interconnector.get("tensile_strength_mpa")
    )
    return width * thickness * strength


def resolve_normal_force(force_n, angle_deg):
    """The part of a pull that acts along the contact normal.

    A grip dragged off the normal puts only the cosine of its angle into
    the joint along the axis the requirement is written for; the rest
    peels it instead.
    """
    force = _require_non_negative("force_n", force_n)
    angle = _require_number("angle_deg", angle_deg)
    if angle < 0.0 or angle >= 90.0:
        raise ValueError(
            "angle_deg must sit between zero and ninety degrees, got %r" % (angle,)
        )
    return force * math.cos(math.radians(angle))


def bond_stress_mpa(normal_force_n, bonded_area_mm2):
    """The stress the joint saw: normal force over the area that carried it."""
    force = _require_non_negative("normal_force_n", normal_force_n)
    area = _require_positive("bonded_area_mm2", bonded_area_mm2)
    return force / area


def assess_contact_pull(contact, policy=DEFAULT_PULL_POLICY):
    """Grade one pulled interconnector on a blocking diode contact."""
    validate_pull_policy(policy)
    if not isinstance(contact, dict):
        raise ValueError("contact must be a mapping, got %r" % (contact,))
    polarity = contact.get("polarity")
    if polarity not in REQUIRED_POLARITIES:
        raise ValueError(
            "contact polarity must be one of %s, got %r"
            % (", ".join(REQUIRED_POLARITIES), polarity)
        )
    mode = contact.get("failure_mode")
    if mode not in FAILURE_MODES:
        raise ValueError(
            "failure_mode on the %s contact must be one of %s, got %r"
            % (polarity, ", ".join(FAILURE_MODES), mode)
        )
    force = _require_non_negative(
        "pull_force_n on the %s contact" % polarity, contact.get("pull_force_n")
    )
    angle = _require_number(
        "pull_angle_deg on the %s contact" % polarity, contact.get("pull_angle_deg")
    )
    area = _require_positive(
        "bonded_area_mm2 on the %s contact" % polarity,
        contact.get("bonded_area_mm2"),
    )
    capacity = interconnector_capacity_n(contact.get("interconnector"))

    findings = []
    dispositions = [ACCEPT]
    factor = policy["review_margin_factor"]

    off_normal = not _at_most(abs(angle), policy["max_pull_angle_deg"])
    if off_normal:
        findings.append(
            "the %s contact was pulled %.2f degrees off the contact normal, past "
            "the %.2f the policy allows; the reading is not comparable with a "
            "requirement written along the normal"
            % (polarity, abs(angle), policy["max_pull_angle_deg"])
        )
        return {
            "polarity": polarity,
            "verdict": PULL_INCOMPLETE,
            "measured": False,
            "bond_measured": False,
            "failure_mode": mode,
            "pull_force_n": force,
            "pull_angle_deg": angle,
            "normal_force_n": 0.0,
            "bond_stress_mpa": 0.0,
            "interconnector_capacity_n": capacity,
            "ribbon_utilisation": 0.0,
            "findings": findings,
        }

    normal = resolve_normal_force(force, angle)
    stress = bond_stress_mpa(normal, area)
    utilisation = force / capacity
    ribbon_limited = not _at_most(utilisation, policy["ribbon_utilisation_ceiling"])
    reached_requirement = _at_least(
        normal, policy["min_pull_force_n"]
    ) and _at_least(stress, policy["min_bond_stress_mpa"])

    bond_measured = mode == BOND_INTERFACE
    measured = True

    if mode == DIE_FRACTURE:
        dispositions.append(REJECT)
        findings.append(
            "the %s contact pull fractured the die at %.3f N; the part is gone "
            "and the joint was never tested" % (polarity, force)
        )
    elif mode == METALLIZATION_LIFT:
        dispositions.append(REJECT)
        findings.append(
            "the %s contact lifted its metallisation off the die at %.3f N with "
            "the ribbon still attached; the contact finish gave way, not the weld"
            % (polarity, force)
        )
    elif mode == RIBBON_FRACTURE:
        if reached_requirement:
            findings.append(
                "the %s contact pull broke the ribbon at %.3f N before the bond "
                "released; the bond is proven to be at least that strong, which "
                "already clears the requirement" % (polarity, force)
            )
        else:
            measured = False
            findings.append(
                "the %s contact pull broke the ribbon at %.3f N, short of the "
                "%.3f N the bond owes; nothing is proven and the pull has to be "
                "repeated on a device whose ribbon can carry the load"
                % (polarity, force, policy["min_pull_force_n"])
            )
    else:
        if not _at_least(normal, policy["min_pull_force_n"]):
            review_floor = policy["min_pull_force_n"] / factor
            if _at_least(normal, review_floor):
                dispositions.append(REVIEW)
                findings.append(
                    "the %s contact bond released at %.3f N along the normal, "
                    "short of the %.3f N the policy asks for"
                    % (polarity, normal, policy["min_pull_force_n"])
                )
            else:
                dispositions.append(REJECT)
                findings.append(
                    "the %s contact bond released at %.3f N along the normal, "
                    "under the %.3f N review floor" % (polarity, normal, review_floor)
                )
        if not _at_least(stress, policy["min_bond_stress_mpa"]):
            review_floor = policy["min_bond_stress_mpa"] / factor
            if _at_least(stress, review_floor):
                dispositions.append(REVIEW)
                findings.append(
                    "the %s contact carried %.3f MPa across its bonded area, "
                    "short of the %.3f MPa the policy asks for"
                    % (polarity, stress, policy["min_bond_stress_mpa"])
                )
            else:
                dispositions.append(REJECT)
                findings.append(
                    "the %s contact carried %.3f MPa across its bonded area, "
                    "under the %.3f MPa review floor" % (polarity, stress, review_floor)
                )

    if ribbon_limited and mode == BOND_INTERFACE:
        findings.append(
            "the %s contact pull reached %.3f of the ribbon's own capacity before "
            "the bond released; a pull run this close to the ribbon is measuring "
            "the two together" % (polarity, utilisation)
        )

    verdict = _worst(dispositions) if measured else PULL_INCOMPLETE
    return {
        "polarity": polarity,
        "verdict": verdict,
        "measured": measured,
        "bond_measured": bond_measured,
        "failure_mode": mode,
        "pull_force_n": force,
        "pull_angle_deg": angle,
        "normal_force_n": normal,
        "bond_stress_mpa": stress,
        "interconnector_capacity_n": capacity,
        "ribbon_utilisation": utilisation,
        "findings": findings,
    }


def assess_blocking_diode_pull(device, policy=DEFAULT_PULL_POLICY):
    """Sentence one blocking diode from the pulls on both its contacts."""
    validate_pull_policy(policy)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    device_id = _require_text("device_id", device.get("device_id"))
    contacts = device.get("contacts")
    if not isinstance(contacts, (list, tuple)) or not contacts:
        raise ValueError(
            "%s must carry at least one pulled contact, got %r"
            % (device_id, contacts)
        )
    graded = []
    seen = set()
    for contact in contacts:
        result = assess_contact_pull(contact, policy)
        if result["polarity"] in seen:
            raise ValueError(
                "%s carries two pull records for its %s contact"
                % (device_id, result["polarity"])
            )
        seen.add(result["polarity"])
        graded.append(result)

    missing = [p for p in REQUIRED_POLARITIES if p not in seen]
    findings = []
    dispositions = [ACCEPT]
    for result in graded:
        if result["measured"]:
            dispositions.append(result["verdict"])
        for finding in result["findings"]:
            findings.append("%s %s" % (device_id, finding))
    if missing:
        findings.append(
            "%s carries no pull on its %s contact; both contacts carry a ribbon, "
            "so the device is sentenced from half the evidence"
            % (device_id, " and ".join(missing))
        )

    unmeasured = [r["polarity"] for r in graded if not r["measured"]]
    complete = not missing and not unmeasured
    verdict = _worst(dispositions) if complete else PULL_INCOMPLETE
    measured_forces = [r["normal_force_n"] for r in graded if r["measured"]]
    return {
        "device_id": device_id,
        "verdict": verdict,
        "complete": complete,
        "pulled_polarities": sorted(seen),
        "missing_polarities": missing,
        "unmeasured_polarities": unmeasured,
        "weakest_normal_force_n": min(measured_forces) if measured_forces else 0.0,
        "bond_measured_count": len([r for r in graded if r["bond_measured"]]),
        "contacts": graded,
        "findings": findings,
    }


def screen_blocking_diode_pull(lot, policy=DEFAULT_PULL_POLICY):
    """Clause 12.6.16 interconnector adherence screen over one lot."""
    validate_pull_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))
    population = _require_count("lot_population", lot.get("lot_population"))
    records = lot.get("devices")
    if not isinstance(records, (list, tuple)):
        raise ValueError("devices must be a list, got %r" % (records,))
    if len(records) > population:
        raise ValueError(
            "%d pulled devices against a lot population of %d on lot %s"
            % (len(records), population, lot_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_blocking_diode_pull(record, policy)
        if result["device_id"] in seen:
            raise ValueError(
                "duplicate device id %r on lot %s" % (result["device_id"], lot_id)
            )
        seen.add(result["device_id"])
        screened.append(result)

    pulled = len(screened)
    counts = dict((state, 0) for state in PULL_DISPOSITIONS)
    counts[PULL_INCOMPLETE] = 0
    findings = []
    dispositions = [ACCEPT]
    failing = 0
    open_devices = []
    weakest = None
    for result in screened:
        counts[result["verdict"]] += 1
        if result["complete"]:
            dispositions.append(result["verdict"])
            if result["verdict"] != ACCEPT:
                failing += 1
        else:
            open_devices.append(result["device_id"])
        if result["complete"]:
            weakest = (
                result["weakest_normal_force_n"]
                if weakest is None
                else min(weakest, result["weakest_normal_force_n"])
            )
        for finding in result["findings"]:
            findings.append(finding)

    share = pulled / float(population)
    if not _at_least(share, policy["min_sample_fraction"]):
        dispositions.append(REVIEW)
        findings.append(
            "%d of %d devices were pulled, a share of %.3f against the %.3f the "
            "policy asks for; a lot cannot be sentenced from a sample too thin "
            "to represent it" % (pulled, population, share, policy["min_sample_fraction"])
        )

    allowed = policy["max_failing_device_fraction"] * pulled
    if pulled and not _at_most(failing, allowed):
        dispositions.append(REJECT)
        findings.append(
            "%d of %d pulled devices did not clear the adherence requirement, "
            "past the %.2f the lot allowance permits" % (failing, pulled, allowed)
        )

    if open_devices:
        findings.append(
            "%d devices carry no usable pull measurement" % len(open_devices)
        )
    complete = not open_devices and pulled > 0
    verdict = _worst(dispositions) if complete else PULL_INCOMPLETE
    return {
        "lot_id": lot_id,
        "verdict": verdict,
        "complete": complete,
        "lot_population": population,
        "pulled_count": pulled,
        "sample_fraction": share,
        "failing_count": failing,
        "weakest_normal_force_n": weakest if weakest is not None else 0.0,
        "counts": counts,
        "open_device_ids": open_devices,
        "devices": screened,
        "findings": findings,
    }
