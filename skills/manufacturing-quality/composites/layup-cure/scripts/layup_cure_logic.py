"""Composite laminate layup and cure process engineering logic.

Pure Python 3, stdlib only. No numpy, no scipy, no network.

Implements:
  - ply_book(): ply sequence with orientation, material, thickness per ply
  - symmetric_check(): ply sequence mirrors around the midplane
  - balanced_check(): every +theta ply has a matching -theta ply
  - cure_cycle_timeline(): vacuum, heat ramp, cure dwell, cool-down,
    pressure (autoclave vs out-of-autoclave vs press)
  - degree_of_cure(): Arrhenius kinetics d(alpha)/dt =
    A * exp(-Ea/(R*T)) * (1-alpha)^n integrated over the temperature
    profile with small time steps
  - glass_transition_tg(): Tg vs degree of cure (DiBenedetto form)
  - c_scan_verdict(): C-scan porosity acceptance disposition

Units: temperatures in degrees Fahrenheit in profiles and timelines
(aerospace practice), converted to Kelvin inside kinetics; time in
minutes; A in 1/min; Ea in J/mol; R = 8.314 J/(mol*K).
"""

import math

R_GAS = 8.314  # J/(mol*K), universal gas constant

DEFAULT_MATERIAL = "carbon-epoxy-prepreg"
DEFAULT_THICKNESS_MM = 0.190  # ~0.0075 in cured ply thickness

ORIENTATION_RANGE = (-90, 90)  # inclusive, integer degrees

# Typical causes of porosity found by C-scan after cure.
POROSITY_CAUSES = [
    "air entrapped between plies during layup (poor debulk, bridging)",
    "vacuum leak or insufficient vacuum level in the bag",
    "moisture absorbed by prepreg or core outgassing",
    "ramp too fast, volatiles trapped before resin gels",
    "insufficient consolidation pressure (low autoclave pressure or "
    "unsealed out-of-autoclave bag)",
    "resin-rich or resin-starved zones from uneven bleed",
]


def _validate_orientation(theta):
    """Reject non-integer or out-of-range ply orientations."""
    if isinstance(theta, bool) or not isinstance(theta, int):
        raise ValueError(
            "ply orientation must be an integer degree value, got %r" % (theta,)
        )
    lo, hi = ORIENTATION_RANGE
    if not (lo <= theta <= hi):
        raise ValueError(
            "ply orientation %r out of range %d..%d degrees" % (theta, lo, hi)
        )


def _validate_sequence(sequence):
    """Reject empty sequences and invalid ply orientations."""
    if not sequence:
        raise ValueError("ply sequence must not be empty")
    for theta in sequence:
        _validate_orientation(theta)


def ply_book(sequence, materials=None, thicknesses_mm=None):
    """Build a ply book from a sequence of ply orientations.

    sequence: list of integer ply orientations in degrees, ordered from
      tool side to bag side.
    materials: optional list of material names, one per ply (defaults to
      carbon-epoxy-prepreg for every ply).
    thicknesses_mm: optional list of cured ply thicknesses in mm
      (defaults to 0.190 mm per ply).

    Returns a dict with plies (per-ply records: ply number, orientation,
    material, thickness), ply_count, total_thickness_mm, sequence.
    Raises ValueError on invalid orientations or length mismatches.
    """
    _validate_sequence(sequence)
    n = len(sequence)
    mats = materials if materials is not None else [DEFAULT_MATERIAL] * n
    thks = thicknesses_mm if thicknesses_mm is not None else [DEFAULT_THICKNESS_MM] * n
    if len(mats) != n:
        raise ValueError("materials length %d does not match ply count %d" % (len(mats), n))
    if len(thks) != n:
        raise ValueError("thicknesses_mm length %d does not match ply count %d" % (len(thks), n))
    for t in thks:
        if t <= 0:
            raise ValueError("ply thickness must be positive, got %r" % (t,))
    plies = [
        {
            "ply": i + 1,
            "orientation": theta,
            "material": mats[i],
            "thickness_mm": thks[i],
        }
        for i, theta in enumerate(sequence)
    ]
    return {
        "plies": plies,
        "ply_count": n,
        "total_thickness_mm": float(sum(thks)),
        "sequence": list(sequence),
    }


