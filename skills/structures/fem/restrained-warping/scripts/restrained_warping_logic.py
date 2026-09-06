"""restrained_warping_logic.py - restrained (non-uniform) torsion of thin-walled open I-sections.

Pure stdlib (math only), deterministic. Solves the non-uniform torsion
equation E*Cw*theta'''' - G*J*theta'' = 0 for a thin-walled open doubly
symmetric I-section whose shear center sits at the centroid and whose web
is the sectorial zero line. The I-section travels as the positional dims
(d, b, t_f, t_w) in that order: d overall depth, b flange breadth, t_f
flange thickness, t_w web thickness. All values are plain SI floats
(metres, newtons, pascals).

Deliverables of the module:
- Section constants: the open-section Saint-Venant torsion constant
  J = (2*b*t_f**3 + h_w*t_w**3)/3 with h_w = d - 2*t_f, the warping
  constant Cw = I_y*h**2/4 with h = d - t_f and I_y = 2*b**3*t_f/12,
  the sectorial coordinate omega_tip = h*b/4 at the flange tip, the
  sectorial modulus Cw/omega_tip and the decay parameter
  k = sqrt(G*J/(E*Cw)) of the non-uniform torsion equation.
- Fixed-end cantilever under a point tip torque: the hyperbolic
  closed-form twist theta(z) = (T/(G*J*k))*(k*z - sinh(k*z) +
  tanh(u)*(cosh(k*z) - 1)) with u = k*L, the twist rate, the bimoment
  B(z) = -E*Cw*theta''(z), the flange-tip warping normal stress
  sigma_w = B*omega_tip/Cw and the torque partition T = T_sv + T_w.
- Fork-supported beam with a point torque at midspan: half-beam
  solution theta(x) = (T/(2*G*J))*(x - sinh(k*x)/(k*cosh(v))) with
  v = k*L/2, mirrored across midspan by symmetry.
- The free Saint-Venant baselines appear only inside the twist ratios
  (fixed_end_response, fork_response); the leaf never returns a free
  torsion result as its deliverable.

Non-physical inputs raise ValueError. Negative torque is allowed (sign
reversal of the loading); zero torque is rejected by the response
functions because the twist ratios are undefined there.
"""

import math

# Section constants of the anchor worked example live in the contract test
# and SKILL.md, not here: this module defines no magic numbers beyond math.


def _require_section(d, b, t_f, t_w):
    """Reject non-physical I-section dimensions (shared ValueError set)."""
    if d <= 0 or b <= 0 or t_f <= 0 or t_w <= 0:
        raise ValueError("section dimensions d, b, t_f, t_w must all be positive")
    if d <= 2 * t_f:
        raise ValueError("overall depth d must exceed the flange pair 2*t_f")


def _require_moduli(e, cw, g, j):
    """Reject non-positive material moduli and section constants."""
    if e <= 0 or cw <= 0 or g <= 0 or j <= 0:
        raise ValueError("moduli E, G and constants Cw, J must all be positive")


def _require_case(torque, length, g, j, e, cw):
    """Shared ValueError set for the span-solution functions."""
    if length <= 0:
        raise ValueError("span length must be positive")
    _require_moduli(e, cw, g, j)


def i_section_saint_venant_j(d, b, t_f, t_w):
    """Open-section Saint-Venant torsion constant J = (2*b*t_f**3 + h_w*t_w**3)/3 in m^4.

    The sum of b_i*t_i**3/3 over the two flanges and the web, with
    h_w = d - 2*t_f the web depth. ValueError: any dim <= 0 or d <= 2*t_f.
    """
    _require_section(d, b, t_f, t_w)
    h_w = d - 2 * t_f
    return (2 * b * t_f ** 3 + h_w * t_w ** 3) / 3.0


def i_section_warping_constant(d, b, t_f, t_w):
    """Warping constant (sectorial second moment) Cw = I_y*h**2/4 in m^6.

    h = d - t_f is the flange mid-line spacing and I_y = 2*b**3*t_f/12 the
    flange-pair second moment about the web plane. The web lies on the
    sectorial zero line so its own t_w**3 minor term contributes nothing;
    Cw equals the direct sectorial integral t_f*h**2*b**3/24 to roundoff.
    ValueError: any dim <= 0 or d <= 2*t_f.
    """
    _require_section(d, b, t_f, t_w)
    h = d - t_f
    i_y = 2.0 * b ** 3 * t_f / 12.0
    return i_y * h ** 2 / 4.0


def i_section_sectorial_max(d, b, t_f):
    """Sectorial coordinate omega_tip = (d - t_f)*b/4 in m^2 at the flange tip.

    rho = h/2 is the lever arm of the flange mid-line about the shear
    center at the centroid, integrated along the half flange of length
    b/2: omega_max = (h/2)*(b/2). ValueError: any dim <= 0 or d <= 2*t_f.
    """
    if d <= 0 or b <= 0 or t_f <= 0:
        raise ValueError("section dimensions d, b, t_f must all be positive")
    if d <= 2 * t_f:
        raise ValueError("overall depth d must exceed the flange pair 2*t_f")
    return (d - t_f) * b / 4.0


