#!/usr/bin/env python3
"""Coating adhesion held against a test standard the customer accepted.

Anchor: ECSS-E-ST-20-08C clause 8.7.18. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause does not name an adhesion test. It says the adhesion of the
coverglass coating is shown against a test standard the customer has
accepted, and that wording carries the whole weight: a result from a
method nobody agreed to in advance is not a weaker result, it is not a
result. So the first thing this module does is refuse a nomination the
customer's accepted list does not contain, before any arithmetic runs.

Once a standard is nominated from that list, the method family it
prescribes decides what evidence the run owes and what its numbers mean

    tape-peel           adhesive tape of a stated peel strength applied,
                        dwelled and removed at a stated angle; the
                        result is the share of the tested area the
                        coating left with the tape
    cross-cut-lattice   a lattice cut through the coating to the glass;
                        the result is the share of the squares that
                        detached, banded into an adhesion grade
    pull-off-stud       a stud bonded to the coating and pulled; the
                        result is a stress, and it is only the coating's
                        stress if the glue was not the weakest link

The three families are not interchangeable and their numbers do not
convert into one another, which is exactly why the customer's accepted
list is the gate rather than a preference.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TAPE_PEEL = "tape-peel"
CROSS_CUT_LATTICE = "cross-cut-lattice"
PULL_OFF_STUD = "pull-off-stud"

METHOD_FAMILIES = (TAPE_PEEL, CROSS_CUT_LATTICE, PULL_OFF_STUD)

REQUIRED_EVIDENCE_BY_FAMILY = {
    TAPE_PEEL: (
        "dwell_time_s",
        "removal_angle_deg",
        "removed_coating_area_mm2",
        "tape_peel_strength_n_per_25mm",
        "tested_area_mm2",
    ),
    CROSS_CUT_LATTICE: (
        "coating_thickness_um",
        "cut_spacing_mm",
        "cuts_per_axis",
        "detached_squares",
    ),
    PULL_OFF_STUD: (
        "failure_mode",
        "pull_force_n",
        "required_pull_off_stress_mpa",
        "stud_diameter_mm",
    ),
}

#: Tape peel strength band. Weak tape under-tests; aggressive tape
#: strips coatings that were adherent enough for the application.
MIN_TAPE_PEEL_STRENGTH_N_PER_25MM = 6.0
MAX_TAPE_PEEL_STRENGTH_N_PER_25MM = 12.0

#: Seconds the tape sits before removal, so the adhesive has wetted out.
MIN_TAPE_DWELL_TIME_S = 60.0

#: Removal angles the tape families use, and the tolerance around them.
ACCEPTED_REMOVAL_ANGLES_DEG = (90.0, 180.0)
REMOVAL_ANGLE_TOLERANCE_DEG = 5.0

#: Share of the tested area the coating may leave with the tape.
MAX_TAPE_REMOVAL_FRACTION = 0.005

#: Lattice cut spacing as a function of coating thickness.
CUT_SPACING_BY_THICKNESS_UM = (
    (60.0, 1.0),
    (120.0, 2.0),
)
THICK_COATING_CUT_SPACING_MM = 3.0
CUT_SPACING_TOLERANCE_MM = 0.05

#: Adhesion grade bands, best first, each an upper detached share.
ADHESION_GRADE_BANDS = (
    (0, 0.0),
    (1, 0.05),
    (2, 0.15),
    (3, 0.35),
    (4, 0.65),
)
WORST_ADHESION_GRADE = 5
DEFAULT_MAX_ACCEPTED_GRADE = 1

#: Pull-off failure modes that say something about the coating bond.
CONCLUSIVE_FAILURE_MODES = (
    "adhesive-coating-to-glass",
    "cohesive-within-coating",
    "cohesive-within-substrate",
)
#: A glue failure only bounds the coating bond from below.
INCONCLUSIVE_FAILURE_MODES = (
    "adhesive-glue-to-stud",
    "adhesive-glue-to-coating",
)
FAILURE_MODES = CONCLUSIVE_FAILURE_MODES + INCONCLUSIVE_FAILURE_MODES

ADHESION_ACCEPTED = "coating-adhesion-accepted"
ADHESION_NOT_ACCEPTED = "coating-adhesion-not-accepted"
ADHESION_RUN_VOID = "coating-adhesion-run-void"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A pull-off stress is a force divided by a squared diameter and a
    detached share is a ratio of integer counts rescaled, so a run cut
    to land on a limit can arrive a few units in the last place either
    side of it. The limit is never relaxed; only the comparison
    tolerates the representation error, which is why no caller here
    uses a bare >= on a derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _accepted_list(customer_accepted_standards):
    if not isinstance(customer_accepted_standards, dict):
        raise ValueError(
            "customer_accepted_standards must be a mapping of standard to "
            "method family, got %r" % (customer_accepted_standards,)
        )
    if not customer_accepted_standards:
        raise ValueError(
            "the customer has accepted no adhesion test standard; nothing can "
            "be shown against an empty list"
        )
    for standard, family in customer_accepted_standards.items():
        if not isinstance(standard, str) or not standard:
            raise ValueError("accepted standard name must be text, got %r" % (standard,))
        if family not in METHOD_FAMILIES:
            raise ValueError(
                "accepted standard %r names an unhandled method family %r; "
                "handled families are %s"
                % (standard, family, ", ".join(METHOD_FAMILIES))
            )
    return customer_accepted_standards


def nominate_accepted_standard(nominated, customer_accepted_standards):
    """Reduce a nomination to one standard the customer has accepted.

    Two standards left open produce two results with no rule for
    reconciling them, and a standard outside the accepted list produces
    a number the customer never agreed to read. Both are refused at the
    input rather than resolved later by preference.
    """
    accepted = _accepted_list(customer_accepted_standards)
    if isinstance(nominated, str):
        candidates = (nominated,)
    elif isinstance(nominated, (list, tuple)):
        candidates = tuple(nominated)
    else:
        raise ValueError(
            "nominated standard must be a name or a sequence of names, got %r"
            % (nominated,)
        )
    if len(candidates) != 1:
        raise ValueError(
            "exactly one adhesion test standard must be nominated, got %d"
            % len(candidates)
        )
    standard = candidates[0]
    if standard not in accepted:
        raise ValueError(
            "standard %r is not on the customer's accepted list (%s); the "
            "clause asks for adhesion shown against an accepted standard"
            % (standard, ", ".join(sorted(accepted)))
        )
    return standard


def method_family(standard, customer_accepted_standards):
    """Method family the nominated accepted standard prescribes."""
    accepted = _accepted_list(customer_accepted_standards)
    if standard not in accepted:
        raise ValueError(
            "standard %r is not on the customer's accepted list" % (standard,)
        )
    return accepted[standard]


def required_evidence(family):
    """Evidence the method family owes before its result can be read."""
    if family not in REQUIRED_EVIDENCE_BY_FAMILY:
        raise ValueError(
            "unhandled method family %r; handled families are %s"
            % (family, ", ".join(METHOD_FAMILIES))
        )
    return tuple(sorted(REQUIRED_EVIDENCE_BY_FAMILY[family]))


def missing_evidence(family, evidence):
    """Required inputs the family needs and the run has not brought."""
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping, got %r" % (evidence,))
    return tuple(
        name for name in required_evidence(family) if evidence.get(name) is None
    )


def removed_area_fraction(removed_area_mm2, tested_area_mm2):
    """Share of the tested area the coating left with the tape."""
    removed = _require_non_negative("removed_coating_area_mm2", removed_area_mm2)
    tested = _require_positive("tested_area_mm2", tested_area_mm2)
    if removed > tested:
        raise ValueError(
            "removed area %g mm2 exceeds the tested area %g mm2" % (removed, tested)
        )
    return removed / tested


def tape_is_within_band(peel_strength_n_per_25mm):
    """Whether the tape's own peel strength makes it a valid instrument."""
    strength = _require_positive(
        "tape_peel_strength_n_per_25mm", peel_strength_n_per_25mm
    )
    return _at_least(strength, MIN_TAPE_PEEL_STRENGTH_N_PER_25MM) and _at_most(
        strength, MAX_TAPE_PEEL_STRENGTH_N_PER_25MM
    )


