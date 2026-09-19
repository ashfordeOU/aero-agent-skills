"""Qualification-path decision for two-phase heat transport equipment.

Anchor: ECSS-E-ST-31-02C clauses 5.3 and 5.4 (qualification process, and the
decision flow of its figure 5-1 that routes an item to a full programme, a
delta programme, or to qualification carried by heritage alone). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the heritage record: a predecessor that is actually qualified, with
   complete evidence and a stated qualification envelope.
2. Compare the operating envelope the new application demands against the
   envelope the predecessor was qualified over, parameter by parameter.
3. Categorize each declared design modification, separating the fundamental
   ones -- those that change the physics of the two-phase loop -- from the ones
   that only move a dimension or a process detail.
4. Accumulate the modification extent index from the per-category weights and
   union the delta test scope the non-fundamental modifications owe.
5. Route the item: full qualification when heritage is absent or incomplete,
   when a fundamental modification is present, when the new envelope leaves the
   qualified one, or when the extent index reaches the full-programme
   threshold; a delta programme over the derived scope otherwise; and no new
   qualification when nothing changed and the envelope still covers it.
"""

import math

__all__ = [
    "ENVELOPE_TOLERANCE",
    "FULL_PROGRAMME_INDEX",
    "MODIFICATION_CATEGORIES",
    "QUALIFICATION_PATHS",
    "validate_heritage",
    "validate_envelope",
    "envelope_exceedances",
    "categorize_modification",
    "modification_extent_index",
    "delta_test_scope",
    "fundamental_modifications",
    "determine_qualification_path",
    "assess_qualification_process",
]

# Envelope limits are engineering figures that the application frequently sits
# exactly on. A request equal to a qualified bound is inside it; only the
# representation error of the comparison is absorbed here.
ENVELOPE_TOLERANCE = 1e-9

# Weighted extent at or above which a delta programme is no longer credible and
# the item goes back through a full one.
FULL_PROGRAMME_INDEX = 12

QUALIFICATION_PATHS = ("none", "delta", "full")

# Each category carries the weight it adds to the modification extent index,
# whether it is fundamental (reopens the whole programme on its own), and the
# qualification test items a delta programme must repeat because of it.
MODIFICATION_CATEGORIES = {
    "working-fluid": {
        "weight": 10,
        "fundamental": True,
        "scope": ("transport-capability", "life-test", "fluid-compatibility"),
    },
    "envelope-material": {
        "weight": 10,
        "fundamental": True,
        "scope": ("proof-pressure", "burst-pressure", "life-test"),
    },
    "wick-type": {
        "weight": 9,
        "fundamental": True,
        "scope": ("transport-capability", "tilt-sensitivity", "start-up"),
    },
    "closure-weld-process": {
        "weight": 8,
        "fundamental": True,
        "scope": ("leak-rate", "proof-pressure", "process-audit"),
    },
    "wick-porosity": {
        "weight": 6,
        "fundamental": False,
        "scope": ("transport-capability", "life-test"),
    },
    "groove-geometry": {
        "weight": 6,
        "fundamental": False,
        "scope": ("transport-capability", "thermal-cycling"),
    },
    "envelope-diameter": {
        "weight": 5,
        "fundamental": False,
        "scope": ("transport-capability", "proof-pressure", "mechanical-loads"),
    },
    "fluid-charge-mass": {
        "weight": 5,
        "fundamental": False,
        "scope": ("transport-capability", "non-condensable-gas"),
    },
    "reservoir-volume": {
        "weight": 5,
        "fundamental": False,
        "scope": ("regulation-band", "off-mode-heat-leak"),
    },
    "length-increase": {
        "weight": 4,
        "fundamental": False,
        "scope": ("transport-capability", "tilt-sensitivity"),
    },
    "bend-configuration": {
        "weight": 4,
        "fundamental": False,
        "scope": ("transport-capability", "bend-degradation"),
    },
    "manufacturing-site": {
        "weight": 3,
        "fundamental": False,
        "scope": ("process-audit", "acceptance-test"),
    },
    "interface-saddle": {
        "weight": 2,
        "fundamental": False,
        "scope": ("mechanical-loads", "thermal-interface"),
    },
    "external-surface-finish": {
        "weight": 2,
        "fundamental": False,
        "scope": ("cleanliness", "life-test"),
    },
}


def _real(value, label):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_envelope(envelope, name="envelope"):
    """Return a validated {parameter: (low, high)} operating envelope."""
    if not isinstance(envelope, dict) or not envelope:
        raise ValueError("%s must be a non-empty mapping of parameter to range" % name)
    out = {}
    for key, span in envelope.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("%s has a non-string parameter name %r" % (name, key))
        if not isinstance(span, (list, tuple)) or len(span) != 2:
            raise ValueError("%s['%s'] must be a (low, high) pair" % (name, key))
        low = _real(span[0], "%s['%s'] low" % (name, key))
        high = _real(span[1], "%s['%s'] high" % (name, key))
        if low > high:
            raise ValueError(
                "%s['%s'] is inverted: low %g exceeds high %g" % (name, key, low, high)
            )
        out[key] = (low, high)
    return out


