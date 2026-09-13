#!/usr/bin/env python3
"""Acceptance criterion for conductive coverglass surface conductivity.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.13.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The criterion is narrow and worth stating exactly: the average surface
conductivity of the measured coverglasses has to reach the value fixed
in the cell assembly control drawing. Three things follow from that
sentence and each one is a way campaigns get it wrong.

The value comes from the drawing. It is not a house rule, not the
coating vendor's datasheet figure and not the number the last programme
used. A verdict quoted without the drawing reference behind it is not a
verdict against this clause at all, so an unreferenced requirement
closes the assessment rather than passing it.

The quantity is an average, and an average needs a weighting. Sites are
averaged within an article and articles are then averaged with equal
weight, so a coverglass that happened to receive forty probe sites
cannot carry the subgroup figure while the others contribute a
correction.

The sense is a floor. Surface conductivity is wanted high -- it is the
inverse of the sheet resistance the charge has to run through -- so the
drawing value is a minimum and an average landing exactly on it is
admissible.

One thing the criterion deliberately does not do is judge uniformity.
An average can clear the drawing value while a single site on one
article is effectively dead, and that is a real finding about the
coating; it is reported beside the verdict as an advisory and taken to
the survey clause, not silently folded into a pass or a fail here.

The site floor fraction below is a declared policy, not a physical
constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PER_ARTICLE = "per-article"
PER_SITE = "per-site"

RECOGNISED_WEIGHTINGS = (PER_ARTICLE, PER_SITE)

REQUIREMENT_NOT_ESTABLISHED = "drawing-requirement-not-established"
AVERAGE_BELOW_DRAWING_VALUE = "average-below-drawing-value"
AVERAGE_MEETS_DRAWING_VALUE = "average-meets-drawing-value"

DEFAULT_ACCEPTANCE_POLICY = {
    "site_floor_fraction": 0.1,
    "weighting": PER_ARTICLE,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-18


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
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_acceptance_policy(policy):
    """Check an acceptance policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fraction = _require_positive(
        "site_floor_fraction", policy.get("site_floor_fraction")
    )
    if fraction > 1.0:
        raise ValueError(
            "site_floor_fraction %g is above one; a site floor above the "
            "drawing value would fail every article that meets it" % fraction
        )
    weighting = _require_label("weighting", policy.get("weighting"))
    if weighting not in RECOGNISED_WEIGHTINGS:
        raise ValueError(
            "unknown weighting %r; recognised weightings are %s"
            % (weighting, ", ".join(RECOGNISED_WEIGHTINGS))
        )
    return policy


