"""Statistical treatment of mechanical-test results into basis values.

Anchor: ECSS-Q-ST-70-45 data clause -- what a set of mechanical test results
has to be put through before any one number from it is handed to the design
allowables process. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Screen the sample for a single extreme result with the maximum normed
   residual against its tabulated critical value, and refuse to extrapolate
   that table past the sample sizes it covers.
2. Report the scatter of the sample as a coefficient of variation and raise a
   finding when it exceeds what the property is allowed to scatter by.
3. Compute the one-sided normal tolerance factor for the coverage and
   confidence the basis demands, by inverting the exact non-central
   distribution numerically rather than by a table lookup.
4. Turn that factor into an A-basis or a B-basis value, mean less factor times
   sample standard deviation.
5. Refuse a basis value from a sample smaller than the floor the basis owes,
   and compare the value obtained against the design allowable already in use.
"""

import math
from statistics import NormalDist

__all__ = [
    "BASIS_DEFINITIONS",
    "DEFAULT_MIN_SAMPLES",
    "MNR_CRITICAL_VALUES",
    "DEFAULT_MAX_CV_PCT",
    "BASIS_TOLERANCE",
    "sample_statistics",
    "mnr_critical_value",
    "outlier_screen",
    "normal_tolerance_factor",
    "basis_value",
    "scatter_finding",
    "assess_statistical_treatment",
]

# Coverage and confidence each basis is defined at.
BASIS_DEFINITIONS = {
    "A": {"proportion": 0.99, "confidence": 0.95},
    "B": {"proportion": 0.90, "confidence": 0.95},
}

# Smallest sample a basis value may be drawn from. Below this the tolerance
# factor is so large that the value is driven by the sample size rather than
# by the material.
DEFAULT_MIN_SAMPLES = {"A": 15, "B": 10}

# Maximum normed residual critical values at the five percent significance
# level, by sample size. The table is not extrapolated: a sample outside it
# is refused rather than screened against an invented limit.
MNR_CRITICAL_VALUES = {
    3: 1.155, 4: 1.481, 5: 1.715, 6: 1.887, 7: 2.020, 8: 2.126, 9: 2.215,
    10: 2.290, 11: 2.355, 12: 2.412, 13: 2.462, 14: 2.507, 15: 2.549,
    16: 2.585, 17: 2.620, 18: 2.651, 19: 2.681, 20: 2.709, 25: 2.822,
    30: 2.908, 40: 3.036, 50: 3.128, 60: 3.199, 80: 3.305, 100: 3.383,
}

# Coefficient of variation, in percent, above which a sample is reported as
# scattered rather than merely variable.
DEFAULT_MAX_CV_PCT = 10.0

# Basis comparisons are differences of numerically integrated quantities. A
# value physically exactly on a limit can land a few ULP either side, so the
# comparisons absorb that rather than moving the limit.
BASIS_TOLERANCE = 1e-12

_NORMAL = NormalDist()
_FACTOR_CACHE = {}

# Simpson panels across the sampling distribution of the standard deviation,
# and bisection steps on the factor. Both are fixed so the factor is
# reproducible run to run and host to host.
_PANELS = 800
_BISECTION_STEPS = 60


