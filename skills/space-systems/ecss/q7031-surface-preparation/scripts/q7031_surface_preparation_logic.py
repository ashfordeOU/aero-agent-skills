"""Substrate preparation sequence before a paint system is applied.

Anchor: ECSS-Q-ST-70-31C surface-preparation clause -- the ordered work that
turns a delivered substrate into a surface a paint system will bond to:
degreasing, abrasion, rinsing, drying, chemical conversion treatment where the
substrate needs one, and masking of the areas that must stay bare. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the required step sequence for the substrate and paint system. A
   metallic substrate owes a conversion treatment that a laminate does not, and
   a conductive or bonded keep-out area owes masking that a plain item does not.
2. Compare the as-performed sequence against the required one: steps missing,
   steps nobody recognises, steps repeated where repetition is not allowed, and
   steps performed out of order.
3. Apply the prepared-to-first-coat time window, because a prepared surface
   re-oxidises and re-contaminates and does not stay prepared indefinitely.
4. Check the masking record covers every declared keep-out area.
5. Close with one disposition: ready-to-coat, rework-required or re-prepare.
"""

import math

__all__ = [
    "PREP_STEPS",
    "REPEATABLE_STEPS",
    "CONVERSION_COATED_SUBSTRATES",
    "PREP_WINDOW_H",
    "DEFAULT_PREP_WINDOW_H",
    "DISPOSITIONS",
    "normalize_key",
    "normalize_sequence",
    "required_sequence",
    "prep_window_h",
    "sequence_findings",
    "window_finding",
    "masking_findings",
    "assess_preparation",
]

# Every preparation step this leaf recognises, in the order they may occur.
PREP_STEPS = (
    "degrease",
    "abrade",
    "rinse",
    "conversion-coat",
    "dry",
    "mask",
)

# Rinsing may legitimately happen more than once; the others may not.
REPEATABLE_STEPS = ("rinse",)

# Substrates whose preparation includes a chemical conversion treatment.
CONVERSION_COATED_SUBSTRATES = (
    "aluminium-alloy",
    "magnesium-alloy",
)

# Maximum hours a prepared surface may wait for its first coat.
PREP_WINDOW_H = {
    "aluminium-alloy": 8.0,
    "magnesium-alloy": 4.0,
    "titanium-alloy": 16.0,
    "stainless-steel": 16.0,
    "cfrp-laminate": 24.0,
    "gfrp-laminate": 24.0,
}
DEFAULT_PREP_WINDOW_H = 8.0

DISPOSITIONS = ("ready-to-coat", "rework-required", "re-prepare")

_WINDOW_TOLERANCE_H = 1e-9


def normalize_key(value, label):
    """Return a trimmed lower-case key, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, v))
    return v


def normalize_sequence(steps):
    """Return the validated, lower-cased step list of a performed sequence."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("a performed preparation sequence needs at least one step")
    return [normalize_key(step, "preparation step") for step in steps]


def required_sequence(substrate, keep_out_areas=None):
    """Return the ordered preparation steps a substrate and item owe."""
    key = normalize_key(substrate, "substrate")
    steps = ["degrease", "abrade", "rinse"]
    if key in CONVERSION_COATED_SUBSTRATES:
        steps.extend(["conversion-coat", "rinse"])
    steps.append("dry")
    if keep_out_areas:
        if not isinstance(keep_out_areas, (list, tuple)):
            raise ValueError("keep_out_areas must be a sequence")
        steps.append("mask")
    return tuple(steps)


def prep_window_h(substrate):
    """Return the hours a prepared surface of this substrate may wait."""
    key = normalize_key(substrate, "substrate")
    return PREP_WINDOW_H.get(key, DEFAULT_PREP_WINDOW_H)


def sequence_findings(required, performed):
    """Return the findings of an as-performed sequence against the required one."""
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required sequence must be a non-empty sequence")
    done = normalize_sequence(performed)
    findings = []
    for step in done:
        if step not in PREP_STEPS:
            findings.append("unrecognised-step-%s" % step)
    for step in set(required):
        if done.count(step) < list(required).count(step):
            findings.append("missing-step-%s" % step)
    for step in set(done):
        if step in PREP_STEPS and step not in REPEATABLE_STEPS and done.count(step) > 1:
            findings.append("repeated-step-%s" % step)
    # A repeatable step legitimately occurs between other steps, so it takes no
    # part in the order check; the non-repeatable steps carry the sequence.
    ordered = [
        PREP_STEPS.index(s)
        for s in done
        if s in PREP_STEPS and s not in REPEATABLE_STEPS
    ]
    for i in range(1, len(ordered)):
        if ordered[i] < ordered[i - 1]:
            findings.append("steps-out-of-order")
            break
    return sorted(set(findings))


def window_finding(elapsed_h, limit_h):
    """Return a finding when the prepared surface waited longer than allowed."""
    elapsed = _non_negative(elapsed_h, "elapsed_h")
    limit = _non_negative(limit_h, "limit_h")
    if elapsed < limit or math.isclose(elapsed, limit, rel_tol=0.0,
                                       abs_tol=_WINDOW_TOLERANCE_H):
        return None
    return "prepared-to-coat-window-exceeded"


def masking_findings(keep_out_areas, masked_areas):
    """Return the declared keep-out areas the masking record does not cover."""
    declared = list(keep_out_areas or [])
    covered = list(masked_areas or [])
    if not isinstance(declared, list) or not isinstance(covered, list):
        raise ValueError("keep-out and masked areas must be sequences")
    covered_keys = {normalize_key(a, "masked area") for a in covered}
    findings = []
    for area in declared:
        key = normalize_key(area, "keep-out area")
        if key not in covered_keys:
            findings.append("keep-out-area-unmasked-%s" % key)
    for key in sorted(covered_keys):
        if key not in {normalize_key(a, "keep-out area") for a in declared}:
            findings.append("masked-area-not-declared-%s" % key)
    return findings


def assess_preparation(record):
    """Return the readiness disposition for one prepared surface."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("substrate", "performed_steps", "elapsed_since_prep_h"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    keep_out = record.get("keep_out_areas") or []
    required = required_sequence(record["substrate"], keep_out)
    findings = sequence_findings(required, record["performed_steps"])
    limit = record.get("window_h", prep_window_h(record["substrate"]))
    window = window_finding(record["elapsed_since_prep_h"], limit)
    if window:
        findings.append(window)
    mask_gaps = masking_findings(keep_out, record.get("masked_areas"))
    findings.extend(mask_gaps)
    sequence_broken = any(
        f.startswith("missing-step") or f.startswith("unrecognised-step")
        or f.startswith("repeated-step") or f == "steps-out-of-order"
        for f in findings
    )
    if sequence_broken or window:
        disposition = "re-prepare"
    elif mask_gaps:
        disposition = "rework-required"
    else:
        disposition = "ready-to-coat"
    return {
        "disposition": disposition,
        "required_steps": list(required),
        "findings": findings,
        "window_h": float(limit),
    }
