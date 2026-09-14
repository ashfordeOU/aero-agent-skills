#!/usr/bin/env python3
"""Coverglass reflectance cut-off against the drawing value.

Anchor: ECSS-E-ST-20-08C clause 8.7.5.3.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A filtered coverglass reflects over a band and transmits outside it. The
long-wavelength edge of that band is the cut-off, and this clause makes it
an acceptance quantity: the cut-off that comes out of the measurement is
admissible only when it agrees with the figure the coverglass source
control drawing fixes, inside the tolerance that drawing carries with it.

Two things have to happen before that comparison means anything.

First, the cut-off has to be derived from the measured spectrum rather
than read off it. A reflectance scan is a sampled curve; the edge almost
never lands on a sampled wavelength. The edge is located by taking the
reflecting plateau the band actually reached, forming the crossing level
from it under a declared convention (half of the plateau by default), and
interpolating the wavelength at which the long-wavelength flank falls
through that level. A scan that stopped before the flank reached the level
has not measured a cut-off at all and is refused rather than extrapolated.

Second, the requirement has to exist. A cut-off compared against a
remembered number, a coating datasheet or the last programme is not a
verdict against this clause, so a requirement with no drawing reference
closes the assessment on "not established" instead of passing it.

The population is then worth more than the verdict. Every article is
compared on its own, the deviation and the share of the tolerance band it
consumed are reported, and two advisories are raised that a bare pass
hides: an article-to-article spread that is wide even though everything
is in tolerance, and a set of articles that all sit on the same side of
the drawing value, which is a coating run bias rather than scatter.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# --- verdicts ---------------------------------------------------------------

REQUIREMENT_NOT_ESTABLISHED = "coverglass-cut-off-requirement-not-established"
MEETS_DRAWING = "coverglass-cut-off-meets-drawing"
OUTSIDE_TOLERANCE = "coverglass-cut-off-outside-drawing-tolerance"

CUT_OFF_VERDICTS = (
    REQUIREMENT_NOT_ESTABLISHED,
    MEETS_DRAWING,
    OUTSIDE_TOLERANCE,
)

# --- crossing conventions ---------------------------------------------------

HALF_PLATEAU = "half-plateau"
PLATEAU_FRACTION = "plateau-fraction"
ABSOLUTE_LEVEL = "absolute-level"

CROSSING_CONVENTIONS = (HALF_PLATEAU, PLATEAU_FRACTION, ABSOLUTE_LEVEL)

DEFAULT_CUT_OFF_POLICY = {
    # how the crossing level is formed from the measured band
    "crossing_convention": HALF_PLATEAU,
    "crossing_fraction": 0.5,
    "absolute_crossing_level": 0.5,
    # the contiguous run around the peak counted as the plateau
    "plateau_inclusion_fraction": 0.9,
    # the scan itself
    "min_spectrum_points": 5,
    "min_plateau_reflectance": 0.2,
    # population advisories, in nanometres
    "spread_advisory_nm": 8.0,
    "bias_advisory_nm": 2.0,
    "min_articles_for_bias_advisory": 3,
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


def _require_unit_fraction(name, value, allow_zero=False):
    fraction = _require_non_negative(name, value)
    if not allow_zero and fraction <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    if fraction > 1.0:
        raise ValueError(
            "%s is a fraction of unity and cannot exceed one, got %r" % (name, value)
        )
    return fraction


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

    Every limit here is a drawing figure combined with a tolerance, so a
    measurement sitting exactly on the band edge can evaluate a few units
    in the last place outside it. The tolerance is never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


# --- policy and requirement -------------------------------------------------


def validate_cut_off_policy(policy):
    """Check a cut-off evaluation policy is usable, returning it unchanged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    convention = policy.get("crossing_convention")
    if convention not in CROSSING_CONVENTIONS:
        raise ValueError(
            "policy crossing_convention must be one of %s, got %r"
            % (", ".join(CROSSING_CONVENTIONS), convention)
        )
    _require_unit_fraction("policy crossing_fraction", policy.get("crossing_fraction"))
    _require_unit_fraction(
        "policy absolute_crossing_level", policy.get("absolute_crossing_level")
    )
    _require_unit_fraction(
        "policy plateau_inclusion_fraction", policy.get("plateau_inclusion_fraction")
    )
    _require_unit_fraction(
        "policy min_plateau_reflectance", policy.get("min_plateau_reflectance")
    )
    points = _require_count("policy min_spectrum_points", policy.get("min_spectrum_points"))
    if points < 3:
        raise ValueError(
            "policy min_spectrum_points must be at least three; two points cannot "
            "show a plateau and a flank, got %r" % (points,)
        )
    _require_positive("policy spread_advisory_nm", policy.get("spread_advisory_nm"))
    _require_positive("policy bias_advisory_nm", policy.get("bias_advisory_nm"))
    _require_count(
        "policy min_articles_for_bias_advisory",
        policy.get("min_articles_for_bias_advisory"),
        minimum=2,
    )
    return policy


