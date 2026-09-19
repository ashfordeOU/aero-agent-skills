"""Mechanism grounding and bonding assessment.

Anchor: ECSS-E-ST-33-01C clause 4.7.7.4 (every mechanism is bonded to the
spacecraft structure). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each bonding strap: length, width, thickness, material resistivity
   and the joint resistances at its two ends.
2. Grade the strap geometry. A strap is a conductor at DC and an inductor at
   the frequencies a motor drive produces; keeping its length-to-width ratio
   under the geometry limit keeps that inductance low enough for the strap to
   remain a bond rather than a choke.
3. Compute the DC resistance of each strap as the bulk resistance of the foil
   plus the two joint resistances, and grade it against the bond limit.
4. Grade coverage: every mechanism in the inventory carries at least one bond,
   and the bonds present are attributed to a real mechanism.
5. Report per-strap records, per-mechanism coverage and the aggregated
   findings.
"""

import math

__all__ = [
    "ASPECT_RATIO_LIMIT",
    "DC_RESISTANCE_LIMIT_OHM",
    "RATIO_TOLERANCE",
    "RESISTANCE_TOLERANCE_OHM",
    "MATERIAL_RESISTIVITY_OHM_M",
    "validate_strap",
    "aspect_ratio",
    "bulk_resistance_ohm",
    "strap_dc_resistance_ohm",
    "grade_strap",
    "coverage_findings",
    "parallel_resistance_ohm",
    "assess_bonding",
]

# Geometry limit: the length-to-width ratio of a bonding strap stays below
# this value so the strap's inductance does not turn it into a choke at the
# frequencies a mechanism drive produces.
ASPECT_RATIO_LIMIT = 4.0

# DC resistance limit of one mechanism-to-structure bond path, in ohms.
DC_RESISTANCE_LIMIT_OHM = 10.0e-3

# A ratio or a resistance can land a few ULPs on the wrong side of an exact
# equality. Absorb the representation error here rather than relaxing the
# engineering limit. A value inside the tolerance of the limit is AT the
# limit, and a limit written as a strict inequality is not met there.
RATIO_TOLERANCE = 1e-9
RESISTANCE_TOLERANCE_OHM = 1e-12

# Bulk resistivity at room temperature, ohm-metres.
MATERIAL_RESISTIVITY_OHM_M = {
    "copper": 1.72e-8,
    "aluminium": 2.82e-8,
    "tinned-copper-braid": 2.10e-8,
    "stainless-steel": 6.90e-7,
    "silver": 1.59e-8,
}


