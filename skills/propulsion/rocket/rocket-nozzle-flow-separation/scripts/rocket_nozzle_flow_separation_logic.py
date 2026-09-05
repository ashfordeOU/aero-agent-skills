"""Rocket nozzle flow separation logic (propulsion/rocket/rocket-nozzle-flow-separation).

Predict wall flow separation in an overexpanded rocket nozzle operating below
its design altitude. SI units throughout (Pa, m, s, kg, N, K).

Model (documented simplifications):
- Summerfield-class separation criterion: the nozzle wall flow separates when
  the local wall static pressure falls to p_sep = K_SEP * pa, with the module
  constant K_SEP = 0.4 (sea-level anchor). Ambient pressure pa in Pa.
- The separation station follows from the isentropic pressure-Mach and
  area-Mach relations at p_sep: M_sep = f(pc / p_sep), then A_sep / At.
- A nozzle whose exit area ratio Ae_At does not exceed A_sep / At keeps the
  flow attached at that ambient pressure.
- separation_altitude is the altitude where the ISA ambient pressure equals
  the design exit pressure pe_design, found by bisection over [0, 20000] m:
  the nozzle un-separates as the ambient pressure falls toward its design
  point. Results are clamped to the search bracket: a pe_design at or above
  the sea-level pressure returns 0.0 m, one at or below the 20 km pressure
  returns 20000.0 m.
- separated_thrust_loss evaluates the thrust with the momentum and the
  pressure term taken at the separation station for the separated case; the
  pressure term beyond the separation station is neglected. The uncorrected
  reference is the design-point thrust m_dot * v_exit at perfect expansion
  (exit pressure matched to ambient), so the loss is measured against the
  rated design point and is non-negative while the flow is separated.
- side_load_flag reports the separated, overexpanded regime (design exit
  pressure below the ambient pressure) where asymmetric separation side
  loads occur.

Pure Python standard library only; deterministic; no network or external
processes. Non-physical inputs raise ValueError.
"""

import math

K_SEP = 0.4
GAMMA_DEFAULT = 1.2
R = 287.0
G0 = 9.80665

# ISA standard-atmosphere module data (reference only): sea level and the
# troposphere lapse base. Below 11000 m the closed-form troposphere relation
# p(h) = 101325 * (1 - 0.0065*h/288.15)**5.2561 is used; above 11000 m the
# isothermal layer keeps the pressure anchored at the tropopause value.
ISA_SEA_LEVEL_PRESSURE = 101325.0
ISA_SEA_LEVEL_TEMPERATURE = 288.15
ISA_TROPOPAUSE_ALTITUDE = 11000.0
ISA_TROPOPAUSE_TEMPERATURE = 216.65
ISA_LAPSE_RATE = 0.0065
ISA_EXPONENT = 5.2561
ISA_TROPOPAUSE_PRESSURE = (
    ISA_SEA_LEVEL_PRESSURE
    * (1.0 - ISA_LAPSE_RATE * ISA_TROPOPAUSE_ALTITUDE / ISA_SEA_LEVEL_TEMPERATURE)
    ** ISA_EXPONENT
)
ISA_PRESSURE_TABLE = (
    (0.0, ISA_SEA_LEVEL_PRESSURE),
    (ISA_TROPOPAUSE_ALTITUDE, ISA_TROPOPAUSE_PRESSURE),
)

_ALTITUDE_MIN = 0.0
_ALTITUDE_MAX = 20000.0
_BISECTION_ITERATIONS = 100


def separation_pressure_ratio(pa, k_sep=K_SEP):
    """Return the separation pressure p_sep = k_sep * pa (Pa).

    Wall flow separation is predicted when the local wall static pressure
    falls to this fraction of the ambient pressure.
    """
    if pa <= 0.0:
        raise ValueError("ambient pressure pa must be positive")
    if k_sep <= 0.0:
        raise ValueError("separation pressure-ratio constant k_sep must be positive")
    return k_sep * pa


def separation_mach(pc, p_sep, gamma):
    """Return the isentropic Mach number at the pressure ratio pc / p_sep.

    M = sqrt(((pc/p_sep)**((gamma-1)/gamma) - 1) * 2/(gamma-1)).
    """
    if pc <= 0.0:
        raise ValueError("chamber pressure pc must be positive")
    if p_sep <= 0.0:
        raise ValueError("separation pressure p_sep must be positive")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must be greater than 1")
    if pc <= p_sep:
        raise ValueError(
            "chamber pressure pc must exceed the separation pressure p_sep "
            "for a real supersonic separation Mach number"
        )
    term = (pc / p_sep) ** ((gamma - 1.0) / gamma)
    return ((term - 1.0) * 2.0 / (gamma - 1.0)) ** 0.5


