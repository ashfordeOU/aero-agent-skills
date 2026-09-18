"""Using offgassing results in crew-compartment material selection.

Anchor: the interface between the ECSS-Q-ST-70-29 offgassing determination and
the material selection and contamination control it feeds (ECSS-Q-ST-70C
material selection, ECSS-Q-ST-70-01C contamination control). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn each compound's specific offgassing yield and the mass of material
   actually installed into the concentration that material alone contributes to
   the sealed crew-compartment free volume.
2. Divide each contribution by that compound's spacecraft maximum allowable
   concentration and sum the ratios into one toxicity index, because the crew
   breathes the mixture rather than any single compound.
3. Invert the same relation to return the mass of the material the compartment
   could carry before the index reaches unity, so an over-index material becomes
   a mass limit rather than a flat refusal.
4. Grade the evidence the selection rests on: the offgassing report itself, its
   age against the revalidation interval, whether the formulation or process has
   moved since the test, and the material selection and contamination control
   records that the report has to be tied to.
5. Rank the findings by severity and close with one selection disposition.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "UG_PER_MG",
    "MAX_TOXICITY_INDEX",
    "REQUIRED_EVIDENCE",
    "DEFAULT_REVALIDATION_DAYS",
    "SEVERITY_ORDER",
    "cabin_concentration_mg_m3",
    "smac_ratio",
    "compound_contributions",
    "toxicity_index",
    "single_compound_mass_limit_g",
    "combined_mass_limit_g",
    "binding_compound",
    "missing_evidence",
    "report_currency_findings",
    "selection_disposition",
    "assess_crewed_material_control",
]

# Ratios and sums of ratios are quotients of measured numbers; an exact equality
# can land a few ULPs on the wrong side of unity. Absorb the representation
# error here instead of relaxing the allowable concentration.
BOUND_TOLERANCE = 1e-9

UG_PER_MG = 1000.0

# The crew breathes the mixture, so the sum of the ratios is the quantity that
# has to stay at or below one.
MAX_TOXICITY_INDEX = 1.0

# The offgassing report alone is not a selection. It is tied to the material
# selection record and to the contamination control the compartment runs under.
REQUIRED_EVIDENCE = (
    "offgassing-test-report-70-29",
    "material-selection-approval-70c",
    "contamination-control-plan-70-01c",
    "declared-materials-list-entry",
)

DEFAULT_REVALIDATION_DAYS = 1825.0

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}


def _real(label, value):
    """Return value as a finite float, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float, or raise ValueError."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _non_negative(label, value):
    """Return value as a non-negative finite float, or raise ValueError."""
    out = _real(label, value)
    if out < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return out


def _at_or_below(value, bound):
    """True when value is below bound or lands on it within tolerance."""
    return value < bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=BOUND_TOLERANCE)


def _token(label, value):
    """Return a lowercase, stripped evidence or compound token."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower()


def cabin_concentration_mg_m3(mass_g, yield_ug_per_g, free_volume_m3):
    """Return the compartment concentration this material mass contributes."""
    mass = _non_negative("mass_g", mass_g)
    specific = _non_negative("yield_ug_per_g", yield_ug_per_g)
    volume = _positive("free_volume_m3", free_volume_m3)
    return (mass * specific) / (volume * UG_PER_MG)


def smac_ratio(concentration_mg_m3, smac_mg_m3):
    """Return the contribution as a fraction of the allowable concentration."""
    concentration = _non_negative("concentration_mg_m3", concentration_mg_m3)
    smac = _positive("smac_mg_m3", smac_mg_m3)
    return concentration / smac


def compound_contributions(compounds, mass_g, free_volume_m3):
    """Return one contribution record per reported compound."""
    if not isinstance(compounds, (list, tuple)) or not compounds:
        raise ValueError("compounds must be a non-empty sequence")
    records = []
    seen = set()
    for index, compound in enumerate(compounds):
        if not isinstance(compound, dict):
            raise ValueError("compounds[%d] must be a mapping" % index)
        for key in ("name", "yield_ug_per_g", "smac_mg_m3"):
            if key not in compound:
                raise ValueError("compounds[%d] missing '%s'" % (index, key))
        name = _token("compounds[%d]['name']" % index, compound["name"])
        if name in seen:
            raise ValueError("compound %r reported twice" % name)
        seen.add(name)
        concentration = cabin_concentration_mg_m3(
            mass_g, compound["yield_ug_per_g"], free_volume_m3
        )
        ratio = smac_ratio(concentration, compound["smac_mg_m3"])
        records.append({
            "name": name,
            "yield_ug_per_g": _non_negative("yield_ug_per_g", compound["yield_ug_per_g"]),
            "smac_mg_m3": _positive("smac_mg_m3", compound["smac_mg_m3"]),
            "concentration_mg_m3": concentration,
            "smac_ratio": ratio,
        })
    return records


def toxicity_index(records):
    """Return the summed mixture index across the contribution records."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    total = 0.0
    for index, record in enumerate(records):
        if not isinstance(record, dict) or "smac_ratio" not in record:
            raise ValueError("records[%d] must carry 'smac_ratio'" % index)
        total += _non_negative("records[%d]['smac_ratio']" % index, record["smac_ratio"])
    return total


