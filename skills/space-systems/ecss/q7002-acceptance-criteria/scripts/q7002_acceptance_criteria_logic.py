"""Screening acceptance of outgassing results against an application class.

Anchor: ECSS-Q-ST-70-02C, the acceptance clause of the thermal-vacuum
outgassing screening test (paraphrased into an implementable procedure;
no standard text is reproduced).

Procedure implemented here:

1. A screening result is a pair: a total mass loss and a condensable
   fraction. Both are percentages of the mass the specimen started with,
   and both carry a limit. Passing one and failing the other is a
   failure.
2. The limits are a property of where the material is used, not of the
   material. A part beside a cold optic is held far tighter on the
   condensable figure than the same part inside a warm sealed box.
3. Mass loss that was only regained water can be credited back. The
   recovered mass loss is the total loss with the water-vapour regained
   figure removed, and where the application allows that credit the
   loss is graded on the recovered figure instead. A cold surface does
   not allow it: water deposits there like anything else.
4. A condensable figure below the balance quantification floor is a
   bound, not a value. It demonstrates compliance only when the bound
   itself sits at or under the limit.
5. A material over a limit is not automatically out. It can be carried
   on an approved deviation, but only with both a deviation reference
   and a contamination assessment behind it; either one alone is an
   assertion.

Stdlib only, offline, deterministic.
"""

BASIS_TOTAL_MASS_LOSS = "total-mass-loss"
BASIS_RECOVERED_MASS_LOSS = "recovered-mass-loss"

# Limits in percent of the initial specimen mass, by application class.
# "water_credit" says whether the recovered-mass-loss substitution is
# available for that application.
APPLICATION_CLASS_LIMITS = {
    "general-screening": {
        "mass_loss_limit_pct": 1.00,
        "cvcm_limit_pct": 0.10,
        "water_credit": True,
    },
    "optically-sensitive-hardware": {
        "mass_loss_limit_pct": 1.00,
        "cvcm_limit_pct": 0.01,
        "water_credit": True,
    },
    "cryogenic-surface-proximity": {
        "mass_loss_limit_pct": 0.50,
        "cvcm_limit_pct": 0.01,
        "water_credit": False,
    },
}

VALID_APPLICATION_CLASSES = tuple(sorted(APPLICATION_CLASS_LIMITS))

ACCEPTED = "accepted"
ACCEPTED_ON_DEVIATION = "accepted-on-approved-deviation"
REJECTED = "rejected"

# Screening values are quotients of weighings scaled by 100, so a result
# sitting exactly on a limit can land a few units in the last place past
# it. This tolerance absorbs that representation error only; no limit is
# ever widened.
PERCENT_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _optional_numeric(label, value, minimum=None):
    if value is None:
        return None
    return _numeric(label, value, minimum)


def class_limits(application_class):
    """Limits for one application class, as a copied mapping."""
    if application_class not in APPLICATION_CLASS_LIMITS:
        raise ValueError(
            "unknown application class %r (expected one of %s)"
            % (application_class, ", ".join(VALID_APPLICATION_CLASSES))
        )
    return dict(APPLICATION_CLASS_LIMITS[application_class])


def validate_result(result):
    """Validate one screening result record and return a normalized copy."""
    if not isinstance(result, dict):
        raise ValueError("result must be a mapping")
    material = result.get("material")
    if not isinstance(material, str) or not material.strip():
        raise ValueError("result needs a non-empty string material")
    tml = _numeric("%s total_mass_loss_pct" % material,
                   result.get("total_mass_loss_pct"), 0.0)
    cvcm = _optional_numeric("%s cvcm_pct" % material, result.get("cvcm_pct"), 0.0)
    floor = _optional_numeric("%s cvcm_floor_pct" % material,
                              result.get("cvcm_floor_pct"), 0.0)
    if cvcm is None and floor is None:
        raise ValueError(
            "%s reports neither a cvcm_pct nor a cvcm_floor_pct bound" % material
        )
    if cvcm is not None and cvcm > tml + PERCENT_TOLERANCE:
        raise ValueError(
            "%s condensed %r percent from a total loss of %r percent"
            % (material, cvcm, tml)
        )
    wvr = _optional_numeric("%s water_vapour_regained_pct" % material,
                            result.get("water_vapour_regained_pct"), 0.0)
    if wvr is not None and wvr > tml + PERCENT_TOLERANCE:
        raise ValueError(
            "%s regained %r percent after losing %r percent" % (material, wvr, tml)
        )
    deviation = result.get("deviation_reference")
    if deviation is not None and not isinstance(deviation, str):
        raise ValueError("%s deviation_reference must be a string" % material)
    assessment = result.get("contamination_assessment_reference")
    if assessment is not None and not isinstance(assessment, str):
        raise ValueError(
            "%s contamination_assessment_reference must be a string" % material
        )
    return {
        "material": material,
        "total_mass_loss_pct": tml,
        "cvcm_pct": cvcm,
        "cvcm_floor_pct": floor,
        "water_vapour_regained_pct": wvr,
        "deviation_reference": deviation or None,
        "contamination_assessment_reference": assessment or None,
    }


