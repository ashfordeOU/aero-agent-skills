"""Purpose of the interconnector pull test: bond strength and electrical stability.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.10.1 (pull testing of solar-cell
interconnectors -- monitoring the strength of the interconnector bonds under an
applied stress and confirming that the circuit is still electrically stable once
the stress has been removed). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the minimum bond strength the joints have to carry from the declared
   handling and deployment load and the factor applied to it.
2. Form the sample statistics of the measured pull forces -- count, mean, sample
   spread and weakest joint -- and the one-sided lower tolerance bound that
   states what the population, not just the sample, is good for.
3. Grade every pulled tab against the strength floor and the population bound
   against the same floor, so a sample whose mean passes while its spread is
   wide is still reported as a shortfall.
4. Compare the pre-test and post-test resistance of every monitored circuit
   against the drift allowance, since a joint that survives the load and then
   reads high is not electrically stable.
5. Report the derived floor, the statistics, the weakest joint, every finding
   and the campaign verdict; the purpose is met only when no finding stands.
"""

import math

__all__ = [
    "FORCE_TOLERANCE_N",
    "DRIFT_TOLERANCE",
    "MIN_SAMPLE_SIZE",
    "TOLERANCE_FACTORS",
    "required_bond_strength_n",
    "sample_statistics",
    "tolerance_factor",
    "lower_tolerance_bound_n",
    "strength_findings",
    "resistance_drift_fraction",
    "stability_findings",
    "assess_pull_test_purpose",
]

# A pull force sitting exactly on the strength floor is compliant: the
# comparison absorbs representation error, the engineering floor is never
# lowered to make a sample pass.
FORCE_TOLERANCE_N = 1e-9

# Same idea on the resistance drift fraction.
DRIFT_TOLERANCE = 1e-12

# Below three pulls there is no spread to speak of, so no statement about the
# population can be made from the sample at all.
MIN_SAMPLE_SIZE = 3

# One-sided lower tolerance factors, normal population, 95 % confidence that
# 95 % of the population lies above the bound. Tabulated by sample size; a size
# between two entries takes the factor of the next smaller tabulated size, which
# is the larger and therefore the conservative factor.
TOLERANCE_FACTORS = {
    3: 7.655,
    4: 5.145,
    5: 4.202,
    6: 3.707,
    7: 3.399,
    8: 3.188,
    9: 3.031,
    10: 2.911,
    12: 2.736,
    15: 2.566,
    20: 2.396,
    25: 2.292,
    30: 2.220,
    40: 2.125,
    50: 2.065,
}


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def _name(value, label):
    """Return a trimmed, non-empty identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("%s must not be empty" % label)
    return cleaned


def required_bond_strength_n(design_load_n, safety_factor):
    """Return the minimum pull force an interconnector bond has to carry."""
    load = _positive(design_load_n, "design_load_n")
    factor = _real(safety_factor, "safety_factor")
    if factor < 1.0:
        raise ValueError("safety_factor must be at least 1.0, got %g" % factor)
    return load * factor


def sample_statistics(forces_n):
    """Return count, mean, sample standard deviation and weakest pull force."""
    if not isinstance(forces_n, (list, tuple)):
        raise ValueError("forces_n must be a sequence of pull forces")
    values = [_positive(force, "pull force") for force in forces_n]
    count = len(values)
    if count < MIN_SAMPLE_SIZE:
        raise ValueError(
            "a pull sample needs at least %d measurements, got %d"
            % (MIN_SAMPLE_SIZE, count)
        )
    mean = math.fsum(values) / count
    variance = math.fsum((value - mean) ** 2 for value in values) / (count - 1)
    return {
        "count": count,
        "mean_n": mean,
        "stdev_n": math.sqrt(variance),
        "minimum_n": min(values),
    }


def tolerance_factor(count):
    """Return the one-sided lower tolerance factor for a sample of this size."""
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < MIN_SAMPLE_SIZE:
        raise ValueError(
            "count must be at least %d, got %d" % (MIN_SAMPLE_SIZE, count)
        )
    sizes = sorted(TOLERANCE_FACTORS)
    if count >= sizes[-1]:
        return TOLERANCE_FACTORS[sizes[-1]]
    chosen = sizes[0]
    for size in sizes:
        if size <= count:
            chosen = size
    return TOLERANCE_FACTORS[chosen]


def lower_tolerance_bound_n(statistics):
    """Return the lower bound the pulled population is good for, in newtons."""
    if not isinstance(statistics, dict):
        raise ValueError("statistics must be a mapping from sample_statistics")
    for key in ("count", "mean_n", "stdev_n"):
        if key not in statistics:
            raise ValueError("statistics missing key '%s'" % key)
    factor = tolerance_factor(statistics["count"])
    mean = _positive(statistics["mean_n"], "mean_n")
    spread = _non_negative(statistics["stdev_n"], "stdev_n")
    return mean - factor * spread


def strength_findings(records, required_n):
    """Return findings for every pulled tab below the strength floor."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of pull records")
    floor = _positive(required_n, "required_n")
    findings = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each pull record must be a mapping")
        for key in ("tab", "pull_force_n"):
            if key not in record:
                raise ValueError("pull record missing key '%s'" % key)
        tab = _name(record["tab"], "tab")
        if tab in seen:
            raise ValueError("tab '%s' appears twice in the pull records" % tab)
        seen.add(tab)
        force = _positive(record["pull_force_n"], "pull_force_n")
        if force < floor - FORCE_TOLERANCE_N:
            findings.append(
                "interconnector tab '%s' parted at %g N, below the %g N floor"
                % (tab, force, floor)
            )
    return findings


