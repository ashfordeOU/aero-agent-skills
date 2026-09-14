#!/usr/bin/env python3
"""Finish quality of the contact surfaces of a solar-array blocking diode.

Anchor: ECSS-E-ST-20-08C clause 12.6.14. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A blocking diode carries the whole string current through two small
metallised contacts, and every later joint -- the welded interconnector,
the soldered tab -- is made onto the finish those contacts carry. The
surface finish check looks at that finish and has to turn what it sees
into a verdict. Two different things are being judged at once and they
fail in opposite directions:

    the texture     the roughness of the metallisation as a whole, which
                    decides whether a weld or a solder joint will wet
                    and seat at all
    the defects     discrete anomalies sitting on an otherwise sound
                    finish -- a blister, a pit, a scratch, oxidation,
                    a residue film -- each of which is judged on how
                    deep into the metallisation it reaches and how much
                    of the contact it covers

Texture is a single number against two ceilings. Below the working
ceiling the contact is as drawn. Between the working ceiling and the
bondable ceiling the contact still takes a joint but not a repeatable
one, so it goes back for repolishing. Past the bondable ceiling no
joint can be relied on and the device is out.

Defects are not judged on how they look. A dark patch that is a film
sitting on top of intact metallisation is a cleaning job; a bright pit
that has eaten through to the substrate has removed the conductor and
is not repairable. The discriminator is penetration -- the depth of the
anomaly as a fraction of the metallisation thickness it sits in -- and
the same visual grade can land on either side of it. Coverage is the
second axis: a shallow anomaly spread over most of the contact leaves
no sound area for the joint even though nothing went through.

A blister is the exception that needs no arithmetic. It is the finish
standing off the metal underneath it, which means adhesion has already
been lost over the area it spans, so it is rejected on sight whatever
its depth reads.

Both polarities carry a joint, so a device with only one contact
examined is not sentenced -- it is left open. The same is true of an
examination carried out below the magnification the inspection policy
declares: what was not resolvable was not examined, and a clean report
from an under-magnified look is a clean report about nothing.

The policy below is a declared project policy, not a physical constant;
a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
FINISH_DISPOSITIONS = (ACCEPT, REWORK, REJECT)

EXAMINATION_INCOMPLETE = "examination-incomplete"

BLISTER = "blister"
PIT = "pit"
SCRATCH = "scratch"
OXIDATION = "oxidation"
RESIDUE = "residue"
ANOMALY_KINDS = (BLISTER, PIT, SCRATCH, OXIDATION, RESIDUE)

ANODE = "anode"
CATHODE = "cathode"
REQUIRED_POLARITIES = (ANODE, CATHODE)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

DEFAULT_FINISH_POLICY = {
    "magnification_floor": 20.0,
    "working_roughness_ceiling_um": 0.80,
    "bondable_roughness_ceiling_um": 1.60,
    "max_anomaly_coverage_fraction": 0.05,
    "max_total_coverage_fraction": 0.10,
    "max_penetration_fraction": 0.30,
    "rework_margin_factor": 2.0,
    "max_affected_device_fraction": 0.05,
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A coverage total is a sum of declared fractions and a penetration is
    a ratio of two measured depths, so a value that should land exactly
    on its limit can evaluate a few units in the last place past it, and
    it lands differently on different machines. The limit is never
    moved; only the comparison tolerates the representation error.
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


def validate_finish_policy(policy):
    """Check a surface finish policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("policy magnification_floor", policy.get("magnification_floor"))
    working = _require_positive(
        "policy working_roughness_ceiling_um",
        policy.get("working_roughness_ceiling_um"),
    )
    bondable = _require_positive(
        "policy bondable_roughness_ceiling_um",
        policy.get("bondable_roughness_ceiling_um"),
    )
    per_kind = _require_fraction(
        "policy max_anomaly_coverage_fraction",
        policy.get("max_anomaly_coverage_fraction"),
    )
    total = _require_fraction(
        "policy max_total_coverage_fraction",
        policy.get("max_total_coverage_fraction"),
    )
    _require_fraction(
        "policy max_penetration_fraction", policy.get("max_penetration_fraction")
    )
    _require_fraction(
        "policy max_affected_device_fraction",
        policy.get("max_affected_device_fraction"),
    )
    factor = policy.get("rework_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "policy rework_margin_factor must be at least one, got %r" % (factor,)
        )
    if bondable <= working:
        raise ValueError(
            "the roughness past which the contact stops being bondable (%r um) is "
            "at or below the roughness it is meant to work at (%r um), which "
            "leaves no band in which a rough contact can be repolished rather "
            "than scrapped" % (bondable, working)
        )
    if per_kind > total:
        raise ValueError(
            "the per-kind coverage allowance (%r) exceeds the total coverage "
            "allowance (%r), so a single anomaly kind could pass while the "
            "contact as a whole is already over" % (per_kind, total)
        )
    return policy


