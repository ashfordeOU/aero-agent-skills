"""Reconciliation of system cleanliness with propulsion cleanliness.

Anchor: ECSS-Q-ST-70-01C sensitive-hardware provisions where they meet the
propulsion-subsystem cleanliness requirements of ECSS-E-ST-35-06C.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Take each fluid interface one at a time: the smallest flow passage behind
   it, the filter that protects that passage, the particle-size limit the
   system-level cleanliness specification flows down, and the particle-size
   and non-volatile-residue limits the propulsion specification imposes.
2. Derive the requirement that actually governs the interface: the more
   stringent of the two limits, and which document it came from. An interface
   where the propulsion side governs is one whose system-level flow-down has
   to be tightened, not one that can be closed by argument.
3. Size the filter the passage needs from the passage itself and a declared
   safety factor, and check that the installed filter both meets that rating
   and is no coarser than the governing particle limit.
4. Quantify what the governing particle would do if it arrived: the fraction
   of the smallest passage area it blocks, which is what turns a particle-size
   statement into a thrust or flow-rate consequence.
5. Reconcile the non-volatile-residue limits the same way, and roll the
   per-interface results into the single most stringent pair the cleanroom,
   the flushing procedure and the acceptance test have to be built around.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE_UM",
    "NVR_TOLERANCE_MG_M2",
    "PROPULSION_SOURCE",
    "SYSTEM_SOURCE",
    "assess_propulsion_interface",
    "governing_nvr_limit",
    "governing_particle_limit",
    "orifice_blockage_fraction",
    "reconcile_interface",
    "required_filter_rating_um",
    "validate_interface",
]

SYSTEM_SOURCE = "system-cleanliness-specification"
PROPULSION_SOURCE = "propulsion-cleanliness-specification"

# Two limits reaching the same value by different routes can differ by ULPs;
# a tie is resolved to the system source only when it really is a tie.
LIMIT_TOLERANCE_UM = 1e-9
NVR_TOLERANCE_MG_M2 = 1e-9


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value


def governing_particle_limit(system_limit_um, propulsion_limit_um):
    """Return the more stringent particle-size limit and the document it came from."""
    system = _positive(system_limit_um, "system_limit_um")
    propulsion = _positive(propulsion_limit_um, "propulsion_limit_um")
    if propulsion < system - LIMIT_TOLERANCE_UM:
        return {"limit_um": propulsion, "source": PROPULSION_SOURCE}
    return {"limit_um": min(system, propulsion), "source": SYSTEM_SOURCE}


def governing_nvr_limit(system_nvr_mg_m2, propulsion_nvr_mg_m2):
    """Return the more stringent non-volatile-residue limit and its source."""
    system = _positive(system_nvr_mg_m2, "system_nvr_mg_m2")
    propulsion = _positive(propulsion_nvr_mg_m2, "propulsion_nvr_mg_m2")
    if propulsion < system - NVR_TOLERANCE_MG_M2:
        return {"limit_mg_m2": propulsion, "source": PROPULSION_SOURCE}
    return {"limit_mg_m2": min(system, propulsion), "source": SYSTEM_SOURCE}


def required_filter_rating_um(smallest_orifice_um, safety_factor):
    """Return the coarsest filter rating that still protects the passage."""
    orifice = _positive(smallest_orifice_um, "smallest_orifice_um")
    factor = _positive(safety_factor, "safety_factor")
    if factor < 1.0:
        raise ValueError(
            "safety_factor must be at least 1; a filter coarser than the passage "
            "protects nothing, got %r" % (safety_factor,)
        )
    return orifice / factor


def orifice_blockage_fraction(orifice_um, particle_um):
    """Return the fraction of the passage area a single particle occupies."""
    orifice = _positive(orifice_um, "orifice_um")
    particle = _positive(particle_um, "particle_um")
    return min(1.0, (particle / orifice) ** 2)


def validate_interface(interface):
    """Return a normalised fluid-interface record."""
    if not isinstance(interface, dict):
        raise ValueError("each interface must be a mapping")
    required = (
        "name",
        "smallest_orifice_um",
        "installed_filter_rating_um",
        "system_limit_um",
        "propulsion_limit_um",
        "system_nvr_mg_m2",
        "propulsion_nvr_mg_m2",
    )
    for key in required:
        if key not in interface:
            raise ValueError("interface missing required key '%s'" % key)
    return {
        "name": _name(interface["name"], "interface name"),
        "smallest_orifice_um": _positive(
            interface["smallest_orifice_um"], "smallest_orifice_um"
        ),
        "installed_filter_rating_um": _positive(
            interface["installed_filter_rating_um"], "installed_filter_rating_um"
        ),
        "system_limit_um": _positive(interface["system_limit_um"], "system_limit_um"),
        "propulsion_limit_um": _positive(
            interface["propulsion_limit_um"], "propulsion_limit_um"
        ),
        "system_nvr_mg_m2": _positive(
            interface["system_nvr_mg_m2"], "system_nvr_mg_m2"
        ),
        "propulsion_nvr_mg_m2": _positive(
            interface["propulsion_nvr_mg_m2"], "propulsion_nvr_mg_m2"
        ),
        "safety_factor": _positive(
            interface.get("safety_factor", 3.0), "safety_factor"
        ),
        "max_blockage_fraction": _positive(
            interface.get("max_blockage_fraction", 0.1), "max_blockage_fraction"
        ),
    }


def reconcile_interface(interface):
    """Reconcile one fluid interface and return its governing requirements."""
    record = validate_interface(interface)
    if record["safety_factor"] < 1.0:
        raise ValueError("safety_factor must be at least 1")
    if record["max_blockage_fraction"] > 1.0:
        raise ValueError("max_blockage_fraction must not exceed 1")
    particle = governing_particle_limit(
        record["system_limit_um"], record["propulsion_limit_um"]
    )
    nvr = governing_nvr_limit(
        record["system_nvr_mg_m2"], record["propulsion_nvr_mg_m2"]
    )
    required_rating = required_filter_rating_um(
        record["smallest_orifice_um"], record["safety_factor"]
    )
    blockage = orifice_blockage_fraction(
        record["smallest_orifice_um"], particle["limit_um"]
    )
    findings = []
    if particle["source"] == PROPULSION_SOURCE:
        findings.append(
            "%s: the propulsion limit %.3f um is tighter than the flowed-down system "
            "limit %.3f um; the system specification governs nothing here"
            % (record["name"], record["propulsion_limit_um"], record["system_limit_um"])
        )
    if nvr["source"] == PROPULSION_SOURCE:
        findings.append(
            "%s: the propulsion residue limit %.4f mg/m2 is tighter than the system "
            "limit %.4f mg/m2"
            % (
                record["name"],
                record["propulsion_nvr_mg_m2"],
                record["system_nvr_mg_m2"],
            )
        )
    filter_sized = record["installed_filter_rating_um"] < required_rating or math.isclose(
        record["installed_filter_rating_um"],
        required_rating,
        rel_tol=0.0,
        abs_tol=LIMIT_TOLERANCE_UM,
    )
    if not filter_sized:
        findings.append(
            "%s: installed filter rating %.3f um is coarser than the %.3f um the "
            "%.3f um passage needs at a safety factor of %.2f"
            % (
                record["name"],
                record["installed_filter_rating_um"],
                required_rating,
                record["smallest_orifice_um"],
                record["safety_factor"],
            )
        )
    filter_matches_limit = (
        record["installed_filter_rating_um"] < particle["limit_um"]
        or math.isclose(
            record["installed_filter_rating_um"],
            particle["limit_um"],
            rel_tol=0.0,
            abs_tol=LIMIT_TOLERANCE_UM,
        )
    )
    if not filter_matches_limit:
        findings.append(
            "%s: installed filter rating %.3f um passes particles larger than the "
            "governing limit %.3f um"
            % (record["name"], record["installed_filter_rating_um"], particle["limit_um"])
        )
    blockage_ok = blockage < record["max_blockage_fraction"] or math.isclose(
        blockage, record["max_blockage_fraction"], rel_tol=0.0, abs_tol=1e-12
    )
    if not blockage_ok:
        findings.append(
            "%s: a governing-limit particle blocks %.4f of the passage area against "
            "an allowable %.4f"
            % (record["name"], blockage, record["max_blockage_fraction"])
        )
    return {
        "name": record["name"],
        "governing_particle_limit_um": particle["limit_um"],
        "governing_particle_source": particle["source"],
        "governing_nvr_limit_mg_m2": nvr["limit_mg_m2"],
        "governing_nvr_source": nvr["source"],
        "required_filter_rating_um": required_rating,
        "installed_filter_rating_um": record["installed_filter_rating_um"],
        "blockage_fraction": blockage,
        "max_blockage_fraction": record["max_blockage_fraction"],
        "compliant": not findings,
        "findings": findings,
    }


def assess_propulsion_interface(spec):
    """Reconcile every declared fluid interface and roll up the governing pair.

    spec keys: interfaces (non-empty sequence of interface mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "interfaces" not in spec:
        raise ValueError("spec missing required key 'interfaces'")
    interfaces = spec["interfaces"]
    if not isinstance(interfaces, (list, tuple)) or not interfaces:
        raise ValueError("interfaces must be a non-empty sequence")
    results = [reconcile_interface(item) for item in interfaces]
    names = [result["name"] for result in results]
    if len(set(names)) != len(names):
        raise ValueError("interface names must be unique for a traceable roll-up")
    driving_particle = min(results, key=lambda r: r["governing_particle_limit_um"])
    driving_nvr = min(results, key=lambda r: r["governing_nvr_limit_mg_m2"])
    findings = []
    for result in results:
        findings.extend(result["findings"])
    return {
        "interfaces": results,
        "system_particle_limit_um": driving_particle["governing_particle_limit_um"],
        "system_particle_driver": driving_particle["name"],
        "system_nvr_limit_mg_m2": driving_nvr["governing_nvr_limit_mg_m2"],
        "system_nvr_driver": driving_nvr["name"],
        "propulsion_driven_interfaces": [
            result["name"]
            for result in results
            if result["governing_particle_source"] == PROPULSION_SOURCE
            or result["governing_nvr_source"] == PROPULSION_SOURCE
        ],
        "compliant": not findings,
        "findings": findings,
    }