def resistance_drift_fraction(pre_ohm, post_ohm):
    """Return the fractional change in circuit resistance across the pull test."""
    pre = _positive(pre_ohm, "pre_ohm")
    post = _positive(post_ohm, "post_ohm")
    return (post - pre) / pre


def stability_findings(records, drift_allowance):
    """Return findings for every circuit whose resistance drifted too far."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError(
            "records must be a non-empty sequence of resistance records"
        )
    allowance = _positive(drift_allowance, "drift_allowance")
    findings = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each resistance record must be a mapping")
        for key in ("circuit", "pre_ohm", "post_ohm"):
            if key not in record:
                raise ValueError("resistance record missing key '%s'" % key)
        circuit = _name(record["circuit"], "circuit")
        drift = resistance_drift_fraction(record["pre_ohm"], record["post_ohm"])
        if abs(drift) > allowance + DRIFT_TOLERANCE:
            findings.append(
                "circuit '%s' resistance moved by %.4f across the pull test, "
                "beyond the %.4f allowance" % (circuit, drift, allowance)
            )
    return findings


def assess_pull_test_purpose(spec):
    """Run the full clause 6.4.3.10.1 pull-test purpose check.

    spec keys: design_load_n, safety_factor, pull_records (tab, pull_force_n),
    resistance_records (circuit, pre_ohm, post_ohm), drift_allowance; optional
    min_sample_size.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "design_load_n",
        "safety_factor",
        "pull_records",
        "resistance_records",
        "drift_allowance",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    minimum = spec.get("min_sample_size", MIN_SAMPLE_SIZE)
    if not isinstance(minimum, int) or isinstance(minimum, bool):
        raise ValueError("min_sample_size must be an integer, got %r" % (minimum,))
    if minimum < MIN_SAMPLE_SIZE:
        raise ValueError(
            "min_sample_size must be at least %d, got %d"
            % (MIN_SAMPLE_SIZE, minimum)
        )

    floor = required_bond_strength_n(spec["design_load_n"], spec["safety_factor"])
    records = spec["pull_records"]
    findings = list(strength_findings(records, floor))
    statistics = sample_statistics(
        [record["pull_force_n"] for record in records]
    )
    bound = lower_tolerance_bound_n(statistics)
    if statistics["count"] < minimum:
        findings.append(
            "%d interconnectors were pulled, short of the %d the campaign "
            "calls for" % (statistics["count"], minimum)
        )
    if bound < floor - FORCE_TOLERANCE_N:
        findings.append(
            "the population lower bound of %g N falls below the %g N floor, so "
            "the sample spread is too wide to demonstrate the bond strength"
            % (bound, floor)
        )
    findings.extend(
        stability_findings(spec["resistance_records"], spec["drift_allowance"])
    )
    weakest = min(records, key=lambda record: float(record["pull_force_n"]))
    return {
        "required_strength_n": floor,
        "statistics": statistics,
        "tolerance_factor": tolerance_factor(statistics["count"]),
        "lower_bound_n": bound,
        "strength_margin_n": statistics["minimum_n"] - floor,
        "weakest_tab": _name(weakest["tab"], "tab"),
        "findings": findings,
        "purpose_met": not findings,
    }
