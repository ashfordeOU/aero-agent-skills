#!/usr/bin/env python3
"""Coverglass reflectance bandwidth against the drawing declaration.

Anchor: ECSS-E-ST-20-08C clause 8.7.5.4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The companion definition clause says what the reflectance bandwidth of a
filtered coverglass is: the cut-on to cut-off span divided by the band
centre wavelength. This clause makes that quantity an acceptance
criterion -- the bandwidth that comes out of the measurement is
admissible only when it matches the figure declared in the coverglass
source control drawing, inside the tolerance that declaration carries.

Three things stand between a measured edge pair and that verdict.

The requirement has to exist. A bandwidth compared against a remembered
number, a coating datasheet or the last programme is not a verdict
against this clause, so a declaration with no drawing reference closes
the assessment on "not established" instead of passing it.

The two figures have to be in the same units and on the same convention.
The same quantity is written as a fraction in one document and as a
percentage in the next, and the band centre is either the arithmetic mean
of the edges or their geometric mean -- two different wavelengths, and
therefore two different bandwidth figures, for every band that is not
infinitesimally narrow. Both are normalised explicitly here, and when the
gap between the two conventions is wider than the whole tolerance band,
the verdict depends on which centre the drawing meant, which is reported
rather than resolved by assumption.

The ratio hides one failure completely. Scaling both band edges by the
same factor leaves the bandwidth untouched, so a filter whose whole band
has drifted to longer wavelengths reports exactly the figure the drawing
asks for. When the drawing also declares a nominal centre, that drift is
recovered and reported beside the verdict; the bandwidth criterion itself
is not the place to fail it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# --- verdicts ---------------------------------------------------------------

REQUIREMENT_NOT_ESTABLISHED = "coverglass-bandwidth-requirement-not-established"
MEETS_DRAWING = "coverglass-bandwidth-meets-drawing"
OUTSIDE_TOLERANCE = "coverglass-bandwidth-outside-drawing-tolerance"

BANDWIDTH_VERDICTS = (
    REQUIREMENT_NOT_ESTABLISHED,
    MEETS_DRAWING,
    OUTSIDE_TOLERANCE,
)

# --- conventions and units --------------------------------------------------

ARITHMETIC_CENTRE = "arithmetic-mean"
GEOMETRIC_CENTRE = "geometric-mean"
CENTRE_CONVENTIONS = (ARITHMETIC_CENTRE, GEOMETRIC_CENTRE)

FRACTION_UNIT = "fraction"
PERCENT_UNIT = "percent"
BANDWIDTH_UNITS = (FRACTION_UNIT, PERCENT_UNIT)

# An arithmetic-centre bandwidth reaches two only as the cut-on reaches zero
# wavelength, so a declared fraction at or above two is a unit error.
IMPLAUSIBLE_FRACTION_CEILING = 2.0

DEFAULT_BANDWIDTH_POLICY = {
    # convention used when the drawing does not declare one
    "centre_convention": ARITHMETIC_CENTRE,
    # how far a measured edge pair may sit from a bandwidth reported on the
    # same article before the record is treated as a transcription error
    "statement_relative_tolerance": 1.0e-6,
    # advisories
    "spread_advisory_fraction": 0.01,
    "centre_drift_advisory_nm": 5.0,
    "min_articles_for_spread_advisory": 2,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


# --- validation helpers -----------------------------------------------------


def _is_real(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_real(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_real(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    The bounds here are a drawing figure combined with a tolerance, so a
    measurement sitting exactly on one can evaluate a few units in the
    last place outside it. The tolerance is never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_centre_convention(convention):
    """Return a recognised band-centre convention, or raise."""
    if not isinstance(convention, str):
        raise ValueError("centre convention must be a string, got %r" % (convention,))
    key = convention.strip().lower()
    if key not in CENTRE_CONVENTIONS:
        raise ValueError(
            "unknown band-centre convention %r; expected one of %s"
            % (convention, ", ".join(CENTRE_CONVENTIONS))
        )
    return key


def validate_bandwidth_unit(unit):
    """Return a recognised bandwidth unit, or raise."""
    if not isinstance(unit, str):
        raise ValueError("bandwidth unit must be a string, got %r" % (unit,))
    key = unit.strip().lower()
    if key not in BANDWIDTH_UNITS:
        raise ValueError(
            "unknown bandwidth unit %r; expected one of %s"
            % (unit, ", ".join(BANDWIDTH_UNITS))
        )
    return key


def normalise_bandwidth(value, unit, name="bandwidth"):
    """Turn a bandwidth written in either unit into a fraction."""
    key = validate_bandwidth_unit(unit)
    declared = _require_positive(name, value)
    fraction = declared / 100.0 if key == PERCENT_UNIT else declared
    if key == FRACTION_UNIT and fraction >= IMPLAUSIBLE_FRACTION_CEILING:
        raise ValueError(
            "%s of %g declared as a fraction is at or above the %g ceiling; it "
            "reads as a percentage that lost its unit"
            % (name, fraction, IMPLAUSIBLE_FRACTION_CEILING)
        )
    return fraction


def validate_bandwidth_policy(policy):
    """Check a bandwidth acceptance policy is usable, returning it unchanged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    validate_centre_convention(policy.get("centre_convention"))
    tolerance = policy.get("statement_relative_tolerance")
    if not _is_real(tolerance) or tolerance <= 0.0 or tolerance >= 1.0:
        raise ValueError(
            "policy statement_relative_tolerance must lie between zero and one, "
            "got %r" % (tolerance,)
        )
    _require_positive(
        "policy spread_advisory_fraction", policy.get("spread_advisory_fraction")
    )
    _require_positive(
        "policy centre_drift_advisory_nm", policy.get("centre_drift_advisory_nm")
    )
    _require_count(
        "policy min_articles_for_spread_advisory",
        policy.get("min_articles_for_spread_advisory"),
        minimum=2,
    )
    return policy


