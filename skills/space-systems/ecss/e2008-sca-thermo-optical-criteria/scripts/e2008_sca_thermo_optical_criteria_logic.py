"""Thermo optical acceptance limits drawn from the cell assembly drawing.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.6.3. The procedure below is a paraphrase
of the clause intent and reproduces none of its text: the acceptance limits a
measured solar absorptance and hemispherical emittance are held against are the
ones the cell assembly control drawing carries, so the first question about any
limit is where it came from, not whether the sample met it.

Procedure implemented here
--------------------------
1. Categorize the provenance of every limit. A limit stated on the drawing, or
   stated in a document the drawing invokes, governs. A house default that no
   drawing sanctioned does not, however sensible its value, and a verdict taken
   against it is a verdict nobody can trace.
2. Check the drawing revision the limits were read from against the revision
   the lot was built to. Limits read from a superseded revision can be tighter
   or looser than the ones the article was made against.
3. Guard band every comparison by the uncertainty of the measurement that
   produced the value. A result inside the limit by less than its own
   uncertainty has not been shown to be inside it; it is marginal, and a
   marginal result is a decision for the customer rather than a pass.
4. Apply each limit in its own sense: absorptance carries a ceiling, emittance
   carries a floor, and the absorptance to emittance ratio carries a ceiling.
5. Roll the samples up on their worst disposition, so one failure is visible in
   the lot verdict rather than averaged into a population that mostly passed.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "ADMISSIBLE_PROVENANCE",
    "DISPOSITION_ORDER",
    "LIMIT_SENSES",
    "categorize_limit_provenance",
    "guard_banded_disposition",
    "worst_disposition",
    "absorptance_emittance_ratio",
    "validate_limit",
    "validate_drawing",
    "evaluate_sample_limits",
    "assess_thermo_optical_criteria",
]

# Measured values, uncertainties and ratios are floats, so a sample built
# exactly to a drawing limit can land a few units in the last place either side
# of it. Absorb that representation error here, never by moving the limit.
LIMIT_TOLERANCE = 1e-9

# A limit only governs when the drawing carries it or invokes the document that
# does. Anything else is a house number wearing a requirement's clothes.
ADMISSIBLE_PROVENANCE = ("drawing-stated", "drawing-invoked")

# Worst-case ordering used to roll a sample or a lot up.
DISPOSITION_ORDER = ("pass", "marginal", "fail")

# Which way each governed property is bounded.
LIMIT_SENSES = {
    "solar_absorptance": "max",
    "hemispherical_emittance": "min",
    "absorptance_emittance_ratio": "max",
}


def _real(label, value, allow_zero=False, allow_negative=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if not allow_negative:
        if allow_zero and number < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
        if not allow_zero and number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _mapping(label, value, required_keys=()):
    """Return value as a mapping carrying every required key."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in required_keys:
        if key not in value:
            raise ValueError("%s is missing required key '%s'" % (label, key))
    return value


