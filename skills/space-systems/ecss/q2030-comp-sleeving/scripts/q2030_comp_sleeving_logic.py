"""Complementary insulation-sleeving requirements on contact terminations.

Anchor: ECSS-Q-ST-20-30C clause 7.5 (complementary ECSS requirements for the
insulation sleeving applied over a terminated contact). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Compute the recovered inside diameter a heat-shrinkable sleeve reaches from
   its supplied inside diameter and its recovery ratio, then decide whether the
   sleeve is selectable at all: it has to slide over the largest diameter on
   the assembly path before shrinking, and it has to close down onto the
   smallest diameter it must grip afterwards, with a named grip margin.
2. Size the cut length from the span that must be covered plus the overlap the
   sleeve owes at each end, uprated for the longitudinal shrinkage the sleeve
   loses when it recovers.
3. Confirm the covered span really is covered once both ends of the installed
   sleeve are placed, and that the sleeve stops short of the features it may
   not reach: the contact's mating face and its retention or release geometry,
   and the connector cavity it would otherwise bottom out in.
4. Decide whether the termination stays inspectable -- an opaque sleeve over a
   joint that has no other inspection record is a finding, not a preference.
5. Roll every sleeve record up into one assessment with named findings.
"""

import math

__all__ = [
    "DIMENSION_TOLERANCE_MM",
    "recovered_inside_diameter_mm",
    "sleeve_slides_on",
    "sleeve_grips",
    "select_sleeve",
    "required_cut_length_mm",
    "installed_length_mm",
    "covers_span",
    "clearance_to_feature_mm",
    "evaluate_sleeve",
    "assess_sleeving",
]

# A diameter or length landing exactly on a bound meets it; the equality is a
# representation question, absorbed here rather than by moving the bound.
DIMENSION_TOLERANCE_MM = 1e-9

# A recovered sleeve must close at least this far below the diameter it grips
# before the grip is counted, expressed as a fraction of that diameter.
DEFAULT_GRIP_MARGIN = 0.05