# --- the measured quantity --------------------------------------------------


def band_figures(cut_on_nm, cut_off_nm):
    """Span, both band centres and both bandwidth figures for an edge pair."""
    cut_on = _require_positive("cut_on_nm", cut_on_nm)
    cut_off = _require_positive("cut_off_nm", cut_off_nm)
    if cut_off <= cut_on:
        raise ValueError(
            "cut_off_nm %g must lie above cut_on_nm %g; a band of zero or "
            "negative span has no bandwidth" % (cut_off, cut_on)
        )
    span = cut_off - cut_on
    arithmetic_centre = 0.5 * (cut_on + cut_off)
    geometric_centre = math.sqrt(cut_on * cut_off)
    return {
        "cut_on_nm": cut_on,
        "cut_off_nm": cut_off,
        "span_nm": span,
        "arithmetic_centre_nm": arithmetic_centre,
        "geometric_centre_nm": geometric_centre,
        "arithmetic_bandwidth": span / arithmetic_centre,
        "geometric_bandwidth": span / geometric_centre,
    }


def measured_bandwidth(article, convention, policy=DEFAULT_BANDWIDTH_POLICY):
    """Resolve one article into a bandwidth fraction on the given convention.

    An article carrying both an edge pair and a reported bandwidth has to
    be self-consistent: the two are measurements of one filter, and a
    disagreement is a transcription error rather than a finding about the
    hardware.
    """
    validate_bandwidth_policy(policy)
    key = validate_centre_convention(convention)
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    cut_on = article.get("cut_on_nm")
    cut_off = article.get("cut_off_nm")
    reported = article.get("bandwidth")

    if cut_on is not None and cut_off is not None:
        figures = band_figures(cut_on, cut_off)
        fraction = (
            figures["arithmetic_bandwidth"]
            if key == ARITHMETIC_CENTRE
            else figures["geometric_bandwidth"]
        )
        centre = (
            figures["arithmetic_centre_nm"]
            if key == ARITHMETIC_CENTRE
            else figures["geometric_centre_nm"]
        )
        if reported is not None:
            stated = normalise_bandwidth(
                reported,
                article.get("bandwidth_unit", FRACTION_UNIT),
                "reported bandwidth",
            )
            if not math.isclose(
                stated,
                fraction,
                rel_tol=policy["statement_relative_tolerance"],
                abs_tol=_ABS_TOL,
            ):
                raise ValueError(
                    "the reported bandwidth %.6f does not describe the %g to %g "
                    "nm edge pair, which gives %.6f on the %s convention"
                    % (stated, figures["cut_on_nm"], figures["cut_off_nm"], fraction, key)
                )
        return {
            "source": "edges",
            "fractional_bandwidth": fraction,
            "centre_nm": centre,
            "figures": figures,
            "convention_gap": abs(
                figures["geometric_bandwidth"] - figures["arithmetic_bandwidth"]
            ),
        }

    if reported is None:
        raise ValueError(
            "an article needs either a cut_on_nm and cut_off_nm pair or a "
            "reported bandwidth; neither was supplied"
        )
    fraction = normalise_bandwidth(
        reported, article.get("bandwidth_unit", FRACTION_UNIT), "reported bandwidth"
    )
    return {
        "source": "reported",
        "fractional_bandwidth": fraction,
        "centre_nm": None,
        "figures": None,
        "convention_gap": None,
    }