def removal_angle_is_accepted(angle_deg):
    """Whether the tape came off at one of the angles the families use."""
    angle = _require_non_negative("removal_angle_deg", angle_deg)
    return any(
        _at_most(abs(angle - nominal), REMOVAL_ANGLE_TOLERANCE_DEG)
        for nominal in ACCEPTED_REMOVAL_ANGLES_DEG
    )


def lattice_square_count(cuts_per_axis):
    """Squares a lattice of n parallel cuts per axis encloses."""
    cuts = _require_count("cuts_per_axis", cuts_per_axis, minimum=2)
    return (cuts - 1) * (cuts - 1)


def detached_square_fraction(detached_squares, cuts_per_axis):
    """Share of the lattice squares that came away from the glass."""
    squares = lattice_square_count(cuts_per_axis)
    detached = _require_count("detached_squares", detached_squares, minimum=0)
    if detached > squares:
        raise ValueError(
            "%d detached squares exceeds the %d the lattice encloses"
            % (detached, squares)
        )
    return detached / float(squares)


def adhesion_grade(detached_fraction):
    """Band the detached share into an adhesion grade, best grade zero."""
    fraction = _require_non_negative("detached_fraction", detached_fraction)
    if fraction > 1.0:
        raise ValueError(
            "detached_fraction must be a share at or below one, got %r"
            % (detached_fraction,)
        )
    for grade, upper in ADHESION_GRADE_BANDS:
        if _at_most(fraction, upper):
            return grade
    return WORST_ADHESION_GRADE


