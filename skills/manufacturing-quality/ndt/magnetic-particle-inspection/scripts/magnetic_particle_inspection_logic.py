"""Magnetic particle inspection (MT/MPI) math for aerospace NDT.

Deterministic, offline, stdlib-only helpers for magnetic particle
inspection of ferromagnetic parts: magnetizing current selection for
circular magnetization by head shot or central conductor, ampere-turns
and coil current for longitudinal magnetization by encircling coil from
the part effective L/D ratio, tangential field strength against the
2400 to 4800 A/m band, coverage overlap between successive
magnetization shots, magnetic particle classification by median size
and the resulting sensitivity level, wet bath concentration check,
indication linearity and acceptance verdict from relevant indications,
and the residual field demagnetization check.

Units: current in amperes, dimensions in inches for the classic
current-per-inch magnetization rules (ampere-turns are dimensionless),
field strength in A/m, lengths in meters, particle size in microns
(um), bath concentration in mL of particle concentrate per 100 mL of
carrier liquid, indication lengths in mm, residual field in A/m.

Contract exercised by scripts/test_magnetic_particle_inspection.py.

Worked anchors:
- head_shot_current(2.0, 800.0) = 1600.0 A (2 inch shaft at 800 A/in)
- central_conductor_current(1.0, 800.0) = 800.0 A
- effective_diameter_hollow(2.0, 1.0) = 1.7320508 in
- effective_ld_ratio(8.0, 1.7320508) = 4.6188
- coil_ampere_turns_low_fill(4.0) = 11250.0 A-turns
- coil_ampere_turns_high_fill(4.0) = 5833.33 A-turns
- coil_current_from_turns(11250.0, 250) = 45.0 A
- solenoid_field_strength(1000.0, 0.25) = 4000.0 A/m
- tangential_field_verdict(4000.0) = 'adequate' (fluorescent band)
- coverage_step(0.2, 0.15) = 0.17 m
- particle_size_class(8.0) = 'extra-fine', particle_sensitivity(45.0) = 'low'
- bath_concentration_check(0.2, 'fluorescent') = 'within-range'
- indication_linear_ratio(6.0, 1.5) = 4.0
- acceptance_verdict(True, 4.0, 3.0) = 'reject'
- residual_field_verdict(5.0) = 'demagnetize'
- magnetization_for_defect('longitudinal') = 'circular'
"""

import math

# Common-practice tangential field strength band for the wet
# fluorescent method, A/m (30 to 60 oersted). The wet visible band is
# 2400 to 3200 A/m (30 to 40 oersted). Verify against the qualified
# procedure; these are summary values, not a standard quote.
FIELD_BAND_FLUORESCENT = (2400.0, 4800.0)
FIELD_BAND_VISIBLE = (2400.0, 3200.0)

# Common-practice wet bath concentration, mL of particle concentrate
# per 100 mL of carrier liquid. Fluorescent: 0.1 to 0.4; visible: 1 to 2.
BATH_BAND_FLUORESCENT = (0.1, 0.4)
BATH_BAND_VISIBLE = (1.0, 2.0)

# Residual field limit below which demagnetization is not required,
# A/m, a common aerospace practice value. Verify against the
# engineering specification.
RESIDUAL_FIELD_LIMIT_AM = 3.0

# Minimum L/D for an encircling coil and the low/high fill factor
# ampere-turns constants, per common MPI practice (ASTM E1444-class
# guidance summarized, not quoted).
COIL_LD_MIN = 2.0
COIL_LD_MAX = 15.0
LOW_FILL_CONSTANT = 45000.0
HIGH_FILL_CONSTANT = 35000.0

# Indication linearity threshold: length / width >= 3 is a linear
# indication, the crack-like class evaluated against linear limits.
LINEAR_RATIO = 3.0

# Particle size class bands, median particle diameter in microns.
PARTICLE_BANDS = (
    (10.0, "extra-fine"),
    (20.0, "fine"),
    (35.0, "medium"),
    (math.inf, "coarse"),
)

# Sensitivity level from median particle size in microns: finer
# particles form indications on tighter, shallower defects.
SENSITIVITY_BANDS = (
    (20.0, "high"),
    (35.0, "standard"),
    (math.inf, "low"),
)


def _positive(value, name):
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return value


def head_shot_current(diameter_in, amperes_per_inch=800.0):
    """Return the circular magnetization current in amperes for a head shot.

    Circular magnetization by direct contact (head shot) applies the
    current along the part axis; the circumferential field detects
    longitudinal defects. Common practice is 300 to 800 A per inch of
    part diameter (diameter in inches), so I = amperes_per_inch * D.

    Anchor: head_shot_current(2.0, 800.0) = 1600.0 A.

    Raises ValueError for a non-positive diameter or current density.
    """
    _positive(diameter_in, "part diameter")
    _positive(amperes_per_inch, "amperes per inch")
    return amperes_per_inch * diameter_in


