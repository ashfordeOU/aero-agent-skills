"""Offgassing test report assembly and self-consistency checking.

Anchor: ECSS-Q-ST-70-29 reporting step -- assembling the identification,
quantification and assessment outputs of an offgassing test into one issued
report and proving the report's conclusion is supported by its own tables.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the traceability block of the article and the run.
2. Validate the three product tables and refuse duplicate compound rows.
3. Cross-check the compound sets in both directions.
4. Recompute every stated total from the rows it claims to summarise and
   compare it under a named accumulation tolerance.
5. Derive the conclusion from the assessment verdicts and the open items, and
   compare it with the conclusion the report states.
"""

import math

__all__ = [
    "TOTAL_TOLERANCE_REL",
    "REQUIRED_IDENTIFICATION_FIELDS",
    "REQUIRED_SECTIONS",
    "CONCLUSION_ACCEPTED",
    "CONCLUSION_REJECTED",
    "CONCLUSION_OPEN",
    "validate_identification",
    "validate_table",
    "cross_check_tables",
    "recompute_total_mass_ug",
    "recompute_governing_t_value",
    "totals_agree",
    "derive_conclusion",
    "build_report",
]

# A stated total is compared against a sum of a few dozen rows; the tolerance
# covers accumulation error only. A discrepancy larger than this is a missing
# or duplicated row, not a rounding artefact.
TOTAL_TOLERANCE_REL = 1e-9

REQUIRED_IDENTIFICATION_FIELDS = (
    "article",
    "batch",
    "tested_mass_g",
    "vessel_volume_m3",
    "conditioning_temperature_c",
    "conditioning_duration_h",
    "analytical_method",
)

REQUIRED_SECTIONS = (
    "identification",
    "products",
    "concentrations",
    "assessments",
    "conclusion",
)

CONCLUSION_ACCEPTED = "accepted"
CONCLUSION_REJECTED = "rejected"
CONCLUSION_OPEN = "open"

_CONCLUSIONS = {CONCLUSION_ACCEPTED, CONCLUSION_REJECTED, CONCLUSION_OPEN}

_TEXT_FIELDS = {"article", "batch", "analytical_method"}
_POSITIVE_FIELDS = {
    "tested_mass_g",
    "vessel_volume_m3",
    "conditioning_duration_h",
}