def _require_number(value, label, positive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if positive and number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _require_fraction(value, label):
    number = _require_number(value, label, positive=False)
    if number < 0.0 or number >= 1.0:
        raise ValueError("%s must sit in [0, 1), got %r" % (label, value))
    return number


def recovered_inside_diameter_mm(supplied_id_mm, recovery_ratio):
    """Return the inside diameter a free-shrunk sleeve recovers to."""
    supplied = _require_number(supplied_id_mm, "supplied_id_mm")
    ratio = _require_number(recovery_ratio, "recovery_ratio")
    if ratio < 1.0:
        raise ValueError("recovery_ratio must be at least 1.0, got %g" % ratio)
    return supplied / ratio


def sleeve_slides_on(supplied_id_mm, largest_path_diameter_mm):
    """Return True when the unshrunk sleeve clears the largest diameter on its path."""
    supplied = _require_number(supplied_id_mm, "supplied_id_mm")
    largest = _require_number(largest_path_diameter_mm, "largest_path_diameter_mm")
    return supplied >= largest - DIMENSION_TOLERANCE_MM


def sleeve_grips(recovered_id_mm, smallest_gripped_diameter_mm, grip_margin=DEFAULT_GRIP_MARGIN):
    """Return True when the recovered sleeve closes onto the smallest gripped diameter."""
    recovered = _require_number(recovered_id_mm, "recovered_id_mm")
    smallest = _require_number(smallest_gripped_diameter_mm, "smallest_gripped_diameter_mm")
    margin = _require_fraction(grip_margin, "grip_margin")
    target = smallest * (1.0 - margin)
    return recovered <= target + DIMENSION_TOLERANCE_MM


def select_sleeve(spec):
    """Decide whether one sleeve size is selectable for a termination.

    spec keys: supplied_id_mm, recovery_ratio, largest_path_diameter_mm,
    smallest_gripped_diameter_mm, optional grip_margin.
    """
    if not isinstance(spec, dict):
        raise ValueError("sleeve spec must be a mapping")
    for key in (
        "supplied_id_mm",
        "recovery_ratio",
        "largest_path_diameter_mm",
        "smallest_gripped_diameter_mm",
    ):
        if key not in spec:
            raise ValueError("sleeve spec missing required key '%s'" % key)
    recovered = recovered_inside_diameter_mm(spec["supplied_id_mm"], spec["recovery_ratio"])
    slides = sleeve_slides_on(spec["supplied_id_mm"], spec["largest_path_diameter_mm"])
    grips = sleeve_grips(
        recovered,
        spec["smallest_gripped_diameter_mm"],
        spec.get("grip_margin", DEFAULT_GRIP_MARGIN),
    )
    findings = []
    if not slides:
        findings.append(
            "supplied inside diameter %.3f mm will not pass the %.3f mm largest path diameter"
            % (float(spec["supplied_id_mm"]), float(spec["largest_path_diameter_mm"]))
        )
    if not grips:
        findings.append(
            "recovered inside diameter %.3f mm does not close onto the %.3f mm gripped diameter"
            % (recovered, float(spec["smallest_gripped_diameter_mm"]))
        )
    return {
        "recovered_id_mm": recovered,
        "slides_on": bool(slides),
        "grips": bool(grips),
        "selectable": bool(slides and grips),
        "findings": findings,
    }


def required_cut_length_mm(span_mm, overlap_each_end_mm, longitudinal_shrinkage=0.0):
    """Return the cut length a sleeve needs to cover a span with an overlap at each end."""
    span = _require_number(span_mm, "span_mm")
    overlap = _require_number(overlap_each_end_mm, "overlap_each_end_mm", positive=False)
    if overlap < 0.0:
        raise ValueError("overlap_each_end_mm must not be negative")
    shrinkage = _require_fraction(longitudinal_shrinkage, "longitudinal_shrinkage")
    installed_need = span + 2.0 * overlap
    return installed_need / (1.0 - shrinkage)


def installed_length_mm(cut_length_mm, longitudinal_shrinkage=0.0):
    """Return the length a cut sleeve settles at once it has recovered."""
    cut = _require_number(cut_length_mm, "cut_length_mm")
    shrinkage = _require_fraction(longitudinal_shrinkage, "longitudinal_shrinkage")
    return cut * (1.0 - shrinkage)


def covers_span(installed_mm, span_mm, overlap_each_end_mm):
    """Return True when an installed sleeve covers the span plus both overlaps."""
    installed = _require_number(installed_mm, "installed_mm")
    span = _require_number(span_mm, "span_mm")
    overlap = _require_number(overlap_each_end_mm, "overlap_each_end_mm", positive=False)
    if overlap < 0.0:
        raise ValueError("overlap_each_end_mm must not be negative")
    needed = span + 2.0 * overlap
    return installed >= needed - DIMENSION_TOLERANCE_MM


def clearance_to_feature_mm(sleeve_end_position_mm, feature_position_mm):
    """Return the clearance from a sleeve end to a feature it may not reach."""
    end = _require_number(sleeve_end_position_mm, "sleeve_end_position_mm", positive=False)
    feature = _require_number(feature_position_mm, "feature_position_mm", positive=False)
    return feature - end


def evaluate_sleeve(record):
    """Evaluate one sleeved termination and return its findings.

    record keys: id, the select_sleeve keys, span_mm, overlap_each_end_mm,
    cut_length_mm, optional longitudinal_shrinkage, sleeve_end_position_mm,
    restricted_feature_position_mm, minimum_feature_clearance_mm, opaque,
    joint_inspection_recorded.
    """
    if not isinstance(record, dict):
        raise ValueError("sleeve record must be a mapping")
    for key in ("id", "span_mm", "overlap_each_end_mm", "cut_length_mm"):
        if key not in record:
            raise ValueError("sleeve record missing required key '%s'" % key)
    identifier = record["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("sleeve record id must be a non-empty string")
    selection = select_sleeve(record)
    shrinkage = record.get("longitudinal_shrinkage", 0.0)
    installed = installed_length_mm(record["cut_length_mm"], shrinkage)
    required = required_cut_length_mm(record["span_mm"], record["overlap_each_end_mm"], shrinkage)
    covered = covers_span(installed, record["span_mm"], record["overlap_each_end_mm"])
    findings = list(selection["findings"])
    if not covered:
        findings.append(
            "sleeve %s recovers to %.3f mm and leaves the %.3f mm covered span short of its overlap"
            % (identifier, installed, float(record["span_mm"]))
        )
    clearance = None
    if "sleeve_end_position_mm" in record and "restricted_feature_position_mm" in record:
        clearance = clearance_to_feature_mm(
            record["sleeve_end_position_mm"], record["restricted_feature_position_mm"]
        )
        minimum_clearance = _require_number(
            record.get("minimum_feature_clearance_mm", 0.5), "minimum_feature_clearance_mm"
        )
        if clearance < minimum_clearance - DIMENSION_TOLERANCE_MM:
            findings.append(
                "sleeve %s ends %.3f mm from a restricted feature, inside the %.3f mm minimum"
                % (identifier, clearance, minimum_clearance)
            )
    if record.get("opaque", False) and not record.get("joint_inspection_recorded", False):
        findings.append(
            "sleeve %s is opaque over a joint with no separate inspection record" % identifier
        )
    return {
        "id": identifier,
        "selection": selection,
        "installed_length_mm": installed,
        "required_cut_length_mm": required,
        "covers_span": bool(covered),
        "feature_clearance_mm": clearance,
        "findings": findings,
        "conforming": not findings,
    }


def assess_sleeving(records):
    """Assess a set of sleeved terminations and return one rolled-up verdict."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of sleeve records")
    evaluated = []
    seen = set()
    for record in records:
        result = evaluate_sleeve(record)
        if result["id"] in seen:
            raise ValueError("duplicate sleeve identifier %r" % result["id"])
        seen.add(result["id"])
        evaluated.append(result)
    findings = []
    for result in evaluated:
        findings.extend(result["findings"])
    conforming = [r for r in evaluated if r["conforming"]]
    return {
        "records": evaluated,
        "evaluated_count": len(evaluated),
        "conforming_count": len(conforming),
        "findings": findings,
        "compliant": not findings,
    }
