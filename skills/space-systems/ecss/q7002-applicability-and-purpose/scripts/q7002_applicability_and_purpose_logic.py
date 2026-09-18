"""Applicability and purpose of the thermal-vacuum outgassing screening test.

Anchor: ECSS-Q-ST-70-02C, scope clause -- the screening test that measures the
total mass loss and the collected volatile condensable material of a candidate
space material, and the rule for deciding which materials owe that test at all.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide applicability from the usage, not from the material name. A material
   owes the screening when it is non-metallic, when the environment it sits in
   can carry its volatiles away, and when there is enough of it exposed to
   matter -- with the de-minimis mass set aside where a contamination-sensitive
   surface is in view.
2. Reuse valid existing data rather than re-testing: a screening result is a
   property of a material in a stated processed condition, so identical
   designation and cure state carry the result across.
3. Grade a screening result against the three acceptance quantities: total mass
   loss, collected volatile condensable material, and the recovered mass loss
   that removes regained water vapour from the total.
4. Separate a clean pass from the case that passes only once water vapour is
   removed; the latter is acceptable subject to a stated justification rather
   than silently on the same footing.
5. Close with one applicability answer, one screening verdict, and the reasons
   behind each.
"""

import math

__all__ = [
    "TML_LIMIT_PCT",
    "CVCM_LIMIT_PCT",
    "RML_LIMIT_PCT",
    "DE_MINIMIS_EXPOSED_MASS_G",
    "LIMIT_TOLERANCE_PCT",
    "MASS_TOLERANCE_G",
    "NON_METALLIC_CATEGORIES",
    "EXEMPT_CATEGORIES",
    "VOLATILE_CARRYING_ENVIRONMENTS",
    "SENSITIVE_SURFACES",
    "recovered_mass_loss_pct",
    "screening_required",
    "existing_data_is_reusable",
    "screening_verdict",
    "assess_material_screening",
]

# Screening acceptance quantities, in percent of the specimen's initial mass.
TML_LIMIT_PCT = 1.00
CVCM_LIMIT_PCT = 0.10
RML_LIMIT_PCT = 1.00

# Below this exposed mass a material is not screened on its own account, unless
# a contamination-sensitive surface is in view of it.
DE_MINIMIS_EXPOSED_MASS_G = 1.0

# Percent figures are reported to two decimals; an exactly-on-limit result is a
# representation question absorbed here rather than by moving the limit.
LIMIT_TOLERANCE_PCT = 1e-9

# The same argument applied to the de-minimis mass comparison.
MASS_TOLERANCE_G = 1e-9

NON_METALLIC_CATEGORIES = (
    "adhesive",
    "conformal-coating",
    "elastomer",
    "encapsulant",
    "film",
    "foam",
    "lubricant",
    "paint",
    "polymer",
    "potting-compound",
    "composite-matrix",
    "tape",
    "thermal-control-coating",
    "wire-insulation",
)

EXEMPT_CATEGORIES = (
    "ceramic",
    "glass",
    "metal",
    "metal-alloy",
    "inorganic-pigment",
)

# Environments in which released volatiles can leave the material and reach
# something else; a sealed pressurised volume and a ground-only fit cannot.
VOLATILE_CARRYING_ENVIRONMENTS = (
    "vacuum",
    "vented-volume",
    "unvented-volume-with-leak-path",
)

SENSITIVE_SURFACES = (
    "optical-element",
    "detector-focal-plane",
    "solar-array-cell",
    "thermal-control-radiator",
    "cryogenic-surface",
    "star-tracker-baffle",
)


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def _percent(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number of percent, got %r" % (label, value))
    pct = float(value)
    if not math.isfinite(pct):
        raise ValueError("%s must be finite" % label)
    if pct < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, pct))
    if pct > 100.0:
        raise ValueError("%s is a percentage of the initial mass and cannot exceed 100, got %g"
                         % (label, pct))
    return pct


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def recovered_mass_loss_pct(tml_pct, water_vapour_regained_pct):
    """Return the total mass loss with regained water vapour removed."""
    tml = _percent(tml_pct, "tml_pct")
    wvr = _percent(water_vapour_regained_pct, "water_vapour_regained_pct")
    if wvr > tml + LIMIT_TOLERANCE_PCT:
        raise ValueError(
            "regained water vapour %g%% exceeds the total mass loss %g%%; the two "
            "are measured on the same specimen and cannot disagree that way" % (wvr, tml)
        )
    return max(0.0, tml - wvr)