# --- the requirement --------------------------------------------------------


def validate_drawing_requirement(requirement, policy=DEFAULT_BANDWIDTH_POLICY):
    """Resolve the bandwidth the source control drawing declares.

    Returns None when the declaration is absent or carries no drawing
    reference; that is a closing condition for the assessment, not an
    error, because a missing declaration is a real programme state.
    """
    validate_bandwidth_policy(policy)
    if requirement is None:
        return None
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    reference = requirement.get("drawing_reference")
    if not isinstance(reference, str) or not reference.strip():
        return None
    unit = requirement.get("bandwidth_unit", FRACTION_UNIT)
    declared = normalise_bandwidth(
        requirement.get("bandwidth"), unit, "requirement bandwidth"
    )
    unit_key = validate_bandwidth_unit(unit)
    scale = 100.0 if unit_key == PERCENT_UNIT else 1.0
    plus = (
        _require_non_negative(
            "requirement tolerance_plus",
            requirement.get("tolerance_plus", requirement.get("tolerance")),
        )
        / scale
    )
    minus = (
        _require_non_negative(
            "requirement tolerance_minus",
            requirement.get("tolerance_minus", requirement.get("tolerance")),
        )
        / scale
    )
    if plus == 0.0 and minus == 0.0:
        raise ValueError(
            "a bandwidth declaration with a zero tolerance band on both sides "
            "cannot be met by any real measurement"
        )
    if minus >= declared:
        raise ValueError(
            "a lower tolerance of %g on a declared bandwidth of %g reaches zero "
            "bandwidth" % (minus, declared)
        )
    convention = requirement.get("centre_convention", policy["centre_convention"])
    centre = requirement.get("centre_nm")
    if centre is not None:
        centre = _require_positive("requirement centre_nm", centre)
    return {
        "drawing_reference": reference.strip(),
        "bandwidth_fraction": declared,
        "declared_unit": unit_key,
        "tolerance_plus": plus,
        "tolerance_minus": minus,
        "lower_bound": declared - minus,
        "upper_bound": declared + plus,
        "centre_convention": validate_centre_convention(convention),
        "centre_nm": centre,
    }


def assess_article_bandwidth(article, resolved_requirement, policy=DEFAULT_BANDWIDTH_POLICY):
    """Compare one coverglass bandwidth against the drawing declaration."""
    validate_bandwidth_policy(policy)
    if not isinstance(resolved_requirement, dict):
        raise ValueError(
            "resolved_requirement must be the mapping validate_drawing_requirement "
            "returns, got %r" % (resolved_requirement,)
        )
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    article_id = _require_text("article_id", article.get("article_id"))
    resolved = measured_bandwidth(
        article, resolved_requirement["centre_convention"], policy
    )
    measured = resolved["fractional_bandwidth"]
    declared = resolved_requirement["bandwidth_fraction"]
    deviation = measured - declared
    within = _at_most(resolved_requirement["lower_bound"], measured) and _at_most(
        measured, resolved_requirement["upper_bound"]
    )
    allowance = (
        resolved_requirement["tolerance_plus"]
        if deviation >= 0.0
        else resolved_requirement["tolerance_minus"]
    )
    if allowance > 0.0:
        consumed = abs(deviation) / allowance
    else:
        consumed = float("inf") if deviation != 0.0 else 0.0
    return {
        "article_id": article_id,
        "measured_bandwidth": measured,
        "measured_percent": 100.0 * measured,
        "declared_bandwidth": declared,
        "deviation": deviation,
        "tolerance_consumed_fraction": consumed,
        "within_tolerance": within,
        "centre_nm": resolved["centre_nm"],
        "convention_gap": resolved["convention_gap"],
        "source": resolved["source"],
    }


