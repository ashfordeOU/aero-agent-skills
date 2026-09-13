#!/usr/bin/env python3
"""Array element mutual-coupling assessment (ECSS-E-ST-20C clause 7.2.2.2.3).

Deterministic, offline, stdlib-only engineering logic for the clause
7.2.2.2.3 case: the radiation of one array element reaches its neighbours,
so the impedance and the excitation each radiator actually presents to the
beam-forming-network depend on what every other radiator is doing.

The procedure implemented here is a paraphrase of the clause intent, not a
reproduction of the standard: the clause is cited as the traceability anchor
only.

Pipeline
--------
1. Geometry -> pair spacing and pair orientation plane.
2. Pair spacing -> coupling magnitude in dB and a complex coupling term.
3. Coupling magnitude -> coupling regime (strong/moderate/weak/negligible).
4. Commanded excitations + coupling matrix -> active reflection coefficient
   and active standing-wave-ratio per radiator.
5. Scan-angle sweep -> scan-blindness screening.
6. Commanded vs realized excitations -> aperture-efficiency loss and
   sidelobe-level penalty.
7. All results vs the coupling allocation -> findings and a verdict.
"""

from __future__ import annotations

import cmath
import math

__all__ = [
    "coupling_magnitude_db",
    "coupling_coefficient",
    "pair_geometry",
    "build_coupling_matrix",
    "categorize_coupling_regime",
    "neighbour_count",
    "edge_element_ids",
    "active_reflection_coefficient",
    "active_standing_wave_ratio",
    "scan_excitations",
    "realized_excitations",
    "scan_blindness_screen",
    "aperture_efficiency",
    "aperture_efficiency_loss_db",
    "excitation_error_rms",
    "sidelobe_level_penalty_db",
    "assess_mutual_coupling",
]

# --- model constants -------------------------------------------------------

REFERENCE_SPACING_WAVELENGTHS = 0.5
REFERENCE_COUPLING_DB = -18.0
PLANE_OFFSET_DB = {"e-plane": 3.0, "h-plane": 0.0, "diagonal": -3.0}
MAX_COUPLING_DB = -3.0
COUPLING_FLOOR_DB = -70.0

STRONG_REGIME_DB = -12.0
MODERATE_REGIME_DB = -20.0
WEAK_REGIME_DB = -30.0

DEFAULT_BLINDNESS_GAMMA = 0.70

GEOMETRY_TOL = 1e-9
REL_TOL = 1e-9
ABS_TOL = 1e-12


# --- small helpers ---------------------------------------------------------