def symmetric_check(sequence):
    """True when the ply sequence mirrors exactly around the midplane.

    Index i must equal index n-1-i for every ply. Mirroring across the
    midplane does not flip the in-plane orientation sign, so a +45 at
    position i mirrors to a +45 at position n-1-i. Returns a dict with
    the boolean verdict and the reason.
    """
    _validate_sequence(sequence)
    n = len(sequence)
    mismatches = []
    for i in range(n // 2):
        if sequence[i] != sequence[n - 1 - i]:
            mismatches.append((i + 1, sequence[i], n - i, sequence[n - 1 - i]))
    if not mismatches:
        reason = "ply sequence mirrors around the midplane (symmetric)"
    else:
        ply_a, ori_a, ply_b, ori_b = mismatches[0]
        reason = (
            "asymmetric: ply %d (%d deg) does not mirror ply %d (%d deg)"
            % (ply_a, ori_a, ply_b, ori_b)
        )
    return {"symmetric": not mismatches, "reason": reason, "sequence": list(sequence)}


def balanced_check(sequence):
    """True when every +theta ply has a matching -theta ply.

    Counts of +theta and -theta must be equal for each nonzero angle.
    0 deg plies and 90/-90 deg plies are self-balancing (90 and -90 are
    the same in-plane direction). An odd ply count is allowed because a
    center ply sits on the midplane. Returns a dict with the boolean
    verdict, the reason, and the per-angle ply counts.
    """
    _validate_sequence(sequence)
    counts = {}
    for theta in sequence:
        t = 90 if abs(theta) == 90 else theta  # 90 and -90 are the same direction
        counts[t] = counts.get(t, 0) + 1
    missing = []
    for theta in sorted(counts):
        if theta == 0 or theta == 90:
            continue
        if counts.get(-theta, 0) != counts[theta]:
            missing.append((theta, counts[theta], counts.get(-theta, 0)))
    if not missing:
        reason = "every +theta ply has a matching -theta ply (balanced)"
    else:
        parts = [
            "%+d deg has %d plies but %+d deg has %d" % (t, c, -t, m)
            for t, c, m in missing
        ]
        reason = "unbalanced: " + "; ".join(parts)
    return {"balanced": not missing, "reason": reason, "counts": counts}


def cure_cycle_timeline(
    ramp_rate_fpm=2.0,
    cure_temp_f=350.0,
    dwell_min=120.0,
    cool_rate_fpm=5.0,
    start_temp_f=70.0,
    end_temp_f=140.0,
    vacuum_stabilize_min=15.0,
    vacuum=True,
    pressure_type="autoclave",
    pressure_psi=85.0,
    vacuum_inhg=-28.0,
):
    """Design a cure cycle timeline for a thermoset prepreg laminate.

    Standard aerospace 350F (177C) epoxy cycle:
      1. vacuum-stabilize at start temperature (bag leak check, debulk)
      2. heat ramp at ramp_rate_fpm to cure_temp_f
      3. dwell at cure_temp_f for dwell_min (resin cure)
      4. cool at cool_rate_fpm to end_temp_f, vent and release pressure

    pressure_type selects the consolidation method:
      'autoclave': vacuum bag plus applied gas pressure (45-100 psi)
      'out-of-autoclave': vacuum bag only, atmospheric consolidation
      'press': matched metal dies, hydraulic pressure, no vacuum bag

    Returns a dict with ordered phases, the piecewise-linear temperature
    profile as [(time_min, temp_F)] points (suitable for
    degree_of_cure()), total_time_min, and the pressure summary.
    Raises ValueError on non-positive rates or a cure temperature at or
    below the start temperature.
    """
    if ramp_rate_fpm <= 0:
        raise ValueError("ramp_rate_fpm must be positive")
    if cool_rate_fpm <= 0:
        raise ValueError("cool_rate_fpm must be positive")
    if dwell_min < 0:
        raise ValueError("dwell_min must be >= 0")
    if vacuum_stabilize_min < 0:
        raise ValueError("vacuum_stabilize_min must be >= 0")
    if cure_temp_f <= start_temp_f:
        raise ValueError("cure_temp_f must be above start_temp_f for a heat ramp")
    if pressure_type not in ("autoclave", "out-of-autoclave", "press"):
        raise ValueError(
            "pressure_type must be autoclave, out-of-autoclave, or press, got %r"
            % (pressure_type,)
        )

    apply_pressure = pressure_type != "out-of-autoclave"
    bag_vacuum = vacuum_inhg if vacuum else 0.0

    t0 = 0.0
    phases = []
    profile = [(t0, start_temp_f)]

    if vacuum and vacuum_stabilize_min > 0:
        t1 = t0 + vacuum_stabilize_min
        phases.append(
            {
                "phase": "vacuum-stabilize",
                "start_min": t0,
                "end_min": t1,
                "start_temp_f": start_temp_f,
                "end_temp_f": start_temp_f,
                "vacuum_inhg": bag_vacuum,
                "pressure_psi": 0.0,
                "note": "vacuum bag leak check and debulk hold",
            }
        )
        t0 = t1

    ramp_min = (cure_temp_f - start_temp_f) / ramp_rate_fpm
    t1 = t0 + ramp_min
    phases.append(
        {
            "phase": "ramp",
            "start_min": t0,
            "end_min": t1,
            "start_temp_f": start_temp_f,
            "end_temp_f": cure_temp_f,
            "vacuum_inhg": bag_vacuum,
            "pressure_psi": pressure_psi if apply_pressure else 0.0,
            "note": "heat ramp at %.1f F/min" % ramp_rate_fpm,
        }
    )
    profile.append((t1, cure_temp_f))
    t0 = t1

    t1 = t0 + dwell_min
    phases.append(
        {
            "phase": "dwell",
            "start_min": t0,
            "end_min": t1,
            "start_temp_f": cure_temp_f,
            "end_temp_f": cure_temp_f,
            "vacuum_inhg": bag_vacuum,
            "pressure_psi": pressure_psi if apply_pressure else 0.0,
            "note": "resin cure dwell at %.0f F" % cure_temp_f,
        }
    )
    profile.append((t1, cure_temp_f))
    t0 = t1

    cool_min = (cure_temp_f - end_temp_f) / cool_rate_fpm
    t1 = t0 + cool_min
    phases.append(
        {
            "phase": "cool",
            "start_min": t0,
            "end_min": t1,
            "start_temp_f": cure_temp_f,
            "end_temp_f": end_temp_f,
            "vacuum_inhg": bag_vacuum,
            "pressure_psi": pressure_psi if apply_pressure else 0.0,
            "note": "cool at %.1f F/min; vent vacuum and release pressure below 150 F"
            % cool_rate_fpm,
        }
    )
    profile.append((t1, end_temp_f))

    pressure = {
        "type": pressure_type,
        "pressure_psi": pressure_psi if apply_pressure else 0.0,
        "vacuum_inhg": bag_vacuum,
        "note": {
            "autoclave": "consolidation pressure plus vacuum bag",
            "out-of-autoclave": "vacuum bag only, atmospheric consolidation",
            "press": "matched metal dies, hydraulic pressure, no vacuum bag",
        }[pressure_type],
    }
    return {
        "phases": phases,
        "profile": profile,
        "total_time_min": t1,
        "pressure": pressure,
    }


def degree_of_cure(temperature_profile, A, Ea, n, dt=0.5):
    """Integrate Arrhenius cure kinetics over a temperature profile.

    Model: d(alpha)/dt = A * exp(-Ea / (R * T)) * (1 - alpha)^n

    temperature_profile: iterable of (time_min, temp_F) points defining
      a piecewise-linear temperature history, or the dict returned by
      cure_cycle_timeline() (its "profile" is used).
    A: pre-exponential factor in 1/min.
    Ea: activation energy in J/mol.
    n: reaction order (dimensionless).
    dt: integration step in minutes, small relative to ramp and hold
      times (default 0.5 min).

    Returns the final degree of cure alpha in [0, 1].
    Raises ValueError on malformed profiles or non-positive kinetics.
    """
    if isinstance(temperature_profile, dict):
        temperature_profile = temperature_profile["profile"]
    pts = [(float(t), float(f)) for t, f in temperature_profile]
    if len(pts) < 2:
        raise ValueError("temperature profile needs at least 2 points")
    if any(t < 0 for t, _ in pts):
        raise ValueError("profile times must be >= 0")
    if A <= 0 or Ea <= 0:
        raise ValueError("A and Ea must be positive")
    if n < 0:
        raise ValueError("n must be >= 0")
    if dt <= 0:
        raise ValueError("dt must be positive")

    def kelvin(f):
        return (f - 32.0) * 5.0 / 9.0 + 273.15

    alpha = 0.0
    for i in range(1, len(pts)):
        t0, f0 = pts[i - 1]
        t1, f1 = pts[i]
        seg = t1 - t0
        if seg <= 0:
            continue
        nsteps = max(1, int(round(seg / dt)))
        step = seg / nsteps
        for j in range(nsteps):
            frac = (j * step) / seg
            f_now = f0 + (f1 - f0) * frac
            k = A * math.exp(-Ea / (R_GAS * kelvin(f_now)))
            alpha += k * (max(0.0, 1.0 - alpha) ** n) * step
            if alpha >= 1.0:
                alpha = 1.0
    return alpha


def glass_transition_tg(alpha, tg0_c=-10.0, tg_inf_c=200.0, lambda_d=0.4):
    """Glass transition temperature vs degree of cure (DiBenedetto form).

    Tg = Tg0 + (Tg_inf - Tg0) * (lambda * alpha) / (1 - (1 - lambda) * alpha)

    tg0_c: Tg of uncured resin at alpha = 0, deg C (default -10).
    tg_inf_c: Tg of fully cured resin at alpha = 1, deg C (default 200).
    lambda_d: DiBenedetto fitting constant in (0, 1] (default 0.4).

    Returns Tg in deg C. The rule of thumb: keep the cure cycle so the
    part Tg exceeds the maximum service temperature by at least 25-30 C;
    a degree of cure below ~0.90 leaves Tg well below Tg_inf.
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("alpha must be in [0, 1], got %r" % (alpha,))
    if not (0.0 < lambda_d <= 1.0):
        raise ValueError("lambda_d must be in (0, 1], got %r" % (lambda_d,))
    return tg0_c + (tg_inf_c - tg0_c) * (lambda_d * alpha) / (
        1.0 - (1.0 - lambda_d) * alpha
    )


def c_scan_verdict(porosity_pct, acceptance_limit_pct=1.0, attenuation_db=None):
    """Disposition a C-scan porosity result against the acceptance limit.

    Aerospace primary structure typically limits porosity to 1% by area
    (up to 2% for secondary structure), per CMH-17 and the part
    specification. C-scan maps through-transmission or pulse-echo
    attenuation; high attenuation zones correlate with porosity.

    Returns a dict with the PASS/FAIL verdict, the measured porosity,
    the acceptance limit, optional attenuation in dB, and the porosity
    causes to cite in the nonconformance record.
    Raises ValueError on negative porosity or non-positive limit.
    """
    if porosity_pct < 0:
        raise ValueError("porosity_pct must be >= 0, got %r" % (porosity_pct,))
    if acceptance_limit_pct <= 0:
        raise ValueError("acceptance_limit_pct must be positive")
    verdict = "PASS" if porosity_pct <= acceptance_limit_pct else "FAIL"
    note = (
        "porosity within acceptance limit, C-scan area qualifies"
        if verdict == "PASS"
        else "porosity exceeds acceptance limit, part needs disposition "
        "(repair assessment or reject)"
    )
    return {
        "verdict": verdict,
        "porosity_pct": porosity_pct,
        "acceptance_limit_pct": acceptance_limit_pct,
        "attenuation_db": attenuation_db,
        "porosity_causes": list(POROSITY_CAUSES),
        "note": note,
    }
