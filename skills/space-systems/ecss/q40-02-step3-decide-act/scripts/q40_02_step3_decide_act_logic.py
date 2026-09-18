"""Step 3 of the hazard-analysis process: decide and act.

Anchor: ECSS-Q-ST-40-02C clause 5.2.3 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Hold every proposed measure to the hazard-reduction precedence.
   Eliminating or minimizing the hazard by design comes first, then a
   safety device, then a warning device, then a procedure or training.
   A lower order is admissible only when every order above it carries
   a written justification for being unavailable.
2. Demand verification evidence per measure. A measure with no
   verification is a proposal, and crediting it in the residual risk
   turns a proposal into an assumption.
3. Credit only the verified measures. Each carries a reduction
   effectiveness, which is what it removes from the occurrence
   probability of the hazard; the survivors compound.
4. Recompute the residual likelihood band from the reduced probability
   and the residual severity from any measure that lowers consequence,
   then read the residual risk index.
5. Report whether the residual index has reached the project's
   acceptance floor -- index 1 is the worst cell and 16 the mildest, so
   an index under the floor is the direction that needs a waiver -- and
   every finding that produced it.

Stdlib only, offline, deterministic.
"""

# Hazard-reduction precedence, strongest first. The ordinal is the rank.
REDUCTION_PRECEDENCE = (
    "eliminate-or-minimize-by-design",
    "safety-device",
    "warning-device",
    "procedure-or-training",
)
PRECEDENCE_ORDINAL = {name: i for i, name in enumerate(REDUCTION_PRECEDENCE)}

SEVERITY_CATEGORIES = ("catastrophic", "critical", "major", "minor")
SEVERITY_ORDINAL = {name: i for i, name in enumerate(SEVERITY_CATEGORIES)}

LIKELIHOOD_BANDS = ("probable", "occasional", "remote", "improbable")
LIKELIHOOD_ORDINAL = {name: i for i, name in enumerate(LIKELIHOOD_BANDS)}

LIKELIHOOD_LOWER_BOUND = (
    ("probable", 1.0e-2),
    ("occasional", 1.0e-3),
    ("remote", 1.0e-5),
    ("improbable", 0.0),
)

# The residual probability is a product of floats, so a value meant to
# land exactly on a band boundary can sit a few units in the last place
# under it. The tolerance absorbs that without moving the boundary.
PROBABILITY_TOLERANCE = 1.0e-12

RISK_INDEX_MATRIX = (
    (1, 2, 4, 8),
    (3, 5, 7, 11),
    (6, 9, 12, 14),
    (10, 13, 15, 16),
)

# Index 1 is the worst cell and 16 the mildest, so a residual index
# BELOW this floor is the unacceptable direction. Anything under it needs
# an explicit waiver, which is outside step 3.
DEFAULT_ACCEPTANCE_FLOOR_INDEX = 10