def torsion_decay_parameter(e, cw, g, j):
    """Decay parameter k = sqrt(G*J/(E*Cw)) in 1/m of the non-uniform torsion ODE.

    The characteristic length 1/k is the span over which warping restraint
    decays. ValueError: e, cw, g or j <= 0.
    """
    if e <= 0 or cw <= 0 or g <= 0 or j <= 0:
        raise ValueError("moduli E, G and constants Cw, J must all be positive")
    return math.sqrt(g * j / (e * cw))


def warping_stress(bimoment, omega_tip, cw):
    """Flange-tip warping normal stress sigma_w = bimoment*omega_tip/cw in Pa.

    Signed: at the positive-omega tip a negative bimoment gives
    compression. ValueError: omega_tip or cw <= 0.
    """
    if omega_tip <= 0 or cw <= 0:
        raise ValueError("sectorial coordinate omega_tip and warping constant Cw must be positive")
    return bimoment * omega_tip / cw


def fixed_end_twist(z, torque, length, g, j, e, cw):
    """Twist theta(z) in rad of the built-in cantilever under a tip torque.

    Hyperbolic closed form theta(z) = (T/(G*J*k))*(k*z - sinh(k*z) +
    tanh(u)*(cosh(k*z) - 1)) with u = k*L: theta(0) = 0 and theta'(0) = 0
    at the built-in root, theta''(L) = 0 and the tip torque balance
    G*J*theta'(L) - E*Cw*theta'''(L) = T at the free tip. ValueError:
    length <= 0 or any modulus/constant <= 0.
    """
    _require_case(torque, length, g, j, e, cw)
    k = torsion_decay_parameter(e, cw, g, j)
    u = k * length
    kz = k * z
    return (torque / (g * j * k)) * (k * z - math.sinh(kz) + math.tanh(u) * (math.cosh(kz) - 1.0))


def fixed_end_twist_rate(z, torque, length, g, j, e, cw):
    """Twist rate theta'(z) in rad/m of the built-in cantilever.

    theta'(z) = (T/(G*J))*(1 - cosh(k*z) + tanh(u)*sinh(k*z)), zero at the
    built-in root (warping blocked) and largest at the free tip.
    """
    _require_case(torque, length, g, j, e, cw)
    k = torsion_decay_parameter(e, cw, g, j)
    u = k * length
    kz = k * z
    return (torque / (g * j)) * (1.0 - math.cosh(kz) + math.tanh(u) * math.sinh(kz))


def fixed_end_bimoment(z, torque, length, g, j, e, cw):
    """Bimoment B(z) = -E*Cw*theta''(z) in N m^2 of the built-in cantilever.

    Signed; the root bimoment B(0) = -T*tanh(u)/k peaks in magnitude at the
    built-in root and the tip bimoment B(L) vanishes to roundoff because
    the tip warps freely. The bimoment is the flange counter-bending
    couple B = M_f*h.
    """
    _require_case(torque, length, g, j, e, cw)
    k = torsion_decay_parameter(e, cw, g, j)
    u = k * length
    kz = k * z
    return (torque / k) * (math.sinh(kz) - math.tanh(u) * math.cosh(kz))


def fork_twist(z, torque, length, g, j, e, cw):
    """Twist theta(z) in rad of the fork-supported beam under a midspan torque.

    Each fork holds theta = 0 and lets the section warp; the midspan plane
    is a symmetry plane (theta'(L/2) = 0). Half-beam x = min(z, L - z) in
    [0, L/2] with theta(x) = (T/(2*G*J))*(x - sinh(k*x)/(k*cosh(v))) and
    v = k*L/2, mirrored across midspan by symmetry.
    """
    _require_case(torque, length, g, j, e, cw)
    k = torsion_decay_parameter(e, cw, g, j)
    v = k * length / 2.0
    x = min(z, length - z)
    kx = k * x
    return (torque / (2.0 * g * j)) * (x - math.sinh(kx) / (k * math.cosh(v)))


def fork_bimoment(z, torque, length, g, j, e, cw):
    """Bimoment B(z) in N m^2 of the fork-supported beam, symmetric about midspan.

    B(x) = (T/(2*k))*sinh(k*x)/cosh(v) on the half-beam x = min(z, L - z):
    zero at the forks (warping free) and peaking at the collar
    B(L/2) = (T/(2*k))*tanh(v) where the applied torque enters the beam
    entirely as warping torque.
    """
    _require_case(torque, length, g, j, e, cw)
    k = torsion_decay_parameter(e, cw, g, j)
    v = k * length / 2.0
    x = min(z, length - z)
    return (torque / (2.0 * k)) * math.sinh(k * x) / math.cosh(v)