def validate_drawing_requirement(requirement):
    """Resolve the cut-off figure the source control drawing fixes.

    Returns None when the requirement is absent or carries no drawing
    reference; that is a closing condition for the assessment, not an
    error, because a missing requirement is a real programme state.
    """
    if requirement is None:
        return None
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    reference = requirement.get("drawing_reference")
    if not isinstance(reference, str) or not reference.strip():
        return None
    declared = _require_positive(
        "requirement cut_off_nm", requirement.get("cut_off_nm")
    )
    plus = _require_non_negative(
        "requirement tolerance_plus_nm",
        requirement.get("tolerance_plus_nm", requirement.get("tolerance_nm")),
    )
    minus = _require_non_negative(
        "requirement tolerance_minus_nm",
        requirement.get("tolerance_minus_nm", requirement.get("tolerance_nm")),
    )
    if plus == 0.0 and minus == 0.0:
        raise ValueError(
            "a cut-off requirement with a zero tolerance band on both sides "
            "cannot be met by any real measurement"
        )
    if minus >= declared:
        raise ValueError(
            "a lower tolerance of %g nm on a %g nm cut-off reaches zero "
            "wavelength" % (minus, declared)
        )
    return {
        "drawing_reference": reference.strip(),
        "cut_off_nm": declared,
        "tolerance_plus_nm": plus,
        "tolerance_minus_nm": minus,
        "lower_bound_nm": declared - minus,
        "upper_bound_nm": declared + plus,
    }


# --- spectrum handling ------------------------------------------------------


def normalise_spectrum(spectrum, policy=DEFAULT_CUT_OFF_POLICY):
    """Validate a measured reflectance scan into ordered (nm, R) pairs."""
    validate_cut_off_policy(policy)
    if not isinstance(spectrum, (list, tuple)):
        raise ValueError("spectrum must be a list of samples, got %r" % (spectrum,))
    if len(spectrum) < policy["min_spectrum_points"]:
        raise ValueError(
            "a reflectance scan of %d points cannot resolve a cut-off; the "
            "policy asks for at least %d"
            % (len(spectrum), policy["min_spectrum_points"])
        )
    samples = []
    for index, sample in enumerate(spectrum):
        if isinstance(sample, dict):
            wavelength = sample.get("wavelength_nm")
            reflectance = sample.get("reflectance")
        elif isinstance(sample, (list, tuple)) and len(sample) == 2:
            wavelength, reflectance = sample
        else:
            raise ValueError(
                "spectrum sample %d must be a mapping or a (wavelength_nm, "
                "reflectance) pair, got %r" % (index, sample)
            )
        wavelength = _require_positive("sample %d wavelength_nm" % index, wavelength)
        reflectance = _require_unit_fraction(
            "sample %d reflectance" % index, reflectance, allow_zero=True
        )
        samples.append((wavelength, reflectance))
    for index in range(1, len(samples)):
        if samples[index][0] <= samples[index - 1][0]:
            raise ValueError(
                "spectrum wavelengths must increase strictly; sample %d at "
                "%g nm does not follow sample %d at %g nm"
                % (index, samples[index][0], index - 1, samples[index - 1][0])
            )
    return samples


