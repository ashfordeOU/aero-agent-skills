"""Validity checks on a completed mechanical test before its result is accepted.

Anchor: ECSS-Q-ST-70-45 acceptance clause -- deciding whether a test that ran
to fracture actually measured the material, or measured the grips, the
extensometer or a machine event. Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Place the fracture along the gauge length: inside it, and far enough from
   the gauge marks that the elongation does not owe the displaced-gauge
   treatment.
2. Take the fracture appearance as a named mode and decide from the mode alone
   whether the specimen broke where the material governs or where the fixture
   did.
3. Sweep the run for anomalies: an extensometer that slipped, a machine that
   stopped, a soak temperature or a strain rate outside its band, and a force
   discontinuity before maximum force.
4. Turn the three into one verdict per specimen: accepted, accepted with the
   elongation qualified, or invalid and owed a repeat.
5. Dispose of the lot on the valid specimens only, against the number of valid
   results the acceptance owes and the repeats the programme allows.
"""

import math

__all__ = [
    "FRACTURE_MODES",
    "DEFAULT_OUTER_FIFTH_FRACTION",
    "DEFAULT_RATE_TOLERANCE_PCT",
    "DEFAULT_TEMPERATURE_TOLERANCE_K",
    "DEFAULT_MAX_FORCE_DROP_FRACTION",
    "VALIDITY_TOLERANCE",
    "fracture_position",
    "fracture_mode_verdict",
    "rate_within_band",
    "temperature_within_band",
    "force_discontinuity",
    "anomaly_findings",
    "specimen_verdict",
    "lot_disposition",
    "assess_test_validity",
]

# Named fracture appearances and whether each one leaves the result standing.
# A mode outside this set is refused rather than assumed benign.
FRACTURE_MODES = {
    "cup-and-cone": True,
    "slant-shear": True,
    "flat-transgranular": True,
    "in-grip": False,
    "at-shoulder": False,
    "at-knife-edge": False,
    "at-gauge-mark": False,
    "at-machining-defect": False,
}

# A fracture further than this fraction of the gauge length from mid-gauge
# sits in the outer part of the gauge length, where the elongation owes the
# displaced-gauge treatment rather than a plain measurement.
DEFAULT_OUTER_FIFTH_FRACTION = 0.3

DEFAULT_RATE_TOLERANCE_PCT = 20.0
DEFAULT_TEMPERATURE_TOLERANCE_K = 3.0

# A force drop larger than this fraction of the running force, before maximum
# force, is a slip or a grip event rather than material behaviour.
DEFAULT_MAX_FORCE_DROP_FRACTION = 0.02

# Position and band comparisons are float comparisons against round limits. A
# value physically exactly on a limit can land a few ULP either side, so the
# comparisons absorb that rather than moving the limit.
VALIDITY_TOLERANCE = 1e-12


