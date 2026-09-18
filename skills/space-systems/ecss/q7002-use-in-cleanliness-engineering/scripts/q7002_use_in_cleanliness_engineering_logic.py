"""Using outgassing screening data in a molecular contamination budget.

Anchor: ECSS-Q-ST-70-02C screening results feeding the cleanliness and
contamination control practice of ECSS-Q-ST-70-01C (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. A screening condensable figure is a bound, not a rate. It is the
   fraction of a small specimen that condensed on a cold plate during a
   fixed bake, under one geometry, in one day. It carries no time
   dependence and no geometry, so it can enter a budget only as a
   bounding source term with an explicit transport fraction beside it.
   A record that presents it as a rate is refused outright.
2. The source term is that fraction of the mass of material actually
   exposed to the vacuum path. A pre-flight bakeout can be credited
   against it, but only with the bakeout on record: an uncited credit is
   an assumption with a number in front of it.
3. What lands on the sensitive surface is the source term times the
   fraction that reaches it -- geometry, line of sight, temperature of
   the receiver and residence once it arrives, folded into one declared
   number that the budget can be audited on.
4. Contributions add. The budget compares their sum against the
   allocation the sensitive surface holds, and reports which contributor
   dominates, because that is the one worth re-testing or re-baking.
5. A contributor whose screening figure came from a run that does not
   compare with baseline screening data has to say so. The number may
   still be the best available, but a budget built from a mixture of
   bases without saying which is which cannot be reviewed.

Stdlib only, offline, deterministic.
"""

# The only admissible reading of a screening condensable figure.
BASIS_SCREENING_BOUND = "screening-bound"

# Micrograms per gram.
MICROGRAM_PER_GRAM = 1.0e6

# A bakeout cannot be credited with removing everything.
MAX_BAKEOUT_CREDIT = 0.90

# Deposited masses are sums of products, so a total sitting exactly on
# its allocation can land a few units in the last place past it. This
# tolerance absorbs that representation error only; the allocation is
# never widened.
DEPOSIT_TOLERANCE_UG_PER_CM2 = 1.0e-9
FRACTION_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _fraction(label, value):
    """Return value as a fraction in the closed unit interval."""
    fraction = _numeric(label, value)
    if fraction < -FRACTION_TOLERANCE or fraction > 1.0 + FRACTION_TOLERANCE:
        raise ValueError("%s must lie between 0 and 1, got %r" % (label, value))
    return min(max(fraction, 0.0), 1.0)


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def validate_contributor(contributor):
    """Validate one budget contributor and return a normalized copy."""
    if not isinstance(contributor, dict):
        raise ValueError("contributor must be a mapping")
    cid = _text("contributor id", contributor.get("id"))
    basis = contributor.get("basis", BASIS_SCREENING_BOUND)
    if basis != BASIS_SCREENING_BOUND:
        raise ValueError(
            "contributor %s declares basis %r; a screening percentage is a "
            "bound on a fixed bake, not an outgassing rate" % (cid, basis)
        )
    cvcm = _numeric("contributor %s cvcm_pct" % cid, contributor.get("cvcm_pct"), 0.0)
    if cvcm > 100.0:
        raise ValueError("contributor %s cvcm_pct %r exceeds 100" % (cid, cvcm))
    mass = _numeric(
        "contributor %s exposed_mass_g" % cid, contributor.get("exposed_mass_g"), 0.0
    )
    transport = _fraction(
        "contributor %s transport_fraction" % cid,
        contributor.get("transport_fraction"),
    )
    credit = contributor.get("bakeout_credit_fraction", 0.0)
    credit = _fraction("contributor %s bakeout_credit_fraction" % cid, credit)
    if credit > MAX_BAKEOUT_CREDIT + FRACTION_TOLERANCE:
        raise ValueError(
            "contributor %s claims a bakeout credit of %r, above the ceiling %r"
            % (cid, credit, MAX_BAKEOUT_CREDIT)
        )
    reference = contributor.get("bakeout_reference")
    if reference is not None and not isinstance(reference, str):
        raise ValueError("contributor %s bakeout_reference must be a string" % cid)
    comparable = contributor.get("screening_comparable", True)
    if not isinstance(comparable, bool):
        raise ValueError("contributor %s screening_comparable must be a boolean" % cid)
    note = contributor.get("non_comparable_note")
    if note is not None and not isinstance(note, str):
        raise ValueError("contributor %s non_comparable_note must be a string" % cid)
    return {
        "id": cid,
        "basis": basis,
        "cvcm_pct": cvcm,
        "exposed_mass_g": mass,
        "transport_fraction": transport,
        "bakeout_credit_fraction": credit,
        "bakeout_reference": (reference or "").strip() or None,
        "screening_comparable": comparable,
        "non_comparable_note": (note or "").strip() or None,
    }