def plateau_reflectance(samples, policy=DEFAULT_CUT_OFF_POLICY):
    """Reflectance level the reflecting band actually reached.

    The plateau is the contiguous run around the peak whose samples stay
    within the policy inclusion fraction of the peak, averaged. A single
    noisy peak sample therefore does not set the crossing level on its own.
    """
    validate_cut_off_policy(policy)
    if not samples:
        raise ValueError("cannot take a plateau from an empty spectrum")
    peak_index = 0
    peak = samples[0][1]
    for index, (_wavelength, reflectance) in enumerate(samples):
        if reflectance > peak:
            peak = reflectance
            peak_index = index
    if peak < policy["min_plateau_reflectance"]:
        raise ValueError(
            "peak reflectance %.4f never reaches the %.4f the policy needs "
            "to call a reflecting band present"
            % (peak, policy["min_plateau_reflectance"])
        )
    floor = peak * policy["plateau_inclusion_fraction"]
    low = peak_index
    while low > 0 and samples[low - 1][1] >= floor:
        low -= 1
    high = peak_index
    while high + 1 < len(samples) and samples[high + 1][1] >= floor:
        high += 1
    run = samples[low : high + 1]
    mean = sum(reflectance for _w, reflectance in run) / float(len(run))
    return {
        "peak_reflectance": peak,
        "peak_wavelength_nm": samples[peak_index][0],
        "peak_index": peak_index,
        "plateau_reflectance": mean,
        "plateau_first_index": low,
        "plateau_last_index": high,
        "plateau_sample_count": len(run),
    }


def crossing_level(plateau, policy=DEFAULT_CUT_OFF_POLICY):
    """The reflectance level whose long-wavelength crossing is the cut-off."""
    validate_cut_off_policy(policy)
    if not isinstance(plateau, dict):
        raise ValueError("plateau must be the mapping plateau_reflectance returns")
    convention = policy["crossing_convention"]
    if convention == ABSOLUTE_LEVEL:
        level = policy["absolute_crossing_level"]
    elif convention == HALF_PLATEAU:
        level = 0.5 * plateau["plateau_reflectance"]
    else:
        level = policy["crossing_fraction"] * plateau["plateau_reflectance"]
    if not level < plateau["plateau_reflectance"]:
        raise ValueError(
            "a crossing level of %.4f is not below the %.4f plateau, so the "
            "flank never falls through it"
            % (level, plateau["plateau_reflectance"])
        )
    return level


