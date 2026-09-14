#!/usr/bin/env python3
"""Twenty loaded eraser strokes on the coated face of a coverglass.

Anchor: ECSS-E-ST-20-08C clause 8.7.17. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The abrasion check is deliberately crude: an eraser under a stated load
is drawn across the coated face a stated number of times, and the face
is then read again. Its value comes entirely from the fact that the
three numbers -- face, strokes and load -- are fixed. A run that
delivers eighteen strokes, or twenty strokes at whatever load the
operator's hand supplied, or twenty strokes on the uncoated side, does
not produce a weaker result than the specified run; it produces a
result that says nothing at all, because there is no dose to attach the
optical change to.

What the assessment therefore does

    - hold the stroke count at the specified number, in both directions
    - hold the applied load inside the band the procedure states
    - turn load and tip into a contact pressure, since the same load on
      a worn-flat eraser is a different test
    - size the rubbed track, so an optical change has an area to belong
      to
    - read the transmittance and haze change across the run
    - hold coating removal on that track under its ceiling

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COATED_FACE = "coated-face"
UNCOATED_FACE = "uncoated-face"
FACES = (COATED_FACE, UNCOATED_FACE)

#: Strokes the procedure fixes. Both a short run and a long one void it.
SPECIFIED_STROKES = 20

#: Nominal eraser load and the band around it the procedure allows.
NOMINAL_ERASER_LOAD_N = 4.45
LOAD_TOLERANCE_FRACTION = 0.10

#: Contact pressure band. A worn-flat tip spreads the same load and
#: under-tests; a sharpened tip concentrates it and over-tests.
MIN_CONTACT_PRESSURE_KPA = 20.0
MAX_CONTACT_PRESSURE_KPA = 400.0

#: Optical change the coated face is allowed to show across the run.
MAX_TRANSMITTANCE_LOSS_FRACTION = 0.01
MAX_HAZE_INCREASE_FRACTION = 0.005

#: Share of the rubbed track the coating may have left, allowing for
#: the measurement noise of a microscope area count.
MAX_COATING_REMOVAL_FRACTION = 0.01

#: Sliding friction of a rubber eraser on a hard oxide coating, used
#: only to report the work the run put into the track.
ERASER_FRICTION_COEFFICIENT = 0.7

REQUIRED_RUN_EVIDENCE = (
    "abraded_face",
    "delivered_strokes",
    "eraser_load_n",
    "eraser_tip_diameter_mm",
    "haze_after_fraction",
    "haze_before_fraction",
    "removed_coating_area_mm2",
    "stroke_length_mm",
    "transmittance_after_fraction",
    "transmittance_before_fraction",
)

RUN_ACCEPTED = "abrasion-resistance-accepted"
RUN_NOT_ACCEPTED = "abrasion-resistance-not-accepted"
RUN_VOID = "abrasion-run-void"

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


def _require_fraction(name, value):
    number = _require_non_negative(name, value)
    if number > 1.0:
        raise ValueError(
            "%s must be a fraction at or below one, got %r" % (name, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A contact pressure is a load divided by a squared diameter and then
    rescaled between millimetres and metres, so a tip cut to land on a
    band edge can arrive a few units in the last place either side of
    it. The band is never widened; only the comparison tolerates the
    representation error, which is why no caller uses a bare >= on a
    derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def missing_run_evidence(run):
    """Evidence the run owes and has not brought."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))
    return tuple(name for name in REQUIRED_RUN_EVIDENCE if run.get(name) is None)


def face_is_the_coated_one(face):
    """Whether the strokes landed on the face the clause is about."""
    if face not in FACES:
        raise ValueError(
            "abraded_face must be one of %s, got %r" % (", ".join(FACES), face)
        )
    return face == COATED_FACE


def stroke_count_matches(delivered_strokes, specified_strokes=SPECIFIED_STROKES):
    """Whether the run delivered the stroke count the procedure fixes.

    Short runs under-test and long runs over-test. Neither is a softer
    or a harsher version of the specified run; both break the link
    between the dose and the optical change, so the count is held in
    both directions.
    """
    if not isinstance(delivered_strokes, int) or isinstance(delivered_strokes, bool):
        raise ValueError(
            "delivered_strokes must be an integer count, got %r" % (delivered_strokes,)
        )
    if delivered_strokes < 0:
        raise ValueError(
            "delivered_strokes must not be negative, got %d" % delivered_strokes
        )
    if not isinstance(specified_strokes, int) or isinstance(specified_strokes, bool):
        raise ValueError(
            "specified_strokes must be an integer count, got %r" % (specified_strokes,)
        )
    if specified_strokes <= 0:
        raise ValueError(
            "specified_strokes must be positive, got %d" % specified_strokes
        )
    return delivered_strokes == specified_strokes