def _as_float(value, name):
    """Coerce to a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _as_complex(value, name):
    """Coerce to a finite complex excitation or raise ValueError."""
    if isinstance(value, bool):
        raise ValueError("%s must be a complex excitation, got %r" % (name, value))
    if isinstance(value, complex):
        out = value
    elif isinstance(value, (int, float)):
        out = complex(float(value), 0.0)
    else:
        raise ValueError("%s must be a complex excitation, got %r" % (name, value))
    if not (math.isfinite(out.real) and math.isfinite(out.imag)):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _le(value, limit):
    """True when value <= limit, absorbing float representation error.

    A sum of dB terms that is physically on the allocation can land a few
    ULPs above it; the engineering limit is not widened, only the binary
    representation of an equal value is tolerated.
    """
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


# --- 1/2. geometry and the coupling term -----------------------------------


def coupling_magnitude_db(spacing_wavelengths, plane="h-plane", extra_decay_db=0.0):
    """Coupling magnitude between two radiators, in dB (always negative).

    Anchored on a reference value at half-wavelength spacing, falling with
    20*log10 of the spacing ratio, offset by the pair orientation plane
    (the E-plane pair of an aperture radiator couples more strongly than the
    H-plane pair) and by an optional surface-wave decay term in dB per
    wavelength of excess spacing.
    """
    spacing = _as_float(spacing_wavelengths, "spacing_wavelengths")
    if spacing <= 0.0:
        raise ValueError("spacing_wavelengths must be > 0, got %r" % (spacing_wavelengths,))
    if plane not in PLANE_OFFSET_DB:
        raise ValueError(
            "plane must be one of %s, got %r" % (sorted(PLANE_OFFSET_DB), plane)
        )
    decay = _as_float(extra_decay_db, "extra_decay_db")
    if decay < 0.0:
        raise ValueError("extra_decay_db must be >= 0, got %r" % (extra_decay_db,))
    ratio = spacing / REFERENCE_SPACING_WAVELENGTHS
    value = (
        REFERENCE_COUPLING_DB
        - 20.0 * math.log10(ratio)
        + PLANE_OFFSET_DB[plane]
        - decay * (spacing - REFERENCE_SPACING_WAVELENGTHS)
    )
    return max(min(value, MAX_COUPLING_DB), COUPLING_FLOOR_DB)


def coupling_coefficient(spacing_wavelengths, plane="h-plane", extra_decay_db=0.0):
    """Complex coupling term: magnitude from the dB model, phase from path."""
    db = coupling_magnitude_db(spacing_wavelengths, plane, extra_decay_db)
    spacing = float(spacing_wavelengths)
    magnitude = 10.0 ** (db / 20.0)
    phase = -2.0 * math.pi * spacing
    return cmath.rect(magnitude, phase)


def pair_geometry(element_a, element_b):
    """Return (spacing_wavelengths, plane) for one radiator pair."""
    for element, name in ((element_a, "element_a"), (element_b, "element_b")):
        if not isinstance(element, dict):
            raise ValueError("%s must be a mapping, got %r" % (name, element))
    ax = _as_float(element_a.get("x_wavelengths"), "element_a.x_wavelengths")
    ay = _as_float(element_a.get("y_wavelengths"), "element_a.y_wavelengths")
    bx = _as_float(element_b.get("x_wavelengths"), "element_b.x_wavelengths")
    by = _as_float(element_b.get("y_wavelengths"), "element_b.y_wavelengths")
    dx = abs(ax - bx)
    dy = abs(ay - by)
    spacing = math.hypot(dx, dy)
    if spacing <= GEOMETRY_TOL:
        raise ValueError(
            "radiators %r and %r are coincident; a lattice needs distinct positions"
            % (element_a.get("id"), element_b.get("id"))
        )
    if dy <= GEOMETRY_TOL:
        plane = "e-plane"
    elif dx <= GEOMETRY_TOL:
        plane = "h-plane"
    else:
        plane = "diagonal"
    return spacing, plane


def build_coupling_matrix(elements, extra_decay_db=0.0):
    """Complex coupling matrix keyed by ordered radiator-id pairs."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list of mappings")
    if len(elements) < 2:
        raise ValueError("a mutual-coupling assessment needs at least 2 radiators")
    seen = []
    for element in elements:
        if not isinstance(element, dict):
            raise ValueError("each element must be a mapping, got %r" % (element,))
        ident = element.get("id")
        if not isinstance(ident, str) or not ident:
            raise ValueError("each element needs a non-empty string id, got %r" % (ident,))
        if ident in seen:
            raise ValueError("duplicate radiator id %r in the lattice" % (ident,))
        seen.append(ident)
    matrix = {}
    for element_a in elements:
        for element_b in elements:
            if element_a["id"] == element_b["id"]:
                continue
            spacing, plane = pair_geometry(element_a, element_b)
            matrix[(element_a["id"], element_b["id"])] = coupling_coefficient(
                spacing, plane, extra_decay_db
            )
    return matrix


# --- 3. regime categorisation ----------------------------------------------


def categorize_coupling_regime(coupling_db):
    """Categorize one pair by its coupling magnitude in dB."""
    value = _as_float(coupling_db, "coupling_db")
    if value > 0.0:
        raise ValueError("coupling_db must be <= 0 dB (a passive pair), got %r" % (coupling_db,))
    if value >= STRONG_REGIME_DB:
        return "strong"
    if value >= MODERATE_REGIME_DB:
        return "moderate"
    if value >= WEAK_REGIME_DB:
        return "weak"
    return "negligible"


def neighbour_count(elements, element_id, radius_wavelengths):
    """How many radiators sit within radius of the named radiator."""
    radius = _as_float(radius_wavelengths, "radius_wavelengths")
    if radius <= 0.0:
        raise ValueError("radius_wavelengths must be > 0, got %r" % (radius_wavelengths,))
    target = None
    for element in elements:
        if element.get("id") == element_id:
            target = element
    if target is None:
        raise ValueError("unknown radiator id %r" % (element_id,))
    count = 0
    for element in elements:
        if element["id"] == element_id:
            continue
        spacing, _plane = pair_geometry(target, element)
        if _le(spacing, radius):
            count += 1
    return count


