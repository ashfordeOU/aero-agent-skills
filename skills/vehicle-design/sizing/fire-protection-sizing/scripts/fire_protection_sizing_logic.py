"""Total-flooding fire protection agent sizing (pure stdlib, deterministic).

Model for skills/vehicle-design/sizing/fire-protection-sizing: fix the
protected zone (Class C cargo compartment or powerplant/APU fire zone),
take the zone free volume and the design agent concentration by volume,
compute the total-flooding agent mass from the agent vapor specific
volume at the discharge temperature with the concentration closure
check, roll up the installed agent from the bottle and shot count, and
set the discharge nozzle count from the zone coverage.

FAR 25.851 cargo class, 25.855 compartment and 25.1191 powerplant zone
context, framing only (standards referenced, not reproduced).

Conventions: free volume in m3, agent concentration in percent by
volume of the compartment, agent mass in kg. The total-flooding
relation: the agent vapor volume at the discharge temperature is W * S
and the concentration closure requires W * S / (V + W * S) = C / 100.

Assumption note: the coverage verdict compares the installed agent mass
(rolled up over bottles and shots) with the required per-shot agent
mass; with one bottle and one shot the two are equal (PASS boundary),
and a below-requirement installation is detected with the standalone
coverage_verdict comparison used by fire_protection_summary.
"""

import math

S_AGENT_DEFAULT = 0.158  # m3/kg, Halon-1301-class agent vapor specific volume at about 20 C
C_CARGO_DEFAULT = 5.0  # percent by volume, Class C cargo design concentration (25.855 context)
C_POWERPLANT_DEFAULT = 6.0  # percent by volume, powerplant fire zone design concentration (25.1191 context)
NOZZLE_M3_PER_NOZZLE = 4.0  # one discharge nozzle per 4 m3 of free volume, design value
MIN_ENGINE_ZONE_NOZZLES = 2  # minimum discharge nozzles for an engine/APU fire zone


def agent_mass(free_volume_m3, concentration_pct, spec_volume_m3_kg=S_AGENT_DEFAULT):
    """Total-flooding agent mass for a protected compartment.

    Solves the concentration closure W * S / (V + W * S) = C / 100 for
    the agent mass W: W = (V / S) * C / (100 - C). Returns a dict with
    the mass in kg, the agent vapor volume W * S in m3, and the achieved
    closure fraction.
    """
    if free_volume_m3 <= 0:
        raise ValueError("free_volume_m3 must be > 0")
    if not (0.0 < concentration_pct < 100.0):
        raise ValueError("concentration_pct must be in (0, 100)")
    if spec_volume_m3_kg <= 0:
        raise ValueError("spec_volume_m3_kg must be > 0")
    mass_kg = (free_volume_m3 / spec_volume_m3_kg) * concentration_pct / (100.0 - concentration_pct)
    vapor_volume_m3 = mass_kg * spec_volume_m3_kg
    closure_fraction = vapor_volume_m3 / (free_volume_m3 + vapor_volume_m3)
    return {"mass_kg": mass_kg, "vapor_volume_m3": vapor_volume_m3, "closure_fraction": closure_fraction}


def concentration_closure(free_volume_m3, mass_kg, spec_volume_m3_kg):
    """Closure fraction achieved by a given agent mass in a free volume.

    Returns mass * S / (V + mass * S), the fraction of the mixture that
    is agent vapor at the discharge temperature.
    """
    if free_volume_m3 <= 0:
        raise ValueError("free_volume_m3 must be > 0")
    if mass_kg < 0:
        raise ValueError("mass_kg must be >= 0")
    if spec_volume_m3_kg <= 0:
        raise ValueError("spec_volume_m3_kg must be > 0")
    vapor_volume_m3 = mass_kg * spec_volume_m3_kg
    return vapor_volume_m3 / (free_volume_m3 + vapor_volume_m3)


def installed_agent(mass_per_shot_kg, n_bottles, shots_per_bottle):
    """Installed agent rollup: per-shot mass times bottles times shots.

    Returns a dict with the installed mass in kg and the echoed per-shot
    mass in kg.
    """
    if mass_per_shot_kg <= 0:
        raise ValueError("mass_per_shot_kg must be > 0")
    if n_bottles < 1:
        raise ValueError("n_bottles must be >= 1")
    if shots_per_bottle < 1:
        raise ValueError("shots_per_bottle must be >= 1")
    installed_kg = mass_per_shot_kg * n_bottles * shots_per_bottle
    return {"installed_kg": installed_kg, "mass_per_shot_kg": mass_per_shot_kg}


def nozzle_count(free_volume_m3, is_powerplant_zone=False):
    """Discharge nozzle count from the zone free volume coverage.

    One nozzle per NOZZLE_M3_PER_NOZZLE m3 of free volume, with a floor
    of MIN_ENGINE_ZONE_NOZZLES nozzles for a powerplant fire zone.
    """
    if free_volume_m3 <= 0:
        raise ValueError("free_volume_m3 must be > 0")
    floor = MIN_ENGINE_ZONE_NOZZLES if is_powerplant_zone else 1
    return max(math.ceil(free_volume_m3 / NOZZLE_M3_PER_NOZZLE), floor)


def coverage_verdict(installed_kg, required_kg):
    """Coverage check: PASS when the installed agent meets the required mass.

    Standalone comparison so an under-configured installation (installed
    below required) is detected before the layout is gated. Returns a
    dict with the PASS/FAIL verdict and the margin in kg.
    """
    if installed_kg < 0:
        raise ValueError("installed_kg must be >= 0")
    if required_kg < 0:
        raise ValueError("required_kg must be >= 0")
    verdict = "PASS" if installed_kg >= required_kg else "FAIL"
    return {"verdict": verdict, "margin_kg": installed_kg - required_kg}


def fire_protection_summary(free_volume_m3, concentration_pct, is_powerplant_zone,
                            spec_volume_m3_kg=S_AGENT_DEFAULT, n_bottles=1,
                            shots_per_bottle=1):
    """One-call fire protection sizing summary for a protected zone.

    Returns the required agent mass per shot, the achieved closure
    fraction, the installed agent mass from the bottle and shot count,
    the discharge nozzle count, and the coverage verdict (PASS when the
    installed mass meets the required mass).
    """
    required = agent_mass(free_volume_m3, concentration_pct, spec_volume_m3_kg)
    installed = installed_agent(required["mass_kg"], n_bottles, shots_per_bottle)
    nozzles = nozzle_count(free_volume_m3, is_powerplant_zone)
    verdict = coverage_verdict(installed["installed_kg"], required["mass_kg"])["verdict"]
    return {
        "required_mass_kg": required["mass_kg"],
        "closure_fraction": required["closure_fraction"],
        "installed_kg": installed["installed_kg"],
        "nozzle_count": nozzles,
        "coverage_verdict": verdict,
    }
