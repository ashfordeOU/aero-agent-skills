"""Charpy V-notch impact testing of metallic materials, with its conditions.

Anchor: ECSS-Q-ST-70-45, methods clause -- where toughness has to be
demonstrated, a notched bar is broken by a swinging pendulum at a stated
temperature and the absorbed energy of a set of specimens is reported against
a requirement. Paraphrased into an implementable procedure; no standard text
is reproduced.

What this module decides
------------------------
Whether a set of impact specimens was broken under the conditions the
requirement assumes, and whether the energies they absorbed satisfy it.

1. A sub-size bar carries a smaller requirement. The requirement scales with
   the width below the notch, and comparing a 5 mm bar with a full-size
   requirement rejects material that is compliant.
2. The requirement is a pair, not a number. A set average and an individual
   floor both have to hold, so one brittle bar cannot be averaged away by two
   tough ones.
3. The conditions are part of the result. Temperature at the moment of
   impact, the soak that got the bar there and the transfer time that let it
   drift back all decide what temperature the energy belongs to.
4. The pendulum has a usable range. Energies in the bottom or the top of the
   machine's capacity carry more windage and friction error than the reading
   resolution suggests.
"""

import math

__all__ = [
    "SPECIMEN_WIDTHS_MM",
    "FULL_WIDTH_MM",
    "TEMPERATURE_TOLERANCE_C",
    "MAX_TRANSFER_S",
    "MIN_SOAK_MIN",
    "CAPACITY_BAND",
    "INDIVIDUAL_FRACTION",
    "subsize_factor",
    "required_average_j",
    "required_individual_j",
    "temperature_findings",
    "condition_findings",
    "capacity_findings",
    "set_average_j",
    "assess_impact_test",
]

# Width below the notch, full size first, then the standard sub-sizes.
SPECIMEN_WIDTHS_MM = (10.0, 7.5, 5.0, 2.5)
FULL_WIDTH_MM = 10.0

# How far the bar may be from its stated temperature when the pendulum lands.
TEMPERATURE_TOLERANCE_C = 2.0

# How long the bar may spend out of the medium before it is struck.
MAX_TRANSFER_S = 5.0

# How long the bar has to sit in the medium to reach it.
MIN_SOAK_MIN = 5.0

# Fraction of the pendulum capacity inside which a reading is trustworthy.
CAPACITY_BAND = (0.10, 0.80)

# The individual floor as a fraction of the set average requirement.
INDIVIDUAL_FRACTION = 0.7

# Comparisons at a limit are inclusive; absorb representation error there.
REL_TOLERANCE = 1e-9


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_finite_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _slack(reference):
    return REL_TOLERANCE * max(abs(reference), 1.0)


def _meets(value, minimum):
    return value >= minimum - _slack(minimum)


def subsize_factor(width_mm):
    """Return the width below the notch as a fraction of the full-size bar."""
    width = _as_positive_float(width_mm, "width_mm")
    for standard in SPECIMEN_WIDTHS_MM:
        if abs(standard - width) <= _slack(standard):
            return standard / FULL_WIDTH_MM
    raise ValueError(
        "%g mm is not a standard width below the notch; the standard set is %s"
        % (width, ", ".join("%g" % w for w in SPECIMEN_WIDTHS_MM))
    )


def required_average_j(full_size_requirement_j, width_mm):
    """Return the set average requirement scaled to the specimen width."""
    full = _as_positive_float(full_size_requirement_j, "full_size_requirement_j")
    return full * subsize_factor(width_mm)


def required_individual_j(average_requirement_j):
    """Return the floor no single specimen of the set may fall below."""
    average = _as_positive_float(average_requirement_j, "average_requirement_j")
    return average * INDIVIDUAL_FRACTION


def set_average_j(energies_j):
    """Return the mean absorbed energy of a validated specimen set."""
    if not isinstance(energies_j, (list, tuple)) or len(energies_j) < 3:
        raise ValueError("an impact set needs at least three specimens")
    values = []
    for i, item in enumerate(energies_j):
        value = _as_finite_float(item, "specimen %d energy" % i)
        if value < 0.0:
            raise ValueError("specimen %d absorbed a negative energy" % i)
        values.append(value)
    return sum(values) / float(len(values))


def temperature_findings(specified_c, measured_c, tolerance_c=TEMPERATURE_TOLERANCE_C):
    """Return findings for specimens struck away from the stated temperature."""
    specified = _as_finite_float(specified_c, "specified_c")
    tolerance = _as_positive_float(tolerance_c, "tolerance_c")
    if not isinstance(measured_c, (list, tuple)) or not measured_c:
        raise ValueError("measured_c must hold one temperature per specimen")
    findings = []
    for i, item in enumerate(measured_c):
        value = _as_finite_float(item, "specimen %d temperature" % i)
        drift = abs(value - specified)
        if drift > tolerance + _slack(tolerance):
            findings.append(
                "specimen %d was struck at %.2f C, %.2f C from the stated %.2f C"
                % (i, value, drift, specified)
            )
    return findings


