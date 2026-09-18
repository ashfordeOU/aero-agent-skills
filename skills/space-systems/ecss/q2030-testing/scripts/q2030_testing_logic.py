"""Test programme of a manufactured electrical harness.

Anchor: ECSS-Q-ST-20-30C section 6.19, which binds the harness testing
section (section 19) of the IPC/WHMA-A-620 acceptance basis
(paraphrased into an implementable procedure; no standard text is
reproduced).

Procedure implemented here:

1. Decide which tests the harness owes. Nondestructive examination and
   electrical continuity are owed by every harness. Insulation
   resistance is owed once there is more than one conductor or a shield
   to isolate from. A dielectric withstanding voltage test is owed once
   the working voltage is above the low-voltage threshold. A mechanical
   strength test is owed where the build documentation calls one.
2. Grade continuity against a computed expectation rather than against
   a guessed number. The loop resistance of a harness leg is the
   conductor resistance of its length and cross-section plus an
   allowance for each mated contact pair in the path; the limit is that
   expectation widened by the manufacturing tolerance.
3. Grade insulation resistance against its floor at the declared test
   voltage, and refuse a reading taken before the electrification time
   has elapsed -- the reading is still falling at that point.
4. Derive the dielectric withstanding voltage from the working voltage
   rather than accepting whatever was applied, and grade the leakage
   current and the dwell against their limits.
5. Grade mechanical strength against a pull force scaled to the
   conductor cross-section.
6. Handle rework and repair. A reworked harness repeats the tests its
   rework could have disturbed, and the dielectric test is repeated at
   a reduced voltage so the insulation is not stressed to the full
   proof level twice.

Stdlib only, offline, deterministic.
"""

TEST_VISUAL = "nondestructive-visual-examination"
TEST_CONTINUITY = "electrical-continuity"
TEST_INSULATION = "insulation-resistance"
TEST_DIELECTRIC = "dielectric-withstanding-voltage"
TEST_MECHANICAL = "mechanical-strength"

TEST_ORDER = (
    TEST_VISUAL,
    TEST_CONTINUITY,
    TEST_INSULATION,
    TEST_DIELECTRIC,
    TEST_MECHANICAL,
)

# Annealed copper at room temperature.
COPPER_RESISTIVITY_OHM_M = 1.72e-8

# Allowance for one mated contact pair in the measured loop.
CONTACT_PAIR_ALLOWANCE_OHM = 5.0e-3

# Manufacturing spread the continuity limit is widened by.
CONTINUITY_TOLERANCE_FRACTION = 0.20

# Below this working voltage the dielectric withstanding test is not
# owed; the insulation is not being asked to hold anything.
DIELECTRIC_THRESHOLD_V = 50.0

# Dielectric withstanding voltage derived from the working voltage.
DIELECTRIC_VOLTAGE_FACTOR = 2.0
DIELECTRIC_VOLTAGE_OFFSET_V = 1000.0

# A harness that has already taken a full-level dielectric test is
# retested below that level after rework.
DIELECTRIC_RETEST_FACTOR = 0.8

MIN_DIELECTRIC_DWELL_S = 60.0
MAX_DIELECTRIC_LEAKAGE_UA = 100.0

MIN_INSULATION_RESISTANCE_MOHM = 100.0
MIN_INSULATION_ELECTRIFICATION_S = 60.0

# Pull force a soldered or crimped termination is expected to hold,
# scaled to conductor cross-section with a floor for fine gauges.
PULL_FORCE_N_PER_MM2 = 60.0
MIN_PULL_FORCE_N = 10.0

# Resistances, voltages and forces are quotients and products of
# measured floats, so a value sitting exactly on its limit can land a
# few units in the last place beyond it. These tolerances are far below
# any test-equipment resolution and absorb that representation error
# without relaxing the limits themselves.
RESISTANCE_TOLERANCE_OHM = 1.0e-12
VOLTAGE_TOLERANCE_V = 1.0e-9
FORCE_TOLERANCE_N = 1.0e-12
TIME_TOLERANCE_S = 1.0e-9
CURRENT_TOLERANCE_UA = 1.0e-12
INSULATION_TOLERANCE_MOHM = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_harness(harness):
    """Validate one harness record and return a normalized copy."""
    if not isinstance(harness, dict):
        raise ValueError("harness must be a mapping")
    harness_id = harness.get("id")
    if not isinstance(harness_id, str) or not harness_id.strip():
        raise ValueError("harness needs a non-empty string id")
    conductors = harness.get("conductor_count")
    if not isinstance(conductors, int) or isinstance(conductors, bool) or conductors < 1:
        raise ValueError(
            "harness %s conductor_count must be an integer >= 1" % harness_id
        )
    contact_pairs = harness.get("contact_pairs", 2)
    if (
        not isinstance(contact_pairs, int)
        or isinstance(contact_pairs, bool)
        or contact_pairs < 0
    ):
        raise ValueError(
            "harness %s contact_pairs must be an integer >= 0" % harness_id
        )
    length = _numeric("harness %s length_m" % harness_id, harness.get("length_m"))
    if length <= 0:
        raise ValueError("harness %s length_m must be positive" % harness_id)
    area = _numeric(
        "harness %s cross_section_mm2" % harness_id, harness.get("cross_section_mm2")
    )
    if area <= 0:
        raise ValueError("harness %s cross_section_mm2 must be positive" % harness_id)
    results = harness.get("results", {})
    if not isinstance(results, dict):
        raise ValueError("harness %s results must be a mapping" % harness_id)
    for name in results:
        if name not in TEST_ORDER:
            raise ValueError("harness %s has unknown test result %r" % (harness_id, name))
    return {
        "id": harness_id,
        "conductor_count": conductors,
        "contact_pairs": contact_pairs,
        "length_m": length,
        "cross_section_mm2": area,
        "shielded": _boolean(
            "harness %s shielded" % harness_id, harness.get("shielded", False)
        ),
        "working_voltage_v": _numeric(
            "harness %s working_voltage_v" % harness_id,
            harness.get("working_voltage_v", 0.0),
            0.0,
        ),
        "mechanical_test_called": _boolean(
            "harness %s mechanical_test_called" % harness_id,
            harness.get("mechanical_test_called", False),
        ),
        "reworked": _boolean(
            "harness %s reworked" % harness_id, harness.get("reworked", False)
        ),
        "rework_touched_insulation": _boolean(
            "harness %s rework_touched_insulation" % harness_id,
            harness.get("rework_touched_insulation", False),
        ),
        "results": dict(results),
    }


