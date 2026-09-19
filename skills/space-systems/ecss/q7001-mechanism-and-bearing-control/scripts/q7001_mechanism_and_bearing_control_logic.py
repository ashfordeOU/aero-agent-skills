"""Contamination control of mechanisms, bearings and slip rings.

Anchor: ECSS-Q-ST-70-01C, the sensitive-hardware provisions covering moving
assemblies whose failure mode is mechanical or electrical rather than optical.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn a declared product cleanliness level into a particle population: the
   number of particles above a given size expected over a reference area, and
   from that the largest particle statistically expected over the real wetted
   area of the assembly.
2. Compare that particle against the two dimensions that matter on a moving
   assembly: the running clearance of the bearing or joint, and the gap a
   slip-ring or contact pair closes. A particle a fraction of the clearance
   raises drag; a particle of the order of the clearance jams; a conductive
   particle spanning a contact gap is an electrical event, not a drag one.
3. Turn the particle population into an added drag torque and fold it into
   the actuator torque margin, so a cleanliness level and a torque budget are
   argued against each other rather than separately.
4. Check the other direction of transport: lubricant creeping out of the
   bearing over the mission is itself a molecular contaminant, and the barrier
   distance to the nearest sensitive surface has to outlast it.
"""

import math

__all__ = [
    "BRIDGING_CATEGORIES",
    "CC1246_EXPONENT",
    "MARGIN_TOLERANCE",
    "REFERENCE_AREA_M2",
    "assess_mechanism_cleanliness",
    "bridging_category",
    "clearance_margin_fraction",
    "contamination_drag_torque_nm",
    "largest_expected_particle_um",
    "lubricant_creep_reach_mm",
    "particle_count_over_area",
    "particle_count_per_reference_area",
    "torque_margin_fraction",
    "validate_mechanism",
]

# Product cleanliness-level population model: the count above a size follows a
# squared-logarithm law with this exponent, referred to the reference area.
CC1246_EXPONENT = 0.926
REFERENCE_AREA_M2 = 0.1

# Margins are quotients of quantities built through log10 and 10**x, neither of
# which is correctly rounded; an exactly on-limit case can land either side.
MARGIN_TOLERANCE = 1e-9

# Grouped outcomes for a particle against a contact or running gap.
BRIDGING_CATEGORIES = ("clear", "marginal", "bridging")

# A particle occupying at least this fraction of the gap is no longer clear.
MARGINAL_GAP_FRACTION = 0.5


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _level(value):
    level = _positive(value, "cleanliness_level")
    if level < 1.0:
        raise ValueError(
            "cleanliness_level is expressed as a particle size in micrometres and "
            "cannot be below 1, got %r" % (value,)
        )
    return level


def _size(value, label="size_um"):
    size = _positive(value, label)
    if size < 1.0:
        raise ValueError(
            "%s must be at least 1 micrometre; the population model is not defined "
            "below it, got %r" % (label, value)
        )
    return size


def particle_count_per_reference_area(cleanliness_level, size_um):
    """Return the expected particle count above a size over the reference area."""
    level = _level(cleanliness_level)
    size = _size(size_um)
    exponent = CC1246_EXPONENT * (
        math.log10(level) ** 2 - math.log10(size) ** 2
    )
    return 10.0 ** exponent


def particle_count_over_area(cleanliness_level, size_um, area_m2):
    """Scale the reference-area count onto the real wetted area."""
    area = _positive(area_m2, "area_m2")
    per_reference = particle_count_per_reference_area(cleanliness_level, size_um)
    return per_reference * area / REFERENCE_AREA_M2


def largest_expected_particle_um(cleanliness_level, area_m2):
    """Return the largest particle statistically expected once over the area.

    Returns 0.0 when not even one particle of a micrometre or more is expected
    over that area, which is a real answer and not a degenerate one.
    """
    level = _level(cleanliness_level)
    area = _positive(area_m2, "area_m2")
    target_per_reference = REFERENCE_AREA_M2 / area
    squared = math.log10(level) ** 2 - math.log10(target_per_reference) / CC1246_EXPONENT
    if squared < 0.0:
        return 0.0
    size = 10.0 ** math.sqrt(squared)
    if size < 1.0:
        return 0.0
    return size


def clearance_margin_fraction(clearance_um, particle_um):
    """Return how much of the running clearance the particle leaves free."""
    clearance = _positive(clearance_um, "clearance_um")
    particle = _non_negative(particle_um, "particle_um")
    return 1.0 - particle / clearance


def bridging_category(gap_um, particle_um):
    """Group a particle against a contact or running gap.

    'clear' below half the gap, 'marginal' from half the gap up to the gap,
    'bridging' at or above the gap.
    """
    gap = _positive(gap_um, "gap_um")
    particle = _non_negative(particle_um, "particle_um")
    ratio = particle / gap
    if ratio >= 1.0 - MARGIN_TOLERANCE:
        return "bridging"
    if ratio >= MARGINAL_GAP_FRACTION - MARGIN_TOLERANCE:
        return "marginal"
    return "clear"


def contamination_drag_torque_nm(base_drag_nm, particle_count, drag_per_particle_nm):
    """Return the resisting torque once contamination drag is added."""
    base = _non_negative(base_drag_nm, "base_drag_nm")
    if (
        not isinstance(particle_count, (int, float))
        or isinstance(particle_count, bool)
    ):
        raise ValueError("particle_count must be a real number")
    count = float(particle_count)
    if not math.isfinite(count) or count < 0.0:
        raise ValueError("particle_count must be finite and non-negative")
    per_particle = _non_negative(drag_per_particle_nm, "drag_per_particle_nm")
    return base + count * per_particle


