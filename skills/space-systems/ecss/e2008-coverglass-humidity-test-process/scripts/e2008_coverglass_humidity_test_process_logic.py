#!/usr/bin/env python3
"""How subgroup O coverglasses are held during an ambient pressure soak.

Anchor: ECSS-E-ST-20-08C clause 8.7.11.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause is about holding, not about heating. The chamber runs at the
pressure of the room it stands in, so the only levers the exposure has
are air temperature, relative humidity and time -- and every one of
them reaches the coverglass through the way the article is held.

Three things travel with the holding arrangement.

Population. The soak is run on the coverglasses belonging to the
designated subgroup, not on whatever was on the bench. An article whose
subgroup is not recorded is not a member: unknown membership is not
membership, and it cannot be read as non-membership either.

Geometry. A humidity soak is a vapour exposure of a surface. A
coverglass lying face down on a tray has shelved the face the coating
is on, and the moisture that reaches it is whatever diffused through
the gap the tray left, which is not the chamber condition. The article
is therefore held at its edges, standing, with a clearance to each
neighbour, and the rack pitch that follows is the article thickness
plus that clearance:

    pitch      = thickness + clearance
    capacity   = floor(usable rack length / pitch)

Whatever the holder does touch is masked, and the masked fraction of
the face is bounded, because a masked area is an unexposed area
reported as an exposed one.

Condensation. At ambient pressure the article is the coldest thing in
a warm humid chamber whenever it enters cold or the set point rises
faster than the glass follows. Below the dew point the exposure stops
being humidity and becomes liquid water, which is a different test.
The dew point is taken from the chamber air by the Magnus relation:

    gamma = ln(RH / 100) + a * T / (b + T)
    dew   = b * gamma / (a - gamma)          a = 17.62, b = 243.12 C

and the article surface is held a declared margin above it.

Time. The dwell is the settled time at the set point. The ramp the
chamber spends reaching the condition is real elapsed time that is not
exposure, and counting it turns a short soak into a compliant record.

The bands, clearances and minima below are a declared policy, not a
physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

EDGE_SLOT = "edge-slot"
EDGE_CLAMP = "edge-clamp"
WIRE_HANGER = "wire-hanger"
FLAT_TRAY = "flat-tray"
FACE_STACK = "face-stack"

EDGE_SUPPORTS = (EDGE_CLAMP, EDGE_SLOT, WIRE_HANGER)
FACE_SHELVING_SUPPORTS = (FACE_STACK, FLAT_TRAY)
RECOGNISED_SUPPORTS = tuple(sorted(EDGE_SUPPORTS + FACE_SHELVING_SUPPORTS))

SUBGROUP_NOT_ESTABLISHED = "subgroup-population-not-established"
HOLDING_NOT_ACCEPTABLE = "holding-arrangement-not-acceptable"
CHAMBER_CONDITIONS_INVALID = "chamber-conditions-invalid"
EXPOSURE_INCOMPLETE = "humidity-exposure-incomplete"
SUBGROUP_EXPOSURE_HELD = "subgroup-humidity-exposure-held"

MAGNUS_A = 17.62
MAGNUS_B_C = 243.12

DEFAULT_HOLDING_POLICY = {
    "min_subgroup_articles": 3,
    "min_face_clearance_mm": 5.0,
    "max_masked_face_fraction": 0.10,
    "min_dew_point_margin_c": 0.5,
    "min_relative_humidity_percent": 85.0,
    "max_relative_humidity_percent": 95.0,
    "min_chamber_temperature_c": 40.0,
    "max_chamber_temperature_c": 50.0,
    "max_gauge_pressure_kpa": 0.5,
    "min_dwell_hours": 24.0,
    "holder_materials": (
        "anodised-aluminium",
        "borosilicate",
        "ptfe",
        "stainless-steel-316l",
    ),
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


def _within(value, low, high):
    return _at_least(value, low) and _at_most(value, high)


def _require_band(policy, low_key, high_key):
    low = _require_number(low_key, policy.get(low_key))
    high = _require_number(high_key, policy.get(high_key))
    if high <= low:
        raise ValueError("%s %g must be above %s %g" % (high_key, high, low_key, low))
    return low, high


def validate_holding_policy(policy):
    """Check a holding policy is complete and internally consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("min_subgroup_articles", policy.get("min_subgroup_articles"))
    _require_positive("min_face_clearance_mm", policy.get("min_face_clearance_mm"))
    masked = _require_number(
        "max_masked_face_fraction", policy.get("max_masked_face_fraction")
    )
    if not 0.0 < masked < 1.0:
        raise ValueError(
            "max_masked_face_fraction must sit between zero and one, got %g" % masked
        )
    _require_non_negative(
        "min_dew_point_margin_c", policy.get("min_dew_point_margin_c")
    )
    low_rh, high_rh = _require_band(
        policy, "min_relative_humidity_percent", "max_relative_humidity_percent"
    )
    if low_rh <= 0.0 or high_rh >= 100.0:
        raise ValueError(
            "the humidity band must sit above zero and below saturation, got "
            "%g%% to %g%%" % (low_rh, high_rh)
        )
    _require_band(policy, "min_chamber_temperature_c", "max_chamber_temperature_c")
    _require_non_negative("max_gauge_pressure_kpa", policy.get("max_gauge_pressure_kpa"))
    _require_positive("min_dwell_hours", policy.get("min_dwell_hours"))
    materials = policy.get("holder_materials")
    if not isinstance(materials, (list, tuple)) or not materials:
        raise ValueError("holder_materials must be a non-empty sequence of names")
    for material in materials:
        if not _require_label("holder material", material):
            raise ValueError("a holder material name must not be blank")
    return policy


