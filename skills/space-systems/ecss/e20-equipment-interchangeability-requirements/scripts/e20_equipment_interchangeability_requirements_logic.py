#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.6 equipment interchangeability
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires equipment items
of the same part number to be interchangeable -- any one of them may be
installed in the slot of any other without selection, rework or
re-adjustment, provided it is equivalent in form (mass and envelope),
fit (mounting pattern, connector type and pinout, interface finish) and
function (electrical interface, consumption, protocol, firmware
baseline), and provided its qualification status is at least the status
the slot requires. Two consequences follow that a parts list does not
show on its own: an attribute compared with no declared tolerance has
not been shown equivalent, only assumed equivalent; and a unit that
drops in only after matched-set pairing or on-installation trimming is
not interchangeable however well its attributes agree.

This module implements attribute categorization into form, fit and
function, numeric deviation against a declared tolerance, exact
matching for discrete attributes, part-number and revision identity,
qualification-status ranking, installation-adjustment screening, the
aggregated pairwise review and a candidate screen over a fleet. It does
not define the qualification programme itself, the configuration
management process, or the tolerances -- those come from the equipment
specification.
"""

# Attributes describing the physical article: what it is.
FORM_ATTRIBUTES = frozenset(
    {
        "mass_kg",
        "envelope_x_mm",
        "envelope_y_mm",
        "envelope_z_mm",
        "centre_of_gravity_offset_mm",
    }
)

# Attributes describing how the article installs: where it goes.
FIT_ATTRIBUTES = frozenset(
    {
        "mounting_hole_pattern",
        "mounting_plane_flatness_mm",
        "connector_type",
        "connector_pinout",
        "thermal_interface_finish",
        "harness_pigtail_length_mm",
    }
)

# Attributes describing what the article does once installed.
FUNCTION_ATTRIBUTES = frozenset(
    {
        "electrical_interface_spec",
        "power_consumption_w",
        "output_voltage_v",
        "data_protocol",
        "firmware_baseline",
    }
)

# Attributes whose values are labels, not measurements: equivalence is
# exact equality and no tolerance applies.
DISCRETE_ATTRIBUTES = frozenset(
    {
        "mounting_hole_pattern",
        "connector_type",
        "connector_pinout",
        "thermal_interface_finish",
        "electrical_interface_spec",
        "data_protocol",
        "firmware_baseline",
    }
)

# Ordered qualification status. A candidate may fill a slot only when
# its status ranks at or above the status the slot requires.
QUALIFICATION_RANK = {
    "breadboard": 0,
    "engineering_model": 1,
    "qualification_model": 2,
    "protoflight_model": 3,
    "flight_model": 4,
}

_REQUIRED_UNIT_KEYS = (
    "unit_id",
    "part_number",
    "revision",
    "qualification_status",
    "attributes",
)

FINDING_GROUPS = ("identity", "form", "fit", "function", "qualification", "installation")


def _require_keys(mapping, keys, what):
    """Raise ValueError naming the first missing key of a record."""
    for key in keys:
        if key not in mapping:
            raise ValueError("%s record is missing required key %r" % (what, key))


def categorize_attribute(attribute):
    """Interchangeability dimension of an attribute: "form", "fit" or
    "function". Raises ValueError for an attribute outside all three
    sets -- an uncategorized attribute cannot be judged under clause
    4.2.6 and must not be silently dropped from the comparison."""
    if attribute in FORM_ATTRIBUTES:
        return "form"
    if attribute in FIT_ATTRIBUTES:
        return "fit"
    if attribute in FUNCTION_ATTRIBUTES:
        return "function"
    raise ValueError(
        "uncategorized equipment attribute %r under "
        "E-ST-20C clause 4.2.6" % (attribute,)
    )


def relative_deviation_percent(reference_value, candidate_value):
    """Deviation of a candidate numeric attribute from the reference, in
    percent of the reference: 100 * |candidate - reference| /
    |reference|. Raises ValueError for a zero reference (the relative
    deviation is undefined) or a non-numeric value."""
    for label, value in (("reference", reference_value), ("candidate", candidate_value)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s value %r is not numeric" % (label, value))
    if reference_value == 0:
        raise ValueError("reference_value must be non-zero for a relative deviation")
    return 100.0 * abs(candidate_value - reference_value) / abs(reference_value)


def attribute_findings(attribute, reference_value, candidate_value, tolerance_percent):
    """Finding list (empty when equivalent) for one attribute of a
    candidate against the reference unit.

    A discrete attribute must match exactly and ignores the tolerance. A
    numeric attribute is compared against tolerance_percent; a
    tolerance of None means the equipment specification never declared
    one, which is itself a finding rather than a pass. Raises ValueError
    for an uncategorized attribute or a negative tolerance."""
    dimension = categorize_attribute(attribute)
    if attribute in DISCRETE_ATTRIBUTES:
        if reference_value == candidate_value:
            return []
        return [
            {
                "issue": "discrete_attribute_mismatch",
                "dimension": dimension,
                "attribute": attribute,
                "reference_value": reference_value,
                "candidate_value": candidate_value,
            }
        ]
    if tolerance_percent is None:
        return [
            {
                "issue": "undeclared_interchangeability_tolerance",
                "dimension": dimension,
                "attribute": attribute,
            }
        ]
    if tolerance_percent < 0:
        raise ValueError("tolerance_percent must be >= 0")
    deviation = relative_deviation_percent(reference_value, candidate_value)
    if deviation <= tolerance_percent:
        return []
    return [
        {
            "issue": "numeric_attribute_outside_tolerance",
            "dimension": dimension,
            "attribute": attribute,
            "deviation_percent": deviation,
            "tolerance_percent": tolerance_percent,
        }
    ]


def identity_findings(reference_unit, candidate_unit):
    """Finding list (empty when compliant) for the configuration
    identity of the two units. Interchangeability under clause 4.2.6 is
    claimed within one part number; a different part number ends the
    claim. A different revision of the same part number is acceptable
    only when the candidate declares that revision form-fit-function
    neutral. Raises ValueError for a missing key."""
    for unit in (reference_unit, candidate_unit):
        _require_keys(unit, ("unit_id", "part_number", "revision"), "unit")
    findings = []
    if reference_unit["part_number"] != candidate_unit["part_number"]:
        findings.append(
            {
                "issue": "distinct_part_number_breaks_interchangeability",
                "reference_part_number": reference_unit["part_number"],
                "candidate_part_number": candidate_unit["part_number"],
            }
        )
        return findings
    if reference_unit["revision"] != candidate_unit["revision"] and not candidate_unit.get(
        "revision_form_fit_function_neutral", False
    ):
        findings.append(
            {
                "issue": "revision_change_not_declared_neutral",
                "reference_revision": reference_unit["revision"],
                "candidate_revision": candidate_unit["revision"],
            }
        )
    return findings


def qualification_findings(candidate_status, required_status):
    """Finding list (empty when compliant) for the qualification status
    of a candidate against the status the slot requires. Raises
    ValueError for an unrecognized status on either side."""
    for label, status in (
        ("candidate", candidate_status),
        ("required", required_status),
    ):
        if status not in QUALIFICATION_RANK:
            raise ValueError("unrecognized %s qualification status %r" % (label, status))
    if QUALIFICATION_RANK[candidate_status] >= QUALIFICATION_RANK[required_status]:
        return []
    return [
        {
            "issue": "qualification_status_below_slot_requirement",
            "candidate_status": candidate_status,
            "required_status": required_status,
        }
    ]


def installation_findings(candidate_unit):
    """Finding list (empty when compliant) for installation
    constraints. A unit that fits only after matched-set pairing, an
    on-installation trim, or a unit-specific calibration file loaded
    into the system is not interchangeable in the sense of clause
    4.2.6, however closely its attributes agree."""
    findings = []
    if candidate_unit.get("requires_matched_set_pairing", False):
        findings.append(
            {
                "issue": "requires_matched_set_pairing",
                "unit": candidate_unit.get("unit_id"),
            }
        )
    if candidate_unit.get("requires_on_installation_adjustment", False):
        findings.append(
            {
                "issue": "requires_on_installation_adjustment",
                "unit": candidate_unit.get("unit_id"),
            }
        )
    if candidate_unit.get("requires_unit_specific_calibration_data", False):
        findings.append(
            {
                "issue": "requires_unit_specific_calibration_data",
                "unit": candidate_unit.get("unit_id"),
            }
        )
    return findings


def interchangeability_review(
    reference_unit, candidate_unit, tolerances, required_status
):
    """Full clause 4.2.6 review of one candidate against one reference
    unit.

    reference_unit / candidate_unit: mappings with unit_id, part_number,
    revision, qualification_status, attributes, and the optional
    neutrality and installation-constraint flags. tolerances: mapping
    from attribute name to the allowed deviation in percent; an
    attribute absent from it is treated as having no declared tolerance.
    required_status: the qualification status the slot demands. Returns
    one finding list per group in FINDING_GROUPS. Raises ValueError for
    a missing key, an uncategorized attribute or an unrecognized
    status."""
    for unit in (reference_unit, candidate_unit):
        _require_keys(unit, _REQUIRED_UNIT_KEYS, "unit")
    review = {group: [] for group in FINDING_GROUPS}
    review["identity"] = identity_findings(reference_unit, candidate_unit)
    reference_attributes = reference_unit["attributes"]
    candidate_attributes = candidate_unit["attributes"]
    for attribute in sorted(reference_attributes):
        dimension = categorize_attribute(attribute)
        if attribute not in candidate_attributes:
            review[dimension].append(
                {
                    "issue": "attribute_not_recorded_on_candidate",
                    "dimension": dimension,
                    "attribute": attribute,
                }
            )
            continue
        review[dimension].extend(
            attribute_findings(
                attribute,
                reference_attributes[attribute],
                candidate_attributes[attribute],
                tolerances.get(attribute),
            )
        )
    review["qualification"] = qualification_findings(
        candidate_unit["qualification_status"], required_status
    )
    review["installation"] = installation_findings(candidate_unit)
    return review


def is_interchangeable(review):
    """True when every finding group in an interchangeability_review
    result is empty -- the candidate may replace the reference unit
    under clause 4.2.6 for this assessment."""
    return all(len(review[group]) == 0 for group in FINDING_GROUPS)


def screen_candidates(reference_unit, candidates, tolerances, required_status):
    """Unit ids of the candidates that are interchangeable with the
    reference unit, in the order given. Every candidate is reviewed;
    a ValueError raised by any one of them propagates rather than
    silently shrinking the interchangeable set."""
    accepted = []
    for candidate in candidates:
        review = interchangeability_review(
            reference_unit, candidate, tolerances, required_status
        )
        if is_interchangeable(review):
            accepted.append(candidate["unit_id"])
    return accepted
