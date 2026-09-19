"""Content audit of a mechanical test report on metallic materials.

Anchor: ECSS-Q-ST-70-45 reporting clause (what a mechanical test report has to
carry: the specimens, the conditions they were tested under, the results and
the raw data behind them). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Build the required section set from the test method, so a fatigue report
   owes its loading spectrum and run-out criterion and a fracture report owes
   its precrack record, while both owe the common laboratory, material,
   specimen, condition, result, raw-data and authorisation sections.
2. Compare the delivered report against that set and report the gaps in the
   order the set requires them, so the chase list reads in the order the
   laboratory will work through it.
3. Audit the specimen register against the results table: a result quoting a
   specimen nobody registered is orphaned, and a registered specimen with no
   result is an untested piece that the report silently dropped.
4. Re-derive the reported tensile properties from the retained raw data and
   report every reported value that the raw data does not reproduce, because
   an unreproducible number is the defect the raw-data requirement exists to
   catch.
5. Return the completeness ratio, the ordered gaps, the specimen findings and
   the reproduction findings with a single acceptance verdict.
"""

import math

__all__ = [
    "BASE_SECTIONS",
    "METHOD_SECTIONS",
    "REPRODUCTION_REL_TOL",
    "known_methods",
    "required_sections",
    "normalise_sections",
    "missing_sections",
    "completeness_ratio",
    "specimen_audit",
    "original_area_mm2",
    "derive_tensile_properties",
    "reproduction_findings",
    "assess_test_report",
]

# Sections every mechanical test report owes whatever the method was.
BASE_SECTIONS = (
    "laboratory-identification",
    "material-identification",
    "test-method-reference",
    "specimen-register",
    "test-conditions",
    "results-table",
    "raw-data-retention",
    "validity-statement",
    "authorisation",
)

# Sections a given method adds on top of the base set.
METHOD_SECTIONS = {
    "tensile": ("stress-strain-curves",),
    "compression": ("stress-strain-curves",),
    "shear": (),
    "hardness": ("indentation-record",),
    "impact": ("absorbed-energy-record", "fracture-appearance"),
    "fatigue": ("loading-spectrum", "run-out-criterion", "stress-life-points"),
    "fracture": ("precrack-record", "crack-length-record", "size-validity-criterion"),
}

# A reported property is treated as reproduced when it agrees with the value
# re-derived from the raw data to this relative tolerance. Reports round their
# printed values, so an exact match is not the standard being applied.
REPRODUCTION_REL_TOL = 5e-3


def known_methods():
    """Return the sorted test methods this audit carries a section set for."""
    return sorted(METHOD_SECTIONS)


def _clean_token(value, label):
    """Return a non-empty lowercase token, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _positive(value, label):
    """Return a strictly positive finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def required_sections(method):
    """Return the ordered section set a report of this method owes."""
    token = _clean_token(method, "method")
    if token not in METHOD_SECTIONS:
        raise ValueError(
            "unknown test method %r; known methods are %s"
            % (method, ", ".join(known_methods()))
        )
    return tuple(BASE_SECTIONS) + tuple(METHOD_SECTIONS[token])


def normalise_sections(sections):
    """Return the delivered section names as a de-duplicated lowercase set."""
    if not isinstance(sections, (list, tuple, set, frozenset)):
        raise ValueError("sections must be a sequence of section names")
    cleaned = set()
    for index, item in enumerate(sorted(sections) if isinstance(sections, (set, frozenset)) else sections):
        cleaned.add(_clean_token(item, "sections[%d]" % index))
    return cleaned


def missing_sections(delivered, method):
    """Return the required sections absent from the report, in required order."""
    present = normalise_sections(delivered)
    return [name for name in required_sections(method) if name not in present]


def completeness_ratio(delivered, method):
    """Return the fraction of the required section set the report delivers."""
    required = required_sections(method)
    gaps = missing_sections(delivered, method)
    return (len(required) - len(gaps)) / float(len(required))


def specimen_audit(specimens, results):
    """Return the orphaned results and the registered-but-unreported specimens."""
    if not isinstance(specimens, (list, tuple)):
        raise ValueError("specimens must be a sequence of specimen identifiers")
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence of result records")
    registered = []
    for index, item in enumerate(specimens):
        token = _clean_token(item, "specimens[%d]" % index)
        if token in registered:
            raise ValueError("specimen identifier %r is registered twice" % token)
        registered.append(token)
    reported = []
    for index, record in enumerate(results):
        if not isinstance(record, dict):
            raise ValueError("results[%d] must be a mapping" % index)
        if "specimen" not in record:
            raise ValueError("results[%d] does not name a specimen" % index)
        reported.append(_clean_token(record["specimen"], "results[%d]['specimen']" % index))
    orphaned = [name for name in reported if name not in registered]
    unreported = [name for name in registered if name not in reported]
    return {
        "registered": registered,
        "reported": reported,
        "orphaned_results": orphaned,
        "unreported_specimens": unreported,
    }


def original_area_mm2(diameter_mm):
    """Return the original cross-section area of a round test piece."""
    diameter = _positive(diameter_mm, "diameter_mm")
    return math.pi * diameter * diameter / 4.0


