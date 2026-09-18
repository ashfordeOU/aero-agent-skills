"""SCC-promoting environment identification across the exposure phases.

Anchor: ECSS-Q-ST-70-36C, the environment clauses that decide which exposures a
part meets over its life can promote stress-corrosion cracking. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Recognise the agent each exposure phase presents -- humid air, salt-laden
   coastal air, chloride solutions, alkaline and ammonia-bearing fluids,
   propellants, chlorinated cleaning solvents, or an inert atmosphere -- and
   read its base severity.
2. Raise the severity of humid air with the relative humidity of the phase,
   because condensation on a cold surface is what turns humid air into an
   electrolyte.
3. Lower the severity by one step for a phase with an effective protection --
   a purge, a sealed bag with desiccant, a conformal coat -- never below
   inert.
4. Take the worst phase as the governing environment, total the promoting
   exposure hours across the whole life, and raise a finding for every severe
   phase left unprotected.
"""

import math

__all__ = [
    "HOURS_TOLERANCE",
    "SEVERITY_LEVELS",
    "AGENT_REGISTRY",
    "HUMIDITY_MODERATE_PCT",
    "HUMIDITY_SEVERE_PCT",
    "normalize_agent",
    "agent_severity",
    "humidity_severity",
    "protected_severity",
    "phase_severity",
    "evaluate_phase",
    "governing_environment",
    "assess_environments",
]

# Durations are summed across phases; a total an engineer means to be exact
# should not be reported one bit off.
HOURS_TOLERANCE = 1e-9

# Severity ladder, least to most able to promote cracking.
SEVERITY_LEVELS = ("inert", "benign", "moderate", "severe")

# Relative humidity at which ambient air starts to behave as an electrolyte on
# a cold surface, and the level at which it is treated as fully aggressive.
HUMIDITY_MODERATE_PCT = 60.0
HUMIDITY_SEVERE_PCT = 85.0

# Agents an exposure phase can present, with the severity each carries before
# humidity and protection are applied.
AGENT_REGISTRY = {
    "dry-nitrogen-purge": {"severity": "inert", "note": "no electrolyte can form"},
    "vacuum": {"severity": "inert", "note": "on-orbit vacuum presents no electrolyte"},
    "cleanroom-air": {"severity": "benign", "note": "humidity-controlled and filtered"},
    "ambient-air": {"severity": "benign", "note": "severity set by the phase humidity"},
    "humid-air": {"severity": "moderate", "note": "severity set by the phase humidity"},
    "condensing-humidity": {"severity": "severe", "note": "a standing electrolyte film"},
    "coastal-salt-air": {"severity": "severe", "note": "airborne chloride plus humidity"},
    "chloride-solution": {"severity": "severe", "note": "the reference aggressive medium"},
    "seawater": {"severity": "severe", "note": "chloride-bearing and conductive"},
    "de-icing-salt": {"severity": "severe", "note": "chloride carried by transport exposure"},
    "alkaline-solution": {"severity": "moderate", "note": "attacks specific alloy families"},
    "ammonia-bearing-fluid": {"severity": "severe", "note": "the copper-alloy cracking agent"},
    "chlorinated-solvent": {"severity": "moderate", "note": "halogen source for titanium"},
    "storable-propellant": {"severity": "moderate", "note": "handled as a chemically active fluid"},
    "distilled-water": {"severity": "benign", "note": "no halide, but still an electrolyte path"},
    "hydrogen-bearing-gas": {"severity": "moderate", "note": "treated with the sustained-load agents"},
}

_AGENT_ALIASES = {
    "gn2": "dry-nitrogen-purge",
    "dry-nitrogen": "dry-nitrogen-purge",
    "nitrogen-purge": "dry-nitrogen-purge",
    "space-vacuum": "vacuum",
    "orbit": "vacuum",
    "clean-room-air": "cleanroom-air",
    "air": "ambient-air",
    "moist-air": "humid-air",
    "salt-spray": "coastal-salt-air",
    "sea-air": "coastal-salt-air",
    "marine-atmosphere": "coastal-salt-air",
    "saltwater": "seawater",
    "salt-solution": "chloride-solution",
    "road-salt": "de-icing-salt",
    "caustic": "alkaline-solution",
    "ammonia": "ammonia-bearing-fluid",
    "trichloroethylene": "chlorinated-solvent",
    "hydrazine": "storable-propellant",
    "nitrogen-tetroxide": "storable-propellant",
    "deionised-water": "distilled-water",
    "hydrogen": "hydrogen-bearing-gas",
}


