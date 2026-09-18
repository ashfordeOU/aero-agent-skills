"""Layout parasitic extraction and budget assessment for die-form MMICs.

Anchor: ECSS-Q-ST-60-12C clause 7.2.3 (parasitic effect analysis -- accounting
for the unintended coupling, inductance and capacitance a physical layout adds
to the schematic-level circuit). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the interconnect geometry: bond-wire lengths and radii, on-die
   track lengths, widths and thicknesses, conductor separations and the
   dielectric constant of the medium between coupled conductors.
2. Size the series parasitic inductance of every bond wire and track from its
   geometry, and the shunt coupling capacitance between every declared
   conductor pair from the facing area and the separation.
3. Convert both into reactances at the highest frequency the part is used at,
   because a parasitic that is negligible at the design centre is not
   necessarily negligible at the top of the band.
4. Locate the parasitic self-resonance of each net from its own inductance and
   capacitance; a self-resonance inside or close above the operating band
   turns a nominally series element into an open circuit.
5. Grade the series reactance against the reference impedance, the insertion
   phase error against its budget, and the conductor-to-conductor isolation
   against the required value, and name the net that dominates each finding.
"""

import math

__all__ = [
    "MU0",
    "EPS0",
    "REACTANCE_TOLERANCE",
    "MIN_LENGTH_RADIUS_RATIO",
    "validate_positive",
    "bond_wire_inductance_nh",
    "track_inductance_nh",
    "coupling_capacitance_ff",
    "inductive_reactance_ohm",
    "capacitive_reactance_ohm",
    "self_resonant_frequency_ghz",
    "insertion_phase_error_deg",
    "isolation_db",
    "evaluate_net",
    "evaluate_coupling_pair",
    "assess_parasitic_effects",
]

# Vacuum permeability (H/m) and permittivity (F/m).
MU0 = 4.0e-7 * math.pi
EPS0 = 8.8541878128e-12

# Reactance and frequency comparisons are ratios of computed floats; a case
# that is physically exactly on the budget can land a few ULPs on the wrong
# side. Absorb the representation error here, never by relaxing the budget.
REACTANCE_TOLERANCE = 1e-9

# The thin-wire inductance expression is a long-wire approximation. Below this
# length-to-radius ratio it is outside its range of validity and the caller
# must supply an extracted value instead of a formula estimate.
MIN_LENGTH_RADIUS_RATIO = 4.0


