"""MSG-3 scheduled maintenance decision logic (pure stdlib, deterministic).

Applies the ATA MSG-3 maintenance steering group decision logic as a
deterministic rule table, paraphrased, never reproducing MSG-3 text or
worksheets: categorize each failure mode by effect visibility (evident
to the flight crew or hidden) and consequence (safety-significant or
economic-only), select the applicable scheduled maintenance task
categories, and assign the interval verdict including the hidden
failure exposure rule.

Each failure mode record is a dict with the keys:
    failure_id (str), function (str), failure_effect (str),
    evident (bool), safety_significant (bool), hidden_safety (bool),
    maintenance_opportunity_interval (float, flight hours),
    single_failure_interval (float, flight hours).
Evident records may also carry task_interval (float, flight hours), the
manufacturer-recommended scheduled maintenance task interval.

Category resolution is total: for a hidden failure any safety concern
(hidden_safety or safety_significant) yields category 5-hidden-safety,
because a safety-marked hidden failure always ranks above the economic
hidden category. An evident failure is judged on safety_significant
alone; hidden_safety is notional for an evident item and does not move
the category. A hidden record with safety_significant True is therefore
still categorized 5-hidden-safety (direct safety consequence while
undetected), never 6-hidden-economic.

ValueError guards: a record missing any required key, a negative
single_failure_interval, a non-positive maintenance_opportunity_interval
on a hidden item, or a negative task_interval.
"""

TASK_CATEGORIES = ["LU", "SV", "OP", "VC", "IN", "FC", "RS", "DS"]
# Lubrication, servicing, operational check, visual check, inspection,
# functional check, restoration, discard.

HIDDEN_EXPOSURE_FACTOR = 0.5
# Hidden failures must be detected within half the exposure time to a
# second independent failure.

REQUIRED_KEYS = (
    "failure_id",
    "function",
    "failure_effect",
    "evident",
    "safety_significant",
    "hidden_safety",
    "maintenance_opportunity_interval",
    "single_failure_interval",
)

CATEGORY_RATIONALE = {
    "5-hidden-safety": (
        "hidden failure whose undetected combination with a second "
        "failure can reach a safety consequence"
    ),
    "6-hidden-economic": (
        "hidden failure with economic or operational effect only, no "
        "safety consequence in the undetected state"
    ),
    "7-evident-safety": (
        "evident failure with a direct safety effect on the operating "
        "crew or vehicle"
    ),
    "8-evident-economic": (
        "evident failure with economic or operational effect only"
    ),
}

_DETECTION_TASKS = ("FC", "IN", "VC")


def _validate_record(record):
    """Check the record keys and physical interval values."""
    if not isinstance(record, dict):
        raise ValueError("msg3 record must be a dict")
    for key in REQUIRED_KEYS:
        if key not in record:
            raise ValueError("msg3 record missing required key: " + key)
    if record["single_failure_interval"] < 0.0:
        raise ValueError(
            "single_failure_interval must be >= 0, got "
            + str(record["single_failure_interval"])
        )
    if not record["evident"] and record["maintenance_opportunity_interval"] <= 0.0:
        raise ValueError(
            "maintenance_opportunity_interval must be > 0 on a hidden "
            "failure item"
        )
    if (
        "task_interval" in record
        and record["task_interval"] is not None
        and record["task_interval"] < 0.0
    ):
        raise ValueError(
            "task_interval must be >= 0, got " + str(record["task_interval"])
        )


def classify_failure(record):
    """Categorize one failure mode record under the MSG-3 top branch.

    Returns a dict with failure_id, category, evident,
    safety_significant, hidden_safety and a non-empty rationale string.
    """
    _validate_record(record)
    failure_id = record["failure_id"]
    evident = bool(record["evident"])
    safety = bool(record["safety_significant"])
    hidden = bool(record["hidden_safety"])
    if not evident:
        if hidden or safety:
            category = "5-hidden-safety"
        else:
            category = "6-hidden-economic"
    else:
        if safety:
            category = "7-evident-safety"
        else:
            category = "8-evident-economic"
    rationale = (
        failure_id
        + " ("
        + str(record["function"])
        + "): "
        + str(record["failure_effect"])
        + "; "
        + CATEGORY_RATIONALE[category]
        + "."
    )
    return {
        "failure_id": failure_id,
        "category": category,
        "evident": evident,
        "safety_significant": safety,
        "hidden_safety": hidden,
        "rationale": rationale,
    }


