"""Storage-condition envelope for limited-shelf-life materials.

Anchor: ECSS-Q-ST-70-22 storage clause -- the storage conditions (temperature,
relative humidity, light) a limited-shelf-life material has to be held at, and
whether a candidate store actually delivers them. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the material record: family, and whatever the manufacturer declared
   for temperature band, relative-humidity ceiling, light sensitivity and the
   need for sub-zero storage.
2. Derive the required envelope as the INTERSECTION of the house family default
   and the declared limits. The tighter side governs on every axis; an empty
   intersection is a contradiction to be refused, not a band to be widened.
3. Widen the candidate store's controlled band by its own control tolerance
   before comparing: a store set to the band edges reaches outside them by the
   tolerance, and it is that reachable extreme the material sees.
4. Raise one finding per breached axis, each carrying whether an added control
   can close it (opaque overwrap for light, desiccation for a small humidity
   overshoot) or not (temperature band, sub-zero capability).
5. Close with one suitable / suitable-with-added-controls / not-suitable
   disposition per material and for the store as a whole.
"""

import math

__all__ = [
    "TEMPERATURE_TOLERANCE_C",
    "HUMIDITY_TOLERANCE_PCT",
    "DESICCATION_LIMIT_PCT",
    "FAMILY_DEFAULTS",
    "family_default",
    "validate_material",
    "validate_store",
    "derive_envelope",
    "reachable_extremes",
    "envelope_findings",
    "disposition_for",
    "assess_material",
    "assess_storage_conditions",
]

# Band comparisons are differences of declared decimal numbers; an exact
# equality at a band edge can land a few ULPs on the wrong side. Absorb the
# representation error here rather than by relaxing the engineering limit.
TEMPERATURE_TOLERANCE_C = 1e-9
HUMIDITY_TOLERANCE_PCT = 1e-9

# A humidity overshoot wider than this cannot be argued away with a desiccated
# overbag; it needs a different store.
DESICCATION_LIMIT_PCT = 10.0

# House defaults per material family. These are the conservative fallback the
# declared manufacturer limits are intersected with -- never replaced by.
FAMILY_DEFAULTS = {
    "elastomer": {
        "temp_min_c": -20.0, "temp_max_c": 27.0, "rh_max_pct": 65.0,
        "light_protection": True, "sub_zero": False,
    },
    "adhesive-paste": {
        "temp_min_c": 2.0, "temp_max_c": 25.0, "rh_max_pct": 60.0,
        "light_protection": False, "sub_zero": False,
    },
    "film-adhesive": {
        "temp_min_c": -40.0, "temp_max_c": -18.0, "rh_max_pct": 60.0,
        "light_protection": False, "sub_zero": True,
    },
    "prepreg": {
        "temp_min_c": -40.0, "temp_max_c": -18.0, "rh_max_pct": 55.0,
        "light_protection": False, "sub_zero": True,
    },
    "sealant": {
        "temp_min_c": 2.0, "temp_max_c": 27.0, "rh_max_pct": 65.0,
        "light_protection": False, "sub_zero": False,
    },
    "coating": {
        "temp_min_c": 5.0, "temp_max_c": 30.0, "rh_max_pct": 70.0,
        "light_protection": True, "sub_zero": False,
    },
    "solvent": {
        "temp_min_c": 5.0, "temp_max_c": 25.0, "rh_max_pct": 75.0,
        "light_protection": True, "sub_zero": False,
    },
}


def _real(value, label):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _flag(value, label):
    """Return value as a bool or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def family_default(family):
    """Return a copy of the house default envelope for a material family."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string")
    key = family.strip().lower()
    if key not in FAMILY_DEFAULTS:
        raise ValueError(
            "unknown material family %r; known families: %s"
            % (family, ", ".join(sorted(FAMILY_DEFAULTS)))
        )
    return dict(FAMILY_DEFAULTS[key])


