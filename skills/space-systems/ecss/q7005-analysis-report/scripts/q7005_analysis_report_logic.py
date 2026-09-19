"""Content and self-consistency of an IR organic contamination analysis report.

Anchor: ECSS-Q-ST-70-05C, the reporting clause of infrared detection of
organic contamination on surfaces (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A report has four loads to carry: what was done, what was seen, what
   it came to, and what it means. Method, spectra, levels and judgement
   are graded as separate sections, because a report is routinely strong
   in one and silent in another and a single completeness percentage
   hides that.
2. Some content is only required by what the run actually was. An
   indirect method owes a solvent, a recovery fraction and a blank; a
   named contaminant owes the reference spectrum the naming rests on; a
   non-detect owes the quantitation limit that bounds it.
3. The level is recomputable from the residue mass, the sampled area and
   the recovery. A report whose stated level does not follow from its
   own numbers is not a reporting style question, it is an arithmetic
   defect, and it is caught by recomputing rather than by reading.
4. A judgement is only a judgement when the level it was made against is
   printed beside it. Without the limit it is an opinion, and a
   judgement that contradicts the report's own numbers is worse than
   none.
5. A level written to more places than its uncertainty supports is an
   observation, not a defect. It is reported so the next issue can tidy
   it, and it does not block the report.

Stdlib only, offline, deterministic.
"""

SECTION_METHOD = "method"
SECTION_SPECTRA = "spectra"
SECTION_LEVELS = "levels"
SECTION_JUDGEMENT = "judgement"

SECTION_ORDER = (SECTION_METHOD, SECTION_SPECTRA, SECTION_LEVELS,
                 SECTION_JUDGEMENT)

# Fields every report owes, whatever the run was.
REPORT_SECTIONS = {
    SECTION_METHOD: ("method_name", "method_kind", "sampled_area_m2"),
    SECTION_SPECTRA: ("sample_spectrum_reference", "background_spectrum_reference"),
    SECTION_LEVELS: ("residue_mass_mg",),
    SECTION_JUDGEMENT: ("required_limit_mg_m2", "judgement"),
}

METHOD_DIRECT = "direct"
METHOD_INDIRECT = "indirect"
VALID_METHOD_KINDS = (METHOD_DIRECT, METHOD_INDIRECT)

# Extra fields an indirect run owes.
INDIRECT_EXTRA_FIELDS = ("solvent", "recovery_fraction",
                         "blank_spectrum_reference")

JUDGEMENT_MEETS = "meets-the-required-level"
JUDGEMENT_ABOVE = "above-the-required-level"
JUDGEMENT_NOT_DEMONSTRATED = "not-demonstrated"

VALID_JUDGEMENTS = (JUDGEMENT_MEETS, JUDGEMENT_ABOVE,
                    JUDGEMENT_NOT_DEMONSTRATED)

REPORTABLE = "reportable"
REPORTABLE_WITH_OBSERVATIONS = "reportable-with-observations"
NOT_REPORTABLE = "not-reportable"

# Areal levels are quotients, so a value that should sit exactly on a
# bound can land a few units in the last place past it.
AREAL_TOLERANCE = 1.0e-12

# A stated level agrees with the recomputed one when it is inside half a
# step of the resolution it was written at.
DEFAULT_RESOLUTION_MG_M2 = 0.01


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return float(value)


def _optional_numeric(label, value, minimum=None, maximum=None):
    if value is None:
        return None
    return _numeric(label, value, minimum, maximum)


def section_fields(section):
    """Unconditionally required field names of one report section."""
    if section not in REPORT_SECTIONS:
        raise ValueError(
            "unknown report section %r (expected one of %s)"
            % (section, ", ".join(SECTION_ORDER))
        )
    return REPORT_SECTIONS[section]


