"""Contamination budget accounting across an environmental test campaign.

Anchor: ECSS-Q-ST-70-01 operations clause (keeping a test article at its
cleanliness level while it goes through thermal-vacuum, vibration and acoustic
testing). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate each test phase: the environment it runs in, how long the hardware
   is exposed, whether it is bagged or purged, and what the chamber does to it.
2. Accumulate particulate fallout from the cleanroom class and the exposure
   hours, reduced by the protection the phase actually provides.
3. Accumulate molecular deposition from the chamber and shroud conditions of a
   vacuum phase, reduced by the same protection where it applies.
4. Compare the running totals with the per-phase allocations and with the
   campaign allocation, and name the first phase at which the article has to be
   re-cleaned rather than carried forward.
"""

import math

__all__ = [
    "CLEANROOM_FALLOUT_PPM_PER_HOUR",
    "PROTECTION_TRANSMISSION",
    "PHASE_KINDS",
    "BUDGET_TOLERANCE",
    "fallout_rate_ppm_per_hour",
    "protection_transmission",
    "validate_phase",
    "phase_particulate_ppm",
    "phase_molecular_mg_per_m2",
    "accumulate_campaign",
    "first_reclean_phase",
    "assess_test_campaign",
]

# Obscuration added per exposure hour, by cleanroom class. Paraphrased
# planning figures, not standard text.
CLEANROOM_FALLOUT_PPM_PER_HOUR = {
    "ISO-5": 0.0008,
    "ISO-6": 0.0025,
    "ISO-7": 0.0080,
    "ISO-8": 0.0250,
    "uncontrolled": 0.2000,
}

# Fraction of the environment the hardware still sees under each protection
# state. A double bag is not a seal, so it is never zero.
PROTECTION_TRANSMISSION = {
    "open": 1.00,
    "covered": 0.30,
    "single-bagged": 0.10,
    "double-bagged": 0.03,
    "purged-enclosure": 0.01,
}

PHASE_KINDS = ("thermal-vacuum", "vibration", "acoustic", "handling", "storage")

REQUIRED_PHASE_KEYS = (
    "name",
    "kind",
    "cleanroom_class",
    "exposure_hours",
    "protection",
)

# Budget comparisons are sums of small floats; a phase landing exactly on its
# allocation must not be failed by the last bit of the sum.
BUDGET_TOLERANCE = 1e-9

# Molecular deposition driver for a vacuum phase: milligrams per square metre
# per hour at a reference chamber loading, scaled by the shroud-to-article
# temperature difference that drives transport onto the cold article.
VACUUM_DEPOSITION_MG_PER_M2_PER_HOUR = 0.004
REFERENCE_SHROUD_DELTA_K = 50.0


def fallout_rate_ppm_per_hour(cleanroom_class):
    """Return the tabulated particulate fallout rate of an environment."""
    if not isinstance(cleanroom_class, str) or not cleanroom_class.strip():
        raise ValueError("cleanroom_class must be a non-empty string")
    key = cleanroom_class.strip()
    if key not in CLEANROOM_FALLOUT_PPM_PER_HOUR:
        raise ValueError(
            "unknown cleanroom class %r; known: %s"
            % (cleanroom_class, ", ".join(sorted(CLEANROOM_FALLOUT_PPM_PER_HOUR)))
        )
    return CLEANROOM_FALLOUT_PPM_PER_HOUR[key]


def protection_transmission(protection):
    """Return the fraction of the environment a protection state still passes."""
    if not isinstance(protection, str) or not protection.strip():
        raise ValueError("protection must be a non-empty string")
    key = protection.strip()
    if key not in PROTECTION_TRANSMISSION:
        raise ValueError(
            "unknown protection state %r; known: %s"
            % (protection, ", ".join(sorted(PROTECTION_TRANSMISSION)))
        )
    return PROTECTION_TRANSMISSION[key]


