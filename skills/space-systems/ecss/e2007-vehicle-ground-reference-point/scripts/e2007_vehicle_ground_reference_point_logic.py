#!/usr/bin/env python3
"""ECSS-E-ST-20-07C clause 4.2.11.2 -- vehicle ground reference point.

Deterministic, offline, standard-library-only logic that qualifies the single
structural point used as the baseline for bonding-resistance measurements and
checks every measurement referred to it: the terminal actually cited, the
measurement method against the allowance being claimed, the substantiation of
the declared lead offset, and the lead-corrected reading against the allowance
for the bond category.

The procedure is a paraphrase; no standard text is reproduced.
"""

import math

BOND_CATEGORY_ALLOWANCE_MOHM = {
    "lightning-return-bond": 1.0,
    "structure-bond-primary": 2.5,
    "structure-bond-secondary": 10.0,
    "shield-termination-bond": 25.0,
}

STRUCTURAL_MEMBERS = (
    "primary-structure",
    "secondary-structure",
    "equipment-panel",
)

CONDUCTIVE_FINISHES = (
    "bare-machined",
    "chemical-conversion-coated",
    "electroplated",
)

NON_CONDUCTIVE_FINISHES = (
    "hard-anodized",
    "painted",
    "adhesive-bonded",
)

SURFACE_FINISHES = CONDUCTIVE_FINISHES + NON_CONDUCTIVE_FINISHES

MEASUREMENT_METHODS = (
    "four-terminal-kelvin",
    "two-terminal-ohmmeter",
)

# Below this allowance the lead resistance of a two-terminal reading swamps
# the quantity being measured, so only the four-terminal method resolves it.
TWO_TERMINAL_RESOLUTION_FLOOR_MOHM = 100.0

# Resistance of a copper lead at room temperature, in milliohm per metre per
# square millimetre of conductor section.
COPPER_MOHM_PER_M_PER_MM2 = 17.24

# A declared lead offset may depart from the geometry-derived figure by this
# fraction before it is treated as unsubstantiated.
LEAD_OFFSET_SUBSTANTIATION_BAND = 0.25

# Absorbs float representation error on a lead-corrected reading that
# physically meets its allowance. It never widens the allowance.
RESISTANCE_REL_TOL = 1e-9
RESISTANCE_ABS_TOL = 1e-12


def _within(value, limit):
    """True when ``value`` does not exceed ``limit``.

    A corrected reading is a difference of two decimal values, so a reading
    that physically sits on the allowance can land a few units in the last
    place above it. That representation error is absorbed here; the
    engineering allowance is not moved.
    """
    if value <= limit:
        return True
    return math.isclose(
        value, limit, rel_tol=RESISTANCE_REL_TOL, abs_tol=RESISTANCE_ABS_TOL
    )


def normalize_token(raw, allowed, label):
    """Return the canonical token for ``raw`` or raise ValueError."""
    if not isinstance(raw, str):
        raise ValueError("%s must be a string, got %r" % (label, raw))
    token = raw.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    if token not in allowed:
        raise ValueError(
            "unknown %s %r; expected one of %s"
            % (label, raw, ", ".join(sorted(allowed)))
        )
    return token


def _positive_number(raw, label, allow_zero=False):
    """Validate a finite non-negative (or strictly positive) magnitude."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, raw))
    value = float(raw)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, raw))
    if allow_zero:
        if value < 0.0:
            raise ValueError("%s must not be negative, got %r" % (label, raw))
    elif value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, raw))
    return value


def allowance_for(bond_category):
    """Allowance in milliohm for a bond category."""
    category = normalize_token(
        bond_category, tuple(BOND_CATEGORY_ALLOWANCE_MOHM), "bond category"
    )
    return BOND_CATEGORY_ALLOWANCE_MOHM[category]


def lead_resistance_mohm(length_m, section_mm2):
    """Geometry-derived resistance of a copper measurement lead, in milliohm."""
    length = _positive_number(length_m, "lead length_m")
    section = _positive_number(section_mm2, "lead section_mm2")
    return COPPER_MOHM_PER_M_PER_MM2 * length / section


def qualify_reference_point(record):
    """Qualify one candidate vehicle ground reference point record."""
    if not isinstance(record, dict):
        raise ValueError("reference point record must be a mapping, got %r" % (record,))
    point_id = record.get("id")
    if not isinstance(point_id, str) or not point_id.strip():
        raise ValueError("reference point record needs a non-empty 'id'")
    member = normalize_token(
        record.get("structural_member"), STRUCTURAL_MEMBERS, "structural member"
    )
    finish = normalize_token(
        record.get("surface_finish"), SURFACE_FINISHES, "surface finish"
    )
    accessible = record.get("accessible_in_measurement_configuration")
    if not isinstance(accessible, bool):
        raise ValueError(
            "accessible_in_measurement_configuration must be a boolean, got %r"
            % (accessible,)
        )
    findings = []
    if member != "primary-structure":
        findings.append("reference-point-not-on-primary-structure")
    if finish not in CONDUCTIVE_FINISHES:
        findings.append("reference-point-surface-finish-not-conductive")
    if not accessible:
        findings.append("reference-point-not-reachable-for-measurement")
    return {
        "id": point_id.strip(),
        "structural_member": member,
        "surface_finish": finish,
        "accessible": accessible,
        "findings": findings,
        "qualified": not findings,
    }


def resolve_reference_point(records):
    """Qualify the one designated reference point out of the candidate set."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("reference point records must be a non-empty sequence")
    designated = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("reference point record must be a mapping, got %r" % (record,))
        if record.get("designated", False):
            designated.append(record)
    if not designated:
        raise ValueError("no reference point record is marked designated")
    if len(designated) > 1:
        names = sorted(str(rec.get("id")) for rec in designated)
        raise ValueError(
            "more than one designated vehicle ground reference point: %s"
            % ", ".join(names)
        )
    return qualify_reference_point(designated[0])