def _token(value, label):
    """Return a lower-cased dash-normalized token, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def normalize_agent(value):
    """Return the canonical agent token for a declared exposure agent."""
    token = _token(value, "agent")
    token = _AGENT_ALIASES.get(token, token)
    if token not in AGENT_REGISTRY:
        raise ValueError(
            "exposure agent %r is not recognised; declare one of %s"
            % (value, ", ".join(sorted(AGENT_REGISTRY)))
        )
    return token


def agent_severity(agent):
    """Return the base severity the agent carries."""
    return AGENT_REGISTRY[normalize_agent(agent)]["severity"]


def _severity_index(severity):
    """Return the ladder index of a severity token."""
    if severity not in SEVERITY_LEVELS:
        raise ValueError("severity %r is not on the ladder" % (severity,))
    return SEVERITY_LEVELS.index(severity)


def humidity_severity(relative_humidity_pct):
    """Return the severity ambient or humid air carries at a relative humidity.

    Both thresholds are inclusive: a phase recorded exactly at a threshold sits
    at the higher severity, and the equality is resolved by a named tolerance.
    """
    if not isinstance(relative_humidity_pct, (int, float)) or isinstance(
        relative_humidity_pct, bool
    ):
        raise ValueError("relative_humidity_pct must be a real number")
    value = float(relative_humidity_pct)
    if not math.isfinite(value):
        raise ValueError("relative_humidity_pct must be finite")
    if value < 0.0 or value > 100.0:
        raise ValueError(
            "relative_humidity_pct %g is outside 0-100; check the units" % value
        )
    at_severe = math.isclose(value, HUMIDITY_SEVERE_PCT, rel_tol=0.0, abs_tol=HOURS_TOLERANCE)
    at_moderate = math.isclose(
        value, HUMIDITY_MODERATE_PCT, rel_tol=0.0, abs_tol=HOURS_TOLERANCE
    )
    if value > HUMIDITY_SEVERE_PCT or at_severe:
        return "severe"
    if value > HUMIDITY_MODERATE_PCT or at_moderate:
        return "moderate"
    return "benign"


def protected_severity(severity, protection=None):
    """Return the severity after an effective protection, floored at inert."""
    index = _severity_index(severity)
    if protection is None:
        return severity
    token = _token(protection, "protection")
    known = ("purge", "sealed-bag-desiccant", "conformal-coat", "sealed-container", "none")
    if token not in known:
        raise ValueError(
            "protection %r is not recognised; declare one of %s"
            % (protection, ", ".join(known))
        )
    if token == "none":
        return severity
    return SEVERITY_LEVELS[max(index - 1, 0)]


def phase_severity(agent, relative_humidity_pct=None, protection=None):
    """Return the effective severity of one exposure phase."""
    token = normalize_agent(agent)
    severity = AGENT_REGISTRY[token]["severity"]
    if token in ("ambient-air", "humid-air"):
        if relative_humidity_pct is None:
            raise ValueError(
                "agent %s needs relative_humidity_pct; its severity is set by the "
                "humidity of the phase, not by its name" % token
            )
        severity = humidity_severity(relative_humidity_pct)
    elif relative_humidity_pct is not None:
        # Accept and validate the reading, but do not let it override an agent
        # whose severity is set by its chemistry rather than by humidity.
        humidity_severity(relative_humidity_pct)
    return protected_severity(severity, protection)


def _hours(value):
    """Return a finite, non-negative duration in hours."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("duration_hours must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("duration_hours must be finite")
    if number < 0.0:
        raise ValueError("duration_hours must not be negative, got %r" % (value,))
    return number


def evaluate_phase(phase):
    """Return the environment record for one exposure phase."""
    if not isinstance(phase, dict):
        raise ValueError("phase must be a mapping")
    for key in ("name", "agent", "duration_hours"):
        if key not in phase:
            raise ValueError("phase missing required key %r" % key)
    name = _token(phase["name"], "phase name")
    agent = normalize_agent(phase["agent"])
    protection = phase.get("protection")
    base = AGENT_REGISTRY[agent]["severity"]
    effective = phase_severity(agent, phase.get("relative_humidity_pct"), protection)
    hours = _hours(phase["duration_hours"])
    promoting = _severity_index(effective) >= _severity_index("moderate")
    return {
        "name": name,
        "agent": agent,
        "base_severity": base,
        "effective_severity": effective,
        "severity_index": _severity_index(effective),
        "protection": None if protection is None else _token(protection, "protection"),
        "duration_hours": hours,
        "promoting": promoting,
        "note": AGENT_REGISTRY[agent]["note"],
    }


def governing_environment(records):
    """Return the worst phase; longest duration then name break a tie."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of phase records")
    best = None
    for record in records:
        if not isinstance(record, dict) or "severity_index" not in record:
            raise ValueError("each record must be a mapping carrying 'severity_index'")
        if best is None:
            best = record
            continue
        if record["severity_index"] > best["severity_index"]:
            best = record
        elif record["severity_index"] == best["severity_index"]:
            same_hours = math.isclose(
                record["duration_hours"],
                best["duration_hours"],
                rel_tol=0.0,
                abs_tol=HOURS_TOLERANCE,
            )
            if not same_hours and record["duration_hours"] > best["duration_hours"]:
                best = record
            elif same_hours and record["name"] < best["name"]:
                best = record
    return best


def assess_environments(phases):
    """Assess a life profile and report the governing SCC environment."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty sequence of mappings")
    records = []
    seen = set()
    for phase in phases:
        record = evaluate_phase(phase)
        if record["name"] in seen:
            raise ValueError("duplicate phase name %r" % record["name"])
        seen.add(record["name"])
        records.append(record)
    promoting = [r for r in records if r["promoting"]]
    governing = governing_environment(records)
    promoting_hours = sum(r["duration_hours"] for r in promoting)
    findings = []
    for record in records:
        if record["effective_severity"] == "severe" and not record["protection"]:
            findings.append(
                "phase %s presents %s unprotected for %.1f h; the environment is "
                "severe and nothing is holding it off the surface"
                % (record["name"], record["agent"], record["duration_hours"])
            )
    if promoting and math.isclose(promoting_hours, 0.0, rel_tol=0.0, abs_tol=HOURS_TOLERANCE):
        findings.append(
            "a cracking-promoting environment is present but every promoting phase "
            "has zero declared duration; the life profile is incomplete"
        )
    return {
        "records": records,
        "governing": governing,
        "governing_severity": governing["effective_severity"],
        "promoting_phase_count": len(promoting),
        "promoting_hours": promoting_hours,
        "any_promoting": bool(promoting),
        "findings": findings,
    }