def single_compound_mass_limit_g(yield_ug_per_g, smac_mg_m3, free_volume_m3):
    """Return the material mass at which one compound reaches its allowable."""
    specific = _positive("yield_ug_per_g", yield_ug_per_g)
    smac = _positive("smac_mg_m3", smac_mg_m3)
    volume = _positive("free_volume_m3", free_volume_m3)
    return (smac * volume * UG_PER_MG) / specific


def combined_mass_limit_g(compounds, free_volume_m3):
    """Return the material mass at which the mixture index reaches unity."""
    if not isinstance(compounds, (list, tuple)) or not compounds:
        raise ValueError("compounds must be a non-empty sequence")
    volume = _positive("free_volume_m3", free_volume_m3)
    burden = 0.0
    for index, compound in enumerate(compounds):
        if not isinstance(compound, dict):
            raise ValueError("compounds[%d] must be a mapping" % index)
        for key in ("yield_ug_per_g", "smac_mg_m3"):
            if key not in compound:
                raise ValueError("compounds[%d] missing '%s'" % (index, key))
        specific = _non_negative("compounds[%d]['yield_ug_per_g']" % index,
                                 compound["yield_ug_per_g"])
        smac = _positive("compounds[%d]['smac_mg_m3']" % index, compound["smac_mg_m3"])
        burden += specific / (smac * volume * UG_PER_MG)
    if burden <= 0.0:
        return float("inf")
    return MAX_TOXICITY_INDEX / burden


def binding_compound(compounds, free_volume_m3):
    """Return the compound whose own allowable is reached at the lowest mass."""
    if not isinstance(compounds, (list, tuple)) or not compounds:
        raise ValueError("compounds must be a non-empty sequence")
    volume = _positive("free_volume_m3", free_volume_m3)
    binding = None
    for index, compound in enumerate(compounds):
        if not isinstance(compound, dict):
            raise ValueError("compounds[%d] must be a mapping" % index)
        for key in ("name", "yield_ug_per_g", "smac_mg_m3"):
            if key not in compound:
                raise ValueError("compounds[%d] missing '%s'" % (index, key))
        specific = _non_negative("compounds[%d]['yield_ug_per_g']" % index,
                                 compound["yield_ug_per_g"])
        if specific <= 0.0:
            continue
        limit = single_compound_mass_limit_g(specific, compound["smac_mg_m3"], volume)
        name = _token("compounds[%d]['name']" % index, compound["name"])
        if binding is None or limit < binding[1]:
            binding = (name, limit)
    return binding


def missing_evidence(evidence_held):
    """Return the required selection evidence the record does not hold."""
    if not isinstance(evidence_held, (list, tuple)):
        raise ValueError("evidence_held must be a sequence")
    held = set()
    for index, item in enumerate(evidence_held):
        held.add(_token("evidence_held[%d]" % index, item))
    return [name for name in REQUIRED_EVIDENCE if name not in held]


