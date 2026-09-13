"""Route selection for demonstrating multipactor performance.

Anchor: ECSS-E-ST-20-01C clause 4.5 (the permitted routes -- by analysis, by
test, by both, or by similarity -- for proving the multipactor performance of
radio-frequency hardware).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Four routes are permitted. ``similarity`` re-uses an already-qualified unit
  when the candidate is the same design, the same surfaces and the same
  process, run no harder. ``analysis-only`` stands alone when a validated
  method covers the geometry and the computed margin clears the requirement
  with room to spare. ``analysis-and-test`` is the usual route: the analysis
  sizes the gaps, the campaign demonstrates them. ``test-only`` is what is
  left when no validated method covers the geometry, or when the analysis
  does not reach the required margin.
* Criticality is a one-way ratchet: a critical unit never rides on analysis
  alone, however comfortable the margin looks.
* A campaign that has to be run is priced in watts:
  ``P_test = P_nominal * 10 ** (margin_db / 10)``. If the facility cannot
  reach that level, the shortfall is a finding with its own corrective route,
  not a reason to quietly lower the demonstrated margin.
* Breakdown during a campaign is only credible if it can be seen. At least
  two independent detection methods are required, and they cannot both be
  global: one has to observe the discharge locally.
"""

from __future__ import annotations

import math

ROUTES = (
    "similarity",
    "analysis-only",
    "analysis-and-test",
    "test-only",
)

ANALYSIS_SUPPORT_STATES = (
    "validated-method",
    "engineering-estimate",
    "no-applicable-method",
)

# Detection methods that watch the whole device from its ports.
GLOBAL_DETECTION_METHODS = (
    "forward-reverse-power-nulling",
    "third-harmonic-detection",
    "phase-null-detection",
    "spectral-noise-rise",
)

# Detection methods that observe the discharge at the gap itself.
LOCAL_DETECTION_METHODS = (
    "electron-probe",
    "optical-emission-monitoring",
    "close-electron-detection",
)

DEFAULT_ANALYSIS_ONLY_EXTRA_DB = 3.0

DEFAULT_SIMILARITY_TOLERANCES = {
    "max_gap_delta_fraction": 0.05,
    "max_frequency_delta_fraction": 0.05,
}