def cut_off_wavelength_nm(spectrum, policy=DEFAULT_CUT_OFF_POLICY):
    """Locate the long-wavelength band edge by linear interpolation."""
    samples = normalise_spectrum(spectrum, policy)
    plateau = plateau_reflectance(samples, policy)
    level = crossing_level(plateau, policy)
    start = plateau["plateau_last_index"]
    for index in range(start + 1, len(samples)):
        if _at_most(samples[index][1], level):
            upper_w, upper_r = samples[index]
            lower_w, lower_r = samples[index - 1]
            if math.isclose(lower_r, upper_r, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
                edge = upper_w
            else:
                share = (lower_r - level) / (lower_r - upper_r)
                edge = lower_w + share * (upper_w - lower_w)
            return {
                "cut_off_nm": edge,
                "crossing_level": level,
                "bracket_low_nm": lower_w,
                "bracket_high_nm": upper_w,
                "plateau_reflectance": plateau["plateau_reflectance"],
                "peak_reflectance": plateau["peak_reflectance"],
                "peak_wavelength_nm": plateau["peak_wavelength_nm"],
            }
    raise ValueError(
        "the scan ends at %g nm with reflectance still above the %.4f "
        "crossing level; the cut-off was never measured"
        % (samples[-1][0], level)
    )


# --- per-article and campaign assessment ------------------------------------


def assess_article_cut_off(article, resolved_requirement, policy=DEFAULT_CUT_OFF_POLICY):
    """Compare one coverglass against the resolved drawing requirement."""
    validate_cut_off_policy(policy)
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    if not isinstance(resolved_requirement, dict):
        raise ValueError(
            "resolved_requirement must be the mapping validate_drawing_requirement "
            "returns, got %r" % (resolved_requirement,)
        )
    article_id = _require_text("article_id", article.get("article_id"))
    if "cut_off_nm" in article and article.get("spectrum") is None:
        measured = _require_positive("article cut_off_nm", article["cut_off_nm"])
        derivation = {"source": "reported", "cut_off_nm": measured}
    else:
        derivation = cut_off_wavelength_nm(article.get("spectrum"), policy)
        derivation["source"] = "spectrum"
        measured = derivation["cut_off_nm"]

    declared = resolved_requirement["cut_off_nm"]
    deviation = measured - declared
    lower = resolved_requirement["lower_bound_nm"]
    upper = resolved_requirement["upper_bound_nm"]
    within = _at_most(lower, measured) and _at_most(measured, upper)
    if deviation >= 0.0:
        allowance = resolved_requirement["tolerance_plus_nm"]
    else:
        allowance = resolved_requirement["tolerance_minus_nm"]
    if allowance > 0.0:
        consumed = abs(deviation) / allowance
    else:
        consumed = float("inf") if deviation != 0.0 else 0.0
    return {
        "article_id": article_id,
        "measured_cut_off_nm": measured,
        "declared_cut_off_nm": declared,
        "deviation_nm": deviation,
        "tolerance_consumed_fraction": consumed,
        "within_tolerance": within,
        "derivation": derivation,
    }


def assess_cut_off_requirement(campaign, policy=DEFAULT_CUT_OFF_POLICY):
    """Clause 8.7.5.3.3 acceptance decision for a coverglass lot."""
    validate_cut_off_policy(policy)
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping, got %r" % (campaign,))
    lot_id = _require_text("lot_id", campaign.get("lot_id"))
    resolved = validate_drawing_requirement(campaign.get("requirement"))
    if resolved is None:
        return {
            "lot_id": lot_id,
            "verdict": REQUIREMENT_NOT_ESTABLISHED,
            "articles": [],
            "findings": [
                "no coverglass source control drawing reference carries a "
                "cut-off value, so there is nothing for the measurement to "
                "be judged against"
            ],
            "advisories": [],
        }

    articles = campaign.get("articles")
    if not isinstance(articles, (list, tuple)) or not articles:
        raise ValueError("campaign articles must be a non-empty list")

    seen = set()
    assessed = []
    for article in articles:
        result = assess_article_cut_off(article, resolved, policy)
        if result["article_id"] in seen:
            raise ValueError(
                "duplicate article_id %r in lot %s" % (result["article_id"], lot_id)
            )
        seen.add(result["article_id"])
        assessed.append(result)

    measured = [result["measured_cut_off_nm"] for result in assessed]
    mean = sum(measured) / float(len(measured))
    spread = max(measured) - min(measured)
    failing = [
        result["article_id"] for result in assessed if not result["within_tolerance"]
    ]

    findings = []
    for result in assessed:
        if not result["within_tolerance"]:
            findings.append(
                "%s measures %.3f nm, %+.3f nm from the %.3f nm drawing value "
                "and outside the %.3f to %.3f nm band"
                % (
                    result["article_id"],
                    result["measured_cut_off_nm"],
                    result["deviation_nm"],
                    resolved["cut_off_nm"],
                    resolved["lower_bound_nm"],
                    resolved["upper_bound_nm"],
                )
            )

    advisories = []
    if spread > policy["spread_advisory_nm"]:
        advisories.append(
            "the lot spans %.3f nm of cut-off between articles, past the "
            "%.3f nm the policy treats as ordinary scatter"
            % (spread, policy["spread_advisory_nm"])
        )
    if len(assessed) >= policy["min_articles_for_bias_advisory"]:
        deviations = [result["deviation_nm"] for result in assessed]
        all_high = all(value > 0.0 for value in deviations)
        all_low = all(value < 0.0 for value in deviations)
        if (all_high or all_low) and abs(mean - resolved["cut_off_nm"]) > policy[
            "bias_advisory_nm"
        ]:
            advisories.append(
                "every article sits on the %s side of the drawing value, mean "
                "offset %+.3f nm; that is a coating run bias rather than "
                "scatter and it belongs with the process, not with this verdict"
                % ("high" if all_high else "low", mean - resolved["cut_off_nm"])
            )

    verdict = OUTSIDE_TOLERANCE if failing else MEETS_DRAWING
    return {
        "lot_id": lot_id,
        "verdict": verdict,
        "drawing_reference": resolved["drawing_reference"],
        "declared_cut_off_nm": resolved["cut_off_nm"],
        "tolerance_band_nm": (resolved["lower_bound_nm"], resolved["upper_bound_nm"]),
        "articles": assessed,
        "mean_cut_off_nm": mean,
        "spread_nm": spread,
        "worst_article_id": max(
            assessed, key=lambda result: abs(result["deviation_nm"])
        )["article_id"],
        "articles_outside_tolerance": failing,
        "findings": findings,
        "advisories": advisories,
    }
