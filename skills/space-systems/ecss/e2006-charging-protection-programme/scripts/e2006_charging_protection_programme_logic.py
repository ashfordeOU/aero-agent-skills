"""ECSS-E-ST-20-06C clause 5 -- charging protection programme.

Offline, deterministic, stdlib-only implementation of the programme
that clause 5 requires: an early charging-hazard assessment, a
mitigation plan derived from it, and closure of that plan through
measurement, inspection, testing and analysis activities booked against
project-review milestones.

The module provides:

  * a hazard index built from the orbital-environment severity, the
    surface-exposure kind and the exposed area of each item;
  * a risk categorization of that index into negligible, low,
    significant or severe bands;
  * the mitigation measures and the verification-method set each band
    demands, plus a coverage check of what a plan actually declares;
  * the latest acceptable project review for each programme activity
    and a schedule check of the planned milestone against it;
  * an aggregate programme report that is compliant only when no
    finding is open.

Boundary handling: a hazard index that lands exactly on a band edge
belongs to the higher band, and the comparison absorbs floating-point
representation error rather than moving the edge.

No verbatim standard text is reproduced; the clause is cited as the
anchor of the procedure only.
"""

import math

__all__ = [
    "ENVIRONMENT_SEVERITY",
    "EXPOSURE_FACTOR",
    "RISK_BANDS",
    "MITIGATION_MEASURES",
    "VERIFICATION_METHODS",
    "PROJECT_REVIEWS",
    "hazard_index",
    "categorize_risk",
    "assess_item_hazard",
    "required_mitigation_measures",
    "required_verification_methods",
    "check_mitigation_coverage",
    "check_verification_coverage",
    "required_milestone",
    "check_schedule",
    "build_protection_programme",
]

# Severity of the charging drivers of an orbital environment.
ENVIRONMENT_SEVERITY = {
    "geostationary": 1.0,
    "geostationary-transfer": 0.85,
    "medium-earth-orbit": 0.80,
    "high-inclination-low-earth-orbit": 0.60,
    "equatorial-low-earth-orbit": 0.20,
    "interplanetary": 0.50,
}

# How exposed an item is to the accumulating surface charge.
EXPOSURE_FACTOR = {
    "exposed-dielectric": 1.00,
    "floating-conductor": 0.90,
    "solar-array-coverglass": 0.80,
    "thermal-blanket-outer-layer": 0.75,
    "grounded-conductor": 0.30,
    "shielded-internal-harness": 0.20,
}

# Lower edge of each risk band on the hazard index.
RISK_BANDS = (
    ("severe", 0.75),
    ("significant", 0.50),
    ("low", 0.25),
    ("negligible", 0.0),
)

MITIGATION_MEASURES = {
    "conductive-surface-treatment",
    "grounding-and-bonding",
    "shielding-or-filtering",
    "layout-separation",
    "operational-constraint",
}

VERIFICATION_METHODS = {"analysis", "inspection", "test", "measurement"}

_REQUIRED_MITIGATION = {
    "severe": ("conductive-surface-treatment", "grounding-and-bonding",
               "shielding-or-filtering"),
    "significant": ("conductive-surface-treatment", "grounding-and-bonding"),
    "low": ("grounding-and-bonding",),
    "negligible": (),
}

_REQUIRED_VERIFICATION = {
    "severe": ("analysis", "inspection", "test", "measurement"),
    "significant": ("analysis", "inspection", "test"),
    "low": ("analysis", "inspection"),
    "negligible": ("analysis",),
}

# Project reviews in chronological order.
PROJECT_REVIEWS = ("SRR", "PDR", "CDR", "QR", "AR", "FRR")

# Latest acceptable review per programme activity and risk band.
_ACTIVITY_MILESTONES = {
    "hazard-assessment": {
        "severe": "SRR", "significant": "PDR", "low": "PDR",
        "negligible": "PDR",
    },
    "mitigation-plan": {
        "severe": "PDR", "significant": "CDR", "low": "CDR",
        "negligible": "CDR",
    },
    "verification-closure": {
        "severe": "QR", "significant": "QR", "low": "AR",
        "negligible": "AR",
    },
}

