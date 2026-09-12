"""
Mass and inertia property budget control — deterministic, stdlib-only logic.
Implements ECSS-E-ST-32 clause 4.5.5 mass/inertia budget and control procedure.
"""

PHASE_MARGIN_REQUIREMENTS = {
    'A': 20.0,
    'B': 15.0,
    'C': 10.0,
    'D': 5.0,
}

VALID_PHASES = set(PHASE_MARGIN_REQUIREMENTS.keys())

_REQUIRED_ENTRY_FIELDS = {'name', 'mass_cbe_kg', 'mass_allocated_kg', 'position'}
_REQUIRED_SUBSYSTEM_FIELDS = {'name', 'cbe_kg', 'allocated_kg'}


def validate_mass_entry(entry):
    """
    Validate a component mass budget entry dict.
    Raises ValueError with a descriptive message on any invalid field.
    Returns the entry unchanged.
    """
    missing = _REQUIRED_ENTRY_FIELDS - set(entry.keys())
    if missing:
        raise ValueError(f"Mass entry missing required fields: {sorted(missing)}")

    name = entry['name']
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Mass entry 'name' must be a non-empty string")

    cbe = entry['mass_cbe_kg']
    if not isinstance(cbe, (int, float)):
        raise ValueError(f"Entry '{name}': mass_cbe_kg must be numeric")
    if cbe < 0:
        raise ValueError(f"Entry '{name}': mass_cbe_kg must be non-negative, got {cbe}")

    allocated = entry['mass_allocated_kg']
    if not isinstance(allocated, (int, float)):
        raise ValueError(f"Entry '{name}': mass_allocated_kg must be numeric")
    if allocated <= 0:
        raise ValueError(
            f"Entry '{name}': mass_allocated_kg must be positive, got {allocated}"
        )

    pos = entry['position']
    if not (isinstance(pos, (list, tuple)) and len(pos) == 3):
        raise ValueError(
            f"Entry '{name}': position must be a 3-element list or tuple (x, y, z)"
        )
    if not all(isinstance(c, (int, float)) for c in pos):
        raise ValueError(f"Entry '{name}': position coordinates must be numeric")

    return entry


def compute_mass_budget(entries):
    """
    Compute system-level mass budget totals from a list of component entries.

    Returns a dict with:
      total_cbe_kg       — sum of current best estimate masses
      total_allocated_kg — sum of allocated masses
      margin_kg          — total_allocated - total_cbe (negative means exceedance)
      margin_pct         — margin_kg / total_allocated * 100

    Raises ValueError if the list is empty or any entry fails validation.
    """
    if not entries:
        raise ValueError("At least one mass entry is required for budget computation")

    for entry in entries:
        validate_mass_entry(entry)

    total_cbe = sum(e['mass_cbe_kg'] for e in entries)
    total_allocated = sum(e['mass_allocated_kg'] for e in entries)
    margin_kg = total_allocated - total_cbe
    margin_pct = (margin_kg / total_allocated) * 100.0 if total_allocated > 0 else 0.0

    return {
        'total_cbe_kg': total_cbe,
        'total_allocated_kg': total_allocated,
        'margin_kg': margin_kg,
        'margin_pct': margin_pct,
    }


def compute_center_of_mass(entries):
    """
    Compute the system center of mass from component mass entries.
    Uses mass_cbe_kg as the mass weight for each component.

    Returns (cx, cy, cz) in metres relative to the system reference frame origin.
    Raises ValueError if total CBE mass is zero (undefined CoM) or entries invalid.
    """
    if not entries:
        raise ValueError("At least one mass entry is required")

    for entry in entries:
        validate_mass_entry(entry)

    total_mass = sum(e['mass_cbe_kg'] for e in entries)
    if total_mass == 0.0:
        raise ValueError(
            "Total CBE mass is zero; center of mass is undefined"
        )

    cx = sum(e['mass_cbe_kg'] * e['position'][0] for e in entries) / total_mass
    cy = sum(e['mass_cbe_kg'] * e['position'][1] for e in entries) / total_mass
    cz = sum(e['mass_cbe_kg'] * e['position'][2] for e in entries) / total_mass

    return (cx, cy, cz)


def compute_moments_of_inertia(entries, reference_point=(0.0, 0.0, 0.0)):
    """
    Compute Ixx, Iyy, Izz about reference_point using the point-mass approximation
    (no self-inertia of individual components):

      Ixx = Σ m_i ((y_i - ry)² + (z_i - rz)²)
      Iyy = Σ m_i ((x_i - rx)² + (z_i - rz)²)
      Izz = Σ m_i ((x_i - rx)² + (y_i - ry)²)

    Returns (Ixx, Iyy, Izz) in kg·m².
    Raises ValueError if entries are empty or invalid.
    """
    if not entries:
        raise ValueError("At least one mass entry is required")

    for entry in entries:
        validate_mass_entry(entry)

    rx, ry, rz = reference_point
    Ixx = 0.0
    Iyy = 0.0
    Izz = 0.0

    for e in entries:
        m = e['mass_cbe_kg']
        x, y, z = e['position']
        dx = x - rx
        dy = y - ry
        dz = z - rz
        Ixx += m * (dy ** 2 + dz ** 2)
        Iyy += m * (dx ** 2 + dz ** 2)
        Izz += m * (dx ** 2 + dy ** 2)

    return (Ixx, Iyy, Izz)


