#!/usr/bin/env python3
"""Secondary-arc test exemption (ECSS-E-ST-20-06C, clause 7.2.3.1).

Offline, deterministic, stdlib-only implementation of the clause 7.2.3.1
allowance: a photovoltaic array whose generator voltage stays low enough
that a primary arc cannot be driven into a sustained secondary arc may omit
the secondary-arc test campaign. The module derives the worst-case
string-to-string potential from its contributing terms, derives the
sustained-arc onset voltage for the actual insulation geometry and
material, checks the voltage, current and evidence criteria, and returns an
auditable grant-or-refuse verdict with the actions a refusal implies.

The onset relation is an engineering surrogate with explicit reference
points; it is monotonic, clamped and deterministic. No standard text is
reproduced.
"""

import math

# ---------------------------------------------------------------------------
# Sustained-arc onset surrogate model
# ---------------------------------------------------------------------------

REFERENCE_CONDUCTOR_GAP_MM = 0.90
BASE_ONSET_VOLTAGE_V = 50.0
GAP_COEFFICIENT_V_PER_MM = 22.0
MINIMUM_ONSET_VOLTAGE_V = 24.0

# Relative resistance of the insulating material bridging the arc site.
MATERIAL_FACTORS = {
    "polyimide": 1.00,
    "glass-fibre-epoxy": 0.92,
    "silicone-adhesive": 0.85,
    "ceramic-coating": 1.15,
    "bare-composite": 0.78,
}

# Exemption criteria.
REQUIRED_VOLTAGE_MARGIN_FRACTION = 0.20
SUSTAINING_CURRENT_LIMIT_A = 0.50

# Evidence a grant has to rest on.
REQUIRED_EVIDENCE_ITEMS = (
    "worst-case-voltage-derivation",
    "conductor-gap-measurement",
    "insulation-material-record",
    "string-current-capability",
)

# Representation tolerance: absorbs the few-ULP error of a summed voltage or
# a summed current. It never widens an engineering limit.
COMPARISON_TOLERANCE = 1e-9


def _almost_le(value, limit, tol=COMPARISON_TOLERANCE):
    """True when value is at or below limit, absorbing float representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=tol, abs_tol=tol)


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _positive(value, label):
    value = _finite(value, label)
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return value


def _non_negative(value, label):
    value = _finite(value, label)
    if value < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


# ---------------------------------------------------------------------------
# 1. Worst-case generator potential
# ---------------------------------------------------------------------------


def worst_case_string_to_string_voltage(
    nominal_operating_v,
    open_circuit_factor=1.0,
    temperature_coefficient_per_c=0.0,
    minimum_temperature_c=20.0,
    reference_temperature_c=20.0,
    regulation_transient_v=0.0,
):
    """Worst-case potential between adjacent strings at an arc site.

    Built term by term: the operating point taken to open circuit, the cold
    excursion below the reference temperature, and the regulation transient.
    """
    nominal = _positive(nominal_operating_v, "nominal_operating_v")
    factor = _finite(open_circuit_factor, "open_circuit_factor")
    if factor < 1.0:
        raise ValueError("open_circuit_factor must be >= 1.0, got %r" % factor)
    coefficient = _finite(temperature_coefficient_per_c, "temperature_coefficient_per_c")
    if coefficient < 0.0:
        raise ValueError(
            "temperature_coefficient_per_c must be >= 0 (magnitude), got %r" % coefficient
        )
    t_min = _finite(minimum_temperature_c, "minimum_temperature_c")
    t_ref = _finite(reference_temperature_c, "reference_temperature_c")
    if t_min > t_ref:
        raise ValueError(
            "minimum_temperature_c %r is above reference_temperature_c %r" % (t_min, t_ref)
        )
    transient = _non_negative(regulation_transient_v, "regulation_transient_v")
    open_circuit_v = nominal * factor
    cold_rise_v = open_circuit_v * coefficient * (t_ref - t_min)
    total = 0.0
    for term in (open_circuit_v, cold_rise_v, transient):
        total += term
    return total


# ---------------------------------------------------------------------------
# 2. Sustained-arc onset voltage for the actual arc site
# ---------------------------------------------------------------------------


def sustained_arc_onset_voltage(conductor_gap_mm, insulation_material):
    """Onset voltage above which a primary arc can be sustained at the site."""
    gap = _positive(conductor_gap_mm, "conductor_gap_mm")
    if not isinstance(insulation_material, str):
        raise ValueError("insulation_material must be a string, got %r" % (insulation_material,))
    key = insulation_material.strip().lower()
    if key not in MATERIAL_FACTORS:
        raise ValueError(
            "unknown insulation_material %r; expected one of %s"
            % (insulation_material, ", ".join(sorted(MATERIAL_FACTORS)))
        )
    raw = BASE_ONSET_VOLTAGE_V + GAP_COEFFICIENT_V_PER_MM * (
        gap - REFERENCE_CONDUCTOR_GAP_MM
    )
    raw *= MATERIAL_FACTORS[key]
    return max(raw, MINIMUM_ONSET_VOLTAGE_V)


# ---------------------------------------------------------------------------
# 3. Individual exemption criteria
# ---------------------------------------------------------------------------


def evaluate_voltage_criterion(
    worst_case_voltage_v, onset_voltage_v, margin_fraction=REQUIRED_VOLTAGE_MARGIN_FRACTION
):
    """Worst-case potential must stay below the onset voltage with margin."""
    worst_case = _non_negative(worst_case_voltage_v, "worst_case_voltage_v")
    onset = _positive(onset_voltage_v, "onset_voltage_v")
    fraction = _finite(margin_fraction, "margin_fraction")
    if not 0.0 <= fraction < 1.0:
        raise ValueError("margin_fraction must be in [0, 1), got %r" % fraction)
    allowable = onset * (1.0 - fraction)
    satisfied = _almost_le(worst_case, allowable)
    return {
        "criterion": "generator-voltage-below-onset",
        "worst_case_voltage_v": worst_case,
        "onset_voltage_v": onset,
        "allowable_voltage_v": allowable,
        "margin_v": allowable - worst_case,
        "satisfied": satisfied,
    }


def evaluate_current_criterion(
    string_current_a, parallel_strings, limit_a=SUSTAINING_CURRENT_LIMIT_A
):
    """Current available at the arc site must stay below the sustaining limit."""
    per_string = _non_negative(string_current_a, "string_current_a")
    if isinstance(parallel_strings, bool) or not isinstance(parallel_strings, int):
        raise ValueError("parallel_strings must be an int, got %r" % (parallel_strings,))
    if parallel_strings < 1:
        raise ValueError("parallel_strings must be >= 1, got %r" % parallel_strings)
    limit = _positive(limit_a, "limit_a")
    available = 0.0
    for _ in range(parallel_strings):
        available += per_string
    return {
        "criterion": "available-current-below-sustaining-limit",
        "available_current_a": available,
        "limit_a": limit,
        "satisfied": _almost_le(available, limit),
    }


def missing_exemption_evidence(record):
    """Evidence items a grant needs that the record does not carry."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    supplied = record.get("evidence", [])
    if not isinstance(supplied, (list, tuple, set, frozenset)):
        raise ValueError("record['evidence'] must be a sequence of item names")
    have = {str(item).strip().lower() for item in supplied}
    return [item for item in REQUIRED_EVIDENCE_ITEMS if item not in have]


