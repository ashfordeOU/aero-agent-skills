"""Design provisions that make cleanliness achievable and maintainable.

Anchor: ECSS-Q-ST-70-01C, the *design* clause -- the provisions a design has
to carry so the cleanliness level it is assigned can actually be reached,
verified and held: drainage, venting, material choice and surfaces a cleaning
operation can reach. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Venting: size the vent path of each enclosed volume from the depressurizing
   time constant it has to achieve, and require the path be filtered and
   directed away from surfaces that cannot tolerate its plume.
2. Drainage: walk the geometric features and find every trapped volume with no
   drain path, where cleaning fluid and the contamination it carries collect.
3. Material choice: require every material on an exposed surface to come from
   the screened set, and refuse a bare declaration with no screening behind it.
4. Accessible surfaces: compute the fraction of the surface area a cleaning and
   inspection operation can reach, and grade it against the fraction the
   assigned cleanliness level needs.
5. Grade the design provision by provision and report what has to change.
"""

import math

__all__ = [
    "CRITERION_TOLERANCE",
    "validate_positive",
    "validate_fraction",
    "vent_time_constant_s",
    "required_vent_area_m2",
    "assess_venting",
    "find_undrained_features",
    "assess_drainage",
    "cleanable_fraction",
    "assess_accessibility",
    "assess_material_choice",
    "assess_design_for_cleanliness",
]

# Provision criteria are comparisons between a computed quantity and a stated
# limit. A design sized exactly to its limit must grade as meeting it, so the
# representation error is absorbed here rather than by moving the limit.
CRITERION_TOLERANCE = 1e-12

PROVISIONS = ("venting", "drainage", "material-choice", "accessibility")


