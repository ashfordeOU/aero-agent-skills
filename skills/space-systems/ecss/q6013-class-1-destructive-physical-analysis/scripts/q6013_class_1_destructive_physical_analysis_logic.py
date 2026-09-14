"""Destructive physical analysis of purchased commercial EEE lots.

Anchor: ECSS-Q-ST-60-13C clause 4.3.9 (Class 1 use of commercial EEE
components -- destructive sample analysis of the procured lot). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the delivered shipment into its date-code groups. A commercial
   shipment against one order line routinely spans several date codes, and
   each date code is a separate build that has to be sampled in its own right.
2. Size the destructive sample per date-code group from a sampling fraction
   and a floor, capped by the group size, and refuse a group too small to
   surrender a sample without consuming the whole delivery.
3. Sort every observed defect into a major or a minor category from a named
   defect register; an unregistered defect code is refused rather than
   silently treated as cosmetic.
4. Evaluate the numeric construction criteria that the teardown produces:
   die-attach voiding (total area fraction and largest single void) and wire
   bond pull strength (sample minimum and sample mean).
5. Combine the categorised defects and the numeric findings into one lot
   disposition: accepted, accepted with a recorded observation, or rejected.
"""

import math

__all__ = [
    "FRACTION_TOLERANCE",
    "DEFAULT_SAMPLE_FRACTION",
    "DEFAULT_MIN_SAMPLE",
    "MAJOR_DEFECTS",
    "MINOR_DEFECTS",
    "validate_fraction",
    "categorize_defect",
    "categorize_defects",
    "dpa_sample_size",
    "sample_plan",
    "void_assessment",
    "bond_pull_assessment",
    "lot_disposition",
    "assess_destructive_physical_analysis",
]

# Area fractions and strengths are compared against declared limits. A value
# placed exactly on a limit can land a few ULP either side of it once it has
# been divided or averaged, so the representation error is absorbed here.
FRACTION_TOLERANCE = 1e-12

DEFAULT_SAMPLE_FRACTION = 0.01
DEFAULT_MIN_SAMPLE = 2

# Construction defects that bear on function or on reliability over life.
# Any one of these disposes of the date-code group it was found in.
MAJOR_DEFECTS = frozenset(
    {
        "wire-bond-lift",
        "wire-bond-neck-break",
        "die-attach-void-excess",
        "die-crack",
        "die-attach-delamination",
        "metallization-corrosion",
        "metallization-void",
        "package-seal-leak",
        "conductive-foreign-particle",
        "glassivation-crack-over-metal",
        "bond-pull-below-limit",
        "incorrect-die-marking",
    }
)

# Observations recorded against the lot without disposing of it.
MINOR_DEFECTS = frozenset(
    {
        "external-marking-blemish",
        "lead-finish-blemish",
        "glassivation-crack-over-oxide",
        "non-conductive-foreign-particle",
        "minor-die-attach-void",
        "tool-mark-on-package",
        "bond-placement-off-centre",
    }
)


def validate_fraction(value, label, allow_zero=True):
    """Return a validated area or sampling fraction in the range 0..1."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    fraction = float(value)
    if not math.isfinite(fraction):
        raise ValueError("%s must be finite" % label)
    if fraction < 0.0 or (fraction == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    if fraction > 1.0:
        raise ValueError("%s is a fraction and cannot exceed unity, got %r" % (label, value))
    return fraction


def _validate_count(value, label, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (label, minimum, value))
    return value


def categorize_defect(code):
    """Return 'major' or 'minor' for a registered construction defect code."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("defect code must be a non-empty string")
    key = code.strip().lower()
    if key in MAJOR_DEFECTS:
        return "major"
    if key in MINOR_DEFECTS:
        return "minor"
    raise ValueError(
        "defect code '%s' is not in the register; add it to the register with a "
        "category rather than letting it pass uncategorized" % key
    )