def dew_point_c(temperature_c, relative_humidity_percent):
    """Dew point of the chamber air, by the Magnus relation."""
    temperature = _require_number("temperature_c", temperature_c)
    humidity = _require_number(
        "relative_humidity_percent", relative_humidity_percent
    )
    if not 0.0 < humidity <= 100.0:
        raise ValueError(
            "relative_humidity_percent must sit above zero and at or below "
            "saturation, got %r" % (relative_humidity_percent,)
        )
    if temperature <= -MAGNUS_B_C:
        raise ValueError(
            "temperature_c %g is outside the range the relation is written for"
            % temperature
        )
    gamma = math.log(humidity / 100.0) + MAGNUS_A * temperature / (
        MAGNUS_B_C + temperature
    )
    if _at_least(gamma, MAGNUS_A):
        raise ValueError(
            "the temperature and humidity given do not describe moist air"
        )
    return MAGNUS_B_C * gamma / (MAGNUS_A - gamma)


def dew_point_margin_c(
    article_surface_temperature_c, chamber_temperature_c, relative_humidity_percent
):
    """How far the article surface sits above the chamber dew point."""
    surface = _require_number(
        "article_surface_temperature_c", article_surface_temperature_c
    )
    return surface - dew_point_c(chamber_temperature_c, relative_humidity_percent)


def rack_pitch_mm(article_thickness_mm, face_clearance_mm):
    """Slot-to-slot pitch a standing article and its clearance need."""
    thickness = _require_positive("article_thickness_mm", article_thickness_mm)
    clearance = _require_positive("face_clearance_mm", face_clearance_mm)
    return thickness + clearance


def rack_capacity(usable_rack_length_mm, pitch_mm):
    """Whole articles a rack of that length holds at that pitch."""
    length = _require_positive("usable_rack_length_mm", usable_rack_length_mm)
    pitch = _require_positive("pitch_mm", pitch_mm)
    return int(math.floor(length / pitch + _REL_TOL))


def realised_clearance_mm(usable_rack_length_mm, loaded_articles, article_thickness_mm):
    """Clearance a rack actually leaves once that many articles stand in it."""
    length = _require_positive("usable_rack_length_mm", usable_rack_length_mm)
    count = _require_count("loaded_articles", loaded_articles)
    thickness = _require_positive("article_thickness_mm", article_thickness_mm)
    return (length - count * thickness) / count


def masked_face_fraction(holder_contact_area_mm2, face_area_mm2):
    """Fraction of one face the holder covers and the vapour never sees."""
    contact = _require_non_negative(
        "holder_contact_area_mm2", holder_contact_area_mm2
    )
    face = _require_positive("face_area_mm2", face_area_mm2)
    if contact > face:
        raise ValueError(
            "holder_contact_area_mm2 %g exceeds the %g mm2 face it sits on"
            % (contact, face)
        )
    return contact / face


def settled_dwell_hours(total_chamber_hours, ramp_hours):
    """Exposure time at the set point, with the ramp taken back out."""
    total = _require_non_negative("total_chamber_hours", total_chamber_hours)
    ramp = _require_non_negative("ramp_hours", ramp_hours)
    if ramp > total:
        raise ValueError(
            "ramp_hours %g cannot exceed the %g h the articles spent in the "
            "chamber" % (ramp, total)
        )
    return total - ramp


