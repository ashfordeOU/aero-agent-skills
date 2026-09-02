#!/usr/bin/env python3
"""Key characteristic (KC) identification and variation management logic.

AS9103 (IAQG/SAE) frames key characteristic identification and variation
management for aerospace production. This module implements a deterministic
decision workflow over characteristic records, expressed as a paraphrase of
AS9103 practice, never as a copy of the standard text. The frontmatter
standards id for the skill is the parent QMS standard AS9100 (as9103 is not
yet listed in standards-map.yaml); AS9103 is named in the skill body only.

Units: all tolerances are millimeters (mm). One unit, stated here, so no
conversion is needed.

Module responsibilities:
- classify_characteristic: KC or non-KC verdict with the fired-rule reasons.
- kc_risk_score: 0-100 weighted risk used to rank KCs (default weights, with
  an override weight set allowed).
- rank_key_characteristics: KCs sorted by risk score, high to low.
- variation_management_plan: per-KC control method, Cpk target, sampling
  frequency, and verification gate.
- change_trigger: whether a tooling, process, design, supplier, or personnel
  change revalidates a KC, with the evidence needed.
- produce_kc_report: markdown-ish report lines for a batch of records.

The decision table and the weight set are documented scoring rules; SPC
control-chart and Cpk math are NOT re-implemented here (the
statistical-process-control leaf owns those). This leaf only assigns the Cpk
target that the capability study must demonstrate.
"""

FEATURE_TYPES = (
    "hole",
    "surface",
    "profile",
    "position",
    "thickness",
    "flatness",
    "runout",
    "assembly-mate",
    "electrical",
    "other",
)

DOWNSTREAM_IMPACTS = ("none", "mate", "seal", "balance", "performance")

CHANGE_TYPES = ("tooling", "process", "design", "supplier", "personnel")

# Decision rule thresholds (documented scoring rule, millimeters).
TIGHT_TOLERANCE_MM = 0.1
TIGHT_FEATURE_TYPES = ("position", "profile")
FIT_DOWNSTREAM_IMPACTS = ("mate", "seal", "performance")
FAILURE_THRESHOLD = 2

# Risk score weights; the full set sums to 100 so the score range is 0-100.
# Customer designation gates KC status by rule but carries no weight: a
# customer-designated KC ranks on its measured signals alone.
RISK_WEIGHTS = {
    "safety": 30,
    "fit_function": 25,
    "tight_tolerance": 20,
    "historical": 15,
    "downstream": 10,
}
WEIGHT_KEYS = tuple(RISK_WEIGHTS)

# Cpk targets mirror common aerospace practice: 1.33 default, 1.67 for a
# safety-critical characteristic (stated target only; index math is the
# statistical-process-control leaf's job).
DEFAULT_CPK_TARGET = 1.33
SAFETY_CPK_TARGET = 1.67

CONTROL_METHOD_XBAR_R = "SPC variable chart Xbar-R"
CONTROL_METHOD_ATTRIBUTE = "attribute"
CONTROL_METHOD_100_PERCENT = "100 percent inspection"
CONTROL_METHOD_GAGE_STUDY = "gage study"

# Revalidation trigger table: tooling, process, and design changes revalidate
# a KC; supplier and personnel changes stay in qualification and training
# control unless the controlled process itself changes.
CHANGE_TRIGGER_TABLE = {
    "tooling": True,
    "process": True,
    "design": True,
    "supplier": False,
    "personnel": False,
}

REASON_SAFETY = "safety-critical flag from the product-safety review"
REASON_CUSTOMER = "customer-designated key characteristic"
REASON_NONE = "no decision rule fires: the characteristic is not a key characteristic"

_EVIDENCE_BY_CHANGE = {
    "tooling": [
        "delta FAI scoped to the affected key characteristic per AS9102 change practice",
        "capability re-study: X-bar/R chart in control and Cpk at or above the target",
        "gage verification against the changed tooling",
    ],
    "process": [
        "delta FAI scoped to the affected key characteristic per AS9102 change practice",
        "capability re-study: X-bar/R chart in control and Cpk at or above the target",
        "process parameter record against the approved parameter set",
    ],
    "design": [
        "delta FAI scoped to the affected key characteristic against the revised drawing",
        "re-verify the characteristic against the revised tolerance",
        "capability re-study when the tolerance change alters the achievable spread",
    ],
}