def report_currency_findings(days_since_test, revalidation_days, formulation_changed):
    """Return the findings raised by the age and standing of the test report."""
    age = _non_negative("days_since_test", days_since_test)
    window = _positive("revalidation_days", revalidation_days)
    if not isinstance(formulation_changed, bool):
        raise ValueError("formulation_changed must be a boolean")
    findings = []
    if not _at_or_below(age, window):
        findings.append({
            "severity": "major",
            "control": "report-revalidation",
            "detail": "offgassing report is %.0f days old against a %.0f day interval"
                      % (age, window),
        })
    if formulation_changed:
        findings.append({
            "severity": "critical",
            "control": "formulation-change",
            "detail": "formulation or process moved since the test, so the report "
                      "describes a material that is no longer the one being installed",
        })
    return findings


def selection_disposition(findings, index, mass_limit_g, installed_mass_g):
    """Return the crew-compartment selection disposition."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    for item in findings:
        if not isinstance(item, dict) or item.get("severity") not in SEVERITY_ORDER:
            raise ValueError("each finding must carry a known severity")
    total = _non_negative("index", index)
    if isinstance(mass_limit_g, bool) or not isinstance(mass_limit_g, (int, float)):
        raise ValueError("mass_limit_g must be a real number, got %r" % (mass_limit_g,))
    limit = float(mass_limit_g)
    if math.isnan(limit):
        raise ValueError("mass_limit_g must not be a NaN")
    installed = _non_negative("installed_mass_g", installed_mass_g)
    if any(item["severity"] == "critical" for item in findings):
        return "not-approved"
    if _at_or_below(total, MAX_TOXICITY_INDEX):
        return "approved-for-crew-compartment"
    if not math.isfinite(limit) or limit <= 0.0 or limit >= installed:
        return "not-approved"
    return "approved-with-mass-limit"


def assess_crewed_material_control(spec):
    """Decide whether an offgassing-tested material may go into the crew compartment.

    spec keys: compounds (list of {name, yield_ug_per_g, smac_mg_m3}),
    installed_mass_g, free_volume_m3, evidence_held, days_since_test,
    formulation_changed, optional revalidation_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("compounds", "installed_mass_g", "free_volume_m3", "evidence_held",
                "days_since_test", "formulation_changed"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    installed = _non_negative("installed_mass_g", spec["installed_mass_g"])
    volume = _positive("free_volume_m3", spec["free_volume_m3"])
    records = compound_contributions(spec["compounds"], installed, volume)
    index = toxicity_index(records)
    limit = combined_mass_limit_g(spec["compounds"], volume)
    binding = binding_compound(spec["compounds"], volume)
    findings = []
    for record in records:
        if not _at_or_below(record["smac_ratio"], MAX_TOXICITY_INDEX):
            findings.append({
                "severity": "major",
                "control": "single-compound-allowable",
                "detail": "%s alone reaches %.4f of its allowable concentration "
                          "at the installed mass" % (record["name"], record["smac_ratio"]),
            })
    if not _at_or_below(index, MAX_TOXICITY_INDEX):
        findings.append({
            "severity": "major",
            "control": "mixture-index",
            "detail": "mixture index %.4f above unity at %.1f g installed; "
                      "%.1f g is the mass the compartment can carry"
                      % (index, installed, limit),
        })
    gaps = missing_evidence(spec["evidence_held"])
    for name in gaps:
        findings.append({
            "severity": "critical" if name == REQUIRED_EVIDENCE[0] else "major",
            "control": "selection-evidence",
            "detail": "selection record does not hold %s" % name,
        })
    findings.extend(report_currency_findings(
        spec["days_since_test"],
        spec.get("revalidation_days", DEFAULT_REVALIDATION_DAYS),
        spec["formulation_changed"],
    ))
    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])
    return {
        "contributions": records,
        "toxicity_index": index,
        "mass_limit_g": limit,
        "installed_mass_g": installed,
        "binding_compound": binding,
        "missing_evidence": gaps,
        "findings": findings,
        "disposition": selection_disposition(findings, index, limit, installed),
    }
