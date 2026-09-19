"""Offgassing collection train: traps, sorbent beds and cold fingers.

Anchor: ECSS-Q-ST-70-29 apparatus step -- the arrangement that collects the
products driven off a conditioned specimen, and the sizing that decides which
compounds it actually captures. Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the stages of the train and the compounds to be collected.
2. Check the ordering rule: a cold surface belongs upstream of a sorbent bed.
3. Derate each sorbent breakthrough volume to the stage temperature, apply the
   safety factor and compare with the swept volume.
4. Require a stated margin between a cold-finger surface and each compound's
   condensation temperature.
5. Combine the contributing stage efficiencies in series.
6. Select the limiting compound and report the findings.
"""

import math

__all__ = [
    "KIND_SORBENT",
    "KIND_COLD_FINGER",
    "STAGE_KINDS",
    "FRACTION_TOLERANCE",
    "VOLUME_TOLERANCE_L",
    "TEMPERATURE_TOLERANCE_K",
    "DERATING_PER_KELVIN",
    "validate_stage",
    "validate_train",
    "validate_compound",
    "validate_sampling",
    "ordering_findings",
    "derated_breakthrough_volume",
    "sorbent_captures",
    "cold_finger_captures",
    "series_capture_fraction",
    "capture_for_compound",
    "size_collection_train",
]

KIND_SORBENT = "sorbent-trap"
KIND_COLD_FINGER = "cold-finger"
STAGE_KINDS = (KIND_SORBENT, KIND_COLD_FINGER)

# A capture fraction is a product of subtractions and can land a few ULP either
# side of a required value; absorb that here rather than by moving the
# requirement.
FRACTION_TOLERANCE = 1e-12
VOLUME_TOLERANCE_L = 1e-12
TEMPERATURE_TOLERANCE_K = 1e-9

# Breakthrough volume falls as the bed warms. A first-order derating of this
# many parts per kelvin above the reference temperature is applied so a heated
# line cannot be sized on its catalogue figure.
DERATING_PER_KELVIN = 0.02


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _unit_fraction(label, value):
    v = _real(label, value)
    if v <= 0.0 or v > 1.0:
        raise ValueError("%s must lie in (0, 1], got %r" % (label, value))
    return v


def validate_stage(stage, position):
    """Return one validated stage of the collection train."""
    if not isinstance(stage, dict):
        raise ValueError("stage %d must be a mapping" % position)
    kind = stage.get("kind")
    if kind not in STAGE_KINDS:
        raise ValueError(
            "stage %d kind must be one of %s, got %r"
            % (position, ", ".join(STAGE_KINDS), kind)
        )
    name = stage.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("stage %d needs a non-empty name" % position)
    out = {
        "name": name.strip(),
        "kind": kind,
        "position": position,
        "efficiency": _unit_fraction("stage %d efficiency" % position, stage.get("efficiency")),
    }
    if kind == KIND_SORBENT:
        out["temperature_k"] = _positive(
            "stage %d temperature_k" % position, stage.get("temperature_k")
        )
        out["reference_temperature_k"] = _positive(
            "stage %d reference_temperature_k" % position,
            stage.get("reference_temperature_k", 298.15),
        )
    else:
        out["surface_temperature_k"] = _positive(
            "stage %d surface_temperature_k" % position, stage.get("surface_temperature_k")
        )
        out["required_margin_k"] = _positive(
            "stage %d required_margin_k" % position, stage.get("required_margin_k", 20.0)
        )
    return out


