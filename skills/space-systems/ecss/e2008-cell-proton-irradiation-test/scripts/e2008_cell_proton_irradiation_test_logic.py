"""Bare cell proton irradiation: performance lost to energetic proton fluence.

Anchor: ECSS-E-ST-20-08C clause 7.5.14 (tracking the performance a bare solar
cell loses when it is exposed to energetic proton fluence). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every exposure: a positive proton energy, a positive delivered
   fluence, a relative damage coefficient tied to the reference energy, the
   projected range of that energy in the cell, and the beam incidence.
2. Check the damage coefficient table is normalised: the coefficient at the
   reference energy is unity by definition, and a table that says otherwise is
   scaled to something else and cannot be summed with this one.
3. Check each energy reaches the junction. A proton whose projected range stops
   short of the junction depth leaves its damage in the layers ahead of it, so
   its fluence buys no displacement damage where the current is generated.
4. Hold the beam near normal incidence and turn the residual tilt into a path
   length factor, because a tilted beam crosses more active material per
   incident proton and therefore does more damage per unit fluence.
5. Weight every exposure by its damage coefficient and its path length factor
   into one reference-energy equivalent fluence, and accumulate it across the
   run so each measurement has an equivalent fluence attached to it.
6. Track the maximum power lost after each exposure. Displacement damage does
   not anneal back during a run, so a loss that shrinks is the bench, not the
   cell, and the end loss is compared with the allowance.
7. Report per-exposure contributions, the accumulated equivalent fluence, the
   loss track, every finding and the run verdict.
"""

import math

__all__ = [
    "LOSS_TOLERANCE",
    "REFERENCE_ENERGY_MEV",
    "MAX_OFF_NORMAL_DEG",
    "NOISE_ALLOWANCE",
    "validate_exposure",
    "path_length_factor",
    "equivalent_contribution",
    "accumulated_equivalent_fluence",
    "damage_coefficient_findings",
    "range_findings",
    "incidence_findings",
    "power_loss_fraction",
    "loss_track_findings",
    "coverage_findings",
    "assess_cell_proton_irradiation",
]

# A loss or an angle sitting exactly on a declared bound is conformant; the
# comparison absorbs representation error and the bound itself never moves.
LOSS_TOLERANCE = 1e-9

# The energy every relative damage coefficient is referred back to.
REFERENCE_ENERGY_MEV = 10.0

# Beyond this much off normal the beam crosses measurably more active material
# per incident proton than the plan assumed.
MAX_OFF_NORMAL_DEG = 3.0

# A tracked loss may shrink by this much between exposures before the dip is
# the cell rather than the measurement.
NOISE_ALLOWANCE = 0.002


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


def validate_exposure(record):
    """Return one validated proton exposure of the run."""
    if not isinstance(record, dict):
        raise ValueError("each exposure must be a mapping")
    required = (
        "label",
        "energy_mev",
        "fluence_p_per_cm2",
        "relative_damage_coefficient",
        "projected_range_um",
        "off_normal_deg",
    )
    for key in required:
        if key not in record:
            raise ValueError("exposure missing key '%s'" % key)
    angle = _non_negative(record["off_normal_deg"], "off_normal_deg")
    if angle >= 90.0:
        raise ValueError("off_normal_deg must be under 90, got %g" % angle)
    return {
        "label": _name(record["label"], "label"),
        "energy_mev": _positive(record["energy_mev"], "energy_mev"),
        "fluence_p_per_cm2": _positive(
            record["fluence_p_per_cm2"], "fluence_p_per_cm2"
        ),
        "relative_damage_coefficient": _positive(
            record["relative_damage_coefficient"],
            "relative_damage_coefficient",
        ),
        "projected_range_um": _positive(
            record["projected_range_um"], "projected_range_um"
        ),
        "off_normal_deg": angle,
    }


def path_length_factor(off_normal_deg):
    """Return the extra active path a tilted beam crosses per proton."""
    angle = _non_negative(off_normal_deg, "off_normal_deg")
    if angle >= 90.0:
        raise ValueError("off_normal_deg must be under 90, got %g" % angle)
    return 1.0 / math.cos(math.radians(angle))


