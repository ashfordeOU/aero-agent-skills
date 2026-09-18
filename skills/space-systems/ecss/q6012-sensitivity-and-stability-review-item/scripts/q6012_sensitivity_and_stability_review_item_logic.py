"""Sensitivity and stability review item of a die-form MMIC design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.5 (design review -- the sensitivity and
stability item). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
Sensitivity half
    1. For each performance parameter, turn each declared variation source into
       a normalised sensitivity coefficient S = (dY/Y) / (dx/x): the fractional
       output move per fractional input move. This makes process, temperature,
       supply and bias variation comparable on one scale.
    2. Weight each coefficient by that source's own declared tolerance and
       combine the contributions root-sum-square, because the sources are
       independent; adding them arithmetically overstates the spread.
    3. Compare the combined relative spread with the allowance, and name the
       dominant contributor, which is the one a design change has to address.
    4. Flag a source whose perturbation moved the output by nothing, and a
       required variation source that the evidence never exercised.

Stability half
    5. At each swept frequency, form the determinant of the scattering matrix
       D = s11*s22 - s12*s21 and Rollett's stability factor
       K = (1 - |s11|^2 - |s22|^2 + |D|^2) / (2 * |s12 * s21|), together with
       the single-parameter factor
       mu = (1 - |s11|^2) / (|s22 - D * conj(s11)| + |s12 * s21|).
    6. Unconditional stability needs K above the required value and |D| below
       one at that frequency; an exact landing on either boundary is treated as
       not cleared, since unconditional stability is a strict condition.
    7. Grade the sweep span itself. Unwanted oscillation in a microwave
       amplifier is usually out of band, where device gain is still high and
       the matching networks no longer control the terminations, so a sweep
       that stops at the band edges is a coverage finding in its own right.
"""

import cmath
import math

__all__ = [
    "STABILITY_TOLERANCE",
    "SPREAD_TOLERANCE",
    "to_complex",
    "scattering_determinant",
    "rollett_k",
    "mu_factor",
    "stability_at_frequency",
    "normalised_sensitivity",
    "source_contributions",
    "root_sum_square",
    "assess_sensitivity",
    "assess_stability_sweep",
    "review_sensitivity_and_stability",
]

# K and |D| are built from squares and a square root, so a design sitting
# exactly on a stability boundary can land a few ULPs either side. Absorb the
# representation error here; the boundary itself does not move.
STABILITY_TOLERANCE = 1e-9

# The combined spread is a root-sum-square, so the same reasoning applies to a
# parameter that lands exactly on its allowance.
SPREAD_TOLERANCE = 1e-9

_S_KEYS = ("s11", "s12", "s21", "s22")


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _text(label, value):
    """Return a non-empty stripped identifier or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % label)
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def _above(value, limit):
    """True when value clears the limit; an exact landing does not clear it."""
    if math.isclose(value, limit, rel_tol=0.0, abs_tol=STABILITY_TOLERANCE):
        return False
    return value > limit


def _below(value, limit):
    """True when value is under the limit; an exact landing is not under it."""
    if math.isclose(value, limit, rel_tol=0.0, abs_tol=STABILITY_TOLERANCE):
        return False
    return value < limit


def to_complex(label, value):
    """Return a scattering entry given as a (magnitude, angle in degrees) pair."""
    if isinstance(value, complex):
        if not (math.isfinite(value.real) and math.isfinite(value.imag)):
            raise ValueError("%s must be finite" % label)
        return value
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be a (magnitude, angle_deg) pair" % label)
    magnitude = _real("%s magnitude" % label, value[0])
    angle = _real("%s angle" % label, value[1])
    if magnitude < 0.0:
        raise ValueError("%s magnitude must not be negative, got %g" % (label, magnitude))
    return cmath.rect(magnitude, math.radians(angle))


def _scattering(entry):
    """Return the four validated scattering entries of one frequency point."""
    if not isinstance(entry, dict):
        raise ValueError("scattering entry must be a mapping")
    out = {}
    for key in _S_KEYS:
        if key not in entry:
            raise ValueError("scattering entry missing '%s'" % key)
        out[key] = to_complex(key, entry[key])
    if abs(out["s12"]) == 0.0 or abs(out["s21"]) == 0.0:
        raise ValueError(
            "a zero reverse or forward transmission makes K undefined; "
            "report the unilateral case explicitly"
        )
    return out


def scattering_determinant(entry):
    """Return the determinant of the two-port scattering matrix."""
    s = _scattering(entry)
    return s["s11"] * s["s22"] - s["s12"] * s["s21"]


def rollett_k(entry):
    """Return Rollett's stability factor K at one frequency."""
    s = _scattering(entry)
    determinant = s["s11"] * s["s22"] - s["s12"] * s["s21"]
    numerator = (
        1.0 - abs(s["s11"]) ** 2 - abs(s["s22"]) ** 2 + abs(determinant) ** 2
    )
    return numerator / (2.0 * abs(s["s12"] * s["s21"]))


