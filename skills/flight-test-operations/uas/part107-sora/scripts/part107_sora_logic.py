#!/usr/bin/env python3
"""Part 107 applicability and EASA SORA operational risk assessment logic.

Pure Python 3, stdlib only. Implements, for small UAS (drone) operations:

1. FAA 14 CFR Part 107 applicability checks: weight under 55 lb (25 kg),
   visual line of sight (VLOS), daylight operations, below 400 ft AGL,
   airspace class restrictions (authorization in controlled airspace),
   remote pilot certificate.
2. EASA SORA operational categories (open, specific, certified) from
   kinetic energy and population density.
3. Ground risk class (GRC) from the kinetic energy / population density
   table (JARUS SORA 2.0 intrinsic GRC, simplified).
4. Air risk class (ARC) from airspace type.
5. SORA robustness levels and containment.
6. BVLOS waiver considerations.
7. Operational safety case summary.

All functions validate inputs and raise ValueError on invalid input.
Deterministic and offline; the contract test is scripts/test_part107_sora.py.
"""

import math

# ---------------------------------------------------------------------------
# Constants (14 CFR Part 107, 49 U.S.C. 44809, EASA Reg 2019/947)
# ---------------------------------------------------------------------------

PART107_WEIGHT_LB_LIMIT = 55.0   # 14 CFR 107.3 definition of small UAS
PART107_MASS_KG_LIMIT = 25.0     # 55 lb in kg (Part 107 / open category ceiling)
PART107_ALTITUDE_AGL_LIMIT_FT = 400.0  # 14 CFR 107.51 default ceiling
LB_TO_KG = 0.45359237
DEFAULT_SPEED_MPS = 20.0         # characteristic cruise speed for KE estimate

# Controlled airspace classes that need 14 CFR 107.41 authorization (LAANC
# or waiver). Class G is uncontrolled and needs no authorization.
CONTROLLED_AIRSPACE = frozenset(("a", "b", "c", "d", "e"))
VALID_AIRSPACE = frozenset(("a", "b", "c", "d", "e", "g"))

# Intrinsic GRC table, JARUS SORA 2.0 style (simplified, max GRC 9).
# Rows: kinetic energy bands in joules (upper bound exclusive).
# Columns: population density bands in people per square km (upper bound
# exclusive). Table value = intrinsic ground risk class.
KE_BANDS = [
    (0.0, 7.0),
    (7.0, 34.0),
    (34.0, 108.0),
    (108.0, 700.0),
    (700.0, 2400.0),
    (2400.0, math.inf),
]
DENSITY_BANDS = [
    (0.0, 1.0),
    (1.0, 25.0),
    (25.0, 100.0),
    (100.0, 250.0),
    (250.0, math.inf),
]
GRC_TABLE = [
    #  <1    1-25  25-100  100-250  >250 people/km2
    [1, 1, 1, 1, 1],    # KE < 7 J
    [1, 2, 3, 4, 5],    # KE 7-34 J
    [2, 3, 4, 5, 6],    # KE 34-108 J
    [3, 4, 5, 6, 7],    # KE 108-700 J
    [4, 5, 6, 7, 8],    # KE 700-2400 J
    [5, 6, 7, 8, 9],    # KE > 2400 J
]

# Airspace class to air risk class mapping (simplified SORA):
# Class B (busiest controlled) -> ARC-d, C/D -> ARC-c, E -> ARC-b,
# G (uncontrolled below 400 ft) -> ARC-a, A (unreachable en-route) -> ARC-d.
AIRSPACE_ARC = {"a": "d", "b": "d", "c": "c", "d": "c", "e": "b", "g": "a"}

