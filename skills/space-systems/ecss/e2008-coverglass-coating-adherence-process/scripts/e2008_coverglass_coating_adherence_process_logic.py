#!/usr/bin/env python3
"""Loading every coverglass into the chamber before an adherence check.

Anchor: ECSS-E-ST-20-08C clause 8.7.11.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The population here is the whole lot, not a sample of it. That single
word is what separates this step from the sampled tests either side of
it: the adherence check that follows reports on articles that were
conditioned, so an article that never entered the chamber has no
conditioned state to report and cannot be covered by a result taken on
its neighbours.

Three things follow from that.

Completeness. The lot is declared before the load, and the load is
measured against the declaration, not against whatever reached the
bench. An article on the roster and not in the chamber is an omission.
An article in the chamber and not on the roster is a stranger: it will
be conditioned, it may be reported, and nobody knows what lot its
result belongs to.

Capacity. A rack holds a whole number of articles, so a lot larger than
the chamber holds is split into batches, and the batch count is the lot
size divided by the capacity, rounded up. Each batch is a separate run
of the same condition, so the batch an article sat in has to be
recorded with it -- two batches at nominally the same set point are
still two exposures.

Attribution. Every article gets one slot and one slot gets one article.
An article whose slot nobody wrote down cannot have an exposure
attributed to it, and two articles recorded in one slot mean at least
one of those records is wrong. Coated faces are kept unstacked and out
of contact for the same reason the soak keeps them apart: a face under
another article is not a conditioned face.

The chamber stays at the pressure of the room. A vent left shut turns
an ambient exposure into a vessel run, which is a different condition
whatever the gauge on the front says.

The capacities, tolerances and minima below are a declared policy, not
a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LOT_NOT_ESTABLISHED = "coverglass-lot-not-established"
LOADING_INCOMPLETE = "chamber-loading-incomplete"
LOADING_NOT_ATTRIBUTABLE = "chamber-loading-not-attributable"
CHAMBER_NOT_AMBIENT = "chamber-not-vented-to-ambient"
LOT_LOADED = "all-coverglasses-loaded"

FACE_UP = "face-up"
FACE_OUTBOARD = "face-outboard"
FACE_DOWN = "face-down"
RECOGNISED_ORIENTATIONS = (FACE_DOWN, FACE_OUTBOARD, FACE_UP)
EXPOSED_ORIENTATIONS = (FACE_OUTBOARD, FACE_UP)

DEFAULT_LOADING_POLICY = {
    "slots_per_rack": 25,
    "max_racks": 4,
    "max_gauge_pressure_kpa": 0.5,
    "max_batches": 6,
    "require_slot_record": True,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_loading_policy(policy):
    """Check a loading policy is complete and internally consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("slots_per_rack", policy.get("slots_per_rack"))
    _require_count("max_racks", policy.get("max_racks"))
    _require_count("max_batches", policy.get("max_batches"))
    gauge = _require_number(
        "max_gauge_pressure_kpa", policy.get("max_gauge_pressure_kpa")
    )
    if gauge < 0.0:
        raise ValueError(
            "max_gauge_pressure_kpa must not be negative, got %g" % gauge
        )
    _require_flag("require_slot_record", policy.get("require_slot_record"))
    return policy


def chamber_capacity(policy=DEFAULT_LOADING_POLICY):
    """Articles the chamber holds in one run, over all its racks."""
    validate_loading_policy(policy)
    return int(policy["slots_per_rack"]) * int(policy["max_racks"])


