#!/usr/bin/env python3
"""Contact metallisation thickness uniformity of a protection diode.

Anchor: ECSS-E-ST-20-08C clause 9.6.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause is a qualification check: the metallisation deposited on a
protection diode contact has to hold an even thickness across the whole
land, not merely somewhere on it. That one word -- across -- carries
three rules that get dropped whenever a uniformity number is quoted
from a handful of readings.

The first is coverage. A spread is only as wide as the sites it was
taken from. A land probed three times near its middle returns a
beautiful spread and says nothing at all about the edge where the
deposit actually thins, so the zones of the contact are enumerated
first and a contact missing a zone is closed as not evaluated rather
than sentenced on the readings that do exist. The site count and the
zone list are separate gates: five readings clustered in one corner
satisfy a count and not a coverage.

The second is that uniformity is a spread about the contact's own mean
and the absolute floor is a different question. A contact plated thin
and plated evenly thin is perfectly uniform and still unweldable, so
the local floor is applied per site independently of the spread, and a
site under it is a reject rather than an outlier. The over-deposit
ceiling sits on the other side for the same reason: a nodule is a local
excess that a mean quietly absorbs.

The third is that a diode has two contacts, one per polarity, and a
verdict needs both. A polarity carrying no map is not a uniform
polarity, and the qualification sample has the same shape one level up:
a run that measured fewer devices than it declared has not qualified
the population it claims to speak for.

The spread and the variation coefficient are kept as separate figures
on purpose. The spread is driven by the two extreme sites and is what a
single thin corner shows up in; the variation coefficient describes the
whole map and is what a land sloping gently across its width shows up
in. A map can pass one and fail the other, and reporting only the
better of the two is how a sloping deposit survives qualification.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANODE = "anode"
CATHODE = "cathode"
CONTACT_POLARITIES = (ANODE, CATHODE)

ZONE_CENTRE = "centre"
ZONE_NORTH = "north"
ZONE_SOUTH = "south"
ZONE_EAST = "east"
ZONE_WEST = "west"
CONTACT_ZONES = (ZONE_CENTRE, ZONE_NORTH, ZONE_SOUTH, ZONE_EAST, ZONE_WEST)

UNIFORM = "uniform"
THIN_SITE = "thin-site"
THICK_SITE = "thick-site"
BARE_SITE = "bare-site"
SITE_GRADES = (UNIFORM, THIN_SITE, THICK_SITE, BARE_SITE)

ACCEPT = "accept"
REFER_FOR_REVIEW = "refer-for-review"
NOT_ESTABLISHED = "not-established"
REJECT = "reject"
VERDICTS = (ACCEPT, REFER_FOR_REVIEW, NOT_ESTABLISHED, REJECT)

_SEVERITY_ORDER = {
    ACCEPT: 0,
    REFER_FOR_REVIEW: 1,
    NOT_ESTABLISHED: 2,
    REJECT: 3,
}

_GRADE_VERDICT = {
    UNIFORM: ACCEPT,
    THIN_SITE: REFER_FOR_REVIEW,
    THICK_SITE: REFER_FOR_REVIEW,
    BARE_SITE: REJECT,
}

DEFAULT_UNIFORMITY_CRITERIA = {
    "max_spread_fraction": 0.20,
    "max_variation_coefficient": 0.08,
    "min_local_thickness_um": 2.0,
    "max_local_thickness_um": 12.0,
    "min_sites_per_contact": 5,
    "required_zones": CONTACT_ZONES,
    "min_qualification_devices": 3,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must fall in the interval (0, 1], got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


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


def validate_uniformity_criteria(criteria):
    """Check a uniformity criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_fraction("max_spread_fraction", criteria.get("max_spread_fraction"))
    _require_fraction(
        "max_variation_coefficient", criteria.get("max_variation_coefficient")
    )
    floor = _require_positive(
        "min_local_thickness_um", criteria.get("min_local_thickness_um")
    )
    ceiling = _require_positive(
        "max_local_thickness_um", criteria.get("max_local_thickness_um")
    )
    if _at_most(ceiling, floor):
        raise ValueError(
            "max_local_thickness_um must sit above min_local_thickness_um; a "
            "band that closes on itself admits no deposit at all"
        )
    sites = _require_count(
        "min_sites_per_contact", criteria.get("min_sites_per_contact")
    )
    if sites < 2:
        raise ValueError(
            "min_sites_per_contact must be at least 2; a single reading has no "
            "spread to describe"
        )
    zones = criteria.get("required_zones")
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError("required_zones must be a non-empty sequence of zone names")
    unknown = [zone for zone in zones if zone not in CONTACT_ZONES]
    if unknown:
        raise ValueError("unknown contact zone %r" % (unknown[0],))
    devices = _require_count(
        "min_qualification_devices", criteria.get("min_qualification_devices")
    )
    if devices < 1:
        raise ValueError(
            "min_qualification_devices must be at least 1; a qualification with "
            "no device measured has qualified nothing"
        )
    return criteria