def equivalent_contribution(exposure):
    """Return one exposure's reference-energy equivalent fluence."""
    item = validate_exposure(exposure)
    return (
        item["fluence_p_per_cm2"]
        * item["relative_damage_coefficient"]
        * path_length_factor(item["off_normal_deg"])
    )


def accumulated_equivalent_fluence(exposures):
    """Return the running equivalent fluence after each exposure."""
    if not isinstance(exposures, (list, tuple)) or not exposures:
        raise ValueError("exposures must be a non-empty sequence")
    running = 0.0
    totals = []
    for exposure in exposures:
        running += equivalent_contribution(exposure)
        totals.append(running)
    return totals


def damage_coefficient_findings(exposures,
                                reference_energy_mev=REFERENCE_ENERGY_MEV):
    """Return findings where the coefficient table is not normalised."""
    if not isinstance(exposures, (list, tuple)) or not exposures:
        raise ValueError("exposures must be a non-empty sequence")
    reference = _positive(reference_energy_mev, "reference_energy_mev")
    findings = []
    for exposure in exposures:
        item = validate_exposure(exposure)
        if abs(item["energy_mev"] - reference) > LOSS_TOLERANCE:
            continue
        if abs(item["relative_damage_coefficient"] - 1.0) > LOSS_TOLERANCE:
            findings.append(
                "exposure '%s' sits at the %g MeV reference energy but carries "
                "a damage coefficient of %g, so the table is scaled to another "
                "reference" % (item["label"], reference,
                               item["relative_damage_coefficient"])
            )
    return findings


def range_findings(exposures, junction_depth_um):
    """Return findings where an energy never reaches the junction."""
    if not isinstance(exposures, (list, tuple)) or not exposures:
        raise ValueError("exposures must be a non-empty sequence")
    depth = _positive(junction_depth_um, "junction_depth_um")
    findings = []
    for exposure in exposures:
        item = validate_exposure(exposure)
        if item["projected_range_um"] < depth - LOSS_TOLERANCE:
            findings.append(
                "exposure '%s' at %g MeV has a projected range of %g um, short "
                "of the %g um junction depth, so its fluence damages the layers "
                "ahead of the junction"
                % (item["label"], item["energy_mev"],
                   item["projected_range_um"], depth)
            )
    return findings


def incidence_findings(exposures, max_off_normal_deg=MAX_OFF_NORMAL_DEG):
    """Return findings where the beam sat too far off the cell normal."""
    if not isinstance(exposures, (list, tuple)) or not exposures:
        raise ValueError("exposures must be a non-empty sequence")
    limit = _non_negative(max_off_normal_deg, "max_off_normal_deg")
    if limit >= 90.0:
        raise ValueError("max_off_normal_deg must be under 90, got %g" % limit)
    findings = []
    for exposure in exposures:
        item = validate_exposure(exposure)
        if item["off_normal_deg"] > limit + LOSS_TOLERANCE:
            findings.append(
                "exposure '%s' arrived %g deg off normal, over the %g deg "
                "allowance, so each proton crossed %.4f times the active path "
                "the plan assumed"
                % (item["label"], item["off_normal_deg"], limit,
                   path_length_factor(item["off_normal_deg"]))
            )
    return findings


def power_loss_fraction(power_after_w, reference_power_w):
    """Return the fraction of its starting power an exposure took away."""
    after = _positive(power_after_w, "power_after_w")
    reference = _positive(reference_power_w, "reference_power_w")
    return 1.0 - after / reference


def loss_track_findings(labels, losses, noise_allowance=NOISE_ALLOWANCE):
    """Return findings where the tracked power loss shrank or went negative."""
    if not isinstance(labels, (list, tuple)) or not labels:
        raise ValueError("labels must be a non-empty sequence")
    if not isinstance(losses, (list, tuple)) or len(losses) != len(labels):
        raise ValueError("one loss is needed per exposure label")
    allowance = _positive(noise_allowance, "noise_allowance")
    names = [_name(label, "label") for label in labels]
    values = [_real(value, "power loss") for value in losses]
    findings = []
    for name, value in zip(names, values):
        if value < -(allowance + LOSS_TOLERANCE):
            findings.append(
                "after exposure '%s' the cell reads %.4f above its starting "
                "power, which proton damage does not do" % (name, -value)
            )
    for index in range(1, len(values)):
        dip = values[index - 1] - values[index]
        if dip > allowance + LOSS_TOLERANCE:
            findings.append(
                "the tracked loss fell from %.4f to %.4f between '%s' and "
                "'%s', so the cell reads as recovered"
                % (values[index - 1], values[index],
                   names[index - 1], names[index])
            )
    return findings