def edge_element_ids(elements, radius_wavelengths):
    """Radiators with fewer in-radius neighbours than the lattice maximum.

    An edge radiator sees an incomplete neighbourhood, so its active
    impedance departs from the embedded-element value of the lattice
    interior; the clause asks for that departure to be carried, not averaged
    away.
    """
    counts = {}
    for element in elements:
        counts[element["id"]] = neighbour_count(elements, element["id"], radius_wavelengths)
    if not counts:
        raise ValueError("elements must not be empty")
    interior = max(counts.values())
    return sorted(ident for ident, count in counts.items() if count < interior)


# --- 4. active impedance ---------------------------------------------------


def active_reflection_coefficient(element_id, excitations, matrix, self_reflection=0.0):
    """Active reflection seen by one radiator with the whole lattice driven."""
    if element_id not in excitations:
        raise ValueError("no excitation on record for radiator %r" % (element_id,))
    own = _as_complex(excitations[element_id], "excitations[%r]" % (element_id,))
    if abs(own) <= ABS_TOL:
        raise ValueError(
            "active reflection is undefined for radiator %r: its excitation is null"
            % (element_id,)
        )
    total = _as_complex(self_reflection, "self_reflection")
    for (target, source), term in matrix.items():
        if target != element_id:
            continue
        if source not in excitations:
            raise ValueError("no excitation on record for radiator %r" % (source,))
        drive = _as_complex(excitations[source], "excitations[%r]" % (source,))
        total += term * drive / own
    return total


def active_standing_wave_ratio(gamma):
    """Standing-wave-ratio from an active reflection coefficient."""
    magnitude = abs(_as_complex(gamma, "gamma"))
    if magnitude >= 1.0 and not math.isclose(magnitude, 1.0, rel_tol=REL_TOL):
        raise ValueError(
            "active reflection magnitude %.6f >= 1: the radiator absorbs no net power"
            % magnitude
        )
    if math.isclose(magnitude, 1.0, rel_tol=REL_TOL):
        raise ValueError("active reflection magnitude is unity: standing-wave-ratio is unbounded")
    return (1.0 + magnitude) / (1.0 - magnitude)


# --- 5. scan screening -----------------------------------------------------


def scan_excitations(elements, amplitudes, scan_theta_deg, scan_phi_deg=0.0):
    """Progressive-phase excitations that steer the beam to (theta, phi)."""
    theta = _as_float(scan_theta_deg, "scan_theta_deg")
    phi = _as_float(scan_phi_deg, "scan_phi_deg")
    if abs(theta) > 90.0:
        raise ValueError("scan_theta_deg must lie within +/-90 deg, got %r" % (scan_theta_deg,))
    theta_rad = math.radians(theta)
    phi_rad = math.radians(phi)
    out = {}
    for element in elements:
        ident = element["id"]
        if ident not in amplitudes:
            raise ValueError("no amplitude on record for radiator %r" % (ident,))
        amplitude = _as_float(amplitudes[ident], "amplitudes[%r]" % (ident,))
        if amplitude < 0.0:
            raise ValueError("amplitude for radiator %r must be >= 0" % (ident,))
        x = _as_float(element.get("x_wavelengths"), "x_wavelengths")
        y = _as_float(element.get("y_wavelengths"), "y_wavelengths")
        phase = -2.0 * math.pi * (
            x * math.sin(theta_rad) * math.cos(phi_rad)
            + y * math.sin(theta_rad) * math.sin(phi_rad)
        )
        out[ident] = cmath.rect(amplitude, phase)
    return out


def realized_excitations(commanded, matrix):
    """Commanded excitations plus the terms coupled in from every neighbour."""
    if not commanded:
        raise ValueError("commanded excitations must not be empty")
    out = {}
    for ident, value in commanded.items():
        total = _as_complex(value, "commanded[%r]" % (ident,))
        for (target, source), term in matrix.items():
            if target != ident:
                continue
            if source not in commanded:
                raise ValueError("no commanded excitation for radiator %r" % (source,))
            total += term * _as_complex(commanded[source], "commanded[%r]" % (source,))
        out[ident] = total
    return out