def validate_thickness_site(site):
    """Normalise one mapped thickness reading on a contact."""
    if not isinstance(site, dict):
        raise ValueError("thickness site must be a mapping, got %r" % (site,))
    zone = site.get("zone")
    if zone not in CONTACT_ZONES:
        raise ValueError(
            "site zone must be one of %s, got %r" % (", ".join(CONTACT_ZONES), zone)
        )
    return {
        "zone": zone,
        "thickness_um": _require_positive(
            "site thickness_um", site.get("thickness_um")
        ),
    }


def validate_uniformity_contact(contact):
    """Normalise one polarity contact and its thickness map."""
    if not isinstance(contact, dict):
        raise ValueError("contact must be a mapping, got %r" % (contact,))
    identifier = _require_label("contact id", contact.get("id"))
    if not identifier:
        raise ValueError("contact id must not be blank")
    polarity = contact.get("polarity")
    if polarity not in CONTACT_POLARITIES:
        raise ValueError(
            "contact polarity must be one of %s, got %r"
            % (", ".join(CONTACT_POLARITIES), polarity)
        )
    sites = contact.get("sites")
    if not isinstance(sites, (list, tuple)):
        raise ValueError("contact must record sites as a sequence")
    if not sites:
        raise ValueError(
            "a contact with no thickness site measured cannot be mapped; an "
            "empty map is not an even one"
        )
    return {
        "id": identifier,
        "polarity": polarity,
        "sites": tuple(validate_thickness_site(site) for site in sites),
    }


def mean_thickness_um(sites):
    """Arithmetic mean of a contact thickness map."""
    readings = [validate_thickness_site(site)["thickness_um"] for site in _sequence(sites)]
    if not readings:
        raise ValueError("a thickness map with no site has no mean")
    return sum(readings) / len(readings)


def _sequence(sites):
    if not isinstance(sites, (list, tuple)):
        raise ValueError("sites must be a sequence of thickness readings")
    return sites


def thickness_spread_fraction(sites):
    """(thickest - thinnest) over the mean: what one thin corner shows up in."""
    readings = [validate_thickness_site(site)["thickness_um"] for site in _sequence(sites)]
    if not readings:
        raise ValueError("a thickness map with no site has no spread")
    mean = sum(readings) / len(readings)
    return (max(readings) - min(readings)) / mean


def variation_coefficient(sites):
    """Population deviation over the mean: what a sloping deposit shows up in."""
    readings = [validate_thickness_site(site)["thickness_um"] for site in _sequence(sites)]
    if not readings:
        raise ValueError("a thickness map with no site has no variation")
    mean = sum(readings) / len(readings)
    variance = sum((reading - mean) ** 2 for reading in readings) / len(readings)
    return math.sqrt(variance) / mean


def zones_without_a_reading(sites, criteria=DEFAULT_UNIFORMITY_CRITERIA):
    """Required zones of the land that the map never reached."""
    validate_uniformity_criteria(criteria)
    covered = {validate_thickness_site(site)["zone"] for site in _sequence(sites)}
    return tuple(zone for zone in criteria["required_zones"] if zone not in covered)