def coverage_findings(accumulated_p_per_cm2, required_p_per_cm2):
    """Return findings where the run never reached the mission equivalent."""
    reached = _positive(accumulated_p_per_cm2, "accumulated_p_per_cm2")
    required = _positive(required_p_per_cm2, "required_p_per_cm2")
    if reached < required * (1.0 - LOSS_TOLERANCE):
        return [
            "the run accumulated %.4g equivalent p/cm2, under the %.4g the "
            "mission asks for" % (reached, required)
        ]
    return []


def assess_cell_proton_irradiation(spec):
    """Run the full clause 7.5.14 bare-cell proton irradiation assessment.

    spec keys: exposures (label, energy_mev, fluence_p_per_cm2,
    relative_damage_coefficient, projected_range_um, off_normal_deg,
    power_after_w), reference_power_w, junction_depth_um,
    required_equivalent_fluence_p_per_cm2, allowed_power_loss; optional
    max_off_normal_deg, noise_allowance, reference_energy_mev.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "exposures",
        "reference_power_w",
        "junction_depth_um",
        "required_equivalent_fluence_p_per_cm2",
        "allowed_power_loss",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    exposures = spec["exposures"]
    if not isinstance(exposures, (list, tuple)) or not exposures:
        raise ValueError("exposures must be a non-empty sequence")
    reference_power = _positive(spec["reference_power_w"], "reference_power_w")
    allowed = _positive(spec["allowed_power_loss"], "allowed_power_loss")
    if allowed >= 1.0:
        raise ValueError("allowed_power_loss must be below 1.0, got %g" % allowed)

    findings = list(
        damage_coefficient_findings(
            exposures, spec.get("reference_energy_mev", REFERENCE_ENERGY_MEV)
        )
    )
    findings.extend(range_findings(exposures, spec["junction_depth_um"]))
    findings.extend(
        incidence_findings(
            exposures, spec.get("max_off_normal_deg", MAX_OFF_NORMAL_DEG)
        )
    )

    totals = accumulated_equivalent_fluence(exposures)
    labels = []
    losses = []
    track = []
    for exposure, total in zip(exposures, totals):
        item = validate_exposure(exposure)
        if "power_after_w" not in exposure:
            raise ValueError(
                "exposure '%s' missing key 'power_after_w'" % item["label"]
            )
        loss = power_loss_fraction(exposure["power_after_w"], reference_power)
        labels.append(item["label"])
        losses.append(loss)
        track.append({
            "label": item["label"],
            "energy_mev": item["energy_mev"],
            "equivalent_contribution_p_per_cm2": equivalent_contribution(
                exposure
            ),
            "accumulated_equivalent_p_per_cm2": total,
            "path_length_factor": path_length_factor(item["off_normal_deg"]),
            "power_loss_fraction": loss,
        })
    findings.extend(
        loss_track_findings(
            labels, losses, spec.get("noise_allowance", NOISE_ALLOWANCE)
        )
    )
    findings.extend(
        coverage_findings(
            totals[-1], spec["required_equivalent_fluence_p_per_cm2"]
        )
    )
    end_loss = losses[-1]
    if end_loss > allowed + LOSS_TOLERANCE:
        findings.append(
            "the cell ends the run %.4f down on power, over the %.4f the "
            "mission allows" % (end_loss, allowed)
        )
    return {
        "exposures": track,
        "exposure_count": len(track),
        "accumulated_equivalent_p_per_cm2": totals[-1],
        "end_power_loss_fraction": end_loss,
        "findings": findings,
        "run_conformant": not findings,
    }