def derive_tensile_properties(raw):
    """Re-derive the reportable tensile properties from the retained raw data.

    raw keys: original_diameter_mm, original_gauge_length_mm, yield_force_kn,
    max_force_kn, final_gauge_length_mm, final_diameter_mm.
    """
    if not isinstance(raw, dict):
        raise ValueError("raw must be a mapping of retained measurements")
    for key in (
        "original_diameter_mm",
        "original_gauge_length_mm",
        "yield_force_kn",
        "max_force_kn",
        "final_gauge_length_mm",
        "final_diameter_mm",
    ):
        if key not in raw:
            raise ValueError("raw data missing required measurement '%s'" % key)
    d0 = _positive(raw["original_diameter_mm"], "original_diameter_mm")
    l0 = _positive(raw["original_gauge_length_mm"], "original_gauge_length_mm")
    fy = _positive(raw["yield_force_kn"], "yield_force_kn")
    fmax = _positive(raw["max_force_kn"], "max_force_kn")
    lu = _positive(raw["final_gauge_length_mm"], "final_gauge_length_mm")
    du = _positive(raw["final_diameter_mm"], "final_diameter_mm")
    if fy > fmax:
        raise ValueError(
            "yield force %g kN exceeds maximum force %g kN; the raw data is inconsistent"
            % (fy, fmax)
        )
    if lu < l0:
        raise ValueError(
            "final gauge length %g mm is shorter than the original %g mm" % (lu, l0)
        )
    if du > d0:
        raise ValueError(
            "final diameter %g mm exceeds the original %g mm" % (du, d0)
        )
    a0 = original_area_mm2(d0)
    au = original_area_mm2(du)
    return {
        "original_area_mm2": a0,
        "final_area_mm2": au,
        "yield_strength_mpa": fy * 1000.0 / a0,
        "tensile_strength_mpa": fmax * 1000.0 / a0,
        "elongation_percent": (lu - l0) / l0 * 100.0,
        "reduction_of_area_percent": (a0 - au) / a0 * 100.0,
    }


def reproduction_findings(reported, derived, rel_tol=REPRODUCTION_REL_TOL):
    """Return one finding per reported property the raw data does not reproduce."""
    if not isinstance(reported, dict):
        raise ValueError("reported must be a mapping of printed property values")
    if not isinstance(derived, dict):
        raise ValueError("derived must be a mapping of re-derived property values")
    if not isinstance(rel_tol, (int, float)) or isinstance(rel_tol, bool):
        raise ValueError("rel_tol must be a real number")
    tolerance = float(rel_tol)
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("rel_tol must be positive and finite, got %r" % (rel_tol,))
    findings = []
    for name in sorted(reported):
        if name not in derived:
            findings.append(
                "reported property '%s' has no raw-data basis in the retained file" % name
            )
            continue
        printed = reported[name]
        if not isinstance(printed, (int, float)) or isinstance(printed, bool):
            raise ValueError("reported['%s'] must be a real number" % name)
        printed = float(printed)
        if not math.isfinite(printed):
            raise ValueError("reported['%s'] must be finite" % name)
        basis = float(derived[name])
        if not math.isclose(printed, basis, rel_tol=tolerance, abs_tol=0.0):
            findings.append(
                "reported '%s' of %.4g is not reproduced by the raw data value %.4g"
                % (name, printed, basis)
            )
    return findings


def assess_test_report(report):
    """Run the full reporting-clause content audit on one test report.

    report keys: method, sections, specimens, results, optional raw_data and
    reported_properties for the tensile reproduction check.
    """
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    for key in ("method", "sections", "specimens", "results"):
        if key not in report:
            raise ValueError("report missing required key '%s'" % key)
    method = _clean_token(report["method"], "method")
    gaps = missing_sections(report["sections"], method)
    ratio = completeness_ratio(report["sections"], method)
    specimens = specimen_audit(report["specimens"], report["results"])
    findings = []
    for name in gaps:
        findings.append("required section '%s' is absent from the report" % name)
    for name in specimens["orphaned_results"]:
        findings.append(
            "results table quotes specimen '%s', which the specimen register does not carry"
            % name
        )
    for name in specimens["unreported_specimens"]:
        findings.append(
            "specimen '%s' is registered but no result is reported for it" % name
        )
    reproduction = []
    derived = None
    raw = report.get("raw_data")
    printed = report.get("reported_properties")
    if raw is not None and printed is not None:
        derived = derive_tensile_properties(raw)
        reproduction = reproduction_findings(printed, derived)
        findings.extend(reproduction)
    elif printed is not None and raw is None:
        findings.append(
            "properties are printed but no raw data is retained, so nothing can be reproduced"
        )
    return {
        "method": method,
        "required_sections": list(required_sections(method)),
        "missing_sections": gaps,
        "completeness_ratio": ratio,
        "specimen_audit": specimens,
        "derived_properties": derived,
        "reproduction_findings": reproduction,
        "findings": findings,
        "acceptable": not findings,
    }