def central_conductor_current(conductor_diameter_in, amperes_per_inch=800.0):
    """Return the circular magnetization current in amperes for a central conductor.

    A central conductor threaded through a bore produces the same
    circumferential field as a head shot; the current-per-inch rule
    applies to the conductor diameter, not the part OD, because the
    field strength at the bore surface is set by the current and the
    conductor radius. I = amperes_per_inch * conductor_diameter.

    Anchor: central_conductor_current(1.0, 800.0) = 800.0 A.

    Raises ValueError for a non-positive conductor diameter or current
    density.
    """
    _positive(conductor_diameter_in, "conductor diameter")
    _positive(amperes_per_inch, "amperes per inch")
    return amperes_per_inch * conductor_diameter_in


def effective_diameter_hollow(outer_diameter, inner_diameter):
    """Return the effective diameter for L/D of a hollow cylindrical part.

    A hollow part magnetized by an encircling coil behaves as a solid
    bar of effective diameter D_eff = sqrt(OD^2 - ID^2); the L/D ratio
    used for coil ampere-turns is length / D_eff.

    Anchor: effective_diameter_hollow(2.0, 1.0) = 1.7320508 in.

    Raises ValueError unless 0 < inner_diameter < outer_diameter.
    """
    _positive(outer_diameter, "outer diameter")
    _positive(inner_diameter, "inner diameter")
    if inner_diameter >= outer_diameter:
        raise ValueError(
            "inner diameter %r must be < outer diameter %r"
            % (inner_diameter, outer_diameter)
        )
    return math.sqrt(outer_diameter * outer_diameter - inner_diameter * inner_diameter)


def effective_ld_ratio(length, effective_diameter):
    """Return the effective length to diameter ratio L/D of the part.

    L/D = length / effective_diameter, where the effective diameter is
    the actual diameter for a solid bar or the hollow-part value from
    effective_diameter_hollow. The ratio sizes the encircling coil
    ampere-turns and must lie in [2, 15) for the coil technique.

    Anchor: effective_ld_ratio(8.0, 1.7320508) = 4.6188.

    Raises ValueError for a non-positive length or diameter.
    """
    _positive(length, "part length")
    _positive(effective_diameter, "effective diameter")
    return length / effective_diameter


def _ld_checked(ld_ratio):
    if ld_ratio < COIL_LD_MIN:
        raise ValueError(
            "L/D %r < %r: add pole pieces or stack parts so the "
            "effective L/D reaches 2" % (ld_ratio, COIL_LD_MIN)
        )
    if ld_ratio >= COIL_LD_MAX:
        raise ValueError(
            "L/D %r >= %r: coil magnetization only covers the central "
            "portion; magnetize in sections or use an alternative "
            "technique" % (ld_ratio, COIL_LD_MAX)
        )


def coil_ampere_turns_low_fill(ld_ratio):
    """Return the ampere-turns for a low fill factor encircling coil.

    A low fill factor coil (part diameter well below the coil inner
    diameter) needs NI = 45000 / (L/D) ampere-turns for 2 <= L/D < 15.
    Fewer turns are needed as the part gets longer relative to its
    diameter, because the part self-demagnetizes less.

    Anchor: coil_ampere_turns_low_fill(4.0) = 11250.0 A-turns.

    Raises ValueError for an L/D outside [2, 15), with guidance.
    """
    _ld_checked(ld_ratio)
    return LOW_FILL_CONSTANT / ld_ratio


def coil_ampere_turns_high_fill(ld_ratio):
    """Return the ampere-turns for a high fill factor encircling coil.

    A high fill factor coil (part nearly fills the coil) needs
    NI = 35000 / (L/D + 2) ampere-turns for 2 <= L/D < 15. The +2 term
    accounts for the shorter flux path when the part fills the coil.

    Anchor: coil_ampere_turns_high_fill(4.0) = 5833.33 A-turns.

    Raises ValueError for an L/D outside [2, 15), with guidance.
    """
    _ld_checked(ld_ratio)
    return HIGH_FILL_CONSTANT / (ld_ratio + 2.0)