_ACTION_TRUE = (
    "revalidate the key characteristic: delta FAI scoped to the affected "
    "characteristic plus a capability re-study against the Cpk target"
)
_ACTION_KC_NO_TRIGGER = (
    "no capability re-study: supplier and personnel changes stay in "
    "external-provider qualification and training control unless the "
    "controlled process itself changes"
)
_ACTION_NON_KC = (
    "no key-characteristic revalidation applies: the characteristic is not "
    "a key characteristic, routine change control per the QMS covers it"
)

_FREQUENCY_BY_METHOD = {
    CONTROL_METHOD_XBAR_R: "subgroup of 5 at each production lot, first piece at setup",
    CONTROL_METHOD_ATTRIBUTE: "attribute sample per lot per the control plan, every unit after a setup change",
    CONTROL_METHOD_100_PERCENT: "every unit",
    CONTROL_METHOD_GAGE_STUDY: "one-time gage R and R study at the capability baseline and after tooling changes",
}
_GATE_BY_METHOD = {
    CONTROL_METHOD_XBAR_R: "X-bar/R chart in control, Cpk at or above target at the capability re-study",
    CONTROL_METHOD_ATTRIBUTE: "attribute inspection record signed at the in-process gate",
    CONTROL_METHOD_100_PERCENT: "final inspection record on every unit",
    CONTROL_METHOD_GAGE_STUDY: "gage R and R acceptance per the measurement-systems-analysis leaf",
}


def _as_bool(rec, key):
    value = rec.get(key, False)
    if not isinstance(value, bool):
        raise ValueError("%s must be a bool, got %r" % (key, value))
    return value


def _normalize_record(rec):
    """Validate and normalize a characteristic record.

    The record has id (required), name (defaults to id), feature_type (one
    of FEATURE_TYPES), tolerance_mm (non-negative number, millimeters),
    drawing_callout, safety_critical, fit_function_impact,
    customer_designated, process_capability_known (bools, default False),
    downstream_impact (one of DOWNSTREAM_IMPACTS, default 'none'), and
    historical_failures (non-negative int, default 0). Raises ValueError on
    a non-dict record, a missing or non-string id, an unknown feature_type,
    a non-numeric or negative tolerance, a non-bool flag, an unknown
    downstream_impact, or a negative or non-int failure count.
    """
    if not isinstance(rec, dict):
        raise ValueError("characteristic record must be a dict, got %r" % (rec,))
    cid = rec.get("id")
    if not isinstance(cid, str) or not cid:
        raise ValueError("characteristic record needs a non-empty string id")
    name = rec.get("name", cid)
    if not isinstance(name, str) or not name:
        raise ValueError("characteristic name must be a non-empty string")
    ftype = rec.get("feature_type")
    if ftype not in FEATURE_TYPES:
        raise ValueError(
            "unknown feature_type %r; expected one of %s"
            % (ftype, ", ".join(FEATURE_TYPES))
        )
    tol = rec.get("tolerance_mm")
    if isinstance(tol, bool) or not isinstance(tol, (int, float)):
        raise ValueError("tolerance_mm must be a number in millimeters, got %r" % (tol,))
    if tol < 0:
        raise ValueError("tolerance_mm must be non-negative, got %r" % (tol,))
    hist = rec.get("historical_failures", 0)
    if isinstance(hist, bool) or not isinstance(hist, int):
        raise ValueError("historical_failures must be an int, got %r" % (hist,))
    if hist < 0:
        raise ValueError("historical_failures must be non-negative, got %r" % (hist,))
    downstream = rec.get("downstream_impact", "none")
    if downstream not in DOWNSTREAM_IMPACTS:
        raise ValueError(
            "unknown downstream_impact %r; expected one of %s"
            % (downstream, ", ".join(DOWNSTREAM_IMPACTS))
        )
    return {
        "id": cid,
        "name": name,
        "feature_type": ftype,
        "tolerance_mm": tol,
        "drawing_callout": _as_bool(rec, "drawing_callout"),
        "safety_critical": _as_bool(rec, "safety_critical"),
        "fit_function_impact": _as_bool(rec, "fit_function_impact"),
        "customer_designated": _as_bool(rec, "customer_designated"),
        "downstream_impact": downstream,
        "process_capability_known": _as_bool(rec, "process_capability_known"),
        "historical_failures": hist,
    }