# Decibel and watt comparisons sit on sums and products of floating point
# values, so a case that is exactly on the limit can land a few units in the
# last place beyond it. These tolerances absorb the representation error only;
# no engineering limit is widened.
MARGIN_TOLERANCE_DB = 1e-9
POWER_REL_TOLERANCE = 1e-9


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive_number(value, label):
    number = _finite_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _non_negative_number(value, label):
    number = _finite_number(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def test_power_w(nominal_power_w, margin_db):
    """Power a campaign has to reach to demonstrate a margin in decibels."""
    nominal = _positive_number(nominal_power_w, "nominal_power_w")
    margin = _finite_number(margin_db, "margin_db")
    return nominal * (10.0 ** (margin / 10.0))


def margin_clears(margin_db, required_margin_db, extra_db=0.0):
    """True when a margin reaches a requirement plus an extra, within tolerance."""
    margin = _finite_number(margin_db, "margin_db")
    required = _finite_number(required_margin_db, "required_margin_db")
    extra = _non_negative_number(extra_db, "extra_db")
    return margin >= required + extra - MARGIN_TOLERANCE_DB


def within_limit(value_w, limit_w):
    """True when a watt figure sits at or below a limit, ties included.

    Both figures are products of powers of ten, so a case that is physically
    exactly on the limit can land a few units in the last place above it; the
    relative tolerance absorbs that without moving the limit.
    """
    value = _positive_number(value_w, "value_w")
    limit = _positive_number(limit_w, "limit_w")
    if math.isclose(value, limit, rel_tol=POWER_REL_TOLERANCE):
        return True
    return value < limit


def facility_can_reach(required_test_power_w, facility_max_power_w):
    """True when the facility reaches the required demonstration level."""
    _positive_number(required_test_power_w, "required_test_power_w")
    _positive_number(facility_max_power_w, "facility_max_power_w")
    return within_limit(required_test_power_w, facility_max_power_w)


def check_detection_methods(methods):
    """Audit the detection set: two independent methods, one of them local."""
    if not isinstance(methods, (list, tuple)):
        raise ValueError(
            "methods must be a list or tuple, got %r" % (type(methods).__name__,)
        )
    known = set(GLOBAL_DETECTION_METHODS) | set(LOCAL_DETECTION_METHODS)
    seen = []
    for name in methods:
        if name not in known:
            raise ValueError(
                "unknown detection method %r (known: %s)"
                % (name, ", ".join(sorted(known)))
            )
        if name not in seen:
            seen.append(name)
    findings = []
    if len(seen) < 2:
        findings.append("fewer-than-two-detection-methods")
    if not any(name in LOCAL_DETECTION_METHODS for name in seen):
        findings.append("no-local-detection-method")
    if not any(name in GLOBAL_DETECTION_METHODS for name in seen):
        findings.append("no-global-detection-method")
    return {
        "methods": seen,
        "global_count": sum(1 for n in seen if n in GLOBAL_DETECTION_METHODS),
        "local_count": sum(1 for n in seen if n in LOCAL_DETECTION_METHODS),
        "findings": findings,
        "adequate": len(findings) == 0,
    }


def similarity_assessment(candidate, reference, tolerances=None):
    """Judge whether a candidate may ride on a qualified unit's evidence.

    ``candidate`` and ``reference`` carry gap_mm, frequency_ghz, power_w, the
    surface-treatment identifier and the manufacturing-process identifier; the
    reference also carries whether it is actually qualified. Every shortfall is
    named, so a rejected similarity claim says what to fix.
    """
    if not isinstance(candidate, dict) or not isinstance(reference, dict):
        raise ValueError("candidate and reference must both be mappings")
    limits = dict(DEFAULT_SIMILARITY_TOLERANCES)
    if tolerances is not None:
        if not isinstance(tolerances, dict):
            raise ValueError("tolerances must be a mapping")
        for key, value in tolerances.items():
            if key not in DEFAULT_SIMILARITY_TOLERANCES:
                raise ValueError("unknown similarity tolerance %r" % (key,))
            limits[key] = _non_negative_number(value, key)
    cand_gap = _positive_number(candidate.get("gap_mm"), "candidate.gap_mm")
    ref_gap = _positive_number(reference.get("gap_mm"), "reference.gap_mm")
    cand_freq = _positive_number(candidate.get("frequency_ghz"), "candidate.frequency_ghz")
    ref_freq = _positive_number(reference.get("frequency_ghz"), "reference.frequency_ghz")
    cand_power = _positive_number(candidate.get("power_w"), "candidate.power_w")
    ref_power = _positive_number(reference.get("power_w"), "reference.power_w")
    shortfalls = []
    if not bool(reference.get("qualified", False)):
        shortfalls.append("reference-not-qualified")
    gap_delta = abs(cand_gap - ref_gap) / ref_gap
    if gap_delta > limits["max_gap_delta_fraction"] + POWER_REL_TOLERANCE:
        shortfalls.append("gap-geometry-delta-too-large")
    freq_delta = abs(cand_freq - ref_freq) / ref_freq
    if freq_delta > limits["max_frequency_delta_fraction"] + POWER_REL_TOLERANCE:
        shortfalls.append("frequency-delta-too-large")
    if not within_limit(cand_power, ref_power):
        shortfalls.append("candidate-run-harder-than-reference")
    if candidate.get("surface_treatment") != reference.get("surface_treatment"):
        shortfalls.append("surface-treatment-differs")
    if candidate.get("manufacturing_process") != reference.get("manufacturing_process"):
        shortfalls.append("manufacturing-process-differs")
    return {
        "gap_delta_fraction": gap_delta,
        "frequency_delta_fraction": freq_delta,
        "power_ratio": cand_power / ref_power,
        "shortfalls": shortfalls,
        "eligible": len(shortfalls) == 0,
    }


def normalize_route_inputs(raw):
    """Validate the inputs the route decision is made from."""
    if not isinstance(raw, dict):
        raise ValueError("inputs must be a mapping, got %r" % (type(raw).__name__,))
    support = raw.get("analysis_support")
    if support not in ANALYSIS_SUPPORT_STATES:
        raise ValueError(
            "analysis_support must be one of %s, got %r"
            % (", ".join(ANALYSIS_SUPPORT_STATES), support)
        )
    inputs = {
        "analysis_support": support,
        "analysis_margin_db": _finite_number(
            raw.get("analysis_margin_db", 0.0), "analysis_margin_db"
        ),
        "required_margin_db": _non_negative_number(
            raw.get("required_margin_db"), "required_margin_db"
        ),
        "analysis_only_extra_db": _non_negative_number(
            raw.get("analysis_only_extra_db", DEFAULT_ANALYSIS_ONLY_EXTRA_DB),
            "analysis_only_extra_db",
        ),
        "nominal_power_w": _positive_number(raw.get("nominal_power_w"), "nominal_power_w"),
        "critical": bool(raw.get("critical", False)),
    }
    facility = raw.get("facility_max_power_w")
    if facility is not None:
        facility = _positive_number(facility, "facility_max_power_w")
    inputs["facility_max_power_w"] = facility
    methods = raw.get("detection_methods", [])
    if not isinstance(methods, (list, tuple)):
        raise ValueError("detection_methods must be a list or tuple")
    inputs["detection_methods"] = list(methods)
    similarity = raw.get("similarity")
    if similarity is not None and not isinstance(similarity, dict):
        raise ValueError("similarity must be a mapping with candidate and reference")
    inputs["similarity"] = similarity
    return inputs


def select_verification_route(raw):
    """Pick the permitted route and say why it was picked."""
    inputs = normalize_route_inputs(raw)
    similarity = None
    if inputs["similarity"] is not None:
        similarity = similarity_assessment(
            inputs["similarity"].get("candidate"),
            inputs["similarity"].get("reference"),
            inputs["similarity"].get("tolerances"),
        )
        if similarity["eligible"]:
            return {
                "route": "similarity",
                "rationale": "candidate matches a qualified unit within the similarity tolerances",
                "similarity": similarity,
                "inputs": inputs,
                "findings": [],
            }
    findings = []
    support = inputs["analysis_support"]
    margin = inputs["analysis_margin_db"]
    required = inputs["required_margin_db"]
    if support == "no-applicable-method":
        route = "test-only"
        rationale = "no validated analysis method covers this geometry"
    elif not margin_clears(margin, required):
        route = "test-only"
        rationale = "analysis does not reach the required margin; redesign or demonstrate by test"
        findings.append("analysis-below-required-margin")
    elif support == "engineering-estimate":
        route = "analysis-and-test"
        rationale = "analysis method is an engineering estimate and cannot stand alone"
    elif margin_clears(margin, required, inputs["analysis_only_extra_db"]):
        if inputs["critical"]:
            route = "analysis-and-test"
            rationale = "critical equipment never rides on analysis alone"
        else:
            route = "analysis-only"
            rationale = "validated method clears the requirement with the analysis-only extra"
    else:
        route = "analysis-and-test"
        rationale = "validated method clears the requirement but not the analysis-only extra"
    return {
        "route": route,
        "rationale": rationale,
        "similarity": similarity,
        "inputs": inputs,
        "findings": findings,
    }


def build_verification_route_plan(raw):
    """Full clause 4.5 route decision with the campaign obligations it implies.

    Returns the chosen route, the demonstration level in watts when a campaign
    is needed, the facility and detection findings, the actions to close, and
    whether the route as declared is executable as it stands.
    """
    decision = select_verification_route(raw)
    inputs = decision["inputs"]
    findings = list(decision["findings"])
    actions = []
    required_power = None
    detection = None
    route = decision["route"]
    if route == "similarity":
        actions.append("record-the-similarity-justification-dossier")
    elif route == "analysis-only":
        actions.append("record-the-analysis-method-validation-evidence")
    else:
        required_power = test_power_w(
            inputs["nominal_power_w"], inputs["required_margin_db"]
        )
        actions.append("run-the-campaign-at-the-demonstration-level")
        detection = check_detection_methods(inputs["detection_methods"])
        for finding in detection["findings"]:
            findings.append(finding)
        if not detection["adequate"]:
            actions.append("add-an-independent-detection-method")
        facility = inputs["facility_max_power_w"]
        if facility is None:
            findings.append("facility-capability-not-declared")
            actions.append("declare-the-facility-capability")
        elif not facility_can_reach(required_power, facility):
            findings.append("facility-power-shortfall")
            actions.append("use-a-dedicated-article-or-an-alternative-demonstration")
    similarity_shortfalls = []
    if decision["similarity"] is not None and route != "similarity":
        similarity_shortfalls = list(decision["similarity"]["shortfalls"])
    return {
        "route": route,
        "rationale": decision["rationale"],
        "required_test_power_w": required_power,
        "detection": detection,
        "similarity": decision["similarity"],
        "similarity_shortfalls": similarity_shortfalls,
        "findings": findings,
        "actions": actions,
        "executable": len(findings) == 0,
    }
