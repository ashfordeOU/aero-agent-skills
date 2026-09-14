#!/usr/bin/env python3
"""Durability of external protection diode contacts, and the route an
integral unit takes instead.

Anchor: ECSS-E-ST-20-08C clause 9.6.10. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protection diode earns its place on an array by staying connected. The
adherence test asks a narrow question about that: after the contacts have
been conditioned, does the metal still hold to the package when it is
pulled away from it. The answer is a stress, not a force, because two
contacts of the same quality laid down over different bonded areas let go
at different forces and only the stress compares.

Two device configurations arrive at the same question from opposite
directions. An external diode is a discrete package with its own anode
and cathode terminals, and each terminal is a site that can be gripped
and pulled. An integral diode is built into the cell or the assembly and
has no free terminal to grip, so the durability of its contacts is shown
another way -- an assembly-level pull, a witness coupon carrying the same
contact process, or a destructive physical analysis. That substitution is
admissible; leaving the sites uncovered is not, which is why the
equivalent route is checked for what it actually covers rather than
accepted on the word "equivalent".

The device is sentenced by its weakest site. A mean over the sites hides
the one that let go, and the one that let go is the one the array sees.

The limits below are declared project values, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ADHERENCE_CONFIGURATION_NOT_STATED = "diode-configuration-not-stated"
EQUIVALENT_ROUTE_NOT_DEMONSTRATED = "equivalent-route-not-demonstrated"
REQUIRED_SITES_MISSING = "required-contact-sites-missing"
CONTACTS_NOT_DURABLE = "diode-contacts-not-durable"
CONTACTS_DURABLE = "diode-contacts-durable"
EQUIVALENT_ROUTE_ACCEPTED = "integral-diode-equivalent-route-accepted"

EXTERNAL = "external"
INTEGRAL = "integral"

DEFAULT_ADHERENCE_POLICY = {
    "min_adherence_stress_mpa": 2.0,
    "required_sites": ("anode-terminal", "cathode-terminal"),
    "admissible_equivalent_routes": (
        "assembly-level-pull",
        "witness-coupon-pull",
        "destructive-physical-analysis",
    ),
    "min_equivalent_coverage_fraction": 1.0,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % name)
    return text


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _site_tuple(name, value):
    if isinstance(value, str) or not isinstance(value, (list, tuple, set)):
        raise ValueError("%s must be a sequence of site names, got %r" % (name, value))
    sites = tuple(_require_label("%s entry" % name, entry) for entry in value)
    if not sites:
        raise ValueError("%s must name at least one site" % name)
    if len(set(sites)) != len(sites):
        raise ValueError("%s repeats a site name: %r" % (name, sites))
    return sites


def validate_adherence_policy(policy):
    """Check the adherence policy is complete and internally sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "min_adherence_stress_mpa", policy.get("min_adherence_stress_mpa")
    )
    _site_tuple("required_sites", policy.get("required_sites"))
    routes = _site_tuple(
        "admissible_equivalent_routes", policy.get("admissible_equivalent_routes")
    )
    if not routes:
        raise ValueError(
            "an integral diode with no admissible equivalent route has no way "
            "to be shown durable at all"
        )
    coverage = _require_number(
        "min_equivalent_coverage_fraction",
        policy.get("min_equivalent_coverage_fraction"),
    )
    if coverage <= 0.0 or coverage > 1.0:
        raise ValueError(
            "min_equivalent_coverage_fraction %g must sit above zero and at "
            "most one" % coverage
        )
    return policy


def normalize_configuration(value):
    """Reduce a declared device configuration to external or integral."""
    label = _require_label("configuration", value).lower()
    if label in (EXTERNAL, "discrete", "external-diode"):
        return EXTERNAL
    if label in (INTEGRAL, "integrated", "integral-diode", "monolithic"):
        return INTEGRAL
    raise ValueError(
        "configuration %r is neither an external nor an integral diode, so the "
        "clause cannot be routed" % value
    )