def area_ratio_from_mach(M, gamma):
    """Return the isentropic area ratio A/A* for a Mach number M.

    (1/M) * ((2/(gamma+1)) * (1 + (gamma-1)/2 * M**2))**((gamma+1)/(2*(gamma-1))).
    At M = 1 the ratio is exactly 1 (the throat).
    """
    if M <= 0.0:
        raise ValueError("Mach number M must be positive")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must be greater than 1")
    exponent = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    core = (2.0 / (gamma + 1.0)) * (1.0 + 0.5 * (gamma - 1.0) * M * M)
    return (1.0 / M) * core ** exponent


def separation_station_area_ratio(pc, pa, gamma):
    """Return the nozzle area ratio A_sep/At at the separation station.

    The separation pressure is K_SEP * pa, the separation Mach number comes
    from the pressure ratio pc / p_sep, and the station area ratio follows
    from the area-Mach relation at that Mach number.
    """
    p_sep = separation_pressure_ratio(pa)
    m_sep = separation_mach(pc, p_sep, gamma)
    return area_ratio_from_mach(m_sep, gamma)


def separated_verdict(Ae_At, A_sep_At):
    """Return True (separated) when Ae_At > A_sep_At, else False (attached).

    A nozzle whose exit area ratio stays at or below the separation station
    area ratio keeps attached flow at that ambient pressure.
    """
    if Ae_At <= 1.0:
        raise ValueError("exit-to-throat area ratio Ae_At must be greater than 1")
    if A_sep_At < 1.0:
        raise ValueError("separation station area ratio cannot fall below 1 (the throat)")
    return Ae_At > A_sep_At


def isa_pressure(h_m):
    """Return the ISA ambient pressure (Pa) at altitude h_m in metres.

    Troposphere closed form below 11000 m and the isothermal layer above,
    anchored at the tropopause pressure computed from the closed form.
    """
    if h_m < 0.0:
        raise ValueError("altitude h_m must be non-negative")
    if h_m <= ISA_TROPOPAUSE_ALTITUDE:
        factor = 1.0 - ISA_LAPSE_RATE * h_m / ISA_SEA_LEVEL_TEMPERATURE
        return ISA_SEA_LEVEL_PRESSURE * factor ** ISA_EXPONENT
    scale_height = R * ISA_TROPOPAUSE_TEMPERATURE / G0
    return ISA_TROPOPAUSE_PRESSURE * math.exp(
        -(h_m - ISA_TROPOPAUSE_ALTITUDE) / scale_height
    )


