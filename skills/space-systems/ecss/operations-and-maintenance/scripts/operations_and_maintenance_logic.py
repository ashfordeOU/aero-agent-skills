"""
Operations and maintenance engineering logic for ECSS-E-ST-32 clause 4.2.3.

Covers: maximum allowable operating pressure, structural damage assessment,
maintenance interval scheduling, inspection finding acceptance, and
service life tracking. Stdlib only, offline, deterministic.
"""

MINIMUM_SAFETY_FACTOR = 1.0

VALID_DAMAGE_TYPES = frozenset({"dent", "scratch", "crack", "delamination", "corrosion"})
VALID_FINDING_TYPES = frozenset({"dimensional", "visual", "torque", "pressure_test"})

# Ratio thresholds for damage disposition
_ADL_ACCEPT_THRESHOLD = 0.75
_ADL_CONDITIONAL_THRESHOLD = 1.0

# Fraction of design life at which service status changes to near-limit
_NEAR_LIMIT_FRACTION = 0.9


def compute_max_allowable_operating_pressure(proof_pressure_pa, safety_factor):
    """Return the maximum allowable operating pressure (Pa).

    MAOP = proof_pressure / safety_factor. A safety factor below 1.0 is
    physically inadmissible (MAOP would exceed proof pressure).
    """
    if proof_pressure_pa <= 0:
        raise ValueError(
            f"proof_pressure_pa must be positive, got {proof_pressure_pa}"
        )
    if safety_factor < MINIMUM_SAFETY_FACTOR:
        raise ValueError(
            f"safety_factor must be >= {MINIMUM_SAFETY_FACTOR}, got {safety_factor}"
        )
    return proof_pressure_pa / safety_factor


def check_operating_pressure(operating_pressure_pa, maop_pa):
    """Check whether an operating pressure is within the safe limit.

    Returns a dict with keys:
      compliant (bool)      — True when operating_pressure_pa <= maop_pa
      margin_fraction (float) — (maop - op) / maop; negative when exceeded
      status (str)          — "PASS" or "EXCEED"
    """
    if operating_pressure_pa <= 0:
        raise ValueError(
            f"operating_pressure_pa must be positive, got {operating_pressure_pa}"
        )
    if maop_pa <= 0:
        raise ValueError(f"maop_pa must be positive, got {maop_pa}")
    margin = (maop_pa - operating_pressure_pa) / maop_pa
    compliant = operating_pressure_pa <= maop_pa
    return {
        "compliant": compliant,
        "margin_fraction": margin,
        "status": "PASS" if compliant else "EXCEED",
    }


def assess_damage(observed_size_mm, allowable_damage_limit_mm, damage_type):
    """Compare an observed damage measurement against its allowable damage limit.

    Disposition rules (ratio = observed / ADL):
      <= 0.75  -> "ACCEPT"
      <= 1.0   -> "CONDITIONAL"
      >  1.0   -> "REJECT"

    Returns a dict with keys: damage_type, observed_mm, adl_mm, ratio, disposition.
    """
    if damage_type not in VALID_DAMAGE_TYPES:
        raise ValueError(
            f"Unrecognized damage type '{damage_type}'. "
            f"Valid types: {sorted(VALID_DAMAGE_TYPES)}"
        )
    if observed_size_mm < 0:
        raise ValueError(
            f"observed_size_mm must be non-negative, got {observed_size_mm}"
        )
    if allowable_damage_limit_mm <= 0:
        raise ValueError(
            f"allowable_damage_limit_mm must be positive, got {allowable_damage_limit_mm}"
        )
    ratio = observed_size_mm / allowable_damage_limit_mm
    if ratio <= _ADL_ACCEPT_THRESHOLD:
        disposition = "ACCEPT"
    elif ratio <= _ADL_CONDITIONAL_THRESHOLD:
        disposition = "CONDITIONAL"
    else:
        disposition = "REJECT"
    return {
        "damage_type": damage_type,
        "observed_mm": observed_size_mm,
        "adl_mm": allowable_damage_limit_mm,
        "ratio": ratio,
        "disposition": disposition,
    }