def _check_unique_ids(records):
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("characteristic ids must be unique within one batch")


def characteristic_signals(rec):
    """Boolean signal set behind the rules and the risk weights.

    Returns dict with keys safety, customer, fit_function, tight_tolerance,
    historical, downstream. fit_function fires only when fit_function_impact
    is set AND the downstream impact is mate, seal, or performance.
    tight_tolerance fires for a position or profile feature whose tolerance
    is at or below TIGHT_TOLERANCE_MM. downstream fires for any mate, seal,
    or performance downstream impact. historical fires at FAILURE_THRESHOLD
    or more historical failures.
    """
    r = _normalize_record(rec)
    fit_downstream = r["downstream_impact"] in FIT_DOWNSTREAM_IMPACTS
    return {
        "safety": r["safety_critical"],
        "customer": r["customer_designated"],
        "fit_function": r["fit_function_impact"] and fit_downstream,
        "tight_tolerance": (
            r["feature_type"] in TIGHT_FEATURE_TYPES
            and r["tolerance_mm"] <= TIGHT_TOLERANCE_MM
        ),
        "historical": r["historical_failures"] >= FAILURE_THRESHOLD,
        "downstream": fit_downstream,
    }


def classify_characteristic(rec):
    """KC or non-KC verdict with reasons.

    Decision rule table (documented; any single firing rule makes the record
    a key characteristic):
    1. safety_critical flag from the product-safety review;
    2. customer_designated flag;
    3. fit_function_impact AND downstream_impact in (mate, seal,
       performance);
    4. feature_type in (position, profile) AND tolerance_mm at or below
       TIGHT_TOLERANCE_MM (0.1 mm);
    5. historical_failures at or above FAILURE_THRESHOLD (2).

    Returns {"id", "name", "verdict": "KC" | "non-KC", "reasons": [...]}
    with the fired rules in table order, or an explanatory reason for a
    non-KC. Raises ValueError on a malformed record (see
    _normalize_record).
    """
    r = _normalize_record(rec)
    sig = characteristic_signals(r)
    reasons = []
    if sig["safety"]:
        reasons.append(REASON_SAFETY)
    if sig["customer"]:
        reasons.append(REASON_CUSTOMER)
    if sig["fit_function"]:
        reasons.append(
            "fit/function impact with %s downstream impact"
            % r["downstream_impact"]
        )
    if sig["tight_tolerance"]:
        reasons.append(
            "position/profile tolerance of %s mm at or below the tight "
            "tolerance threshold of 0.1 mm" % ("%g" % r["tolerance_mm"])
        )
    if sig["historical"]:
        reasons.append(
            "%d historical failures at or above the failure threshold of 2"
            % r["historical_failures"]
        )
    verdict = "KC" if reasons else "non-KC"
    if not reasons:
        reasons = [REASON_NONE]
    return {"id": r["id"], "name": r["name"], "verdict": verdict, "reasons": reasons}


def _resolve_weights(weights):
    if weights is None:
        return dict(RISK_WEIGHTS)
    if not isinstance(weights, dict):
        raise ValueError("weights must be a dict, got %r" % (weights,))
    for key in weights:
        if key not in WEIGHT_KEYS:
            raise ValueError(
                "unknown weight key %r; expected one of %s"
                % (key, ", ".join(WEIGHT_KEYS))
            )
    merged = dict(RISK_WEIGHTS)
    merged.update(weights)
    for key, value in merged.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("weight %s must be numeric, got %r" % (key, value))
        if value < 0:
            raise ValueError("weight %s must be non-negative, got %r" % (key, value))
    total = sum(merged.values())
    if abs(total - 100.0) > 1e-9:
        raise ValueError(
            "override weights must sum to 100 for a 0-100 score, got %r" % (total,)
        )
    return merged