def required_cut_spacing_mm(coating_thickness_um):
    """Lattice spacing the coating thickness calls for."""
    thickness = _require_positive("coating_thickness_um", coating_thickness_um)
    for upper_thickness, spacing in CUT_SPACING_BY_THICKNESS_UM:
        if _at_most(thickness, upper_thickness):
            return spacing
    return THICK_COATING_CUT_SPACING_MM


def cut_spacing_is_correct(cut_spacing_mm, coating_thickness_um):
    """Whether the lattice was cut at the spacing the coating calls for."""
    spacing = _require_positive("cut_spacing_mm", cut_spacing_mm)
    required = required_cut_spacing_mm(coating_thickness_um)
    return _at_most(abs(spacing - required), CUT_SPACING_TOLERANCE_MM)


def pull_off_stress_mpa(pull_force_n, stud_diameter_mm):
    """Stress the stud pull put across the bonded face, in megapascals."""
    force = _require_positive("pull_force_n", pull_force_n)
    diameter = _require_positive("stud_diameter_mm", stud_diameter_mm)
    area_mm2 = math.pi * diameter * diameter / 4.0
    return force / area_mm2


def failure_mode_is_conclusive(failure_mode):
    """Whether the break said anything about the coating's own bond.

    A glue failure only says the coating held at least as well as the
    adhesive did. That is a lower bound, and a lower bound below the
    requirement is not a pass hiding inside a technicality.
    """
    if failure_mode not in FAILURE_MODES:
        raise ValueError(
            "unknown failure_mode %r; handled modes are %s"
            % (failure_mode, ", ".join(FAILURE_MODES))
        )
    return failure_mode in CONCLUSIVE_FAILURE_MODES