def categorize_defects(codes):
    """Group a sequence of defect codes into major and minor buckets."""
    if not isinstance(codes, (list, tuple)):
        raise ValueError("codes must be a sequence of defect codes")
    grouped = {"major": [], "minor": []}
    for code in codes:
        grouped[categorize_defect(code)].append(code.strip().lower())
    return grouped


def dpa_sample_size(group_size, fraction=DEFAULT_SAMPLE_FRACTION, minimum=DEFAULT_MIN_SAMPLE):
    """Return the destructive sample size for one date-code group.

    The sample is the sampling fraction of the group rounded up, never below
    the floor, and never above the group size itself.
    """
    group_size = _validate_count(group_size, "group_size")
    minimum = _validate_count(minimum, "minimum")
    fraction = validate_fraction(fraction, "fraction", allow_zero=False)
    proportional = int(math.ceil(group_size * fraction - FRACTION_TOLERANCE))
    return min(group_size, max(minimum, proportional))


def sample_plan(date_code_counts, fraction=DEFAULT_SAMPLE_FRACTION, minimum=DEFAULT_MIN_SAMPLE):
    """Return the per-date-code destructive sample plan for a shipment."""
    if not isinstance(date_code_counts, dict) or not date_code_counts:
        raise ValueError("date_code_counts must be a non-empty mapping of code to count")
    groups = []
    findings = []
    total_units = 0
    total_sample = 0
    for code in sorted(date_code_counts):
        if not isinstance(code, str) or not code.strip():
            raise ValueError("date code must be a non-empty string")
        count = _validate_count(date_code_counts[code], "count for date code '%s'" % code)
        size = dpa_sample_size(count, fraction, minimum)
        if size >= count:
            findings.append(
                "date-code group '%s' holds %d unit(s); a destructive sample of %d "
                "consumes the group" % (code, count, size)
            )
        groups.append({"date_code": code.strip(), "group_size": count, "sample_size": size})
        total_units += count
        total_sample += size
    if len(groups) > 1:
        findings.append(
            "shipment spans %d date codes; each is a separate build and is sampled "
            "on its own" % len(groups)
        )
    return {
        "groups": groups,
        "total_units": total_units,
        "total_sample": total_sample,
        "findings": findings,
    }


def void_assessment(total_void_fraction, largest_void_fraction, limits):
    """Assess die-attach voiding against the declared area-fraction limits.

    limits keys: total_limit, largest_limit (both area fractions).
    """
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping")
    for key in ("total_limit", "largest_limit"):
        if key not in limits:
            raise ValueError("limits missing required key '%s'" % key)
    total_limit = validate_fraction(limits["total_limit"], "total_limit", allow_zero=False)
    largest_limit = validate_fraction(limits["largest_limit"], "largest_limit", allow_zero=False)
    total = validate_fraction(total_void_fraction, "total_void_fraction")
    largest = validate_fraction(largest_void_fraction, "largest_void_fraction")
    if largest > total and not math.isclose(largest, total, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0):
        raise ValueError(
            "largest single void %g cannot exceed the total void fraction %g"
            % (largest, total)
        )
    if largest_limit > total_limit and not math.isclose(
        largest_limit, total_limit, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
    ):
        raise ValueError("largest_limit cannot exceed total_limit")
    defects = []
    if total > total_limit and not math.isclose(
        total, total_limit, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
    ):
        defects.append("die-attach-void-excess")
    if largest > largest_limit and not math.isclose(
        largest, largest_limit, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
    ):
        defects.append("die-attach-void-excess")
    return {
        "total_void_fraction": total,
        "largest_void_fraction": largest,
        "total_limit": total_limit,
        "largest_limit": largest_limit,
        "within_limits": not defects,
        "defects": sorted(set(defects)),
    }