def validate_material(record):
    """Return a normalised material record."""
    if not isinstance(record, dict):
        raise ValueError("material record must be a mapping")
    ident = record.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("material record needs a non-empty 'id'")
    family = record.get("family")
    default = family_default(family)
    norm = {"id": ident.strip(), "family": family.strip().lower()}

    t_min = record.get("declared_temp_min_c")
    t_max = record.get("declared_temp_max_c")
    norm["declared_temp_min_c"] = None if t_min is None else _real(t_min, "declared_temp_min_c")
    norm["declared_temp_max_c"] = None if t_max is None else _real(t_max, "declared_temp_max_c")
    if norm["declared_temp_min_c"] is not None and norm["declared_temp_max_c"] is not None:
        if norm["declared_temp_min_c"] > norm["declared_temp_max_c"]:
            raise ValueError(
                "declared temperature band of %s is inverted (%g > %g)"
                % (norm["id"], norm["declared_temp_min_c"], norm["declared_temp_max_c"])
            )

    rh = record.get("declared_rh_max_pct")
    if rh is None:
        norm["declared_rh_max_pct"] = None
    else:
        rh = _real(rh, "declared_rh_max_pct")
        if rh <= 0.0 or rh > 100.0:
            raise ValueError("declared_rh_max_pct must lie in (0, 100], got %g" % rh)
        norm["declared_rh_max_pct"] = rh

    norm["light_sensitive"] = _flag(record.get("light_sensitive", default["light_protection"]),
                                   "light_sensitive")
    norm["sub_zero_required"] = _flag(record.get("sub_zero_required", default["sub_zero"]),
                                      "sub_zero_required")
    return norm


def validate_store(record):
    """Return a normalised store record."""
    if not isinstance(record, dict):
        raise ValueError("store record must be a mapping")
    ident = record.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("store record needs a non-empty 'id'")
    t_min = _real(record.get("set_temp_min_c"), "set_temp_min_c")
    t_max = _real(record.get("set_temp_max_c"), "set_temp_max_c")
    if t_min > t_max:
        raise ValueError("store %s temperature band is inverted (%g > %g)" % (ident, t_min, t_max))
    t_tol = _real(record.get("temp_control_tolerance_c", 0.0), "temp_control_tolerance_c")
    if t_tol < 0.0:
        raise ValueError("temp_control_tolerance_c must be non-negative, got %g" % t_tol)
    rh_max = _real(record.get("set_rh_max_pct"), "set_rh_max_pct")
    if rh_max <= 0.0 or rh_max > 100.0:
        raise ValueError("set_rh_max_pct must lie in (0, 100], got %g" % rh_max)
    rh_tol = _real(record.get("rh_control_tolerance_pct", 0.0), "rh_control_tolerance_pct")
    if rh_tol < 0.0:
        raise ValueError("rh_control_tolerance_pct must be non-negative, got %g" % rh_tol)
    return {
        "id": ident.strip(),
        "set_temp_min_c": t_min,
        "set_temp_max_c": t_max,
        "temp_control_tolerance_c": t_tol,
        "set_rh_max_pct": rh_max,
        "rh_control_tolerance_pct": rh_tol,
        "light_excluded": _flag(record.get("light_excluded", False), "light_excluded"),
        "desiccation_available": _flag(record.get("desiccation_available", False),
                                       "desiccation_available"),
        "sub_zero_capable": _flag(record.get("sub_zero_capable", False), "sub_zero_capable"),
    }


def derive_envelope(material):
    """Return the required storage envelope: family default intersected with declared limits."""
    norm = validate_material(material)
    default = family_default(norm["family"])
    governed_by = {}

    t_min = default["temp_min_c"]
    if norm["declared_temp_min_c"] is not None and norm["declared_temp_min_c"] > t_min:
        t_min = norm["declared_temp_min_c"]
        governed_by["temp_min_c"] = "declared"
    else:
        governed_by["temp_min_c"] = "family-default"

    t_max = default["temp_max_c"]
    if norm["declared_temp_max_c"] is not None and norm["declared_temp_max_c"] < t_max:
        t_max = norm["declared_temp_max_c"]
        governed_by["temp_max_c"] = "declared"
    else:
        governed_by["temp_max_c"] = "family-default"

    if t_min > t_max + TEMPERATURE_TOLERANCE_C:
        raise ValueError(
            "material %s has no admissible temperature band: family default and declared "
            "limits intersect empty (%g > %g)" % (norm["id"], t_min, t_max)
        )

    rh_max = default["rh_max_pct"]
    if norm["declared_rh_max_pct"] is not None and norm["declared_rh_max_pct"] < rh_max:
        rh_max = norm["declared_rh_max_pct"]
        governed_by["rh_max_pct"] = "declared"
    else:
        governed_by["rh_max_pct"] = "family-default"

    return {
        "id": norm["id"],
        "family": norm["family"],
        "temp_min_c": t_min,
        "temp_max_c": t_max,
        "rh_max_pct": rh_max,
        "light_protection": bool(default["light_protection"] or norm["light_sensitive"]),
        "sub_zero": bool(default["sub_zero"] or norm["sub_zero_required"]),
        "governed_by": governed_by,
    }