def mu_factor(entry):
    """Return the source-plane single-parameter stability factor mu."""
    s = _scattering(entry)
    determinant = s["s11"] * s["s22"] - s["s12"] * s["s21"]
    denominator = abs(s["s22"] - determinant * s["s11"].conjugate()) + abs(s["s12"] * s["s21"])
    if denominator == 0.0:
        raise ValueError("mu is undefined for this scattering set")
    return (1.0 - abs(s["s11"]) ** 2) / denominator


def stability_at_frequency(point, required_k=1.0):
    """Grade one swept frequency for unconditional stability."""
    if not isinstance(point, dict):
        raise ValueError("point must be a mapping")
    frequency = _positive("frequency_ghz", point.get("frequency_ghz"))
    limit = _real("required_k", required_k)
    if limit < 1.0:
        raise ValueError("required_k must be at least 1, got %g" % limit)
    k = rollett_k(point)
    mu = mu_factor(point)
    magnitude = abs(scattering_determinant(point))
    k_clear = _above(k, limit)
    determinant_clear = _below(magnitude, 1.0)
    return {
        "frequency_ghz": frequency,
        "k": k,
        "mu": mu,
        "determinant_magnitude": magnitude,
        "k_clear": k_clear,
        "determinant_clear": determinant_clear,
        "unconditionally_stable": k_clear and determinant_clear,
    }


def normalised_sensitivity(nominal_output, perturbed_output, relative_input_change):
    """Return the fractional output move per fractional input move."""
    nominal = _real("nominal_output", nominal_output)
    perturbed = _real("perturbed_output", perturbed_output)
    change = _real("relative_input_change", relative_input_change)
    if nominal == 0.0:
        raise ValueError("a zero nominal output has no normalised sensitivity")
    if change == 0.0:
        raise ValueError("relative_input_change must not be zero")
    return ((perturbed - nominal) / nominal) / change


def source_contributions(nominal_output, sources):
    """Return the per-source sensitivity and tolerance-weighted contribution."""
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("sources must be a non-empty sequence")
    records = []
    seen = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError("sources[%d] must be a mapping" % index)
        name = _text("sources[%d] name" % index, source.get("name", "")).lower()
        if name in seen:
            raise ValueError("variation source '%s' is declared twice" % name)
        seen.add(name)
        sensitivity = normalised_sensitivity(
            nominal_output,
            source.get("perturbed_output"),
            source.get("relative_input_change"),
        )
        tolerance = _real("sources[%d] tolerance" % index, source.get("tolerance"))
        if tolerance <= 0.0:
            raise ValueError("variation source '%s' tolerance must be positive" % name)
        records.append(
            {
                "name": name,
                "sensitivity": sensitivity,
                "tolerance": tolerance,
                "contribution": sensitivity * tolerance,
            }
        )
    return records


def root_sum_square(values):
    """Return the root-sum-square of independent contributions."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    total = 0.0
    for index, item in enumerate(values):
        one = _real("values[%d]" % index, item)
        total += one * one
    return math.sqrt(total)


def assess_sensitivity(parameter, required_sources=()):
    """Grade one parameter's tolerance to the declared variation sources."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping")
    name = _text("parameter name", parameter.get("name", ""))
    nominal = _real("parameter '%s' nominal" % name, parameter.get("nominal"))
    allowance = _positive(
        "parameter '%s' allowed_relative_spread" % name,
        parameter.get("allowed_relative_spread"),
    )
    records = source_contributions(nominal, parameter.get("sources"))
    spread = root_sum_square([record["contribution"] for record in records])

    findings = []
    for record in records:
        if math.isclose(record["sensitivity"], 0.0, rel_tol=0.0, abs_tol=SPREAD_TOLERANCE):
            findings.append(
                "%s: variation source '%s' moved the output by nothing; "
                "confirm the perturbation reached the simulation"
                % (name, record["name"])
            )
    covered = set(record["name"] for record in records)
    for item in required_sources or ():
        wanted = _text("required variation source", item).lower()
        if wanted not in covered:
            findings.append(
                "%s: required variation source '%s' was never exercised" % (name, wanted)
            )
    within = spread < allowance or math.isclose(
        spread, allowance, rel_tol=0.0, abs_tol=SPREAD_TOLERANCE
    )
    if not within:
        findings.append(
            "%s: combined relative spread %.6g exceeds the allowance %.6g"
            % (name, spread, allowance)
        )
    dominant = max(records, key=lambda record: abs(record["contribution"]))
    return {
        "name": name,
        "nominal": nominal,
        "sources": records,
        "relative_spread": spread,
        "allowed_relative_spread": allowance,
        "dominant_source": dominant["name"],
        "within_allowance": within,
        "findings": findings,
    }


