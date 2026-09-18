"""Minimum acceptable quality level for microwave dies in a space build.

Anchor: ECSS-Q-ST-60-12C clause 4.3 (the lowest quality level a die used in
space equipment may be bought at). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the application: the criticality the equipment is grouped under,
   how long the mission runs, the total dose the die sees, whether the die sits
   in a single point of failure, and any floor the programme imposes above the
   level the standard would derive on its own.
2. Place the application on the quality ladder: a base rung from criticality,
   then one rung of escalation for each aggravating condition, capped at the
   top of the ladder rather than allowed to run off it.
3. Apply the absolute floor. No space equipment build may sit below it however
   benign the application reads, so the derived rung is raised to it.
4. Compare the offered die against the resulting floor. At or above it the die
   is acceptable as procured.
5. Below it, derive the rung-by-rung upgrade actions that would carry the die
   to the floor, and refuse the die outright when the gap is wider than the
   number of rungs an upgrade route can credibly bridge.
"""

import math

__all__ = [
    "QUALITY_LADDER",
    "ABSOLUTE_FLOOR",
    "MAX_UPGRADE_STEPS",
    "CRITICALITY_BASE",
    "LONG_MISSION_YEARS",
    "RADIATION_THRESHOLD_KRAD",
    "COMPARISON_TOLERANCE",
    "level_rank",
    "level_at_rank",
    "validate_level",
    "validate_application",
    "base_floor",
    "escalation_steps",
    "required_floor",
    "upgrade_path",
    "assess_die_quality",
]

# Ascending quality order: index 0 is the least controlled rung.
QUALITY_LADDER = (
    "commercial",
    "industrial",
    "screened-industrial",
    "level-3",
    "level-2",
    "level-1",
)

# No space equipment build sits below this rung, however benign it reads.
ABSOLUTE_FLOOR = "level-3"

# An upgrade route buys screening and lot evidence; it cannot manufacture a
# process history, so it can carry a die at most this many rungs.
MAX_UPGRADE_STEPS = 2

CRITICALITY_BASE = {
    "non-critical": "level-3",
    "mission-critical": "level-2",
    "safety-critical": "level-1",
}

LONG_MISSION_YEARS = 5.0

RADIATION_THRESHOLD_KRAD = 30.0

# Mission duration and dose arrive as floats and are often the result of a
# budget computed elsewhere. Compare against the thresholds with a relative
# tolerance so a value that should sit exactly on a threshold does so on every
# platform instead of escalating on one and not on another.
COMPARISON_TOLERANCE = 1e-9

_UPGRADE_ACTIONS = {
    "industrial": ("supplier process control review",),
    "screened-industrial": ("full visual inspection", "temperature cycling screen"),
    "level-3": ("wafer lot acceptance testing", "full visual and RF screening"),
    "level-2": ("destructive physical analysis on the lot", "extended burn-in screen"),
    "level-1": ("full lot validation testing", "radiation lot acceptance"),
}


def _exceeds(value, threshold):
    """True when value is above threshold by more than representation noise."""
    if math.isclose(value, threshold, rel_tol=COMPARISON_TOLERANCE, abs_tol=0.0):
        return False
    return value > threshold


def _at_least(value, threshold):
    """True when value reaches threshold, treating an exact hit as reaching it."""
    if math.isclose(value, threshold, rel_tol=COMPARISON_TOLERANCE, abs_tol=0.0):
        return True
    return value > threshold


def validate_level(level, label="level"):
    """Return a normalised rung token from the quality ladder."""
    if not isinstance(level, str):
        raise ValueError("%s must be a string token" % label)
    token = level.strip().lower()
    if token not in QUALITY_LADDER:
        raise ValueError(
            "%s '%s' is not one of %s" % (label, level, ", ".join(QUALITY_LADDER))
        )
    return token


def level_rank(level):
    """Return the ascending ladder index of a quality level."""
    return QUALITY_LADDER.index(validate_level(level))


def level_at_rank(rank):
    """Return the quality level sitting at a ladder index."""
    if not isinstance(rank, int) or isinstance(rank, bool):
        raise ValueError("rank must be an integer")
    if rank < 0 or rank >= len(QUALITY_LADDER):
        raise ValueError(
            "rank %d is outside the ladder 0..%d" % (rank, len(QUALITY_LADDER) - 1)
        )
    return QUALITY_LADDER[rank]


def _validate_non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def validate_application(spec):
    """Return the normalised application the floor is derived from."""
    if not isinstance(spec, dict):
        raise ValueError("application must be a mapping")
    for key in ("criticality", "mission_years", "total_dose_krad", "offered_level"):
        if key not in spec:
            raise ValueError("application missing required key '%s'" % key)
    allowed = {
        "criticality", "mission_years", "total_dose_krad", "offered_level",
        "single_point_failure", "programme_floor",
    }
    for key in spec:
        if key not in allowed:
            raise ValueError("application carries unknown key '%s'" % key)

    criticality = spec["criticality"]
    if not isinstance(criticality, str):
        raise ValueError("criticality must be a string token")
    criticality = criticality.strip().lower()
    if criticality not in CRITICALITY_BASE:
        raise ValueError(
            "criticality '%s' is not one of %s"
            % (spec["criticality"], ", ".join(sorted(CRITICALITY_BASE)))
        )

    single_point = spec.get("single_point_failure", False)
    if not isinstance(single_point, bool):
        raise ValueError("single_point_failure must be a boolean")

    programme_floor = spec.get("programme_floor")
    if programme_floor is not None:
        programme_floor = validate_level(programme_floor, "programme_floor")

    return {
        "criticality": criticality,
        "mission_years": _validate_non_negative(spec["mission_years"], "mission_years"),
        "total_dose_krad": _validate_non_negative(spec["total_dose_krad"], "total_dose_krad"),
        "single_point_failure": single_point,
        "offered_level": validate_level(spec["offered_level"], "offered_level"),
        "programme_floor": programme_floor,
    }