def scan_blindness_screen(
    elements,
    amplitudes,
    matrix,
    scan_angles_deg,
    self_reflection=0.0,
    blindness_gamma=DEFAULT_BLINDNESS_GAMMA,
):
    """Sweep the scan volume and flag angles where the active match collapses."""
    if not isinstance(scan_angles_deg, (list, tuple)) or not scan_angles_deg:
        raise ValueError("scan_angles_deg must be a non-empty sequence")
    threshold = _as_float(blindness_gamma, "blindness_gamma")
    if not 0.0 < threshold < 1.0:
        raise ValueError("blindness_gamma must lie in (0, 1), got %r" % (blindness_gamma,))
    findings = []
    for angle in scan_angles_deg:
        excitations = scan_excitations(elements, amplitudes, angle)
        worst_id = None
        worst_magnitude = -1.0
        for element in elements:
            gamma = active_reflection_coefficient(
                element["id"], excitations, matrix, self_reflection
            )
            magnitude = abs(gamma)
            if magnitude > worst_magnitude:
                worst_magnitude = magnitude
                worst_id = element["id"]
        findings.append(
            {
                "scan_theta_deg": float(angle),
                "worst_element": worst_id,
                "active_reflection_magnitude": worst_magnitude,
                "blind": not _le(worst_magnitude, threshold),
            }
        )
    return findings


# --- 6. aperture consequences ----------------------------------------------


def aperture_efficiency(excitations):
    """Taper efficiency |sum a|^2 / (N * sum |a|^2) of an excitation set."""
    if not excitations:
        raise ValueError("excitations must not be empty")
    total = 0j
    power = 0.0
    count = 0
    for ident, value in excitations.items():
        term = _as_complex(value, "excitations[%r]" % (ident,))
        total += term
        power += abs(term) ** 2
        count += 1
    if power <= 0.0:
        raise ValueError("excitation set carries no power")
    return abs(total) ** 2 / (count * power)


def aperture_efficiency_loss_db(commanded, realized):
    """Loss in dB from the commanded taper to the coupled, realized taper."""
    eta_commanded = aperture_efficiency(commanded)
    eta_realized = aperture_efficiency(realized)
    if eta_realized <= 0.0:
        raise ValueError("realized excitation set has zero aperture efficiency")
    return 10.0 * math.log10(eta_commanded / eta_realized)


def excitation_error_rms(commanded, realized):
    """RMS excitation departure, normalised by the commanded RMS amplitude."""
    if set(commanded) != set(realized):
        raise ValueError("commanded and realized excitation sets cover different radiators")
    error_power = 0.0
    reference_power = 0.0
    for ident in commanded:
        want = _as_complex(commanded[ident], "commanded[%r]" % (ident,))
        got = _as_complex(realized[ident], "realized[%r]" % (ident,))
        error_power += abs(got - want) ** 2
        reference_power += abs(want) ** 2
    if reference_power <= 0.0:
        raise ValueError("commanded excitation set carries no power")
    return math.sqrt(error_power / reference_power)


def sidelobe_level_penalty_db(rms_error, element_count, design_sidelobe_db):
    """Rise of the first sidelobe caused by a random excitation departure."""
    error = _as_float(rms_error, "rms_error")
    if error < 0.0:
        raise ValueError("rms_error must be >= 0, got %r" % (rms_error,))
    if not isinstance(element_count, int) or isinstance(element_count, bool):
        raise ValueError("element_count must be an int, got %r" % (element_count,))
    if element_count < 2:
        raise ValueError("element_count must be >= 2, got %r" % (element_count,))
    design = _as_float(design_sidelobe_db, "design_sidelobe_db")
    if design >= 0.0:
        raise ValueError("design_sidelobe_db must be < 0 dB relative to the beam peak")
    design_power = 10.0 ** (design / 10.0)
    realized_power = design_power + (error ** 2) / element_count
    return 10.0 * math.log10(realized_power / design_power)


# --- 7. aggregate assessment ------------------------------------------------

_DEFAULT_LIMITS = {
    "max_pair_coupling_db": -15.0,
    "max_active_standing_wave_ratio": 2.0,
    "max_aperture_efficiency_loss_db": 0.5,
    "max_sidelobe_penalty_db": 1.0,
}