def subgroup_population(articles, designated_subgroup):
    """Split an article inventory into subgroup members and non-members."""
    if not isinstance(articles, (list, tuple)):
        raise ValueError("articles must be a sequence of article records")
    designation = _require_label("designated_subgroup", designated_subgroup)
    members = []
    others = []
    seen = set()
    for article in articles:
        if not isinstance(article, dict):
            raise ValueError("article must be a mapping, got %r" % (article,))
        identifier = _require_label("article id", article.get("id"))
        if not identifier:
            raise ValueError("article id must not be blank")
        if identifier in seen:
            raise ValueError("duplicate article id %r in the inventory" % identifier)
        seen.add(identifier)
        if "subgroup" not in article:
            raise ValueError(
                "article %r records no subgroup; unknown membership is not "
                "membership and cannot be read as non-membership either"
                % identifier
            )
        subgroup = _require_label("article subgroup", article.get("subgroup"))
        if subgroup == designation:
            members.append(article)
        else:
            others.append(article)
    return tuple(members), tuple(others)


def support_exposes_both_faces(support):
    """True when the support holds the article by its edges only."""
    name = _require_label("support", support)
    if name not in RECOGNISED_SUPPORTS:
        raise ValueError(
            "unknown support %r; recognised supports are %s"
            % (support, ", ".join(RECOGNISED_SUPPORTS))
        )
    return name in EDGE_SUPPORTS


def article_holding_findings(article, policy=DEFAULT_HOLDING_POLICY):
    """Everything wrong with how one article is held, in record order."""
    validate_holding_policy(policy)
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    identifier = _require_label("article id", article.get("id"))
    findings = []

    if not support_exposes_both_faces(article.get("support")):
        findings.append(
            "article %s is held on a %s, which shelves a face; the moisture "
            "reaching it is whatever diffused into the gap, not the chamber "
            "condition" % (identifier, _require_label("support", article["support"]))
        )

    material = _require_label("holder_material", article.get("holder_material"))
    if material not in tuple(policy["holder_materials"]):
        findings.append(
            "article %s is held in %s, which is not among the holder materials "
            "the soak is qualified with (%s)"
            % (identifier, material, ", ".join(policy["holder_materials"]))
        )

    fraction = masked_face_fraction(
        article.get("holder_contact_area_mm2"), article.get("face_area_mm2")
    )
    limit = float(policy["max_masked_face_fraction"])
    if not _at_most(fraction, limit):
        findings.append(
            "the holder masks %.1f%% of article %s, above the %.1f%% of a face "
            "that may go unexposed" % (fraction * 100.0, identifier, limit * 100.0)
        )

    clearance = _require_non_negative(
        "face_clearance_mm", article.get("face_clearance_mm")
    )
    min_clearance = float(policy["min_face_clearance_mm"])
    if not _at_least(clearance, min_clearance):
        findings.append(
            "article %s stands %.1f mm from its neighbour, inside the %.1f mm "
            "the vapour needs to circulate" % (identifier, clearance, min_clearance)
        )

    if _require_flag("touching_neighbour", article.get("touching_neighbour")):
        findings.append(
            "article %s touches a neighbour, so the two contact patches are "
            "unexposed on both articles at once" % identifier
        )

    return tuple(findings)