def _real(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(label, value):
    number = _real(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def fracture_position(distance_from_mid_mm, gauge_length_mm,
                      outer_fraction=DEFAULT_OUTER_FIFTH_FRACTION):
    """Place the fracture along the gauge length and say what it costs.

    Returns the offset as a fraction of the gauge length, whether the fracture
    fell inside the gauge length at all, and whether the elongation owes the
    displaced-gauge treatment.
    """
    offset = abs(_real("distance_from_mid_mm", distance_from_mid_mm))
    length = _positive("gauge_length_mm", gauge_length_mm)
    fraction = _positive("outer_fraction", outer_fraction)
    if fraction >= 0.5:
        raise ValueError("outer_fraction must sit inside half the gauge length, got %r" % (outer_fraction,))
    relative = offset / length
    half = 0.5
    inside = relative < half or math.isclose(relative, half, rel_tol=0.0, abs_tol=VALIDITY_TOLERANCE)
    in_outer = not (
        relative < fraction or math.isclose(relative, fraction, rel_tol=0.0, abs_tol=VALIDITY_TOLERANCE)
    )
    return {
        "offset_fraction": relative,
        "inside_gauge_length": inside,
        "needs_displaced_gauge": inside and in_outer,
    }


def fracture_mode_verdict(mode):
    """Return whether a named fracture appearance leaves the result standing."""
    if not isinstance(mode, str) or not mode:
        raise ValueError("fracture mode must be a non-empty name, got %r" % (mode,))
    key = mode.strip().lower()
    if key not in FRACTURE_MODES:
        raise ValueError(
            "fracture mode %r is not one of %s; an unnamed appearance is not assumed "
            "acceptable" % (mode, sorted(FRACTURE_MODES))
        )
    return {"mode": key, "material_governed": FRACTURE_MODES[key]}


def rate_within_band(actual, nominal, tolerance_pct=DEFAULT_RATE_TOLERANCE_PCT):
    """Return whether an achieved rate sat inside its permitted band."""
    achieved = _positive("actual rate", actual)
    target = _positive("nominal rate", nominal)
    tolerance = _positive("tolerance_pct", tolerance_pct)
    deviation = 100.0 * abs(achieved - target) / target
    within = deviation < tolerance or math.isclose(
        deviation, tolerance, rel_tol=0.0, abs_tol=VALIDITY_TOLERANCE
    )
    return {"deviation_pct": deviation, "within": within}


def temperature_within_band(actual_k, nominal_k, tolerance_k=DEFAULT_TEMPERATURE_TOLERANCE_K):
    """Return whether a soak temperature sat inside its permitted band."""
    achieved = _positive("actual_k", actual_k)
    target = _positive("nominal_k", nominal_k)
    tolerance = _positive("tolerance_k", tolerance_k)
    deviation = abs(achieved - target)
    within = deviation < tolerance or math.isclose(
        deviation, tolerance, rel_tol=0.0, abs_tol=VALIDITY_TOLERANCE
    )
    return {"deviation_k": deviation, "within": within}


def force_discontinuity(forces, max_drop_fraction=DEFAULT_MAX_FORCE_DROP_FRACTION):
    """Find the first force drop before maximum force larger than the allowance.

    A slipping grip or a slipping extensometer shows as a step down in force
    while the crosshead is still rising; after maximum force a falling force
    is the specimen necking and is not an anomaly.
    """
    if not isinstance(forces, (list, tuple)) or len(forces) < 3:
        raise ValueError("a force trace needs at least three readings")
    allowance = _positive("max_drop_fraction", max_drop_fraction)
    if allowance >= 1.0:
        raise ValueError("max_drop_fraction must be below one, got %r" % (max_drop_fraction,))
    values = [_real("forces[%d]" % index, item) for index, item in enumerate(forces)]
    peak_index = max(range(len(values)), key=lambda index: values[index])
    for index in range(1, peak_index + 1):
        previous = values[index - 1]
        if previous <= 0.0:
            continue
        drop = (previous - values[index]) / previous
        if drop > allowance and not math.isclose(
            drop, allowance, rel_tol=0.0, abs_tol=VALIDITY_TOLERANCE
        ):
            return {"index": index, "drop_fraction": drop, "found": True}
    return {"index": None, "drop_fraction": 0.0, "found": False}


def anomaly_findings(record, rate_tolerance_pct=DEFAULT_RATE_TOLERANCE_PCT,
                     temperature_tolerance_k=DEFAULT_TEMPERATURE_TOLERANCE_K,
                     max_drop_fraction=DEFAULT_MAX_FORCE_DROP_FRACTION):
    """Sweep one specimen record for the anomalies that invalidate a test."""
    if not isinstance(record, dict):
        raise ValueError("a specimen record must be a mapping")
    findings = []
    if record.get("extensometer_slipped"):
        findings.append("the extensometer slipped during the run")
    if record.get("machine_stopped"):
        findings.append("the machine stopped and the run was restarted")
    if record.get("actual_rate") is not None and record.get("nominal_rate") is not None:
        band = rate_within_band(record["actual_rate"], record["nominal_rate"], rate_tolerance_pct)
        if not band["within"]:
            findings.append(
                "the achieved rate was %.2f%% away from nominal, outside the %.2f%% band"
                % (band["deviation_pct"], rate_tolerance_pct)
            )
    if record.get("actual_temperature_k") is not None and record.get("nominal_temperature_k") is not None:
        band = temperature_within_band(
            record["actual_temperature_k"], record["nominal_temperature_k"], temperature_tolerance_k
        )
        if not band["within"]:
            findings.append(
                "the soak sat %.2f K away from nominal, outside the %.2f K band"
                % (band["deviation_k"], temperature_tolerance_k)
            )
    if record.get("force_trace") is not None:
        step = force_discontinuity(record["force_trace"], max_drop_fraction)
        if step["found"]:
            findings.append(
                "the force fell %.2f%% at reading %d, before maximum force"
                % (100.0 * step["drop_fraction"], step["index"])
            )
    return findings


def specimen_verdict(record, gauge_length_mm, outer_fraction=DEFAULT_OUTER_FIFTH_FRACTION,
                     rate_tolerance_pct=DEFAULT_RATE_TOLERANCE_PCT,
                     temperature_tolerance_k=DEFAULT_TEMPERATURE_TOLERANCE_K,
                     max_drop_fraction=DEFAULT_MAX_FORCE_DROP_FRACTION):
    """Return the validity verdict of one tested specimen."""
    if not isinstance(record, dict):
        raise ValueError("a specimen record must be a mapping")
    for key in ("id", "fracture_offset_mm", "fracture_mode"):
        if key not in record:
            raise ValueError("specimen record missing required key '%s'" % key)
    reasons = []
    qualifications = []

    position = fracture_position(record["fracture_offset_mm"], gauge_length_mm, outer_fraction)
    if not position["inside_gauge_length"]:
        reasons.append("the fracture fell outside the gauge length")
    elif position["needs_displaced_gauge"]:
        qualifications.append(
            "the fracture sat in the outer part of the gauge length; the elongation owes "
            "the displaced-gauge treatment"
        )

    mode = fracture_mode_verdict(record["fracture_mode"])
    if not mode["material_governed"]:
        reasons.append("the fracture appearance '%s' is fixture-governed" % mode["mode"])

    reasons.extend(
        anomaly_findings(record, rate_tolerance_pct, temperature_tolerance_k, max_drop_fraction)
    )

    return {
        "id": record["id"],
        "position": position,
        "mode": mode,
        "valid": not reasons,
        "reasons": reasons,
        "qualifications": qualifications,
    }


def lot_disposition(verdicts, required_valid, max_repeats=0):
    """Dispose of a lot on its valid specimens only."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence of specimen verdicts")
    if not isinstance(required_valid, int) or isinstance(required_valid, bool) or required_valid < 1:
        raise ValueError("required_valid must be a whole number of at least one, got %r" % (required_valid,))
    if not isinstance(max_repeats, int) or isinstance(max_repeats, bool) or max_repeats < 0:
        raise ValueError("max_repeats must be a non-negative whole number, got %r" % (max_repeats,))
    valid = [verdict for verdict in verdicts if verdict.get("valid")]
    invalid = [verdict for verdict in verdicts if not verdict.get("valid")]
    shortfall = required_valid - len(valid)
    if shortfall <= 0:
        disposition = "accept"
    elif shortfall <= max_repeats and len(invalid) >= shortfall:
        disposition = "repeat"
    else:
        disposition = "reject"
    return {
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "required_valid": required_valid,
        "shortfall": max(shortfall, 0),
        "disposition": disposition,
        "repeat_ids": [verdict["id"] for verdict in invalid][: max(shortfall, 0)],
    }


def assess_test_validity(spec):
    """Run the whole validity assessment over a tested lot.

    spec keys: specimens, gauge_length_mm, required_valid. Optional:
    outer_fraction, rate_tolerance_pct, temperature_tolerance_k,
    max_drop_fraction, max_repeats.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("specimens", "gauge_length_mm", "required_valid"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if not isinstance(spec["specimens"], (list, tuple)) or not spec["specimens"]:
        raise ValueError("a lot needs at least one tested specimen")
    verdicts = [
        specimen_verdict(
            record,
            spec["gauge_length_mm"],
            spec.get("outer_fraction", DEFAULT_OUTER_FIFTH_FRACTION),
            spec.get("rate_tolerance_pct", DEFAULT_RATE_TOLERANCE_PCT),
            spec.get("temperature_tolerance_k", DEFAULT_TEMPERATURE_TOLERANCE_K),
            spec.get("max_drop_fraction", DEFAULT_MAX_FORCE_DROP_FRACTION),
        )
        for record in spec["specimens"]
    ]
    lot = lot_disposition(verdicts, spec["required_valid"], spec.get("max_repeats", 0))
    findings = []
    for verdict in verdicts:
        for reason in verdict["reasons"]:
            findings.append("specimen '%s': %s" % (verdict["id"], reason))
    qualifications = []
    for verdict in verdicts:
        for note in verdict["qualifications"]:
            qualifications.append("specimen '%s': %s" % (verdict["id"], note))
    return {
        "verdicts": verdicts,
        "lot": lot,
        "findings": findings,
        "qualifications": qualifications,
        "acceptable": lot["disposition"] == "accept",
    }