def assess_stability_sweep(sweep, band_ghz, span_factor=3.0, required_k=1.0):
    """Grade a swept stability analysis for clearance and for span coverage."""
    if not isinstance(sweep, (list, tuple)) or len(sweep) < 2:
        raise ValueError("sweep must carry at least two frequency points")
    if not isinstance(band_ghz, (list, tuple)) or len(band_ghz) != 2:
        raise ValueError("band_ghz must be a (low, high) pair")
    low = _positive("band low edge", band_ghz[0])
    high = _positive("band high edge", band_ghz[1])
    if low > high:
        raise ValueError("band low edge %g exceeds high edge %g" % (low, high))
    factor = _real("span_factor", span_factor)
    if factor < 1.0:
        raise ValueError("span_factor must be at least 1, got %g" % factor)

    records = []
    previous = None
    for index, point in enumerate(sweep):
        record = stability_at_frequency(point, required_k)
        if previous is not None and record["frequency_ghz"] <= previous:
            raise ValueError(
                "sweep frequencies must strictly increase (point %d at %g GHz)"
                % (index, record["frequency_ghz"])
            )
        previous = record["frequency_ghz"]
        records.append(record)

    findings = []
    unstable = [record for record in records if not record["unconditionally_stable"]]
    for record in unstable:
        findings.append(
            "potential instability at %g GHz: K = %.6g, |determinant| = %.6g"
            % (record["frequency_ghz"], record["k"], record["determinant_magnitude"])
        )
    lowest = records[0]["frequency_ghz"]
    highest = records[-1]["frequency_ghz"]
    wanted_low = low / factor
    wanted_high = high * factor
    if _above(lowest, wanted_low):
        findings.append(
            "sweep starts at %g GHz; low-frequency oscillation is unexamined below %g GHz"
            % (lowest, wanted_low)
        )
    if _below(highest, wanted_high):
        findings.append(
            "sweep stops at %g GHz; out-of-band oscillation is unexamined above %g GHz"
            % (highest, wanted_high)
        )
    in_band = [
        record for record in records
        if low <= record["frequency_ghz"] <= high
    ]
    if not in_band:
        findings.append("sweep contains no point inside the operating band")
    return {
        "points": records,
        "band_ghz": (low, high),
        "span_factor": factor,
        "required_k": _real("required_k", required_k),
        "lowest_swept_ghz": lowest,
        "highest_swept_ghz": highest,
        "minimum_k": min(record["k"] for record in records),
        "unstable_frequencies_ghz": [record["frequency_ghz"] for record in unstable],
        "sweep_clean": not findings,
        "findings": findings,
    }


def review_sensitivity_and_stability(package):
    """Run the whole clause 7.3.5 sensitivity and stability review item.

    package keys: parameters (each carrying name, nominal,
    allowed_relative_spread and sources), optional required_variation_sources,
    and stability (band_ghz, sweep, optional span_factor and required_k).
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    for key in ("parameters", "stability"):
        if key not in package:
            raise ValueError("package missing required key '%s'" % key)
    parameters = package["parameters"]
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("package['parameters'] must be a non-empty sequence")
    stability = package["stability"]
    if not isinstance(stability, dict):
        raise ValueError("package['stability'] must be a mapping")
    for key in ("band_ghz", "sweep"):
        if key not in stability:
            raise ValueError("package['stability'] missing required key '%s'" % key)

    required_sources = package.get("required_variation_sources", ())
    graded = []
    seen = set()
    findings = []
    for parameter in parameters:
        record = assess_sensitivity(parameter, required_sources)
        if record["name"] in seen:
            raise ValueError("parameter '%s' is graded twice" % record["name"])
        seen.add(record["name"])
        graded.append(record)
        findings.extend(record["findings"])

    sweep = assess_stability_sweep(
        stability["sweep"],
        stability["band_ghz"],
        stability.get("span_factor", 3.0),
        stability.get("required_k", 1.0),
    )
    findings.extend(sweep["findings"])
    worst = max(graded, key=lambda record: record["relative_spread"])
    return {
        "parameters": graded,
        "stability": sweep,
        "worst_spread_parameter": worst["name"],
        "worst_relative_spread": worst["relative_spread"],
        "findings": findings,
        "item_passed": not findings,
    }
