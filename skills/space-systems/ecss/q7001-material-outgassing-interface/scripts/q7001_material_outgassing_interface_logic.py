"""Outgassing screening of a material facing a contamination sensitive surface.

Anchor: ECSS-Q-ST-70-01C cleanliness and contamination control, the screening
it imposes on a material used in view of a sensitive surface, using the
outgassing figures produced by the ECSS-Q-ST-70-02C micro-balance method
(total mass loss, recovered mass loss after water vapour regain, and the
collected volatile condensable fraction). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the measured outgassing record: percentages in range, the
   recovered mass loss no larger than the total, and the regain consistent
   with the pair when all three are reported.
2. Take the recovered figure over the total whenever a regain was measured:
   re-adsorbed water is not a contaminant the surface ever sees.
3. Tighten the condensable limit for the grade of the surface in view, so a
   cryogenic detector does not inherit a structure-grade limit.
4. Grade the material against the mass-loss and condensable limits and name
   which of them it exceeds.
5. Estimate the deposit the interface actually produces: the condensable
   fraction of the exposed mass, transported by the view factor and by the
   source to collector temperature difference, spread over the surface area.
6. Compare that areal deposit with the surface budget and return the
   disposition: acceptance, vacuum bakeout and retest, shielding or
   relocation, or refusal.
"""

import math

__all__ = [
    "TML_LIMIT_PCT",
    "CVCM_LIMIT_PCT",
    "RML_LIMIT_PCT",
    "SURFACE_GRADES",
    "REGAIN_TOLERANCE_PCT",
    "BUDGET_TOLERANCE_NG_CM2",
    "CONDENSATION_SPAN_C",
    "normalise_identifier",
    "validate_outgassing_record",
    "effective_mass_loss_pct",
    "surface_grade",
    "screening_limits",
    "screening_findings",
    "condensation_fraction",
    "areal_deposit_ng_cm2",
    "budget_findings",
    "disposition",
    "assess_material_interface",
]

# Screening limits the micro-balance method is read against, in percent of the
# conditioned specimen mass.
TML_LIMIT_PCT = 1.0
CVCM_LIMIT_PCT = 0.10
RML_LIMIT_PCT = 1.0

# A measured triple is reported to two decimals, so the regain consistency
# check absorbs reporting granularity rather than demanding exact arithmetic.
REGAIN_TOLERANCE_PCT = 1e-9

# Budget comparisons are a difference of computed quantities; an interface
# sitting exactly on its budget is a pass, not a representation accident.
BUDGET_TOLERANCE_NG_CM2 = 1e-9

# Above this source-to-collector temperature difference the condensable
# fraction arriving at the surface is taken as fully retained.
CONDENSATION_SPAN_C = 40.0

# Grades of surface a material can face. Each carries the areal deposit the
# surface can absorb over the mission phase, in nanograms per square
# centimetre, and the factor its grade applies to the condensable limit.
SURFACE_GRADES = {
    "cryogenic-detector": {"budget_ng_cm2": 10.0, "cvcm_factor": 0.3},
    "optical-window": {"budget_ng_cm2": 40.0, "cvcm_factor": 0.5},
    "thermal-radiator": {"budget_ng_cm2": 100.0, "cvcm_factor": 1.0},
    "solar-array-cell": {"budget_ng_cm2": 150.0, "cvcm_factor": 1.0},
    "antenna-reflector": {"budget_ng_cm2": 300.0, "cvcm_factor": 1.0},
    "structure": {"budget_ng_cm2": 1000.0, "cvcm_factor": 1.0},
}


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _positive_real(value, label, allow_zero=False):
    """Return value as a finite float, raising when it is not usable."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if allow_zero:
        if number < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, number))
    elif number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _real(value, label):
    """Return value as a finite float of either sign (a temperature)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _percentage(value, label):
    """Return a percentage between zero and one hundred."""
    number = _positive_real(value, label, allow_zero=True)
    if number > 100.0:
        raise ValueError("%s must not exceed 100 percent, got %g" % (label, number))
    return number