def load_within_band(
    load_n, nominal_n=NOMINAL_ERASER_LOAD_N, tolerance_fraction=LOAD_TOLERANCE_FRACTION
):
    """Whether the applied eraser load sits inside the procedure band."""
    applied = _require_positive("eraser_load_n", load_n)
    nominal = _require_positive("nominal_n", nominal_n)
    tolerance = _require_fraction("tolerance_fraction", tolerance_fraction)
    low = nominal * (1.0 - tolerance)
    high = nominal * (1.0 + tolerance)
    return _at_least(applied, low) and _at_most(applied, high)


def contact_pressure_kpa(load_n, tip_diameter_mm):
    """Pressure the eraser tip puts on the coating, in kilopascals.

    The same load on a tip worn to twice the diameter is a quarter of
    the pressure, which is why the load alone does not describe the run.
    """
    load = _require_positive("eraser_load_n", load_n)
    diameter = _require_positive("eraser_tip_diameter_mm", tip_diameter_mm)
    area_mm2 = math.pi * diameter * diameter / 4.0
    # N per mm^2 is MPa; the factor of 1000 reports kPa.
    return load / area_mm2 * 1000.0


def abraded_track_area_mm2(tip_diameter_mm, stroke_length_mm):
    """Area the tip sweeps: a rectangle with the tip's two end caps."""
    diameter = _require_positive("eraser_tip_diameter_mm", tip_diameter_mm)
    length = _require_positive("stroke_length_mm", stroke_length_mm)
    return diameter * length + math.pi * diameter * diameter / 4.0


def total_travel_mm(stroke_length_mm, delivered_strokes):
    """Path the tip covered across the whole run."""
    length = _require_positive("stroke_length_mm", stroke_length_mm)
    if not isinstance(delivered_strokes, int) or isinstance(delivered_strokes, bool):
        raise ValueError(
            "delivered_strokes must be an integer count, got %r" % (delivered_strokes,)
        )
    if delivered_strokes < 0:
        raise ValueError(
            "delivered_strokes must not be negative, got %d" % delivered_strokes
        )
    return length * float(delivered_strokes)


def abrasion_work_j(load_n, travel_mm, friction_coefficient=ERASER_FRICTION_COEFFICIENT):
    """Frictional work the run put into the track, in joules."""
    load = _require_positive("eraser_load_n", load_n)
    travel = _require_non_negative("travel_mm", travel_mm)
    mu = _require_non_negative("friction_coefficient", friction_coefficient)
    return mu * load * travel / 1000.0


def transmittance_loss_fraction(before_fraction, after_fraction):
    """Transmittance the coated face lost across the run.

    A positive number is a loss. A negative number means the face reads
    brighter after abrasion, which is a measurement or cleanliness
    problem rather than a result.
    """
    before = _require_fraction("transmittance_before_fraction", before_fraction)
    after = _require_fraction("transmittance_after_fraction", after_fraction)
    if before <= 0.0:
        raise ValueError(
            "transmittance_before_fraction must be greater than zero, got %r"
            % (before_fraction,)
        )
    return (before - after) / before


def haze_increase_fraction(before_fraction, after_fraction):
    """Scatter the run added to the coated face."""
    before = _require_fraction("haze_before_fraction", before_fraction)
    after = _require_fraction("haze_after_fraction", after_fraction)
    return after - before


def coating_removal_fraction(removed_area_mm2, track_area_mm2):
    """Share of the rubbed track the coating has left."""
    removed = _require_non_negative("removed_coating_area_mm2", removed_area_mm2)
    track = _require_positive("track_area_mm2", track_area_mm2)
    return removed / track