def assess_mutual_coupling(config):
    """Full clause 7.2.2.2.3 mutual-coupling assessment of one lattice."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    elements = config.get("elements")
    if not isinstance(elements, (list, tuple)) or len(elements) < 2:
        raise ValueError("config['elements'] must list at least 2 radiators")
    limits = dict(_DEFAULT_LIMITS)
    supplied = config.get("limits", {})
    if not isinstance(supplied, dict):
        raise ValueError("config['limits'] must be a mapping")
    for key in supplied:
        if key not in _DEFAULT_LIMITS:
            raise ValueError("unknown allocation key %r" % (key,))
        limits[key] = _as_float(supplied[key], "limits[%r]" % (key,))

    amplitudes = config.get("amplitudes")
    if amplitudes is None:
        amplitudes = {element["id"]: 1.0 for element in elements}
    self_reflection = _as_complex(config.get("self_reflection", 0.0), "self_reflection")
    if abs(self_reflection) >= 1.0:
        raise ValueError("self_reflection magnitude must be < 1")
    decay = _as_float(config.get("extra_decay_db", 0.0), "extra_decay_db")

    matrix = build_coupling_matrix(elements, decay)
    pair_db = {}
    regimes = {}
    for key, term in matrix.items():
        db = 20.0 * math.log10(abs(term))
        pair_db[key] = db
        regimes[key] = categorize_coupling_regime(db)

    worst_pair = max(pair_db, key=lambda key: pair_db[key])
    worst_pair_db = pair_db[worst_pair]

    commanded = scan_excitations(elements, amplitudes, 0.0)
    realized = realized_excitations(commanded, matrix)

    standing_wave = {}
    for element in elements:
        gamma = active_reflection_coefficient(
            element["id"], commanded, matrix, self_reflection
        )
        standing_wave[element["id"]] = active_standing_wave_ratio(gamma)
    worst_swr_id = max(standing_wave, key=lambda key: standing_wave[key])
    worst_swr = standing_wave[worst_swr_id]

    efficiency_loss = aperture_efficiency_loss_db(commanded, realized)
    rms_error = excitation_error_rms(commanded, realized)
    design_sidelobe_db = _as_float(
        config.get("design_sidelobe_db", -25.0), "design_sidelobe_db"
    )
    sidelobe_penalty = sidelobe_level_penalty_db(
        rms_error, len(elements), design_sidelobe_db
    )

    scan_angles = config.get("scan_angles_deg")
    blindness = []
    if scan_angles:
        blindness = scan_blindness_screen(
            elements,
            amplitudes,
            matrix,
            scan_angles,
            self_reflection,
            _as_float(config.get("blindness_gamma", DEFAULT_BLINDNESS_GAMMA), "blindness_gamma"),
        )

    findings = []
    if not _le(worst_pair_db, limits["max_pair_coupling_db"]):
        findings.append(
            "pair %s-%s couples at %.2f dB, above the %.2f dB allocation"
            % (worst_pair[0], worst_pair[1], worst_pair_db, limits["max_pair_coupling_db"])
        )
    if not _le(worst_swr, limits["max_active_standing_wave_ratio"]):
        findings.append(
            "radiator %s reaches an active standing-wave-ratio of %.3f, above %.3f"
            % (worst_swr_id, worst_swr, limits["max_active_standing_wave_ratio"])
        )
    if not _le(efficiency_loss, limits["max_aperture_efficiency_loss_db"]):
        findings.append(
            "coupling costs %.3f dB of aperture efficiency, above the %.3f dB allocation"
            % (efficiency_loss, limits["max_aperture_efficiency_loss_db"])
        )
    if not _le(sidelobe_penalty, limits["max_sidelobe_penalty_db"]):
        findings.append(
            "sidelobe level rises %.3f dB, above the %.3f dB allocation"
            % (sidelobe_penalty, limits["max_sidelobe_penalty_db"])
        )
    for record in blindness:
        if record["blind"]:
            findings.append(
                "scan angle %.1f deg is blind: radiator %s reflects %.3f"
                % (
                    record["scan_theta_deg"],
                    record["worst_element"],
                    record["active_reflection_magnitude"],
                )
            )

    return {
        "pair_coupling_db": pair_db,
        "pair_regimes": regimes,
        "worst_pair": worst_pair,
        "worst_pair_coupling_db": worst_pair_db,
        "active_standing_wave_ratio": standing_wave,
        "worst_standing_wave_ratio": worst_swr,
        "aperture_efficiency_loss_db": efficiency_loss,
        "excitation_error_rms": rms_error,
        "sidelobe_penalty_db": sidelobe_penalty,
        "edge_elements": edge_element_ids(
            elements, _as_float(config.get("neighbour_radius_wavelengths", 1.0),
                                "neighbour_radius_wavelengths")
        ),
        "scan_blindness": blindness,
        "findings": findings,
        "compliant": not findings,
    }