def screening_required(usage):
    """Decide whether a usage owes the outgassing screening test.

    usage keys: material_category, environment, exposed_mass_g, optional
    surfaces_in_view (sequence) and existing_data (mapping).
    """
    _require_mapping(usage, "usage")
    for key in ("material_category", "environment", "exposed_mass_g"):
        if key not in usage:
            raise ValueError("usage missing required key '%s'" % key)
    category = _token(usage["material_category"], "material_category")
    environment = _token(usage["environment"], "environment")
    mass = usage["exposed_mass_g"]
    if not isinstance(mass, (int, float)) or isinstance(mass, bool):
        raise ValueError("exposed_mass_g must be a real number, got %r" % (mass,))
    mass = float(mass)
    if not math.isfinite(mass) or mass < 0.0:
        raise ValueError("exposed_mass_g must be non-negative and finite, got %r"
                         % (usage["exposed_mass_g"],))

    reasons = []
    if category in EXEMPT_CATEGORIES:
        reasons.append(
            "category '%s' has no organic volatile inventory to screen" % category
        )
        return {"required": False, "reasons": reasons, "reuse": None}
    if category not in NON_METALLIC_CATEGORIES:
        reasons.append(
            "category '%s' is not on the screened or the exempt list; treat it as "
            "screened until it is placed on one" % category
        )
    if environment not in VOLATILE_CARRYING_ENVIRONMENTS:
        reasons.append(
            "environment '%s' cannot carry released volatiles to another surface"
            % environment
        )
        return {"required": False, "reasons": reasons, "reuse": None}

    surfaces = usage.get("surfaces_in_view") or []
    if not isinstance(surfaces, (list, tuple, set, frozenset)):
        raise ValueError("surfaces_in_view must be a sequence of surface identifiers")
    sensitive = sorted({_token(s, "surfaces_in_view entry") for s in surfaces}
                       & set(SENSITIVE_SURFACES))

    if mass < DE_MINIMIS_EXPOSED_MASS_G - MASS_TOLERANCE_G and not sensitive:
        reasons.append(
            "exposed mass of %g g is below the %g g de-minimis and no "
            "contamination-sensitive surface is in view" % (mass, DE_MINIMIS_EXPOSED_MASS_G)
        )
        return {"required": False, "reasons": reasons, "reuse": None}

    if sensitive:
        reasons.append(
            "contamination-sensitive surfaces in view: %s" % ", ".join(sensitive)
        )
    else:
        reasons.append(
            "exposed mass of %g g is at or above the %g g de-minimis"
            % (mass, DE_MINIMIS_EXPOSED_MASS_G)
        )
    reasons.append("environment '%s' carries released volatiles" % environment)

    existing = usage.get("existing_data")
    if existing is not None and existing_data_is_reusable(usage, existing):
        reasons.append(
            "valid screening data already exists for this material in this processed "
            "condition; reuse it rather than re-testing"
        )
        return {"required": False, "reasons": reasons, "reuse": existing.get("reference")}
    return {"required": True, "reasons": reasons, "reuse": None}


def existing_data_is_reusable(usage, existing_data):
    """Decide whether existing screening data covers this usage."""
    _require_mapping(usage, "usage")
    _require_mapping(existing_data, "existing_data")
    for key in ("reference", "material_designation", "processed_condition"):
        if not existing_data.get(key):
            return False
    designation = usage.get("material_designation")
    condition = usage.get("processed_condition")
    if not designation or not condition:
        return False
    return (
        _token(designation, "material_designation")
        == _token(existing_data["material_designation"], "existing material_designation")
        and _token(condition, "processed_condition")
        == _token(existing_data["processed_condition"], "existing processed_condition")
    )


def _within(value, limit):
    return value < limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE_PCT)


def screening_verdict(tml_pct, cvcm_pct, water_vapour_regained_pct=None):
    """Grade a screening result against the acceptance quantities."""
    tml = _percent(tml_pct, "tml_pct")
    cvcm = _percent(cvcm_pct, "cvcm_pct")
    findings = []
    rml = None
    if water_vapour_regained_pct is not None:
        rml = recovered_mass_loss_pct(tml, water_vapour_regained_pct)

    cvcm_ok = _within(cvcm, CVCM_LIMIT_PCT)
    tml_ok = _within(tml, TML_LIMIT_PCT)
    rml_ok = rml is not None and _within(rml, RML_LIMIT_PCT)

    if not cvcm_ok:
        findings.append(
            "collected volatile condensable material of %g%% is above the %g%% limit"
            % (cvcm, CVCM_LIMIT_PCT)
        )
    if not tml_ok:
        findings.append(
            "total mass loss of %g%% is above the %g%% limit" % (tml, TML_LIMIT_PCT)
        )

    if not cvcm_ok:
        verdict = "fail"
    elif tml_ok:
        verdict = "pass"
    elif rml_ok:
        verdict = "conditional"
        findings.append(
            "recovered mass loss of %g%% is within the %g%% limit once regained water "
            "vapour is removed; acceptance needs the water-regain basis stated"
            % (rml, RML_LIMIT_PCT)
        )
    else:
        verdict = "fail"
        if rml is not None:
            findings.append(
                "recovered mass loss of %g%% is still above the %g%% limit"
                % (rml, RML_LIMIT_PCT)
            )
    return {
        "tml_pct": tml,
        "cvcm_pct": cvcm,
        "rml_pct": rml,
        "verdict": verdict,
        "findings": findings,
    }


def assess_material_screening(usage, results=None):
    """Combine the applicability decision with a screening verdict when results exist."""
    applicability = screening_required(usage)
    verdict = None
    if results is not None:
        _require_mapping(results, "results")
        for key in ("tml_pct", "cvcm_pct"):
            if key not in results:
                raise ValueError("results missing required key '%s'" % key)
        verdict = screening_verdict(
            results["tml_pct"], results["cvcm_pct"], results.get("water_vapour_regained_pct")
        )
    if applicability["required"] and verdict is None:
        status = "screening-owed"
    elif not applicability["required"]:
        status = "screening-not-required"
    elif verdict["verdict"] == "pass":
        status = "screened-acceptable"
    elif verdict["verdict"] == "conditional":
        status = "screened-acceptable-with-justification"
    else:
        status = "screened-rejected"
    return {
        "applicability": applicability,
        "screening": verdict,
        "status": status,
    }
