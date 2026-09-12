"""
ECSS-E-ST-32C Annex P — Test Evaluation (TE DRD) logic.

Deterministic, offline, stdlib only. Implements objective assessment,
prediction-vs-measurement comparison, anomaly disposition evaluation,
post-test article condition assessment, and overall evaluation determination.
"""

OBJECTIVE_STATUSES = {"met", "not_met", "partial"}
ANOMALY_DISPOSITIONS = {"resolved", "waived", "open"}
ARTICLE_CONDITIONS = {"acceptable", "conditional", "not_acceptable"}


def evaluate_test_objective(objective_id, status):
    """
    Assess a single test objective.

    Returns a dict with keys: objective_id, status, met (bool).
    Raises ValueError for an unrecognised status.
    """
    if not isinstance(objective_id, str) or not objective_id:
        raise ValueError("objective_id must be a non-empty string")
    if status not in OBJECTIVE_STATUSES:
        raise ValueError(
            f"Unknown objective status '{status}' for '{objective_id}'. "
            f"Expected one of {sorted(OBJECTIVE_STATUSES)}."
        )
    return {
        "objective_id": objective_id,
        "status": status,
        "met": status == "met",
    }


def assess_result_vs_prediction(parameter, measured, predicted, tolerance_fraction):
    """
    Compare a measured response value to its predicted value.

    tolerance_fraction: allowed relative deviation (e.g. 0.05 for ±5 %).
    When predicted is zero, assessment is within-prediction only if
    measured is also zero.

    Returns a dict with: parameter, measured, predicted, tolerance_fraction,
    relative_error, assessment ("within_prediction" | "outside_prediction").
    Raises ValueError for negative tolerance or non-numeric inputs.
    """
    for label, val in (("measured", measured), ("predicted", predicted),
                       ("tolerance_fraction", tolerance_fraction)):
        if not isinstance(val, (int, float)):
            raise ValueError(f"'{label}' must be numeric, got {type(val).__name__}")
    if tolerance_fraction < 0:
        raise ValueError("tolerance_fraction must be non-negative")

    if predicted == 0:
        relative_error = 0.0 if measured == 0 else float("inf")
        within = measured == 0
    else:
        relative_error = abs(measured - predicted) / abs(predicted)
        within = relative_error <= tolerance_fraction

    return {
        "parameter": parameter,
        "measured": measured,
        "predicted": predicted,
        "tolerance_fraction": tolerance_fraction,
        "relative_error": relative_error,
        "assessment": "within_prediction" if within else "outside_prediction",
    }


def evaluate_anomaly(anomaly_id, disposition):
    """
    Record the disposition of a test anomaly.

    Returns a dict with: anomaly_id, disposition, blocking (bool).
    An open anomaly is blocking; resolved and waived are not.
    Raises ValueError for an unrecognised disposition.
    """
    if not isinstance(anomaly_id, str) or not anomaly_id:
        raise ValueError("anomaly_id must be a non-empty string")
    if disposition not in ANOMALY_DISPOSITIONS:
        raise ValueError(
            f"Unknown anomaly disposition '{disposition}' for '{anomaly_id}'. "
            f"Expected one of {sorted(ANOMALY_DISPOSITIONS)}."
        )
    return {
        "anomaly_id": anomaly_id,
        "disposition": disposition,
        "blocking": disposition == "open",
    }


def assess_article_condition(article_id, condition):
    """
    Record the post-test condition of a test article.

    Returns a dict with: article_id, condition, acceptable (bool).
    "acceptable" and "conditional" are both acceptable; "not_acceptable" blocks.
    Raises ValueError for an unrecognised condition.
    """
    if not isinstance(article_id, str) or not article_id:
        raise ValueError("article_id must be a non-empty string")
    if condition not in ARTICLE_CONDITIONS:
        raise ValueError(
            f"Unknown article condition '{condition}' for '{article_id}'. "
            f"Expected one of {sorted(ARTICLE_CONDITIONS)}."
        )
    return {
        "article_id": article_id,
        "condition": condition,
        "acceptable": condition in {"acceptable", "conditional"},
    }


def determine_overall_evaluation(objectives, result_assessments,
                                 anomalies, article_conditions):
    """
    Derive the overall test evaluation status from the four input lists.

    Each list element must be the dict returned by the corresponding
    helper function above.

    Returns a dict with:
      overall_status:                   "accepted" | "rejected"
      findings:                         list of descriptive finding strings
      objectives_count:                 total objectives assessed
      objectives_met_count:             objectives with status "met"
      anomalies_count:                  total anomalies recorded
      open_anomalies_count:             blocking anomalies
      results_count:                    total result comparisons
      results_within_prediction_count:  within-prediction count
      results_outside_prediction_count: outside-prediction count
      articles_count:                   total articles assessed
      articles_not_acceptable_count:    not-acceptable articles
    """
    findings = []

    objectives_not_met = [o for o in objectives if not o["met"]]
    if objectives_not_met:
        ids = [o["objective_id"] for o in objectives_not_met]
        findings.append(f"Objectives not met: {ids}")

    outside = [r for r in result_assessments if r["assessment"] == "outside_prediction"]
    if outside:
        params = [r["parameter"] for r in outside]
        findings.append(f"Results outside prediction: {params}")

    blocking = [a for a in anomalies if a["blocking"]]
    if blocking:
        ids = [a["anomaly_id"] for a in blocking]
        findings.append(f"Open anomalies blocking acceptance: {ids}")

    not_acceptable = [c for c in article_conditions if not c["acceptable"]]
    if not_acceptable:
        ids = [c["article_id"] for c in not_acceptable]
        findings.append(f"Test articles in not-acceptable condition: {ids}")

    return {
        "overall_status": "accepted" if not findings else "rejected",
        "findings": findings,
        "objectives_count": len(objectives),
        "objectives_met_count": len([o for o in objectives if o["met"]]),
        "anomalies_count": len(anomalies),
        "open_anomalies_count": len(blocking),
        "results_count": len(result_assessments),
        "results_within_prediction_count": len(result_assessments) - len(outside),
        "results_outside_prediction_count": len(outside),
        "articles_count": len(article_conditions),
        "articles_not_acceptable_count": len(not_acceptable),
    }