def adherence_stress_mpa(adherence_force_n, bonded_area_mm2):
    """Turn a recorded adherence force into a stress over the area it acted on."""
    force = _require_positive("adherence_force_n", adherence_force_n)
    area = _require_positive("bonded_area_mm2", bonded_area_mm2)
    return force / area


def site_durable(stress_mpa, policy=DEFAULT_ADHERENCE_POLICY):
    """True when a site's adherence stress reaches the declared minimum."""
    validate_adherence_policy(policy)
    stress = _require_positive("stress_mpa", stress_mpa)
    return _at_least(stress, float(policy["min_adherence_stress_mpa"]))


def validate_site_reading(site):
    """Read one contact site: its name, the force it took and the area it covered."""
    if not isinstance(site, dict):
        raise ValueError("site must be a mapping, got %r" % (site,))
    name = _require_label("site name", site.get("site"))
    force = _require_positive(
        "adherence_force_n on %s" % name, site.get("adherence_force_n")
    )
    area = _require_positive(
        "bonded_area_mm2 on %s" % name, site.get("bonded_area_mm2")
    )
    return name, force, area


def missing_sites(presented, policy=DEFAULT_ADHERENCE_POLICY):
    """Required sites the record does not carry, in policy order."""
    validate_adherence_policy(policy)
    seen = set(_site_tuple("presented", presented))
    return tuple(
        site for site in policy["required_sites"] if site not in seen
    )


def weakest_site(site_records):
    """The record with the lowest adherence stress, which sentences the device."""
    if not isinstance(site_records, (list, tuple)) or not site_records:
        raise ValueError("at least one site record is needed to sentence a device")
    return min(site_records, key=lambda entry: entry["adherence_stress_mpa"])


def equivalent_route_admissible(route, policy=DEFAULT_ADHERENCE_POLICY):
    """True when the declared substitute route is one the policy admits."""
    validate_adherence_policy(policy)
    label = _require_label("route", route)
    return label in tuple(policy["admissible_equivalent_routes"])


def equivalent_coverage_fraction(covered_sites, policy=DEFAULT_ADHERENCE_POLICY):
    """Share of the required sites the equivalent route actually reaches."""
    validate_adherence_policy(policy)
    required = tuple(policy["required_sites"])
    covered = set(_site_tuple("covered_sites", covered_sites))
    reached = sum(1 for site in required if site in covered)
    return float(reached) / float(len(required))


def equivalent_coverage_sufficient(covered_sites, policy=DEFAULT_ADHERENCE_POLICY):
    """True when the substitute route covers the share of sites the policy asks."""
    validate_adherence_policy(policy)
    fraction = equivalent_coverage_fraction(covered_sites, policy)
    return _at_least(fraction, float(policy["min_equivalent_coverage_fraction"]))


def _assess_integral(case, policy, result, findings):
    equivalence = case.get("equivalent_route")
    if not isinstance(equivalence, dict):
        findings.append(
            "the unit is integral and no equivalent route is declared, so the "
            "contacts are simply unassessed rather than assessed another way"
        )
        result["verdict"] = EQUIVALENT_ROUTE_NOT_DEMONSTRATED
        return result

    route = _require_label("equivalent_route method", equivalence.get("method"))
    result["equivalent_route"] = route
    covered = equivalence.get("covered_sites")
    if covered is None:
        findings.append(
            "the equivalent route names no sites, so nothing says it reaches "
            "the contacts the pull would have reached"
        )
        result["verdict"] = EQUIVALENT_ROUTE_NOT_DEMONSTRATED
        return result

    fraction = equivalent_coverage_fraction(covered, policy)
    result["equivalent_coverage_fraction"] = fraction

    if not equivalent_route_admissible(route, policy):
        findings.append(
            "%s is not among the routes the policy admits as equivalent, so the "
            "substitution is a decision and not yet a demonstration" % route
        )
    if not equivalent_coverage_sufficient(covered, policy):
        findings.append(
            "the equivalent route reaches %.0f per cent of the required contact "
            "sites, below the coverage the policy asks"
            % (fraction * 100.0)
        )
    if findings:
        result["verdict"] = EQUIVALENT_ROUTE_NOT_DEMONSTRATED
        return result

    result["verdict"] = EQUIVALENT_ROUTE_ACCEPTED
    return result


