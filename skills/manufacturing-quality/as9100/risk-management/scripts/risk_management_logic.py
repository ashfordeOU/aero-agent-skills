"""AS9100D operational risk assessment and mitigation planning math.

Deterministic, offline, stdlib-only helpers for aerospace quality
risk management: failure-mode risk priority numbers (RPN = severity *
likelihood * detection per the FMEA convention), RPN classification
bands, post-mitigation RPN with reduction credits, risk reduction
fraction, occurrence probability from production history, residual
risk acceptance checks, a 5x5 severity-likelihood risk matrix
classification, and deterministic risk ranking for mitigation
priority. All scores are unitless ratings on the FMEA 1-10 scales
(severity, likelihood, detection) or the 1-5 risk-matrix scales.

Worked anchor examples (checked at authoring time):
- risk_priority_number(8, 5, 3) == 120
- mitigated_risk_priority_number(8, 5, 3, 2, 3, 1) == 24
- risk_reduction_fraction(120, 24) == 0.8
- occurrence_probability(3, 10000) == 3e-4
- risk_matrix_classification(4, 4) == "high"
- rank_risks([("A", 50), ("B", 120), ("C", 20)]) == ["B", "A", "C"]

Contract exercised by scripts/test_risk_management.py.
"""

import math

RPN_LOW_DEFAULT = 40
RPN_HIGH_DEFAULT = 100


def _check_rating_1_10(value, name):
    if not isinstance(value, int) or not 1 <= value <= 10:
        raise ValueError("%s must be an integer in 1-10, got %r" % (name, value))


def risk_priority_number(severity, likelihood, detection):
    """Return the FMEA risk priority number: RPN = S * L * D.

    The classic FMEA risk score multiplies the severity, likelihood
    (occurrence), and detection ratings, each on a 1-10 scale. Higher
    RPN means higher priority for mitigation planning; the scale is
    nonlinear, so equal RPN steps are not equal risk steps.

    Anchor: risk_priority_number(8, 5, 3) == 120;
    risk_priority_number(6, 2, 2) == 24.

    Raises ValueError unless each rating is an integer in 1-10.
    """
    _check_rating_1_10(severity, "severity")
    _check_rating_1_10(likelihood, "likelihood")
    _check_rating_1_10(detection, "detection")
    return severity * likelihood * detection


def risk_priority_classification(rpn, low_threshold=RPN_LOW_DEFAULT, high_threshold=RPN_HIGH_DEFAULT):
    """Return the RPN band as "low", "medium", or "high".

    Classification bands: rpn below low_threshold is "low", at or
    above high_threshold is "high", otherwise "medium". Defaults are
    the common FMEA bands 40 and 100.

    Anchors: risk_priority_classification(25) == "low";
    risk_priority_classification(60) == "medium";
    risk_priority_classification(120) == "high";
    risk_priority_classification(100) == "high" (boundary inclusive).

    Raises ValueError for a negative rpn or inconsistent thresholds
    (high_threshold must exceed low_threshold).
    """
    if rpn < 0:
        raise ValueError("rpn must be >= 0, got %r" % (rpn,))
    if high_threshold <= low_threshold:
        raise ValueError(
            "high_threshold %r must exceed low_threshold %r"
            % (high_threshold, low_threshold)
        )
    if rpn < low_threshold:
        return "low"
    if rpn >= high_threshold:
        return "high"
    return "medium"


def mitigated_risk_priority_number(
    severity, likelihood, detection,
    severity_reduction, likelihood_reduction, detection_reduction,
):
    """Return the post-mitigation RPN after reduction credits.

    Each mitigation action lowers the severity, likelihood, or
    detection rating; the residual RPN is the product of the reduced
    ratings: RPN_after = (S - dS) * (L - dL) * (D - dD). Re-scoring
    after mitigation is mandatory for AS9100D 8.1.1 close-out so the
    residual risk is demonstrated, not assumed.

    Anchor: mitigated_risk_priority_number(8, 5, 3, 2, 3, 1) == 24
    (6 * 2 * 2).

    Raises ValueError unless each rating is an integer in 1-10 and
    each reduction is a non-negative integer no larger than its
    rating.
    """
    _check_rating_1_10(severity, "severity")
    _check_rating_1_10(likelihood, "likelihood")
    _check_rating_1_10(detection, "detection")
    pairs = [
        (severity_reduction, severity, "severity reduction"),
        (likelihood_reduction, likelihood, "likelihood reduction"),
        (detection_reduction, detection, "detection reduction"),
    ]
    for reduction, rating, name in pairs:
        if not isinstance(reduction, int) or not 0 <= reduction <= rating:
            raise ValueError(
                "%s must be an integer in 0-%d, got %r" % (name, rating, reduction)
            )
    return (
        (severity - severity_reduction)
        * (likelihood - likelihood_reduction)
        * (detection - detection_reduction)
    )