def _real(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _clean_sample(values):
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence of test results")
    cleaned = [_real("values[%d]" % index, item) for index, item in enumerate(values)]
    if len(cleaned) < 2:
        raise ValueError("a statistical treatment needs at least two results, got %d" % len(cleaned))
    return cleaned


def sample_statistics(values):
    """Return the size, mean, sample standard deviation and scatter of a sample."""
    cleaned = _clean_sample(values)
    n = len(cleaned)
    mean = sum(cleaned) / n
    variance = sum((value - mean) ** 2 for value in cleaned) / (n - 1)
    sd = math.sqrt(variance)
    if mean == 0.0:
        raise ValueError("a sample mean of zero has no coefficient of variation")
    return {
        "n": n,
        "mean": mean,
        "standard_deviation": sd,
        "cv_pct": 100.0 * sd / abs(mean),
        "minimum": min(cleaned),
        "maximum": max(cleaned),
    }


def mnr_critical_value(n):
    """Return the maximum normed residual critical value for a sample size."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError("n must be an integer sample size, got %r" % (n,))
    sizes = sorted(MNR_CRITICAL_VALUES)
    if n < sizes[0] or n > sizes[-1]:
        raise ValueError(
            "the critical-value table covers sample sizes %d to %d; %d is outside it, "
            "extrapolation refused" % (sizes[0], sizes[-1], n)
        )
    if n in MNR_CRITICAL_VALUES:
        return MNR_CRITICAL_VALUES[n]
    lower = max(size for size in sizes if size < n)
    upper = min(size for size in sizes if size > n)
    fraction = (n - lower) / float(upper - lower)
    return MNR_CRITICAL_VALUES[lower] + fraction * (
        MNR_CRITICAL_VALUES[upper] - MNR_CRITICAL_VALUES[lower]
    )


def outlier_screen(values):
    """Screen a sample for one extreme result with the maximum normed residual."""
    stats = sample_statistics(values)
    cleaned = _clean_sample(values)
    if stats["standard_deviation"] == 0.0:
        return {
            "mnr": 0.0,
            "critical": mnr_critical_value(stats["n"]),
            "index": None,
            "value": None,
            "flagged": False,
            "retained": list(cleaned),
        }
    critical = mnr_critical_value(stats["n"])
    worst_index = 0
    worst_mnr = -1.0
    for index, value in enumerate(cleaned):
        normed = abs(value - stats["mean"]) / stats["standard_deviation"]
        if normed > worst_mnr:
            worst_mnr = normed
            worst_index = index
    flagged = worst_mnr > critical and not math.isclose(
        worst_mnr, critical, rel_tol=0.0, abs_tol=BASIS_TOLERANCE
    )
    retained = [v for i, v in enumerate(cleaned) if not (flagged and i == worst_index)]
    return {
        "mnr": worst_mnr,
        "critical": critical,
        "index": worst_index if flagged else None,
        "value": cleaned[worst_index] if flagged else None,
        "flagged": flagged,
        "retained": retained,
    }


def _confidence_at(n, factor, z_proportion):
    """Return the confidence a candidate tolerance factor actually delivers."""
    nu = n - 1
    hi = 1.0 + 12.0 / math.sqrt(2.0 * nu)
    step = hi / _PANELS
    log_norm = (
        math.log(2.0)
        + (nu / 2.0) * math.log(nu)
        - (nu / 2.0) * math.log(2.0)
        - math.lgamma(nu / 2.0)
    )
    root_n = math.sqrt(n)
    total = 0.0
    for index in range(_PANELS + 1):
        s = index * step
        if s <= 0.0:
            continue
        weight = 1.0 if index in (0, _PANELS) else (4.0 if index % 2 else 2.0)
        density = math.exp(log_norm + (nu - 1) * math.log(s) - nu * s * s / 2.0)
        total += weight * density * _NORMAL.cdf(factor * root_n * s - z_proportion * root_n)
    return total * step / 3.0


def normal_tolerance_factor(n, proportion, confidence):
    """Return the one-sided normal tolerance factor for a coverage and confidence.

    Found by bisection on the exact sampling distribution rather than read off
    a table, so any coverage and confidence pair is available and no
    interpolation error enters the allowable.
    """
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError("n must be an integer sample size, got %r" % (n,))
    if n < 3:
        raise ValueError("a tolerance factor needs at least three results, got %d" % n)
    for label, value in (("proportion", proportion), ("confidence", confidence)):
        number = _real(label, value)
        if not 0.5 <= number < 1.0:
            raise ValueError("%s must lie in [0.5, 1.0), got %r" % (label, value))
    key = (n, float(proportion), float(confidence))
    if key in _FACTOR_CACHE:
        return _FACTOR_CACHE[key]
    z_proportion = _NORMAL.inv_cdf(float(proportion))
    target = float(confidence)
    low, high = 0.0, 30.0
    for _ in range(_BISECTION_STEPS):
        middle = 0.5 * (low + high)
        if _confidence_at(n, middle, z_proportion) < target:
            low = middle
        else:
            high = middle
    factor = 0.5 * (low + high)
    _FACTOR_CACHE[key] = factor
    return factor


def basis_value(values, basis, min_samples=None):
    """Return the one-sided lower basis value of a sample."""
    if basis not in BASIS_DEFINITIONS:
        raise ValueError("basis must be one of %s, got %r" % (sorted(BASIS_DEFINITIONS), basis))
    stats = sample_statistics(values)
    floor = DEFAULT_MIN_SAMPLES[basis] if min_samples is None else min_samples
    if not isinstance(floor, int) or isinstance(floor, bool) or floor < 3:
        raise ValueError("min_samples must be an integer of at least three, got %r" % (floor,))
    definition = BASIS_DEFINITIONS[basis]
    factor = normal_tolerance_factor(
        stats["n"], definition["proportion"], definition["confidence"]
    )
    value = stats["mean"] - factor * stats["standard_deviation"]
    return {
        "basis": basis,
        "n": stats["n"],
        "mean": stats["mean"],
        "standard_deviation": stats["standard_deviation"],
        "tolerance_factor": factor,
        "value": value,
        "min_samples": floor,
        "sample_sufficient": stats["n"] >= floor,
    }


def scatter_finding(cv_pct, max_cv_pct=DEFAULT_MAX_CV_PCT):
    """Grade the scatter of a sample against the limit the property allows."""
    measured = _real("cv_pct", cv_pct)
    if measured < 0.0:
        raise ValueError("cv_pct must not be negative, got %r" % (cv_pct,))
    limit = _real("max_cv_pct", max_cv_pct)
    if limit <= 0.0:
        raise ValueError("max_cv_pct must be positive, got %r" % (max_cv_pct,))
    within = measured < limit or math.isclose(
        measured, limit, rel_tol=0.0, abs_tol=BASIS_TOLERANCE
    )
    return {
        "cv_pct": measured,
        "max_cv_pct": limit,
        "within": within,
        "finding": None if within else (
            "sample scatter %.3f%% exceeds the %.3f%% the property allows" % (measured, limit)
        ),
    }


def assess_statistical_treatment(spec):
    """Run the whole statistical treatment of one set of mechanical test results.

    spec keys: values, basis. Optional: drop_outlier (bool), max_cv_pct,
    min_samples, design_allowable.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("values", "basis"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    findings = []
    screen = outlier_screen(spec["values"])
    working = spec["values"]
    if screen["flagged"]:
        findings.append(
            "result %g at position %d exceeds the maximum normed residual critical value "
            "%.3f; it owes a cause before it is kept or set aside"
            % (screen["value"], screen["index"], screen["critical"])
        )
        if spec.get("drop_outlier", False):
            working = screen["retained"]

    stats = sample_statistics(working)
    scatter = scatter_finding(stats["cv_pct"], spec.get("max_cv_pct", DEFAULT_MAX_CV_PCT))
    if scatter["finding"]:
        findings.append(scatter["finding"])

    result = basis_value(working, spec["basis"], spec.get("min_samples"))
    if not result["sample_sufficient"]:
        findings.append(
            "a %s-basis value owes at least %d results and the sample holds %d"
            % (result["basis"], result["min_samples"], result["n"])
        )

    allowable = spec.get("design_allowable")
    margin = None
    if allowable is not None:
        allowable = _real("design_allowable", allowable)
        margin = result["value"] - allowable
        supported = margin > 0.0 or math.isclose(
            result["value"], allowable, rel_tol=0.0, abs_tol=BASIS_TOLERANCE
        )
        if not supported:
            findings.append(
                "the design allowable %g sits above the %s-basis value %g this sample "
                "supports" % (allowable, result["basis"], result["value"])
            )

    return {
        "screen": screen,
        "statistics": stats,
        "scatter": scatter,
        "basis": result,
        "design_allowable": allowable,
        "margin": margin,
        "findings": findings,
        "usable": not findings,
    }
