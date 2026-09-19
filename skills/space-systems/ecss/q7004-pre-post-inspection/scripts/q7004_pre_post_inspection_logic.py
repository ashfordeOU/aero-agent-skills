"""Pre-test and post-test inspection of a thermally tested item.

Anchor: ECSS-Q-ST-70-04C, the evaluation clauses requiring that the item be
inspected before and after the thermal test so that damage, distortion and
degradation caused by the test are separable from what the item arrived with.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Compare the recorded dimensions before and after against the distortion
   tolerance declared for each one.
2. Compare the defect registers: defects present after that were not present
   before, defects that grew beyond the growth tolerance, and defects recorded
   before that the post-test register does not account for.
3. Reduce the mass records to a signed change fraction and compare it with the
   loss the campaign allows.
4. Reduce each performance reading pair to a degradation fraction and compare
   it with its own allowance.
5. Group the anomalies by what they permit and return a disposition of accept,
   review or reject with the findings behind it.
"""

import math

__all__ = [
    "CRITICAL_DEFECT_KINDS",
    "DEFECT_KINDS",
    "COMPARISON_TOLERANCE",
    "validate_defect",
    "index_defects",
    "dimension_comparison",
    "defect_comparison",
    "mass_change_fraction",
    "performance_degradation",
    "disposition_for",
    "assess_pre_post_inspection",
]

# Defect kinds a thermal test can leave behind or make worse.
DEFECT_KINDS = (
    "crack",
    "delamination",
    "fracture",
    "deformation",
    "coating-loss",
    "discolouration",
)

# The kinds that make the item unusable when they appear or grow, whatever the
# rest of the inspection says.
CRITICAL_DEFECT_KINDS = ("crack", "delamination", "fracture")

# Dimensions, masses and fractions are floats; a value sitting on a tolerance
# is compared within this tolerance rather than by widening the tolerance.
COMPARISON_TOLERANCE = 1e-9

_DISPOSITIONS = ("accept", "review", "reject")