def check_mass_margin(total_cbe_kg, total_allocated_kg, phase):
    """
    Verify that the mass margin satisfies the minimum required for the given
    design phase (A, B, C, or D per ECSS-E-ST-32 clause 4.5.5).

    Returns a dict with:
      margin_pct        — (allocated - cbe) / allocated * 100
      min_required_pct  — minimum required margin for the phase
      compliant         — True iff margin_pct >= min_required_pct

    Raises ValueError for an unknown phase or non-positive allocated mass.
    """
    phase = phase.upper()
    if phase not in VALID_PHASES:
        raise ValueError(
            f"Unknown design phase '{phase}'. Must be one of {sorted(VALID_PHASES)}"
        )
    if total_allocated_kg <= 0:
        raise ValueError("total_allocated_kg must be positive")
    if total_cbe_kg < 0:
        raise ValueError("total_cbe_kg must be non-negative")

    margin_kg = total_allocated_kg - total_cbe_kg
    margin_pct = (margin_kg / total_allocated_kg) * 100.0
    min_required = PHASE_MARGIN_REQUIREMENTS[phase]
    compliant = margin_pct >= min_required

    return {
        'margin_pct': margin_pct,
        'min_required_pct': min_required,
        'compliant': compliant,
    }


def roll_up_subsystems(subsystem_list):
    """
    Roll up a list of subsystem budget entries to system level.
    Each entry must have: name (str), cbe_kg (float ≥ 0), allocated_kg (float > 0).

    Returns a dict with:
      total_cbe_kg       — sum of subsystem CBE masses
      total_allocated_kg — sum of subsystem allocations
      margin_kg          — total_allocated - total_cbe
      margin_pct         — margin as percentage of total_allocated
      subsystem_count    — number of subsystems rolled up

    Raises ValueError if the list is empty or any entry is invalid.
    """
    if not subsystem_list:
        raise ValueError("At least one subsystem is required for roll-up")

    for ss in subsystem_list:
        missing = _REQUIRED_SUBSYSTEM_FIELDS - set(ss.keys())
        if missing:
            raise ValueError(
                f"Subsystem entry missing required fields: {sorted(missing)}"
            )
        if ss['cbe_kg'] < 0:
            raise ValueError(
                f"Subsystem '{ss['name']}': cbe_kg must be non-negative"
            )
        if ss['allocated_kg'] <= 0:
            raise ValueError(
                f"Subsystem '{ss['name']}': allocated_kg must be positive"
            )

    total_cbe = sum(ss['cbe_kg'] for ss in subsystem_list)
    total_allocated = sum(ss['allocated_kg'] for ss in subsystem_list)
    margin_kg = total_allocated - total_cbe
    margin_pct = (margin_kg / total_allocated) * 100.0

    return {
        'total_cbe_kg': total_cbe,
        'total_allocated_kg': total_allocated,
        'margin_kg': margin_kg,
        'margin_pct': margin_pct,
        'subsystem_count': len(subsystem_list),
    }


def generate_sms_drd_fields(entries, phase, reference_point=(0.0, 0.0, 0.0)):
    """
    Generate the complete set of mass and inertia fields required for the
    Structural Mechanics Summary (SMS) DRD.

    Returns a dict containing:
      total_cbe_kg, total_allocated_kg, margin_kg, margin_pct
      phase, phase_margin_required_pct, mass_margin_compliant
      center_of_mass_m  — (cx, cy, cz) tuple in metres
      Ixx_kg_m2, Iyy_kg_m2, Izz_kg_m2
      reference_point_m — reference point used for MoI computation

    Raises ValueError for invalid entries, unknown phase, or zero total mass.
    """
    budget = compute_mass_budget(entries)
    com = compute_center_of_mass(entries)
    moi = compute_moments_of_inertia(entries, reference_point)
    margin_check = check_mass_margin(
        budget['total_cbe_kg'], budget['total_allocated_kg'], phase
    )

    return {
        'total_cbe_kg': budget['total_cbe_kg'],
        'total_allocated_kg': budget['total_allocated_kg'],
        'margin_kg': budget['margin_kg'],
        'margin_pct': budget['margin_pct'],
        'phase': phase.upper(),
        'phase_margin_required_pct': margin_check['min_required_pct'],
        'mass_margin_compliant': margin_check['compliant'],
        'center_of_mass_m': com,
        'Ixx_kg_m2': moi[0],
        'Iyy_kg_m2': moi[1],
        'Izz_kg_m2': moi[2],
        'reference_point_m': reference_point,
    }
