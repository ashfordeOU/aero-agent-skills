#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.8.3 cable and shield categories
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the cables of the spacecraft
harness and their shields to be grouped into categories, following the
electromagnetic wiring clauses it refers to. This module implements the
checkable part of that clause: the mapping of a wire kind onto exactly
one harness category and its rank, the minimum bundle separation for a
routed pair derived from the two ranks, the segregation rule for the
pyrotechnic family, the required shield termination style from the
category and the highest frequency carried, the pigtail inductance and
the reactance it presents at the analysis frequency, the per-category
braid optical coverage minimum, and the voltage a shield transfer
impedance couples into a victim run. It does not lay out a connector,
does not solve a three-dimensional field problem and does not select a
braid construction.
"""

import math

# Relative tolerance used only to absorb floating-point representation
# error on an exactly-at-the-limit comparison. It never widens an
# engineering limit.
LIMIT_REL_TOL = 1e-9

CATEGORY_BY_WIRE_KIND = {
    "rf_receive_coax": "category_1_very_sensitive",
    "low_level_analogue": "category_1_very_sensitive",
    "thermistor_harness": "category_1_very_sensitive",
    "bridge_excitation": "category_1_very_sensitive",
    "digital_data_bus": "category_2_sensitive",
    "pulse_command": "category_2_sensitive",
    "secondary_power": "category_2_sensitive",
    "primary_power_feed": "category_3_noisy",
    "primary_power_return": "category_3_noisy",
    "switched_load_feed": "category_3_noisy",
    "motor_drive": "category_4_very_noisy",
    "reaction_wheel_drive": "category_4_very_noisy",
    "rf_transmit_coax": "category_4_very_noisy",
    "heater_chopper_feed": "category_4_very_noisy",
    "pyrotechnic_firing": "category_5_pyrotechnic",
    "pyrotechnic_return": "category_5_pyrotechnic",
}

CATEGORY_RANK = {
    "category_1_very_sensitive": 1,
    "category_2_sensitive": 2,
    "category_3_noisy": 3,
    "category_4_very_noisy": 4,
    "category_5_pyrotechnic": 5,
}

PYROTECHNIC_CATEGORY = "category_5_pyrotechnic"

# Minimum bundle separation in metres, keyed by the distance between
# the two category ranks.
SEPARATION_BY_RANK_DISTANCE_M = {0: 0.0, 1: 0.05, 2: 0.15, 3: 0.30, 4: 0.30}

# Shield termination styles.
TERMINATION_BOTH_ENDS = "circumferential_both_ends"
TERMINATION_SOURCE_END = "single_end_source_side"
TERMINATION_HYBRID = "hybrid_direct_source_capacitive_load"
VALID_TERMINATION_STYLES = frozenset(
    {TERMINATION_BOTH_ENDS, TERMINATION_SOURCE_END, TERMINATION_HYBRID}
)

# Above this frequency a shield only works as a barrier when it is
# bonded circumferentially at both ends.
HIGH_FREQUENCY_THRESHOLD_HZ = 1.0e5

DEFAULT_PIGTAIL_INDUCTANCE_H_PER_M = 1.0e-6
MAX_PIGTAIL_LENGTH_M = 0.025
DEFAULT_MAX_PIGTAIL_REACTANCE_OHM = 1.0

MIN_OPTICAL_COVERAGE_PERCENT = {
    "category_1_very_sensitive": 90.0,
    "category_2_sensitive": 85.0,
    "category_3_noisy": 85.0,
    "category_4_very_noisy": 90.0,
    "category_5_pyrotechnic": 95.0,
}


def categorize_cable(wire_kind):
    """Harness category for a clause 6.3.8.3 wire kind. Raises
    ValueError for a kind the wiring categories do not cover."""
    try:
        return CATEGORY_BY_WIRE_KIND[wire_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "uncategorized wire kind %r under E-ST-20C clause 6.3.8.3"
            % (wire_kind,)
        )


def category_rank(category):
    """Ordinal rank of a harness category, 1 (very sensitive) to 5
    (pyrotechnic). Raises ValueError for an unrecognized category."""
    try:
        return CATEGORY_RANK[category]
    except (KeyError, TypeError):
        raise ValueError("unrecognized harness category %r" % (category,))


def minimum_separation_m(category_a, category_b):
    """Minimum centre-to-centre bundle separation in metres for a routed
    pair, from the distance between the two category ranks. A pair that
    involves the pyrotechnic family without both runs being pyrotechnic
    always takes the largest gap. Raises ValueError through
    category_rank for an unrecognized category."""
    rank_a = category_rank(category_a)
    rank_b = category_rank(category_b)
    if (category_a == PYROTECHNIC_CATEGORY) != (
        category_b == PYROTECHNIC_CATEGORY
    ):
        return SEPARATION_BY_RANK_DISTANCE_M[3]
    return SEPARATION_BY_RANK_DISTANCE_M[abs(rank_a - rank_b)]


def requires_dedicated_overshield(category_a, category_b):
    """True when the routed pair needs a dedicated overshield on top of
    the separation: any pair with exactly one pyrotechnic run. Raises
    ValueError through category_rank for an unrecognized category."""
    category_rank(category_a)
    category_rank(category_b)
    return (category_a == PYROTECHNIC_CATEGORY) != (
        category_b == PYROTECHNIC_CATEGORY
    )


def separation_findings(pair):
    """Findings (empty when routed correctly) for one routed bundle
    pair.

    pair: {"pair_id": str, "wire_kind_a": str, "wire_kind_b": str,
    "separation_m": float, "has_dedicated_overshield": bool}. A
    separation landing exactly on the minimum is compliant; the
    comparison absorbs representation error rather than shrinking the
    minimum. Raises ValueError for a negative separation, a non-boolean
    overshield flag, or an uncategorized wire kind."""
    if pair["separation_m"] < 0:
        raise ValueError("separation_m must be >= 0")
    if not isinstance(pair.get("has_dedicated_overshield", False), bool):
        raise ValueError("has_dedicated_overshield must be a bool")
    category_a = categorize_cable(pair["wire_kind_a"])
    category_b = categorize_cable(pair["wire_kind_b"])
    required_m = minimum_separation_m(category_a, category_b)
    findings = []
    actual_m = pair["separation_m"]
    if actual_m < required_m and not math.isclose(
        actual_m, required_m, rel_tol=LIMIT_REL_TOL
    ):
        findings.append(
            {
                "issue": "bundle_separation_below_minimum",
                "pair": pair["pair_id"],
                "separation_m": actual_m,
                "minimum_m": required_m,
                "categories": (category_a, category_b),
            }
        )
    if requires_dedicated_overshield(category_a, category_b) and not pair.get(
        "has_dedicated_overshield", False
    ):
        findings.append(
            {
                "issue": "pyrotechnic_pair_without_dedicated_overshield",
                "pair": pair["pair_id"],
                "categories": (category_a, category_b),
            }
        )
    return findings


def required_shield_termination_style(category, highest_frequency_hz):
    """Shield termination style a run must use. Pyrotechnic runs and any
    run carrying content at or above the high-frequency threshold are
    bonded circumferentially at both ends; below the threshold a very
    sensitive run is terminated at the source end only, and the other
    ranks take the hybrid termination. Raises ValueError for a
    non-positive frequency or an unrecognized category."""
    category_rank(category)
    if highest_frequency_hz <= 0:
        raise ValueError("highest_frequency_hz must be > 0")
    if category == PYROTECHNIC_CATEGORY:
        return TERMINATION_BOTH_ENDS
    if highest_frequency_hz >= HIGH_FREQUENCY_THRESHOLD_HZ or math.isclose(
        highest_frequency_hz, HIGH_FREQUENCY_THRESHOLD_HZ, rel_tol=LIMIT_REL_TOL
    ):
        return TERMINATION_BOTH_ENDS
    if category == "category_1_very_sensitive":
        return TERMINATION_SOURCE_END
    return TERMINATION_HYBRID


def pigtail_inductance_h(
    pigtail_length_m, inductance_per_metre_h=DEFAULT_PIGTAIL_INDUCTANCE_H_PER_M
):
    """Inductance in henries of a shield pigtail of the given length.
    Raises ValueError for a negative length or a non-positive
    inductance per metre."""
    if pigtail_length_m < 0:
        raise ValueError("pigtail_length_m must be >= 0")
    if inductance_per_metre_h <= 0:
        raise ValueError("inductance_per_metre_h must be > 0")
    return pigtail_length_m * inductance_per_metre_h


def pigtail_reactance_ohm(
    pigtail_length_m,
    frequency_hz,
    inductance_per_metre_h=DEFAULT_PIGTAIL_INDUCTANCE_H_PER_M,
):
    """Reactance in ohms the pigtail inductance presents to shield
    current at the analysis frequency: two pi f L. Raises ValueError
    for a negative frequency or through pigtail_inductance_h."""
    if frequency_hz < 0:
        raise ValueError("frequency_hz must be >= 0")
    inductance = pigtail_inductance_h(pigtail_length_m, inductance_per_metre_h)
    return 2.0 * math.pi * frequency_hz * inductance


def termination_findings(run):
    """Findings (empty when terminated correctly) for one shielded run.

    run: {"run_id": str, "wire_kind": str, "highest_frequency_hz":
    float, "declared_termination": str, "pigtail_length_m": float,
    "max_pigtail_reactance_ohm": float (optional)}. Raises ValueError
    for a declared style outside the recognised set, a non-positive
    reactance allowance, or through the helpers."""
    declared = run["declared_termination"]
    if declared not in VALID_TERMINATION_STYLES:
        raise ValueError("unrecognized termination style %r" % (declared,))
    allowance = run.get(
        "max_pigtail_reactance_ohm", DEFAULT_MAX_PIGTAIL_REACTANCE_OHM
    )
    if allowance <= 0:
        raise ValueError("max_pigtail_reactance_ohm must be > 0")
    category = categorize_cable(run["wire_kind"])
    required = required_shield_termination_style(
        category, run["highest_frequency_hz"]
    )
    findings = []
    if declared != required:
        findings.append(
            {
                "issue": "shield_termination_style_mismatch",
                "run": run["run_id"],
                "declared_termination": declared,
                "required_termination": required,
                "category": category,
            }
        )
    if required == TERMINATION_BOTH_ENDS:
        length_m = run["pigtail_length_m"]
        if length_m > MAX_PIGTAIL_LENGTH_M and not math.isclose(
            length_m, MAX_PIGTAIL_LENGTH_M, rel_tol=LIMIT_REL_TOL
        ):
            findings.append(
                {
                    "issue": "pigtail_longer_than_circumferential_allowance",
                    "run": run["run_id"],
                    "pigtail_length_m": length_m,
                    "maximum_m": MAX_PIGTAIL_LENGTH_M,
                }
            )
        reactance = pigtail_reactance_ohm(
            length_m, run["highest_frequency_hz"]
        )
        if reactance > allowance and not math.isclose(
            reactance, allowance, rel_tol=LIMIT_REL_TOL
        ):
            findings.append(
                {
                    "issue": "pigtail_reactance_above_allowance",
                    "run": run["run_id"],
                    "reactance_ohm": reactance,
                    "allowance_ohm": allowance,
                }
            )
    return findings


def minimum_optical_coverage_percent(category):
    """Minimum braid optical coverage in percent for a harness category.
    Raises ValueError for an unrecognized category."""
    category_rank(category)
    return MIN_OPTICAL_COVERAGE_PERCENT[category]


def coverage_findings(run_id, wire_kind, optical_coverage_percent):
    """Findings (empty when covered) for one braid. Coverage exactly on
    the minimum is compliant. Raises ValueError for a coverage outside
    (0, 100] or an uncategorized wire kind."""
    if not (0.0 < optical_coverage_percent <= 100.0):
        raise ValueError("optical_coverage_percent must be in (0, 100]")
    category = categorize_cable(wire_kind)
    minimum = minimum_optical_coverage_percent(category)
    if optical_coverage_percent >= minimum or math.isclose(
        optical_coverage_percent, minimum, rel_tol=LIMIT_REL_TOL
    ):
        return []
    return [
        {
            "issue": "braid_optical_coverage_below_minimum",
            "run": run_id,
            "category": category,
            "coverage_percent": optical_coverage_percent,
            "minimum_percent": minimum,
        }
    ]


def shield_transfer_coupled_voltage(
    transfer_impedance_ohm_per_m, coupled_length_m, disturbing_current_a
):
    """Voltage in volts coupled through a shield: transfer impedance per
    metre times the coupled length times the disturbing current. Raises
    ValueError for a negative transfer impedance, length or current."""
    if transfer_impedance_ohm_per_m < 0:
        raise ValueError("transfer_impedance_ohm_per_m must be >= 0")
    if coupled_length_m < 0:
        raise ValueError("coupled_length_m must be >= 0")
    if disturbing_current_a < 0:
        raise ValueError("disturbing_current_a must be >= 0")
    return (
        transfer_impedance_ohm_per_m * coupled_length_m * disturbing_current_a
    )


def coupling_findings(coupling):
    """Findings (empty when inside budget) for one aggressor and victim
    pair.

    coupling: {"victim_id": str, "transfer_impedance_ohm_per_m": float,
    "coupled_length_m": float, "disturbing_current_a": float,
    "susceptibility_voltage_v": float}. A coupled voltage landing
    exactly on the susceptibility voltage is compliant. Raises
    ValueError for a non-positive susceptibility voltage or through
    shield_transfer_coupled_voltage."""
    susceptibility_v = coupling["susceptibility_voltage_v"]
    if susceptibility_v <= 0:
        raise ValueError("susceptibility_voltage_v must be > 0")
    coupled_v = shield_transfer_coupled_voltage(
        coupling["transfer_impedance_ohm_per_m"],
        coupling["coupled_length_m"],
        coupling["disturbing_current_a"],
    )
    if coupled_v <= susceptibility_v or math.isclose(
        coupled_v, susceptibility_v, rel_tol=LIMIT_REL_TOL
    ):
        return []
    return [
        {
            "issue": "shield_coupled_voltage_above_susceptibility",
            "victim": coupling["victim_id"],
            "coupled_v": coupled_v,
            "susceptibility_v": susceptibility_v,
        }
    ]


def harness_review(harness):
    """Full clause 6.3.8.3 review of one harness definition.

    harness: {"runs": [{"run_id", "wire_kind", "highest_frequency_hz",
    "declared_termination", "pigtail_length_m",
    "optical_coverage_percent", "max_pigtail_reactance_ohm"
    (optional)}], "routed_pairs": [...see separation_findings...],
    "couplings": [...see coupling_findings...]}.

    Returns {"category": [...], "separation": [...],
    "termination": [...], "coverage": [...], "coupling": [...]}. The
    category list records every run whose declared category differs
    from the one its wire kind maps to, when a category is declared.
    Raises ValueError through the helpers. Does not mutate harness."""
    category_findings = []
    termination = []
    coverage = []
    for run in harness.get("runs", []):
        category = categorize_cable(run["wire_kind"])
        declared_category = run.get("declared_category")
        if declared_category is not None and declared_category != category:
            category_findings.append(
                {
                    "issue": "declared_category_does_not_match_wire_kind",
                    "run": run["run_id"],
                    "declared_category": declared_category,
                    "derived_category": category,
                }
            )
        termination.extend(termination_findings(run))
        coverage.extend(
            coverage_findings(
                run["run_id"], run["wire_kind"], run["optical_coverage_percent"]
            )
        )
    separation = []
    for pair in harness.get("routed_pairs", []):
        separation.extend(separation_findings(pair))
    coupling = []
    for item in harness.get("couplings", []):
        coupling.extend(coupling_findings(item))
    return {
        "category": category_findings,
        "separation": separation,
        "termination": termination,
        "coverage": coverage,
        "coupling": coupling,
    }


def is_harness_compliant(review):
    """True when every finding list in a harness_review result is empty
    -- every run is categorized, routed, terminated, covered and inside
    its coupling budget."""
    return all(len(findings) == 0 for findings in review.values())
