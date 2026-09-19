"""Testing-machine and extensometry control for metallic mechanical testing.

Anchor: ECSS-Q-ST-70-45 equipment clause -- the control a laboratory keeps over
the testing machine, its force-measuring system, its extensometry and its rate
control before a mechanical test is run. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn each force-verification reading into a relative indication error and
   grade the force-measuring system on its worst reading.
2. Place the planned peak force inside the verified span of that system: above
   the lowest verified force, below the machine capacity.
3. Grade the extensometer on whichever of its relative and absolute errors is
   the worse at the gauge length in use.
4. Turn a required specimen strain rate into the crosshead speed the machine
   has to be driven at, carrying the deflection of the load train so a
   compliant frame is not quietly starved of rate.
5. Turn opposed strain-gauge readings into a bending percentage and grade the
   load-train alignment on it.
6. Aggregate the above into one usable/not-usable statement with a named
   finding for every part that failed.
"""

import math

__all__ = [
    "FORCE_GRADE_LIMITS_PCT",
    "EXTENSOMETER_GRADE_LIMITS",
    "GRADE_TOLERANCE",
    "DEFAULT_MIN_CAPACITY_FRACTION",
    "DEFAULT_MAX_BENDING_PCT",
    "relative_indication_error_pct",
    "force_system_grade",
    "extensometer_grade",
    "grade_meets_requirement",
    "force_range_findings",
    "crosshead_speed_mm_per_min",
    "bending_percent",
    "alignment_finding",
    "assess_machine_control",
]

# Worst permitted relative indication error, in percent, for each grade of a
# force-measuring system. Finest grade first.
FORCE_GRADE_LIMITS_PCT = (
    ("0.5", 0.5),
    ("1", 1.0),
    ("2", 2.0),
    ("3", 3.0),
)

# Extensometer grades: (grade, max relative error percent, max absolute error
# in micrometres). An extensometer has to satisfy whichever of the two is
# binding at the gauge length in use, which is the relative one on a long
# gauge length and the absolute one on a short one.
EXTENSOMETER_GRADE_LIMITS = (
    ("0.5", 0.5, 1.5),
    ("1", 1.0, 3.0),
    ("2", 2.0, 7.0),
)

# Grading is a comparison of a measured error against a round limit. An error
# that is physically exactly on the limit can land a few ULP either side of it,
# so absorb the representation error here rather than by moving the limit.
GRADE_TOLERANCE = 1e-12

# Below this fraction of the verified capacity a force reading carries the
# accuracy of the bottom of the range, not of the grade.
DEFAULT_MIN_CAPACITY_FRACTION = 0.02

# Bending on the load train, as a percentage of the axial strain.
DEFAULT_MAX_BENDING_PCT = 5.0