def validate_drawing_requirement(requirement):
    """Check the drawing-fixed requirement can be judged against."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    reference = _require_label(
        "drawing_reference", requirement.get("drawing_reference")
    )
    value = _require_positive(
        "required_surface_conductivity_s_per_square",
        requirement.get("required_surface_conductivity_s_per_square"),
    )
    return reference, value


def article_site_values(article):
    """The site conductivities recorded for one article, in record order."""
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    identifier = _require_label("article id", article.get("id"))
    if not identifier:
        raise ValueError("article id must not be blank")
    values = article.get("site_conductivities_s_per_square")
    if not isinstance(values, (list, tuple)):
        raise ValueError(
            "article %s must record site_conductivities_s_per_square as a "
            "sequence" % identifier
        )
    if not values:
        raise ValueError(
            "article %s records no site conductivity; an empty article cannot "
            "contribute to an average" % identifier
        )
    return identifier, tuple(
        _require_positive("site conductivity on %s" % identifier, value)
        for value in values
    )


def article_mean_conductivity_s_per_square(article):
    """Mean surface conductivity over the sites of one article."""
    _identifier, values = article_site_values(article)
    return sum(values) / len(values)


def article_means(articles):
    """Mean conductivity per article, keyed by article identifier."""
    if not isinstance(articles, (list, tuple)):
        raise ValueError("articles must be a sequence of article records")
    if not articles:
        raise ValueError("no article was measured, so there is no average to judge")
    means = {}
    for article in articles:
        identifier, values = article_site_values(article)
        if identifier in means:
            raise ValueError("duplicate article id %r in the record" % identifier)
        means[identifier] = sum(values) / len(values)
    return means


def average_surface_conductivity_s_per_square(articles, weighting=PER_ARTICLE):
    """Average surface conductivity of the measured coverglasses."""
    name = _require_label("weighting", weighting)
    if name not in RECOGNISED_WEIGHTINGS:
        raise ValueError(
            "unknown weighting %r; recognised weightings are %s"
            % (weighting, ", ".join(RECOGNISED_WEIGHTINGS))
        )
    if name == PER_ARTICLE:
        means = article_means(articles)
        return sum(means.values()) / len(means)
    if not isinstance(articles, (list, tuple)) or not articles:
        raise ValueError("articles must be a non-empty sequence of article records")
    total = 0.0
    count = 0
    for article in articles:
        _identifier, values = article_site_values(article)
        total += sum(values)
        count += len(values)
    return total / count


def margin_fraction(average_s_per_square, required_s_per_square):
    """How far the average stands above the drawing value, as a fraction."""
    average = _require_positive("average_s_per_square", average_s_per_square)
    required = _require_positive("required_s_per_square", required_s_per_square)
    return average / required - 1.0


def meets_drawing_value(average_s_per_square, required_s_per_square):
    """True when the average reaches the drawing value; a tie is admissible."""
    average = _require_positive("average_s_per_square", average_s_per_square)
    required = _require_positive("required_s_per_square", required_s_per_square)
    return _at_least(average, required)


def dead_site_advisories(
    articles, required_s_per_square, policy=DEFAULT_ACCEPTANCE_POLICY
):
    """Name sites so far below the drawing value that the coating is not bleeding.

    These do not move the verdict -- the criterion of this clause is the
    average -- but a coating with a dead patch is a real finding and it
    must not disappear behind an average that clears the value.
    """
    validate_acceptance_policy(policy)
    required = _require_positive("required_s_per_square", required_s_per_square)
    floor = required * float(policy["site_floor_fraction"])
    advisories = []
    if not isinstance(articles, (list, tuple)):
        raise ValueError("articles must be a sequence of article records")
    for article in articles:
        identifier, values = article_site_values(article)
        for index, value in enumerate(values, start=1):
            if not _at_least(value, floor):
                advisories.append(
                    "site %d on article %s reads %.4g S per square, below the "
                    "%.4g S per square floor; the average can still clear the "
                    "drawing value over a patch that is not bleeding charge"
                    % (index, identifier, value, floor)
                )
    return tuple(advisories)


def assess_coverglass_conductivity_criteria(case, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Full clause 6.4.3.13.3 acceptance decision for one measured subgroup."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_acceptance_policy(policy)

    findings = []
    advisories = []
    result = {
        "drawing_reference": None,
        "required_surface_conductivity_s_per_square": None,
        "weighting": _require_label("weighting", policy["weighting"]),
        "article_means_s_per_square": {},
        "average_surface_conductivity_s_per_square": None,
        "margin_fraction": None,
        "worst_site_s_per_square": None,
        "best_site_s_per_square": None,
        "site_spread_ratio": None,
        "findings": findings,
        "advisories": advisories,
    }

    requirement = case.get("drawing_requirement")
    if requirement is None:
        findings.append(
            "no cell assembly control drawing value is referenced, so there is "
            "nothing this average can be judged against"
        )
        result["verdict"] = REQUIREMENT_NOT_ESTABLISHED
        return result
    reference, required = validate_drawing_requirement(requirement)
    result["drawing_reference"] = reference
    result["required_surface_conductivity_s_per_square"] = required
    if not reference:
        findings.append(
            "the requirement carries no drawing reference; a conductivity value "
            "with no drawing behind it is not the criterion of this clause"
        )
        result["verdict"] = REQUIREMENT_NOT_ESTABLISHED
        return result

    articles = case.get("articles")
    if not isinstance(articles, (list, tuple)):
        raise ValueError("case is missing an articles record")

    means = article_means(articles)
    average = average_surface_conductivity_s_per_square(
        articles, result["weighting"]
    )
    every_site = []
    for article in articles:
        _identifier, values = article_site_values(article)
        every_site.extend(values)

    result["article_means_s_per_square"] = means
    result["average_surface_conductivity_s_per_square"] = average
    result["margin_fraction"] = margin_fraction(average, required)
    result["worst_site_s_per_square"] = min(every_site)
    result["best_site_s_per_square"] = max(every_site)
    result["site_spread_ratio"] = max(every_site) / min(every_site)

    advisories.extend(dead_site_advisories(articles, required, policy))

    if meets_drawing_value(average, required):
        result["verdict"] = AVERAGE_MEETS_DRAWING_VALUE
        return result

    findings.append(
        "the %.4g S per square average is below the %.4g S per square fixed in "
        "drawing %s, short by %.1f per cent"
        % (average, required, reference, abs(result["margin_fraction"]) * 100.0)
    )
    result["verdict"] = AVERAGE_BELOW_DRAWING_VALUE
    return result
