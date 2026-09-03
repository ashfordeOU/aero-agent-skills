"""RNP containment logic: ANP against RNP with margin (stdlib only).

Checks navigation performance containment for performance based
navigation: the actual navigation performance (ANP) is the 95th
percentile lateral position error, computed as CONTAINMENT_SIGMA times
the supplied 1-sigma lateral position error (or taken directly from an
ANP input), and it must stay within the required navigation performance
(RNP) after applying an optional required margin.

Pure Python standard library, deterministic, no network, no external
processes. Non-physical inputs raise ValueError.
"""

CONTAINMENT_SIGMA = 2.0
DEFAULT_MARGIN_FRACTION = 0.0
PASS_VERDICT = "PASS"
FAIL_VERDICT = "FAIL"


def _require_nonnegative(value, name):
    if value is None or value < 0.0:
        raise ValueError("%s must be a non-negative number, got %r" % (name, value))
    return float(value)


def _require_positive(value, name):
    if value is None or value <= 0.0:
        raise ValueError("%s must be a positive number, got %r" % (name, value))
    return float(value)


def anp_from_sigma(sigma_lateral_m):
    """Compute the ANP as the 95th percentile bound: 2 * sigma."""
    sigma = _require_nonnegative(sigma_lateral_m, "sigma_lateral_m")
    return CONTAINMENT_SIGMA * sigma


def margin_m(rnp_m, margin_fraction=DEFAULT_MARGIN_FRACTION):
    """Required margin in meters: rnp * margin_fraction."""
    rnp = _require_positive(rnp_m, "rnp_m")
    fraction = _require_nonnegative(margin_fraction, "margin_fraction")
    return rnp * fraction


def containment_pass(anp_m, rnp_m, margin_fraction=DEFAULT_MARGIN_FRACTION):
    """True when anp + margin <= rnp (inclusive boundary passes)."""
    anp = _require_nonnegative(anp_m, "anp_m")
    rnp = _require_positive(rnp_m, "rnp_m")
    fraction = _require_nonnegative(margin_fraction, "margin_fraction")
    return (anp + margin_m(rnp, fraction)) <= rnp


def margin_available_m(anp_m, rnp_m, margin_fraction=DEFAULT_MARGIN_FRACTION):
    """Remaining containment margin: rnp - margin - anp."""
    anp = _require_nonnegative(anp_m, "anp_m")
    rnp = _require_positive(rnp_m, "rnp_m")
    fraction = _require_nonnegative(margin_fraction, "margin_fraction")
    return rnp - margin_m(rnp, fraction) - anp


def analyze(sigma_lateral_m=None, anp_m=None, *, rnp_m,
            margin_fraction=DEFAULT_MARGIN_FRACTION):
    """Return the RNP containment verdict dict.

    anp_m is used directly when supplied; otherwise it is derived from
    sigma_lateral_m as CONTAINMENT_SIGMA * sigma_lateral_m. Raises
    ValueError when both inputs are missing, rnp_m is not positive,
    sigma_lateral_m or margin_fraction is negative, or anp_m is
    negative.
    """
    rnp = _require_positive(rnp_m, "rnp_m")
    fraction = _require_nonnegative(margin_fraction, "margin_fraction")
    if anp_m is not None:
        anp = _require_nonnegative(anp_m, "anp_m")
    else:
        if sigma_lateral_m is None:
            raise ValueError(
                "supply sigma_lateral_m or anp_m to run the containment check"
            )
        anp = anp_from_sigma(sigma_lateral_m)
    margin = margin_m(rnp, fraction)
    passed = containment_pass(anp, rnp, fraction)
    return {
        "anp_m": anp,
        "rnp_m": rnp,
        "pass": passed,
        "margin_m": margin,
        "verdict": PASS_VERDICT if passed else FAIL_VERDICT,
    }