def validate_heritage(record):
    """Return a validated heritage record for the predecessor item."""
    if not isinstance(record, dict):
        raise ValueError("heritage record must be a mapping")
    for key in ("qualified", "evidence_complete", "envelope"):
        if key not in record:
            raise ValueError("heritage record missing required key '%s'" % key)
    for key in ("qualified", "evidence_complete"):
        if not isinstance(record[key], bool):
            raise ValueError("heritage['%s'] must be a boolean" % key)
    envelope = validate_envelope(record["envelope"], name="heritage envelope")
    return {
        "qualified": record["qualified"],
        "evidence_complete": record["evidence_complete"],
        "envelope": envelope,
    }


def envelope_exceedances(qualified_envelope, application_envelope):
    """Return the parameters where the application leaves the qualified span.

    A parameter the qualified envelope never covered is an exceedance in its
    own right: silence in the heritage record is not coverage.
    """
    qualified = validate_envelope(qualified_envelope, name="qualified envelope")
    application = validate_envelope(application_envelope, name="application envelope")
    findings = []
    for key in sorted(application):
        low, high = application[key]
        if key not in qualified:
            findings.append(
                {
                    "parameter": key,
                    "reason": "not covered by the heritage qualification envelope",
                    "requested": (low, high),
                    "qualified": None,
                }
            )
            continue
        q_low, q_high = qualified[key]
        below = low < q_low and not math.isclose(
            low, q_low, rel_tol=0.0, abs_tol=ENVELOPE_TOLERANCE
        )
        above = high > q_high and not math.isclose(
            high, q_high, rel_tol=0.0, abs_tol=ENVELOPE_TOLERANCE
        )
        if below or above:
            findings.append(
                {
                    "parameter": key,
                    "reason": "requested range leaves the qualified range",
                    "requested": (low, high),
                    "qualified": (q_low, q_high),
                }
            )
    return findings


def categorize_modification(category):
    """Return the weight, fundamental flag and delta scope of a modification."""
    if not isinstance(category, str) or not category.strip():
        raise ValueError("modification category must be a non-empty string")
    key = category.strip().lower()
    if key not in MODIFICATION_CATEGORIES:
        raise ValueError(
            "unknown modification category '%s'; known categories: %s"
            % (category, ", ".join(sorted(MODIFICATION_CATEGORIES)))
        )
    entry = MODIFICATION_CATEGORIES[key]
    return {
        "category": key,
        "weight": entry["weight"],
        "fundamental": entry["fundamental"],
        "scope": tuple(entry["scope"]),
    }


def _categorize_all(modifications):
    if modifications is None:
        return []
    if not isinstance(modifications, (list, tuple)):
        raise ValueError("modifications must be a sequence of category names")
    return [categorize_modification(item) for item in modifications]


def fundamental_modifications(modifications):
    """Return the sorted categories that reopen the whole programme."""
    return sorted({m["category"] for m in _categorize_all(modifications) if m["fundamental"]})


def modification_extent_index(modifications):
    """Return the weighted extent index; a repeated category counts once."""
    seen = {}
    for entry in _categorize_all(modifications):
        seen[entry["category"]] = entry["weight"]
    return sum(seen.values())


def delta_test_scope(modifications):
    """Return the sorted union of test items the modifications reopen."""
    scope = set()
    for entry in _categorize_all(modifications):
        scope.update(entry["scope"])
    return sorted(scope)


def determine_qualification_path(heritage, application_envelope, modifications=None):
    """Return the qualification path and the reasons that produced it."""
    record = validate_heritage(heritage)
    entries = _categorize_all(modifications)
    reasons = []
    if not record["qualified"]:
        reasons.append("no qualified predecessor item")
    elif not record["evidence_complete"]:
        reasons.append("heritage qualification evidence is incomplete")
    exceedances = envelope_exceedances(record["envelope"], application_envelope)
    for finding in exceedances:
        reasons.append("envelope parameter '%s': %s" % (finding["parameter"], finding["reason"]))
    fundamentals = sorted({e["category"] for e in entries if e["fundamental"]})
    for name in fundamentals:
        reasons.append("fundamental modification '%s'" % name)
    index = modification_extent_index(modifications)
    if index >= FULL_PROGRAMME_INDEX and not fundamentals:
        reasons.append(
            "modification extent index %d reaches the full-programme threshold %d"
            % (index, FULL_PROGRAMME_INDEX)
        )
    if reasons:
        path = "full"
    elif entries:
        path = "delta"
    else:
        path = "none"
    return {
        "path": path,
        "reasons": reasons,
        "extent_index": index,
        "fundamental_modifications": fundamentals,
        "envelope_exceedances": exceedances,
    }


def assess_qualification_process(spec):
    """Run the full clause 5.3/5.4 qualification-path assessment.

    spec keys: heritage (mapping), application_envelope (mapping), optional
    modifications (sequence of category names).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("heritage", "application_envelope"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    modifications = spec.get("modifications")
    decision = determine_qualification_path(
        spec["heritage"], spec["application_envelope"], modifications
    )
    if decision["path"] == "delta":
        scope = delta_test_scope(modifications)
    elif decision["path"] == "full":
        scope = sorted(
            set(delta_test_scope(modifications))
            | {
                "transport-capability",
                "proof-pressure",
                "burst-pressure",
                "leak-rate",
                "life-test",
                "mechanical-loads",
                "thermal-cycling",
            }
        )
    else:
        scope = []
    return {
        "path": decision["path"],
        "reasons": decision["reasons"],
        "extent_index": decision["extent_index"],
        "fundamental_modifications": decision["fundamental_modifications"],
        "envelope_exceedances": decision["envelope_exceedances"],
        "test_scope": scope,
        "heritage_usable": decision["path"] != "full",
    }
