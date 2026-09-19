"""Launch-campaign cleanliness control from arrival to lift-off.

Anchor: ECSS-Q-ST-70-01 operations clause (preserving hardware cleanliness at
the launch site, through transport, integration, propellant loading and fairing
encapsulation). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate the launch-campaign sequence: each stage has a known activity, an
   environment, a duration and a protection state, and the stages have to
   appear in a physically possible order.
2. Accumulate particulate and molecular pickup stage by stage, crediting the
   protection state for what it actually blocks.
3. Apply the rules the campaign cannot be run without: propellant loading needs
   vapour protection, the fairing has to be verified clean before it closes,
   and a purge credit is only available where a purge is actually connected.
4. Report the budget consumed at lift-off, the stage that consumed most of it,
   and every blocking finding.
"""

import math

__all__ = [
    "STAGE_ACTIVITIES",
    "ENVIRONMENT_FALLOUT_PPM_PER_HOUR",
    "PROTECTION_TRANSMISSION",
    "STAGE_ORDER",
    "BUDGET_TOLERANCE",
    "environment_rate",
    "protection_transmission",
    "validate_stage",
    "validate_sequence",
    "stage_particulate_ppm",
    "stage_molecular_mg_per_m2",
    "encapsulation_findings",
    "propellant_findings",
    "purge_findings",
    "accumulate_launch_campaign",
    "plan_launch_site_control",
]

# Launch-campaign activities in the order they can physically occur.
STAGE_ACTIVITIES = (
    "arrival",
    "unpacking",
    "integration",
    "propellant-loading",
    "encapsulation",
    "transfer",
    "pad-stay",
)

STAGE_ORDER = {name: index for index, name in enumerate(STAGE_ACTIVITIES)}

# Obscuration added per exposure hour by environment. Paraphrased planning
# figures, not standard text.
ENVIRONMENT_FALLOUT_PPM_PER_HOUR = {
    "ISO-5": 0.0008,
    "ISO-6": 0.0025,
    "ISO-7": 0.0080,
    "ISO-8": 0.0250,
    "payload-processing-hall": 0.0120,
    "transfer-corridor": 0.0600,
    "pad-open-air": 0.3000,
}

# Fraction of the environment the hardware still sees under each protection
# state.
PROTECTION_TRANSMISSION = {
    "open": 1.00,
    "covered": 0.30,
    "single-bagged": 0.10,
    "transport-container": 0.05,
    "encapsulated-unpurged": 0.08,
    "encapsulated-purged": 0.01,
}

# Molecular pickup per hour, by environment, in milligrams per square metre.
ENVIRONMENT_MOLECULAR_MG_PER_M2_PER_HOUR = {
    "ISO-5": 0.0004,
    "ISO-6": 0.0008,
    "ISO-7": 0.0015,
    "ISO-8": 0.0030,
    "payload-processing-hall": 0.0025,
    "transfer-corridor": 0.0090,
    "pad-open-air": 0.0400,
}

# Propellant vapour adds a molecular source of its own during loading.
PROPELLANT_VAPOUR_MG_PER_M2_PER_HOUR = 0.0600

REQUIRED_STAGE_KEYS = ("activity", "environment", "duration_hours", "protection")

BUDGET_TOLERANCE = 1e-9


def environment_rate(environment, table=None):
    """Return the tabulated pickup rate of a launch-site environment."""
    lookup = ENVIRONMENT_FALLOUT_PPM_PER_HOUR if table is None else table
    if not isinstance(environment, str) or not environment.strip():
        raise ValueError("environment must be a non-empty string")
    key = environment.strip()
    if key not in lookup:
        raise ValueError(
            "unknown launch-site environment %r; known: %s"
            % (environment, ", ".join(sorted(lookup)))
        )
    return lookup[key]


def protection_transmission(protection):
    """Return the fraction of the environment a protection state passes."""
    if not isinstance(protection, str) or not protection.strip():
        raise ValueError("protection must be a non-empty string")
    key = protection.strip()
    if key not in PROTECTION_TRANSMISSION:
        raise ValueError(
            "unknown protection state %r; known: %s"
            % (protection, ", ".join(sorted(PROTECTION_TRANSMISSION)))
        )
    return PROTECTION_TRANSMISSION[key]