def reachable_extremes(store):
    """Return the (coldest, hottest, wettest) the material actually sees in a store."""
    norm = validate_store(store)
    return {
        "coldest_c": norm["set_temp_min_c"] - norm["temp_control_tolerance_c"],
        "hottest_c": norm["set_temp_max_c"] + norm["temp_control_tolerance_c"],
        "wettest_rh_pct": norm["set_rh_max_pct"] + norm["rh_control_tolerance_pct"],
    }


def envelope_findings(envelope, store):
    """Return one finding per breached axis, each marked mitigable or not."""
    if not isinstance(envelope, dict) or "temp_min_c" not in envelope:
        raise ValueError("envelope must be a mapping produced by derive_envelope")
    norm = validate_store(store)
    reach = reachable_extremes(norm)
    findings = []

    if reach["coldest_c"] < envelope["temp_min_c"] - TEMPERATURE_TOLERANCE_C:
        findings.append({
            "axis": "temperature-low",
            "detail": "store reaches %.3f C, below the required %.3f C"
                      % (reach["coldest_c"], envelope["temp_min_c"]),
            "mitigable": False,
        })
    if reach["hottest_c"] > envelope["temp_max_c"] + TEMPERATURE_TOLERANCE_C:
        findings.append({
            "axis": "temperature-high",
            "detail": "store reaches %.3f C, above the required %.3f C"
                      % (reach["hottest_c"], envelope["temp_max_c"]),
            "mitigable": False,
        })
    if reach["wettest_rh_pct"] > envelope["rh_max_pct"] + HUMIDITY_TOLERANCE_PCT:
        overshoot = reach["wettest_rh_pct"] - envelope["rh_max_pct"]
        findings.append({
            "axis": "humidity",
            "detail": "store reaches %.3f %%RH, above the required %.3f %%RH"
                      % (reach["wettest_rh_pct"], envelope["rh_max_pct"]),
            "overshoot_pct": overshoot,
            "mitigable": bool(norm["desiccation_available"]
                              and overshoot <= DESICCATION_LIMIT_PCT + HUMIDITY_TOLERANCE_PCT),
        })
    if envelope["light_protection"] and not norm["light_excluded"]:
        findings.append({
            "axis": "light",
            "detail": "material needs light protection; store does not exclude light",
            "mitigable": True,
        })
    if envelope["sub_zero"] and not norm["sub_zero_capable"]:
        findings.append({
            "axis": "sub-zero",
            "detail": "material needs sub-zero storage; store is not sub-zero capable",
            "mitigable": False,
        })
    return findings


def disposition_for(findings):
    """Return suitable / suitable-with-added-controls / not-suitable for a finding list."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    if not findings:
        return "suitable"
    for finding in findings:
        if not isinstance(finding, dict) or "mitigable" not in finding:
            raise ValueError("each finding must be a mapping carrying 'mitigable'")
        if not finding["mitigable"]:
            return "not-suitable"
    return "suitable-with-added-controls"


def assess_material(material, store):
    """Derive one material's envelope and grade a store against it."""
    envelope = derive_envelope(material)
    findings = envelope_findings(envelope, store)
    return {
        "id": envelope["id"],
        "envelope": envelope,
        "findings": findings,
        "added_controls": sorted(f["axis"] for f in findings if f["mitigable"]),
        "disposition": disposition_for(findings),
    }


def assess_storage_conditions(materials, store):
    """Grade a store against every material it is asked to hold."""
    if not isinstance(materials, (list, tuple)) or not materials:
        raise ValueError("materials must be a non-empty sequence of material records")
    norm_store = validate_store(store)
    seen = set()
    results = []
    for material in materials:
        result = assess_material(material, norm_store)
        if result["id"] in seen:
            raise ValueError("duplicate material id %r in the list" % result["id"])
        seen.add(result["id"])
        results.append(result)
    blocked = [r["id"] for r in results if r["disposition"] == "not-suitable"]
    conditioned = [r["id"] for r in results if r["disposition"] == "suitable-with-added-controls"]
    if blocked:
        overall = "not-suitable"
    elif conditioned:
        overall = "suitable-with-added-controls"
    else:
        overall = "suitable"
    return {
        "store_id": norm_store["id"],
        "materials": results,
        "not_suitable_ids": blocked,
        "conditioned_ids": conditioned,
        "overall_disposition": overall,
    }