def correct_reading(raw_mohm, lead_offset_mohm):
    """Lead-corrected bonding reading in milliohm."""
    raw = _positive_number(raw_mohm, "raw reading_mohm", allow_zero=True)
    offset = _positive_number(lead_offset_mohm, "lead_offset_mohm", allow_zero=True)
    corrected = raw - offset
    if corrected < 0.0 and not math.isclose(
        corrected, 0.0, rel_tol=RESISTANCE_REL_TOL, abs_tol=RESISTANCE_ABS_TOL
    ):
        raise ValueError(
            "lead offset %.6g mohm exceeds the raw reading %.6g mohm" % (offset, raw)
        )
    return max(corrected, 0.0)


def check_lead_offset(declared_offset_mohm, length_m, section_mm2):
    """Compare a declared lead offset with the geometry-derived figure."""
    declared = _positive_number(
        declared_offset_mohm, "declared lead_offset_mohm", allow_zero=True
    )
    computed = lead_resistance_mohm(length_m, section_mm2)
    departure = abs(declared - computed) / computed
    substantiated = departure <= LEAD_OFFSET_SUBSTANTIATION_BAND or math.isclose(
        departure, LEAD_OFFSET_SUBSTANTIATION_BAND, rel_tol=RESISTANCE_REL_TOL
    )
    return {
        "declared_mohm": declared,
        "computed_mohm": computed,
        "departure_fraction": departure,
        "substantiated": substantiated,
    }


def method_resolves(method, allowance_mohm):
    """True when the measurement method can resolve the claimed allowance."""
    token = normalize_token(method, MEASUREMENT_METHODS, "measurement method")
    allowance = _positive_number(allowance_mohm, "allowance_mohm")
    if token == "four-terminal-kelvin":
        return True
    return allowance >= TWO_TERMINAL_RESOLUTION_FLOOR_MOHM


def evaluate_measurement(record, reference_id):
    """Evaluate one bonding-resistance measurement against the baseline."""
    if not isinstance(record, dict):
        raise ValueError("measurement record must be a mapping, got %r" % (record,))
    if not isinstance(reference_id, str) or not reference_id.strip():
        raise ValueError("reference_id must be a non-empty string")
    bond_id = record.get("id")
    if not isinstance(bond_id, str) or not bond_id.strip():
        raise ValueError("measurement record needs a non-empty 'id'")
    category = normalize_token(
        record.get("bond_category"), tuple(BOND_CATEGORY_ALLOWANCE_MOHM), "bond category"
    )
    allowance = BOND_CATEGORY_ALLOWANCE_MOHM[category]
    method = normalize_token(
        record.get("method"), MEASUREMENT_METHODS, "measurement method"
    )
    cited = record.get("reference_terminal")
    if not isinstance(cited, str) or not cited.strip():
        raise ValueError("measurement record needs a non-empty 'reference_terminal'")
    offset = record.get("lead_offset_mohm", 0.0)
    corrected = correct_reading(record.get("raw_reading_mohm"), offset)
    findings = []
    if cited.strip() != reference_id.strip():
        findings.append("measurement-not-referred-to-designated-reference")
    if not method_resolves(method, allowance):
        findings.append("measurement-method-cannot-resolve-allowance")
    offset_check = None
    if "lead_length_m" in record and "lead_section_mm2" in record:
        offset_check = check_lead_offset(
            offset, record["lead_length_m"], record["lead_section_mm2"]
        )
        if not offset_check["substantiated"]:
            findings.append("lead-offset-not-substantiated-by-geometry")
    if not _within(corrected, allowance):
        findings.append("corrected-reading-exceeds-bond-allowance")
    return {
        "id": bond_id.strip(),
        "bond_category": category,
        "method": method,
        "allowance_mohm": allowance,
        "corrected_mohm": corrected,
        "lead_offset": offset_check,
        "findings": findings,
        "compliant": not findings,
    }


def assess_bonding_baseline(reference_records, measurements):
    """Full clause 4.2.11.2 verdict for a bonding measurement campaign."""
    reference = resolve_reference_point(reference_records)
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("measurements must be a sequence of measurement records")
    results = [evaluate_measurement(rec, reference["id"]) for rec in measurements]
    findings = list(reference["findings"])
    for entry in results:
        for finding in entry["findings"]:
            findings.append("%s: %s" % (entry["id"], finding))
    corrected = [entry["corrected_mohm"] for entry in results]
    return {
        "reference": reference,
        "measurements": results,
        "measurement_count": len(results),
        "worst_corrected_mohm": max(corrected) if corrected else None,
        "mean_corrected_mohm": (sum(corrected) / len(corrected)) if corrected else None,
        "findings": findings,
        "compliant": not findings,
    }


def summarize_assessment(report):
    """One-line summary of a bonding baseline assessment report."""
    if not isinstance(report, dict) or "compliant" not in report:
        raise ValueError("summary needs an assessment report mapping")
    verdict = "COMPLIANT" if report["compliant"] else "NON-COMPLIANT"
    worst = report["worst_corrected_mohm"]
    worst_text = "n/a" if worst is None else "%.3f mohm" % worst
    return "%s: baseline=%s, %d measurement(s), worst=%s, %d finding(s)" % (
        verdict,
        report["reference"]["id"],
        report["measurement_count"],
        worst_text,
        len(report["findings"]),
    )