def assess_abrasion_resistance(case):
    """Full clause 8.7.17 judgement of one eraser abrasion run."""
    absent = missing_run_evidence(case)
    if absent:
        raise ValueError(
            "abrasion run is missing required evidence: %s" % ", ".join(absent)
        )

    specified = case.get("specified_strokes", SPECIFIED_STROKES)
    nominal_load = case.get("nominal_load_n", NOMINAL_ERASER_LOAD_N)
    tolerance = case.get("load_tolerance_fraction", LOAD_TOLERANCE_FRACTION)

    delivered = case["delivered_strokes"]
    load = _require_positive("eraser_load_n", case["eraser_load_n"])
    tip = _require_positive("eraser_tip_diameter_mm", case["eraser_tip_diameter_mm"])
    stroke_length = _require_positive("stroke_length_mm", case["stroke_length_mm"])

    on_coated_face = face_is_the_coated_one(case["abraded_face"])
    count_ok = stroke_count_matches(delivered, specified)
    load_ok = load_within_band(load, nominal_load, tolerance)
    pressure = contact_pressure_kpa(load, tip)
    pressure_ok = _at_least(pressure, MIN_CONTACT_PRESSURE_KPA) and _at_most(
        pressure, MAX_CONTACT_PRESSURE_KPA
    )
    track = abraded_track_area_mm2(tip, stroke_length)
    travel = total_travel_mm(stroke_length, delivered)
    work = abrasion_work_j(load, travel)

    voids = []
    if not on_coated_face:
        voids.append(
            "the strokes landed on the uncoated face; the run says nothing "
            "about the coating and has to be repeated on the coated side"
        )
    if not count_ok:
        voids.append(
            "run delivered %d strokes against the %d the procedure fixes; the "
            "optical change has no stated dose to belong to"
            % (delivered, specified)
        )
    if not load_ok:
        voids.append(
            "eraser load %.2f N falls outside the %.2f N band at %.0f%% "
            "tolerance; the dose is not the specified one"
            % (load, float(nominal_load), float(tolerance) * 100.0)
        )
    if not pressure_ok:
        voids.append(
            "contact pressure %.1f kPa falls outside the %.0f to %.0f kPa band; "
            "the tip is worn flat or cut too fine for the stated load"
            % (pressure, MIN_CONTACT_PRESSURE_KPA, MAX_CONTACT_PRESSURE_KPA)
        )

    transmittance_loss = transmittance_loss_fraction(
        case["transmittance_before_fraction"], case["transmittance_after_fraction"]
    )
    haze_increase = haze_increase_fraction(
        case["haze_before_fraction"], case["haze_after_fraction"]
    )
    removal = coating_removal_fraction(case["removed_coating_area_mm2"], track)

    findings = []
    if not _at_most(transmittance_loss, MAX_TRANSMITTANCE_LOSS_FRACTION):
        findings.append(
            "transmittance fell %.2f%% across the run, above the %.2f%% ceiling"
            % (transmittance_loss * 100.0, MAX_TRANSMITTANCE_LOSS_FRACTION * 100.0)
        )
    if transmittance_loss < 0.0 and not math.isclose(
        transmittance_loss, 0.0, rel_tol=_REL_TOL, abs_tol=1e-12
    ):
        findings.append(
            "the face reads brighter after abrasion than before; treat the "
            "before reading as suspect rather than as a gain"
        )
    if not _at_most(haze_increase, MAX_HAZE_INCREASE_FRACTION):
        findings.append(
            "haze rose %.3f across the run, above the %.3f ceiling"
            % (haze_increase, MAX_HAZE_INCREASE_FRACTION)
        )
    if not _at_most(removal, MAX_COATING_REMOVAL_FRACTION):
        findings.append(
            "coating has left %.2f%% of the rubbed track, above the %.2f%% "
            "ceiling; the coating is not adherent enough to survive handling"
            % (removal * 100.0, MAX_COATING_REMOVAL_FRACTION * 100.0)
        )

    if voids:
        verdict = RUN_VOID
        accepted = False
    elif findings:
        verdict = RUN_NOT_ACCEPTED
        accepted = False
    else:
        verdict = RUN_ACCEPTED
        accepted = True

    return {
        "abraded_face": case["abraded_face"],
        "on_coated_face": on_coated_face,
        "delivered_strokes": delivered,
        "specified_strokes": specified,
        "stroke_count_matches": count_ok,
        "eraser_load_n": load,
        "load_within_band": load_ok,
        "contact_pressure_kpa": pressure,
        "contact_pressure_within_band": pressure_ok,
        "track_area_mm2": track,
        "total_travel_mm": travel,
        "abrasion_work_j": work,
        "transmittance_loss_fraction": transmittance_loss,
        "haze_increase_fraction": haze_increase,
        "coating_removal_fraction": removal,
        "run_void": bool(voids),
        "void_reasons": voids,
        "verdict": verdict,
        "accepted": accepted,
        "findings": findings,
    }