def validate_positive(value, label, allow_zero=False):
    """Return value as a finite positive float (or non-negative if allowed)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if allow_zero:
        if v < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def validate_fraction(value, label):
    """Return value as a finite fraction in [0, 1]."""
    v = validate_positive(value, label, allow_zero=True)
    if v > 1.0:
        raise ValueError("%s must not exceed 1, got %r" % (label, value))
    return v


def _at_most(value, limit):
    """True when value is at or under limit, within the named tolerance."""
    return value < limit or math.isclose(
        value, limit, rel_tol=CRITERION_TOLERANCE, abs_tol=0.0
    )


def _at_least(value, limit):
    """True when value is at or above limit, within the named tolerance."""
    return value > limit or math.isclose(
        value, limit, rel_tol=CRITERION_TOLERANCE, abs_tol=0.0
    )


def vent_time_constant_s(volume_m3, vent_area_m2, conductance_m_per_s):
    """Return the depressurizing time constant of a vented enclosed volume."""
    volume = validate_positive(volume_m3, "volume_m3")
    area = validate_positive(vent_area_m2, "vent_area_m2")
    conductance = validate_positive(conductance_m_per_s, "conductance_m_per_s")
    return volume / (conductance * area)


def required_vent_area_m2(volume_m3, target_time_constant_s, conductance_m_per_s):
    """Return the vent area a volume needs to reach a target time constant."""
    volume = validate_positive(volume_m3, "volume_m3")
    target = validate_positive(target_time_constant_s, "target_time_constant_s")
    conductance = validate_positive(conductance_m_per_s, "conductance_m_per_s")
    return volume / (conductance * target)


def assess_venting(enclosure):
    """Grade one enclosed volume's vent provision.

    enclosure keys: name, volume_m3, vent_area_m2, conductance_m_per_s,
    max_time_constant_s, filtered (bool), directed_away (bool).
    """
    if not isinstance(enclosure, dict):
        raise ValueError("enclosure must be a mapping")
    for key in ("name", "volume_m3", "vent_area_m2", "conductance_m_per_s",
                "max_time_constant_s"):
        if key not in enclosure:
            raise ValueError("enclosure missing required key %r" % key)
    name = enclosure["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("enclosure name must be a non-empty string")
    actual = vent_time_constant_s(
        enclosure["volume_m3"],
        enclosure["vent_area_m2"],
        enclosure["conductance_m_per_s"],
    )
    limit = validate_positive(enclosure["max_time_constant_s"], "max_time_constant_s")
    needed = required_vent_area_m2(
        enclosure["volume_m3"], limit, enclosure["conductance_m_per_s"]
    )
    findings = []
    fast_enough = _at_most(actual, limit)
    if not fast_enough:
        findings.append(
            "enclosure %r vents with a time constant of %.4g s against a limit of "
            "%.4g s; open the vent path to at least %.4g m2"
            % (name, actual, limit, needed)
        )
    if not enclosure.get("filtered", False):
        findings.append(
            "enclosure %r vents unfiltered; the vent path carries whatever the "
            "volume has collected straight out" % name
        )
    if not enclosure.get("directed_away", False):
        findings.append(
            "enclosure %r vents toward a sensitive surface; redirect the plume" % name
        )
    return {
        "name": name,
        "time_constant_s": actual,
        "max_time_constant_s": limit,
        "required_vent_area_m2": needed,
        "fast_enough": fast_enough,
        "compliant": not findings,
        "findings": findings,
    }


def find_undrained_features(features):
    """Return the names of trapped-volume features carrying no drain path."""
    if not isinstance(features, (list, tuple)):
        raise ValueError("features must be a sequence")
    undrained = []
    seen = set()
    for i, feature in enumerate(features):
        if not isinstance(feature, dict):
            raise ValueError("features[%d] must be a mapping" % i)
        for key in ("name", "traps_fluid", "drained"):
            if key not in feature:
                raise ValueError("features[%d] missing required key %r" % (i, key))
        name = feature["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("features[%d] name must be a non-empty string" % i)
        if name in seen:
            raise ValueError("feature %r appears twice" % name)
        seen.add(name)
        for key in ("traps_fluid", "drained"):
            if not isinstance(feature[key], bool):
                raise ValueError("features[%d][%r] must be a boolean" % (i, key))
        if feature["traps_fluid"] and not feature["drained"]:
            undrained.append(name)
    return undrained


def assess_drainage(features):
    """Grade the drainage provision over a feature list."""
    undrained = find_undrained_features(features)
    findings = [
        "feature %r traps cleaning fluid with no drain path" % name
        for name in undrained
    ]
    return {
        "features": len(features),
        "undrained": undrained,
        "compliant": not undrained,
        "findings": findings,
    }


def cleanable_fraction(accessible_area_m2, total_area_m2):
    """Return the share of surface area a cleaning operation can reach."""
    accessible = validate_positive(
        accessible_area_m2, "accessible_area_m2", allow_zero=True
    )
    total = validate_positive(total_area_m2, "total_area_m2")
    if accessible > total and not math.isclose(
        accessible, total, rel_tol=CRITERION_TOLERANCE, abs_tol=0.0
    ):
        raise ValueError(
            "accessible area %g m2 exceeds the total area %g m2" % (accessible, total)
        )
    return min(accessible, total) / total


def assess_accessibility(accessible_area_m2, total_area_m2, required_fraction):
    """Grade the accessible-surface provision against a required fraction."""
    achieved = cleanable_fraction(accessible_area_m2, total_area_m2)
    required = validate_fraction(required_fraction, "required_fraction")
    ok = _at_least(achieved, required)
    findings = []
    if not ok:
        findings.append(
            "only %.1f%% of the surface can be reached for cleaning against a "
            "required %.1f%%" % (100.0 * achieved, 100.0 * required)
        )
    return {
        "cleanable_fraction": achieved,
        "required_fraction": required,
        "compliant": ok,
        "findings": findings,
    }


def assess_material_choice(materials):
    """Grade the material-choice provision over the exposed-surface materials.

    Each material: name, usage, exposed (bool), screened (bool), optional
    low_outgassing (bool) and substitute (a screened alternative already known).
    """
    if not isinstance(materials, (list, tuple)) or not materials:
        raise ValueError("materials must be a non-empty sequence")
    findings = []
    seen = set()
    exposed = 0
    compliant_exposed = 0
    for i, material in enumerate(materials):
        if not isinstance(material, dict):
            raise ValueError("materials[%d] must be a mapping" % i)
        for key in ("name", "usage", "exposed", "screened"):
            if key not in material:
                raise ValueError("materials[%d] missing required key %r" % (i, key))
        name = material["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("materials[%d] name must be a non-empty string" % i)
        if name in seen:
            raise ValueError("material %r appears twice" % name)
        seen.add(name)
        for key in ("exposed", "screened"):
            if not isinstance(material[key], bool):
                raise ValueError("materials[%d][%r] must be a boolean" % (i, key))
        if not material["exposed"]:
            continue
        exposed += 1
        item_ok = True
        if not material["screened"]:
            item_ok = False
            findings.append(
                "material %r (%s) sits on an exposed surface with no screening "
                "behind it" % (name, material["usage"])
            )
        elif material.get("low_outgassing") is False:
            item_ok = False
            note = (
                "; a screened alternative %r is already known"
                % material["substitute"]
                if material.get("substitute")
                else ""
            )
            findings.append(
                "material %r (%s) is screened but does not meet the low-outgassing "
                "criterion for an exposed surface%s" % (name, material["usage"], note)
            )
        if item_ok:
            compliant_exposed += 1
    if exposed == 0:
        raise ValueError("no material is marked as exposed; nothing to grade")
    return {
        "exposed": exposed,
        "compliant_exposed": compliant_exposed,
        "compliant_share": compliant_exposed / exposed,
        "compliant": not findings,
        "findings": findings,
    }


def assess_design_for_cleanliness(spec):
    """Grade a design against every cleanliness provision it owes.

    spec keys: enclosures (sequence for assess_venting), features (sequence for
    assess_drainage), materials (sequence for assess_material_choice),
    accessible_area_m2, total_area_m2, required_accessible_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("enclosures", "features", "materials", "accessible_area_m2",
                "total_area_m2", "required_accessible_fraction"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    enclosures = spec["enclosures"]
    if not isinstance(enclosures, (list, tuple)) or not enclosures:
        raise ValueError("spec['enclosures'] must be a non-empty sequence")
    vent_records = [assess_venting(enclosure) for enclosure in enclosures]
    names = [record["name"] for record in vent_records]
    if len(set(names)) != len(names):
        raise ValueError("two enclosures share a name")
    venting = {
        "records": vent_records,
        "compliant": all(record["compliant"] for record in vent_records),
        "findings": [f for record in vent_records for f in record["findings"]],
    }
    drainage = assess_drainage(spec["features"])
    materials = assess_material_choice(spec["materials"])
    accessibility = assess_accessibility(
        spec["accessible_area_m2"],
        spec["total_area_m2"],
        spec["required_accessible_fraction"],
    )
    provisions = {
        "venting": venting,
        "drainage": drainage,
        "material-choice": materials,
        "accessibility": accessibility,
    }
    met = [name for name in PROVISIONS if provisions[name]["compliant"]]
    findings = [f for name in PROVISIONS for f in provisions[name]["findings"]]
    return {
        "provisions": provisions,
        "provisions_met": met,
        "provisions_outstanding": [name for name in PROVISIONS if name not in met],
        "compliant": len(met) == len(PROVISIONS),
        "findings": findings,
    }