def expected_loop_resistance_ohm(length_m, cross_section_mm2, contact_pairs):
    """Loop resistance a healthy harness leg is expected to show, in ohms."""
    length = _numeric("length_m", length_m)
    area = _numeric("cross_section_mm2", cross_section_mm2)
    if length <= 0:
        raise ValueError("length_m must be positive")
    if area <= 0:
        raise ValueError("cross_section_mm2 must be positive")
    if not isinstance(contact_pairs, int) or isinstance(contact_pairs, bool) or contact_pairs < 0:
        raise ValueError("contact_pairs must be an integer >= 0")
    conductor = COPPER_RESISTIVITY_OHM_M * length / (area * 1.0e-6)
    return conductor + contact_pairs * CONTACT_PAIR_ALLOWANCE_OHM


def continuity_limit_ohm(expected_ohm):
    """Continuity limit: the expectation widened by the build tolerance."""
    expected = _numeric("expected_ohm", expected_ohm, 0.0)
    return expected * (1.0 + CONTINUITY_TOLERANCE_FRACTION)


def dielectric_test_voltage_v(working_voltage_v, previously_tested=False):
    """Dielectric withstanding voltage owed by a working voltage."""
    working = _numeric("working_voltage_v", working_voltage_v, 0.0)
    full = DIELECTRIC_VOLTAGE_FACTOR * working + DIELECTRIC_VOLTAGE_OFFSET_V
    if _boolean("previously_tested", previously_tested):
        return full * DIELECTRIC_RETEST_FACTOR
    return full


def minimum_pull_force_n(cross_section_mm2):
    """Pull force a termination of this cross-section is expected to hold."""
    area = _numeric("cross_section_mm2", cross_section_mm2)
    if area <= 0:
        raise ValueError("cross_section_mm2 must be positive")
    scaled = PULL_FORCE_N_PER_MM2 * area
    return scaled if scaled > MIN_PULL_FORCE_N else MIN_PULL_FORCE_N


def required_tests(harness):
    """Tests the harness owes, in the order they are run."""
    norm = validate_harness(harness)
    owed = [TEST_VISUAL, TEST_CONTINUITY]
    if norm["conductor_count"] > 1 or norm["shielded"]:
        owed.append(TEST_INSULATION)
    if norm["working_voltage_v"] > DIELECTRIC_THRESHOLD_V:
        owed.append(TEST_DIELECTRIC)
    if norm["mechanical_test_called"]:
        owed.append(TEST_MECHANICAL)
    return [name for name in TEST_ORDER if name in owed]


def tests_after_rework(harness):
    """Tests a reworked or repaired harness repeats."""
    norm = validate_harness(harness)
    if not norm["reworked"]:
        return []
    owed = required_tests(norm)
    repeat = [name for name in owed if name in (TEST_VISUAL, TEST_CONTINUITY)]
    if norm["rework_touched_insulation"]:
        repeat.extend(
            name for name in owed if name in (TEST_INSULATION, TEST_DIELECTRIC)
        )
    return [name for name in TEST_ORDER if name in repeat]


def continuity_findings(harness):
    """Findings about the continuity result of one harness."""
    norm = validate_harness(harness)
    record = norm["results"].get(TEST_CONTINUITY)
    if not isinstance(record, dict):
        return ["no-continuity-measurement-on-record"]
    measured = _numeric("measured_ohm", record.get("measured_ohm"), 0.0)
    expected = expected_loop_resistance_ohm(
        norm["length_m"], norm["cross_section_mm2"], norm["contact_pairs"]
    )
    limit = continuity_limit_ohm(expected)
    if measured > limit + RESISTANCE_TOLERANCE_OHM:
        return ["continuity-resistance-above-the-computed-limit"]
    return []