def assess_coating_adhesion(case):
    """Full clause 8.7.18 judgement of one coating adhesion run."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    accepted_standards = case.get("customer_accepted_standards")
    standard = nominate_accepted_standard(
        case.get("nominated_standard"), accepted_standards
    )
    family = method_family(standard, accepted_standards)
    evidence = case.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping, got %r" % (evidence,))
    absent = missing_evidence(family, evidence)
    if absent:
        raise ValueError(
            "%s run under %s is missing required evidence: %s"
            % (family, standard, ", ".join(absent))
        )

    voids = []
    findings = []
    detail = {}

    if family == TAPE_PEEL:
        strength = evidence["tape_peel_strength_n_per_25mm"]
        dwell = _require_non_negative("dwell_time_s", evidence["dwell_time_s"])
        angle_ok = removal_angle_is_accepted(evidence["removal_angle_deg"])
        tape_ok = tape_is_within_band(strength)
        removed = removed_area_fraction(
            evidence["removed_coating_area_mm2"], evidence["tested_area_mm2"]
        )
        detail["tape_within_band"] = tape_ok
        detail["removal_angle_accepted"] = angle_ok
        detail["dwell_time_s"] = dwell
        detail["removed_area_fraction"] = removed
        if not tape_ok:
            voids.append(
                "tape peel strength %.2f N per 25 mm is outside the %.1f to "
                "%.1f band; the instrument is not the specified one"
                % (
                    float(strength),
                    MIN_TAPE_PEEL_STRENGTH_N_PER_25MM,
                    MAX_TAPE_PEEL_STRENGTH_N_PER_25MM,
                )
            )
        if not _at_least(dwell, MIN_TAPE_DWELL_TIME_S):
            voids.append(
                "tape dwelled %.0f s against the %.0f s minimum; the adhesive "
                "had not wetted out when it was pulled"
                % (dwell, MIN_TAPE_DWELL_TIME_S)
            )
        if not angle_ok:
            voids.append(
                "tape was removed at %.1f degrees, which is neither of the "
                "accepted angles" % float(evidence["removal_angle_deg"])
            )
        if not _at_most(removed, MAX_TAPE_REMOVAL_FRACTION):
            findings.append(
                "coating left %.3f%% of the tested area with the tape, above "
                "the %.3f%% ceiling"
                % (removed * 100.0, MAX_TAPE_REMOVAL_FRACTION * 100.0)
            )

    elif family == CROSS_CUT_LATTICE:
        spacing_ok = cut_spacing_is_correct(
            evidence["cut_spacing_mm"], evidence["coating_thickness_um"]
        )
        squares = lattice_square_count(evidence["cuts_per_axis"])
        fraction = detached_square_fraction(
            evidence["detached_squares"], evidence["cuts_per_axis"]
        )
        grade = adhesion_grade(fraction)
        max_grade = _require_count(
            "max_accepted_grade",
            case.get("max_accepted_grade", DEFAULT_MAX_ACCEPTED_GRADE),
            minimum=0,
        )
        detail["cut_spacing_correct"] = spacing_ok
        detail["required_cut_spacing_mm"] = required_cut_spacing_mm(
            evidence["coating_thickness_um"]
        )
        detail["lattice_squares"] = squares
        detail["detached_square_fraction"] = fraction
        detail["adhesion_grade"] = grade
        detail["max_accepted_grade"] = max_grade
        if not spacing_ok:
            voids.append(
                "lattice cut at %.2f mm where the %.2f um coating calls for "
                "%.2f mm; the grade bands do not apply to this lattice"
                % (
                    float(evidence["cut_spacing_mm"]),
                    float(evidence["coating_thickness_um"]),
                    detail["required_cut_spacing_mm"],
                )
            )
        if grade > max_grade:
            findings.append(
                "adhesion grade %d is worse than the grade %d the customer "
                "accepts, on %.1f%% of the lattice squares detaching"
                % (grade, max_grade, fraction * 100.0)
            )

    else:
        stress = pull_off_stress_mpa(
            evidence["pull_force_n"], evidence["stud_diameter_mm"]
        )
        required = _require_positive(
            "required_pull_off_stress_mpa", evidence["required_pull_off_stress_mpa"]
        )
        conclusive = failure_mode_is_conclusive(evidence["failure_mode"])
        meets = _at_least(stress, required)
        detail["pull_off_stress_mpa"] = stress
        detail["required_pull_off_stress_mpa"] = required
        detail["failure_mode"] = evidence["failure_mode"]
        detail["failure_mode_conclusive"] = conclusive
        detail["stress_meets_requirement"] = meets
        if not conclusive and not meets:
            voids.append(
                "the glue was the weakest link at %.2f MPa, below the %.2f MPa "
                "required; the run bounds the coating bond from below and "
                "settles nothing" % (stress, required)
            )
        elif not meets:
            findings.append(
                "pull-off stress %.2f MPa is below the %.2f MPa required"
                % (stress, required)
            )

    if voids:
        verdict = ADHESION_RUN_VOID
        accepted = False
    elif findings:
        verdict = ADHESION_NOT_ACCEPTED
        accepted = False
    else:
        verdict = ADHESION_ACCEPTED
        accepted = True

    return {
        "nominated_standard": standard,
        "method_family": family,
        "method_detail": detail,
        "run_void": bool(voids),
        "void_reasons": voids,
        "verdict": verdict,
        "accepted": accepted,
        "findings": findings,
    }