def coil_current_from_turns(ampere_turns, turns):
    """Return the coil current in amperes for a given turn count.

    I = NI / N, the current needed in an N-turn coil to reach the
    required ampere-turns from coil_ampere_turns_low_fill or
    coil_ampere_turns_high_fill.

    Anchor: coil_current_from_turns(11250.0, 250) = 45.0 A.

    Raises ValueError for non-positive ampere-turns or a non-positive
    integer turn count.
    """
    _positive(ampere_turns, "ampere-turns")
    if turns <= 0 or int(turns) != turns:
        raise ValueError("turns must be a positive integer, got %r" % (turns,))
    return ampere_turns / float(turns)


def solenoid_field_strength(ampere_turns, coil_length_m):
    """Return the axial field strength H = NI / L in A/m.

    For a long solenoid (encircling coil whose length is large
    compared with its diameter), the field inside is H = NI / L with
    NI in ampere-turns and L in meters. This is the field that must
    fall inside the tangential field band of the procedure.

    Anchor: solenoid_field_strength(1000.0, 0.25) = 4000.0 A/m.

    Raises ValueError for non-positive ampere-turns or length.
    """
    _positive(ampere_turns, "ampere-turns")
    _positive(coil_length_m, "coil length")
    return ampere_turns / coil_length_m


def tangential_field_verdict(field_am, fluorescent=True):
    """Return 'adequate', 'low', or 'high' for a tangential field.

    The wet fluorescent method needs 2400 to 4800 A/m (30 to 60
    oersted); the wet visible method needs 2400 to 3200 A/m (30 to 40
    oersted). A low field misses tight defects; an excessive field can
    form false indications from background particle collection.

    Anchor: tangential_field_verdict(4000.0) = 'adequate';
    tangential_field_verdict(2000.0) = 'low';
    tangential_field_verdict(5000.0, True) = 'high';
    tangential_field_verdict(4000.0, False) = 'high' (visible band).

    Raises ValueError for a negative field.
    """
    if field_am < 0:
        raise ValueError("field strength must be >= 0, got %r" % (field_am,))
    low, high = FIELD_BAND_FLUORESCENT if fluorescent else FIELD_BAND_VISIBLE
    if field_am < low:
        return "low"
    if field_am > high:
        return "high"
    return "adequate"


def coverage_step(shot_width, overlap_fraction):
    """Return the spacing between successive magnetization shots.

    Adjacent magnetization coverage must overlap, commonly 10 to 15
    percent of the shot width, so the step between passes is
    step = width * (1 - overlap). A 0.2 m shot at 15 percent overlap
    advances 0.17 m per pass, leaving 0.03 m of re-magnetized overlap.

    Anchor: coverage_step(0.2, 0.15) = 0.17 m.

    Raises ValueError for a non-positive width or an overlap outside
    [0, 1).
    """
    _positive(shot_width, "shot width")
    if overlap_fraction < 0 or overlap_fraction >= 1.0:
        raise ValueError(
            "overlap fraction must be in [0, 1), got %r" % (overlap_fraction,)
        )
    return shot_width * (1.0 - overlap_fraction)


def particle_size_class(median_diameter_um):
    """Return the magnetic particle size class.

    Classes by median particle diameter: extra-fine below 10 um, fine
    10 to 20 um, medium 20 to 35 um, coarse 35 um and above. Finer
    particles stay suspended longer and form indications on tight,
    shallow defects; coarse particles collect strongly but mask fine
    detail.

    Anchor: particle_size_class(8.0) = 'extra-fine';
    particle_size_class(45.0) = 'coarse'.

    Raises ValueError for a non-positive diameter.
    """
    _positive(median_diameter_um, "median particle diameter")
    for limit, label in PARTICLE_BANDS:
        if median_diameter_um < limit:
            return label
    return "coarse"


def particle_sensitivity(median_diameter_um):
    """Return the particle sensitivity level from median size.

    Finer particles give higher sensitivity: below 20 um is 'high',
    20 to 35 um is 'standard', 35 um and above is 'low'. High
    sensitivity particles detect tight fatigue cracks but produce
    weaker, less visible indications.

    Anchor: particle_sensitivity(8.0) = 'high';
    particle_sensitivity(25.0) = 'standard';
    particle_sensitivity(45.0) = 'low'.

    Raises ValueError for a non-positive diameter.
    """
    _positive(median_diameter_um, "median particle diameter")
    for limit, label in SENSITIVITY_BANDS:
        if median_diameter_um < limit:
            return label
    return "low"