def condition_findings(soak_minutes=None, transfer_seconds=None):
    """Return findings for a bar that was not conditioned as the method assumes."""
    findings = []
    if soak_minutes is not None:
        soak = _as_positive_float(soak_minutes, "soak_minutes")
        if soak < MIN_SOAK_MIN - _slack(MIN_SOAK_MIN):
            findings.append(
                "soak of %.2f min is below the %.2f min the bar needs to reach "
                "the medium" % (soak, MIN_SOAK_MIN)
            )
    if transfer_seconds is not None:
        transfer = _as_positive_float(transfer_seconds, "transfer_seconds")
        if transfer > MAX_TRANSFER_S + _slack(MAX_TRANSFER_S):
            findings.append(
                "transfer of %.2f s exceeds the %.2f s limit; the bar drifted "
                "back towards ambient before it was struck"
                % (transfer, MAX_TRANSFER_S)
            )
    return findings


def capacity_findings(energies_j, machine_capacity_j):
    """Return findings for readings outside the usable part of the pendulum."""
    capacity = _as_positive_float(machine_capacity_j, "machine_capacity_j")
    if not isinstance(energies_j, (list, tuple)) or not energies_j:
        raise ValueError("energies_j must hold one reading per specimen")
    low, high = CAPACITY_BAND
    findings = []
    for i, item in enumerate(energies_j):
        value = _as_finite_float(item, "specimen %d energy" % i)
        fraction = value / capacity
        if fraction < low - _slack(low) or fraction > high + _slack(high):
            findings.append(
                "specimen %d absorbed %.2f J, %.1f%% of the %.2f J pendulum, "
                "outside the %.0f%% to %.0f%% usable range"
                % (i, value, fraction * 100.0, capacity, low * 100.0, high * 100.0)
            )
    return findings


def assess_impact_test(spec):
    """Judge one set of impact specimens against its requirement and conditions.

    spec keys: energies_j (one per specimen), width_mm, full_size_requirement_j,
    specified_temperature_c; optional measured_temperatures_c, soak_minutes,
    transfer_seconds, machine_capacity_j, lateral_expansions_mm and
    minimum_lateral_expansion_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("energies_j", "width_mm", "full_size_requirement_j",
                "specified_temperature_c"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    energies = spec["energies_j"]
    average = set_average_j(energies)
    factor = subsize_factor(spec["width_mm"])
    required_avg = required_average_j(spec["full_size_requirement_j"],
                                      spec["width_mm"])
    required_ind = required_individual_j(required_avg)

    findings = []
    if not _meets(average, required_avg):
        findings.append(
            "set average %.3f J is below the required %.3f J"
            % (average, required_avg)
        )
    for i, item in enumerate(energies):
        value = _as_finite_float(item, "specimen %d energy" % i)
        if not _meets(value, required_ind):
            findings.append(
                "specimen %d absorbed %.3f J, below the individual floor of "
                "%.3f J" % (i, value, required_ind)
            )

    if spec.get("measured_temperatures_c") is not None:
        measured = spec["measured_temperatures_c"]
        if len(measured) != len(energies):
            raise ValueError(
                "measured_temperatures_c holds %d entries for %d specimens"
                % (len(measured), len(energies))
            )
        findings.extend(
            temperature_findings(spec["specified_temperature_c"], measured)
        )
    findings.extend(
        condition_findings(spec.get("soak_minutes"), spec.get("transfer_seconds"))
    )
    if spec.get("machine_capacity_j") is not None:
        findings.extend(capacity_findings(energies, spec["machine_capacity_j"]))

    expansions = spec.get("lateral_expansions_mm")
    minimum_expansion = spec.get("minimum_lateral_expansion_mm")
    if expansions is not None:
        if minimum_expansion is None:
            raise ValueError(
                "lateral_expansions_mm given without minimum_lateral_expansion_mm"
            )
        floor = _as_positive_float(
            minimum_expansion, "minimum_lateral_expansion_mm"
        )
        if len(expansions) != len(energies):
            raise ValueError(
                "lateral_expansions_mm holds %d entries for %d specimens"
                % (len(expansions), len(energies))
            )
        for i, item in enumerate(expansions):
            value = _as_finite_float(item, "specimen %d lateral expansion" % i)
            if not _meets(value, floor):
                findings.append(
                    "specimen %d expanded %.4f mm laterally, below the %.4f mm "
                    "minimum" % (i, value, floor)
                )
    elif minimum_expansion is not None:
        findings.append(
            "a lateral expansion minimum is specified but no expansion was "
            "measured"
        )

    return {
        "specimen_count": len(energies),
        "width_factor": factor,
        "set_average_j": average,
        "required_average_j": required_avg,
        "required_individual_j": required_ind,
        "lowest_j": min(_as_finite_float(e, "energy") for e in energies),
        "findings": findings,
        "set_accepted": not findings,
    }
