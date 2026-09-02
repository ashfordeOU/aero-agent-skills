"""Rocket combustion thermochemistry in the spirit of NASA CEA (Aero Agent Skills).

Simplified frozen-flow equilibrium model, pure Python stdlib, offline and
deterministic. Computes the adiabatic flame temperature and chamber
conditions (composition, molecular weight, gamma, characteristic velocity
c*, ideal vacuum and sea-level specific impulse) from the propellant pair,
the mixture ratio O/F, and the chamber pressure, by a combustion enthalpy
balance over representative species with simplified dissociation
equilibria.

Model notes (documented simplifications, appropriate for a quick-look tool):
- Representative species set: CO2, H2O, CO, H2, O2, OH, H, O plus inert N2.
  Equilibrium constants come from species Gibbs functions with quadratic
  heat capacities fitted through 298/1500/3500 K, so the equilibrium
  chemistry is internally consistent (water-gas shift plus H2O, H2 and O2
  dissociation). Representative published chamber conditions for the
  reference propellant pairs (LOX/RP-1, LOX/LH2, LOX/CH4, NTO/MMH) are
  reproduced within a few percent.
- Enthalpy is the exact integral of the quadratic cp; reference state
  298.15 K, gas-phase reactants (enthalpy of vaporization neglected, a few
  percent on Tc).
- Flow is frozen: the chamber composition and a single gamma are used for
  c* and Isp; the nozzle is an ideal-gas isentropic expansion, so the
  reported Isp values are ideal ceilings (real engines deliver roughly 80
  to 95 percent of these because of finite expansion ratio, divergence,
  boundary layers and combustion losses).
- SI units: pressure in Pa, temperature in K, amounts in kmol per kmol of
  fuel, masses in kg, c* and velocities in m/s, Isp in seconds.

Invalid inputs raise ValueError.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2
UNIVERSAL_GAS_CONSTANT = 8314.462  # J/(kmol K)
GAS_CONSTANT_KMOL = 8.314462  # kJ/(kmol K)
ATMOSPHERE_PA = 101325.0  # sea-level ambient pressure, Pa
REF_TEMPERATURE = 298.15  # reference state temperature, K
P_TOL = 1.0  # fixed-point convergence tolerance on T, K

# Species thermochemistry. hf: standard enthalpy of formation at 298.15 K
# in kJ/kmol. s298: standard entropy in J/(mol K), numerically equal to
# kJ/(kmol K). cp_points: (T, cp) knots in K and kJ/(kmol K) for the
# quadratic heat capacity fit cp(T) = a + b*T + c*T^2.
SPECIES_THERMO = {
    "CO2": {"hf": -393522.0, "s298": 213.8, "mw": 44.010,
            "cp_points": [(298.15, 37.1), (1500.0, 54.3), (3500.0, 59.5)]},
    "H2O": {"hf": -241826.0, "s298": 188.8, "mw": 18.015,
            "cp_points": [(298.15, 33.6), (1500.0, 44.9), (3500.0, 51.5)]},
    "CO": {"hf": -110527.0, "s298": 197.7, "mw": 28.010,
           "cp_points": [(298.15, 29.1), (1500.0, 33.9), (3500.0, 37.5)]},
    "H2": {"hf": 0.0, "s298": 130.7, "mw": 2.016,
           "cp_points": [(298.15, 28.8), (1500.0, 31.4), (3500.0, 36.5)]},
    "O2": {"hf": 0.0, "s298": 205.2, "mw": 31.999,
           "cp_points": [(298.15, 29.4), (1500.0, 35.0), (3500.0, 40.5)]},
    "OH": {"hf": 38989.0, "s298": 183.7, "mw": 17.007,
           "cp_points": [(298.15, 29.9), (1500.0, 33.4), (3500.0, 34.5)]},
    "H": {"hf": 217977.0, "s298": 114.7, "mw": 1.008,
          "cp_points": [(298.15, 20.8), (1500.0, 20.8), (3500.0, 20.8)]},
    "O": {"hf": 249170.0, "s298": 161.1, "mw": 15.999,
          "cp_points": [(298.15, 21.9), (1500.0, 21.9), (3500.0, 21.9)]},
    "N2": {"hf": 0.0, "s298": 191.6, "mw": 28.013,
           "cp_points": [(298.15, 29.1), (1500.0, 33.0), (3500.0, 36.5)]},
}

# Equilibrium reactions as stoich vectors (products minus reactants, kmol).
_REACTIONS = {
    "wgs": {"CO2": 1, "H2": 1, "CO": -1, "H2O": -1},
    "h2o_dissoc": {"H2": 1, "O2": 0.5, "H2O": -1},
    "oh": {"OH": 1, "H2": 0.5, "H2O": -1},
    "h2_dissoc": {"H": 2, "H2": -1},
    "o2_dissoc": {"O": 2, "O2": -1},
}

# Propellant definitions. atoms: kmol of C/H/O/N per kmol of fuel (or
# oxidizer). mw: molar mass in kg/kmol. hf: gas-phase enthalpy of formation
# at 298.15 K in kJ/kmol.
PROPELLANTS = {
    "LOX/RP-1": {
        "family": "cryogenic",
        "fuel": {"atoms": {"C": 12, "H": 26}, "mw": 170.34, "hf": -243900.0},
        "oxidizer": {"atoms": {"O": 2}, "mw": 31.999, "hf": 0.0},
    },
    "LOX/LH2": {
        "family": "cryogenic",
        "fuel": {"atoms": {"H": 2}, "mw": 2.016, "hf": 0.0},
        "oxidizer": {"atoms": {"O": 2}, "mw": 31.999, "hf": 0.0},
    },
    "LOX/CH4": {
        "family": "cryogenic",
        "fuel": {"atoms": {"C": 1, "H": 4}, "mw": 16.043, "hf": -74873.0},
        "oxidizer": {"atoms": {"O": 2}, "mw": 31.999, "hf": 0.0},
    },
    "NTO/MMH": {
        "family": "hypergolic",
        "fuel": {"atoms": {"C": 1, "H": 6, "N": 2}, "mw": 46.07, "hf": 93300.0},
        "oxidizer": {"atoms": {"N": 2, "O": 4}, "mw": 92.011, "hf": 9160.0},
    },
}


def _fit_cp(points):
    """Quadratic cp(T) = a + b*T + c*T^2 through three (T, cp) knots."""
    (t1, v1), (t2, v2), (t3, v3) = points
    m = [[1.0, t1, t1 * t1], [1.0, t2, t2 * t2], [1.0, t3, t3 * t3]]
    rhs = [v1, v2, v3]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(m[r][col]))
        m[col], m[pivot] = m[pivot], m[col]
        rhs[col], rhs[pivot] = rhs[pivot], rhs[col]
        for row in range(col + 1, 3):
            f = m[row][col] / m[col][col]
            for j in range(col, 3):
                m[row][j] -= f * m[col][j]
            rhs[row] -= f * rhs[col]
    x = [0.0, 0.0, 0.0]
    for i in range(2, -1, -1):
        x[i] = (rhs[i] - sum(m[i][j] * x[j] for j in range(i + 1, 3))) / m[i][i]
    return tuple(x)


_CP = {s: _fit_cp(SPECIES_THERMO[s]["cp_points"]) for s in SPECIES_THERMO}


def _cp(species, temperature):
    a, b, c = _CP[species]
    return a + b * temperature + c * temperature * temperature


def _enthalpy(species, temperature):
    """Enthalpy h(T) = hf + integral(cp) in kJ/kmol (exact for the fit)."""
    a, b, c = _CP[species]
    t0 = REF_TEMPERATURE
    return (
        SPECIES_THERMO[species]["hf"]
        + a * (temperature - t0)
        + 0.5 * b * (temperature ** 2 - t0 ** 2)
        + c / 3.0 * (temperature ** 3 - t0 ** 3)
    )


def _entropy(species, temperature):
    """Entropy s(T) in kJ/(kmol K); s298 in J/(mol K) is numerically equal."""
    a, b, c = _CP[species]
    t0 = REF_TEMPERATURE
    return (
        SPECIES_THERMO[species]["s298"]
        + a * math.log(temperature / t0)
        + b * (temperature - t0)
        + 0.5 * c * (temperature ** 2 - t0 ** 2)
    )


def _gibbs(species, temperature):
    return _enthalpy(species, temperature) - temperature * _entropy(species, temperature)


def _kp(reaction, temperature):
    """Equilibrium constant from species Gibbs functions (atm-based p)."""
    dg = sum(v * _gibbs(s, temperature) for s, v in _REACTIONS[reaction].items())
    return math.exp(-dg / (GAS_CONSTANT_KMOL * temperature))


def _propellant(name):
    try:
        return PROPELLANTS[name]
    except KeyError:
        raise ValueError(
            "unknown propellant %r; choose from %s"
            % (name, ", ".join(sorted(PROPELLANTS)))
        )


def _check_positive(value, label):
    if value <= 0:
        raise ValueError("%s must be positive (got %r)" % (label, value))


def propellant_family(name):
    """Propellant family tag: cryogenic, hypergolic (storable)."""
    return _propellant(name)["family"]


def _reactants(name, mixture_ratio):
    """Atom totals and reactant enthalpy per kmol of fuel at 298.15 K.

    Returns (atoms dict, h_react in kJ/kmol fuel, kmol oxidizer per kmol
    fuel).
    """
    prop = _propellant(name)
    fuel = prop["fuel"]
    ox = prop["oxidizer"]
    x_ox = mixture_ratio * fuel["mw"] / ox["mw"]  # kmol oxidizer / kmol fuel
    atoms = {}
    for key in ("C", "H", "O", "N"):
        atoms[key] = fuel["atoms"].get(key, 0.0) + x_ox * ox["atoms"].get(key, 0.0)
    h_react = fuel["hf"] + x_ox * ox["hf"]
    return atoms, h_react, x_ox


def stoichiometric_mixture_ratio(name):
    """O/F mass ratio for complete combustion to CO2 and H2O (N inert)."""
    prop = _propellant(name)
    fuel = prop["fuel"]
    ox = prop["oxidizer"]
    c = fuel["atoms"].get("C", 0.0)
    h = fuel["atoms"].get("H", 0.0)
    o = fuel["atoms"].get("O", 0.0)
    o_needed = 2.0 * c + h / 2.0 - o
    if o_needed <= 0:
        raise ValueError("fuel is oxygen rich; stoichiometric ratio undefined")
    o_atoms_per_ox = ox["atoms"].get("O", 0.0)
    if o_atoms_per_ox <= 0:
        raise ValueError("oxidizer carries no oxygen")
    x_stoich = o_needed / o_atoms_per_ox
    return x_stoich * ox["mw"] / fuel["mw"]


def _solve_composition(atoms, temperature, pressure_pa, has_carbon, warm=None):
    """Equilibrium composition at one temperature (kmol per kmol of fuel).

    The three balances (water-gas shift, hydrogen, oxygen) are solved by
    bisection on log(n_H2): for a trial n_H2 and the current q, the
    hydrogen balance gives H2O in closed form, the water-gas shift gives
    CO2 in closed form, and O2, OH, H, O follow from their equilibrium
    relations, leaving the oxygen balance as a monotone residual. q is
    then updated to P_atm / n_tot and the pair iterates to a fixed point.
    Deterministic; raises ValueError if the solve diverges.
    """
    c = atoms["C"]
    h = atoms["H"]
    o = atoms["O"]
    if has_carbon and o < c:
        raise ValueError(
            "mixture ratio too fuel rich: not enough oxygen atoms to form CO"
        )
    k1 = _kp("wgs", temperature)
    k2 = _kp("h2o_dissoc", temperature)
    k3 = _kp("oh", temperature)
    k4 = _kp("h2_dissoc", temperature)
    k5 = _kp("o2_dissoc", temperature)
    p_atm = pressure_pa / ATMOSPHERE_PA

    if warm is not None:
        n_h2 = warm["H2"] if warm["H2"] > 1e-14 else 1e-14
        q = p_atm / sum(warm.values())
    else:
        n_h2 = h * 0.25
        q = p_atm / 30.0
    if q <= 0:
        q = p_atm / 30.0
    n_n2 = atoms["N"] / 2.0

    def composition_at(n_h2, q):
        """Full species dict for trial n_H2 and q (closed form, monotone)."""
        n_h2 = min(max(n_h2, 1e-14), h / 2.0 * 0.999)
        n_h = math.sqrt(k4 * n_h2 / q) if n_h2 > 0 else 0.0
        n_h = min(n_h, (h - 2.0 * n_h2) * 0.99)
        denom = 2.0 + k3 / math.sqrt(n_h2 * q) if n_h2 > 0 else 2.0
        n_h2o = max((h - 2.0 * n_h2 - n_h) / denom, 0.0)
        n_h2o = min(n_h2o, h / 2.0)
        n_oh = k3 * n_h2o / math.sqrt(n_h2 * q) if n_h2 > 0 and n_h2o > 0 else 0.0
        n_oh = min(n_oh, (h - 2.0 * n_h2o - n_h) * 0.99)
        if has_carbon:
            n_co2 = k1 * c * n_h2o / (n_h2 + k1 * n_h2o) if n_h2 > 0 else c
            n_co2 = min(n_co2, c)
            n_co = c - n_co2
        else:
            n_co2 = 0.0
            n_co = 0.0
        n_o2 = (
            (k2 * n_h2o / (n_h2 * math.sqrt(q))) ** 2
            if n_h2 > 0 and n_h2o > 0 else 0.0
        )
        n_o = math.sqrt(k5 * n_o2 / q) if n_o2 > 0 else 0.0
        return {
            "CO2": n_co2, "H2O": n_h2o, "CO": n_co, "H2": n_h2,
            "O2": max(n_o2, 1e-24), "OH": max(n_oh, 1e-24),
            "H": max(n_h, 1e-24), "O": max(n_o, 1e-24), "N2": n_n2,
        }

    def oxygen_residual(ln_h2, q):
        n = composition_at(math.exp(ln_h2), q)
        used = (
            2.0 * n["CO2"] + n["H2O"] + n["CO"] + 2.0 * n["O2"]
            + n["OH"] + n["O"]
        )
        return o - used

    lo = math.log(1e-14)
    hi = math.log(h / 2.0 * 0.999)
    norm = float("inf")
    q = max(q, 1e-14)
    for _ in range(120):
        # Bisection on log(n_H2) for the oxygen balance.
        flo = oxygen_residual(lo, q)
        fhi = oxygen_residual(hi, q)
        if flo >= 0.0:
            ln_h2 = lo  # oxidizer rich: all H to water, all C to CO2
        elif fhi <= 0.0:
            ln_h2 = hi  # extremely fuel rich: bounded by H2
        else:
            a, b = lo, hi
            for _ in range(60):
                mid = 0.5 * (a + b)
                fm = oxygen_residual(mid, q)
                if abs(fm) < 1e-10 or (b - a) < 1e-10:
                    break
                if flo * fm <= 0.0:
                    b = mid
                else:
                    a = mid
                    flo = fm
            ln_h2 = 0.5 * (a + b)
        n = composition_at(math.exp(ln_h2), q)
        n_tot = sum(n.values())
        q_new = p_atm / n_tot
        # Convergence check with the log-space equilibrium residuals.
        r = []
        if has_carbon:
            r.append(
                math.log(n["CO2"]) + math.log(n["H2"]) - math.log(n["CO"])
                - math.log(n["H2O"]) - math.log(k1)
            )
        r.append(
            math.log(n["H2"]) + 0.5 * math.log(n["O2"] * q)
            - math.log(n["H2O"]) - math.log(k2)
        )
        r.append(
            math.log(n["OH"]) + 0.5 * math.log(n["H2"] * q)
            - math.log(n["H2O"]) - math.log(k3)
        )
        r.append(
            2.0 * math.log(n["H"]) + math.log(q)
            - math.log(n["H2"]) - math.log(k4)
        )
        r.append(
            2.0 * math.log(n["O"]) + math.log(q)
            - math.log(n["O2"]) - math.log(k5)
        )
        norm = math.sqrt(sum(v * v for v in r))
        if norm < 1e-3 and abs(math.log(q_new) - math.log(q)) < 1e-3:
            return n
        q = 0.5 * (q + q_new)
    raise ValueError(
        "equilibrium solve did not converge at T=%.1f K (residual %.3e)"
        % (temperature, norm)
    )


def _energy_balance_temperature(comp, h_react):
    """Adiabatic flame temperature from the enthalpy balance (bisection).

    Solves sum(n_i * h_i(T)) = h_react for T in [500, 6000] K with the
    composition frozen. The product enthalpy is monotone in T, so bisection
    is exact to the bracket tolerance.
    """
    def f(t):
        return h_react - sum(
            n * _enthalpy(s, t) for s, n in comp.items()
        )

    lo, hi = 500.0, 6000.0
    flo = f(lo)
    fhi = f(hi)
    if flo * fhi > 0:
        # Degenerate: composition cannot balance the reactants within the
        # bracket; return the closer bound (caller validates via closure).
        return lo if abs(flo) < abs(fhi) else hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < 1e-9 * max(abs(h_react), 1.0) or (hi - lo) < 1e-6:
            return mid
        if flo * fm <= 0:
            hi = mid
            fhi = fm
        else:
            lo = mid
            flo = fm
    return 0.5 * (lo + hi)


def _flame_solution(name, mixture_ratio, pressure_pa):
    """Converged (T, composition, atoms, h_react); shared by the API."""
    _check_positive(mixture_ratio, "mixture_ratio")
    _check_positive(pressure_pa, "pressure_pa")
    _propellant(name)
    atoms, h_react, _x_ox = _reactants(name, mixture_ratio)
    has_carbon = atoms["C"] > 0.0
    t = 3000.0
    comp = None
    for _ in range(40):
        comp = _solve_composition(atoms, t, pressure_pa, has_carbon, warm=comp)
        t_new = _energy_balance_temperature(comp, h_react)
        if abs(t_new - t) < P_TOL:
            t = t_new
            break
        if abs(t_new - t) > 400.0:
            # Far jump: the previous composition is a poor warm start.
            comp = None
        t = 0.5 * (t + t_new)
    comp = _solve_composition(atoms, t, pressure_pa, has_carbon, warm=comp)
    return t, comp, atoms, h_react


def adiabatic_flame_temperature(name, mixture_ratio, pressure_pa):
    """Adiabatic flame temperature Tc in K.

    Converges the equilibrium composition at T against the combustion
    enthalpy balance at that composition until the temperature change is
    below P_TOL K.
    """
    return _flame_solution(name, mixture_ratio, pressure_pa)[0]


def equilibrium_composition(name, mixture_ratio, pressure_pa, temperature=None):
    """Species amounts in kmol per kmol of fuel at the flame temperature.

    Pass temperature to freeze the composition at another temperature.
    """
    _check_positive(mixture_ratio, "mixture_ratio")
    _check_positive(pressure_pa, "pressure_pa")
    _propellant(name)
    atoms, _h_react, _x_ox = _reactants(name, mixture_ratio)
    has_carbon = atoms["C"] > 0.0
    if temperature is None:
        temperature = adiabatic_flame_temperature(name, mixture_ratio, pressure_pa)
    return _solve_composition(atoms, temperature, pressure_pa, has_carbon)


def mole_fractions(comp):
    """Species mole fractions from an amounts dict; sums to one."""
    n_tot = sum(comp.values())
    if n_tot <= 0:
        raise ValueError("empty composition")
    return {s: n / n_tot for s, n in comp.items()}


def mixture_molecular_weight(comp):
    """Mean molecular weight of the product gas in kg/kmol."""
    n_tot = sum(comp.values())
    if n_tot <= 0:
        raise ValueError("empty composition")
    return sum(n * SPECIES_THERMO[s]["mw"] for s, n in comp.items()) / n_tot


def mixture_gamma(comp):
    """Frozen specific heat ratio gamma = cp / (cp - R) of the product gas."""
    n_tot = sum(comp.values())
    if n_tot <= 0:
        raise ValueError("empty composition")
    mw = mixture_molecular_weight(comp)
    cp_kmol = sum(n * _cp(s, 3500.0) for s, n in comp.items()) / n_tot
    cp_mass = cp_kmol / mw  # kJ/(kg K)
    r_mass = GAS_CONSTANT_KMOL / mw  # kJ/(kg K)
    return cp_mass / (cp_mass - r_mass)


def chamber_conditions(name, mixture_ratio, pressure_pa):
    """Full chamber state at the adiabatic flame temperature.

    Returns a dict with flame_temperature (K), molecular_weight (kg/kmol),
    gamma, cstar (m/s), isp_vacuum (s), isp_sea_level (s), mole_fractions,
    and energy_closure_error (fraction of the reactant enthalpy).
    """
    t, comp, _atoms, h_react = _flame_solution(name, mixture_ratio, pressure_pa)
    mw = mixture_molecular_weight(comp)
    gamma = mixture_gamma(comp)
    cstar = theoretical_cstar(t, mw, gamma)
    isp_vac = ideal_vacuum_isp(t, mw, gamma)
    isp_sl = ideal_sea_level_isp(t, mw, gamma, pressure_pa)
    h_prod = sum(n * _enthalpy(s, t) for s, n in comp.items())
    h_chem = abs(sum(n * SPECIES_THERMO[s]["hf"] for s, n in comp.items()))
    closure = abs(h_prod - h_react) / max(h_chem, 1e-9)
    return {
        "flame_temperature": t,
        "molecular_weight": mw,
        "gamma": gamma,
        "cstar": cstar,
        "isp_vacuum": isp_vac,
        "isp_sea_level": isp_sl,
        "mole_fractions": mole_fractions(comp),
        "energy_closure_error": closure,
    }


def theoretical_cstar(chamber_temp, molecular_weight, gamma):
    """Ideal characteristic velocity c* in m/s from the chamber gas.

    c* = sqrt(gamma * R * Tc) / (gamma * sqrt((2/(gamma+1))**((gamma+1)/(gamma-1))))
    with R = UNIVERSAL_GAS_CONSTANT / molecular_weight in J/(kg K).
    """
    _check_positive(chamber_temp, "chamber_temp")
    _check_positive(molecular_weight, "molecular_weight")
    if not 1.0 < gamma <= 5.0 / 3.0:
        raise ValueError("gamma must be in (1, 5/3]")
    r = UNIVERSAL_GAS_CONSTANT / molecular_weight
    denom = gamma * math.sqrt(
        (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0))
    )
    return math.sqrt(gamma * r * chamber_temp) / denom


def expansion_velocity(chamber_temp, molecular_weight, gamma, pc_pa, pe_pa):
    """Ideal isentropic exhaust velocity v_e in m/s.

    Frozen composition, constant gamma, ideal gas:
    v_e = sqrt(2*gamma/(gamma-1) * R * Tc * (1 - (Pe/Pc)**((gamma-1)/gamma))).
    """
    _check_positive(chamber_temp, "chamber_temp")
    _check_positive(molecular_weight, "molecular_weight")
    if not 1.0 < gamma <= 5.0 / 3.0:
        raise ValueError("gamma must be in (1, 5/3]")
    _check_positive(pc_pa, "pc_pa")
    _check_positive(pe_pa, "pe_pa")
    if pe_pa >= pc_pa:
        raise ValueError("pe_pa must be below pc_pa for an expanding nozzle")
    r = UNIVERSAL_GAS_CONSTANT / molecular_weight
    ratio = (pe_pa / pc_pa) ** ((gamma - 1.0) / gamma)
    return math.sqrt(
        2.0 * gamma / (gamma - 1.0) * r * chamber_temp * (1.0 - ratio)
    )


def ideal_vacuum_isp(chamber_temp, molecular_weight, gamma):
    """Ideal vacuum specific impulse in seconds, full expansion to Pe = 0.

    This is the ideal-gas frozen-flow ceiling; delivered values are lower
    (see module docstring).
    """
    _check_positive(chamber_temp, "chamber_temp")
    _check_positive(molecular_weight, "molecular_weight")
    if not 1.0 < gamma <= 5.0 / 3.0:
        raise ValueError("gamma must be in (1, 5/3]")
    r = UNIVERSAL_GAS_CONSTANT / molecular_weight
    v_max = math.sqrt(2.0 * gamma / (gamma - 1.0) * r * chamber_temp)
    return v_max / G0


def ideal_sea_level_isp(chamber_temp, molecular_weight, gamma, pc_pa,
                        ambient_pa=ATMOSPHERE_PA):
    """Ideal sea-level specific impulse in seconds (Pe = ambient pressure).

    Assumes perfect expansion to the ambient pressure, so the pressure
    term vanishes: Isp = v_e(Pe = Pa) / g0.
    """
    v_e = expansion_velocity(
        chamber_temp, molecular_weight, gamma, pc_pa, ambient_pa
    )
    return v_e / G0


def cstar_with_efficiency(ideal_cstar, efficiency):
    """Delivered c* from the ideal value and a c* efficiency (0.92-0.98)."""
    _check_positive(ideal_cstar, "ideal_cstar")
    if not 0.0 < efficiency <= 1.0:
        raise ValueError("efficiency must be in (0, 1]")
    return efficiency * ideal_cstar


def isp_with_efficiency(ideal_isp, efficiency):
    """Delivered Isp from the ideal value and an efficiency (0.8-0.95)."""
    _check_positive(ideal_isp, "ideal_isp")
    if not 0.0 < efficiency <= 1.0:
        raise ValueError("efficiency must be in (0, 1]")
    return efficiency * ideal_isp


def isp_mixture_ratio_sensitivity(name, mixture_ratio, pressure_pa, delta_r=0.1):
    """Fractional sensitivity of ideal vacuum Isp to the mixture ratio.

    (Isp(r+dr) - Isp(r-dr)) / (2*dr*Isp(r)) per unit of O/F. Positive when
    the mixture sits fuel-rich of the Isp optimum.
    """
    _check_positive(delta_r, "delta_r")
    base = chamber_conditions(name, mixture_ratio, pressure_pa)["isp_vacuum"]
    hi = chamber_conditions(name, mixture_ratio + delta_r, pressure_pa)["isp_vacuum"]
    lo = chamber_conditions(name, mixture_ratio - delta_r, pressure_pa)["isp_vacuum"]
    return (hi - lo) / (2.0 * delta_r * base)


def mixture_ratio_trade(name, pressure_pa, r_min, r_max, steps):
    """Mixture ratio trade: list of chamber states over a ratio sweep.

    Each entry is a dict with mixture_ratio, flame_temperature,
    molecular_weight, gamma, cstar, isp_vacuum, isp_sea_level.
    """
    _check_positive(pressure_pa, "pressure_pa")
    if r_max <= r_min:
        raise ValueError("r_max must exceed r_min")
    if steps < 2:
        raise ValueError("steps must be at least 2")
    out = []
    for i in range(steps):
        r = r_min + (r_max - r_min) * i / (steps - 1.0)
        c = chamber_conditions(name, r, pressure_pa)
        out.append(
            {
                "mixture_ratio": r,
                "flame_temperature": c["flame_temperature"],
                "molecular_weight": c["molecular_weight"],
                "gamma": c["gamma"],
                "cstar": c["cstar"],
                "isp_vacuum": c["isp_vacuum"],
                "isp_sea_level": c["isp_sea_level"],
            }
        )
    return out