def assess_bandwidth_requirement(lot, policy=DEFAULT_BANDWIDTH_POLICY):
    """Clause 8.7.5.4.2 acceptance decision for a coverglass lot."""
    validate_bandwidth_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))
    resolved = validate_drawing_requirement(lot.get("requirement"), policy)
    if resolved is None:
        return {
            "lot_id": lot_id,
            "verdict": REQUIREMENT_NOT_ESTABLISHED,
            "articles": [],
            "findings": [
                "no coverglass source control drawing reference declares a "
                "reflectance bandwidth, so there is nothing for the measured "
                "figure to be matched against"
            ],
            "advisories": [],
        }

    articles = lot.get("articles")
    if not isinstance(articles, (list, tuple)) or not articles:
        raise ValueError("lot articles must be a non-empty list")

    seen = set()
    assessed = []
    for article in articles:
        result = assess_article_bandwidth(article, resolved, policy)
        if result["article_id"] in seen:
            raise ValueError(
                "duplicate article_id %r in lot %s" % (result["article_id"], lot_id)
            )
        seen.add(result["article_id"])
        assessed.append(result)

    measured = [result["measured_bandwidth"] for result in assessed]
    mean = sum(measured) / float(len(measured))
    spread = max(measured) - min(measured)
    failing = [
        result["article_id"] for result in assessed if not result["within_tolerance"]
    ]

    findings = []
    for result in assessed:
        if not result["within_tolerance"]:
            findings.append(
                "%s measures a bandwidth of %.5f, %+.5f from the %.5f the "
                "drawing declares and outside the %.5f to %.5f band"
                % (
                    result["article_id"],
                    result["measured_bandwidth"],
                    result["deviation"],
                    resolved["bandwidth_fraction"],
                    resolved["lower_bound"],
                    resolved["upper_bound"],
                )
            )

    advisories = []
    band_width = resolved["tolerance_plus"] + resolved["tolerance_minus"]
    sensitive = [
        result["article_id"]
        for result in assessed
        if result["convention_gap"] is not None and result["convention_gap"] > band_width
    ]
    if sensitive:
        advisories.append(
            "on %s the two band-centre conventions differ by more than the whole "
            "tolerance band, so this verdict rests on the drawing meaning the %s "
            "centre" % (", ".join(sensitive), resolved["centre_convention"])
        )

    centres = [
        result["centre_nm"] for result in assessed if result["centre_nm"] is not None
    ]
    if resolved["centre_nm"] is not None and centres:
        mean_centre = sum(centres) / float(len(centres))
        drift = mean_centre - resolved["centre_nm"]
        if abs(drift) > policy["centre_drift_advisory_nm"]:
            advisories.append(
                "the measured band centre averages %.3f nm against the %.3f nm "
                "the drawing declares, a drift of %+.3f nm that the bandwidth "
                "ratio cancels and cannot show"
                % (mean_centre, resolved["centre_nm"], drift)
            )
    else:
        mean_centre = sum(centres) / float(len(centres)) if centres else None

    if (
        len(assessed) >= policy["min_articles_for_spread_advisory"]
        and spread > policy["spread_advisory_fraction"]
    ):
        advisories.append(
            "the lot spans %.5f of bandwidth between articles, past the %.5f the "
            "policy treats as ordinary scatter"
            % (spread, policy["spread_advisory_fraction"])
        )

    verdict = OUTSIDE_TOLERANCE if failing else MEETS_DRAWING
    return {
        "lot_id": lot_id,
        "verdict": verdict,
        "drawing_reference": resolved["drawing_reference"],
        "declared_bandwidth": resolved["bandwidth_fraction"],
        "declared_unit": resolved["declared_unit"],
        "centre_convention": resolved["centre_convention"],
        "tolerance_band": (resolved["lower_bound"], resolved["upper_bound"]),
        "articles": assessed,
        "mean_bandwidth": mean,
        "spread": spread,
        "mean_centre_nm": mean_centre,
        "worst_article_id": max(
            assessed, key=lambda result: abs(result["deviation"])
        )["article_id"],
        "articles_outside_tolerance": failing,
        "findings": findings,
        "advisories": advisories,
    }