def validate_outgassing_record(record):
    """Return the normalised micro-balance record for one material."""
    if not isinstance(record, dict):
        raise ValueError("outgassing record must be a mapping")
    for key in ("material", "tml_pct", "cvcm_pct"):
        if key not in record:
            raise ValueError("outgassing record is missing '%s'" % key)
    material = normalise_identifier(record["material"], "material")
    tml = _percentage(record["tml_pct"], "tml_pct")
    cvcm = _percentage(record["cvcm_pct"], "cvcm_pct")
    if cvcm > tml:
        raise ValueError(
            "cvcm_pct %g cannot exceed tml_pct %g; the condensed fraction is part "
            "of the mass lost" % (cvcm, tml)
        )
    rml = record.get("rml_pct")
    regain = record.get("water_vapour_regain_pct")
    if rml is not None:
        rml = _percentage(rml, "rml_pct")
        if rml > tml:
            raise ValueError("rml_pct %g cannot exceed tml_pct %g" % (rml, tml))
    if regain is not None:
        regain = _percentage(regain, "water_vapour_regain_pct")
        if rml is None:
            rml = tml - regain
            if rml < 0.0:
                raise ValueError(
                    "water_vapour_regain_pct %g exceeds tml_pct %g" % (regain, tml)
                )
        elif not math.isclose(
            tml - regain, rml, rel_tol=0.0, abs_tol=REGAIN_TOLERANCE_PCT
        ):
            raise ValueError(
                "reported triple is inconsistent: tml %g minus regain %g is not "
                "rml %g" % (tml, regain, rml)
            )
    return {
        "material": material,
        "tml_pct": tml,
        "cvcm_pct": cvcm,
        "rml_pct": rml,
        "water_vapour_regain_pct": regain,
    }


def effective_mass_loss_pct(record):
    """Return the mass-loss figure the screening is read against."""
    if not isinstance(record, dict) or "tml_pct" not in record:
        raise ValueError("record must be a validated outgassing record")
    if record.get("rml_pct") is None:
        return record["tml_pct"]
    return record["rml_pct"]


def surface_grade(surface):
    """Return the grade entry of a contamination sensitive surface."""
    key = normalise_identifier(surface, "surface")
    if key not in SURFACE_GRADES:
        raise ValueError(
            "surface must be one of %s, got %r"
            % ("/".join(sorted(SURFACE_GRADES)), surface)
        )
    entry = SURFACE_GRADES[key]
    return {"surface": key, "budget_ng_cm2": entry["budget_ng_cm2"],
            "cvcm_factor": entry["cvcm_factor"]}


def screening_limits(surface):
    """Return the mass-loss and condensable limits for a surface grade."""
    grade = surface_grade(surface)
    return {
        "surface": grade["surface"],
        "mass_loss_limit_pct": TML_LIMIT_PCT,
        "cvcm_limit_pct": CVCM_LIMIT_PCT * grade["cvcm_factor"],
        "budget_ng_cm2": grade["budget_ng_cm2"],
    }


def screening_findings(record, surface):
    """Return which screening limits a material exceeds in view of a surface."""
    limits = screening_limits(surface)
    loss = effective_mass_loss_pct(record)
    findings = []
    mass_loss_exceeded = loss > limits["mass_loss_limit_pct"] and not math.isclose(
        loss, limits["mass_loss_limit_pct"], rel_tol=0.0, abs_tol=REGAIN_TOLERANCE_PCT
    )
    cvcm_exceeded = record["cvcm_pct"] > limits["cvcm_limit_pct"] and not math.isclose(
        record["cvcm_pct"], limits["cvcm_limit_pct"],
        rel_tol=0.0, abs_tol=REGAIN_TOLERANCE_PCT
    )
    if mass_loss_exceeded:
        findings.append(
            "mass loss %.3f percent exceeds the %.3f percent screening limit"
            % (loss, limits["mass_loss_limit_pct"])
        )
    if cvcm_exceeded:
        findings.append(
            "condensable fraction %.4f percent exceeds the %.4f percent limit the "
            "%s grade applies" % (record["cvcm_pct"], limits["cvcm_limit_pct"],
                                  limits["surface"])
        )
    return {
        "mass_loss_pct": loss,
        "mass_loss_exceeded": mass_loss_exceeded,
        "cvcm_exceeded": cvcm_exceeded,
        "limits": limits,
        "findings": findings,
    }