def _identifier(label, value):
    """Return value as a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def categorize_limit_provenance(limit):
    """Return where a limit came from, grouped into one provenance category.

    A limit naming the drawing itself is drawing-stated; one naming a document
    the drawing invokes is drawing-invoked; anything else is a house default
    that the drawing never sanctioned.
    """
    data = _mapping("limit", limit, ("source",))
    source = _identifier("limit['source']", data["source"]).lower()
    if source in ("drawing", "control-drawing", "drawing-stated"):
        return "drawing-stated"
    if source in ("drawing-invoked", "invoked-specification", "invoked"):
        return "drawing-invoked"
    return "house-default"


def guard_banded_disposition(value, bound, sense, uncertainty):
    """Return pass, marginal or fail for one guard-banded comparison."""
    measured = _real("value", value, allow_zero=True, allow_negative=True)
    limit = _real("bound", bound, allow_zero=True, allow_negative=True)
    spread = _real("uncertainty", uncertainty, allow_zero=True)
    if sense not in ("max", "min"):
        raise ValueError("sense must be 'max' or 'min', got %r" % (sense,))
    if sense == "max":
        clear_edge = measured + spread
        breach_edge = measured - spread
        if clear_edge < limit or math.isclose(
            clear_edge, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
        ):
            return "pass"
        if breach_edge > limit and not math.isclose(
            breach_edge, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
        ):
            return "fail"
        return "marginal"
    clear_edge = measured - spread
    breach_edge = measured + spread
    if clear_edge > limit or math.isclose(
        clear_edge, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    ):
        return "pass"
    if breach_edge < limit and not math.isclose(
        breach_edge, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    ):
        return "fail"
    return "marginal"


def worst_disposition(dispositions):
    """Return the heaviest disposition in a sequence."""
    if not isinstance(dispositions, (list, tuple)) or not dispositions:
        raise ValueError("dispositions must be a non-empty sequence")
    worst = "pass"
    for entry in dispositions:
        if entry not in DISPOSITION_ORDER:
            raise ValueError("unknown disposition %r" % (entry,))
        if DISPOSITION_ORDER.index(entry) > DISPOSITION_ORDER.index(worst):
            worst = entry
    return worst


def absorptance_emittance_ratio(absorptance, emittance):
    """Return the absorptance to emittance ratio the thermal design consumes."""
    alpha = _real("absorptance", absorptance, allow_zero=True)
    epsilon = _real("emittance", emittance)
    return alpha / epsilon


def validate_limit(name, limit):
    """Return (limit record, findings) for one governed property limit."""
    if name not in LIMIT_SENSES:
        raise ValueError("'%s' is not a governed thermo optical property" % name)
    data = _mapping("limits['%s']" % name, limit, ("value", "source"))
    value = _real("limits['%s']['value']" % name, data["value"], allow_zero=True)
    provenance = categorize_limit_provenance(data)
    document = data.get("document")
    if document is not None:
        document = _identifier("limits['%s']['document']" % name, document)
    findings = []
    if provenance not in ADMISSIBLE_PROVENANCE:
        findings.append(
            "the %s limit of %g is a house default the cell assembly control "
            "drawing never sanctioned" % (name.replace("_", " "), value)
        )
    elif provenance == "drawing-invoked" and document is None:
        findings.append(
            "the %s limit leans on a drawing-invoked document that is not named"
            % name.replace("_", " ")
        )
    return (
        {
            "property": name,
            "value": value,
            "sense": LIMIT_SENSES[name],
            "provenance": provenance,
            "document": document,
            "admissible": provenance in ADMISSIBLE_PROVENANCE,
        },
        findings,
    )


def validate_drawing(drawing):
    """Return (drawing record, findings) for the governing control drawing."""
    data = _mapping("drawing", drawing, ("number", "revision", "lot_built_to_revision"))
    number = _identifier("drawing['number']", data["number"])
    revision = _identifier("drawing['revision']", data["revision"])
    built_to = _identifier(
        "drawing['lot_built_to_revision']", data["lot_built_to_revision"]
    )
    findings = []
    if revision != built_to:
        findings.append(
            "limits were read from drawing %s revision %s while the lot was built "
            "to revision %s" % (number, revision, built_to)
        )
    return (
        {
            "number": number,
            "revision": revision,
            "lot_built_to_revision": built_to,
            "revision_aligned": revision == built_to,
        },
        findings,
    )


def evaluate_sample_limits(sample, limit_records):
    """Hold one sample's measured properties against the governed limits."""
    data = _mapping(
        "sample",
        sample,
        ("id", "solar_absorptance", "hemispherical_emittance"),
    )
    sample_id = _identifier("sample['id']", data["id"])
    absorptance = _real(
        "sample['solar_absorptance']", data["solar_absorptance"], allow_zero=True
    )
    emittance = _real("sample['hemispherical_emittance']", data["hemispherical_emittance"])
    uncertainties = _mapping("sample['uncertainty']", data.get("uncertainty", {}))
    ratio = absorptance_emittance_ratio(absorptance, emittance)
    measured = {
        "solar_absorptance": absorptance,
        "hemispherical_emittance": emittance,
        "absorptance_emittance_ratio": ratio,
    }
    ratio_uncertainty = uncertainties.get("absorptance_emittance_ratio")
    if ratio_uncertainty is None:
        absorptance_uncertainty = _real(
            "uncertainty['solar_absorptance']",
            uncertainties.get("solar_absorptance", 0.0),
            allow_zero=True,
        )
        emittance_uncertainty = _real(
            "uncertainty['hemispherical_emittance']",
            uncertainties.get("hemispherical_emittance", 0.0),
            allow_zero=True,
        )
        # Propagate the two property uncertainties through the quotient.
        relative = math.hypot(
            absorptance_uncertainty / absorptance if absorptance else 0.0,
            emittance_uncertainty / emittance,
        )
        ratio_uncertainty = ratio * relative
    resolved_uncertainty = {
        "solar_absorptance": _real(
            "uncertainty['solar_absorptance']",
            uncertainties.get("solar_absorptance", 0.0),
            allow_zero=True,
        ),
        "hemispherical_emittance": _real(
            "uncertainty['hemispherical_emittance']",
            uncertainties.get("hemispherical_emittance", 0.0),
            allow_zero=True,
        ),
        "absorptance_emittance_ratio": _real(
            "uncertainty['absorptance_emittance_ratio']",
            ratio_uncertainty,
            allow_zero=True,
        ),
    }
    checks = []
    findings = []
    for name, record in sorted(limit_records.items()):
        disposition = guard_banded_disposition(
            measured[name],
            record["value"],
            record["sense"],
            resolved_uncertainty[name],
        )
        checks.append(
            {
                "property": name,
                "measured": measured[name],
                "limit": record["value"],
                "sense": record["sense"],
                "uncertainty": resolved_uncertainty[name],
                "disposition": disposition,
                "limit_admissible": record["admissible"],
            }
        )
        if disposition == "fail":
            findings.append(
                "sample %s reports %s of %.6g against a %s limit of %g"
                % (
                    sample_id,
                    name.replace("_", " "),
                    measured[name],
                    record["sense"],
                    record["value"],
                )
            )
        elif disposition == "marginal":
            findings.append(
                "sample %s sits within its own measurement uncertainty of the %s "
                "limit, so it is marginal rather than accepted"
                % (sample_id, name.replace("_", " "))
            )
    return {
        "id": sample_id,
        "solar_absorptance": absorptance,
        "hemispherical_emittance": emittance,
        "absorptance_emittance_ratio": ratio,
        "checks": checks,
        "disposition": worst_disposition([check["disposition"] for check in checks]),
        "findings": findings,
    }