def torque_margin_fraction(available_torque_nm, resisting_torque_nm):
    """Return the fractional torque margin of the actuator."""
    available = _non_negative(available_torque_nm, "available_torque_nm")
    resisting = _positive(resisting_torque_nm, "resisting_torque_nm")
    return available / resisting - 1.0


def lubricant_creep_reach_mm(creep_rate_mm_per_day, mission_days):
    """Return how far lubricant creeps from the bearing over the mission."""
    rate = _non_negative(creep_rate_mm_per_day, "creep_rate_mm_per_day")
    days = _positive(mission_days, "mission_days")
    return rate * days


def validate_mechanism(spec):
    """Return a normalised mechanism contamination record."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "cleanliness_level",
        "wetted_area_m2",
        "running_clearance_um",
        "available_torque_nm",
        "base_drag_nm",
        "mission_days",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    record = {
        "cleanliness_level": _level(spec["cleanliness_level"]),
        "wetted_area_m2": _positive(spec["wetted_area_m2"], "wetted_area_m2"),
        "running_clearance_um": _positive(
            spec["running_clearance_um"], "running_clearance_um"
        ),
        "available_torque_nm": _non_negative(
            spec["available_torque_nm"], "available_torque_nm"
        ),
        "base_drag_nm": _positive(spec["base_drag_nm"], "base_drag_nm"),
        "mission_days": _positive(spec["mission_days"], "mission_days"),
        "slip_ring_gap_um": (
            None
            if spec.get("slip_ring_gap_um") is None
            else _positive(spec["slip_ring_gap_um"], "slip_ring_gap_um")
        ),
        "drag_particle_size_um": _size(
            spec.get("drag_particle_size_um", 25.0), "drag_particle_size_um"
        ),
        "drag_per_particle_nm": _non_negative(
            spec.get("drag_per_particle_nm", 1.0e-6), "drag_per_particle_nm"
        ),
        "required_torque_margin": _non_negative(
            spec.get("required_torque_margin", 1.0), "required_torque_margin"
        ),
        "required_clearance_margin": _non_negative(
            spec.get("required_clearance_margin", 0.5), "required_clearance_margin"
        ),
        "creep_rate_mm_per_day": _non_negative(
            spec.get("creep_rate_mm_per_day", 0.0), "creep_rate_mm_per_day"
        ),
        "creep_barrier_mm": _positive(spec.get("creep_barrier_mm", 10.0), "creep_barrier_mm"),
    }
    if record["required_clearance_margin"] > 1.0:
        raise ValueError("required_clearance_margin must not exceed 1")
    return record


def assess_mechanism_cleanliness(spec):
    """Run the full mechanism, bearing and slip-ring contamination assessment."""
    record = validate_mechanism(spec)
    largest = largest_expected_particle_um(
        record["cleanliness_level"], record["wetted_area_m2"]
    )
    clearance_margin = clearance_margin_fraction(
        record["running_clearance_um"], largest
    )
    drag_count = particle_count_over_area(
        record["cleanliness_level"],
        record["drag_particle_size_um"],
        record["wetted_area_m2"],
    )
    resisting = contamination_drag_torque_nm(
        record["base_drag_nm"], drag_count, record["drag_per_particle_nm"]
    )
    torque_margin = torque_margin_fraction(record["available_torque_nm"], resisting)
    reach = lubricant_creep_reach_mm(
        record["creep_rate_mm_per_day"], record["mission_days"]
    )
    barrier_margin = record["creep_barrier_mm"] - reach
    slip_ring = None
    if record["slip_ring_gap_um"] is not None:
        slip_ring = {
            "gap_um": record["slip_ring_gap_um"],
            "particle_um": largest,
            "category": bridging_category(record["slip_ring_gap_um"], largest),
        }
    findings = []
    clearance_ok = clearance_margin > record["required_clearance_margin"] or math.isclose(
        clearance_margin,
        record["required_clearance_margin"],
        rel_tol=0.0,
        abs_tol=MARGIN_TOLERANCE,
    )
    if not clearance_ok:
        findings.append(
            "largest expected particle %.2f um leaves a clearance margin of %.4f "
            "against a required %.4f"
            % (largest, clearance_margin, record["required_clearance_margin"])
        )
    torque_ok = torque_margin > record["required_torque_margin"] or math.isclose(
        torque_margin,
        record["required_torque_margin"],
        rel_tol=0.0,
        abs_tol=MARGIN_TOLERANCE,
    )
    if not torque_ok:
        findings.append(
            "torque margin %.4f against a required %.4f once contamination drag is "
            "added" % (torque_margin, record["required_torque_margin"])
        )
    creep_ok = barrier_margin > 0.0 or math.isclose(
        barrier_margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    if not creep_ok:
        findings.append(
            "lubricant creeps %.4f mm over the mission against a %.4f mm barrier"
            % (reach, record["creep_barrier_mm"])
        )
    slip_ring_ok = True
    if slip_ring is not None and slip_ring["category"] != "clear":
        slip_ring_ok = False
        findings.append(
            "slip-ring gap %.2f um is %s against the largest expected particle "
            "%.2f um" % (slip_ring["gap_um"], slip_ring["category"], largest)
        )
    return {
        "largest_expected_particle_um": largest,
        "clearance_margin_fraction": clearance_margin,
        "drag_particle_count": drag_count,
        "resisting_torque_nm": resisting,
        "torque_margin_fraction": torque_margin,
        "lubricant_reach_mm": reach,
        "creep_barrier_margin_mm": barrier_margin,
        "slip_ring": slip_ring,
        "compliant": clearance_ok and torque_ok and creep_ok and slip_ring_ok,
        "findings": findings,
    }