def risk_reduction_fraction(before_rpn, after_rpn):
    """Return the fractional risk reduction: (before - after) / before.

    Fraction of the original RPN removed by the mitigation plan. A
    reduction from 120 to 24 is 0.8 (80%). A residual at or above the
    original is 0.0 or negative, signaling an ineffective plan.

    Anchor: risk_reduction_fraction(120, 24) == 0.8.

    Raises ValueError for a non-positive before_rpn or a negative
    after_rpn (an after value above before is allowed and returns a
    negative fraction, flagging an ineffective plan).
    """
    if before_rpn <= 0:
        raise ValueError("before rpn must be > 0, got %r" % (before_rpn,))
    if after_rpn < 0:
        raise ValueError("after rpn must be >= 0, got %r" % (after_rpn,))
    return (before_rpn - after_rpn) / before_rpn


def occurrence_probability(occurrences, units_produced):
    """Return the historical occurrence probability: occurrences / units.

    Frequency of a failure mode in the production history, used to
    ground the likelihood rating instead of guessing. Expresses the
    per-unit probability of the risk event.

    Anchor: occurrence_probability(3, 10000) == 3e-4.

    Raises ValueError for a negative occurrence count, a non-positive
    unit count, or occurrences exceeding units produced.
    """
    if occurrences < 0:
        raise ValueError("occurrences must be >= 0, got %r" % (occurrences,))
    if units_produced <= 0:
        raise ValueError("units produced must be > 0, got %r" % (units_produced,))
    if occurrences > units_produced:
        raise ValueError(
            "occurrences %r cannot exceed units produced %r"
            % (occurrences, units_produced)
        )
    return occurrences / units_produced


def residual_risk_acceptable(after_rpn, threshold):
    """Return True when the residual RPN meets the acceptance threshold.

    AS9100D 8.1.1 risk close-out: each assessed risk needs a
    mitigation plan and the residual risk must be accepted by the
    responsible function. This check implements the acceptance
    decision against the organization threshold.

    Anchors: residual_risk_acceptable(24, 40) is True;
    residual_risk_acceptable(60, 40) is False.

    Raises ValueError for a negative after_rpn or threshold.
    """
    if after_rpn < 0:
        raise ValueError("after rpn must be >= 0, got %r" % (after_rpn,))
    if threshold < 0:
        raise ValueError("threshold must be >= 0, got %r" % (threshold,))
    return after_rpn <= threshold


def risk_matrix_classification(severity, likelihood):
    """Return the 5x5 risk-matrix band: "high", "medium", or "low".

    The AS9100-style 5x5 matrix classifies by the severity-likelihood
    product: product >= 15 is "high", product >= 6 is "medium", else
    "low". The matrix bands rank risks for planning priority and are
    coarser than the FMEA RPN (which adds the detection axis).

    Anchors: risk_matrix_classification(4, 4) == "high" (16);
    risk_matrix_classification(3, 2) == "medium" (6);
    risk_matrix_classification(2, 2) == "low" (4).

    Raises ValueError unless each rating is an integer in 1-5.
    """
    for value, name in ((severity, "severity"), (likelihood, "likelihood")):
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError("%s must be an integer in 1-5, got %r" % (name, value))
    product = severity * likelihood
    if product >= 15:
        return "high"
    if product >= 6:
        return "medium"
    return "low"


def rank_risks(risks):
    """Return risk identifiers ordered by descending RPN (mitigation priority).

    Accepts an iterable of (identifier, rpn) pairs and returns the
    identifiers sorted by RPN descending, with ties broken by
    identifier ascending so the ordering is deterministic. The top
    entry is the first mitigation-planning target.

    Anchor: rank_risks([("A", 50), ("B", 120), ("C", 20)]) ==
    ["B", "A", "C"].

    Raises ValueError for an empty list or a negative rpn.
    """
    items = list(risks)
    if not items:
        raise ValueError("risks list must not be empty")
    for identifier, rpn in items:
        if rpn < 0:
            raise ValueError("rpn for %r must be >= 0, got %r" % (identifier, rpn))
        if not math.isfinite(rpn):
            raise ValueError("rpn for %r must be finite, got %r" % (identifier, rpn))
    items.sort(key=lambda pair: (-pair[1], str(pair[0])))
    return [identifier for identifier, _ in items]