def kc_risk_score(rec, weights=None):
    """Weighted KC risk score, 0-100, used to rank key characteristics.

    Default weights: safety 30, fit/function 25, tight tolerance 20,
    historical 15, downstream 10 (RISK_WEIGHTS, summing to 100). The
    override weight set replaces entries by key and must also sum to 100;
    unknown keys raise ValueError. The score is the sum of the weights whose
    signal fires, so an all-clear record scores 0 and a record where every
    weighted signal fires scores 100. Customer designation is a status rule
    without a weight and does not move the score. Returns an int for the
    default integer weights, a float otherwise.
    """
    r = _normalize_record(rec)
    sig = characteristic_signals(r)
    merged = _resolve_weights(weights)
    score = sum(merged[key] for key in WEIGHT_KEYS if sig[key])
    if all(isinstance(merged[key], int) for key in WEIGHT_KEYS):
        return int(score)
    return round(float(score), 2)


def rank_key_characteristics(records, weights=None):
    """Key characteristics sorted by risk score, high to low.

    Returns a list of {"id", "name", "score", "reasons"} for the KC verdicts
    only, ordered by score descending with ties broken by id ascending.
    Raises ValueError for an empty list, duplicate ids, or a malformed
    record.
    """
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty list or tuple")
    norms = [_normalize_record(rec) for rec in records]
    _check_unique_ids(norms)
    rows = []
    for r in norms:
        verdict = classify_characteristic(r)
        if verdict["verdict"] != "KC":
            continue
        rows.append(
            {
                "id": r["id"],
                "name": r["name"],
                "score": kc_risk_score(r, weights),
                "reasons": verdict["reasons"],
            }
        )
    rows.sort(key=lambda row: (-row["score"], row["id"]))
    return rows


def _control_method(r):
    """Control method by the documented method rule table, first match wins.

    1. electrical feature: 100 percent inspection (every-unit functional
       test);
    2. assembly-mate feature: attribute (go/no-go fit gage);
    3. two or more historical failures: 100 percent inspection (intensified
       containment after repeated escapes);
    4. capability not yet demonstrated: gage study (measurement system
       study before routine control);
    5. otherwise: SPC variable chart Xbar-R.
    """
    if r["feature_type"] == "electrical":
        return CONTROL_METHOD_100_PERCENT
    if r["feature_type"] == "assembly-mate":
        return CONTROL_METHOD_ATTRIBUTE
    if r["historical_failures"] >= FAILURE_THRESHOLD:
        return CONTROL_METHOD_100_PERCENT
    if not r["process_capability_known"]:
        return CONTROL_METHOD_GAGE_STUDY
    return CONTROL_METHOD_XBAR_R


def variation_management_plan(records):
    """Per-KC variation management plan.

    For every key characteristic in the batch: control method, Cpk target
    (1.67 for a safety-critical characteristic, 1.33 otherwise, mirroring
    common aerospace practice), sampling frequency, and verification gate.
    The plan rows are ordered by risk score descending (ties by id), the
    same ranking the report uses. Non-KC records in the batch are skipped.
    Raises ValueError for an empty list, duplicate ids, or a malformed
    record.
    """
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty list or tuple")
    norms = [_normalize_record(rec) for rec in records]
    _check_unique_ids(norms)
    rows = []
    for r in norms:
        if classify_characteristic(r)["verdict"] != "KC":
            continue
        method = _control_method(r)
        rows.append(
            {
                "id": r["id"],
                "name": r["name"],
                "control_method": method,
                "cpk_target": (
                    SAFETY_CPK_TARGET if r["safety_critical"] else DEFAULT_CPK_TARGET
                ),
                "sampling_frequency": _FREQUENCY_BY_METHOD[method],
                "verification_gate": _GATE_BY_METHOD[method],
            }
        )
    scores = {
        r["id"]: kc_risk_score(r)
        for r in norms
        if classify_characteristic(r)["verdict"] == "KC"
    }
    rows.sort(key=lambda row: (-scores[row["id"]], row["id"]))
    return rows