def _as_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _non_negative(value, label):
    out = _as_float(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def validate_defect(defect):
    """Return the validated record of one registered defect."""
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping")
    for key in ("id", "kind", "size_mm"):
        if key not in defect:
            raise ValueError("defect missing required key '%s'" % key)
    identity = defect["id"]
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("defect id must be a non-empty string")
    kind = defect["kind"]
    if kind not in DEFECT_KINDS:
        raise ValueError(
            "defect %s has kind %r, expected one of %s"
            % (identity, kind, ", ".join(DEFECT_KINDS))
        )
    return {
        "id": identity.strip(),
        "kind": kind,
        "size_mm": _non_negative(defect["size_mm"], "size_mm of defect %s" % identity),
        "location": defect.get("location", "unrecorded"),
    }


def index_defects(defects, label="register"):
    """Return the defect register keyed by defect identifier."""
    if not isinstance(defects, (list, tuple)):
        raise ValueError("%s must be a sequence of defect records" % label)
    indexed = {}
    for defect in defects:
        record = validate_defect(defect)
        if record["id"] in indexed:
            raise ValueError("%s lists defect '%s' twice" % (label, record["id"]))
        indexed[record["id"]] = record
    return indexed


def dimension_comparison(pre_dimensions, post_dimensions, tolerances):
    """Compare the before and after dimensions against the distortion tolerances."""
    for label, mapping in (
        ("pre_dimensions", pre_dimensions),
        ("post_dimensions", post_dimensions),
        ("tolerances", tolerances),
    ):
        if not isinstance(mapping, dict):
            raise ValueError("%s must be a mapping" % label)
    if not tolerances:
        raise ValueError("at least one dimension tolerance is required")
    results = []
    for name in sorted(tolerances):
        tolerance = _non_negative(tolerances[name], "tolerance of '%s'" % name)
        if name not in pre_dimensions or name not in post_dimensions:
            results.append(
                {
                    "dimension": name,
                    "distortion_mm": None,
                    "tolerance_mm": tolerance,
                    "within_tolerance": False,
                    "measured_both": False,
                }
            )
            continue
        before = _as_float(pre_dimensions[name], "pre dimension '%s'" % name)
        after = _as_float(post_dimensions[name], "post dimension '%s'" % name)
        distortion = abs(after - before)
        results.append(
            {
                "dimension": name,
                "pre_mm": before,
                "post_mm": after,
                "distortion_mm": distortion,
                "tolerance_mm": tolerance,
                "within_tolerance": distortion <= tolerance + COMPARISON_TOLERANCE,
                "measured_both": True,
            }
        )
    return results


def defect_comparison(pre_defects, post_defects, growth_tolerance_mm):
    """Compare the two defect registers and group what changed."""
    growth = _non_negative(growth_tolerance_mm, "growth_tolerance_mm")
    before = index_defects(pre_defects, "pre-test register")
    after = index_defects(post_defects, "post-test register")
    new = []
    grown = []
    unchanged = []
    unaccounted = []
    for identity in sorted(after):
        record = after[identity]
        if identity not in before:
            new.append(record)
            continue
        increase = record["size_mm"] - before[identity]["size_mm"]
        if increase > growth + COMPARISON_TOLERANCE:
            entry = dict(record)
            entry["growth_mm"] = increase
            entry["pre_size_mm"] = before[identity]["size_mm"]
            grown.append(entry)
        else:
            unchanged.append(record)
    for identity in sorted(before):
        if identity not in after:
            unaccounted.append(before[identity])
    critical = [
        record
        for record in new + grown
        if record["kind"] in CRITICAL_DEFECT_KINDS
    ]
    return {
        "new": new,
        "grown": grown,
        "unchanged": unchanged,
        "unaccounted": unaccounted,
        "critical": critical,
    }


def mass_change_fraction(pre_mass_g, post_mass_g):
    """Return the signed mass change as a fraction of the pre-test mass."""
    before = _as_float(pre_mass_g, "pre_mass_g")
    after = _as_float(post_mass_g, "post_mass_g")
    if before <= 0.0:
        raise ValueError("pre_mass_g must be positive, got %g" % before)
    if after < 0.0:
        raise ValueError("post_mass_g must be non-negative, got %g" % after)
    return (after - before) / before


def performance_degradation(pre_value, post_value):
    """Return the magnitude of the relative change in a performance reading."""
    before = _as_float(pre_value, "pre_value")
    after = _as_float(post_value, "post_value")
    if before == 0.0:
        raise ValueError("degradation is undefined against a zero pre-test reading")
    return abs(after - before) / abs(before)


def disposition_for(blocking, reviewable):
    """Return the disposition implied by the two anomaly groups."""
    if not isinstance(blocking, (list, tuple)) or not isinstance(reviewable, (list, tuple)):
        raise ValueError("both anomaly groups must be sequences")
    if blocking:
        return "reject"
    if reviewable:
        return "review"
    return "accept"


def assess_pre_post_inspection(spec):
    """Judge one item against its pre-test and post-test inspection records.

    spec keys: pre_dimensions, post_dimensions, dimension_tolerances,
    pre_defects, post_defects, defect_growth_tolerance_mm, pre_mass_g,
    post_mass_g, allowable_mass_loss_fraction, optional performance mapping of
    name to {pre, post, allowable_fraction}.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("pre_dimensions", "post_dimensions", "dimension_tolerances",
                "pre_defects", "post_defects", "defect_growth_tolerance_mm",
                "pre_mass_g", "post_mass_g", "allowable_mass_loss_fraction"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    allowable_loss = _non_negative(
        spec["allowable_mass_loss_fraction"], "allowable_mass_loss_fraction"
    )

    dimensions = dimension_comparison(
        spec["pre_dimensions"], spec["post_dimensions"], spec["dimension_tolerances"]
    )
    defects = defect_comparison(
        spec["pre_defects"], spec["post_defects"], spec["defect_growth_tolerance_mm"]
    )
    change = mass_change_fraction(spec["pre_mass_g"], spec["post_mass_g"])
    loss = max(0.0, -change)
    mass_within = loss < allowable_loss + COMPARISON_TOLERANCE

    performance_results = []
    performance = spec.get("performance")
    if performance is not None:
        if not isinstance(performance, dict):
            raise ValueError("performance must be a mapping of parameter to readings")
        for name in sorted(performance):
            entry = performance[name]
            if not isinstance(entry, dict):
                raise ValueError("performance['%s'] must be a mapping" % name)
            for key in ("pre", "post", "allowable_fraction"):
                if key not in entry:
                    raise ValueError("performance['%s'] missing '%s'" % (name, key))
            allowed = _non_negative(
                entry["allowable_fraction"], "allowable_fraction of '%s'" % name
            )
            degradation = performance_degradation(entry["pre"], entry["post"])
            performance_results.append(
                {
                    "parameter": name,
                    "degradation": degradation,
                    "allowable_fraction": allowed,
                    "acceptable": degradation < allowed + COMPARISON_TOLERANCE,
                }
            )

    blocking = []
    reviewable = []
    findings = []

    for result in dimensions:
        if not result["measured_both"]:
            reviewable.append("dimension '%s' not measured at both inspections" % result["dimension"])
            findings.append(
                "dimension '%s' is missing from one of the inspection records"
                % result["dimension"]
            )
        elif not result["within_tolerance"]:
            blocking.append("dimension '%s' distorted" % result["dimension"])
            findings.append(
                "dimension '%s' moved %.4f mm against a tolerance of %.4f mm"
                % (result["dimension"], result["distortion_mm"], result["tolerance_mm"])
            )

    for record in defects["critical"]:
        blocking.append("critical defect '%s'" % record["id"])
    for record in defects["new"]:
        findings.append(
            "post-test register adds a %s at %s (%s), %.3f mm"
            % (record["kind"], record["location"], record["id"], record["size_mm"])
        )
        if record["kind"] not in CRITICAL_DEFECT_KINDS:
            reviewable.append("new defect '%s'" % record["id"])
    for record in defects["grown"]:
        findings.append(
            "defect %s grew from %.3f mm to %.3f mm"
            % (record["id"], record["pre_size_mm"], record["size_mm"])
        )
        if record["kind"] not in CRITICAL_DEFECT_KINDS:
            reviewable.append("grown defect '%s'" % record["id"])
    for record in defects["unaccounted"]:
        reviewable.append("unaccounted pre-test defect '%s'" % record["id"])
        findings.append(
            "defect %s was registered before the test and is absent afterwards"
            % record["id"]
        )

    if not mass_within:
        reviewable.append("mass loss")
        findings.append(
            "mass loss of %.5f exceeds the allowed %.5f" % (loss, allowable_loss)
        )

    for result in performance_results:
        if not result["acceptable"]:
            reviewable.append("degradation of '%s'" % result["parameter"])
            findings.append(
                "'%s' degraded by %.5f against an allowance of %.5f"
                % (result["parameter"], result["degradation"], result["allowable_fraction"])
            )

    disposition = disposition_for(blocking, reviewable)
    if disposition not in _DISPOSITIONS:
        raise ValueError("internal disposition error: %r" % (disposition,))
    return {
        "dimensions": dimensions,
        "defects": defects,
        "mass_change_fraction": change,
        "mass_loss_fraction": loss,
        "mass_within_allowance": mass_within,
        "performance": performance_results,
        "blocking": blocking,
        "reviewable": reviewable,
        "disposition": disposition,
        "findings": findings,
    }
