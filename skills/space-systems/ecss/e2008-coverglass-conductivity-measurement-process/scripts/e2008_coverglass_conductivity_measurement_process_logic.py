#!/usr/bin/env python3
"""Surface conductivity measurement on the designated qualification subgroup.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.13.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause names two things at once, and a campaign that gets either
wrong produces a number nobody can use.

The first is population. The measurement is made on the coverglasses
belonging to one designated qualification subgroup, not on whichever
articles happened to be on the bench. An article whose subgroup is not
recorded is not a member -- unknown membership is not membership -- and
a reading taken on a non-member does not count toward the population
however carefully it was taken.

The second is method. A surface conductivity is not measured directly;
a voltage and a current are measured and a geometry factor turns them
into a sheet resistance, whose reciprocal is the quantity wanted:

    four-point collinear probe   sheet resistance = (pi / ln 2) * V / I
    concentric ring electrodes   sheet resistance =
                                 2 * pi * (V / I) / ln(r_outer / r_inner)

Both are electrometer measurements on a coating whose resistance is
large, so two conditions travel with them. The drive current has to sit
inside a band -- below the floor it is lost in the electrometer, above
the ceiling it heats and can damage a thin coating. And the ambient has
to sit inside a declared band, because adsorbed moisture conducts:
the same coverglass reads differently at twenty per cent relative
humidity and at eighty.

The bands and the population minima below are a declared policy, not a
physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FOUR_POINT_COLLINEAR = "four-point-collinear-probe"
CONCENTRIC_RING = "concentric-ring-electrode"

RECOGNISED_METHODS = (CONCENTRIC_RING, FOUR_POINT_COLLINEAR)

SUBGROUP_NOT_ESTABLISHED = "qualification-subgroup-not-established"
POPULATION_INCOMPLETE = "subgroup-population-incomplete"
MEASUREMENT_INVALID = "measurement-conditions-invalid"
SUBGROUP_CONDUCTIVITY_MEASURED = "subgroup-conductivity-measured"

DEFAULT_MEASUREMENT_POLICY = {
    "min_subgroup_articles": 3,
    "min_sites_per_article": 5,
    "min_probe_current_a": 1.0e-12,
    "max_probe_current_a": 1.0e-6,
    "min_relative_humidity_percent": 20.0,
    "max_relative_humidity_percent": 50.0,
    "min_temperature_c": 18.0,
    "max_temperature_c": 28.0,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
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


def _within(value, low, high):
    return _at_least(value, low) and _at_most(value, high)


def _require_band(policy, low_key, high_key):
    low = _require_number(low_key, policy.get(low_key))
    high = _require_number(high_key, policy.get(high_key))
    if high <= low:
        raise ValueError("%s %g must be above %s %g" % (high_key, high, low_key, low))
    return low, high


def validate_measurement_policy(policy):
    """Check a subgroup measurement policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("min_subgroup_articles", policy.get("min_subgroup_articles"))
    _require_count("min_sites_per_article", policy.get("min_sites_per_article"))
    low, _ = _require_band(policy, "min_probe_current_a", "max_probe_current_a")
    if low <= 0.0:
        raise ValueError("min_probe_current_a must be greater than zero, got %g" % low)
    _require_band(
        policy, "min_relative_humidity_percent", "max_relative_humidity_percent"
    )
    _require_band(policy, "min_temperature_c", "max_temperature_c")
    return policy


def sheet_resistance_four_point(voltage_v, current_a):
    """Sheet resistance from an equally spaced collinear four-point probe."""
    voltage = _require_positive("voltage_v", voltage_v)
    current = _require_positive("current_a", current_a)
    return (math.pi / math.log(2.0)) * voltage / current


def sheet_resistance_concentric_ring(
    voltage_v, current_a, inner_radius_m, outer_radius_m
):
    """Sheet resistance from a guarded concentric ring electrode pair."""
    voltage = _require_positive("voltage_v", voltage_v)
    current = _require_positive("current_a", current_a)
    inner = _require_positive("inner_radius_m", inner_radius_m)
    outer = _require_positive("outer_radius_m", outer_radius_m)
    if outer <= inner:
        raise ValueError(
            "outer_radius_m %g must be above inner_radius_m %g" % (outer, inner)
        )
    return 2.0 * math.pi * (voltage / current) / math.log(outer / inner)


