#!/usr/bin/env python3
"""Engine-airframe integration logic: installed thrust bookkeeping.

First-order, common propulsion engineering knowledge (documented
model, no copyrighted text). Units (one convention throughout,
asserted here):

- mass flow mdot in kg/s
- velocity V in m/s
- thrust and drag in N (newtons)
- area A in m^2, density rho in kg/m^3
- pressure in Pa, power in W

Bookkeeping convention (installed thrust):

  Fg        = mdot_e*Vj + (Pe - P0)*Ae      uninstalled gross thrust
  D_ram     = mdot_0*V0                     intake momentum (ram) drag
  F_uninst  = Fg - D_ram                    uninstalled net thrust
  D_nac     = 0.5*rho*V0^2*Cd_nac*A_nac     nacelle external drag
  D_pyl     = 0.5*rho*V0^2*Cd_pyl*A_pyl     pylon drag
  dF_b      = mdot_b*(Vj - V0)              bleed air thrust loss
  dF_a      = P_ext/V0                      accessory power thrust loss
  F_inst    = F_uninst - D_nac - D_pyl - dF_b - dF_a
  loss_frac = 1 - F_inst/F_uninst           installation loss fraction
  F_axial   = F_inst*cos(theta)             misalignment trim

The ram drag is already netted inside F_uninst (F = mdot*(Vj - V0)
form); it is never subtracted a second time. The turbofan-cycle,
bypass-ratio-trade, and nozzle-design leaves produce the uninstalled
cycle terms; the ramjet-inlet and rocket-staging leaves have their
own conventions (a ramjet recovers ram pressure as compression, a
rocket has no captured air and therefore no ram drag).

FAR-33 (engine certification) and FAR-25 (airframe certification) are
referenced, not reproduced; this model is common propulsion
methodology summarized per standards-map.yaml.
"""


def _check_positive(name, value):
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def _check_nonnegative(name, value):
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))


def gross_thrust(mdot_e, Vj, Pe=0.0, P0=0.0, Ae=0.0):
    """Uninstalled gross thrust Fg = mdot_e*Vj + (Pe - P0)*Ae (N).

    mdot_e is the exhaust mass flow (captured air plus fuel), Vj the
    jet velocity. The pressure term (Pe - P0)*Ae adds thrust when the
    nozzle exit pressure exceeds ambient (underexpanded) and subtracts
    when overexpanded.
    """
    _check_positive("mdot_e", mdot_e)
    _check_positive("Vj", Vj)
    _check_nonnegative("Ae", Ae)
    return mdot_e * Vj + (Pe - P0) * Ae


def intake_momentum_drag(mdot_0, V0):
    """Intake momentum (ram) drag D_ram = mdot_0*V0 (N).

    The momentum of the captured stream that the engine must supply:
    linear in the captured air flow and in the flight velocity.
    """
    _check_positive("mdot_0", mdot_0)
    _check_positive("V0", V0)
    return mdot_0 * V0


def uninstalled_net_thrust(Fg, D_ram):
    """Uninstalled net thrust F_uninst = Fg - D_ram (N).

    The cycle result: gross thrust minus the intake momentum drag.
    A working installation must produce positive net thrust.
    """
    _check_nonnegative("Fg", Fg)
    _check_nonnegative("D_ram", D_ram)
    if Fg <= D_ram:
        raise ValueError(
            "Fg must exceed D_ram for positive net thrust, got Fg=%r D_ram=%r"
            % (Fg, D_ram)
        )
    return Fg - D_ram


def _external_drag(rho, V0, Cd, A, name):
    _check_positive("rho", rho)
    _check_positive("V0", V0)
    _check_nonnegative("Cd", Cd)
    _check_positive("A", A)
    return 0.5 * rho * V0 * V0 * Cd * A


def nacelle_drag(rho, V0, Cd_nac, A_nac):
    """Nacelle external drag D = 0.5*rho*V0^2*Cd_nac*A_nac (N).

    Skin friction and pressure drag on the cowl, boat-tail, and
    cooling flow exits; scales with the dynamic pressure and the
    reference area, so doubling V0 quadruples the term.
    """
    return _external_drag(rho, V0, Cd_nac, A_nac, "nacelle")


def pylon_drag(rho, V0, Cd_pyl, A_pyl):
    """Pylon drag D = 0.5*rho*V0^2*Cd_pyl*A_pyl (N).

    The strut carrying the nacelle off the wing or fuselage, sized on
    its frontal area; same quadratic form as the nacelle term.
    """
    return _external_drag(rho, V0, Cd_pyl, A_pyl, "pylon")


def bleed_thrust_loss(mdot_b, Vj, V0):
    """Bleed air thrust loss dF_b = mdot_b*(Vj - V0) (N).

    Bleed taken from the compressor for anti-ice, pressurization, or
    cooling removes its specific-thrust contribution (Vj - V0) from
    the propulsive stream, so the loss is linear in the bleed flow.
    """
    _check_nonnegative("mdot_b", mdot_b)
    _check_positive("Vj", Vj)
    _check_positive("V0", V0)
    if Vj <= V0:
        raise ValueError(
            "Vj must be > V0 for a thrusting stream, got Vj=%r V0=%r" % (Vj, V0)
        )
    return mdot_b * (Vj - V0)