def source_term_g(cvcm_pct, exposed_mass_g):
    """Bounding condensable mass a material can release, in grams."""
    cvcm = _numeric("cvcm_pct", cvcm_pct, 0.0)
    mass = _numeric("exposed_mass_g", exposed_mass_g, 0.0)
    return cvcm / 100.0 * mass


def deposited_ug_per_cm2(source_g, transport_fraction, receiver_area_cm2):
    """Areal deposit on the receiver from one source term, in ug/cm2."""
    source = _numeric("source_g", source_g, 0.0)
    transport = _fraction("transport_fraction", transport_fraction)
    area = _numeric("receiver_area_cm2", receiver_area_cm2)
    if area <= 0:
        raise ValueError("receiver_area_cm2 must be positive")
    return source * MICROGRAM_PER_GRAM * transport / area


def contributor_deposit(contributor, receiver_area_cm2):
    """Deposit and findings for one contributor on one receiver."""
    norm = validate_contributor(contributor)
    findings = []
    credit = norm["bakeout_credit_fraction"]
    if credit > FRACTION_TOLERANCE and norm["bakeout_reference"] is None:
        findings.append("bakeout-credit-claimed-without-a-bakeout-on-record")
        credit = 0.0
    if credit <= FRACTION_TOLERANCE and norm["bakeout_reference"] is not None:
        findings.append("bakeout-on-record-with-no-credit-taken")
    if not norm["screening_comparable"] and norm["non_comparable_note"] is None:
        findings.append("non-baseline-screening-figure-used-without-a-note")

    source = source_term_g(norm["cvcm_pct"], norm["exposed_mass_g"]) * (1.0 - credit)
    deposit = deposited_ug_per_cm2(source, norm["transport_fraction"], receiver_area_cm2)
    return {
        "id": norm["id"],
        "source_term_g": source,
        "applied_bakeout_credit_fraction": credit,
        "deposit_ug_per_cm2": deposit,
        "findings": findings,
    }


def assess_contamination_budget(contributors, receiver):
    """Build a molecular deposition budget from screening data."""
    if not isinstance(contributors, list) or not contributors:
        raise ValueError("contributors must be a non-empty list")
    if not isinstance(receiver, dict):
        raise ValueError("receiver must be a mapping")
    area = _numeric("receiver area_cm2", receiver.get("area_cm2"))
    if area <= 0:
        raise ValueError("receiver area_cm2 must be positive")
    allocation = _numeric(
        "receiver allocation_ug_per_cm2", receiver.get("allocation_ug_per_cm2")
    )
    if allocation <= 0:
        raise ValueError("receiver allocation_ug_per_cm2 must be positive")

    rows = []
    findings = []
    seen = set()
    for contributor in contributors:
        row = contributor_deposit(contributor, area)
        if row["id"] in seen:
            raise ValueError("duplicate contributor id %r" % (row["id"],))
        seen.add(row["id"])
        findings.extend(row["findings"])
        rows.append(row)

    total = sum(row["deposit_ug_per_cm2"] for row in rows)
    within = total <= allocation + DEPOSIT_TOLERANCE_UG_PER_CM2
    if not within:
        findings.append("molecular-deposition-budget-exceeds-its-allocation")
    ranked = sorted(rows, key=lambda r: (-r["deposit_ug_per_cm2"], r["id"]))
    return {
        "receiver_area_cm2": area,
        "allocation_ug_per_cm2": allocation,
        "contributors": rows,
        "total_deposit_ug_per_cm2": total,
        "margin_ug_per_cm2": allocation - total,
        "utilization_fraction": total / allocation,
        "dominant_contributor": ranked[0]["id"],
        "ranked_contributor_ids": [row["id"] for row in ranked],
        "within_allocation": within,
        "findings": findings,
        "clear": within and not findings,
    }
