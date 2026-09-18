"""Complementary EMC shielding with conductive metal foil.

Anchor: ECSS-Q-ST-20-30C clause 7.8 (complementary ECSS requirements for
applying conductive metal foil as an EMC shield over a harness, and for
terminating it). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Size the foil against the physics it has to work at: the skin depth of the
   foil metal at the lowest frequency the shield is required to work from, and
   the number of skin depths the project demands the thickness carries.
2. Size the application: a helically wrapped tape advances by its width less
   its overlap, so the overlap fraction fixes both the pitch and how many foil
   layers sit over any point of the bundle, and the tape length the run
   consumes follows from the pitch and the bundle circumference.
3. Confirm the foil is applied conductive face inward against the drain wire.
   A foil tape carries a conductive layer on a carrier film, so a tape wrapped
   the wrong way round leaves the drain wire in contact with an insulator and
   the shield with no way out.
4. Grade the termination. Foil is not self-terminating, so it leaves through a
   drain wire, and the reactance of that drain-wire pigtail at the highest
   frequency of concern is what degrades the termination relative to a full
   circumferential one. The degradation is computed in decibels and graded.
5. Roll the whole run up into one verdict with named findings.
"""

import math

__all__ = [
    "VACUUM_PERMEABILITY",
    "THICKNESS_TOLERANCE_MM",
    "DECIBEL_TOLERANCE",
    "DEFAULT_PIGTAIL_INDUCTANCE_NH_PER_MM",
    "skin_depth_mm",
    "foil_thickness_adequate",
    "helical_pitch_mm",
    "layers_over_a_point",
    "tape_length_required_mm",
    "pigtail_inductance_nh",
    "inductive_reactance_ohm",
    "termination_penalty_db",
    "evaluate_foil_application",
    "evaluate_foil_termination",
    "assess_foil_shield",
]

VACUUM_PERMEABILITY = 4.0e-7 * math.pi

# A thickness, a layer count or a decibel figure landing exactly on its bound
# meets it; the equality is a representation question absorbed here.
THICKNESS_TOLERANCE_MM = 1e-12
DECIBEL_TOLERANCE = 1e-9

# The working rule of thumb for a round wire run above a reference plane.
DEFAULT_PIGTAIL_INDUCTANCE_NH_PER_MM = 1.0