def recompute_level(residue_mass_mg, sampled_area_m2, recovery_fraction=1.0):
    """Areal level in mg/m2 implied by a residue mass, an area and a recovery."""
    mass = _numeric("residue_mass_mg", residue_mass_mg, 0.0)
    area = _numeric("sampled_area_m2", sampled_area_m2, 0.0)
    recovery = _numeric("recovery_fraction", recovery_fraction, 0.0, 1.0)
    if area <= 0.0:
        raise ValueError("sampled_area_m2 must be greater than zero")
    if recovery <= 0.0:
        raise ValueError("recovery_fraction must be greater than zero")
    return mass / (area * recovery)


def values_agree(reported, recomputed, resolution=DEFAULT_RESOLUTION_MG_M2):
    """True when a stated level sits within half a step of the computed one."""
    stated = _numeric("reported", reported, 0.0)
    computed = _numeric("recomputed", recomputed, 0.0)
    step = _numeric("resolution", resolution, 0.0)
    if step <= 0.0:
        raise ValueError("resolution must be greater than zero")
    return abs(stated - computed) <= step / 2.0 + AREAL_TOLERANCE


def implied_judgement(level_mg_m2, required_limit_mg_m2, detected=True):
    """Judgement the report's own numbers support."""
    limit = _numeric("required_limit_mg_m2", required_limit_mg_m2, 0.0)
    value = _numeric("level_mg_m2", level_mg_m2, 0.0)
    if not isinstance(detected, bool):
        raise ValueError("detected must be a boolean")
    if value <= limit + AREAL_TOLERANCE:
        return JUDGEMENT_MEETS
    if not detected:
        return JUDGEMENT_NOT_DEMONSTRATED
    return JUDGEMENT_ABOVE


def required_fields(report):
    """Every field this particular report owes, in a stable order."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    fields = []
    for section in SECTION_ORDER:
        fields.extend(REPORT_SECTIONS[section])
    if report.get("method_kind") == METHOD_INDIRECT:
        fields.extend(INDIRECT_EXTRA_FIELDS)
    if report.get("identified_species"):
        fields.append("reference_spectrum_reference")
    if report.get("detected", True):
        fields.append("reported_level_mg_m2")
    else:
        fields.append("quantitation_limit_mg_m2")
    ordered = []
    for name in fields:
        if name not in ordered:
            ordered.append(name)
    return tuple(ordered)


def missing_fields(report):
    """Required fields this report leaves empty, in a stable order."""
    present = []
    for name in required_fields(report):
        value = report.get(name)
        if value is None:
            present.append(name)
        elif isinstance(value, str) and not value.strip():
            present.append(name)
    return tuple(present)


def validate_report(report):
    """Validate the typed content of a report record and normalize it."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    item = report.get("item")
    if not isinstance(item, str) or not item.strip():
        raise ValueError("report needs a non-empty string item")
    kind = report.get("method_kind")
    if kind is not None and kind not in VALID_METHOD_KINDS:
        raise ValueError(
            "method_kind %r must be one of %s"
            % (kind, ", ".join(VALID_METHOD_KINDS))
        )
    detected = report.get("detected", True)
    if not isinstance(detected, bool):
        raise ValueError("detected must be a boolean")
    judgement = report.get("judgement")
    if judgement is not None and judgement not in VALID_JUDGEMENTS:
        raise ValueError(
            "judgement %r must be one of %s"
            % (judgement, ", ".join(VALID_JUDGEMENTS))
        )
    if detected and report.get("reported_level_mg_m2") is None and \
            report.get("quantitation_limit_mg_m2") is not None:
        raise ValueError(
            "%s reports a detection but only a quantitation limit" % item.strip()
        )
    normalized = dict(report)
    normalized["item"] = item.strip()
    normalized["detected"] = detected
    _optional_numeric("sampled_area_m2", report.get("sampled_area_m2"), 0.0)
    _optional_numeric("residue_mass_mg", report.get("residue_mass_mg"), 0.0)
    _optional_numeric(
        "recovery_fraction", report.get("recovery_fraction"), 0.0, 1.0
    )
    _optional_numeric(
        "reported_level_mg_m2", report.get("reported_level_mg_m2"), 0.0
    )
    _optional_numeric(
        "quantitation_limit_mg_m2", report.get("quantitation_limit_mg_m2"), 0.0
    )
    _optional_numeric(
        "expanded_uncertainty_mg_m2", report.get("expanded_uncertainty_mg_m2"), 0.0
    )
    _optional_numeric(
        "reporting_resolution_mg_m2", report.get("reporting_resolution_mg_m2"), 0.0
    )
    _optional_numeric(
        "required_limit_mg_m2", report.get("required_limit_mg_m2"), 0.0
    )
    return normalized