def categorize_thickness_site(
    site, reference_mean_um, criteria=DEFAULT_UNIFORMITY_CRITERIA
):
    """Grade one mapped reading against the floor, the ceiling and the mean."""
    validate_uniformity_criteria(criteria)
    reading = validate_thickness_site(site)
    mean = _require_positive("reference_mean_um", reference_mean_um)
    thickness = reading["thickness_um"]
    if not _at_least(thickness, criteria["min_local_thickness_um"]):
        return (
            BARE_SITE,
            "the %s zone measures %.3g um, under the %.3g um local floor; a "
            "contact plated evenly thin is uniform and still unweldable"
            % (reading["zone"], thickness, criteria["min_local_thickness_um"]),
        )
    if not _at_most(thickness, criteria["max_local_thickness_um"]):
        return (
            THICK_SITE,
            "the %s zone measures %.3g um, over the %.3g um local ceiling; a "
            "nodule is a local excess the map mean quietly absorbs"
            % (reading["zone"], thickness, criteria["max_local_thickness_um"]),
        )
    tolerance = criteria["max_spread_fraction"] / 2.0
    deviation = (thickness - mean) / mean
    if _at_most(abs(deviation), tolerance):
        return (
            UNIFORM,
            "the %s zone sits %.1f per cent off the contact mean, inside the "
            "%.1f per cent a site may take"
            % (reading["zone"], deviation * 100.0, tolerance * 100.0),
        )
    if deviation < 0.0:
        return (
            THIN_SITE,
            "the %s zone runs %.1f per cent under the contact mean, past the "
            "%.1f per cent a site may take"
            % (reading["zone"], -deviation * 100.0, tolerance * 100.0),
        )
    return (
        THICK_SITE,
        "the %s zone runs %.1f per cent over the contact mean, past the %.1f "
        "per cent a site may take"
        % (reading["zone"], deviation * 100.0, tolerance * 100.0),
    )


def worst_verdict(verdicts):
    """The governing verdict of a set; severity, not record order."""
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence")
    if not verdicts:
        return ACCEPT
    unknown = [verdict for verdict in verdicts if verdict not in _SEVERITY_ORDER]
    if unknown:
        raise ValueError("unknown verdict %r" % (unknown[0],))
    return max(verdicts, key=lambda verdict: _SEVERITY_ORDER[verdict])


def assess_contact_uniformity(contact, criteria=DEFAULT_UNIFORMITY_CRITERIA):
    """Clause 9.6.7 uniformity verdict for one polarity contact."""
    validate_uniformity_criteria(criteria)
    land = validate_uniformity_contact(contact)
    sites = land["sites"]

    mean = mean_thickness_um(sites)
    spread = thickness_spread_fraction(sites)
    variation = variation_coefficient(sites)
    missing = zones_without_a_reading(sites, criteria)

    findings = []
    verdicts = []
    grades = []
    for site in sites:
        grade, reason = categorize_thickness_site(site, mean, criteria)
        grades.append((site["zone"], grade))
        verdicts.append(_GRADE_VERDICT[grade])
        if grade != UNIFORM:
            findings.append(reason)

    if len(sites) < criteria["min_sites_per_contact"]:
        verdicts.append(NOT_ESTABLISHED)
        findings.append(
            "%d site%s measured on the %s contact, under the %d the criteria "
            "want; a spread is only as wide as the sites it came from"
            % (
                len(sites),
                "" if len(sites) == 1 else "s",
                land["polarity"],
                criteria["min_sites_per_contact"],
            )
        )
    if missing:
        verdicts.append(NOT_ESTABLISHED)
        findings.append(
            "no reading in the %s zone%s of the %s contact; readings clustered "
            "away from a zone describe the zone they covered"
            % (
                " and ".join(missing),
                "" if len(missing) == 1 else "s",
                land["polarity"],
            )
        )
    if not _at_most(spread, criteria["max_spread_fraction"]):
        verdicts.append(REFER_FOR_REVIEW)
        findings.append(
            "the %s contact spreads %.1f per cent of its mean, past the %.1f "
            "per cent allowed; the two extreme sites drive this figure"
            % (
                land["polarity"],
                spread * 100.0,
                criteria["max_spread_fraction"] * 100.0,
            )
        )
    if not _at_most(variation, criteria["max_variation_coefficient"]):
        verdicts.append(REFER_FOR_REVIEW)
        findings.append(
            "the %s contact varies by %.1f per cent of its mean, past the %.1f "
            "per cent allowed; a land sloping gently across its width shows up "
            "here and not in the spread"
            % (
                land["polarity"],
                variation * 100.0,
                criteria["max_variation_coefficient"] * 100.0,
            )
        )

    return {
        "contact_id": land["id"],
        "polarity": land["polarity"],
        "verdict": worst_verdict(verdicts),
        "sites_measured": len(sites),
        "mean_thickness_um": mean,
        "min_thickness_um": min(site["thickness_um"] for site in sites),
        "max_thickness_um": max(site["thickness_um"] for site in sites),
        "spread_fraction": spread,
        "variation_coefficient": variation,
        "zones_without_a_reading": missing,
        "site_grades": tuple(grades),
        "findings": findings,
    }


