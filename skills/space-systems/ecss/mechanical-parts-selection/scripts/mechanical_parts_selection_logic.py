#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.5.7 mechanical parts selection
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structures standard's mechanical-parts clause requires fasteners (bolts,
screws, rivets, pins), inserts (helicoil, key-locking, threaded), and
bearings (ball, roller, bush) to be selected from a Qualified Parts List
(QPL) or equivalent approved-source register; each installation must carry
a non-negative margin of safety (MS = rated_load/applied_load - 1) against
the governing structural load case; the part's rated temperature range must
encompass the full mission thermal envelope; and dissimilar-metal pairings
with significant galvanic potential must be flagged for mitigation. This
module implements part categorization, qualification-status checking, load
margin computation, temperature-range compliance, and galvanic-risk
identification; it does not define QPL content, set load factors, or specify
mitigation techniques.
"""

FASTENER_SUBTYPES = frozenset({"bolt", "screw", "rivet", "pin", "stud"})
INSERT_SUBTYPES = frozenset(
    {"helicoil_insert", "key_locking_insert", "threaded_insert", "press_fit_insert"}
)
BEARING_SUBTYPES = frozenset(
    {"ball_bearing", "roller_bearing", "bush_bearing", "plain_bearing"}
)

# Minimum acceptable margin of safety per structural design practice.
MINIMUM_MARGIN_OF_SAFETY = 0.0

# Material pairs with significant galvanic corrosion risk in a spacecraft
# assembly environment (based on standard electrochemical series practice,
# not verbatim ECSS text). Each entry is a frozenset of two material names.
HIGH_GALVANIC_RISK_PAIRS = frozenset(
    {
        frozenset({"aluminum", "steel"}),
        frozenset({"magnesium", "steel"}),
        frozenset({"magnesium", "aluminum"}),
        frozenset({"cfrp", "aluminum"}),
        frozenset({"titanium", "magnesium"}),
        frozenset({"copper", "aluminum"}),
        frozenset({"cfrp", "steel"}),
    }
)


def categorize_part(part_type):
    """Mechanical-parts category for a part type: "fastener", "insert", or
    "bearing". Raises ValueError for a part type outside all known sets."""
    if part_type in FASTENER_SUBTYPES:
        return "fastener"
    if part_type in INSERT_SUBTYPES:
        return "insert"
    if part_type in BEARING_SUBTYPES:
        return "bearing"
    raise ValueError(
        "unrecognized mechanical part type %r under "
        "E-ST-32C clause 4.5.7" % (part_type,)
    )


def check_qualification_status(part_id, qualified_parts_set):
    """Violation list (empty if compliant) for a part's qualification status.
    qualified_parts_set: iterable of approved part-number strings. If
    part_id is absent from that set the part must receive a formal
    deviation before use."""
    if part_id not in qualified_parts_set:
        return [
            {
                "issue": "part_not_on_qualified_parts_list",
                "part": part_id,
            }
        ]
    return []


def compute_margin_of_safety(applied_load_n, rated_load_n):
    """Margin of safety = rated_load_n / applied_load_n - 1.
    Raises ValueError for a non-positive applied load or rated load."""
    if applied_load_n <= 0:
        raise ValueError("applied_load_n must be > 0; got %r" % (applied_load_n,))
    if rated_load_n <= 0:
        raise ValueError("rated_load_n must be > 0; got %r" % (rated_load_n,))
    return rated_load_n / applied_load_n - 1.0


def check_load_compliance(part_id, applied_load_n, rated_load_n):
    """Violation list (empty if compliant) for the load margin of safety.
    Flags the part when MS < MINIMUM_MARGIN_OF_SAFETY. Propagates
    ValueError from compute_margin_of_safety for invalid inputs."""
    ms = compute_margin_of_safety(applied_load_n, rated_load_n)
    if ms < MINIMUM_MARGIN_OF_SAFETY:
        return [
            {
                "issue": "negative_load_margin_of_safety",
                "part": part_id,
                "applied_load_n": applied_load_n,
                "rated_load_n": rated_load_n,
                "margin_of_safety": ms,
            }
        ]
    return []


def check_temperature_range(
    part_id, mission_min_c, mission_max_c, part_rated_min_c, part_rated_max_c
):
    """Violation list (empty if compliant) for thermal range coverage.
    Flags separately when the part's rated minimum exceeds the mission
    cold-case minimum or the part's rated maximum falls below the
    mission hot-case maximum. Does not mutate inputs."""
    violations = []
    if part_rated_min_c > mission_min_c:
        violations.append(
            {
                "issue": "part_rated_min_exceeds_mission_min",
                "part": part_id,
                "mission_min_c": mission_min_c,
                "part_rated_min_c": part_rated_min_c,
            }
        )
    if part_rated_max_c < mission_max_c:
        violations.append(
            {
                "issue": "part_rated_max_below_mission_max",
                "part": part_id,
                "mission_max_c": mission_max_c,
                "part_rated_max_c": part_rated_max_c,
            }
        )
    return violations


def check_galvanic_compatibility(part_id, part_material, mating_material):
    """Violation list (empty if compliant) for galvanic corrosion risk.
    Flags the pairing when the (part_material, mating_material) combination
    appears in HIGH_GALVANIC_RISK_PAIRS."""
    pair = frozenset({part_material, mating_material})
    if pair in HIGH_GALVANIC_RISK_PAIRS:
        return [
            {
                "issue": "high_galvanic_risk_material_pair",
                "part": part_id,
                "part_material": part_material,
                "mating_material": mating_material,
            }
        ]
    return []


def mechanical_part_review(part):
    """Full clause 4.5.7 parts-selection review for one mechanical part.

    part: {
        "part_id": str,
        "part_type": str,
        "qualified_parts_set": set[str] | None  (None skips check),
        "applied_load_n": float | None           (None skips load check),
        "rated_load_n": float | None,
        "mission_min_c": float | None            (all four required for temp check),
        "mission_max_c": float | None,
        "part_rated_min_c": float | None,
        "part_rated_max_c": float | None,
        "part_material": str | None              (both required for galvanic check),
        "mating_material": str | None,
    }

    Returns {
        "category": str,
        "qualification": [...],
        "load": [...],
        "temperature": [...],
        "galvanic": [...],
    }.
    Raises ValueError for an unrecognized part_type or invalid load inputs.
    Does not mutate part."""
    part_id = part["part_id"]

    category = categorize_part(part["part_type"])

    qualified_parts_set = part.get("qualified_parts_set")
    qual_violations = (
        check_qualification_status(part_id, qualified_parts_set)
        if qualified_parts_set is not None
        else []
    )

    applied = part.get("applied_load_n")
    rated = part.get("rated_load_n")
    load_violations = (
        check_load_compliance(part_id, applied, rated)
        if applied is not None and rated is not None
        else []
    )

    m_min = part.get("mission_min_c")
    m_max = part.get("mission_max_c")
    p_min = part.get("part_rated_min_c")
    p_max = part.get("part_rated_max_c")
    temp_violations = (
        check_temperature_range(part_id, m_min, m_max, p_min, p_max)
        if all(v is not None for v in (m_min, m_max, p_min, p_max))
        else []
    )

    part_mat = part.get("part_material")
    mating_mat = part.get("mating_material")
    galv_violations = (
        check_galvanic_compatibility(part_id, part_mat, mating_mat)
        if part_mat is not None and mating_mat is not None
        else []
    )

    return {
        "category": category,
        "qualification": qual_violations,
        "load": load_violations,
        "temperature": temp_violations,
        "galvanic": galv_violations,
    }


def is_part_compliant(review):
    """True when all violation lists in a mechanical_part_review result are
    empty — the part satisfies all clause 4.5.7 checks for this assessment."""
    return all(
        len(v) == 0 for k, v in review.items() if k != "category"
    )