def grade_report(report):
    """Grade one analysis report for content and self-consistency."""
    norm = validate_report(report)
    owed = required_fields(norm)
    absent = missing_fields(norm)
    blocking = ["missing-required-field:" + name for name in absent]
    observations = []
    recomputed = None

    resolution = norm.get("reporting_resolution_mg_m2") or DEFAULT_RESOLUTION_MG_M2

    if (
        norm.get("residue_mass_mg") is not None
        and norm.get("sampled_area_m2")
        and norm.get("reported_level_mg_m2") is not None
    ):
        recovery = norm.get("recovery_fraction")
        if recovery is None:
            recovery = 1.0
        recomputed = recompute_level(
            norm["residue_mass_mg"], norm["sampled_area_m2"], recovery
        )
        if not values_agree(norm["reported_level_mg_m2"], recomputed, resolution):
            blocking.append("stated-level-does-not-follow-from-the-reported-inputs")

    if norm.get("identified_species") and not norm.get(
        "reference_spectrum_reference"
    ):
        blocking.append("named-contaminant-without-a-reference-spectrum")

    stated_judgement = norm.get("judgement")
    limit = norm.get("required_limit_mg_m2")
    expected = None
    if stated_judgement is not None and limit is None:
        blocking.append("judgement-without-the-level-it-was-made-against")
    elif stated_judgement is not None and limit is not None:
        if norm["detected"]:
            basis = norm.get("reported_level_mg_m2")
        else:
            basis = norm.get("quantitation_limit_mg_m2")
        if basis is not None:
            expected = implied_judgement(basis, limit, norm["detected"])
            if expected != stated_judgement:
                blocking.append("judgement-contradicts-the-reported-numbers")

    uncertainty = norm.get("expanded_uncertainty_mg_m2")
    if uncertainty is None:
        observations.append("no-expanded-uncertainty-reported")
    elif uncertainty > 0.0 and resolution * 10.0 < uncertainty:
        observations.append("level-written-finer-than-its-uncertainty-supports")

    present_count = len(owed) - len(absent)
    completeness = float(present_count) / float(len(owed)) if owed else 1.0

    if blocking:
        verdict = NOT_REPORTABLE
    elif observations:
        verdict = REPORTABLE_WITH_OBSERVATIONS
    else:
        verdict = REPORTABLE

    return {
        "item": norm["item"],
        "required_fields": owed,
        "missing_fields": absent,
        "completeness": completeness,
        "recomputed_level_mg_m2": recomputed,
        "implied_judgement": expected,
        "stated_judgement": stated_judgement,
        "blocking_findings": blocking,
        "observations": observations,
        "verdict": verdict,
    }


def grade_report_set(reports):
    """Grade a set of reports and group them by verdict."""
    if not isinstance(reports, list) or not reports:
        raise ValueError("reports must be a non-empty list")
    graded = []
    seen = set()
    for report in reports:
        row = grade_report(report)
        if row["item"] in seen:
            raise ValueError("duplicate report item %r" % (row["item"],))
        seen.add(row["item"])
        graded.append(row)
    return {
        "reports": graded,
        "reportable": [r["item"] for r in graded if r["verdict"] == REPORTABLE],
        "with_observations": [
            r["item"] for r in graded
            if r["verdict"] == REPORTABLE_WITH_OBSERVATIONS
        ],
        "not_reportable": [
            r["item"] for r in graded if r["verdict"] == NOT_REPORTABLE
        ],
        "clear": all(r["verdict"] != NOT_REPORTABLE for r in graded),
    }
