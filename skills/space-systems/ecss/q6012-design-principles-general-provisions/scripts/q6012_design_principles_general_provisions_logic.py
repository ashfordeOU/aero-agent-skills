#!/usr/bin/env python3
"""Baseline design provisions held across every stage of an MMIC design effort.

Anchor: ECSS-Q-ST-60-12C clause 7.1.2 (general provisions -- the baseline
conditions that apply across the whole of a microwave circuit design effort,
not at one milestone only). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared design-stage sequence against the canonical
   specification-to-freeze order: unknown names, duplicates and out-of-order
   sequences are input errors, not degenerate cases to be sorted silently.
2. Validate each declared provision: the stage it first applies from, whether
   it is mandatory, and its held/not-held status at each stage it was assessed
   at, with an evidence reference.
3. Build the coverage matrix of provision against stage, giving each cell one
   of four states: not-applicable (before the provision applies), held,
   not-held, or undeclared (applicable but never assessed).
4. Find, per provision, the first stage at which it lapses -- the earliest
   applicable stage whose state is not-held or undeclared. That stage, not the
   freeze milestone, is where the baseline was actually lost.
5. Evaluate the two numeric baseline conditions that carry the whole effort:
   the operating band has to sit inside the span the process models were
   validated over, and the predicted junction temperature has to sit inside
   the derating limit. Both boundaries absorb representation error with a
   named tolerance rather than by moving the limit.
6. Report whether the baseline is established: every mandatory provision held
   at every applicable declared stage, band inside the model span, junction
   temperature inside the derating limit.
"""

import math

__all__ = [
    "CANONICAL_STAGES",
    "MANDATORY_PROVISIONS",
    "STATE_NOT_APPLICABLE",
    "STATE_HELD",
    "STATE_NOT_HELD",
    "STATE_UNDECLARED",
    "BAND_TOLERANCE_GHZ",
    "TEMPERATURE_TOLERANCE_C",
    "normalise_stage",
    "validate_stage_sequence",
    "validate_provision",
    "provision_coverage",
    "first_lapse",
    "band_coverage",
    "derating_margin_c",
    "missing_mandatory_provisions",
    "assess_general_provisions",
]

# The design effort in canonical order. A provision applies from its own entry
# stage onwards, so the order is load bearing and is validated, never inferred.
CANONICAL_STAGES = (
    "specification",
    "architecture",
    "schematic-design",
    "layout",
    "verification",
    "design-freeze",
)

# Provision identifier -> the stage it first applies from. These are the
# baseline conditions clause 7.1.2 carries across the effort; a design that
# never declares one of them has no baseline, whatever its later results say.
MANDATORY_PROVISIONS = {
    "process-design-kit-currency": "specification",
    "radiation-environment-baseline": "specification",
    "lifetime-baseline": "specification",
    "model-validity-band": "architecture",
    "thermal-derating-baseline": "architecture",
    "layout-rule-compliance": "layout",
}

STATE_NOT_APPLICABLE = "not-applicable"
STATE_HELD = "held"
STATE_NOT_HELD = "not-held"
STATE_UNDECLARED = "undeclared"

# A band edge or a derating limit that a design sits exactly on is a
# representation question, not an engineering one. Absorb it here.
BAND_TOLERANCE_GHZ = 1e-9
TEMPERATURE_TOLERANCE_C = 1e-9


def _require_real(value, label, positive=False):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def normalise_stage(stage):
    """Return the canonical spelling of one design-stage name."""
    if not isinstance(stage, str):
        raise ValueError("stage must be a string, got %r" % (stage,))
    token = stage.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in token:
        token = token.replace("--", "-")
    if not token:
        raise ValueError("stage must not be empty")
    if token not in CANONICAL_STAGES:
        raise ValueError(
            "unknown design stage %r; the effort runs %s"
            % (stage, " -> ".join(CANONICAL_STAGES))
        )
    return token