def torque_components(z, torque, length, g, j, e, cw):
    """Saint-Venant and warping torque shares at station z, dict with keys
    'T_sv' and 'T_w' in N m, under the caller's carried-torque convention.

    The partition follows the fixed-end solution: the carried torque is
    the full applied torque T and T_sv(z) = G*J*theta'(z) with
    T_w(z) = T - T_sv(z) equal to -E*Cw*theta'''(z), the z-derivative of
    the bimoment. At the built-in root the full torque is warping torque
    (T_sv = 0, T_w = T); far from the restraint the Saint-Venant share
    dominates and T_sv + T_w = T at every station. For the fork case each
    half-beam carries torque/2 and the per-half components come from the
    fork_response keys saint_venant_torque_fork, warping_torque_fork,
    saint_venant_torque_mid and warping_torque_mid.
    """
    _require_case(torque, length, g, j, e, cw)
    k = torsion_decay_parameter(e, cw, g, j)
    u = k * length
    kz = k * z
    t_sv = torque * (1.0 - math.cosh(kz) + math.tanh(u) * math.sinh(kz))
    return {"T_sv": t_sv, "T_w": torque - t_sv}


def fixed_end_response(torque, length, g, j, e, cw):
    """Full restrained response of the built-in cantilever under a tip torque.

    Dict keys: twist_tip (rad), twist_rate_tip (rad/m), free_twist
    (torque*length/(g*j), baseline only), twist_ratio (twist_tip divided
    by the free twist, equal to 1 - tanh(u)/u), bimoment_root (signed
    N m^2, equal to -T*tanh(u)/k), bimoment_tip (N m^2, zero to
    roundoff), saint_venant_torque_tip = T*(1 - 1/cosh(u)),
    warping_torque_tip = T/cosh(u), saint_venant_torque_root = 0.0 and
    warping_torque_root = T (N m). ValueError: length <= 0, any
    modulus/constant <= 0 or torque == 0 (the twist ratio is undefined).
    """
    if torque == 0:
        raise ValueError("torque must be nonzero for the restrained response twist ratio")
    _require_case(torque, length, g, j, e, cw)
    k = torsion_decay_parameter(e, cw, g, j)
    u = k * length
    free_twist = torque * length / (g * j)
    twist_tip = fixed_end_twist(length, torque, length, g, j, e, cw)
    return {
        "twist_tip": twist_tip,
        "twist_rate_tip": fixed_end_twist_rate(length, torque, length, g, j, e, cw),
        "free_twist": free_twist,
        "twist_ratio": twist_tip / free_twist,
        "bimoment_root": fixed_end_bimoment(0.0, torque, length, g, j, e, cw),
        "bimoment_tip": fixed_end_bimoment(length, torque, length, g, j, e, cw),
        "saint_venant_torque_tip": torque * (1.0 - 1.0 / math.cosh(u)),
        "warping_torque_tip": torque / math.cosh(u),
        "saint_venant_torque_root": 0.0,
        "warping_torque_root": torque,
    }


def fork_response(torque, length, g, j, e, cw):
    """Full restrained response of the fork-supported beam under a midspan torque.

    Dict keys: twist_mid (rad), free_twist (torque*length/(4*g*j),
    baseline only), twist_ratio (twist_mid divided by the free twist,
    equal to 1 - tanh(v)/v), bimoment_mid (N m^2, equal to
    (T/(2*k))*tanh(v)), bimoment_fork (N m^2, zero to roundoff),
    saint_venant_torque_fork = (T/2)*(1 - 1/cosh(v)),
    warping_torque_fork = (T/2)/cosh(v) (per half at the fork face),
    saint_venant_torque_mid = 0.0 and warping_torque_mid = torque/2
    (per half at the collar, N m). ValueError: length <= 0, any
    modulus/constant <= 0 or torque == 0 (the twist ratio is undefined).
    """
    if torque == 0:
        raise ValueError("torque must be nonzero for the restrained response twist ratio")
    _require_case(torque, length, g, j, e, cw)
    k = torsion_decay_parameter(e, cw, g, j)
    v = k * length / 2.0
    free_twist = torque * length / (4.0 * g * j)
    twist_mid = fork_twist(length / 2.0, torque, length, g, j, e, cw)
    return {
        "twist_mid": twist_mid,
        "free_twist": free_twist,
        "twist_ratio": twist_mid / free_twist,
        "bimoment_mid": fork_bimoment(length / 2.0, torque, length, g, j, e, cw),
        "bimoment_fork": fork_bimoment(0.0, torque, length, g, j, e, cw),
        "saint_venant_torque_fork": (torque / 2.0) * (1.0 - 1.0 / math.cosh(v)),
        "warping_torque_fork": (torque / 2.0) / math.cosh(v),
        "saint_venant_torque_mid": 0.0,
        "warping_torque_mid": torque / 2.0,
    }
