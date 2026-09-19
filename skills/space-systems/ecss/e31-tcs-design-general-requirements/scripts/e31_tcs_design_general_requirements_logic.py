"""General thermal control design-to-requirements process.

Anchor: ECSS-E-ST-31C clause 4.4.1 (general design requirements for the
thermal control subsystem). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Take the analysis maturity of the thermal model and turn it into the
   uncertainty margin the predicted temperatures carry. An uncorrelated
   preliminary model earns a wide margin; a model correlated against flight
   hardware earns a narrow one.
2. Build the temperature stack for each item, in the direction the case
   pushes: predicted, plus uncertainty gives the design temperature; plus
   the acceptance margin gives the acceptance limit; plus the qualification
   margin gives the qualification limit. The cold case walks the same stack
   downwards.
3. Grade the design temperature against the requirement limit and report the
   remaining margin in kelvin for both the hot and the cold case.
4. Confirm the worst-case basis is self-consistent: a case declared hot has
   to combine the maximum environmental fluxes, end-of-life degraded optical
   properties and the maximum dissipation; a cold case the minimum fluxes,
   beginning-of-life properties and the minimum dissipation. A case that
   mixes them is not a worst case and its margins mean nothing.
5. Rank the items by the smallest margin they carry and name the driving
   case, so the design drivers of the subsystem are an output rather than an
   opinion.
"""

import math

__all__ = [
    "MATURITY_UNCERTAINTY_K",
    "MARGIN_TOLERANCE_K",
    "validate_real",
    "validate_positive",
    "uncertainty_margin_k",
    "design_temperature_c",
    "acceptance_limit_c",
    "qualification_limit_c",
    "requirement_margin_k",
    "worst_case_basis_findings",
    "evaluate_item",
    "rank_design_drivers",
    "assess_tcs_design",
]

# Uncertainty margin in kelvin carried by a predicted temperature, by the
# maturity of the thermal model the prediction came from.
MATURITY_UNCERTAINTY_K = {
    "preliminary": 15.0,
    "detailed-uncorrelated": 10.0,
    "detailed-correlated": 5.0,
    "flight-correlated": 3.0,
}

# A design temperature landing exactly on its requirement is a decision, not
# a failure; absorb the representation error at the boundary.
MARGIN_TOLERANCE_K = 1e-9

_CASES = ("hot", "cold")