def surface_conductivity_s_per_square(sheet_resistance_ohm_per_sq):
    """Surface conductivity: the reciprocal of the sheet resistance."""
    resistance = _require_positive(
        "sheet_resistance_ohm_per_sq", sheet_resistance_ohm_per_sq
    )
    return 1.0 / resistance


def site_sheet_resistance(method, reading):
    """Sheet resistance at one probe site, by the method that produced it."""
    name = _require_label("method", method)
    if name not in RECOGNISED_METHODS:
        raise ValueError(
            "unknown measurement method %r; recognised methods are %s"
            % (method, ", ".join(RECOGNISED_METHODS))
        )
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping, got %r" % (reading,))
    if name == FOUR_POINT_COLLINEAR:
        return sheet_resistance_four_point(
            reading.get("voltage_v"), reading.get("current_a")
        )
    return sheet_resistance_concentric_ring(
        reading.get("voltage_v"),
        reading.get("current_a"),
        reading.get("inner_radius_m"),
        reading.get("outer_radius_m"),
    )


def site_surface_conductivity(method, reading):
    """Surface conductivity at one probe site."""
    return surface_conductivity_s_per_square(site_sheet_resistance(method, reading))


def probe_current_within_band(current_a, policy=DEFAULT_MEASUREMENT_POLICY):
    """True when the drive current is readable without heating the coating."""
    validate_measurement_policy(policy)
    current = _require_positive("current_a", current_a)
    return _within(
        current,
        float(policy["min_probe_current_a"]),
        float(policy["max_probe_current_a"]),
    )


def environment_within_band(environment, policy=DEFAULT_MEASUREMENT_POLICY):
    """Check the ambient the readings were taken in against the declared band.

    Adsorbed moisture conducts, so a surface conductivity carries the
    humidity it was measured at whether or not the record says so.
    """
    validate_measurement_policy(policy)
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping, got %r" % (environment,))
    humidity = _require_number(
        "relative_humidity_percent", environment.get("relative_humidity_percent")
    )
    temperature = _require_number(
        "temperature_c", environment.get("temperature_c")
    )
    findings = []
    if not _within(
        humidity,
        float(policy["min_relative_humidity_percent"]),
        float(policy["max_relative_humidity_percent"]),
    ):
        findings.append(
            "the %.1f%% relative humidity is outside the %.1f%% to %.1f%% band "
            "the readings are comparable in"
            % (
                humidity,
                float(policy["min_relative_humidity_percent"]),
                float(policy["max_relative_humidity_percent"]),
            )
        )
    if not _within(
        temperature,
        float(policy["min_temperature_c"]),
        float(policy["max_temperature_c"]),
    ):
        findings.append(
            "the %.1f C ambient is outside the %.1f C to %.1f C band the "
            "readings are comparable in"
            % (
                temperature,
                float(policy["min_temperature_c"]),
                float(policy["max_temperature_c"]),
            )
        )
    return (not findings), tuple(findings)


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


def article_site_conductivities(article):
    """Surface conductivity at every site of one article, in record order."""
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    method = article.get("method")
    sites = article.get("sites")
    if not isinstance(sites, (list, tuple)):
        raise ValueError("article sites must be a sequence of site readings")
    if not sites:
        raise ValueError("article %r records no sites" % article.get("id"))
    values = []
    seen = set()
    for site in sites:
        if not isinstance(site, dict):
            raise ValueError("site must be a mapping, got %r" % (site,))
        identifier = _require_label("site id", site.get("id"))
        if identifier in seen:
            raise ValueError("duplicate site id %r on one article" % identifier)
        seen.add(identifier)
        values.append(site_surface_conductivity(method, site))
    return tuple(values)


def article_mean_conductivity_s_per_square(article):
    """Mean surface conductivity over the sites of one article."""
    values = article_site_conductivities(article)
    return sum(values) / len(values)