def assess_thermo_optical_criteria(spec):
    """Run the full clause 6.4.3.6.3 acceptance limit assessment.

    spec keys: drawing (number, revision, lot_built_to_revision), limits (a
    mapping of governed property name to a value and a source, optionally the
    invoked document), samples (non-empty sequence of measured samples with an
    optional per-property uncertainty mapping).
    """
    data = _mapping("spec", spec, ("drawing", "limits", "samples"))
    drawing, findings = validate_drawing(data["drawing"])
    limits = _mapping("spec['limits']", data["limits"])
    if not limits:
        raise ValueError("spec['limits'] must carry at least one governed limit")
    limit_records = {}
    for name in sorted(limits):
        record, limit_findings = validate_limit(name, limits[name])
        limit_records[name] = record
        findings.extend(limit_findings)
    samples = data["samples"]
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("spec['samples'] must be a non-empty sequence of samples")
    records = []
    seen = set()
    for sample in samples:
        record = evaluate_sample_limits(sample, limit_records)
        if record["id"] in seen:
            raise ValueError(
                "sample id '%s' appears twice in spec['samples']" % record["id"]
            )
        seen.add(record["id"])
        records.append(record)
        findings.extend(record["findings"])
    tally = {name: 0 for name in DISPOSITION_ORDER}
    for record in records:
        tally[record["disposition"]] += 1
    return {
        "drawing": drawing,
        "limit_records": limit_records,
        "sample_records": records,
        "disposition_counts": tally,
        "lot_disposition": worst_disposition(
            [record["disposition"] for record in records]
        ),
        "findings": findings,
        "valid": not findings,
    }