def accessory_thrust_loss(P_extract, V0):
    """Accessory power thrust loss dF_a = P_extract/V0 (N).

    Shaft power drawn by generators and gearboxes costs propulsive
    power; at flight speed V0 the rate of doing work is F*V0, so a
    power off-take P_extract maps to a thrust loss linear in the
    power and inverse in the flight speed.
    """
    _check_nonnegative("P_extract", P_extract)
    _check_positive("V0", V0)
    return P_extract / V0


def axial_thrust(F, theta_deg):
    """Axial component F_axial = F*cos(theta) (N).

    Thrust vector misalignment theta (degrees, 0 <= theta < 90) trims
    the thrust available along the flight path; the cross component
    is an additional small trim or steering item.
    """
    _check_nonnegative("F", F)
    if theta_deg < 0.0 or theta_deg >= 90.0:
        raise ValueError(
            "theta_deg must be in [0, 90), got %r" % (theta_deg,)
        )
    import math

    return F * math.cos(math.radians(theta_deg))


def installed_thrust(F_uninst, D_nac, D_pyl, dF_b, dF_a):
    """Installed thrust F_inst = F_uninst - D_nac - D_pyl - dF_b - dF_a (N).

    The full installation loss ledger on top of the uninstalled net
    thrust. The result must stay positive for a viable installation.
    """
    _check_positive("F_uninst", F_uninst)
    for name, v in (("D_nac", D_nac), ("D_pyl", D_pyl), ("dF_b", dF_b), ("dF_a", dF_a)):
        _check_nonnegative(name, v)
    losses = D_nac + D_pyl + dF_b + dF_a
    if F_uninst <= losses:
        raise ValueError(
            "installation losses must stay below F_uninst, got F_uninst=%r losses=%r"
            % (F_uninst, losses)
        )
    return F_uninst - losses


def thrust_drag_summary(
    mdot_0,
    mdot_e,
    Vj,
    V0,
    Pe,
    P0,
    Ae,
    rho,
    Cd_nac,
    A_nac,
    Cd_pyl,
    A_pyl,
    mdot_b,
    P_extract,
    theta_deg=0.0,
):
    """Bundled installed thrust ledger (dict).

    Computes every term of the thrust-drag bookkeeping for one flight
    point and returns Fg, D_ram, F_uninst, D_nac, D_pyl, dF_b, dF_a,
    F_inst, the installation loss fraction, and the axial installed
    thrust after the misalignment trim.
    """
    Fg = gross_thrust(mdot_e, Vj, Pe, P0, Ae)
    D_ram = intake_momentum_drag(mdot_0, V0)
    F_uninst = uninstalled_net_thrust(Fg, D_ram)
    D_nac = nacelle_drag(rho, V0, Cd_nac, A_nac)
    D_pyl = pylon_drag(rho, V0, Cd_pyl, A_pyl)
    dF_b = bleed_thrust_loss(mdot_b, Vj, V0)
    dF_a = accessory_thrust_loss(P_extract, V0)
    F_inst = installed_thrust(F_uninst, D_nac, D_pyl, dF_b, dF_a)
    return {
        "Fg": Fg,
        "D_ram": D_ram,
        "F_uninst": F_uninst,
        "D_nac": D_nac,
        "D_pyl": D_pyl,
        "dF_b": dF_b,
        "dF_a": dF_a,
        "F_inst": F_inst,
        "loss_fraction": 1.0 - F_inst / F_uninst,
        "F_axial": axial_thrust(F_inst, theta_deg),
    }


def demonstrate():
    """Worked anchor case: prints and returns the installed thrust ledger.

    mdot_0 = 100 kg/s, mdot_e = 102 kg/s, Vj = 600 m/s, V0 = 250 m/s,
    fully expanded nozzle (Pe = P0), rho = 0.36 kg/m^3,
    Cd_nac = 0.35, A_nac = 1.2 m^2, Cd_pyl = 0.30, A_pyl = 0.5 m^2,
    bleed 1.5 kg/s, accessory 500 kW, 2 deg misalignment.
    """
    s = thrust_drag_summary(
        mdot_0=100.0,
        mdot_e=102.0,
        Vj=600.0,
        V0=250.0,
        Pe=101325.0,
        P0=101325.0,
        Ae=0.4,
        rho=0.36,
        Cd_nac=0.35,
        A_nac=1.2,
        Cd_pyl=0.30,
        A_pyl=0.5,
        mdot_b=1.5,
        P_extract=500000.0,
        theta_deg=2.0,
    )
    print("engine-airframe integration, worked anchor (fully expanded nozzle):")
    print("  gross thrust Fg           = %8.1f N" % s["Fg"])
    print("  ram drag D_ram            = %8.1f N" % s["D_ram"])
    print("  uninstalled net F_uninst  = %8.1f N" % s["F_uninst"])
    print("  nacelle drag D_nac        = %8.1f N" % s["D_nac"])
    print("  pylon drag D_pyl          = %8.1f N" % s["D_pyl"])
    print("  bleed loss dF_b           = %8.1f N" % s["dF_b"])
    print("  accessory loss dF_a       = %8.1f N" % s["dF_a"])
    print("  installed thrust F_inst   = %8.1f N" % s["F_inst"])
    print("  loss fraction             = %7.3f" % s["loss_fraction"])
    print("  axial installed thrust    = %8.1f N" % s["F_axial"])
    return s


if __name__ == "__main__":
    demonstrate()