def validate_train(stages):
    """Return the validated train in flow order, upstream stage first."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("the train needs at least one stage")
    out = [validate_stage(stage, i) for i, stage in enumerate(stages)]
    seen = set()
    for stage in out:
        if stage["name"] in seen:
            raise ValueError("duplicate stage name %r in the train" % stage["name"])
        seen.add(stage["name"])
    return out


def validate_compound(compound):
    """Return one validated compound to be collected."""
    if not isinstance(compound, dict):
        raise ValueError("compound must be a mapping")
    name = compound.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("compound needs a non-empty name")
    out = {
        "name": name.strip(),
        "condensation_temperature_k": _positive(
            "condensation_temperature_k of %s" % name,
            compound.get("condensation_temperature_k"),
        ),
        "breakthrough_volume_l": {},
    }
    table = compound.get("breakthrough_volume_l", {})
    if not isinstance(table, dict):
        raise ValueError(
            "breakthrough_volume_l of %s must be a mapping from stage name to litres" % name
        )
    for stage_name, volume in table.items():
        if not isinstance(stage_name, str) or not stage_name.strip():
            raise ValueError("breakthrough table of %s has a non-string stage key" % name)
        out["breakthrough_volume_l"][stage_name.strip()] = _positive(
            "breakthrough_volume_l[%s] of %s" % (stage_name, name), volume
        )
    return out


def validate_sampling(swept_volume_l, duration_h, safety_factor):
    """Return the validated sampling conditions of the collection."""
    factor = _real("safety_factor", safety_factor)
    if factor < 1.0:
        raise ValueError("safety_factor must be at least 1, got %r" % (safety_factor,))
    return {
        "swept_volume_l": _positive("swept_volume_l", swept_volume_l),
        "duration_h": _positive("duration_h", duration_h),
        "safety_factor": factor,
    }


def ordering_findings(train):
    """Return findings for sorbent beds sitting upstream of a cold surface."""
    findings = []
    for stage in train:
        if stage["kind"] != KIND_SORBENT:
            continue
        downstream_cold = [
            other["name"]
            for other in train
            if other["kind"] == KIND_COLD_FINGER and other["position"] > stage["position"]
        ]
        if downstream_cold:
            findings.append(
                "sorbent bed %r sits upstream of cold stage(s) %s; the condensable "
                "load reaches the bed first"
                % (stage["name"], ", ".join(downstream_cold))
            )
    return findings


def derated_breakthrough_volume(catalogue_volume_l, temperature_k, reference_temperature_k):
    """Return the breakthrough volume derated to the stage temperature."""
    volume = _positive("catalogue_volume_l", catalogue_volume_l)
    temperature = _positive("temperature_k", temperature_k)
    reference = _positive("reference_temperature_k", reference_temperature_k)
    excess = temperature - reference
    if excess <= 0.0:
        return volume
    factor = 1.0 - DERATING_PER_KELVIN * excess
    if factor <= 0.0:
        return 0.0
    return volume * factor


def sorbent_captures(stage, compound, sampling):
    """Decide whether a sorbent bed holds a compound for the swept volume."""
    if stage["kind"] != KIND_SORBENT:
        raise ValueError("sorbent_captures needs a %s stage" % KIND_SORBENT)
    catalogue = compound["breakthrough_volume_l"].get(stage["name"])
    if catalogue is None:
        return False, None, "no breakthrough volume declared for this bed"
    derated = derated_breakthrough_volume(
        catalogue, stage["temperature_k"], stage["reference_temperature_k"]
    )
    allowed = derated / sampling["safety_factor"]
    if sampling["swept_volume_l"] > allowed + VOLUME_TOLERANCE_L:
        return (
            False,
            allowed,
            "swept volume %g l exceeds the derated allowance %g l"
            % (sampling["swept_volume_l"], allowed),
        )
    return True, allowed, None


def cold_finger_captures(stage, compound):
    """Decide whether a cold surface sits far enough below the dew point."""
    if stage["kind"] != KIND_COLD_FINGER:
        raise ValueError("cold_finger_captures needs a %s stage" % KIND_COLD_FINGER)
    required = compound["condensation_temperature_k"] - stage["required_margin_k"]
    if stage["surface_temperature_k"] > required + TEMPERATURE_TOLERANCE_K:
        return (
            False,
            required,
            "surface at %g K is not %g K below the condensation point %g K"
            % (
                stage["surface_temperature_k"],
                stage["required_margin_k"],
                compound["condensation_temperature_k"],
            ),
        )
    return True, required, None


def series_capture_fraction(efficiencies):
    """Combine per-stage efficiencies in series: one minus the escape product."""
    if not isinstance(efficiencies, (list, tuple)):
        raise ValueError("efficiencies must be a sequence")
    escape = 1.0
    for i, value in enumerate(efficiencies):
        escape *= 1.0 - _unit_fraction("efficiency[%d]" % i, value)
    return 1.0 - escape


def capture_for_compound(train, compound, sampling):
    """Return the delivered capture fraction of the train for one compound."""
    contributing = []
    notes = []
    for stage in train:
        if stage["kind"] == KIND_SORBENT:
            holds, allowed, why = sorbent_captures(stage, compound, sampling)
            if holds:
                contributing.append(stage["efficiency"])
            else:
                notes.append("%s: %s" % (stage["name"], why))
            del allowed
        else:
            holds, required, why = cold_finger_captures(stage, compound)
            if holds:
                contributing.append(stage["efficiency"])
            else:
                notes.append("%s: %s" % (stage["name"], why))
            del required
    fraction = series_capture_fraction(contributing) if contributing else 0.0
    return {
        "compound": compound["name"],
        "capture_fraction": fraction,
        "contributing_stages": len(contributing),
        "notes": notes,
    }


def size_collection_train(spec):
    """Size and grade a collection train against the compounds it must hold.

    spec keys: stages, compounds, swept_volume_l, duration_h, safety_factor,
    minimum_capture_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "stages",
        "compounds",
        "swept_volume_l",
        "duration_h",
        "safety_factor",
        "minimum_capture_fraction",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    train = validate_train(spec["stages"])
    compounds = spec["compounds"]
    if not isinstance(compounds, (list, tuple)) or not compounds:
        raise ValueError("spec['compounds'] must be a non-empty sequence")
    sampling = validate_sampling(
        spec["swept_volume_l"], spec["duration_h"], spec["safety_factor"]
    )
    minimum = _unit_fraction("minimum_capture_fraction", spec["minimum_capture_fraction"])
    findings = ordering_findings(train)
    records = []
    seen = set()
    for item in compounds:
        compound = validate_compound(item)
        if compound["name"] in seen:
            raise ValueError("duplicate compound %r in the list" % compound["name"])
        seen.add(compound["name"])
        records.append(capture_for_compound(train, compound, sampling))
    uncaptured = [r["compound"] for r in records if r["contributing_stages"] == 0]
    short = [
        r["compound"]
        for r in records
        if r["capture_fraction"] < minimum - FRACTION_TOLERANCE
    ]
    limiting = min(records, key=lambda r: (r["capture_fraction"], r["compound"]))
    if uncaptured:
        findings.append(
            "no stage captures %s; a blank result for these is unmeasured, not absent"
            % ", ".join(sorted(uncaptured))
        )
    if short:
        findings.append(
            "delivered capture is below the required %g for %s"
            % (minimum, ", ".join(sorted(short)))
        )
    return {
        "train": train,
        "sampling": sampling,
        "minimum_capture_fraction": minimum,
        "records": records,
        "limiting_compound": limiting["compound"],
        "limiting_capture_fraction": limiting["capture_fraction"],
        "adequate": not short and not uncaptured,
        "findings": findings,
    }