def _positive(label, value):
    """Return value as a positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def relative_indication_error_pct(indicated, reference):
    """Return the relative indication error of one verification reading, in percent."""
    ref = _positive("reference force", reference)
    if not isinstance(indicated, (int, float)) or isinstance(indicated, bool):
        raise ValueError("indicated force must be a real number, got %r" % (indicated,))
    ind = float(indicated)
    if not math.isfinite(ind):
        raise ValueError("indicated force must be finite, got %r" % (indicated,))
    return 100.0 * (ind - ref) / ref


def _grade_from_table(worst_error_pct, table):
    """Return the finest grade whose limit covers the worst error, else None."""
    for grade, limit in table:
        if worst_error_pct < limit or math.isclose(
            worst_error_pct, limit, rel_tol=0.0, abs_tol=GRADE_TOLERANCE
        ):
            return grade
    return None


def force_system_grade(readings):
    """Grade a force-measuring system from its verification readings.

    readings: sequence of (indicated, reference) force pairs in any one unit.
    Returns {"worst_error_pct", "grade"}; grade is None when the worst reading
    is outside the coarsest tabulated grade.
    """
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence of (indicated, reference) pairs")
    worst = 0.0
    for index, item in enumerate(readings):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("readings[%d] must be an (indicated, reference) pair" % index)
        error = abs(relative_indication_error_pct(item[0], item[1]))
        if error > worst:
            worst = error
    return {"worst_error_pct": worst, "grade": _grade_from_table(worst, FORCE_GRADE_LIMITS_PCT)}


def extensometer_grade(relative_error_pct, absolute_error_um, gauge_length_mm,
                       strain_reading=0.002):
    """Grade an extensometer at the gauge length and strain level in use.

    The absolute error is turned into an equivalent relative error at the
    reading of interest, and the binding one of the two decides the grade.
    """
    rel = _non_negative("relative_error_pct", relative_error_pct)
    absolute_um = _non_negative("absolute_error_um", absolute_error_um)
    length = _positive("gauge_length_mm", gauge_length_mm)
    reading = _positive("strain_reading", strain_reading)
    extension_mm = reading * length
    equivalent_rel = 100.0 * (absolute_um / 1000.0) / extension_mm
    binding = "relative" if rel >= equivalent_rel else "absolute"
    candidates = []
    for grade, rel_limit, abs_limit in EXTENSOMETER_GRADE_LIMITS:
        rel_ok = rel < rel_limit or math.isclose(
            rel, rel_limit, rel_tol=0.0, abs_tol=GRADE_TOLERANCE
        )
        abs_ok = absolute_um < abs_limit or math.isclose(
            absolute_um, abs_limit, rel_tol=0.0, abs_tol=GRADE_TOLERANCE
        )
        if rel_ok and abs_ok:
            candidates.append(grade)
    return {
        "grade": candidates[0] if candidates else None,
        "relative_error_pct": rel,
        "absolute_error_um": absolute_um,
        "equivalent_relative_pct": equivalent_rel,
        "binding_error": binding,
    }


def grade_meets_requirement(grade, required_grade, table=FORCE_GRADE_LIMITS_PCT):
    """Return True when grade is no coarser than required_grade."""
    order = [name for name, _limit in table]
    if required_grade not in order:
        raise ValueError("required grade %r is not one of %s" % (required_grade, order))
    if grade is None:
        return False
    if grade not in order:
        raise ValueError("grade %r is not one of %s" % (grade, order))
    return order.index(grade) <= order.index(required_grade)


def force_range_findings(peak_force, capacity, lowest_verified_force=None,
                         min_capacity_fraction=DEFAULT_MIN_CAPACITY_FRACTION):
    """Place the planned peak force inside the verified span of the machine."""
    peak = _positive("peak_force", peak_force)
    cap = _positive("capacity", capacity)
    fraction = _positive("min_capacity_fraction", min_capacity_fraction)
    if fraction >= 1.0:
        raise ValueError("min_capacity_fraction must be below one, got %r" % (min_capacity_fraction,))
    floor = cap * fraction if lowest_verified_force is None else _positive(
        "lowest_verified_force", lowest_verified_force
    )
    findings = []
    if peak > cap and not math.isclose(peak, cap, rel_tol=1e-12, abs_tol=0.0):
        findings.append(
            "planned peak force %g exceeds the machine capacity %g" % (peak, cap)
        )
    if peak < floor and not math.isclose(peak, floor, rel_tol=1e-12, abs_tol=0.0):
        findings.append(
            "planned peak force %g is below the lowest verified force %g; the reading "
            "carries the accuracy of the bottom of the range" % (peak, floor)
        )
    return {
        "utilisation": peak / cap,
        "lowest_verified_force": floor,
        "findings": findings,
    }


def crosshead_speed_mm_per_min(strain_rate_per_s, gauge_length_mm,
                               compliance_mm_per_kn=0.0, force_rate_kn_per_s=0.0):
    """Return the crosshead speed that delivers a strain rate at the specimen.

    The crosshead has to cover the extension of the parallel length plus the
    deflection the load train takes up at the force rate of the moment.
    """
    rate = _positive("strain_rate_per_s", strain_rate_per_s)
    length = _positive("gauge_length_mm", gauge_length_mm)
    compliance = _non_negative("compliance_mm_per_kn", compliance_mm_per_kn)
    force_rate = _non_negative("force_rate_kn_per_s", force_rate_kn_per_s)
    specimen_mm_per_s = rate * length
    train_mm_per_s = compliance * force_rate
    return 60.0 * (specimen_mm_per_s + train_mm_per_s)


def bending_percent(opposed_strains):
    """Return the bending strain as a percentage of the mean axial strain."""
    if not isinstance(opposed_strains, (list, tuple)) or len(opposed_strains) < 2:
        raise ValueError("opposed_strains needs at least two gauge readings")
    values = []
    for index, item in enumerate(opposed_strains):
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            raise ValueError("opposed_strains[%d] must be a real number" % index)
        number = float(item)
        if not math.isfinite(number):
            raise ValueError("opposed_strains[%d] must be finite" % index)
        values.append(number)
    mean = sum(values) / len(values)
    if mean <= 0.0:
        raise ValueError("mean axial strain must be positive, got %g" % mean)
    return 100.0 * (max(values) - min(values)) / (2.0 * mean)


def alignment_finding(opposed_strains, max_bending_pct=DEFAULT_MAX_BENDING_PCT):
    """Grade load-train alignment on the bending percentage of opposed gauges."""
    limit = _positive("max_bending_pct", max_bending_pct)
    measured = bending_percent(opposed_strains)
    within = measured < limit or math.isclose(
        measured, limit, rel_tol=0.0, abs_tol=GRADE_TOLERANCE
    )
    finding = None
    if not within:
        finding = (
            "load-train bending %.3f%% exceeds the alignment limit %.3f%%"
            % (measured, limit)
        )
    return {"bending_pct": measured, "within_limit": within, "finding": finding}


def assess_machine_control(spec):
    """Run the whole equipment-control assessment for one planned test.

    spec keys: force_readings, peak_force, capacity, required_force_grade,
    extensometer (mapping), required_extensometer_grade, strain_rate_per_s,
    gauge_length_mm, and optionally lowest_verified_force, compliance_mm_per_kn,
    force_rate_kn_per_s, opposed_strains, max_bending_pct.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "force_readings",
        "peak_force",
        "capacity",
        "required_force_grade",
        "extensometer",
        "required_extensometer_grade",
        "strain_rate_per_s",
        "gauge_length_mm",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    findings = []

    force = force_system_grade(spec["force_readings"])
    if not grade_meets_requirement(
        force["grade"], spec["required_force_grade"], FORCE_GRADE_LIMITS_PCT
    ):
        findings.append(
            "force-measuring system grades %s against a required grade %s"
            % (force["grade"] or "outside the tabulated grades", spec["required_force_grade"])
        )

    span = force_range_findings(
        spec["peak_force"],
        spec["capacity"],
        spec.get("lowest_verified_force"),
        spec.get("min_capacity_fraction", DEFAULT_MIN_CAPACITY_FRACTION),
    )
    findings.extend(span["findings"])

    ext_spec = spec["extensometer"]
    if not isinstance(ext_spec, dict):
        raise ValueError("spec['extensometer'] must be a mapping")
    for key in ("relative_error_pct", "absolute_error_um"):
        if key not in ext_spec:
            raise ValueError("extensometer mapping missing '%s'" % key)
    extensometer = extensometer_grade(
        ext_spec["relative_error_pct"],
        ext_spec["absolute_error_um"],
        spec["gauge_length_mm"],
        ext_spec.get("strain_reading", 0.002),
    )
    ext_order = [name for name, _r, _a in EXTENSOMETER_GRADE_LIMITS]
    wanted = spec["required_extensometer_grade"]
    if wanted not in ext_order:
        raise ValueError("required extensometer grade %r is not one of %s" % (wanted, ext_order))
    ext_ok = (
        extensometer["grade"] is not None
        and ext_order.index(extensometer["grade"]) <= ext_order.index(wanted)
    )
    if not ext_ok:
        findings.append(
            "extensometer grades %s against a required grade %s, bound by its %s error"
            % (
                extensometer["grade"] or "outside the tabulated grades",
                wanted,
                extensometer["binding_error"],
            )
        )

    speed = crosshead_speed_mm_per_min(
        spec["strain_rate_per_s"],
        spec["gauge_length_mm"],
        spec.get("compliance_mm_per_kn", 0.0),
        spec.get("force_rate_kn_per_s", 0.0),
    )

    alignment = None
    if spec.get("opposed_strains") is not None:
        alignment = alignment_finding(
            spec["opposed_strains"],
            spec.get("max_bending_pct", DEFAULT_MAX_BENDING_PCT),
        )
        if alignment["finding"]:
            findings.append(alignment["finding"])

    return {
        "force_system": force,
        "force_span": span,
        "extensometer": extensometer,
        "crosshead_speed_mm_per_min": speed,
        "alignment": alignment,
        "findings": findings,
        "usable": not findings,
    }
