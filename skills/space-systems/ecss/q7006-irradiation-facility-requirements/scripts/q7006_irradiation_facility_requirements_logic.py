"""Irradiation facility requirements for a space-material degradation test.

Anchor: ECSS-Q-ST-70-06C, facility clause -- deciding which irradiation source
a campaign is run at, and whether the ultraviolet and particle exposures are
delivered together or one after the other. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate a candidate facility: the agents it produces, the energy window it
   covers, the flux and ultraviolet intensity it reaches, the uniformity of
   its target plane and the chamber conditions it maintains.
2. Grade the candidate against the campaign requirement: agent coverage,
   energy-window coverage, uniformity limit, chamber pressure and the
   specimen temperature window.
3. Compute the acceleration factor the candidate would be run at -- test flux
   over mission flux -- and refuse an acceleration beyond the limit at which
   the degradation mechanism is no longer the mission mechanism.
4. Decide the exposure mode: combined when the campaign expects the two
   agents to interact and the facility can deliver them together, otherwise a
   named sequential order, with the loss of synergy recorded as a finding.
5. Rank the admissible candidates by acceleration factor, lowest first, and
   break a tie on the facility name so the choice is reproducible.
"""

import math

__all__ = [
    "MAX_ACCELERATION_FACTOR",
    "MAX_UNIFORMITY_PCT",
    "SEQUENTIAL_ORDERS",
    "AGENTS",
    "validate_facility",
    "acceleration_factor",
    "exposure_hours",
    "uniformity_pct",
    "energy_coverage_findings",
    "exposure_mode",
    "grade_facility",
    "rank_facilities",
    "select_irradiation_facility",
]

# Beyond this ratio of test flux to mission flux, dose-rate effects displace
# the mission degradation mechanism and the result stops being representative.
MAX_ACCELERATION_FACTOR = 1000.0

# Flux variation across the coupon plane, expressed as a plus-or-minus
# percentage of the mean, above which the coupons are not comparably exposed.
MAX_UNIFORMITY_PCT = 10.0

AGENTS = ("particles", "ultraviolet")

SEQUENTIAL_ORDERS = ("particles-then-ultraviolet", "ultraviolet-then-particles")

# Comparisons against a limit absorb representation error here rather than by
# relaxing the limit itself.
_TOLERANCE = 1e-9