def compute_maintenance_interval(
    design_life_cycles, inspection_interval_fraction, last_inspection_cycle
):
    """Compute the next maintenance due cycle.

    interval_cycles = design_life_cycles * inspection_interval_fraction
    next_due_cycle  = last_inspection_cycle + interval_cycles

    overdue_at_design_life is True when next_due_cycle > design_life_cycles,
    indicating the component must be retired or life-extended before the
    next interval falls due.

    Returns a dict with keys: interval_cycles, next_due_cycle, overdue_at_design_life.
    """
    if design_life_cycles <= 0:
        raise ValueError(
            f"design_life_cycles must be positive, got {design_life_cycles}"
        )
    if not (0 < inspection_interval_fraction <= 1.0):
        raise ValueError(
            "inspection_interval_fraction must be in (0, 1], "
            f"got {inspection_interval_fraction}"
        )
    if last_inspection_cycle < 0:
        raise ValueError(
            f"last_inspection_cycle must be non-negative, got {last_inspection_cycle}"
        )
    interval_cycles = design_life_cycles * inspection_interval_fraction
    next_due_cycle = last_inspection_cycle + interval_cycles
    overdue_at_design_life = next_due_cycle > design_life_cycles
    return {
        "interval_cycles": interval_cycles,
        "next_due_cycle": next_due_cycle,
        "overdue_at_design_life": overdue_at_design_life,
    }


def check_inspection_finding(finding_type, measured_value, lower_limit, upper_limit):
    """Check whether an inspection measurement is within its acceptance band.

    Returns a dict with keys: finding_type, measured, lower_limit, upper_limit, status.
    status is "PASS" when lower_limit <= measured_value <= upper_limit, else "FAIL".
    """
    if finding_type not in VALID_FINDING_TYPES:
        raise ValueError(
            f"Unrecognized finding type '{finding_type}'. "
            f"Valid types: {sorted(VALID_FINDING_TYPES)}"
        )
    if lower_limit > upper_limit:
        raise ValueError(
            f"lower_limit ({lower_limit}) must be <= upper_limit ({upper_limit})"
        )
    in_tolerance = lower_limit <= measured_value <= upper_limit
    return {
        "finding_type": finding_type,
        "measured": measured_value,
        "lower_limit": lower_limit,
        "upper_limit": upper_limit,
        "status": "PASS" if in_tolerance else "FAIL",
    }


def check_service_life(cycles_accumulated, design_life_cycles, life_fraction_limit=_NEAR_LIMIT_FRACTION):
    """Determine service status from accumulated and design cycles.

    Status rules (fraction_used = cycles_accumulated / design_life_cycles):
      > 1.0                  -> "EXPIRED"   (immediate stop-work)
      >= life_fraction_limit -> "NEAR_LIMIT" (initiate life-extension review)
      otherwise              -> "IN_SERVICE"

    Returns a dict with keys: cycles_accumulated, design_life_cycles,
    fraction_used, remaining_cycles, status.
    """
    if cycles_accumulated < 0:
        raise ValueError(
            f"cycles_accumulated must be non-negative, got {cycles_accumulated}"
        )
    if design_life_cycles <= 0:
        raise ValueError(
            f"design_life_cycles must be positive, got {design_life_cycles}"
        )
    if not (0 < life_fraction_limit <= 1.0):
        raise ValueError(
            f"life_fraction_limit must be in (0, 1], got {life_fraction_limit}"
        )
    fraction_used = cycles_accumulated / design_life_cycles
    remaining_cycles = design_life_cycles - cycles_accumulated
    if fraction_used > 1.0:
        status = "EXPIRED"
    elif fraction_used >= life_fraction_limit:
        status = "NEAR_LIMIT"
    else:
        status = "IN_SERVICE"
    return {
        "cycles_accumulated": cycles_accumulated,
        "design_life_cycles": design_life_cycles,
        "fraction_used": fraction_used,
        "remaining_cycles": remaining_cycles,
        "status": status,
    }