def assess_diode_uniformity(case, criteria=DEFAULT_UNIFORMITY_CRITERIA):
    """Roll the clause 9.6.7 check up over both polarities of one diode."""
    validate_uniformity_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    contacts = case.get("contacts")
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("case must record contacts as a sequence")
    if not contacts:
        raise ValueError(
            "a diode with no contact declared cannot be checked against a "
            "clause about contact metallisation"
        )

    results = []
    seen = set()
    for contact in contacts:
        result = assess_contact_uniformity(contact, criteria)
        if result["contact_id"] in seen:
            raise ValueError(
                "duplicate contact id %r on the diode" % result["contact_id"]
            )
        seen.add(result["contact_id"])
        results.append(result)

    mapped = {result["polarity"] for result in results}
    unmapped = tuple(p for p in CONTACT_POLARITIES if p not in mapped)

    findings = []
    verdicts = [result["verdict"] for result in results]
    if unmapped:
        verdicts.append(NOT_ESTABLISHED)
        findings.append(
            "no thickness map for the %s contact; a polarity nobody mapped is "
            "not a uniform polarity" % " and ".join(unmapped)
        )

    return {
        "diode_id": _require_label("diode id", case.get("id", "unnamed-diode")),
        "verdict": worst_verdict(verdicts),
        "contacts_assessed": len(results),
        "polarities_without_a_map": unmapped,
        "widest_spread_fraction": max(result["spread_fraction"] for result in results),
        "thinnest_site_um": min(result["min_thickness_um"] for result in results),
        "contacts_not_accepted": tuple(
            result["contact_id"] for result in results if result["verdict"] != ACCEPT
        ),
        "rollup_findings": findings,
        "contact_results": tuple(results),
    }


def assess_uniformity_qualification(lot, criteria=DEFAULT_UNIFORMITY_CRITERIA):
    """Sentence a qualification run, not just the devices that were mapped."""
    validate_uniformity_criteria(criteria)
    if not isinstance(lot, dict):
        raise ValueError("qualification lot must be a mapping, got %r" % (lot,))
    declared = _require_count("declared_sample", lot.get("declared_sample"))
    devices = lot.get("devices")
    if not isinstance(devices, (list, tuple)):
        raise ValueError("qualification lot must record devices as a sequence")

    results = []
    seen = set()
    for device in devices:
        result = assess_diode_uniformity(device, criteria)
        if result["diode_id"] in seen:
            raise ValueError("duplicate diode id %r in the run" % result["diode_id"])
        seen.add(result["diode_id"])
        results.append(result)

    findings = []
    verdicts = [result["verdict"] for result in results]
    if declared < criteria["min_qualification_devices"]:
        verdicts.append(NOT_ESTABLISHED)
        findings.append(
            "the run declares %d device%s, under the %d a qualification needs; "
            "a smaller sample speaks for itself and not for the population"
            % (
                declared,
                "" if declared == 1 else "s",
                criteria["min_qualification_devices"],
            )
        )
    if len(results) < declared:
        verdicts.append(NOT_ESTABLISHED)
        findings.append(
            "%d of the %d declared devices carry a map; a run short of its own "
            "sample has not qualified the population it speaks for"
            % (len(results), declared)
        )

    return {
        "lot_id": _require_label("lot id", lot.get("id", "unnamed-lot")),
        "verdict": worst_verdict(verdicts),
        "declared_sample": declared,
        "devices_mapped": len(results),
        "devices_not_accepted": tuple(
            result["diode_id"] for result in results if result["verdict"] != ACCEPT
        ),
        "rollup_findings": findings,
        "device_results": tuple(results),
    }