def _positive(label, value):
    """Return value as a positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def validate_strap(strap):
    """Return a normalised bonding-strap record.

    Required keys: id, mechanism, length_m, width_m, thickness_m, material.
    Optional keys: joint_resistance_ohm (each end), measured_resistance_ohm.
    """
    if not isinstance(strap, dict):
        raise ValueError("strap must be a mapping")
    for key in ("id", "mechanism", "length_m", "width_m", "thickness_m", "material"):
        if key not in strap:
            raise ValueError("strap missing required key '%s'" % key)
    for key in ("id", "mechanism"):
        if not isinstance(strap[key], str) or not strap[key].strip():
            raise ValueError("strap %s must be a non-empty string" % key)
    material = strap["material"]
    if not isinstance(material, str):
        raise ValueError("material must be a string")
    material = material.strip().lower()
    if material not in MATERIAL_RESISTIVITY_OHM_M:
        raise ValueError(
            "material %r is not one of %s"
            % (strap["material"], ", ".join(sorted(MATERIAL_RESISTIVITY_OHM_M)))
        )
    record = {
        "id": strap["id"].strip(),
        "mechanism": strap["mechanism"].strip(),
        "length_m": _positive("length_m", strap["length_m"]),
        "width_m": _positive("width_m", strap["width_m"]),
        "thickness_m": _positive("thickness_m", strap["thickness_m"]),
        "material": material,
        "resistivity_ohm_m": MATERIAL_RESISTIVITY_OHM_M[material],
        "joint_resistance_ohm": _non_negative(
            "joint_resistance_ohm", strap.get("joint_resistance_ohm", 0.0)
        ),
    }
    if "measured_resistance_ohm" in strap:
        record["measured_resistance_ohm"] = _positive(
            "measured_resistance_ohm", strap["measured_resistance_ohm"]
        )
    return record


def aspect_ratio(length_m, width_m):
    """Return the length-to-width ratio of a bonding strap."""
    length = _positive("length_m", length_m)
    width = _positive("width_m", width_m)
    return length / width


def bulk_resistance_ohm(length_m, width_m, thickness_m, resistivity_ohm_m):
    """Return the bulk DC resistance of a rectangular strap."""
    length = _positive("length_m", length_m)
    width = _positive("width_m", width_m)
    thickness = _positive("thickness_m", thickness_m)
    resistivity = _positive("resistivity_ohm_m", resistivity_ohm_m)
    return resistivity * length / (width * thickness)


def strap_dc_resistance_ohm(strap):
    """Return the end-to-end DC resistance of a strap, joints included."""
    record = validate_strap(strap)
    if "measured_resistance_ohm" in record:
        return record["measured_resistance_ohm"]
    bulk = bulk_resistance_ohm(
        record["length_m"], record["width_m"], record["thickness_m"],
        record["resistivity_ohm_m"],
    )
    return bulk + 2.0 * record["joint_resistance_ohm"]


def parallel_resistance_ohm(resistances):
    """Return the combined resistance of bonds carrying the same path in parallel."""
    if not isinstance(resistances, (list, tuple)) or not resistances:
        raise ValueError("resistances must be a non-empty sequence")
    conductance = 0.0
    for index, value in enumerate(resistances):
        conductance += 1.0 / _positive("resistances[%d]" % index, value)
    return 1.0 / conductance


def grade_strap(strap, ratio_limit=ASPECT_RATIO_LIMIT,
                resistance_limit_ohm=DC_RESISTANCE_LIMIT_OHM):
    """Return the geometry and resistance grading of one bonding strap."""
    record = validate_strap(strap)
    limit_ratio = _positive("ratio_limit", ratio_limit)
    limit_ohm = _positive("resistance_limit_ohm", resistance_limit_ohm)
    ratio = aspect_ratio(record["length_m"], record["width_m"])
    resistance = strap_dc_resistance_ohm(strap)
    # Both limits are written as strict inequalities, so a value sitting on the
    # limit within the named tolerance does NOT meet them.
    ratio_ok = ratio < limit_ratio and not math.isclose(
        ratio, limit_ratio, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    resistance_ok = resistance < limit_ohm and not math.isclose(
        resistance, limit_ohm, rel_tol=0.0, abs_tol=RESISTANCE_TOLERANCE_OHM
    )
    findings = []
    if not ratio_ok:
        findings.append(
            "%s (%s): length-to-width ratio %.4f does not stay below the %.4f limit; "
            "the strap is an inductor at drive frequencies"
            % (record["id"], record["mechanism"], ratio, limit_ratio)
        )
    if not resistance_ok:
        findings.append(
            "%s (%s): DC bond resistance %.6g ohm does not stay below the %.6g ohm limit"
            % (record["id"], record["mechanism"], resistance, limit_ohm)
        )
    return {
        "id": record["id"],
        "mechanism": record["mechanism"],
        "aspect_ratio": ratio,
        "dc_resistance_ohm": resistance,
        "ratio_ok": ratio_ok,
        "resistance_ok": resistance_ok,
        "compliant": ratio_ok and resistance_ok,
        "findings": findings,
    }


def coverage_findings(mechanisms, straps):
    """Return the findings for mechanisms with no bond and straps with no mechanism."""
    if not isinstance(mechanisms, (list, tuple)) or not mechanisms:
        raise ValueError("mechanisms must be a non-empty sequence of names")
    names = []
    for index, name in enumerate(mechanisms):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("mechanisms[%d] must be a non-empty string" % index)
        cleaned = name.strip()
        if cleaned in names:
            raise ValueError("duplicate mechanism name '%s'" % cleaned)
        names.append(cleaned)
    bonded = {}
    for strap in straps:
        record = validate_strap(strap)
        bonded.setdefault(record["mechanism"], []).append(record["id"])
    findings = []
    for name in names:
        if name not in bonded:
            findings.append("%s: no bonding strap to structure" % name)
    for mechanism in sorted(bonded):
        if mechanism not in names:
            findings.append(
                "bond(s) %s attributed to '%s', which is not in the mechanism inventory"
                % (", ".join(sorted(bonded[mechanism])), mechanism)
            )
    return {"bonded": bonded, "findings": findings}


def assess_bonding(spec):
    """Run the full clause 4.7.7.4 grounding and bonding assessment.

    spec keys: mechanisms (sequence of names), straps (non-empty sequence).
    Optional: ratio_limit, resistance_limit_ohm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("mechanisms", "straps"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    straps = spec["straps"]
    if not isinstance(straps, (list, tuple)) or not straps:
        raise ValueError("spec['straps'] must be a non-empty sequence")
    ratio_limit = spec.get("ratio_limit", ASPECT_RATIO_LIMIT)
    resistance_limit = spec.get("resistance_limit_ohm", DC_RESISTANCE_LIMIT_OHM)
    records = []
    findings = []
    seen = set()
    for strap in straps:
        graded = grade_strap(strap, ratio_limit, resistance_limit)
        if graded["id"] in seen:
            raise ValueError("duplicate strap id '%s'" % graded["id"])
        seen.add(graded["id"])
        records.append(graded)
        findings.extend(graded["findings"])
    coverage = coverage_findings(spec["mechanisms"], straps)
    findings.extend(coverage["findings"])
    return {
        "straps": records,
        "bonded": coverage["bonded"],
        "findings": findings,
        "compliant": not findings,
    }