def _string(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _fraction(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    val = float(value)
    if val < 0.0 or val > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return val


def likelihood_band(probability):
    """Place an occurrence probability in a likelihood band."""
    value = _fraction("probability", probability)
    for name, bound in LIKELIHOOD_LOWER_BOUND:
        if value >= bound - PROBABILITY_TOLERANCE:
            return name
    return LIKELIHOOD_BANDS[-1]


def risk_index(severity, likelihood):
    """Project risk index for a severity and likelihood pair."""
    if severity not in SEVERITY_ORDINAL:
        raise ValueError("unknown severity %r" % (severity,))
    if likelihood not in LIKELIHOOD_ORDINAL:
        raise ValueError("unknown likelihood %r" % (likelihood,))
    return RISK_INDEX_MATRIX[SEVERITY_ORDINAL[severity]][LIKELIHOOD_ORDINAL[likelihood]]


def validate_measure(measure):
    """Validate one risk-reduction measure and return a normalized copy."""
    if not isinstance(measure, dict):
        raise ValueError("measure must be a mapping")
    measure_id = _string("measure id", measure.get("id"))
    order = measure.get("precedence")
    if order not in PRECEDENCE_ORDINAL:
        raise ValueError(
            "measure %s has unknown precedence %r (expected one of %s)"
            % (measure_id, order, ", ".join(REDUCTION_PRECEDENCE))
        )
    justified = measure.get("higher_orders_justified_unavailable", [])
    if not isinstance(justified, (list, tuple)):
        raise ValueError(
            "measure %s higher_orders_justified_unavailable must be a sequence"
            % measure_id
        )
    for item in justified:
        if item not in PRECEDENCE_ORDINAL:
            raise ValueError(
                "measure %s justifies unknown order %r" % (measure_id, item)
            )
    severity_step = measure.get("severity_steps_reduced", 0)
    if isinstance(severity_step, bool) or not isinstance(severity_step, int):
        raise ValueError(
            "measure %s severity_steps_reduced must be an int" % measure_id
        )
    if severity_step < 0:
        raise ValueError(
            "measure %s severity_steps_reduced must not be negative" % measure_id
        )
    return {
        "id": measure_id,
        "precedence": order,
        "higher_orders_justified_unavailable": [str(i) for i in justified],
        "verified": _boolean(
            "measure %s verified" % measure_id, measure.get("verified", False)
        ),
        "reduction_effectiveness": _fraction(
            "measure %s reduction_effectiveness" % measure_id,
            measure.get("reduction_effectiveness", 0.0),
        ),
        "severity_steps_reduced": severity_step,
    }


def precedence_findings(measure):
    """Findings about a measure that skipped a stronger reduction order."""
    norm = validate_measure(measure)
    rank = PRECEDENCE_ORDINAL[norm["precedence"]]
    justified = set(norm["higher_orders_justified_unavailable"])
    findings = []
    for order in REDUCTION_PRECEDENCE[:rank]:
        if order not in justified:
            findings.append("higher-order-not-justified:%s" % order)
    return findings


def effectiveness_findings(measure):
    """Findings about a measure credited without verification evidence."""
    norm = validate_measure(measure)
    findings = []
    if not norm["verified"]:
        findings.append("measure-effectiveness-not-verified")
    elif norm["reduction_effectiveness"] <= 0.0:
        findings.append("verified-measure-reduces-nothing")
    return findings


def credited_measures(measures):
    """The measures that may be credited in the residual risk."""
    if not isinstance(measures, list):
        raise ValueError("measures must be a list")
    out = []
    seen = set()
    for measure in measures:
        norm = validate_measure(measure)
        if norm["id"] in seen:
            raise ValueError("duplicate measure id %r" % (norm["id"],))
        seen.add(norm["id"])
        if norm["verified"] and norm["reduction_effectiveness"] > 0.0:
            out.append(norm)
    return out


def residual_probability(base_probability, measures):
    """Occurrence probability once the credited measures compound."""
    value = _fraction("base_probability", base_probability)
    for norm in credited_measures(measures):
        value = value * (1.0 - norm["reduction_effectiveness"])
    return value


def residual_severity(base_severity, measures):
    """Severity once the credited measures lower the consequence."""
    if base_severity not in SEVERITY_ORDINAL:
        raise ValueError("unknown severity %r" % (base_severity,))
    ordinal = SEVERITY_ORDINAL[base_severity]
    for norm in credited_measures(measures):
        ordinal += norm["severity_steps_reduced"]
    if ordinal > len(SEVERITY_CATEGORIES) - 1:
        ordinal = len(SEVERITY_CATEGORIES) - 1
    return SEVERITY_CATEGORIES[ordinal]


def assess_step3_decide_act(hazard, measures, floor_index=None):
    """Assess the decide-and-act step for one hazard and its measures."""
    if not isinstance(hazard, dict):
        raise ValueError("hazard must be a mapping")
    hazard_id = _string("hazard id", hazard.get("id"))
    base_severity = hazard.get("severity")
    if base_severity not in SEVERITY_ORDINAL:
        raise ValueError("hazard %s has unknown severity %r" % (hazard_id, base_severity))
    base_probability = _fraction(
        "hazard %s base_probability" % hazard_id, hazard.get("base_probability")
    )
    if not isinstance(measures, list) or not measures:
        raise ValueError("measures must be a non-empty list")
    floor = DEFAULT_ACCEPTANCE_FLOOR_INDEX if floor_index is None else floor_index
    if isinstance(floor, bool) or not isinstance(floor, int):
        raise ValueError("floor_index must be an int, got %r" % (floor_index,))
    if floor < 1 or floor > 16:
        raise ValueError("floor_index must lie in 1..16, got %r" % (floor,))

    findings = []
    measure_results = []
    for measure in measures:
        norm = validate_measure(measure)
        local = precedence_findings(norm) + effectiveness_findings(norm)
        measure_results.append(
            {
                "id": norm["id"],
                "precedence": norm["precedence"],
                "credited": norm["verified"] and norm["reduction_effectiveness"] > 0.0,
                "findings": local,
            }
        )
        for finding in local:
            findings.append("%s:%s" % (finding, norm["id"]))

    probability = residual_probability(base_probability, measures)
    severity = residual_severity(base_severity, measures)
    band = likelihood_band(probability)
    index = risk_index(severity, band)
    initial_index = risk_index(base_severity, likelihood_band(base_probability))
    if index < floor:
        findings.append("residual-risk-index-below-acceptance-floor")
    return {
        "hazard": hazard_id,
        "initial_risk_index": initial_index,
        "residual_severity": severity,
        "residual_probability": probability,
        "residual_likelihood": band,
        "residual_risk_index": index,
        "acceptance_floor_index": floor,
        "measures": measure_results,
        "findings": findings,
        "acceptable": not findings,
    }