def recovered_mass_loss_pct(total_mass_loss_pct, water_vapour_regained_pct):
    """Total mass loss with the regained water removed, in percent."""
    tml = _numeric("total_mass_loss_pct", total_mass_loss_pct, 0.0)
    wvr = _numeric("water_vapour_regained_pct", water_vapour_regained_pct, 0.0)
    if wvr > tml + PERCENT_TOLERANCE:
        raise ValueError(
            "water_vapour_regained_pct %r exceeds total_mass_loss_pct %r"
            % (wvr, tml)
        )
    return max(tml - wvr, 0.0)


def mass_loss_basis(result, application_class):
    """Return (basis name, graded value) for the mass-loss criterion."""
    norm = validate_result(result)
    limits = class_limits(application_class)
    wvr = norm["water_vapour_regained_pct"]
    if wvr is not None and limits["water_credit"]:
        return (
            BASIS_RECOVERED_MASS_LOSS,
            recovered_mass_loss_pct(norm["total_mass_loss_pct"], wvr),
        )
    return BASIS_TOTAL_MASS_LOSS, norm["total_mass_loss_pct"]


def within_limit(value, limit):
    """True when a screening value sits at or under its limit."""
    val = _numeric("value", value)
    lim = _numeric("limit", limit)
    return val <= lim + PERCENT_TOLERANCE


def evaluate_material(result, application_class):
    """Grade one screening result against an application class."""
    norm = validate_result(result)
    limits = class_limits(application_class)
    basis, loss_value = mass_loss_basis(norm, application_class)

    findings = []
    if not within_limit(loss_value, limits["mass_loss_limit_pct"]):
        findings.append("mass-loss-above-the-class-limit")

    cvcm = norm["cvcm_pct"]
    cvcm_bound = None
    if cvcm is None:
        cvcm_bound = norm["cvcm_floor_pct"]
        if not within_limit(cvcm_bound, limits["cvcm_limit_pct"]):
            findings.append("sub-floor-cvcm-bound-above-the-class-limit")
    elif not within_limit(cvcm, limits["cvcm_limit_pct"]):
        findings.append("cvcm-above-the-class-limit")

    if (
        norm["water_vapour_regained_pct"] is not None
        and not limits["water_credit"]
    ):
        findings.append("water-credit-not-available-for-this-application")

    verdict = ACCEPTED
    if findings:
        blocking = [f for f in findings
                    if f != "water-credit-not-available-for-this-application"]
        if not blocking:
            verdict = ACCEPTED
        elif norm["deviation_reference"] and norm[
            "contamination_assessment_reference"
        ]:
            verdict = ACCEPTED_ON_DEVIATION
        else:
            verdict = REJECTED
            if norm["deviation_reference"] and not norm[
                "contamination_assessment_reference"
            ]:
                findings.append("deviation-cited-without-a-contamination-assessment")
            elif norm["contamination_assessment_reference"] and not norm[
                "deviation_reference"
            ]:
                findings.append("contamination-assessment-cited-without-a-deviation")

    return {
        "material": norm["material"],
        "application_class": application_class,
        "mass_loss_basis": basis,
        "mass_loss_value_pct": loss_value,
        "mass_loss_limit_pct": limits["mass_loss_limit_pct"],
        "cvcm_value_pct": cvcm,
        "cvcm_bound_pct": cvcm_bound,
        "cvcm_limit_pct": limits["cvcm_limit_pct"],
        "verdict": verdict,
        "findings": findings,
    }


def assess_acceptance(results, application_class):
    """Grade a list of screening results against one application class."""
    if not isinstance(results, list) or not results:
        raise ValueError("results must be a non-empty list")
    class_limits(application_class)
    graded = []
    seen = set()
    for result in results:
        row = evaluate_material(result, application_class)
        if row["material"] in seen:
            raise ValueError("duplicate material %r" % (row["material"],))
        seen.add(row["material"])
        graded.append(row)
    return {
        "application_class": application_class,
        "materials": graded,
        "accepted": [r["material"] for r in graded if r["verdict"] == ACCEPTED],
        "on_deviation": [
            r["material"] for r in graded if r["verdict"] == ACCEPTED_ON_DEVIATION
        ],
        "rejected": [r["material"] for r in graded if r["verdict"] == REJECTED],
        "clear": all(r["verdict"] == ACCEPTED for r in graded),
    }