def assess_coverglass_conductivity_measurement(
    case, policy=DEFAULT_MEASUREMENT_POLICY
):
    """Full clause 6.4.3.13.2 judgement for one subgroup measurement run."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_measurement_policy(policy)
    if "designated_subgroup" not in case:
        raise ValueError(
            "case is missing designated_subgroup; an absent designation is not "
            "a blank one"
        )
    designation = _require_label("designated_subgroup", case["designated_subgroup"])
    articles = case.get("articles")
    if not isinstance(articles, (list, tuple)):
        raise ValueError("case is missing an articles inventory")

    findings = []
    result = {
        "designated_subgroup": designation,
        "measured_articles": (),
        "excluded_articles": (),
        "article_means_s_per_square": {},
        "subgroup_average_s_per_square": None,
        "site_count": 0,
        "probe_currents_within_band": None,
        "environment_representative": None,
        "findings": findings,
    }

    if not designation:
        findings.append(
            "no qualification subgroup is designated, so there is no population "
            "the measurement can be made on"
        )
        result["verdict"] = SUBGROUP_NOT_ESTABLISHED
        return result

    members, others = subgroup_population(articles, designation)
    result["excluded_articles"] = tuple(article["id"].strip() for article in others)
    result["measured_articles"] = tuple(
        article["id"].strip() for article in members
    )

    if not members:
        findings.append(
            "no article in the inventory carries the %r subgroup; the %d "
            "article(s) present belong elsewhere and their readings do not "
            "count toward this population" % (designation, len(others))
        )
        result["verdict"] = SUBGROUP_NOT_ESTABLISHED
        return result

    min_articles = int(policy["min_subgroup_articles"])
    min_sites = int(policy["min_sites_per_article"])
    short_articles = []
    total_sites = 0
    for article in members:
        sites = article.get("sites")
        count = len(sites) if isinstance(sites, (list, tuple)) else 0
        total_sites += count
        if count < min_sites:
            short_articles.append((article["id"].strip(), count))
    result["site_count"] = total_sites

    if len(members) < min_articles or short_articles:
        if len(members) < min_articles:
            findings.append(
                "the subgroup holds %d measured article(s), fewer than the %d "
                "the sampling policy asks for" % (len(members), min_articles)
            )
        for identifier, count in short_articles:
            findings.append(
                "article %s carries %d site(s), fewer than the %d sites per "
                "article the sampling policy asks for"
                % (identifier, count, min_sites)
            )
        result["verdict"] = POPULATION_INCOMPLETE
        return result

    article_means = {}
    currents_ok = True
    for article in members:
        identifier = article["id"].strip()
        article_means[identifier] = article_mean_conductivity_s_per_square(article)
        for site in article["sites"]:
            current = _require_positive("site current_a", site.get("current_a"))
            if not _within(
                current,
                float(policy["min_probe_current_a"]),
                float(policy["max_probe_current_a"]),
            ):
                currents_ok = False
                findings.append(
                    "site %s on article %s was driven at %.4g A, outside the "
                    "%.4g A to %.4g A the electrometer reads without heating "
                    "the coating"
                    % (
                        _require_label("site id", site.get("id")),
                        identifier,
                        current,
                        float(policy["min_probe_current_a"]),
                        float(policy["max_probe_current_a"]),
                    )
                )

    result["article_means_s_per_square"] = article_means
    # Equal weight per article: an over-sampled coverglass must not carry the
    # subgroup figure on its own.
    result["subgroup_average_s_per_square"] = sum(article_means.values()) / len(
        article_means
    )
    result["probe_currents_within_band"] = currents_ok

    environment = case.get("environment")
    if environment is None:
        raise ValueError(
            "case is missing an environment block; a surface conductivity "
            "carries the ambient it was measured in"
        )
    env_ok, env_findings = environment_within_band(environment, policy)
    result["environment_representative"] = env_ok
    findings.extend(env_findings)

    result["verdict"] = (
        SUBGROUP_CONDUCTIVITY_MEASURED
        if currents_ok and env_ok
        else MEASUREMENT_INVALID
    )
    return result