def separation_altitude(pe_design):
    """Return the altitude (m) where the ISA pressure equals pe_design.

    This is the un-separation altitude for a nozzle designed for pe_design:
    above it the ambient pressure has fallen below the design exit pressure
    and the flow stays attached. Bisection over [0, 20000] m for 100
    iterations, with results clamped to the search bracket.
    """
    if pe_design <= 0.0:
        raise ValueError("design exit pressure pe_design must be positive")
    p_top = isa_pressure(_ALTITUDE_MAX)
    if pe_design >= ISA_SEA_LEVEL_PRESSURE:
        return 0.0
    if pe_design <= p_top:
        return _ALTITUDE_MAX
    low = _ALTITUDE_MIN
    high = _ALTITUDE_MAX
    for _ in range(_BISECTION_ITERATIONS):
        mid = 0.5 * (low + high)
        if isa_pressure(mid) > pe_design:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def _choked_flow_rate(pc, Tc, At, gamma):
    """Return the choked flow rate m_dot (kg/s) through the throat area At."""
    choke = (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
    return At * pc / (Tc ** 0.5) * (gamma / R) ** 0.5 * choke


def _velocity_at_mach(mach, Tc, gamma):
    """Return the isentropic flow velocity (m/s) at a Mach number."""
    static_temperature = Tc / (1.0 + 0.5 * (gamma - 1.0) * mach * mach)
    return mach * (gamma * R * static_temperature) ** 0.5


def _pressure_at_mach(mach, pc, gamma):
    """Return the isentropic static pressure (Pa) at a Mach number."""
    return pc / (1.0 + 0.5 * (gamma - 1.0) * mach * mach) ** (
        gamma / (gamma - 1.0)
    )


def _supersonic_mach_from_area_ratio(Ae_At, gamma):
    """Return the supersonic Mach number for an area ratio (bisection)."""
    if Ae_At <= 1.0:
        raise ValueError("exit-to-throat area ratio Ae_At must be greater than 1")
    low = 1.0
    high = 2.0
    while area_ratio_from_mach(high, gamma) < Ae_At:
        high *= 2.0
    for _ in range(200):
        mid = 0.5 * (low + high)
        if area_ratio_from_mach(mid, gamma) < Ae_At:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def separated_thrust_loss(pc, Tc, At, pa, gamma, Ae_At, k_sep=K_SEP):
    """Return a dict of thrust terms for the separated nozzle case.

    Inputs: chamber pressure pc (Pa), chamber temperature Tc (K), throat
    area At (m^2), ambient pressure pa (Pa), specific heat ratio gamma, and
    exit-to-throat area ratio Ae_At. Returns:
      uncorrected_thrust: design-point reference m_dot * v_exit, the thrust
        at perfect expansion where the exit pressure term vanishes;
      corrected_thrust: momentum and pressure term evaluated at the
        separation station for the separated case, the exit-side pressure
        term beyond the separation station neglected; equals the uncorrected
        thrust when the flow is attached;
      thrust_loss: uncorrected minus corrected thrust, non-negative while
        separated;
      relative_loss: thrust_loss over the uncorrected thrust;
      separated: the separation verdict at this ambient pressure.
    """
    if pc <= 0.0:
        raise ValueError("chamber pressure pc must be positive")
    if Tc <= 0.0:
        raise ValueError("chamber temperature Tc must be positive")
    if At <= 0.0:
        raise ValueError("throat area At must be positive")
    if pa <= 0.0:
        raise ValueError("ambient pressure pa must be positive")
    if gamma <= 1.0:
        raise ValueError("specific heat ratio gamma must be greater than 1")
    if Ae_At <= 1.0:
        raise ValueError("exit-to-throat area ratio Ae_At must be greater than 1")
    if k_sep <= 0.0:
        raise ValueError("separation pressure-ratio constant k_sep must be positive")

    m_dot = _choked_flow_rate(pc, Tc, At, gamma)
    m_exit = _supersonic_mach_from_area_ratio(Ae_At, gamma)
    v_exit = _velocity_at_mach(m_exit, Tc, gamma)
    uncorrected = m_dot * v_exit

    p_sep = separation_pressure_ratio(pa, k_sep)
    m_sep = separation_mach(pc, p_sep, gamma)
    area_sep = area_ratio_from_mach(m_sep, gamma)
    separated = separated_verdict(Ae_At, area_sep)

    if not separated:
        return {
            "uncorrected_thrust": uncorrected,
            "corrected_thrust": uncorrected,
            "thrust_loss": 0.0,
            "relative_loss": 0.0,
            "separated": False,
        }

    v_sep = _velocity_at_mach(m_sep, Tc, gamma)
    area_sep_si = area_sep * At
    corrected = m_dot * v_sep + (p_sep - pa) * area_sep_si
    thrust_loss = uncorrected - corrected
    return {
        "uncorrected_thrust": uncorrected,
        "corrected_thrust": corrected,
        "thrust_loss": thrust_loss,
        "relative_loss": thrust_loss / uncorrected,
        "separated": True,
    }


def side_load_flag(separated, pc, pa, pe_design=None):
    """Return True in the asymmetric side-load regime.

    The side-load regime is the separated, overexpanded state: the flow is
    separated and the nozzle runs below its design point (design exit
    pressure pe_design below the ambient pressure pa). Pass pe_design to
    test the design point explicitly; when pe_design is omitted the nozzle
    is treated as overexpanded whenever separation occurs, because reaching
    the separation criterion p_sep = K_SEP * pa below the ambient pressure
    already requires the nozzle to run overexpanded.
    """
    if not isinstance(separated, bool):
        raise ValueError("separated must be a bool")
    if pc <= 0.0:
        raise ValueError("chamber pressure pc must be positive")
    if pa <= 0.0:
        raise ValueError("ambient pressure pa must be positive")
    if pe_design is not None and pe_design <= 0.0:
        raise ValueError("design exit pressure pe_design must be positive")
    if not separated:
        return False
    overexpanded = True if pe_design is None else pe_design < pa
    return overexpanded