def batch_count(lot_size, capacity):
    """Runs a lot of that size needs at that capacity, rounding up."""
    size = _require_count("lot_size", lot_size)
    held = _require_count("capacity", capacity)
    return -(-size // held)


def loaded_fraction(loaded_articles, lot_size):
    """Share of the declared lot that actually entered the chamber."""
    size = _require_count("lot_size", lot_size)
    if not isinstance(loaded_articles, int) or isinstance(loaded_articles, bool):
        raise ValueError(
            "loaded_articles must be a whole number, got %r" % (loaded_articles,)
        )
    if loaded_articles < 0:
        raise ValueError(
            "loaded_articles must not be negative, got %d" % loaded_articles
        )
    if loaded_articles > size:
        raise ValueError(
            "%d loaded article(s) exceed the %d on the declared roster; the "
            "surplus belongs to no lot" % (loaded_articles, size)
        )
    return loaded_articles / size


def lot_membership(lot_roster, loaded_records):
    """Split a load against the roster into loaded, omitted and strangers."""
    if not isinstance(lot_roster, (list, tuple)):
        raise ValueError("lot_roster must be a sequence of article identifiers")
    if not isinstance(loaded_records, (list, tuple)):
        raise ValueError("loaded_records must be a sequence of load records")
    roster = []
    for entry in lot_roster:
        identifier = _require_label("roster entry", entry)
        if not identifier:
            raise ValueError("a roster entry must not be blank")
        if identifier in roster:
            raise ValueError("duplicate roster entry %r" % identifier)
        roster.append(identifier)
    if not roster:
        return (), (), ()

    loaded = []
    strangers = []
    seen = set()
    for record in loaded_records:
        if not isinstance(record, dict):
            raise ValueError("load record must be a mapping, got %r" % (record,))
        identifier = _require_label("load record id", record.get("id"))
        if not identifier:
            raise ValueError("a load record id must not be blank")
        if identifier in seen:
            raise ValueError("article %r is loaded twice" % identifier)
        seen.add(identifier)
        if identifier in roster:
            loaded.append(identifier)
        else:
            strangers.append(identifier)
    omitted = [identifier for identifier in roster if identifier not in seen]
    return tuple(loaded), tuple(omitted), tuple(strangers)


def orientation_exposes_the_coating(orientation):
    """True when the coated face meets the chamber atmosphere."""
    name = _require_label("orientation", orientation)
    if name not in RECOGNISED_ORIENTATIONS:
        raise ValueError(
            "unknown orientation %r; recognised orientations are %s"
            % (orientation, ", ".join(RECOGNISED_ORIENTATIONS))
        )
    return name in EXPOSED_ORIENTATIONS


def slot_findings(loaded_records, policy=DEFAULT_LOADING_POLICY):
    """Everything that stops a load being attributed, in record order."""
    validate_loading_policy(policy)
    if not isinstance(loaded_records, (list, tuple)):
        raise ValueError("loaded_records must be a sequence of load records")
    findings = []
    occupied = {}
    slots_per_rack = int(policy["slots_per_rack"])
    max_racks = int(policy["max_racks"])
    require_slot = bool(policy["require_slot_record"])

    for record in loaded_records:
        if not isinstance(record, dict):
            raise ValueError("load record must be a mapping, got %r" % (record,))
        identifier = _require_label("load record id", record.get("id"))

        if "slot" not in record:
            if require_slot:
                findings.append(
                    "article %s records no slot, so nothing attributes an "
                    "exposure to it" % identifier
                )
        else:
            rack = _require_count("rack", record.get("rack"))
            slot = _require_count("slot", record.get("slot"))
            if rack > max_racks:
                findings.append(
                    "article %s is recorded in rack %d, beyond the %d the "
                    "chamber holds" % (identifier, rack, max_racks)
                )
            if slot > slots_per_rack:
                findings.append(
                    "article %s is recorded in slot %d, beyond the %d a rack "
                    "holds" % (identifier, slot, slots_per_rack)
                )
            position = (rack, slot)
            if position in occupied:
                findings.append(
                    "articles %s and %s are both recorded in rack %d slot %d, "
                    "so at least one of those records is wrong"
                    % (occupied[position], identifier, rack, slot)
                )
            else:
                occupied[position] = identifier

        if "batch" not in record:
            findings.append(
                "article %s records no batch, so its exposure cannot be tied "
                "to the run it actually sat in" % identifier
            )
        else:
            _require_count("batch", record.get("batch"))

        if not orientation_exposes_the_coating(record.get("orientation")):
            findings.append(
                "article %s lies %s, so the coated face is against the rack "
                "rather than the atmosphere"
                % (identifier, _require_label("orientation", record["orientation"]))
            )
        if _require_flag("stacked_on_another", record.get("stacked_on_another")):
            findings.append(
                "article %s is stacked on another, so neither of the two "
                "touching faces is a conditioned face" % identifier
            )
    return tuple(findings)


def chamber_vented_to_ambient(gauge_pressure_kpa, policy=DEFAULT_LOADING_POLICY):
    """True while the chamber sits at the pressure of the room around it."""
    validate_loading_policy(policy)
    gauge = _require_number("gauge_pressure_kpa", gauge_pressure_kpa)
    return _at_most(abs(gauge), float(policy["max_gauge_pressure_kpa"]))


def assess_coverglass_chamber_loading(case, policy=DEFAULT_LOADING_POLICY):
    """Full clause 8.7.11.2.2 judgement for one chamber load."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_loading_policy(policy)
    if "lot_roster" not in case:
        raise ValueError(
            "case is missing lot_roster; an absent roster is not an empty one"
        )
    roster = case["lot_roster"]
    records = case.get("loaded_records")
    if not isinstance(records, (list, tuple)):
        raise ValueError("case is missing a loaded_records list")
    gauge = _require_number("gauge_pressure_kpa", case.get("gauge_pressure_kpa"))

    findings = []
    capacity = chamber_capacity(policy)
    result = {
        "lot_size": 0,
        "chamber_capacity": capacity,
        "loaded_articles": (),
        "omitted_articles": (),
        "stranger_articles": (),
        "loaded_fraction": None,
        "required_batches": None,
        "findings": findings,
    }

    loaded, omitted, strangers = lot_membership(roster, records)
    result["lot_size"] = len(loaded) + len(omitted)
    result["loaded_articles"] = loaded
    result["omitted_articles"] = omitted
    result["stranger_articles"] = strangers

    if not result["lot_size"]:
        findings.append(
            "the lot roster is empty, so there is no declared population the "
            "load can be measured against"
        )
        result["verdict"] = LOT_NOT_ESTABLISHED
        return result

    result["required_batches"] = batch_count(result["lot_size"], capacity)
    result["loaded_fraction"] = loaded_fraction(len(loaded), result["lot_size"])

    if result["required_batches"] > int(policy["max_batches"]):
        findings.append(
            "the %d article lot needs %d run(s) at a chamber capacity of %d, "
            "beyond the %d the campaign allows"
            % (
                result["lot_size"],
                result["required_batches"],
                capacity,
                int(policy["max_batches"]),
            )
        )
        result["verdict"] = LOT_NOT_ESTABLISHED
        return result

    if omitted or strangers:
        for identifier in omitted:
            findings.append(
                "roster article %s never entered the chamber, so it has no "
                "conditioned state an adherence check can report" % identifier
            )
        for identifier in strangers:
            findings.append(
                "loaded article %s is not on the roster, so its result belongs "
                "to no declared lot" % identifier
            )
        result["verdict"] = LOADING_INCOMPLETE
        return result

    attribution = slot_findings(records, policy)
    if attribution:
        findings.extend(attribution)
        result["verdict"] = LOADING_NOT_ATTRIBUTABLE
        return result

    if not chamber_vented_to_ambient(gauge, policy):
        findings.append(
            "the chamber sits %.2f kPa off the pressure of the room; the "
            "conditioning is an ambient pressure exposure and a sealed vessel "
            "is a different one" % gauge
        )
        result["verdict"] = CHAMBER_NOT_AMBIENT
        return result

    result["verdict"] = LOT_LOADED
    return result
