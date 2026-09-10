#!/usr/bin/env python3
"""ECSS-E-ST-10-03C clause 4.4.3 measurement uncertainty vs. test margin
logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
measurement uncertainty of the test facility/instrumentation must be
accounted for whenever a test result is used to demonstrate a margin;
Table 4-2 gives typical uncertainty values, by parameter type, to use
as a default when the project has not characterized its own
facility/instrumentation uncertainty. This module implements the
uncertainty-resolution, effective-margin, adequacy, and
typical-value-flagging logic; it does not implement the allowable
test input tolerance (clause 4.4.2, see the sibling
e1003-input-tolerances leaf) or the margin objectives a campaign must
demonstrate (clause 4.5, see the sibling e1003-objectives leaf).
"""

DEFAULT_TYPICAL_UNCERTAINTY = {
    "temperature": 2.0,
    "vibration": 10.0,
    "acoustic": 1.0,
    "pressure": 5.0,
    "mass": 1.0,
    "electrical": 5.0,
}


def typical_uncertainty(parameter_type, table=None):
    """Table 4-2 style typical measurement uncertainty for one parameter
    type. table optionally overrides/extends DEFAULT_TYPICAL_UNCERTAINTY
    for this lookup only (does not mutate the module default). Raises
    ValueError when parameter_type is not in the effective table."""
    effective = dict(DEFAULT_TYPICAL_UNCERTAINTY)
    if table:
        effective.update(table)
    if parameter_type not in effective:
        raise ValueError("unknown parameter type: %r" % (parameter_type,))
    return effective[parameter_type]


def resolve_uncertainty(parameter_type, measured_uncertainty=None, table=None):
    """Uncertainty value to apply for one parameter type: the project's
    own measured/characterized uncertainty when supplied, otherwise the
    Table 4-2 typical value for that parameter type."""
    if measured_uncertainty is not None:
        return measured_uncertainty
    return typical_uncertainty(parameter_type, table)


def effective_margin(demonstrated_margin, uncertainty):
    """Margin that remains once measurement uncertainty is subtracted
    from the demonstrated (achieved minus required) margin."""
    return demonstrated_margin - uncertainty


def margin_is_adequate(demonstrated_margin, uncertainty):
    """True when the effective margin still supports the margin claim
    (strictly positive; zero or negative means the uncertainty alone
    could account for the apparent margin)."""
    return effective_margin(demonstrated_margin, uncertainty) > 0


def exceeds_typical(uncertainty, parameter_type, table=None):
    """True when a project-specific uncertainty value is worse (larger)
    than the Table 4-2 typical value for its parameter type."""
    return uncertainty > typical_uncertainty(parameter_type, table)


def assess_test_point(point, table=None):
    """Full measurement-uncertainty-vs-margin assessment for one test
    point dict. Required keys: id, parameter_type, demonstrated_margin.
    Optional key: measured_uncertainty (falls back to the Table 4-2
    typical for parameter_type when absent or None). Returns a new
    dict; does not mutate the input. Raises ValueError when 'id' is
    missing or parameter_type is unknown."""
    if "id" not in point:
        raise ValueError("test point is missing an id")
    parameter_type = point["parameter_type"]
    measured = point.get("measured_uncertainty")
    uncertainty = resolve_uncertainty(parameter_type, measured, table)
    demonstrated_margin = point["demonstrated_margin"]
    margin = effective_margin(demonstrated_margin, uncertainty)
    flagged = measured is not None and exceeds_typical(measured, parameter_type, table)
    return {
        "id": point["id"],
        "parameter_type": parameter_type,
        "uncertainty_used": uncertainty,
        "uncertainty_source": "measured" if measured is not None else "table_typical",
        "effective_margin": margin,
        "margin_adequate": margin > 0,
        "uncertainty_flagged": flagged,
    }


def build_uncertainty_assessment(points, table=None):
    """Assessment record: one assess_test_point() result per test point,
    in input order. Raises ValueError on a duplicate point id."""
    record = []
    seen_ids = set()
    for point in points:
        assessment = assess_test_point(point, table)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate test point id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def inadequate_items(record):
    """Test point ids in the record whose margin is not adequate, in
    record order -- these cannot support a compliance claim as-is."""
    return [entry["id"] for entry in record if not entry["margin_adequate"]]


def flagged_items(record):
    """Test point ids in the record whose project-specific uncertainty
    exceeds its Table 4-2 typical value, in record order -- these need
    justification even if the margin itself is adequate."""
    return [entry["id"] for entry in record if entry["uncertainty_flagged"]]


def all_margins_adequate(record):
    """True when every entry in the assessment record has an adequate
    effective margin."""
    return len(inadequate_items(record)) == 0