def condensation_fraction(source_temp_c, surface_temp_c, span_c=CONDENSATION_SPAN_C):
    """Return the retained fraction of condensable arriving at the surface.

    Nothing is retained by a collector at or above the source temperature; the
    retained fraction rises linearly with the temperature difference and is
    complete once the difference reaches the span.
    """
    source = _real(source_temp_c, "source_temp_c")
    collector = _real(surface_temp_c, "surface_temp_c")
    span = _positive_real(span_c, "span_c")
    difference = source - collector
    if difference <= 0.0:
        return 0.0
    if difference >= span:
        return 1.0
    return difference / span


def areal_deposit_ng_cm2(record, exposed_mass_g, view_factor,
                         surface_area_cm2, source_temp_c, surface_temp_c):
    """Return the deposit the interface leaves on the surface, ng per cm2."""
    if not isinstance(record, dict) or "cvcm_pct" not in record:
        raise ValueError("record must be a validated outgassing record")
    mass = _positive_real(exposed_mass_g, "exposed_mass_g")
    area = _positive_real(surface_area_cm2, "surface_area_cm2")
    factor = _positive_real(view_factor, "view_factor", allow_zero=True)
    if factor > 1.0:
        raise ValueError("view_factor must not exceed unity, got %g" % factor)
    retained = condensation_fraction(source_temp_c, surface_temp_c)
    condensable_g = mass * record["cvcm_pct"] / 100.0
    return condensable_g * factor * retained * 1.0e9 / area


def budget_findings(deposit_ng_cm2, budget_ng_cm2):
    """Return the finding list for a deposit against a surface budget."""
    deposit = _positive_real(deposit_ng_cm2, "deposit_ng_cm2", allow_zero=True)
    budget = _positive_real(budget_ng_cm2, "budget_ng_cm2")
    if deposit > budget and not math.isclose(
        deposit, budget, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE_NG_CM2
    ):
        return [
            "estimated deposit %.2f ng/cm2 exceeds the %.2f ng/cm2 surface budget"
            % (deposit, budget)
        ]
    return []


def disposition(screening, over_budget, shielded):
    """Return the disposition of a material at a sensitive-surface interface."""
    if not isinstance(screening, dict) or "cvcm_exceeded" not in screening:
        raise ValueError("screening must be the mapping returned by screening_findings")
    if shielded:
        return "accepted-behind-shield"
    if screening["cvcm_exceeded"]:
        return "refused-in-view-of-surface"
    if screening["mass_loss_exceeded"]:
        return "vacuum-bakeout-and-retest"
    if over_budget:
        return "relocate-or-reduce-exposed-area"
    return "accepted"


def assess_material_interface(spec):
    """Screen one material at one sensitive-surface interface end to end.

    spec keys: record (the micro-balance triple), surface, exposed_mass_g,
    view_factor, surface_area_cm2, source_temp_c, surface_temp_c.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("record", "surface", "exposed_mass_g", "view_factor",
                "surface_area_cm2", "source_temp_c", "surface_temp_c"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    record = validate_outgassing_record(spec["record"])
    screening = screening_findings(record, spec["surface"])
    deposit = areal_deposit_ng_cm2(
        record,
        spec["exposed_mass_g"],
        spec["view_factor"],
        spec["surface_area_cm2"],
        spec["source_temp_c"],
        spec["surface_temp_c"],
    )
    budget = screening["limits"]["budget_ng_cm2"]
    over = bool(budget_findings(deposit, budget))
    shielded = float(spec["view_factor"]) == 0.0
    findings = list(screening["findings"])
    findings.extend(budget_findings(deposit, budget))
    if shielded and findings:
        findings.append(
            "material is out of line of sight of the surface; the screening "
            "exceedances above are carried as a housekeeping note"
        )
    verdict = disposition(screening, over, shielded)
    return {
        "material": record["material"],
        "surface": screening["limits"]["surface"],
        "mass_loss_pct": screening["mass_loss_pct"],
        "cvcm_pct": record["cvcm_pct"],
        "cvcm_limit_pct": screening["limits"]["cvcm_limit_pct"],
        "deposit_ng_cm2": deposit,
        "budget_ng_cm2": budget,
        "within_budget": not over,
        "findings": findings,
        "disposition": verdict,
    }