def _require_number(value, label, positive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if positive and number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _require_fraction(value, label):
    number = _require_number(value, label, positive=False)
    if number < 0.0 or number >= 1.0:
        raise ValueError("%s must sit in [0, 1), got %r" % (label, value))
    return number


def skin_depth_mm(resistivity_ohm_m, relative_permeability, frequency_hz):
    """Return the skin depth of the foil metal in millimetres at a frequency."""
    resistivity = _require_number(resistivity_ohm_m, "resistivity_ohm_m")
    mu_r = _require_number(relative_permeability, "relative_permeability")
    frequency = _require_number(frequency_hz, "frequency_hz")
    permeability = VACUUM_PERMEABILITY * mu_r
    depth_m = math.sqrt(resistivity / (math.pi * frequency * permeability))
    return depth_m * 1000.0


def foil_thickness_adequate(thickness_mm, depth_mm, required_skin_depths=1.0):
    """Return True when the foil is at least the required number of skin depths thick."""
    thickness = _require_number(thickness_mm, "thickness_mm")
    depth = _require_number(depth_mm, "depth_mm")
    required = _require_number(required_skin_depths, "required_skin_depths")
    return thickness >= required * depth - THICKNESS_TOLERANCE_MM


def helical_pitch_mm(tape_width_mm, overlap_fraction):
    """Return the axial advance per turn of a helically wrapped foil tape."""
    width = _require_number(tape_width_mm, "tape_width_mm")
    overlap = _require_fraction(overlap_fraction, "overlap_fraction")
    return width * (1.0 - overlap)


def layers_over_a_point(tape_width_mm, overlap_fraction):
    """Return how many foil layers sit over any point of the bundle."""
    width = _require_number(tape_width_mm, "tape_width_mm")
    pitch = helical_pitch_mm(width, overlap_fraction)
    return width / pitch


def tape_length_required_mm(bundle_length_mm, bundle_circumference_mm, tape_width_mm,
                            overlap_fraction):
    """Return the tape length a helically wrapped run consumes."""
    length = _require_number(bundle_length_mm, "bundle_length_mm")
    circumference = _require_number(bundle_circumference_mm, "bundle_circumference_mm")
    pitch = helical_pitch_mm(tape_width_mm, overlap_fraction)
    turns = length / pitch
    return turns * math.hypot(circumference, pitch)


def pigtail_inductance_nh(length_mm, inductance_per_mm_nh=DEFAULT_PIGTAIL_INDUCTANCE_NH_PER_MM):
    """Return the inductance of a drain-wire pigtail of a given length."""
    length = _require_number(length_mm, "length_mm", positive=False)
    if length < 0.0:
        raise ValueError("length_mm must not be negative")
    per_mm = _require_number(inductance_per_mm_nh, "inductance_per_mm_nh")
    return length * per_mm


def inductive_reactance_ohm(inductance_nh, frequency_hz):
    """Return the reactance an inductance presents at a frequency."""
    inductance = _require_number(inductance_nh, "inductance_nh", positive=False)
    if inductance < 0.0:
        raise ValueError("inductance_nh must not be negative")
    frequency = _require_number(frequency_hz, "frequency_hz")
    return 2.0 * math.pi * frequency * inductance * 1.0e-9


def termination_penalty_db(pigtail_reactance_ohm, reference_impedance_ohm):
    """Return the decibels a pigtail costs against a full circumferential termination."""
    reactance = _require_number(pigtail_reactance_ohm, "pigtail_reactance_ohm", positive=False)
    if reactance < 0.0:
        raise ValueError("pigtail_reactance_ohm must not be negative")
    reference = _require_number(reference_impedance_ohm, "reference_impedance_ohm")
    return 20.0 * math.log10(1.0 + reactance / reference)


def evaluate_foil_application(spec):
    """Evaluate how a foil tape is applied over a bundle.

    spec keys: tape_width_mm, overlap_fraction, foil_thickness_mm,
    resistivity_ohm_m, relative_permeability, lowest_frequency_hz,
    required_skin_depths, required_layers, conductive_face_inward,
    bundle_length_mm, bundle_circumference_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("application spec must be a mapping")
    for key in ("tape_width_mm", "overlap_fraction", "foil_thickness_mm", "resistivity_ohm_m",
                "relative_permeability", "lowest_frequency_hz", "bundle_length_mm",
                "bundle_circumference_mm"):
        if key not in spec:
            raise ValueError("application spec missing required key '%s'" % key)
    depth = skin_depth_mm(
        spec["resistivity_ohm_m"], spec["relative_permeability"], spec["lowest_frequency_hz"]
    )
    required_depths = spec.get("required_skin_depths", 1.0)
    thickness_ok = foil_thickness_adequate(spec["foil_thickness_mm"], depth, required_depths)
    pitch = helical_pitch_mm(spec["tape_width_mm"], spec["overlap_fraction"])
    layers = layers_over_a_point(spec["tape_width_mm"], spec["overlap_fraction"])
    required_layers = _require_number(spec.get("required_layers", 2.0), "required_layers")
    tape_length = tape_length_required_mm(
        spec["bundle_length_mm"],
        spec["bundle_circumference_mm"],
        spec["tape_width_mm"],
        spec["overlap_fraction"],
    )
    findings = []
    if not thickness_ok:
        findings.append(
            "foil is %.5f mm thick against the %.5f mm that %.2f skin depth(s) at %.0f Hz demand"
            % (float(spec["foil_thickness_mm"]), float(required_depths) * depth,
               float(required_depths), float(spec["lowest_frequency_hz"]))
        )
    if layers < required_layers - THICKNESS_TOLERANCE_MM:
        findings.append(
            "an overlap of %.3f puts %.3f foil layer(s) over a point against the %.3f required"
            % (float(spec["overlap_fraction"]), layers, required_layers)
        )
    if not spec.get("conductive_face_inward", False):
        findings.append(
            "foil tape is applied carrier-side inward; the drain wire lies against an insulator"
        )
    return {
        "skin_depth_mm": depth,
        "thickness_adequate": bool(thickness_ok),
        "pitch_mm": pitch,
        "layers_over_a_point": layers,
        "tape_length_required_mm": tape_length,
        "findings": findings,
        "conforming": not findings,
    }


def evaluate_foil_termination(spec):
    """Evaluate the drain-wire termination of a foil shield.

    spec keys: drain_wire_present, pigtail_length_mm, highest_frequency_hz,
    reference_impedance_ohm, allowed_penalty_db, optional
    inductance_per_mm_nh, drain_continuous_with_foil.
    """
    if not isinstance(spec, dict):
        raise ValueError("termination spec must be a mapping")
    for key in ("pigtail_length_mm", "highest_frequency_hz", "reference_impedance_ohm",
                "allowed_penalty_db"):
        if key not in spec:
            raise ValueError("termination spec missing required key '%s'" % key)
    findings = []
    if not spec.get("drain_wire_present", False):
        findings.append("foil shield has no drain wire; it cannot be terminated as applied")
    if not spec.get("drain_continuous_with_foil", True):
        findings.append("drain wire is not continuous with the foil along the whole run")
    inductance = pigtail_inductance_nh(
        spec["pigtail_length_mm"],
        spec.get("inductance_per_mm_nh", DEFAULT_PIGTAIL_INDUCTANCE_NH_PER_MM),
    )
    reactance = inductive_reactance_ohm(inductance, spec["highest_frequency_hz"])
    penalty = termination_penalty_db(reactance, spec["reference_impedance_ohm"])
    allowed = _require_number(spec["allowed_penalty_db"], "allowed_penalty_db", positive=False)
    if allowed < 0.0:
        raise ValueError("allowed_penalty_db must not be negative")
    if penalty > allowed + DECIBEL_TOLERANCE:
        findings.append(
            "a %.1f mm pigtail costs %.3f dB at %.0f Hz against the %.3f dB allowed"
            % (float(spec["pigtail_length_mm"]), penalty, float(spec["highest_frequency_hz"]),
               allowed)
        )
    return {
        "pigtail_inductance_nh": inductance,
        "pigtail_reactance_ohm": reactance,
        "penalty_db": penalty,
        "allowed_penalty_db": allowed,
        "findings": findings,
        "conforming": not findings,
    }


def assess_foil_shield(spec):
    """Run the whole clause 7.8 conductive-foil assessment on one shielded run.

    spec keys: application (the evaluate_foil_application spec), termination
    (the evaluate_foil_termination spec).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("application", "termination"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    application = evaluate_foil_application(spec["application"])
    termination = evaluate_foil_termination(spec["termination"])
    findings = list(application["findings"]) + list(termination["findings"])
    return {
        "application": application,
        "termination": termination,
        "findings": findings,
        "compliant": not findings,
    }