def base_floor(criticality):
    """Return the base rung the equipment criticality alone sets."""
    if not isinstance(criticality, str):
        raise ValueError("criticality must be a string token")
    token = criticality.strip().lower()
    if token not in CRITICALITY_BASE:
        raise ValueError(
            "criticality '%s' is not one of %s"
            % (criticality, ", ".join(sorted(CRITICALITY_BASE)))
        )
    return CRITICALITY_BASE[token]


def escalation_steps(application):
    """Return the rungs of escalation the application earns, with their reasons."""
    if not isinstance(application, dict) or "criticality" not in application:
        raise ValueError("application must be a normalised application mapping")
    reasons = []
    if _exceeds(application["mission_years"], LONG_MISSION_YEARS):
        reasons.append(
            "mission runs %.2f years, beyond the %.2f year duration threshold"
            % (application["mission_years"], LONG_MISSION_YEARS)
        )
    if _at_least(application["total_dose_krad"], RADIATION_THRESHOLD_KRAD):
        reasons.append(
            "total dose %.2f krad reaches the %.2f krad evaluation threshold"
            % (application["total_dose_krad"], RADIATION_THRESHOLD_KRAD)
        )
    if application["single_point_failure"]:
        reasons.append("the die sits in a single point of failure")
    return len(reasons), reasons


def required_floor(application):
    """Return the minimum acceptable rung for this application, and how it was reached."""
    base = base_floor(application["criticality"])
    steps, reasons = escalation_steps(application)
    top = len(QUALITY_LADDER) - 1
    raw = level_rank(base) + steps
    capped = raw > top
    rank = min(raw, top)
    if rank < level_rank(ABSOLUTE_FLOOR):
        rank = level_rank(ABSOLUTE_FLOOR)
        reasons = reasons + ["raised to the absolute floor for space equipment"]
    programme = application.get("programme_floor")
    programme_raised = False
    if programme is not None and level_rank(programme) > rank:
        rank = level_rank(programme)
        programme_raised = True
        reasons = reasons + ["raised to the programme floor '%s'" % programme]
    return {
        "base_level": base,
        "escalation_steps": steps,
        "capped_at_top": capped,
        "programme_raised": programme_raised,
        "level": level_at_rank(rank),
        "reasons": reasons,
    }


def upgrade_path(offered_level, target_level):
    """Return the rung-by-rung upgrade actions carrying offered up to target."""
    start = level_rank(offered_level)
    end = level_rank(target_level)
    if end < start:
        raise ValueError(
            "target level '%s' sits below the offered level '%s'"
            % (target_level, offered_level)
        )
    path = []
    for rank in range(start + 1, end + 1):
        rung = level_at_rank(rank)
        path.append({
            "from_level": level_at_rank(rank - 1),
            "to_level": rung,
            "actions": _UPGRADE_ACTIONS[rung],
        })
    return path


def assess_die_quality(spec):
    """Run the full clause 4.3 minimum quality baseline assessment.

    spec keys: criticality, mission_years, total_dose_krad, offered_level,
    optional single_point_failure and programme_floor.
    """
    application = validate_application(spec)
    floor = required_floor(application)
    offered = application["offered_level"]
    gap = level_rank(floor["level"]) - level_rank(offered)

    findings = []
    notes = []
    if level_rank(offered) < level_rank(ABSOLUTE_FLOOR):
        findings.append(
            "offered level '%s' sits below '%s', the lowest rung any space equipment "
            "build may use" % (offered, ABSOLUTE_FLOOR)
        )
    if floor["capped_at_top"]:
        notes.append(
            "escalation was capped at the top of the ladder; the aggravating "
            "conditions exceed what the ladder can express"
        )
    if gap <= 0:
        if level_rank(offered) > level_rank(floor["level"]):
            notes.append(
                "offered level '%s' sits above the floor '%s'; the margin is not a defect"
                % (offered, floor["level"])
            )
        return {
            "application": application,
            "required_level": floor["level"],
            "required_reasons": floor["reasons"],
            "offered_level": offered,
            "gap_rungs": 0,
            "acceptable_as_procured": True,
            "upgradable": True,
            "upgrade_path": [],
            "findings": findings,
            "notes": notes,
            "clear": not findings,
        }

    upgradable = gap <= MAX_UPGRADE_STEPS
    path = upgrade_path(offered, floor["level"]) if upgradable else []
    findings.append(
        "offered level '%s' sits %d rung(s) below the required floor '%s'"
        % (offered, gap, floor["level"])
    )
    if not upgradable:
        findings.append(
            "the gap is wider than the %d rungs an upgrade route can bridge; "
            "the die is refused for this application" % MAX_UPGRADE_STEPS
        )
    return {
        "application": application,
        "required_level": floor["level"],
        "required_reasons": floor["reasons"],
        "offered_level": offered,
        "gap_rungs": gap,
        "acceptable_as_procured": False,
        "upgradable": upgradable,
        "upgrade_path": path,
        "findings": findings,
        "notes": notes,
        "clear": False,
    }