def _real(value, label, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_facility(facility):
    """Return a normalised record for one candidate irradiation facility."""
    if not isinstance(facility, dict):
        raise ValueError("facility must be a mapping")
    for key in ("name", "agents", "energy_min_mev", "energy_max_mev",
                "max_particle_flux", "max_uv_suns", "uniformity_pct",
                "base_pressure_pa", "temperature_window_c", "combined_capable"):
        if key not in facility:
            raise ValueError("facility missing required key '%s'" % key)
    name = facility["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("facility name must be a non-empty string")
    agents = facility["agents"]
    if not isinstance(agents, (list, tuple)) or not agents:
        raise ValueError("facility '%s': agents must be a non-empty sequence" % name)
    for agent in agents:
        if agent not in AGENTS:
            raise ValueError("facility '%s': unknown agent %r" % (name, agent))
    if not isinstance(facility["combined_capable"], bool):
        raise ValueError("facility '%s': combined_capable must be a boolean" % name)
    window = facility["temperature_window_c"]
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("facility '%s': temperature_window_c must be a pair" % name)
    low = float(window[0])
    high = float(window[1])
    if not math.isfinite(low) or not math.isfinite(high) or low > high:
        raise ValueError("facility '%s': temperature window is inverted" % name)
    e_min = _real(facility["energy_min_mev"], "energy_min_mev")
    e_max = _real(facility["energy_max_mev"], "energy_max_mev")
    if e_min > e_max:
        raise ValueError("facility '%s': energy window is inverted" % name)
    record = {
        "name": name.strip(),
        "agents": tuple(sorted(set(agents))),
        "energy_min_mev": e_min,
        "energy_max_mev": e_max,
        "max_particle_flux": _real(facility["max_particle_flux"], "max_particle_flux", True),
        "max_uv_suns": _real(facility["max_uv_suns"], "max_uv_suns", True),
        "uniformity_pct": _real(facility["uniformity_pct"], "uniformity_pct", True),
        "base_pressure_pa": _real(facility["base_pressure_pa"], "base_pressure_pa"),
        "temperature_window_c": (low, high),
        "combined_capable": facility["combined_capable"],
    }
    if record["combined_capable"] and len(record["agents"]) < 2:
        raise ValueError(
            "facility '%s' claims combined capability with a single agent" % record["name"]
        )
    return record


def acceleration_factor(test_flux, mission_flux):
    """Return the ratio of test flux to the flux the mission actually delivers."""
    test = _real(test_flux, "test_flux")
    mission = _real(mission_flux, "mission_flux")
    return test / mission


def exposure_hours(target_fluence, test_flux):
    """Return the beam hours needed to deliver the target fluence."""
    fluence = _real(target_fluence, "target_fluence", allow_zero=True)
    flux = _real(test_flux, "test_flux")
    return fluence / flux / 3600.0


def uniformity_pct(min_flux, max_flux):
    """Return the plus-or-minus percentage spread of flux about its mean."""
    low = _real(min_flux, "min_flux")
    high = _real(max_flux, "max_flux")
    if low > high:
        raise ValueError("min_flux %g exceeds max_flux %g" % (low, high))
    mean = 0.5 * (low + high)
    return 100.0 * (high - low) / (2.0 * mean)


def energy_coverage_findings(record, required_min_mev, required_max_mev):
    """Return the findings raised when a facility cannot span the required window."""
    need_min = _real(required_min_mev, "required_min_mev")
    need_max = _real(required_max_mev, "required_max_mev")
    if need_min > need_max:
        raise ValueError("required energy window is inverted")
    findings = []
    if record["energy_min_mev"] > need_min and not math.isclose(
        record["energy_min_mev"], need_min, rel_tol=_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "%s starts at %.4g MeV, the campaign needs %.4g MeV"
            % (record["name"], record["energy_min_mev"], need_min)
        )
    if record["energy_max_mev"] < need_max and not math.isclose(
        record["energy_max_mev"], need_max, rel_tol=_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "%s stops at %.4g MeV, the campaign needs %.4g MeV"
            % (record["name"], record["energy_max_mev"], need_max)
        )
    return findings


def exposure_mode(record, agents_required, synergy_expected,
                  sequential_order="particles-then-ultraviolet"):
    """Return the (mode, findings) the campaign runs in at this facility."""
    if not isinstance(agents_required, (list, tuple)) or not agents_required:
        raise ValueError("agents_required must be a non-empty sequence")
    for agent in agents_required:
        if agent not in AGENTS:
            raise ValueError("unknown required agent %r" % agent)
    if not isinstance(synergy_expected, bool):
        raise ValueError("synergy_expected must be a boolean")
    if sequential_order not in SEQUENTIAL_ORDERS:
        raise ValueError(
            "sequential_order must be one of %r, got %r" % (SEQUENTIAL_ORDERS, sequential_order)
        )
    needed = tuple(sorted(set(agents_required)))
    findings = []
    if len(needed) == 1:
        return ("single-agent", findings)
    if record["combined_capable"]:
        return ("combined", findings)
    if synergy_expected:
        findings.append(
            "%s cannot combine the agents; a synergistic response will not be reproduced"
            % record["name"]
        )
    return (sequential_order, findings)


def grade_facility(facility, requirement):
    """Grade one candidate facility against the campaign requirement."""
    record = validate_facility(facility)
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    for key in ("agents", "energy_min_mev", "energy_max_mev", "mission_particle_flux",
                "target_particle_fluence", "max_pressure_pa", "specimen_temperature_c"):
        if key not in requirement:
            raise ValueError("requirement missing required key '%s'" % key)
    findings = []
    needed = tuple(sorted(set(requirement["agents"])))
    for agent in needed:
        if agent not in record["agents"]:
            findings.append("%s does not produce %s" % (record["name"], agent))
    if "particles" in needed:
        findings.extend(
            energy_coverage_findings(
                record, requirement["energy_min_mev"], requirement["energy_max_mev"]
            )
        )
    if record["uniformity_pct"] > MAX_UNIFORMITY_PCT and not math.isclose(
        record["uniformity_pct"], MAX_UNIFORMITY_PCT, rel_tol=_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "%s target-plane uniformity is +/-%.2f%%, above the +/-%.2f%% limit"
            % (record["name"], record["uniformity_pct"], MAX_UNIFORMITY_PCT)
        )
    max_pressure = _real(requirement["max_pressure_pa"], "max_pressure_pa")
    if record["base_pressure_pa"] > max_pressure and not math.isclose(
        record["base_pressure_pa"], max_pressure, rel_tol=_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "%s reaches %.3g Pa, the campaign needs %.3g Pa or better"
            % (record["name"], record["base_pressure_pa"], max_pressure)
        )
    temperature = float(requirement["specimen_temperature_c"])
    low, high = record["temperature_window_c"]
    if temperature < low or temperature > high:
        findings.append(
            "%s holds %.1f to %.1f C and cannot hold the specimen at %.1f C"
            % (record["name"], low, high, temperature)
        )
    mission_flux = _real(requirement["mission_particle_flux"], "mission_particle_flux")
    factor = None
    hours = None
    if "particles" in needed and record["max_particle_flux"] > 0.0:
        factor = acceleration_factor(record["max_particle_flux"], mission_flux)
        hours = exposure_hours(
            requirement["target_particle_fluence"], record["max_particle_flux"]
        )
        if factor > MAX_ACCELERATION_FACTOR and not math.isclose(
            factor, MAX_ACCELERATION_FACTOR, rel_tol=_TOLERANCE, abs_tol=0.0
        ):
            findings.append(
                "%s runs at an acceleration factor of %.4g, above the limit of %.4g"
                % (record["name"], factor, MAX_ACCELERATION_FACTOR)
            )
    mode, mode_findings = exposure_mode(
        record,
        needed,
        bool(requirement.get("synergy_expected", False)),
        requirement.get("sequential_order", "particles-then-ultraviolet"),
    )
    findings.extend(mode_findings)
    return {
        "name": record["name"],
        "agents": record["agents"],
        "exposure_mode": mode,
        "acceleration_factor": factor,
        "beam_hours": hours,
        "uniformity_pct": record["uniformity_pct"],
        "findings": findings,
        "admissible": not findings,
    }


def rank_facilities(facilities, requirement):
    """Return every graded candidate, admissible ones first by acceleration."""
    if not isinstance(facilities, (list, tuple)) or not facilities:
        raise ValueError("facilities must be a non-empty sequence")
    graded = [grade_facility(candidate, requirement) for candidate in facilities]
    names = [record["name"] for record in graded]
    if len(set(names)) != len(names):
        raise ValueError("facility names must be unique within one selection")

    def key(record):
        factor = record["acceleration_factor"]
        return (
            0 if record["admissible"] else 1,
            factor if factor is not None else math.inf,
            record["name"],
        )

    return sorted(graded, key=key)


def select_irradiation_facility(facilities, requirement):
    """Return the selection record naming the facility the campaign runs at."""
    ranked = rank_facilities(facilities, requirement)
    admissible = [record for record in ranked if record["admissible"]]
    chosen = admissible[0] if admissible else None
    findings = []
    if chosen is None:
        findings.append("no candidate facility meets the campaign requirement")
    return {
        "ranked": ranked,
        "selected": chosen,
        "admissible_count": len(admissible),
        "findings": findings,
        "selection_made": chosen is not None,
    }