def _real(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def validate_identification(block):
    """Return the validated traceability block of the article and the run."""
    if not isinstance(block, dict):
        raise ValueError("identification block must be a mapping")
    out = {}
    missing = [f for f in REQUIRED_IDENTIFICATION_FIELDS if f not in block]
    if missing:
        raise ValueError(
            "identification block missing field(s): %s" % ", ".join(sorted(missing))
        )
    for field in REQUIRED_IDENTIFICATION_FIELDS:
        value = block[field]
        if field in _TEXT_FIELDS:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("%s must be a non-empty string" % field)
            out[field] = value.strip()
        elif field in _POSITIVE_FIELDS:
            out[field] = _positive(field, value)
        else:
            # Conditioning temperature is a Celsius reading and may be negative,
            # but a physically impossible value is still an input error.
            temperature = _real(field, value)
            if temperature <= -273.15:
                raise ValueError("%s must be above absolute zero, got %r" % (field, value))
            out[field] = temperature
    return out


def validate_table(rows, name, required_keys):
    """Return the rows of one report table, refusing duplicates and gaps."""
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("%s table must be a non-empty sequence of rows" % name)
    out = []
    seen = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("%s row %d must be a mapping" % (name, i))
        for key in required_keys:
            if key not in row:
                raise ValueError("%s row %d missing '%s'" % (name, i, key))
        compound = row["compound"]
        if not isinstance(compound, str) or not compound.strip():
            raise ValueError("%s row %d compound must be a non-empty string" % (name, i))
        compound = compound.strip()
        if compound in seen:
            raise ValueError("%s table has duplicate rows for %r" % (name, compound))
        seen.add(compound)
        normalised = dict(row)
        normalised["compound"] = compound
        out.append(normalised)
    return out


def cross_check_tables(products, concentrations, assessments):
    """Return the compounds missing from each table, checked in both directions."""
    named = {r["compound"] for r in products}
    measured = {r["compound"] for r in concentrations}
    graded = {r["compound"] for r in assessments}
    return {
        "identified_without_concentration": sorted(named - measured),
        "identified_without_assessment": sorted(named - graded),
        "measured_without_identification": sorted(measured - named),
        "assessed_without_identification": sorted(graded - named),
        "assessed_without_concentration": sorted(graded - measured),
    }


def recompute_total_mass_ug(concentrations):
    """Return the total released mass implied by the concentration rows."""
    if not isinstance(concentrations, (list, tuple)) or not concentrations:
        raise ValueError("concentration rows must be a non-empty sequence")
    values = []
    for row in concentrations:
        value = _real("reported_mass_ug of %s" % row.get("compound", "?"),
                      row["reported_mass_ug"])
        if value < 0.0:
            raise ValueError("reported_mass_ug must not be negative, got %r" % value)
        values.append(value)
    return math.fsum(values)


def recompute_governing_t_value(assessments):
    """Return the governing toxicological-group total from the assessment rows."""
    if not isinstance(assessments, (list, tuple)) or not assessments:
        raise ValueError("assessment rows must be a non-empty sequence")
    totals = {}
    for row in assessments:
        ratio = row.get("t_ratio")
        if ratio is None:
            continue
        value = _real("t_ratio of %s" % row.get("compound", "?"), ratio)
        if value < 0.0:
            raise ValueError("t_ratio must not be negative, got %r" % ratio)
        group = row.get("group") or "ungrouped"
        totals[group] = totals.get(group, 0.0) + value
    if not totals:
        return 0.0
    return max(totals.values())


def totals_agree(stated, recomputed):
    """Return True when a stated total matches its recomputation."""
    a = _real("stated total", stated)
    b = _real("recomputed total", recomputed)
    scale = max(abs(a), abs(b), 1.0)
    return abs(a - b) <= scale * TOTAL_TOLERANCE_REL


def derive_conclusion(assessments, open_items):
    """Derive the report conclusion from the assessment rows and open items."""
    if not isinstance(assessments, (list, tuple)) or not assessments:
        raise ValueError("assessment rows must be a non-empty sequence")
    if not isinstance(open_items, (list, tuple)):
        raise ValueError("open_items must be a sequence")
    for row in assessments:
        verdict = row.get("verdict")
        if verdict not in ("met", "breached", "open"):
            raise ValueError(
                "assessment verdict for %r must be met, breached or open, got %r"
                % (row.get("compound"), verdict)
            )
    if any(row["verdict"] == "breached" for row in assessments):
        return CONCLUSION_REJECTED
    if open_items or any(row["verdict"] == "open" for row in assessments):
        return CONCLUSION_OPEN
    return CONCLUSION_ACCEPTED


def build_report(spec):
    """Assemble the offgassing test report and check it against itself.

    spec keys: identification, products, concentrations, assessments,
    stated_conclusion, stated_total_mass_ug, stated_governing_t_value,
    optional open_items.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "identification", "products", "concentrations", "assessments",
        "stated_conclusion", "stated_total_mass_ug", "stated_governing_t_value",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    stated_conclusion = spec["stated_conclusion"]
    if stated_conclusion not in _CONCLUSIONS:
        raise ValueError(
            "stated_conclusion must be one of %s, got %r"
            % (sorted(_CONCLUSIONS), stated_conclusion)
        )
    identification = validate_identification(spec["identification"])
    products = validate_table(spec["products"], "products", ("compound", "grade"))
    concentrations = validate_table(
        spec["concentrations"], "concentrations", ("compound", "reported_mass_ug")
    )
    assessments = validate_table(
        spec["assessments"], "assessments", ("compound", "verdict")
    )
    open_items = list(spec.get("open_items", []))
    cross = cross_check_tables(products, concentrations, assessments)
    total_mass = recompute_total_mass_ug(concentrations)
    governing = recompute_governing_t_value(assessments)
    mass_ok = totals_agree(spec["stated_total_mass_ug"], total_mass)
    t_ok = totals_agree(spec["stated_governing_t_value"], governing)
    derived = derive_conclusion(assessments, open_items)
    findings = []
    for key in sorted(cross):
        if cross[key]:
            findings.append("%s: %s" % (key.replace("_", " "), ", ".join(cross[key])))
    if not mass_ok:
        findings.append(
            "stated total released mass %.6g does not match the %.6g implied by "
            "the concentration rows" % (float(spec["stated_total_mass_ug"]), total_mass)
        )
    if not t_ok:
        findings.append(
            "stated governing toxicity total %.6g does not match the %.6g implied "
            "by the assessment rows"
            % (float(spec["stated_governing_t_value"]), governing)
        )
    if derived != stated_conclusion:
        findings.append(
            "stated conclusion %r is not the %r derived from the assessment rows"
            % (stated_conclusion, derived)
        )
    if open_items:
        findings.append("open item(s) carried into the issued report: %d" % len(open_items))
    return {
        "sections": list(REQUIRED_SECTIONS),
        "identification": identification,
        "products": products,
        "concentrations": concentrations,
        "assessments": assessments,
        "cross_check": cross,
        "recomputed_total_mass_ug": total_mass,
        "recomputed_governing_t_value": governing,
        "totals_consistent": mass_ok and t_ok,
        "derived_conclusion": derived,
        "stated_conclusion": stated_conclusion,
        "open_items": open_items,
        "issuable": (
            mass_ok
            and t_ok
            and derived == stated_conclusion
            and not any(cross[key] for key in cross)
        ),
        "findings": findings,
    }