def assess_diode_contact_adherence(case, policy=DEFAULT_ADHERENCE_POLICY):
    """Full clause 9.6.10 assessment over one presented protection diode lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_adherence_policy(policy)

    findings = []
    device_records = []
    result = {
        "configuration": None,
        "equivalent_route": None,
        "equivalent_coverage_fraction": None,
        "device_records": device_records,
        "weakest_stress_mpa": None,
        "missing_sites": (),
        "findings": findings,
    }

    configuration = case.get("configuration")
    if configuration is None:
        findings.append(
            "the record does not say whether the diode is external or integral, "
            "and the two configurations take different routes through the clause"
        )
        result["verdict"] = ADHERENCE_CONFIGURATION_NOT_STATED
        return result
    configuration = normalize_configuration(configuration)
    result["configuration"] = configuration

    if configuration == INTEGRAL:
        return _assess_integral(case, policy, result, findings)

    devices = case.get("devices")
    if not isinstance(devices, (list, tuple)):
        raise ValueError("an external diode case needs a devices record")
    if not devices:
        raise ValueError("no diode was presented, so there is nothing to assess")

    seen_devices = set()
    shortfalls = []
    absent = []
    for device in devices:
        if not isinstance(device, dict):
            raise ValueError("device must be a mapping, got %r" % (device,))
        identifier = _require_label("device id", device.get("id"))
        if identifier in seen_devices:
            raise ValueError("duplicate device id %r in the record" % identifier)
        seen_devices.add(identifier)

        sites = device.get("sites")
        if not isinstance(sites, (list, tuple)) or not sites:
            raise ValueError("device %s presents no contact site" % identifier)

        site_records = []
        names = []
        for site in sites:
            name, force, area = validate_site_reading(site)
            if name in names:
                raise ValueError(
                    "device %s repeats the site %r" % (identifier, name)
                )
            names.append(name)
            site_records.append(
                {
                    "site": name,
                    "adherence_force_n": force,
                    "bonded_area_mm2": area,
                    "adherence_stress_mpa": adherence_stress_mpa(force, area),
                }
            )

        gap = missing_sites(names, policy)
        if gap:
            absent.extend("%s/%s" % (identifier, site) for site in gap)

        weakest = weakest_site(site_records)
        durable = site_durable(weakest["adherence_stress_mpa"], policy)
        if not durable:
            shortfalls.append((identifier, weakest))
        device_records.append(
            {
                "id": identifier,
                "sites": site_records,
                "weakest_site": weakest["site"],
                "weakest_stress_mpa": weakest["adherence_stress_mpa"],
                "durable": durable,
            }
        )

    result["weakest_stress_mpa"] = min(
        entry["weakest_stress_mpa"] for entry in device_records
    )

    if absent:
        result["missing_sites"] = tuple(absent)
        findings.append(
            "the record leaves %d required contact site(s) unpulled (%s), so the "
            "lot cannot be sentenced from what was presented"
            % (len(absent), ", ".join(absent))
        )
        result["verdict"] = REQUIRED_SITES_MISSING
        return result

    if shortfalls:
        for identifier, weakest in shortfalls:
            findings.append(
                "device %s lets go at %.3g MPa on its %s, below the declared "
                "minimum, and the device is sentenced by that site"
                % (identifier, weakest["adherence_stress_mpa"], weakest["site"])
            )
        result["verdict"] = CONTACTS_NOT_DURABLE
        return result

    result["verdict"] = CONTACTS_DURABLE
    return result