def validate_positive(label, value):
    """Return value as a strictly positive finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return number


def bond_wire_inductance_nh(length_um, radius_um, loop_factor=1.0):
    """Return the self-inductance in nH of a round bond wire.

    length_um and radius_um are the wire length and conductor radius in
    micrometres; loop_factor scales the result for the extra path length of a
    high loop profile relative to the straight span.
    """
    length = validate_positive("length_um", length_um)
    radius = validate_positive("radius_um", radius_um)
    factor = validate_positive("loop_factor", loop_factor)
    if factor < 1.0:
        raise ValueError("loop_factor cannot shorten the wire, got %r" % (loop_factor,))
    ratio = length / radius
    if ratio < MIN_LENGTH_RADIUS_RATIO:
        raise ValueError(
            "length/radius %g is below the %g validity floor of the thin-wire "
            "expression; supply an extracted inductance instead"
            % (ratio, MIN_LENGTH_RADIUS_RATIO)
        )
    metres = length * 1.0e-6 * factor
    henries = (MU0 / (2.0 * math.pi)) * metres * (math.log(2.0 * ratio) - 0.75)
    return henries * 1.0e9


def track_inductance_nh(length_um, width_um, thickness_um):
    """Return the self-inductance in nH of a flat on-die interconnect track."""
    length = validate_positive("length_um", length_um)
    width = validate_positive("width_um", width_um)
    thickness = validate_positive("thickness_um", thickness_um)
    girth = width + thickness
    ratio = 2.0 * length / girth
    if ratio <= 1.0:
        raise ValueError(
            "track is not long compared with its cross-section (2*l/(w+t)=%g); "
            "supply an extracted inductance instead" % ratio
        )
    metres = length * 1.0e-6
    henries = 2.0e-7 * metres * (
        math.log(ratio) + 0.5 + 0.2235 * girth / length
    )
    if henries <= 0.0:
        raise ValueError("track geometry yields a non-physical inductance")
    return henries * 1.0e9


def coupling_capacitance_ff(length_um, separation_um, facing_height_um, relative_permittivity):
    """Return the coupling capacitance in fF between two parallel conductors.

    The facing sidewalls of length_um by facing_height_um separated by
    separation_um are treated as a parallel-plate pair in a medium of the given
    relative permittivity.
    """
    length = validate_positive("length_um", length_um)
    separation = validate_positive("separation_um", separation_um)
    height = validate_positive("facing_height_um", facing_height_um)
    eps_r = validate_positive("relative_permittivity", relative_permittivity)
    if eps_r < 1.0:
        raise ValueError(
            "relative_permittivity cannot be below unity, got %r" % (relative_permittivity,)
        )
    area_m2 = (length * 1.0e-6) * (height * 1.0e-6)
    farads = EPS0 * eps_r * area_m2 / (separation * 1.0e-6)
    return farads * 1.0e15


def inductive_reactance_ohm(inductance_nh, frequency_ghz):
    """Return the series reactance in ohms of an inductance at a frequency."""
    inductance = validate_positive("inductance_nh", inductance_nh)
    frequency = validate_positive("frequency_ghz", frequency_ghz)
    return 2.0 * math.pi * (frequency * 1.0e9) * (inductance * 1.0e-9)


def capacitive_reactance_ohm(capacitance_ff, frequency_ghz):
    """Return the shunt reactance magnitude in ohms of a capacitance."""
    capacitance = validate_positive("capacitance_ff", capacitance_ff)
    frequency = validate_positive("frequency_ghz", frequency_ghz)
    return 1.0 / (2.0 * math.pi * (frequency * 1.0e9) * (capacitance * 1.0e-15))


def self_resonant_frequency_ghz(inductance_nh, capacitance_ff):
    """Return the self-resonant frequency in GHz of a parasitic L-C pair."""
    inductance = validate_positive("inductance_nh", inductance_nh) * 1.0e-9
    capacitance = validate_positive("capacitance_ff", capacitance_ff) * 1.0e-15
    return 1.0 / (2.0 * math.pi * math.sqrt(inductance * capacitance)) / 1.0e9


def insertion_phase_error_deg(series_reactance_ohm, reference_impedance_ohm):
    """Return the insertion phase error in degrees added by a series reactance."""
    reactance = validate_positive("series_reactance_ohm", series_reactance_ohm)
    impedance = validate_positive("reference_impedance_ohm", reference_impedance_ohm)
    return math.degrees(math.atan2(reactance, 2.0 * impedance))


def isolation_db(coupling_reactance_ohm, reference_impedance_ohm):
    """Return the conductor-to-conductor isolation in dB through a coupling path.

    The aggressor drives the victim through the coupling reactance into the two
    parallel terminations the victim sees, so the voltage ratio is a divider
    between that reactance and half the reference impedance.
    """
    reactance = validate_positive("coupling_reactance_ohm", coupling_reactance_ohm)
    impedance = validate_positive("reference_impedance_ohm", reference_impedance_ohm)
    half = impedance / 2.0
    return 20.0 * math.log10(math.hypot(reactance, half) / half)


def evaluate_net(net, frequency_ghz, reference_impedance_ohm):
    """Evaluate one interconnect net and return its parasitic record.

    net keys: name, kind ('bond_wire' or 'track'), the geometry keys the chosen
    kind needs, and shunt_capacitance_ff for the net's own capacitance to
    ground.
    """
    if not isinstance(net, dict):
        raise ValueError("net must be a mapping")
    name = net.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("net requires a non-empty 'name'")
    kind = net.get("kind")
    if kind == "bond_wire":
        inductance = bond_wire_inductance_nh(
            net.get("length_um"), net.get("radius_um"), net.get("loop_factor", 1.0)
        )
    elif kind == "track":
        inductance = track_inductance_nh(
            net.get("length_um"), net.get("width_um"), net.get("thickness_um")
        )
    else:
        raise ValueError(
            "net '%s' has an unknown kind %r; use 'bond_wire' or 'track'" % (name, kind)
        )
    shunt_ff = validate_positive("shunt_capacitance_ff", net.get("shunt_capacitance_ff"))
    reactance = inductive_reactance_ohm(inductance, frequency_ghz)
    impedance = validate_positive("reference_impedance_ohm", reference_impedance_ohm)
    return {
        "name": name,
        "kind": kind,
        "inductance_nh": inductance,
        "shunt_capacitance_ff": shunt_ff,
        "series_reactance_ohm": reactance,
        "reactance_ratio": reactance / impedance,
        "phase_error_deg": insertion_phase_error_deg(reactance, impedance),
        "self_resonance_ghz": self_resonant_frequency_ghz(inductance, shunt_ff),
    }


def evaluate_coupling_pair(pair, frequency_ghz, reference_impedance_ohm):
    """Evaluate one declared conductor pair and return its coupling record.

    pair keys: name, length_um, separation_um, facing_height_um,
    relative_permittivity.
    """
    if not isinstance(pair, dict):
        raise ValueError("coupling pair must be a mapping")
    name = pair.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("coupling pair requires a non-empty 'name'")
    capacitance = coupling_capacitance_ff(
        pair.get("length_um"),
        pair.get("separation_um"),
        pair.get("facing_height_um"),
        pair.get("relative_permittivity"),
    )
    reactance = capacitive_reactance_ohm(capacitance, frequency_ghz)
    return {
        "name": name,
        "coupling_capacitance_ff": capacitance,
        "coupling_reactance_ohm": reactance,
        "isolation_db": isolation_db(reactance, reference_impedance_ohm),
    }


def assess_parasitic_effects(spec):
    """Run the full clause 7.2.3 parasitic-effect assessment.

    spec keys: nets (sequence), coupling_pairs (sequence, may be empty),
    max_frequency_ghz, reference_impedance_ohm, max_reactance_ratio,
    max_phase_error_deg, min_isolation_db, resonance_margin_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "nets",
        "max_frequency_ghz",
        "reference_impedance_ohm",
        "max_reactance_ratio",
        "max_phase_error_deg",
        "min_isolation_db",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    nets = spec["nets"]
    if not isinstance(nets, (list, tuple)) or not nets:
        raise ValueError("spec['nets'] must be a non-empty sequence")
    pairs = spec.get("coupling_pairs", [])
    if not isinstance(pairs, (list, tuple)):
        raise ValueError("spec['coupling_pairs'] must be a sequence")
    frequency = validate_positive("max_frequency_ghz", spec["max_frequency_ghz"])
    impedance = validate_positive("reference_impedance_ohm", spec["reference_impedance_ohm"])
    max_ratio = validate_positive("max_reactance_ratio", spec["max_reactance_ratio"])
    max_phase = validate_positive("max_phase_error_deg", spec["max_phase_error_deg"])
    min_isolation = validate_positive("min_isolation_db", spec["min_isolation_db"])
    margin_factor = validate_positive(
        "resonance_margin_factor", spec.get("resonance_margin_factor", 2.0)
    )
    if margin_factor < 1.0:
        raise ValueError(
            "resonance_margin_factor must place the resonance above the band, got %r"
            % (margin_factor,)
        )

    net_records = [evaluate_net(net, frequency, impedance) for net in nets]
    seen = set()
    for record in net_records:
        if record["name"] in seen:
            raise ValueError("duplicate net name '%s'" % record["name"])
        seen.add(record["name"])
    pair_records = [evaluate_coupling_pair(pair, frequency, impedance) for pair in pairs]

    findings = []
    resonance_floor_ghz = margin_factor * frequency

    worst_ratio = max(net_records, key=lambda r: r["reactance_ratio"])
    if worst_ratio["reactance_ratio"] > max_ratio + REACTANCE_TOLERANCE:
        findings.append(
            "net '%s' adds a series reactance of %.3f ohm, %.3f of the %.1f ohm "
            "reference against a budget of %.3f"
            % (
                worst_ratio["name"],
                worst_ratio["series_reactance_ohm"],
                worst_ratio["reactance_ratio"],
                impedance,
                max_ratio,
            )
        )

    worst_phase = max(net_records, key=lambda r: r["phase_error_deg"])
    if worst_phase["phase_error_deg"] > max_phase + REACTANCE_TOLERANCE:
        findings.append(
            "net '%s' contributes %.3f deg of insertion phase error against a "
            "budget of %.3f deg" % (worst_phase["name"], worst_phase["phase_error_deg"], max_phase)
        )

    lowest_resonance = min(net_records, key=lambda r: r["self_resonance_ghz"])
    if lowest_resonance["self_resonance_ghz"] < resonance_floor_ghz - REACTANCE_TOLERANCE:
        findings.append(
            "net '%s' self-resonates at %.3f GHz, below the %.3f GHz floor set by "
            "%.2f times the top operating frequency"
            % (
                lowest_resonance["name"],
                lowest_resonance["self_resonance_ghz"],
                resonance_floor_ghz,
                margin_factor,
            )
        )

    worst_isolation = None
    if pair_records:
        worst_isolation = min(pair_records, key=lambda r: r["isolation_db"])
        if worst_isolation["isolation_db"] < min_isolation - REACTANCE_TOLERANCE:
            findings.append(
                "coupling pair '%s' reaches only %.3f dB of isolation against a "
                "required %.3f dB"
                % (worst_isolation["name"], worst_isolation["isolation_db"], min_isolation)
            )
    else:
        findings.append(
            "no conductor pairs were declared; layout coupling was not assessed and "
            "the isolation budget is unverified"
        )

    return {
        "frequency_ghz": frequency,
        "net_records": net_records,
        "pair_records": pair_records,
        "resonance_floor_ghz": resonance_floor_ghz,
        "dominant_reactance_net": worst_ratio["name"],
        "lowest_resonance_net": lowest_resonance["name"],
        "worst_isolation_pair": worst_isolation["name"] if worst_isolation else None,
        "findings": findings,
        "compliant": not findings,
    }