def chamber_findings(chamber, policy=DEFAULT_HOLDING_POLICY):
    """Everything wrong with the chamber condition, in record order."""
    validate_holding_policy(policy)
    if not isinstance(chamber, dict):
        raise ValueError("chamber must be a mapping, got %r" % (chamber,))
    temperature = _require_number("temperature_c", chamber.get("temperature_c"))
    humidity = _require_number(
        "relative_humidity_percent", chamber.get("relative_humidity_percent")
    )
    gauge = _require_number("gauge_pressure_kpa", chamber.get("gauge_pressure_kpa"))
    surface = _require_number(
        "article_surface_temperature_c", chamber.get("article_surface_temperature_c")
    )
    findings = []

    if not _within(
        temperature,
        float(policy["min_chamber_temperature_c"]),
        float(policy["max_chamber_temperature_c"]),
    ):
        findings.append(
            "the %.1f C chamber air is outside the %.1f C to %.1f C the soak is "
            "defined at"
            % (
                temperature,
                float(policy["min_chamber_temperature_c"]),
                float(policy["max_chamber_temperature_c"]),
            )
        )
    if not _within(
        humidity,
        float(policy["min_relative_humidity_percent"]),
        float(policy["max_relative_humidity_percent"]),
    ):
        findings.append(
            "the %.1f%% relative humidity is outside the %.1f%% to %.1f%% band "
            "the soak is defined at"
            % (
                humidity,
                float(policy["min_relative_humidity_percent"]),
                float(policy["max_relative_humidity_percent"]),
            )
        )
    if not _at_most(abs(gauge), float(policy["max_gauge_pressure_kpa"])):
        findings.append(
            "the chamber sits %.2f kPa off the pressure of the room; the soak "
            "is an ambient pressure exposure and a sealed vessel is a different "
            "one" % gauge
        )

    margin = dew_point_margin_c(surface, temperature, humidity)
    min_margin = float(policy["min_dew_point_margin_c"])
    if not _at_least(margin, min_margin):
        findings.append(
            "the article surface sits %.2f C above the %.2f C dew point, inside "
            "the %.2f C margin; below it the soak becomes liquid water on the "
            "coating"
            % (margin, dew_point_c(temperature, humidity), min_margin)
        )
    return margin, tuple(findings)


def assess_coverglass_humidity_holding(case, policy=DEFAULT_HOLDING_POLICY):
    """Full clause 8.7.11.1.2 judgement for one holding arrangement."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_holding_policy(policy)
    if "designated_subgroup" not in case:
        raise ValueError(
            "case is missing designated_subgroup; an absent designation is not "
            "a blank one"
        )
    designation = _require_label("designated_subgroup", case["designated_subgroup"])
    articles = case.get("articles")
    if not isinstance(articles, (list, tuple)):
        raise ValueError("case is missing an articles inventory")
    chamber = case.get("chamber")
    if not isinstance(chamber, dict):
        raise ValueError("case is missing a chamber record")

    findings = []
    result = {
        "designated_subgroup": designation,
        "held_articles": (),
        "excluded_articles": (),
        "dew_point_margin_c": None,
        "settled_dwell_hours": None,
        "findings": findings,
    }

    if not designation:
        findings.append(
            "no subgroup is designated, so there is no population the soak can "
            "be held on"
        )
        result["verdict"] = SUBGROUP_NOT_ESTABLISHED
        return result

    members, others = subgroup_population(articles, designation)
    result["held_articles"] = tuple(article["id"].strip() for article in members)
    result["excluded_articles"] = tuple(article["id"].strip() for article in others)

    if not members:
        findings.append(
            "no article in the inventory carries the %r subgroup; the %d "
            "article(s) present belong elsewhere and holding them proves "
            "nothing about this population" % (designation, len(others))
        )
        result["verdict"] = SUBGROUP_NOT_ESTABLISHED
        return result

    minimum = int(policy["min_subgroup_articles"])
    if len(members) < minimum:
        findings.append(
            "the subgroup holds %d article(s), fewer than the %d the sampling "
            "policy asks for" % (len(members), minimum)
        )
        result["verdict"] = SUBGROUP_NOT_ESTABLISHED
        return result

    holding = []
    for article in members:
        holding.extend(article_holding_findings(article, policy))
    if holding:
        findings.extend(holding)
        result["verdict"] = HOLDING_NOT_ACCEPTABLE
        return result

    margin, chamber_problems = chamber_findings(chamber, policy)
    result["dew_point_margin_c"] = margin
    if chamber_problems:
        findings.extend(chamber_problems)
        result["verdict"] = CHAMBER_CONDITIONS_INVALID
        return result

    dwell = settled_dwell_hours(
        chamber.get("total_chamber_hours"), chamber.get("ramp_hours")
    )
    result["settled_dwell_hours"] = dwell
    required = float(policy["min_dwell_hours"])
    if not _at_least(dwell, required):
        findings.append(
            "the articles held the set point for %.2f h once the %.2f h ramp is "
            "taken back out, short of the %.2f h the soak asks for"
            % (
                dwell,
                _require_non_negative("ramp_hours", chamber.get("ramp_hours")),
                required,
            )
        )
        result["verdict"] = EXPOSURE_INCOMPLETE
        return result

    result["verdict"] = SUBGROUP_EXPOSURE_HELD
    return result