BOUNDARY_REL_TOL = 1e-12
BOUNDARY_ABS_TOL = 1e-12


def _at_or_above(value, edge):
    """True when value is at or above edge, absorbing float error."""
    if value >= edge:
        return True
    return math.isclose(value, edge, rel_tol=BOUNDARY_REL_TOL,
                        abs_tol=BOUNDARY_ABS_TOL)


def _require_positive_area(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("exposed_area_m2 must be a real number, got %r"
                         % (value,))
    area = float(value)
    if math.isnan(area) or math.isinf(area):
        raise ValueError("exposed_area_m2 must be finite, got %r" % (value,))
    if area <= 0.0:
        raise ValueError("exposed_area_m2 must be > 0, got %r" % (value,))
    return area


def _lookup(table, key, label):
    if not isinstance(key, str):
        raise ValueError("%s must be a string, got %r" % (label, key))
    if key not in table:
        raise ValueError(
            "uncategorized %s %r; known values: %s"
            % (label, key, ", ".join(sorted(table)))
        )
    return table[key]


def hazard_index(environment, exposure, exposed_area_m2):
    """Dimensionless charging-hazard index in the range 0 to 1.

    Environment severity times exposure factor times an area factor
    that saturates at one square metre of exposed surface.
    """
    severity = _lookup(ENVIRONMENT_SEVERITY, environment, "environment")
    factor = _lookup(EXPOSURE_FACTOR, exposure, "exposure kind")
    area = _require_positive_area(exposed_area_m2)
    area_factor = min(1.0, 0.40 + 0.60 * math.sqrt(area))
    return severity * factor * area_factor


def categorize_risk(index):
    """Categorize a hazard index into a risk band."""
    if isinstance(index, bool) or not isinstance(index, (int, float)):
        raise ValueError("hazard index must be a real number, got %r"
                         % (index,))
    value = float(index)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("hazard index must be finite, got %r" % (index,))
    if value < 0.0 or value > 1.0:
        raise ValueError("hazard index must lie in [0, 1], got %r" % (index,))
    for band, edge in RISK_BANDS:
        if _at_or_above(value, edge):
            return band
    return "negligible"


def assess_item_hazard(item):
    """Score one programme item and categorize its charging risk."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("name", "environment", "exposure", "exposed_area_m2"):
        if key not in item:
            raise ValueError("item missing required key %r" % key)
    index = hazard_index(item["environment"], item["exposure"],
                         item["exposed_area_m2"])
    return {
        "name": str(item["name"]),
        "environment": item["environment"],
        "exposure": item["exposure"],
        "hazard_index": index,
        "risk": categorize_risk(index),
    }


def required_mitigation_measures(risk):
    """Mitigation measures a risk band demands."""
    return tuple(_lookup(_REQUIRED_MITIGATION, risk, "risk band"))


def required_verification_methods(risk):
    """Verification methods a risk band demands."""
    return tuple(_lookup(_REQUIRED_VERIFICATION, risk, "risk band"))


def check_mitigation_coverage(risk, declared_measures):
    """Compare declared mitigation measures against the demanded set."""
    required = set(required_mitigation_measures(risk))
    if not isinstance(declared_measures, (list, tuple, set, frozenset)):
        raise ValueError("declared measures must be a sequence or set")
    declared = set()
    for measure in declared_measures:
        if measure not in MITIGATION_MEASURES:
            raise ValueError(
                "uncategorized mitigation measure %r; known measures: %s"
                % (measure, ", ".join(sorted(MITIGATION_MEASURES)))
            )
        declared.add(measure)
    missing = sorted(required - declared)
    return {
        "risk": risk,
        "required": sorted(required),
        "declared": sorted(declared),
        "missing": missing,
        "covered": not missing,
    }


def check_verification_coverage(risk, declared_methods):
    """Compare declared verification methods against the demanded set."""
    required = set(required_verification_methods(risk))
    if not isinstance(declared_methods, (list, tuple, set, frozenset)):
        raise ValueError("declared methods must be a sequence or set")
    declared = set()
    for method in declared_methods:
        if method not in VERIFICATION_METHODS:
            raise ValueError(
                "uncategorized verification method %r; known methods: %s"
                % (method, ", ".join(sorted(VERIFICATION_METHODS)))
            )
        declared.add(method)
    missing = sorted(required - declared)
    return {
        "risk": risk,
        "required": sorted(required),
        "declared": sorted(declared),
        "missing": missing,
        "covered": not missing,
    }


def required_milestone(activity, risk):
    """Latest acceptable project review for a programme activity."""
    table = _lookup(_ACTIVITY_MILESTONES, activity, "programme activity")
    return _lookup(table, risk, "risk band")


def check_schedule(activity, risk, planned_review):
    """Check a planned review against the latest acceptable one."""
    if not isinstance(planned_review, str):
        raise ValueError("planned review must be a string, got %r"
                         % (planned_review,))
    if planned_review not in PROJECT_REVIEWS:
        raise ValueError(
            "uncategorized project review %r; known reviews: %s"
            % (planned_review, ", ".join(PROJECT_REVIEWS))
        )
    latest = required_milestone(activity, risk)
    on_time = PROJECT_REVIEWS.index(planned_review) <= \
        PROJECT_REVIEWS.index(latest)
    return {
        "activity": activity,
        "risk": risk,
        "planned": planned_review,
        "latest_acceptable": latest,
        "on_time": on_time,
    }


def build_protection_programme(items, plan):
    """Aggregate the clause 5 protection programme over every item.

    items: list of item mappings (name, environment, exposure,
      exposed_area_m2).
    plan: mapping of item name -> {'measures': [...], 'methods': [...],
      'schedule': {activity: review}}.
    """
    entries = list(items)
    if not entries:
        raise ValueError("item inventory must not be empty")
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of item name -> entry")

    assessed = []
    findings = []
    seen = set()
    for item in entries:
        hazard = assess_item_hazard(item)
        if hazard["name"] in seen:
            raise ValueError("duplicate item name %r" % hazard["name"])
        seen.add(hazard["name"])

        entry = plan.get(hazard["name"])
        if entry is None:
            findings.append(
                "%s carries a %s charging risk with no entry in the "
                "protection plan" % (hazard["name"], hazard["risk"])
            )
            hazard["mitigation"] = None
            hazard["verification"] = None
            hazard["schedule"] = []
            assessed.append(hazard)
            continue
        if not isinstance(entry, dict):
            raise ValueError("plan entry for %r must be a mapping"
                             % hazard["name"])

        mitigation = check_mitigation_coverage(
            hazard["risk"], entry.get("measures", []))
        if not mitigation["covered"]:
            findings.append(
                "%s is missing the mitigation measures %s required by its "
                "%s charging risk"
                % (hazard["name"], ", ".join(mitigation["missing"]),
                   hazard["risk"])
            )

        verification = check_verification_coverage(
            hazard["risk"], entry.get("methods", []))
        if not verification["covered"]:
            findings.append(
                "%s is missing the verification methods %s required by its "
                "%s charging risk"
                % (hazard["name"], ", ".join(verification["missing"]),
                   hazard["risk"])
            )

        schedule = entry.get("schedule", {})
        if not isinstance(schedule, dict):
            raise ValueError("schedule for %r must be a mapping"
                             % hazard["name"])
        schedule_results = []
        for activity in sorted(_ACTIVITY_MILESTONES):
            planned = schedule.get(activity)
            if planned is None:
                findings.append(
                    "%s has no planned review for the %s activity"
                    % (hazard["name"], activity)
                )
                continue
            result = check_schedule(activity, hazard["risk"], planned)
            schedule_results.append(result)
            if not result["on_time"]:
                findings.append(
                    "%s books %s at %s, later than the %s required by its "
                    "%s charging risk"
                    % (hazard["name"], activity, result["planned"],
                       result["latest_acceptable"], hazard["risk"])
                )

        hazard["mitigation"] = mitigation
        hazard["verification"] = verification
        hazard["schedule"] = schedule_results
        assessed.append(hazard)

    return {
        "items": assessed,
        "findings": findings,
        "compliant": not findings,
    }