def validate_real(label, value):
    """Return value as a finite float of any sign."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_positive(label, value, allow_zero=False):
    """Return value as a positive finite float, raising on anything else."""
    out = validate_real(label, value)
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, out))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def _validate_case(case):
    """Return the validated worst-case label."""
    if case not in _CASES:
        raise ValueError("case must be 'hot' or 'cold', got %r" % (case,))
    return case


def uncertainty_margin_k(maturity):
    """Return the uncertainty margin a model maturity earns, in kelvin."""
    if not isinstance(maturity, str):
        raise ValueError("maturity must be a string, got %r" % (maturity,))
    if maturity not in MATURITY_UNCERTAINTY_K:
        raise ValueError(
            "unknown model maturity %r; the recognised levels are %s"
            % (maturity, ", ".join(sorted(MATURITY_UNCERTAINTY_K)))
        )
    return MATURITY_UNCERTAINTY_K[maturity]


def design_temperature_c(predicted_c, uncertainty_k, case):
    """Return the design temperature, pushed in the direction of the case."""
    predicted = validate_real("predicted_c", predicted_c)
    uncertainty = validate_positive("uncertainty_k", uncertainty_k, allow_zero=True)
    if _validate_case(case) == "hot":
        return predicted + uncertainty
    return predicted - uncertainty


def acceptance_limit_c(design_c, acceptance_margin_k, case):
    """Return the acceptance test limit derived from a design temperature."""
    design = validate_real("design_c", design_c)
    margin = validate_positive("acceptance_margin_k", acceptance_margin_k,
                               allow_zero=True)
    if _validate_case(case) == "hot":
        return design + margin
    return design - margin


def qualification_limit_c(acceptance_c, qualification_margin_k, case):
    """Return the qualification test limit derived from an acceptance limit."""
    acceptance = validate_real("acceptance_c", acceptance_c)
    margin = validate_positive("qualification_margin_k", qualification_margin_k,
                               allow_zero=True)
    if _validate_case(case) == "hot":
        return acceptance + margin
    return acceptance - margin


def requirement_margin_k(design_c, requirement_c, case):
    """Return the kelvin margin a design temperature keeps to its limit."""
    design = validate_real("design_c", design_c)
    requirement = validate_real("requirement_c", requirement_c)
    if _validate_case(case) == "hot":
        return requirement - design
    return design - requirement


def worst_case_basis_findings(case_record):
    """Return the findings raised by an internally inconsistent worst case."""
    if not isinstance(case_record, dict):
        raise ValueError("case_record must be a mapping")
    for key in ("case", "environment", "optical_properties", "dissipation"):
        if key not in case_record:
            raise ValueError("case_record missing required key %r" % key)
    case = _validate_case(case_record["case"])
    findings = []
    if case == "hot":
        expected = {
            "environment": "maximum",
            "optical_properties": "end-of-life",
            "dissipation": "maximum",
        }
    else:
        expected = {
            "environment": "minimum",
            "optical_properties": "beginning-of-life",
            "dissipation": "minimum",
        }
    allowed = {
        "environment": ("maximum", "minimum"),
        "optical_properties": ("end-of-life", "beginning-of-life"),
        "dissipation": ("maximum", "minimum"),
    }
    for key, want in expected.items():
        got = case_record[key]
        if got not in allowed[key]:
            raise ValueError(
                "%s must be one of %s, got %r" % (key, allowed[key], got)
            )
        if got != want:
            findings.append(
                "%s case declares %s %r where a worst case needs %r"
                % (case, key.replace("_", " "), got, want)
            )
    return findings


def evaluate_item(item):
    """Evaluate one item against its hot and cold worst-case requirements."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("name", "maturity", "acceptance_margin_k",
                "qualification_margin_k", "cases"):
        if key not in item:
            raise ValueError("item record missing required key %r" % key)
    cases = item["cases"]
    if not isinstance(cases, dict) or set(cases) != set(_CASES):
        raise ValueError(
            "item %r must declare exactly a 'hot' and a 'cold' case"
            % (item["name"],)
        )
    uncertainty = uncertainty_margin_k(item["maturity"])
    results = {}
    findings = []
    for case in _CASES:
        entry = cases[case]
        if not isinstance(entry, dict):
            raise ValueError("case %r of item %r must be a mapping"
                             % (case, item["name"]))
        for key in ("predicted_c", "requirement_c", "environment",
                    "optical_properties", "dissipation"):
            if key not in entry:
                raise ValueError(
                    "case %r of item %r missing key %r"
                    % (case, item["name"], key)
                )
        design = design_temperature_c(entry["predicted_c"], uncertainty, case)
        acceptance = acceptance_limit_c(design, item["acceptance_margin_k"], case)
        qualification = qualification_limit_c(
            acceptance, item["qualification_margin_k"], case
        )
        margin = requirement_margin_k(design, entry["requirement_c"], case)
        compliant = margin > 0.0 or math.isclose(
            margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_K
        )
        basis = worst_case_basis_findings({
            "case": case,
            "environment": entry["environment"],
            "optical_properties": entry["optical_properties"],
            "dissipation": entry["dissipation"],
        })
        findings.extend("%s: %s" % (item["name"], text) for text in basis)
        if not compliant:
            findings.append(
                "%s: %s case design temperature %.2f C misses its %.2f C "
                "requirement by %.2f K"
                % (item["name"], case, design, entry["requirement_c"], -margin)
            )
        results[case] = {
            "design_temperature_c": design,
            "acceptance_limit_c": acceptance,
            "qualification_limit_c": qualification,
            "margin_k": margin,
            "compliant": compliant,
            "basis_findings": basis,
        }
    driving = min(_CASES, key=lambda c: results[c]["margin_k"])
    return {
        "name": item["name"],
        "uncertainty_margin_k": uncertainty,
        "cases": results,
        "driving_case": driving,
        "smallest_margin_k": results[driving]["margin_k"],
        "compliant": all(results[c]["compliant"] for c in _CASES) and not findings,
        "findings": findings,
    }


def rank_design_drivers(records):
    """Return the item records ordered by the smallest margin they carry."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of item records")
    for record in records:
        if not isinstance(record, dict) or "smallest_margin_k" not in record:
            raise ValueError("each record must carry 'smallest_margin_k'")
    return sorted(records, key=lambda r: (r["smallest_margin_k"], r["name"]))


def assess_tcs_design(spec):
    """Run the full clause 4.4.1 design-to-requirements assessment.

    spec keys: items (sequence of item records).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "items" not in spec:
        raise ValueError("spec missing required key 'items'")
    items = spec["items"]
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("spec['items'] must be a non-empty sequence")
    records = [evaluate_item(item) for item in items]
    names = [record["name"] for record in records]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    if len(set(names)) != len(names):
        findings.append("two items share a name; design drivers cannot be traced")
    ranked = rank_design_drivers(records)
    return {
        "items": records,
        "design_drivers": [
            {"name": r["name"], "case": r["driving_case"],
             "margin_k": r["smallest_margin_k"]}
            for r in ranked
        ],
        "compliant": all(r["compliant"] for r in records)
        and len(set(names)) == len(names),
        "findings": findings,
    }
