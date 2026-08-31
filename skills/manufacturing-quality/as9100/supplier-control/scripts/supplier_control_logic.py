#!/usr/bin/env python3
"""AS9100 supplier control logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, as9100: gated):
AS9100 clause 8.4 requires the organization to control externally
provided processes, products, and services: evaluate prospective
external providers, define the controls required for each provider
based on risk and criticality, flow down the applicable requirements
(including customer, regulatory, and special requirements), monitor
and periodically re-evaluate provider performance, and maintain an
approved supplier list. This module implements the risk classification,
the derived control set, record completeness, and the approval verdict.

Supplier risk class rule (documented, applied in order):
1. part_criticality == 'critical'      -> 'critical' (criticality drives
   the class; history cannot downgrade a critical part's supplier).
2. part_criticality == 'major':
     quality_history_score < 70 or
     delivery_history_score < 70       -> 'high'
     otherwise                         -> 'medium'
3. part_criticality == 'standard':
     both history scores >= 90         -> 'low'
     both history scores >= 70         -> 'medium'
     otherwise                         -> 'high'

Required controls by risk class (documented table):
  risk_class | on_site_audit | monitoring_frequency | delegated_verification_allowed | flow_down_required
  -----------+---------------+----------------------+-------------------------------+-------------------
  critical   | True          | quarterly            | False                         | True
  high       | True          | semi-annual          | False                         | True
  medium     | False         | annual               | True                          | True
  low        | False         | biennial             | True                          | True

Flow-down of requirements applies to every externally provided item
(flow_down_required is True for all classes); the risk class scales the
depth of verification and the monitoring frequency instead. Delegated
verification (letting the provider verify its own output) is allowed only
for medium and low risk providers.
"""

PART_CRITICALITY_LEVELS = frozenset({"critical", "major", "standard"})

RISK_CLASSES = frozenset({"critical", "high", "medium", "low"})

# Checks a complete supplier record must cover, per 8.4 practice:
# initial evaluation, approved supplier list membership, performance
# monitoring, periodic re-evaluation, and flowed-down requirements.
RECORD_CHECKS = (
    "evaluation",
    "approved_list",
    "monitoring",
    "reevaluation",
    "flow_down",
)

MONITORING_FREQUENCIES = {
    "critical": "quarterly",
    "high": "semi-annual",
    "medium": "annual",
    "low": "biennial",
}


def _validate_score(score, name):
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, score))
    if not 0 <= score <= 100:
        raise ValueError("%s must be in 0..100, got %r" % (name, score))


def supplier_risk_class(part_criticality, quality_history_score, delivery_history_score):
    """Classify the supplier risk from part criticality and history.

    Args:
        part_criticality: critical, major, or standard.
        quality_history_score: 0..100 quality score (higher is better).
        delivery_history_score: 0..100 delivery score (higher is better).

    Returns 'critical', 'high', 'medium', or 'low' per the documented
    rule table in the module docstring: criticality drives the class,
    history adjusts it within the major and standard levels.
    """
    if part_criticality not in PART_CRITICALITY_LEVELS:
        raise ValueError(
            "unknown part criticality: %r (expected one of %s)"
            % (part_criticality, ", ".join(sorted(PART_CRITICALITY_LEVELS)))
        )
    _validate_score(quality_history_score, "quality_history_score")
    _validate_score(delivery_history_score, "delivery_history_score")
    if part_criticality == "critical":
        return "critical"
    if part_criticality == "major":
        if quality_history_score < 70 or delivery_history_score < 70:
            return "high"
        return "medium"
    # standard
    if quality_history_score >= 90 and delivery_history_score >= 90:
        return "low"
    if quality_history_score >= 70 and delivery_history_score >= 70:
        return "medium"
    return "high"


def required_controls(risk_class):
    """Return the required controls dict for a supplier risk class.

    The table is documented in the module docstring. Controls are:
    on_site_audit (bool), monitoring_frequency, delegated_verification_allowed
    (bool), and flow_down_required (bool). Flow-down is required for every
    class; on-site audit and monitoring frequency scale with risk.
    """
    if risk_class not in RISK_CLASSES:
        raise ValueError(
            "unknown risk class: %r (expected one of %s)"
            % (risk_class, ", ".join(sorted(RISK_CLASSES)))
        )
    return {
        "on_site_audit": risk_class in ("critical", "high"),
        "monitoring_frequency": MONITORING_FREQUENCIES[risk_class],
        "delegated_verification_allowed": risk_class in ("medium", "low"),
        "flow_down_required": True,
    }


def supplier_record_complete(
    evaluation, approved_list, monitoring, reevaluation, flow_down
):
    """A supplier record is complete only when all five 8.4 checks hold:
    initial evaluation, approved supplier list membership, performance
    monitoring, periodic re-evaluation, and flowed-down requirements."""
    checks = {
        "evaluation": bool(evaluation),
        "approved_list": bool(approved_list),
        "monitoring": bool(monitoring),
        "reevaluation": bool(reevaluation),
        "flow_down": bool(flow_down),
    }
    missing = [name for name in RECORD_CHECKS if not checks[name]]
    return {
        "checks": sum(checks.values()),
        "total": len(checks),
        "complete": not missing,
        "missing": missing,
    }


def approval_verdict(record, risk_class):
    """Approve a supplier from its record completeness and risk class.

    A complete record approves the supplier; the critical class returns
    'approved-critical' to flag the heightened control set (on-site audit,
    quarterly monitoring). An incomplete record is 'not-approved'.
    """
    if risk_class not in RISK_CLASSES:
        raise ValueError(
            "unknown risk class: %r (expected one of %s)"
            % (risk_class, ", ".join(sorted(RISK_CLASSES)))
        )
    if not record["complete"]:
        return "not-approved"
    if risk_class == "critical":
        return "approved-critical"
    return "approved"


def supplier_control_summary(
    part_criticality,
    quality_history_score,
    delivery_history_score,
    evaluation=True,
    approved_list=True,
    monitoring=True,
    reevaluation=True,
    flow_down=True,
):
    """Convenience: run the full supplier control pipeline and summarize it."""
    risk_class = supplier_risk_class(
        part_criticality, quality_history_score, delivery_history_score
    )
    record = supplier_record_complete(
        evaluation, approved_list, monitoring, reevaluation, flow_down
    )
    return {
        "risk_class": risk_class,
        "controls": required_controls(risk_class),
        "record": record,
        "verdict": approval_verdict(record, risk_class),
    }