def validate_stage(stage):
    """Return a normalized launch-campaign stage, raising on bad input."""
    if not isinstance(stage, dict):
        raise ValueError("a launch-campaign stage must be a mapping")
    for key in REQUIRED_STAGE_KEYS:
        if key not in stage:
            raise ValueError("stage missing required key '%s'" % key)
    activity = stage["activity"]
    if activity not in STAGE_ACTIVITIES:
        raise ValueError(
            "activity must be one of %s, got %r"
            % (", ".join(STAGE_ACTIVITIES), activity)
        )
    hours = stage["duration_hours"]
    if isinstance(hours, bool) or not isinstance(hours, (int, float)):
        raise ValueError("duration_hours must be a real number")
    hours = float(hours)
    if not math.isfinite(hours) or hours < 0.0:
        raise ValueError("duration_hours must be non-negative and finite, got %r" % (hours,))
    environment_rate(stage["environment"])
    environment_rate(stage["environment"], ENVIRONMENT_MOLECULAR_MG_PER_M2_PER_HOUR)
    protection_transmission(stage["protection"])
    return {
        "activity": activity,
        "environment": stage["environment"].strip(),
        "duration_hours": hours,
        "protection": stage["protection"].strip(),
        "purge_connected": bool(stage.get("purge_connected", False)),
        "vapour_protection": bool(stage.get("vapour_protection", False)),
        "fairing_verified": bool(stage.get("fairing_verified", False)),
    }