def validate_phase(phase):
    """Return a normalized test phase, raising on anything missing or absurd."""
    if not isinstance(phase, dict):
        raise ValueError("a test phase must be a mapping")
    for key in REQUIRED_PHASE_KEYS:
        if key not in phase:
            raise ValueError("test phase missing required key '%s'" % key)
    name = phase["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("phase name must be a non-empty string")
    kind = phase["kind"]
    if kind not in PHASE_KINDS:
        raise ValueError(
            "phase kind must be one of %s, got %r" % (", ".join(PHASE_KINDS), kind)
        )
    hours = phase["exposure_hours"]
    if isinstance(hours, bool) or not isinstance(hours, (int, float)):
        raise ValueError("exposure_hours must be a real number")
    hours = float(hours)
    if not math.isfinite(hours) or hours < 0.0:
        raise ValueError("exposure_hours must be non-negative and finite, got %r" % (hours,))
    fallout_rate_ppm_per_hour(phase["cleanroom_class"])
    protection_transmission(phase["protection"])

    normalized = {
        "name": name.strip(),
        "kind": kind,
        "cleanroom_class": phase["cleanroom_class"].strip(),
        "exposure_hours": hours,
        "protection": phase["protection"].strip(),
        "chamber_loading_factor": 1.0,
        "shroud_delta_k": 0.0,
        "particulate_allocation_ppm": None,
        "molecular_allocation_mg_per_m2": None,
    }
    if "chamber_loading_factor" in phase:
        factor = phase["chamber_loading_factor"]
        if isinstance(factor, bool) or not isinstance(factor, (int, float)):
            raise ValueError("chamber_loading_factor must be a real number")
        factor = float(factor)
        if not math.isfinite(factor) or factor < 0.0:
            raise ValueError("chamber_loading_factor must be non-negative and finite")
        normalized["chamber_loading_factor"] = factor
    if "shroud_delta_k" in phase:
        delta = phase["shroud_delta_k"]
        if isinstance(delta, bool) or not isinstance(delta, (int, float)):
            raise ValueError("shroud_delta_k must be a real number")
        delta = float(delta)
        if not math.isfinite(delta) or delta < 0.0:
            raise ValueError("shroud_delta_k must be non-negative and finite")
        normalized["shroud_delta_k"] = delta
    if normalized["kind"] != "thermal-vacuum" and normalized["shroud_delta_k"] > 0.0:
        raise ValueError(
            "phase %s is not a vacuum phase but declares a shroud temperature "
            "difference" % normalized["name"]
        )
    for key, label in (
        ("particulate_allocation_ppm", "particulate allocation"),
        ("molecular_allocation_mg_per_m2", "molecular allocation"),
    ):
        if key in phase and phase[key] is not None:
            value = phase[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("%s must be a real number" % label)
            value = float(value)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError("%s must be non-negative and finite" % label)
            normalized[key] = value
    return normalized


def phase_particulate_ppm(phase):
    """Return the obscuration a single phase adds to the article."""
    normalized = validate_phase(phase)
    rate = fallout_rate_ppm_per_hour(normalized["cleanroom_class"])
    transmission = protection_transmission(normalized["protection"])
    return rate * normalized["exposure_hours"] * transmission


def phase_molecular_mg_per_m2(phase):
    """Return the molecular loading a single phase deposits on the article."""
    normalized = validate_phase(phase)
    if normalized["kind"] != "thermal-vacuum":
        return 0.0
    transmission = protection_transmission(normalized["protection"])
    delta_scale = normalized["shroud_delta_k"] / REFERENCE_SHROUD_DELTA_K
    return (
        VACUUM_DEPOSITION_MG_PER_M2_PER_HOUR
        * normalized["exposure_hours"]
        * normalized["chamber_loading_factor"]
        * delta_scale
        * transmission
    )


def accumulate_campaign(phases):
    """Return the running per-phase and cumulative contamination totals."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty sequence of test phases")
    running_particulate = 0.0
    running_molecular = 0.0
    seen = set()
    rows = []
    for phase in phases:
        normalized = validate_phase(phase)
        if normalized["name"] in seen:
            raise ValueError("phase name %r appears twice" % normalized["name"])
        seen.add(normalized["name"])
        added_particulate = phase_particulate_ppm(phase)
        added_molecular = phase_molecular_mg_per_m2(phase)
        running_particulate += added_particulate
        running_molecular += added_molecular
        rows.append(
            {
                "name": normalized["name"],
                "kind": normalized["kind"],
                "added_particulate_ppm": added_particulate,
                "added_molecular_mg_per_m2": added_molecular,
                "cumulative_particulate_ppm": running_particulate,
                "cumulative_molecular_mg_per_m2": running_molecular,
                "particulate_allocation_ppm": normalized["particulate_allocation_ppm"],
                "molecular_allocation_mg_per_m2": normalized[
                    "molecular_allocation_mg_per_m2"
                ],
            }
        )
    return rows


def _within(value, allocation):
    """Return True when a value is inside an allocation within tolerance."""
    if allocation is None:
        return True
    return value < allocation or math.isclose(
        value, allocation, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE
    )


def first_reclean_phase(rows):
    """Return the name of the first phase that breaks its own allocation."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("rows must be a sequence of accumulated phase rows")
    for row in rows:
        if not isinstance(row, dict) or "name" not in row:
            raise ValueError("each row must be a mapping carrying 'name'")
        if not _within(row["added_particulate_ppm"], row["particulate_allocation_ppm"]):
            return row["name"]
        if not _within(
            row["added_molecular_mg_per_m2"], row["molecular_allocation_mg_per_m2"]
        ):
            return row["name"]
    return None


def assess_test_campaign(campaign):
    """Run the full test-campaign contamination assessment.

    campaign keys: phases (sequence of test phases), campaign_particulate_ppm
    (the obscuration the campaign may add), campaign_molecular_mg_per_m2, and
    optionally start_particulate_ppm / start_molecular_mg_per_m2 for an article
    that did not arrive pristine.
    """
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping")
    for key in ("phases", "campaign_particulate_ppm", "campaign_molecular_mg_per_m2"):
        if key not in campaign:
            raise ValueError("campaign missing required key '%s'" % key)
    for key in ("campaign_particulate_ppm", "campaign_molecular_mg_per_m2"):
        value = campaign[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % key)
        if not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("%s must be non-negative and finite" % key)
    start_particulate = float(campaign.get("start_particulate_ppm", 0.0) or 0.0)
    start_molecular = float(campaign.get("start_molecular_mg_per_m2", 0.0) or 0.0)
    if start_particulate < 0.0 or start_molecular < 0.0:
        raise ValueError("starting contamination must not be negative")

    rows = accumulate_campaign(campaign["phases"])
    for row in rows:
        row["cumulative_particulate_ppm"] += start_particulate
        row["cumulative_molecular_mg_per_m2"] += start_molecular

    total_particulate = rows[-1]["cumulative_particulate_ppm"]
    total_molecular = rows[-1]["cumulative_molecular_mg_per_m2"]
    allocation_particulate = float(campaign["campaign_particulate_ppm"])
    allocation_molecular = float(campaign["campaign_molecular_mg_per_m2"])

    findings = []
    for row in rows:
        if not _within(row["added_particulate_ppm"], row["particulate_allocation_ppm"]):
            findings.append(
                "phase %s adds %.5f ppm obscuration against its %.5f ppm allocation"
                % (
                    row["name"],
                    row["added_particulate_ppm"],
                    row["particulate_allocation_ppm"],
                )
            )
        if not _within(
            row["added_molecular_mg_per_m2"], row["molecular_allocation_mg_per_m2"]
        ):
            findings.append(
                "phase %s deposits %.5f mg/m2 against its %.5f mg/m2 allocation"
                % (
                    row["name"],
                    row["added_molecular_mg_per_m2"],
                    row["molecular_allocation_mg_per_m2"],
                )
            )
    if not _within(total_particulate, allocation_particulate):
        findings.append(
            "campaign obscuration %.5f ppm exceeds the %.5f ppm allocation"
            % (total_particulate, allocation_particulate)
        )
    if not _within(total_molecular, allocation_molecular):
        findings.append(
            "campaign deposition %.5f mg/m2 exceeds the %.5f mg/m2 allocation"
            % (total_molecular, allocation_molecular)
        )

    dominant = max(rows, key=lambda row: row["added_particulate_ppm"])
    return {
        "rows": rows,
        "total_particulate_ppm": total_particulate,
        "total_molecular_mg_per_m2": total_molecular,
        "particulate_margin_ppm": allocation_particulate - total_particulate,
        "molecular_margin_mg_per_m2": allocation_molecular - total_molecular,
        "dominant_particulate_phase": dominant["name"],
        "reclean_after_phase": first_reclean_phase(rows),
        "within_budget": not findings,
        "findings": findings,
    }