def change_trigger(rec, change_type):
    """Does a change revalidate the key characteristic?

    Rule table (documented): a tooling, process, or design change revalidates
    a KC (delta FAI scoped to the affected characteristic plus a capability
    re-study); a supplier or personnel change does not, because those route
    to external-provider qualification and training control unless the
    controlled process itself changes. A change never revalidates a non-KC.

    Returns {"id", "name", "change_type", "verdict", "action", "evidence"}
    where evidence lists what the revalidation must produce when the verdict
    is True and is empty otherwise. Raises ValueError for an unknown change
    type or a malformed record.
    """
    r = _normalize_record(rec)
    if change_type not in CHANGE_TYPES:
        raise ValueError(
            "unknown change_type %r; expected one of %s"
            % (change_type, ", ".join(CHANGE_TYPES))
        )
    if classify_characteristic(r)["verdict"] != "KC":
        return {
            "id": r["id"],
            "name": r["name"],
            "change_type": change_type,
            "verdict": False,
            "action": _ACTION_NON_KC,
            "evidence": [],
        }
    if not CHANGE_TRIGGER_TABLE[change_type]:
        return {
            "id": r["id"],
            "name": r["name"],
            "change_type": change_type,
            "verdict": False,
            "action": _ACTION_KC_NO_TRIGGER,
            "evidence": [],
        }
    return {
        "id": r["id"],
        "name": r["name"],
        "change_type": change_type,
        "verdict": True,
        "action": _ACTION_TRUE,
        "evidence": list(_EVIDENCE_BY_CHANGE[change_type]),
    }


def produce_kc_report(records):
    """Markdown-ish report lines for a batch of characteristic records.

    Sections: evaluation summary, the KC list ranked by risk score with
    reasons, the non-KC list with rationale, the variation management plan
    summary with Cpk targets, the KC count, and the revalidation trigger
    table in words. Returns a list of strings, one per line. Raises
    ValueError for an empty list, duplicate ids, or a malformed record.
    """
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty list or tuple")
    norms = [_normalize_record(rec) for rec in records]
    _check_unique_ids(norms)
    verdicts = {r["id"]: classify_characteristic(r) for r in norms}
    kc_rows = rank_key_characteristics(norms)
    plan_rows = variation_management_plan(norms)
    plan_by_id = {row["id"]: row for row in plan_rows}
    non_kc = [v for v in verdicts.values() if v["verdict"] != "KC"]
    kc_count = len(kc_rows)
    lines = [
        "KC report: %d characteristics evaluated, %d key characteristics"
        % (len(norms), kc_count),
        "",
        "Key characteristics, ranked by risk score:",
    ]
    for i, row in enumerate(kc_rows, start=1):
        lines.append(
            "- %d. %s (%s): KC, risk %d/100 - %s"
            % (i, row["id"], row["name"], row["score"], "; ".join(row["reasons"]))
        )
    lines += ["", "Non-key characteristics:"]
    for v in non_kc:
        lines.append(
            "- %s (%s): non-KC - %s" % (v["id"], v["name"], "; ".join(v["reasons"]))
        )
    lines += ["", "Variation management plan summary:"]
    for row in plan_rows:
        lines.append(
            "- %s: %s, Cpk target %g, sampling %s, gate %s"
            % (
                row["id"],
                row["control_method"],
                row["cpk_target"],
                row["sampling_frequency"],
                row["verification_gate"],
            )
        )
    lines += [
        "",
        "Key characteristic count: %d" % kc_count,
        "Revalidation: tooling, process, and design changes trigger KC "
        "revalidation; supplier and personnel changes do not",
    ]
    return lines