def validate_sequence(stages):
    """Return the normalized stages, refusing an impossible campaign order."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("stages must be a non-empty sequence")
    normalized = [validate_stage(stage) for stage in stages]
    seen = set()
    previous_rank = -1
    for stage in normalized:
        activity = stage["activity"]
        if activity in seen:
            raise ValueError("activity %r appears twice in the campaign" % activity)
        seen.add(activity)
        rank = STAGE_ORDER[activity]
        if rank < previous_rank:
            raise ValueError(
                "activity %r cannot follow a later campaign stage" % activity
            )
        previous_rank = rank
    return normalized


def stage_particulate_ppm(stage):
    """Return the obscuration one launch-campaign stage adds."""
    normalized = validate_stage(stage)
    rate = environment_rate(normalized["environment"])
    transmission = protection_transmission(normalized["protection"])
    return rate * normalized["duration_hours"] * transmission


def stage_molecular_mg_per_m2(stage):
    """Return the molecular loading one launch-campaign stage adds."""
    normalized = validate_stage(stage)
    rate = environment_rate(
        normalized["environment"], ENVIRONMENT_MOLECULAR_MG_PER_M2_PER_HOUR
    )
    transmission = protection_transmission(normalized["protection"])
    loading = rate * normalized["duration_hours"] * transmission
    if normalized["activity"] == "propellant-loading":
        vapour = PROPELLANT_VAPOUR_MG_PER_M2_PER_HOUR * normalized["duration_hours"]
        loading += vapour * (0.1 if normalized["vapour_protection"] else 1.0)
    return loading


def encapsulation_findings(stages):
    """Return findings about closing the fairing on an unverified article."""
    normalized = validate_sequence(stages)
    findings = []
    for stage in normalized:
        if stage["activity"] != "encapsulation":
            continue
        if not stage["fairing_verified"]:
            findings.append(
                "the fairing is closed without a cleanliness verification; "
                "nothing inside can be re-verified afterwards"
            )
    return findings


def propellant_findings(stages):
    """Return findings about loading propellant without vapour protection."""
    normalized = validate_sequence(stages)
    findings = []
    for stage in normalized:
        if stage["activity"] != "propellant-loading":
            continue
        if not stage["vapour_protection"]:
            findings.append(
                "propellant loading is run with the article unprotected against "
                "vapour; the deposit it leaves is not removable at the pad"
            )
    return findings


def purge_findings(stages):
    """Return findings where a purge credit is taken without a purge."""
    normalized = validate_sequence(stages)
    findings = []
    for stage in normalized:
        if stage["protection"] != "encapsulated-purged":
            continue
        if not stage["purge_connected"]:
            findings.append(
                "stage %s claims the purged-fairing credit with no purge "
                "connected" % stage["activity"]
            )
    return findings


def accumulate_launch_campaign(stages):
    """Return the running per-stage and cumulative launch-campaign totals."""
    normalized = validate_sequence(stages)
    running_particulate = 0.0
    running_molecular = 0.0
    rows = []
    for stage in normalized:
        added_particulate = stage_particulate_ppm(stage)
        added_molecular = stage_molecular_mg_per_m2(stage)
        running_particulate += added_particulate
        running_molecular += added_molecular
        rows.append(
            {
                "activity": stage["activity"],
                "environment": stage["environment"],
                "duration_hours": stage["duration_hours"],
                "protection": stage["protection"],
                "added_particulate_ppm": added_particulate,
                "added_molecular_mg_per_m2": added_molecular,
                "cumulative_particulate_ppm": running_particulate,
                "cumulative_molecular_mg_per_m2": running_molecular,
            }
        )
    return rows


def _within(value, allocation):
    """Return True when a value is inside an allocation within tolerance."""
    return value < allocation or math.isclose(
        value, allocation, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE
    )


def plan_launch_site_control(campaign):
    """Run the full launch-campaign cleanliness plan.

    campaign keys: stages (sequence of campaign stages), particulate_budget_ppm,
    molecular_budget_mg_per_m2, and optionally arrival_particulate_ppm and
    arrival_molecular_mg_per_m2 for the state the article shipped in.
    """
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping")
    for key in ("stages", "particulate_budget_ppm", "molecular_budget_mg_per_m2"):
        if key not in campaign:
            raise ValueError("campaign missing required key '%s'" % key)
    for key in ("particulate_budget_ppm", "molecular_budget_mg_per_m2"):
        value = campaign[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % key)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite" % key)
    arrival_particulate = float(campaign.get("arrival_particulate_ppm", 0.0) or 0.0)
    arrival_molecular = float(campaign.get("arrival_molecular_mg_per_m2", 0.0) or 0.0)
    for label, value in (
        ("arrival_particulate_ppm", arrival_particulate),
        ("arrival_molecular_mg_per_m2", arrival_molecular),
    ):
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("%s must be non-negative and finite" % label)

    rows = accumulate_launch_campaign(campaign["stages"])
    for row in rows:
        row["cumulative_particulate_ppm"] += arrival_particulate
        row["cumulative_molecular_mg_per_m2"] += arrival_molecular

    total_particulate = rows[-1]["cumulative_particulate_ppm"]
    total_molecular = rows[-1]["cumulative_molecular_mg_per_m2"]
    particulate_budget = float(campaign["particulate_budget_ppm"])
    molecular_budget = float(campaign["molecular_budget_mg_per_m2"])

    findings = []
    findings.extend(propellant_findings(campaign["stages"]))
    findings.extend(encapsulation_findings(campaign["stages"]))
    findings.extend(purge_findings(campaign["stages"]))
    if not _within(total_particulate, particulate_budget):
        findings.append(
            "obscuration at lift-off %.5f ppm exceeds the %.5f ppm budget"
            % (total_particulate, particulate_budget)
        )
    if not _within(total_molecular, molecular_budget):
        findings.append(
            "molecular loading at lift-off %.5f mg/m2 exceeds the %.5f mg/m2 budget"
            % (total_molecular, molecular_budget)
        )

    dominant = max(rows, key=lambda row: row["added_particulate_ppm"])
    return {
        "rows": rows,
        "total_particulate_ppm": total_particulate,
        "total_molecular_mg_per_m2": total_molecular,
        "particulate_margin_ppm": particulate_budget - total_particulate,
        "molecular_margin_mg_per_m2": molecular_budget - total_molecular,
        "dominant_stage": dominant["activity"],
        "ready_for_launch": not findings,
        "findings": findings,
    }