# Robustness levels: GRC reduction credit (SORA strategic mitigations).
ROBUSTNESS_REDUCTION = {"none": 0, "low": 1, "medium": 2, "high": 3}


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _require_number(value, name, minimum, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    value = float(value)
    if value < minimum:
        raise ValueError("%s must be >= %s, got %s" % (name, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %s, got %s" % (name, maximum, value))
    return value


def _require_bool(value, name):
    if not isinstance(value, bool):
        raise ValueError("%s must be a bool" % name)
    return value


def _normalize_airspace(airspace_class):
    if not isinstance(airspace_class, str):
        raise ValueError("airspace_class must be a string like 'g' or 'class g'")
    s = airspace_class.strip().lower()
    for prefix in ("class ", "class-", "class"):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
            break
    s = s.replace("-", "").replace(" ", "")
    if s not in VALID_AIRSPACE:
        raise ValueError("invalid airspace_class %r" % airspace_class)
    return s


# ---------------------------------------------------------------------------
# Part 107 applicability
# ---------------------------------------------------------------------------

def part107_applicable(weight_lb, vlos=True, daylight=True,
                       altitude_agl_ft=400.0, airspace_class="g",
                       remote_pilot_cert=True, airspace_authorization=False):
    """Check FAA 14 CFR Part 107 applicability for a small UAS operation.

    Arguments:
        weight_lb: takeoff weight in pounds (must be > 0).
        vlos: True if visual line of sight is maintained (107.31).
        daylight: True if operation is in daylight or civil twilight (107.29).
        altitude_agl_ft: planned altitude above ground level (107.51).
        airspace_class: one of a, b, c, d, e, g (accepts 'class g' forms).
        remote_pilot_cert: True if the pilot holds a Part 107 remote pilot
            certificate (107.12, 107.64).
        airspace_authorization: True if 107.41 authorization (LAANC or
            waiver) is held for the operating volume.

    Returns a dict with 'applicable', per-check 'checks', and
    'waivers_required' listing the regulatory waivers needed for failed
    checks. Raises ValueError on invalid input.
    """
    weight = _require_number(weight_lb, "weight_lb", minimum=0.0)
    if weight <= 0.0:
        raise ValueError("weight_lb must be > 0")
    altitude = _require_number(altitude_agl_ft, "altitude_agl_ft", minimum=0.0)
    airspace = _normalize_airspace(airspace_class)
    vlos = _require_bool(vlos, "vlos")
    daylight = _require_bool(daylight, "daylight")
    remote_pilot_cert = _require_bool(remote_pilot_cert, "remote_pilot_cert")
    airspace_authorization = _require_bool(airspace_authorization,
                                           "airspace_authorization")

    checks = {
        "weight": weight <= PART107_WEIGHT_LB_LIMIT,
        "vlos": vlos,
        "daylight": daylight,
        "altitude": altitude <= PART107_ALTITUDE_AGL_LIMIT_FT,
        "airspace": airspace_authorization or airspace not in CONTROLLED_AIRSPACE,
        "remote_pilot_cert": remote_pilot_cert,
    }
    waivers = []
    if not checks["weight"]:
        waivers.append("operation exceeds 55 lb (25 kg) small-UAS limit; "
                       "Part 107 does not apply")
    if not checks["vlos"]:
        waivers.append("waiver of 14 CFR 107.31 (VLOS) or BVLOS rule approval")
    if not checks["daylight"]:
        waivers.append("waiver of 14 CFR 107.29 (daylight operations)")
    if not checks["altitude"]:
        waivers.append("waiver of 14 CFR 107.51 (operating limits, 400 ft AGL)")
    if not checks["airspace"]:
        waivers.append("airspace authorization under 14 CFR 107.41 (LAANC or waiver)")
    if not checks["remote_pilot_cert"]:
        waivers.append("remote pilot certificate per 14 CFR 107.12/107.64")
    return {
        "applicable": all(checks.values()),
        "checks": checks,
        "weight_lb": weight,
        "altitude_agl_ft": altitude,
        "airspace_class": airspace,
        "waivers_required": waivers,
    }


# ---------------------------------------------------------------------------
# Kinetic energy and ground risk class (SORA)
# ---------------------------------------------------------------------------

def kinetic_energy(mass_kg, speed_mps=DEFAULT_SPEED_MPS):
    """Characteristic kinetic energy in joules: 0.5 * m * v^2."""
    mass = _require_number(mass_kg, "mass_kg", minimum=0.0)
    if mass <= 0.0:
        raise ValueError("mass_kg must be > 0")
    speed = _require_number(speed_mps, "speed_mps", minimum=0.0)
    if speed <= 0.0:
        raise ValueError("speed_mps must be > 0")
    return 0.5 * mass * speed * speed


def _band_index(value, bands):
    for i, (lo, hi) in enumerate(bands):
        if lo <= value < hi:
            return i
    return len(bands) - 1


def ground_risk_class(ke_j, population_density):
    """Intrinsic ground risk class (GRC 1-9) from kinetic energy and
    population density (JARUS SORA 2.0 table, simplified).

    ke_j: kinetic energy in joules (>= 0).
    population_density: people per square km (>= 0).
    """
    ke = _require_number(ke_j, "ke_j", minimum=0.0)
    density = _require_number(population_density, "population_density",
                              minimum=0.0)
    row = _band_index(ke, KE_BANDS)
    col = _band_index(density, DENSITY_BANDS)
    return GRC_TABLE[row][col]


# ---------------------------------------------------------------------------
# SORA operational category
# ---------------------------------------------------------------------------

def sora_operational_category(mass_kg, population_density,
                              speed_mps=DEFAULT_SPEED_MPS):
    """Classify the operation under the EASA framework.

    Simplified mapping of SORA outcomes to the EASA operational categories:
    - 'open': intrinsic GRC <= 3 and mass within the 25 kg open ceiling.
    - 'specific': intrinsic GRC 4-6 (needs a SORA and an operational
      authorization or a pre-defined risk assessment).
    - 'certified': mass > 25 kg or intrinsic GRC >= 7 (high-energy
      operation over people; type certification territory).

    Returns a dict with 'category', 'grc', 'ke_j' and inputs. Raises
    ValueError on invalid input.
    """
    mass = _require_number(mass_kg, "mass_kg", minimum=0.0)
    if mass <= 0.0:
        raise ValueError("mass_kg must be > 0")
    density = _require_number(population_density, "population_density",
                              minimum=0.0)
    speed = _require_number(speed_mps, "speed_mps", minimum=0.0)
    if speed <= 0.0:
        raise ValueError("speed_mps must be > 0")
    ke = kinetic_energy(mass, speed)
    grc = ground_risk_class(ke, density)
    if mass > PART107_MASS_KG_LIMIT or grc >= 7:
        category = "certified"
    elif grc <= 3:
        category = "open"
    else:
        category = "specific"
    return {
        "category": category,
        "grc": grc,
        "ke_j": ke,
        "mass_kg": mass,
        "population_density": density,
        "speed_mps": speed,
    }


# ---------------------------------------------------------------------------
# Air risk class
# ---------------------------------------------------------------------------

def arc_from_airspace(airspace_type, altitude_agl_ft=400.0):
    """Air risk class (ARC a-d) from airspace type (simplified SORA).

    Class B -> d, C/D -> c, E -> b, G below 400 ft AGL -> a. Operating
    above 400 ft AGL escalates the ARC by one level (density of manned
    traffic grows with altitude). Returns a dict with 'arc' and
    'rationale'. Raises ValueError on invalid input.
    """
    airspace = _normalize_airspace(airspace_type)
    altitude = _require_number(altitude_agl_ft, "altitude_agl_ft", minimum=0.0)
    arc = AIRSPACE_ARC[airspace]
    if altitude > PART107_ALTITUDE_AGL_LIMIT_FT:
        arc = {"a": "b", "b": "c", "c": "d", "d": "d"}[arc]
        rationale = ("class %s above 400 ft AGL escalates to ARC-%s "
                     "(manned traffic density increases with altitude)"
                     % (airspace, arc))
    else:
        rationale = "class %s at or below 400 ft AGL gives ARC-%s" % (airspace, arc)
    return {
        "arc": arc,
        "airspace_class": airspace,
        "altitude_agl_ft": altitude,
        "rationale": rationale,
    }


# ---------------------------------------------------------------------------
# Robustness levels and containment (SORA)
# ---------------------------------------------------------------------------

def robustness_level(grc, mitigation="none"):
    """Apply SORA robustness to an intrinsic GRC.

    mitigation: 'none', 'low', 'medium' or 'high'. GRC reduction credit:
    none 0, low 1, medium 2, high 3. final_grc is floored at 1. Operational
    containment (geofencing plus contingency procedures) is required
    whenever any mitigation credit is claimed; it is the mechanism that
    makes the reduction credible.

    Returns a dict with 'robustness', 'grc_reduction', 'final_grc' and
    'containment_required'. Raises ValueError on invalid input.
    """
    grc = _require_number(grc, "grc", minimum=1.0, maximum=9.0)
    if not float(grc).is_integer():
        raise ValueError("grc must be an integer in 1-9")
    grc = int(grc)
    if mitigation not in ROBUSTNESS_REDUCTION:
        raise ValueError("mitigation must be one of %s"
                         % sorted(ROBUSTNESS_REDUCTION))
    reduction = ROBUSTNESS_REDUCTION[mitigation]
    final_grc = max(1, grc - reduction)
    return {
        "robustness": mitigation,
        "grc": grc,
        "grc_reduction": reduction,
        "final_grc": final_grc,
        "containment_required": mitigation != "none",
        "rationale": ("robustness %s reduces GRC %d to %d; containment %s"
                      % (mitigation, grc, final_grc,
                         "required" if final_grc < grc else "not credited")),
    }


# ---------------------------------------------------------------------------
# BVLOS waiver considerations
# ---------------------------------------------------------------------------

def bvlos_waiver_considerations(vlos=True):
    """BVLOS waiver considerations under Part 107.

    Returns a dict with 'waiver_required', 'regulatory_basis' and
    'considerations'. When vlos is True no waiver is needed. When False,
    a 14 CFR 107.31 waiver or FAA BVLOS rule approval is required and the
    considerations list enumerates the mitigations an applicant must show.
    """
    if not isinstance(vlos, bool):
        raise ValueError("vlos must be a bool")
    if vlos:
        return {
            "waiver_required": False,
            "regulatory_basis": "VLOS maintained; 14 CFR 107.31 satisfied",
            "considerations": [],
        }
    return {
        "waiver_required": True,
        "regulatory_basis": ("14 CFR 107.31 waiver or FAA BVLOS rule "
                             "approval; verify current FAA guidance"),
        "considerations": [
            "observer or approved detect-and-avoid capability",
            "remote ID compliance (14 CFR 89)",
            "airspace authorization for the whole BVLOS volume",
            "lost link and contingency procedures",
            "weather and visibility minima for the route",
            "payload and airframe reliability evidence",
            "crew training for BVLOS operations",
        ],
    }


# ---------------------------------------------------------------------------
# Operational safety case summary
# ---------------------------------------------------------------------------

def ops_summary(weight_lb, population_density, airspace_class="g",
                vlos=True, daylight=True, altitude_agl_ft=400.0,
                remote_pilot_cert=True, airspace_authorization=False,
                speed_mps=DEFAULT_SPEED_MPS, mitigation="none",
                bvlos=False, mass_kg=None):
    """Produce the operational safety case summary for a UAS operation.

    Combines the Part 107 applicability check, SORA category, GRC, ARC,
    robustness and BVLOS considerations into one dict with a human
    readable 'summary' block. mass_kg defaults to weight_lb converted;
    pass mass_kg explicitly when the actual MTOM differs from the
    weight_lb conversion (e.g. payload added). Raises ValueError on
    invalid input.
    """
    weight = _require_number(weight_lb, "weight_lb", minimum=0.0)
    if weight <= 0.0:
        raise ValueError("weight_lb must be > 0")
    if mass_kg is None:
        mass_kg = weight * LB_TO_KG
    mass = _require_number(mass_kg, "mass_kg", minimum=0.0)
    if mass <= 0.0:
        raise ValueError("mass_kg must be > 0")
    density = _require_number(population_density, "population_density",
                              minimum=0.0)

    p107 = part107_applicable(
        weight_lb=weight, vlos=vlos, daylight=daylight,
        altitude_agl_ft=altitude_agl_ft, airspace_class=airspace_class,
        remote_pilot_cert=remote_pilot_cert,
        airspace_authorization=airspace_authorization)
    sora = sora_operational_category(mass, density, speed_mps)
    arc = arc_from_airspace(airspace_class, altitude_agl_ft)
    rob = robustness_level(sora["grc"], mitigation)
    bv = bvlos_waiver_considerations(vlos=(vlos and not bvlos))

    lines = [
        "OPERATIONAL SAFETY CASE SUMMARY",
        "Part 107: %s (weight %.1f lb, %s)"
        % ("APPLICABLE" if p107["applicable"] else "NOT APPLICABLE",
           weight, p107["waivers_required"] or "no waivers"),
        "SORA category: %s | intrinsic GRC %d (KE %.0f J) | ARC-%s (%s)"
        % (sora["category"].upper(), sora["grc"], sora["ke_j"],
           arc["arc"], arc["airspace_class"]),
        "Robustness %s: final GRC %d, containment %s"
        % (rob["robustness"], rob["final_grc"],
           "REQUIRED" if rob["containment_required"] else "not required"),
        "BVLOS: %s" % ("waiver required" if bv["waiver_required"] else "VLOS"),
    ]
    return {
        "part107": p107,
        "sora_category": sora["category"],
        "grc": sora["grc"],
        "ke_j": sora["ke_j"],
        "arc": arc["arc"],
        "airspace_class": arc["airspace_class"],
        "robustness": rob,
        "bvlos": bv,
        "summary": "\n".join(lines),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        res = ops_summary(weight_lb=4.4, population_density=0.5)
        print(res["summary"])
    else:
        print("part107_sora_logic: run scripts/test_part107_sora.py")