def bath_concentration_check(concentration_ml_per_100ml, method="fluorescent"):
    """Return 'within-range', 'below-range', or 'above-range' for the bath.

    Wet bath concentration in mL of particle concentrate per 100 mL of
    carrier liquid: fluorescent method 0.1 to 0.4, visible method 1 to
    2. Too little particle means weak indications; too much means heavy
    background that hides real indications.

    Anchor: bath_concentration_check(0.2, 'fluorescent') = 'within-range';
    bath_concentration_check(0.05, 'fluorescent') = 'below-range';
    bath_concentration_check(1.5, 'visible') = 'within-range'.

    Raises ValueError for a negative concentration or an unknown method.
    """
    if concentration_ml_per_100ml < 0:
        raise ValueError(
            "concentration must be >= 0, got %r" % (concentration_ml_per_100ml,)
        )
    if method == "fluorescent":
        low, high = BATH_BAND_FLUORESCENT
    elif method == "visible":
        low, high = BATH_BAND_VISIBLE
    else:
        raise ValueError(
            "method must be 'fluorescent' or 'visible', got %r" % (method,)
        )
    if concentration_ml_per_100ml < low:
        return "below-range"
    if concentration_ml_per_100ml > high:
        return "above-range"
    return "within-range"


def indication_linear_ratio(length_mm, width_mm):
    """Return the indication length to width ratio.

    ratio = length / width. A ratio of 3 or more is a linear
    (crack-like) indication evaluated against the linear acceptance
    limit; a lower ratio is a rounded indication (pore, inclusion)
    evaluated against its own class.

    Anchor: indication_linear_ratio(6.0, 1.5) = 4.0.

    Raises ValueError for non-positive length or width.
    """
    _positive(length_mm, "indication length")
    _positive(width_mm, "indication width")
    return length_mm / width_mm


def indication_is_linear(length_mm, width_mm):
    """Return True when the indication is linear (crack-like).

    Linear means length / width >= 3, the classic crack-like class.

    Anchor: indication_is_linear(6.0, 1.5) = True;
    indication_is_linear(4.0, 2.0) = False.

    Raises ValueError for non-positive length or width.
    """
    return indication_linear_ratio(length_mm, width_mm) >= LINEAR_RATIO


def magnetization_for_defect(defect_orientation):
    """Return the magnetization direction that detects a defect class.

    A longitudinal (axial) defect lies along the part axis and is cut
    by the circumferential field of circular magnetization, so it needs
    'circular'. A transverse (circumferential) defect is cut by the
    axial field of an encircling coil, so it needs 'longitudinal'.
    Both directions are applied on production parts so every
    orientation is covered.

    Anchor: magnetization_for_defect('longitudinal') = 'circular';
    magnetization_for_defect('transverse') = 'longitudinal'.

    Raises ValueError for an unknown orientation.
    """
    o = defect_orientation.strip().lower()
    if o in ("longitudinal", "axial", "axially-oriented"):
        return "circular"
    if o in ("transverse", "circumferential", "circumferentially-oriented"):
        return "longitudinal"
    raise ValueError(
        "defect orientation must be 'longitudinal' or 'transverse', got %r"
        % (defect_orientation,)
    )


def acceptance_verdict(relevant, indication_length_mm, max_allowed_mm):
    """Return 'accept', 'reject', or 'evaluate' for an indication.

    Non-relevant indications (threads, sharp section changes, magnetic
    writing, part geometry) are recorded and evaluated, never
    auto-accepted or auto-rejected. A relevant indication is rejected
    when its length exceeds the acceptance limit, accepted otherwise.

    Anchor: acceptance_verdict(True, 4.0, 3.0) = 'reject';
    acceptance_verdict(True, 2.0, 3.0) = 'accept';
    acceptance_verdict(False, 9.0, 3.0) = 'evaluate'.

    Raises ValueError for a non-positive length or limit.
    """
    _positive(indication_length_mm, "indication length")
    _positive(max_allowed_mm, "acceptance limit")
    if not relevant:
        return "evaluate"
    if indication_length_mm > max_allowed_mm:
        return "reject"
    return "accept"


def residual_field_verdict(residual_am, limit_am=RESIDUAL_FIELD_LIMIT_AM):
    """Return 'demagnetize' or 'acceptable' from the residual field.

    After magnetization the part must be demagnetized when the
    residual field exceeds the limit, commonly 3 A/m for aerospace
    parts that run against bearings or chips. The verdict compares the
    measured residual field with the limit.

    Anchor: residual_field_verdict(5.0) = 'demagnetize';
    residual_field_verdict(2.0) = 'acceptable'.

    Raises ValueError for a negative residual field or non-positive
    limit.
    """
    if residual_am < 0:
        raise ValueError("residual field must be >= 0, got %r" % (residual_am,))
    _positive(limit_am, "residual field limit")
    if residual_am > limit_am:
        return "demagnetize"
    return "acceptable"