def insulation_findings(harness):
    """Findings about the insulation-resistance result of one harness."""
    norm = validate_harness(harness)
    if TEST_INSULATION not in required_tests(norm):
        return []
    record = norm["results"].get(TEST_INSULATION)
    if not isinstance(record, dict):
        return ["no-insulation-resistance-measurement-on-record"]
    findings = []
    measured = _numeric("measured_mohm", record.get("measured_mohm"), 0.0)
    dwell = _numeric("electrification_time_s", record.get("electrification_time_s", 0.0), 0.0)
    if dwell + TIME_TOLERANCE_S < MIN_INSULATION_ELECTRIFICATION_S:
        findings.append("insulation-reading-taken-before-electrification-time")
    if measured + INSULATION_TOLERANCE_MOHM < MIN_INSULATION_RESISTANCE_MOHM:
        findings.append("insulation-resistance-below-the-floor")
    return findings


def dielectric_findings(harness):
    """Findings about the dielectric withstanding result of one harness."""
    norm = validate_harness(harness)
    if TEST_DIELECTRIC not in required_tests(norm):
        return []
    record = norm["results"].get(TEST_DIELECTRIC)
    if not isinstance(record, dict):
        return ["no-dielectric-withstanding-test-on-record"]
    findings = []
    applied = _numeric("applied_v", record.get("applied_v"), 0.0)
    leakage = _numeric("leakage_ua", record.get("leakage_ua", 0.0), 0.0)
    dwell = _numeric("dwell_s", record.get("dwell_s", 0.0), 0.0)
    required = dielectric_test_voltage_v(
        norm["working_voltage_v"],
        previously_tested=norm["reworked"],
    )
    if applied + VOLTAGE_TOLERANCE_V < required:
        findings.append("dielectric-test-voltage-below-the-derived-level")
    if norm["reworked"] and applied > required + VOLTAGE_TOLERANCE_V:
        findings.append("retest-applied-above-the-reduced-level")
    if dwell + TIME_TOLERANCE_S < MIN_DIELECTRIC_DWELL_S:
        findings.append("dielectric-dwell-shorter-than-required")
    if leakage > MAX_DIELECTRIC_LEAKAGE_UA + CURRENT_TOLERANCE_UA:
        findings.append("dielectric-leakage-current-above-the-limit")
    return findings


def mechanical_findings(harness):
    """Findings about the mechanical-strength result of one harness."""
    norm = validate_harness(harness)
    if TEST_MECHANICAL not in required_tests(norm):
        return []
    record = norm["results"].get(TEST_MECHANICAL)
    if not isinstance(record, dict):
        return ["no-mechanical-strength-test-on-record"]
    applied = _numeric("applied_force_n", record.get("applied_force_n"), 0.0)
    required = minimum_pull_force_n(norm["cross_section_mm2"])
    if applied + FORCE_TOLERANCE_N < required:
        return ["pull-force-below-the-scaled-minimum"]
    return []


def missing_tests(harness):
    """Owed tests with no result on record."""
    norm = validate_harness(harness)
    return [
        name
        for name in required_tests(norm)
        if not isinstance(norm["results"].get(name), dict)
    ]


def assess_harness_test_programme(harness):
    """Assess the test programme of one harness against section 6.19."""
    norm = validate_harness(harness)
    owed = required_tests(norm)
    findings = []
    visual = norm["results"].get(TEST_VISUAL)
    if not isinstance(visual, dict):
        findings.append("no-visual-examination-on-record")
    elif not _boolean("visual accepted", visual.get("accepted", False)):
        findings.append("visual-examination-not-accepted")
    findings.extend(continuity_findings(norm))
    findings.extend(insulation_findings(norm))
    findings.extend(dielectric_findings(norm))
    findings.extend(mechanical_findings(norm))
    repeats = tests_after_rework(norm)
    return {
        "id": norm["id"],
        "required_tests": owed,
        "missing_tests": missing_tests(norm),
        "repeat_after_rework": repeats,
        "expected_loop_resistance_ohm": expected_loop_resistance_ohm(
            norm["length_m"], norm["cross_section_mm2"], norm["contact_pairs"]
        ),
        "dielectric_test_voltage_v": (
            dielectric_test_voltage_v(
                norm["working_voltage_v"], previously_tested=norm["reworked"]
            )
            if TEST_DIELECTRIC in owed
            else None
        ),
        "minimum_pull_force_n": (
            minimum_pull_force_n(norm["cross_section_mm2"])
            if TEST_MECHANICAL in owed
            else None
        ),
        "findings": findings,
        "compliant": not findings,
    }


def assess_harness_lot(harnesses):
    """Run the section 6.19 assessment over a lot of harnesses."""
    if not isinstance(harnesses, list) or not harnesses:
        raise ValueError("harnesses must be a non-empty list")
    results = []
    seen = set()
    for harness in harnesses:
        result = assess_harness_test_programme(harness)
        if result["id"] in seen:
            raise ValueError("duplicate harness id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "harnesses": results,
        "reworked_ids": [r["id"] for r in results if r["repeat_after_rework"]],
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