def validate_stage_sequence(stages):
    """Return the declared stages as a canonical, strictly ordered tuple."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("stages must be a non-empty sequence of stage names")
    normalised = [normalise_stage(s) for s in stages]
    seen = set()
    previous = -1
    for name in normalised:
        if name in seen:
            raise ValueError("design stage %r declared more than once" % name)
        seen.add(name)
        index = CANONICAL_STAGES.index(name)
        if index <= previous:
            raise ValueError(
                "declared stages are out of order at %r; expected the "
                "specification-to-freeze order" % name
            )
        previous = index
    return tuple(normalised)


def validate_provision(provision):
    """Return one provision record normalised, raising on a malformed one."""
    if not isinstance(provision, dict):
        raise ValueError("provision must be a mapping, got %r" % (provision,))
    ident = provision.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("provision needs a non-empty string 'id'")
    ident = ident.strip().lower().replace("_", "-").replace(" ", "-")
    applies_from = provision.get("applies_from", MANDATORY_PROVISIONS.get(ident))
    if applies_from is None:
        raise ValueError(
            "provision %r is not a known baseline provision and declares no "
            "'applies_from' stage" % ident
        )
    applies_from = normalise_stage(applies_from)
    mandatory = provision.get("mandatory", ident in MANDATORY_PROVISIONS)
    if not isinstance(mandatory, bool):
        raise ValueError("provision %r 'mandatory' must be a boolean" % ident)
    raw_status = provision.get("stage_status", {})
    if not isinstance(raw_status, dict):
        raise ValueError("provision %r 'stage_status' must be a mapping" % ident)
    status = {}
    for stage, held in raw_status.items():
        key = normalise_stage(stage)
        if not isinstance(held, bool):
            raise ValueError(
                "provision %r status at stage %r must be a boolean" % (ident, key)
            )
        if key in status:
            raise ValueError("provision %r declares stage %r twice" % (ident, key))
        status[key] = held
    evidence = provision.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        raise ValueError("provision %r 'evidence' must be a string when given" % ident)
    return {
        "id": ident,
        "applies_from": applies_from,
        "mandatory": mandatory,
        "stage_status": status,
        "evidence": evidence.strip() if isinstance(evidence, str) else None,
    }


def provision_coverage(provision, stages):
    """Return the stage -> state row of the coverage matrix for one provision."""
    record = validate_provision(provision)
    ordered = validate_stage_sequence(stages)
    entry = CANONICAL_STAGES.index(record["applies_from"])
    row = {}
    for stage in ordered:
        if CANONICAL_STAGES.index(stage) < entry:
            row[stage] = STATE_NOT_APPLICABLE
        elif stage not in record["stage_status"]:
            row[stage] = STATE_UNDECLARED
        elif record["stage_status"][stage]:
            row[stage] = STATE_HELD
        else:
            row[stage] = STATE_NOT_HELD
    return row


def first_lapse(provision, stages):
    """Return the earliest declared stage where a provision stops holding."""
    row = provision_coverage(provision, stages)
    for stage in validate_stage_sequence(stages):
        if row[stage] in (STATE_NOT_HELD, STATE_UNDECLARED):
            return stage
    return None


def band_coverage(operating_band_ghz, model_band_ghz):
    """Return how the operating band sits inside the validated model span."""
    for label, band in (
        ("operating_band_ghz", operating_band_ghz),
        ("model_band_ghz", model_band_ghz),
    ):
        if not isinstance(band, (list, tuple)) or len(band) != 2:
            raise ValueError("%s must be a (low, high) pair" % label)
    op_lo = _require_real(operating_band_ghz[0], "operating band low edge", positive=True)
    op_hi = _require_real(operating_band_ghz[1], "operating band high edge", positive=True)
    md_lo = _require_real(model_band_ghz[0], "model band low edge", positive=True)
    md_hi = _require_real(model_band_ghz[1], "model band high edge", positive=True)
    if op_lo > op_hi:
        raise ValueError("operating band low edge %g exceeds high edge %g" % (op_lo, op_hi))
    if md_lo >= md_hi:
        raise ValueError("model band low edge %g does not precede high edge %g" % (md_lo, md_hi))
    low_margin = op_lo - md_lo
    high_margin = md_hi - op_hi
    inside = (
        low_margin >= -BAND_TOLERANCE_GHZ and high_margin >= -BAND_TOLERANCE_GHZ
    )
    return {
        "low_margin_ghz": low_margin,
        "high_margin_ghz": high_margin,
        "inside": inside,
    }


def derating_margin_c(junction_temperature_c, derating_limit_c):
    """Return the margin in kelvin between a junction temperature and its limit."""
    junction = _require_real(junction_temperature_c, "junction_temperature_c")
    limit = _require_real(derating_limit_c, "derating_limit_c")
    if junction <= -273.15 or limit <= -273.15:
        raise ValueError("temperatures must be above absolute zero")
    return limit - junction


def missing_mandatory_provisions(provisions):
    """Return the mandatory provision ids that were never declared at all."""
    if not isinstance(provisions, (list, tuple)):
        raise ValueError("provisions must be a sequence of provision mappings")
    declared = set()
    for provision in provisions:
        declared.add(validate_provision(provision)["id"])
    return sorted(set(MANDATORY_PROVISIONS) - declared)


def assess_general_provisions(spec):
    """Run the clause 7.1.2 baseline-provision assessment over a design effort.

    spec keys: stages, provisions, operating_band_ghz, model_band_ghz,
    junction_temperature_c, derating_limit_c.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "stages",
        "provisions",
        "operating_band_ghz",
        "model_band_ghz",
        "junction_temperature_c",
        "derating_limit_c",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    stages = validate_stage_sequence(spec["stages"])
    provisions = spec["provisions"]
    if not isinstance(provisions, (list, tuple)) or not provisions:
        raise ValueError("spec['provisions'] must be a non-empty sequence")

    matrix = {}
    lapses = {}
    seen = set()
    for provision in provisions:
        record = validate_provision(provision)
        if record["id"] in seen:
            raise ValueError("provision %r declared more than once" % record["id"])
        seen.add(record["id"])
        matrix[record["id"]] = provision_coverage(provision, stages)
        lapses[record["id"]] = first_lapse(provision, stages)

    missing = missing_mandatory_provisions(provisions)
    band = band_coverage(spec["operating_band_ghz"], spec["model_band_ghz"])
    margin = derating_margin_c(spec["junction_temperature_c"], spec["derating_limit_c"])
    thermal_ok = margin >= -TEMPERATURE_TOLERANCE_C

    findings = []
    for ident in sorted(missing):
        findings.append(
            "mandatory baseline provision %r was never declared for any stage" % ident
        )
    for ident in sorted(lapses):
        stage = lapses[ident]
        if stage is None:
            continue
        mandatory = ident in MANDATORY_PROVISIONS
        findings.append(
            "%s provision %r first lapses at stage %r (%s)"
            % (
                "mandatory" if mandatory else "optional",
                ident,
                stage,
                matrix[ident][stage],
            )
        )
    for ident in sorted(seen):
        record = None
        for provision in provisions:
            candidate = validate_provision(provision)
            if candidate["id"] == ident:
                record = candidate
                break
        if record is not None and record["mandatory"] and not record["evidence"]:
            findings.append(
                "mandatory provision %r carries no evidence reference" % ident
            )
    if not band["inside"]:
        findings.append(
            "operating band sits outside the validated model span "
            "(low margin %.6g GHz, high margin %.6g GHz)"
            % (band["low_margin_ghz"], band["high_margin_ghz"])
        )
    if not thermal_ok:
        findings.append(
            "junction temperature exceeds the derating baseline by %.6g K" % (-margin,)
        )

    mandatory_lapsed = sorted(
        ident
        for ident in lapses
        if lapses[ident] is not None and ident in MANDATORY_PROVISIONS
    )
    baseline_established = (
        not missing and not mandatory_lapsed and band["inside"] and thermal_ok
    )
    return {
        "stages": list(stages),
        "coverage": matrix,
        "first_lapse": lapses,
        "missing_mandatory": missing,
        "mandatory_lapsed": mandatory_lapsed,
        "band": band,
        "derating_margin_c": margin,
        "thermal_baseline_held": thermal_ok,
        "baseline_established": baseline_established,
        "findings": findings,
    }