def bond_pull_assessment(pull_values_g, minimum_g, mean_minimum_g):
    """Assess wire bond pull strengths against a floor and a mean floor."""
    if not isinstance(pull_values_g, (list, tuple)) or not pull_values_g:
        raise ValueError("pull_values_g must be a non-empty sequence")
    values = []
    for i, value in enumerate(pull_values_g):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("pull_values_g[%d] must be a real number" % i)
        value = float(value)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("pull_values_g[%d] must be non-negative and finite" % i)
        values.append(value)
    for label, limit in (("minimum_g", minimum_g), ("mean_minimum_g", mean_minimum_g)):
        if not isinstance(limit, (int, float)) or isinstance(limit, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(limit)) or float(limit) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, limit))
    floor = float(minimum_g)
    mean_floor = float(mean_minimum_g)
    if floor > mean_floor and not math.isclose(
        floor, mean_floor, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
    ):
        raise ValueError("minimum_g cannot exceed mean_minimum_g")
    observed_min = min(values)
    observed_mean = math.fsum(values) / len(values)
    defects = []
    if observed_min < floor and not math.isclose(
        observed_min, floor, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
    ):
        defects.append("bond-pull-below-limit")
    if observed_mean < mean_floor and not math.isclose(
        observed_mean, mean_floor, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
    ):
        defects.append("bond-pull-below-limit")
    return {
        "count": len(values),
        "minimum_observed_g": observed_min,
        "mean_observed_g": observed_mean,
        "minimum_limit_g": floor,
        "mean_limit_g": mean_floor,
        "within_limits": not defects,
        "defects": sorted(set(defects)),
    }


def lot_disposition(grouped):
    """Return the lot disposition implied by the grouped defect record."""
    if not isinstance(grouped, dict):
        raise ValueError("grouped must be a mapping with 'major' and 'minor' keys")
    for key in ("major", "minor"):
        if key not in grouped or not isinstance(grouped[key], (list, tuple)):
            raise ValueError("grouped['%s'] must be a sequence" % key)
    if grouped["major"]:
        return "lot-rejected"
    if grouped["minor"]:
        return "lot-accepted-with-record"
    return "lot-accepted"


def assess_destructive_physical_analysis(spec):
    """Run the clause 4.3.9 assessment for one purchased commercial shipment.

    spec keys: date_code_counts, observed_defects, void_limits,
    total_void_fraction, largest_void_fraction, pull_values_g,
    bond_minimum_g, bond_mean_minimum_g; optional sample_fraction,
    minimum_sample.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "date_code_counts",
        "observed_defects",
        "void_limits",
        "total_void_fraction",
        "largest_void_fraction",
        "pull_values_g",
        "bond_minimum_g",
        "bond_mean_minimum_g",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    plan = sample_plan(
        spec["date_code_counts"],
        spec.get("sample_fraction", DEFAULT_SAMPLE_FRACTION),
        spec.get("minimum_sample", DEFAULT_MIN_SAMPLE),
    )
    voids = void_assessment(
        spec["total_void_fraction"], spec["largest_void_fraction"], spec["void_limits"]
    )
    bonds = bond_pull_assessment(
        spec["pull_values_g"], spec["bond_minimum_g"], spec["bond_mean_minimum_g"]
    )
    codes = list(spec["observed_defects"]) + voids["defects"] + bonds["defects"]
    grouped = categorize_defects(codes)
    grouped = {
        "major": sorted(set(grouped["major"])),
        "minor": sorted(set(grouped["minor"])),
    }
    disposition = lot_disposition(grouped)
    findings = list(plan["findings"])
    for code in grouped["major"]:
        findings.append("major construction defect '%s' disposes of the lot" % code)
    for code in grouped["minor"]:
        findings.append("minor observation '%s' recorded against the lot" % code)
    return {
        "sample_plan": plan,
        "void_assessment": voids,
        "bond_pull_assessment": bonds,
        "defects": grouped,
        "disposition": disposition,
        "accepted": disposition != "lot-rejected",
        "findings": findings,
    }