# ---------------------------------------------------------------------------
# 4. Top-level exemption decision
# ---------------------------------------------------------------------------


def evaluate_secondary_arc_test_exemption(record):
    """Grant or refuse the clause 7.2.3.1 secondary-arc test exemption."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    for key in ("nominal_operating_v", "conductor_gap_mm", "insulation_material"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    worst_case = worst_case_string_to_string_voltage(
        record["nominal_operating_v"],
        record.get("open_circuit_factor", 1.0),
        record.get("temperature_coefficient_per_c", 0.0),
        record.get("minimum_temperature_c", 20.0),
        record.get("reference_temperature_c", 20.0),
        record.get("regulation_transient_v", 0.0),
    )
    onset = sustained_arc_onset_voltage(
        record["conductor_gap_mm"], record["insulation_material"]
    )
    voltage = evaluate_voltage_criterion(
        worst_case, onset, record.get("margin_fraction", REQUIRED_VOLTAGE_MARGIN_FRACTION)
    )
    current = evaluate_current_criterion(
        record.get("string_current_a", 0.0), record.get("parallel_strings", 1)
    )
    gaps = missing_exemption_evidence(record)
    refusals = []
    if not voltage["satisfied"]:
        refusals.append("worst-case-voltage-reaches-onset")
    if not current["satisfied"]:
        refusals.append("available-current-can-sustain-an-arc")
    if gaps:
        refusals.append("exemption-evidence-incomplete")
    granted = not refusals
    return {
        "worst_case_voltage_v": worst_case,
        "onset_voltage_v": onset,
        "voltage_criterion": voltage,
        "current_criterion": current,
        "missing_evidence": gaps,
        "exemption_granted": granted,
        "refusal_reasons": refusals,
        "required_actions": [] if granted else required_actions_on_refusal(refusals),
    }


def required_actions_on_refusal(refusal_reasons):
    """Actions an array has to take when the exemption is refused."""
    if not isinstance(refusal_reasons, (list, tuple)) or not refusal_reasons:
        raise ValueError("refusal_reasons must be a non-empty sequence")
    known = {
        "worst-case-voltage-reaches-onset": "run-secondary-arc-test-campaign",
        "available-current-can-sustain-an-arc": "run-secondary-arc-test-campaign",
        "exemption-evidence-incomplete": "complete-exemption-evidence-package",
    }
    actions = []
    for reason in refusal_reasons:
        if reason not in known:
            raise ValueError("unknown refusal reason %r" % (reason,))
        if known[reason] not in actions:
            actions.append(known[reason])
    return actions