def select_tasks(classification, applicable_hidden=True):
    """Select the scheduled maintenance task categories for a category.

    applicable_hidden asserts that an inspection or functional check
    exists that can reveal the hidden function (used only by category
    6-hidden-economic, where a check-less hidden item falls back to a
    visual check). Returns a dict with failure_id, category,
    task_categories (ordered, highest-value first) and a non-empty
    rationale string.
    """
    category = classification["category"]
    failure_id = classification["failure_id"]
    if category == "5-hidden-safety":
        tasks = ["FC", "IN", "VC"]
        rationale = (
            failure_id
            + ": reveal the hidden failure with a functional check, "
            "inspection or visual check before the exposure limit; a "
            "lubrication or servicing task alone is never sufficient."
        )
    elif category == "6-hidden-economic":
        if applicable_hidden:
            tasks = ["FC", "IN"]
            rationale = (
                failure_id
                + ": the item has a hidden function, so a functional "
                "check or inspection can reveal the failure on economic "
                "grounds."
            )
        else:
            tasks = ["VC"]
            rationale = (
                failure_id
                + ": no functional check applies to this hidden item, so "
                "only a visual check can reveal the failure."
            )
    elif category == "7-evident-safety":
        tasks = ["IN", "FC", "RS", "DS"]
        rationale = (
            failure_id
            + ": preventive tasks (inspection, functional check, "
            "restoration, discard) reduce the probability of the direct "
            "safety effect."
        )
    else:  # "8-evident-economic"
        tasks = ["VC", "IN", "FC", "RS", "DS"]
        rationale = (
            failure_id
            + ": evident economic failure, so the lowest-cost applicable "
            "task set is scheduled on economic grounds."
        )
    return {
        "failure_id": failure_id,
        "category": category,
        "task_categories": tasks,
        "rationale": rationale,
    }


def interval_verdict(record, classification, task_categories):
    """Return the interval verdict for a record and its task selection.

    For a hidden failure with a detection task (FC, IN or VC) selected,
    the exposure rule applies: the detection interval, taken as the
    maintenance opportunity interval, must be <= HIDDEN_EXPOSURE_FACTOR
    times the single-failure interval. When the opportunity exceeds the
    exposure limit the verdict is interval-too-long and the recommended
    interval is the exposure limit; otherwise interval-ok.

    An evident record with no detection task compares the opportunity
    interval against the manufacturer task_interval when provided;
    without task_interval the verdict is interval-not-scoped. Returns a
    dict with failure_id, exposure_limit (None when the rule does not
    bind), opportunity_interval, verdict and recommended_interval (None
    when no change is required).
    """
    _validate_record(record)
    failure_id = classification["failure_id"]
    opportunity = float(record["maintenance_opportunity_interval"])
    hidden = not bool(record["evident"])
    detection = [t for t in task_categories if t in _DETECTION_TASKS]
    if hidden and detection:
        single = float(record["single_failure_interval"])
        exposure_limit = HIDDEN_EXPOSURE_FACTOR * single
        if opportunity > exposure_limit:
            return {
                "failure_id": failure_id,
                "exposure_limit": exposure_limit,
                "opportunity_interval": opportunity,
                "verdict": "interval-too-long",
                "recommended_interval": exposure_limit,
            }
        return {
            "failure_id": failure_id,
            "exposure_limit": exposure_limit,
            "opportunity_interval": opportunity,
            "verdict": "interval-ok",
            "recommended_interval": None,
        }
    if hidden and not detection:
        return {
            "failure_id": failure_id,
            "exposure_limit": None,
            "opportunity_interval": opportunity,
            "verdict": "interval-not-scoped",
            "recommended_interval": None,
        }
    if "task_interval" in record and record["task_interval"] is not None:
        task_interval = float(record["task_interval"])
        if opportunity > task_interval:
            return {
                "failure_id": failure_id,
                "exposure_limit": None,
                "opportunity_interval": opportunity,
                "verdict": "interval-too-long",
                "recommended_interval": task_interval,
            }
        return {
            "failure_id": failure_id,
            "exposure_limit": None,
            "opportunity_interval": opportunity,
            "verdict": "interval-ok",
            "recommended_interval": None,
        }
    return {
        "failure_id": failure_id,
        "exposure_limit": None,
        "opportunity_interval": opportunity,
        "verdict": "interval-not-scoped",
        "recommended_interval": None,
    }


def run_msg3_analysis(records):
    """Run classify, select and verdict over every record.

    Returns {"results": [...], "summary": {...}} where each result
    carries the category, classification rationale, selected task
    categories, task rationale and interval verdict fields, and the
    summary counts total, hidden_count, safety_significant_count and
    interval_too_long_count over the input records.
    """
    results = []
    for record in records:
        cls = classify_failure(record)
        tasks = select_tasks(cls)
        verdict = interval_verdict(record, cls, tasks["task_categories"])
        results.append(
            {
                "failure_id": cls["failure_id"],
                "category": cls["category"],
                "classification_rationale": cls["rationale"],
                "task_categories": tasks["task_categories"],
                "task_rationale": tasks["rationale"],
                "verdict": verdict["verdict"],
                "exposure_limit": verdict["exposure_limit"],
                "opportunity_interval": verdict["opportunity_interval"],
                "recommended_interval": verdict["recommended_interval"],
            }
        )
    total = len(results)
    hidden_count = sum(1 for r in records if not bool(r["evident"]))
    safety_count = sum(1 for r in records if bool(r["safety_significant"]))
    too_long_count = sum(1 for r in results if r["verdict"] == "interval-too-long")
    summary = {
        "total": total,
        "hidden_count": hidden_count,
        "safety_significant_count": safety_count,
        "interval_too_long_count": too_long_count,
    }
    return {"results": results, "summary": summary}