def penetration_fraction(depth_um, metallization_thickness_um):
    """How far into the metallisation an anomaly reaches, as a fraction.

    One means the anomaly has reached the substrate; above one means it
    has gone past it into the material beneath.
    """
    depth = _require_non_negative("depth_um", depth_um)
    thickness = _require_positive(
        "metallization_thickness_um", metallization_thickness_um
    )
    return depth / thickness


def assess_anomaly(anomaly, metallization_thickness_um, policy=DEFAULT_FINISH_POLICY):
    """Grade one finish anomaly on penetration and coverage, not appearance."""
    validate_finish_policy(policy)
    if not isinstance(anomaly, dict):
        raise ValueError("anomaly must be a mapping, got %r" % (anomaly,))
    kind = anomaly.get("kind")
    if kind not in ANOMALY_KINDS:
        raise ValueError(
            "anomaly kind must be one of %s, got %r"
            % (", ".join(ANOMALY_KINDS), kind)
        )
    coverage = _require_fraction("coverage_fraction", anomaly.get("coverage_fraction"))
    penetration = penetration_fraction(
        anomaly.get("depth_um"), metallization_thickness_um
    )
    factor = policy["rework_margin_factor"]
    dispositions = [ACCEPT]
    findings = []

    if kind == BLISTER:
        dispositions.append(REJECT)
        findings.append(
            "a blister over %.3f of the contact is the finish standing off the "
            "metal beneath it, so adhesion is already lost over that area "
            "whatever its depth reads" % coverage
        )

    through = _at_least(penetration, 1.0)
    if through:
        dispositions.append(REJECT)
        findings.append(
            "the anomaly reaches %.3f of the metallisation thickness, so the "
            "conductor is gone through to the substrate and no joint can be "
            "remade on it" % penetration
        )
    elif not _at_most(penetration, policy["max_penetration_fraction"]):
        deep_limit = policy["max_penetration_fraction"] * factor
        if _at_most(penetration, deep_limit):
            dispositions.append(REWORK)
            findings.append(
                "the anomaly reaches %.3f of the metallisation thickness, past "
                "the %.3f the policy permits"
                % (penetration, policy["max_penetration_fraction"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "the anomaly reaches %.3f of the metallisation thickness, past "
                "the rework margin of %.3f" % (penetration, deep_limit)
            )

    if not _at_most(coverage, policy["max_anomaly_coverage_fraction"]):
        wide_limit = policy["max_anomaly_coverage_fraction"] * factor
        if _at_most(coverage, wide_limit):
            dispositions.append(REWORK)
            findings.append(
                "%s covers %.3f of the contact, past the %.3f the policy permits"
                % (kind, coverage, policy["max_anomaly_coverage_fraction"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%s covers %.3f of the contact, past the rework margin of %.3f"
                % (kind, coverage, wide_limit)
            )

    return {
        "kind": kind,
        "coverage_fraction": coverage,
        "penetration_fraction": penetration,
        "through_to_substrate": through,
        "disposition": _worst(dispositions),
        "findings": findings,
    }


def coverage_by_kind(anomalies, metallization_thickness_um,
                     policy=DEFAULT_FINISH_POLICY):
    """Total the coverage each anomaly kind takes off one contact."""
    validate_finish_policy(policy)
    if not isinstance(anomalies, (list, tuple)):
        raise ValueError("anomalies must be a list, got %r" % (anomalies,))
    graded = []
    totals = dict((kind, 0.0) for kind in ANOMALY_KINDS)
    running = 0.0
    for anomaly in anomalies:
        result = assess_anomaly(anomaly, metallization_thickness_um, policy)
        totals[result["kind"]] += result["coverage_fraction"]
        running += result["coverage_fraction"]
        graded.append(result)
    if not _at_most(running, 1.0):
        raise ValueError(
            "the anomalies add up to %.3f of the contact area, which is more "
            "area than the contact has; the coverage figures are inconsistent"
            % running
        )
    return {
        "graded": graded,
        "coverage_by_kind": totals,
        "total_coverage_fraction": running,
    }


def assess_contact_finish(contact, policy=DEFAULT_FINISH_POLICY):
    """Grade the finish on one blocking diode contact."""
    validate_finish_policy(policy)
    if not isinstance(contact, dict):
        raise ValueError("contact must be a mapping, got %r" % (contact,))
    polarity = contact.get("polarity")
    if polarity not in REQUIRED_POLARITIES:
        raise ValueError(
            "contact polarity must be one of %s, got %r"
            % (", ".join(REQUIRED_POLARITIES), polarity)
        )
    thickness = _require_positive(
        "metallization_thickness_um on the %s contact" % polarity,
        contact.get("metallization_thickness_um"),
    )
    roughness = _require_non_negative(
        "roughness_um on the %s contact" % polarity, contact.get("roughness_um")
    )
    magnification = _require_positive(
        "examination_magnification on the %s contact" % polarity,
        contact.get("examination_magnification"),
    )
    accumulation = coverage_by_kind(
        contact.get("anomalies", []), thickness, policy
    )

    findings = []
    dispositions = [ACCEPT]
    factor = policy["rework_margin_factor"]

    under_magnified = not _at_least(magnification, policy["magnification_floor"])
    if under_magnified:
        findings.append(
            "the %s contact was examined at x%.1f, below the x%.1f the policy "
            "declares; an anomaly finer than the examination resolved was not "
            "looked for, so a clean report says nothing"
            % (polarity, magnification, policy["magnification_floor"])
        )

    if not _at_most(roughness, policy["bondable_roughness_ceiling_um"]):
        dispositions.append(REJECT)
        findings.append(
            "the %s contact reads %.3f um, past the %.3f um beyond which no "
            "joint onto it can be relied on"
            % (polarity, roughness, policy["bondable_roughness_ceiling_um"])
        )
    elif not _at_most(roughness, policy["working_roughness_ceiling_um"]):
        dispositions.append(REWORK)
        findings.append(
            "the %s contact reads %.3f um, past the %.3f um it is meant to work "
            "at but still inside the bondable ceiling, so it returns for "
            "repolishing"
            % (polarity, roughness, policy["working_roughness_ceiling_um"])
        )

    for result in accumulation["graded"]:
        dispositions.append(result["disposition"])
        for finding in result["findings"]:
            findings.append("the %s contact: %s" % (polarity, finding))

    total = accumulation["total_coverage_fraction"]
    if not _at_most(total, policy["max_total_coverage_fraction"]):
        wide_limit = policy["max_total_coverage_fraction"] * factor
        if _at_most(total, wide_limit):
            dispositions.append(REWORK)
            findings.append(
                "anomalies take %.3f of the %s contact in total, past the %.3f "
                "the policy permits even though no single one is over"
                % (total, polarity, policy["max_total_coverage_fraction"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "anomalies take %.3f of the %s contact in total, past the "
                "rework margin of %.3f" % (total, polarity, wide_limit)
            )

    verdict = EXAMINATION_INCOMPLETE if under_magnified else _worst(dispositions)
    return {
        "polarity": polarity,
        "verdict": verdict,
        "examined": not under_magnified,
        "roughness_um": roughness,
        "metallization_thickness_um": thickness,
        "examination_magnification": magnification,
        "anomaly_count": len(accumulation["graded"]),
        "coverage_by_kind": accumulation["coverage_by_kind"],
        "total_coverage_fraction": total,
        "deepest_penetration_fraction": max(
            [0.0] + [r["penetration_fraction"] for r in accumulation["graded"]]
        ),
        "findings": findings,
    }


def assess_blocking_diode_finish(device, policy=DEFAULT_FINISH_POLICY):
    """Sentence one blocking diode from the finish on both its contacts."""
    validate_finish_policy(policy)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    device_id = _require_text("device_id", device.get("device_id"))
    contacts = device.get("contacts")
    if not isinstance(contacts, (list, tuple)) or not contacts:
        raise ValueError(
            "%s must carry at least one contact record, got %r"
            % (device_id, contacts)
        )
    graded = []
    seen = set()
    for contact in contacts:
        result = assess_contact_finish(contact, policy)
        if result["polarity"] in seen:
            raise ValueError(
                "%s carries two records for its %s contact; one of them belongs "
                "to another device or another polarity"
                % (device_id, result["polarity"])
            )
        seen.add(result["polarity"])
        graded.append(result)

    missing = [p for p in REQUIRED_POLARITIES if p not in seen]
    findings = []
    dispositions = [ACCEPT]
    for result in graded:
        if result["examined"]:
            dispositions.append(result["verdict"])
        for finding in result["findings"]:
            findings.append("%s %s" % (device_id, finding))
    if missing:
        findings.append(
            "%s carries no finish examination on its %s contact; both polarities "
            "take a joint, so the device is not sentenced from one of them"
            % (device_id, " and ".join(missing))
        )

    unexamined = [r["polarity"] for r in graded if not r["examined"]]
    complete = not missing and not unexamined
    verdict = _worst(dispositions) if complete else EXAMINATION_INCOMPLETE
    return {
        "device_id": device_id,
        "verdict": verdict,
        "complete": complete,
        "examined_polarities": sorted(seen),
        "missing_polarities": missing,
        "under_magnified_polarities": unexamined,
        "contacts": graded,
        "worst_total_coverage_fraction": max(
            [0.0] + [r["total_coverage_fraction"] for r in graded]
        ),
        "findings": findings,
    }


def screen_blocking_diode_surface_finish(lot, policy=DEFAULT_FINISH_POLICY):
    """Clause 12.6.14 surface finish screen over one blocking diode lot."""
    validate_finish_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))
    declared = lot.get("declared_device_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_device_count must be a positive integer, got %r" % (declared,)
        )
    records = lot.get("devices")
    if not isinstance(records, (list, tuple)):
        raise ValueError("devices must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d device records against a declared count of %d on lot %s"
            % (len(records), declared, lot_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_blocking_diode_finish(record, policy)
        if result["device_id"] in seen:
            raise ValueError(
                "duplicate device id %r on lot %s" % (result["device_id"], lot_id)
            )
        seen.add(result["device_id"])
        screened.append(result)

    examined = len(screened)
    counts = dict((state, 0) for state in FINISH_DISPOSITIONS)
    counts[EXAMINATION_INCOMPLETE] = 0
    findings = []
    dispositions = [ACCEPT]
    affected = 0
    open_devices = []
    for result in screened:
        counts[result["verdict"]] += 1
        if result["complete"]:
            dispositions.append(result["verdict"])
        else:
            open_devices.append(result["device_id"])
        if result["findings"]:
            affected += 1
        for finding in result["findings"]:
            findings.append(finding)

    factor = policy["rework_margin_factor"]
    allowed = policy["max_affected_device_fraction"] * examined
    if examined and not _at_most(affected, allowed):
        if _at_most(affected, allowed * factor):
            dispositions.append(REWORK)
            findings.append(
                "%d of %d examined blocking diodes carry a finish finding, past "
                "the %.2f the lot allowance permits" % (affected, examined, allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d examined blocking diodes carry a finish finding, past "
                "the rework margin of %.2f" % (affected, examined, allowed * factor)
            )

    missing = declared - examined
    if missing:
        findings.append(
            "%d of %d blocking diodes in the lot carry no finish examination; an "
            "allowance applied to a short set is applied to the wrong population"
            % (missing, declared)
        )
    if open_devices:
        findings.append(
            "%d blocking diodes are left open on an incomplete examination"
            % len(open_devices)
        )
    complete = missing == 0 and not open_devices
    verdict = _worst(dispositions) if complete else EXAMINATION_INCOMPLETE
    return {
        "lot_id": lot_id,
        "verdict": verdict,
        "complete": complete,
        "declared_device_count": declared,
        "examined_count": examined,
        "missing_count": missing,
        "affected_count": affected,
        "counts": counts,
        "open_device_ids": open_devices,
        "devices": screened,
        "findings": findings,
    }
