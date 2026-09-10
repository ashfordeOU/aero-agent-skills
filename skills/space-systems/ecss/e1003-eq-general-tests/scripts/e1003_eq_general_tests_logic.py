"""Deterministic logic for ECSS-E-ST-10-03C clause 5.5.1 general equipment
test requirements.

Offline, stdlib-only module backing the e1003-eq-general-tests skill leaf:
the functional/performance test depth and baseline comparison, the
physical configuration verification (mass properties and visual
inspection), the launch configuration verification, and the point-level
and sequence-level disposition that accompany every test in an equipment
qualification, acceptance, or protoflight test sequence.
"""

SEQUENCE_POSITIONS = frozenset({"baseline", "interim", "final"})

FUNCTIONAL_DEPTHS = frozenset({"comprehensive", "abbreviated"})

CONFIGURATION_STATUSES = frozenset({"as_configured", "configuration_discrepancy"})

VERDICTS = frozenset(
    {
        "pass",
        "functional_degradation",
        "configuration_discrepancy",
        "launch_configuration_mismatch",
    }
)


def required_functional_depth(position: str, anomaly_suspected: bool) -> str:
    """Functional/performance test depth required at a sequence position.

    The baseline and final positions are always comprehensive so the
    sequence has full-coverage endpoints to compare interim results
    against. An interim position may be abbreviated, unless an anomaly is
    suspected at that point, in which case a comprehensive run is needed
    to characterize it regardless of position.
    """
    if position not in SEQUENCE_POSITIONS:
        raise ValueError(f"unknown sequence position: {position!r}")
    if position in ("baseline", "final") or anomaly_suspected:
        return "comprehensive"
    return "abbreviated"


def evaluate_functional_performance(
    baseline_measurements: dict, current_measurements: dict, tolerance_pct: float
) -> list:
    """Parameters whose current value has drifted from baseline beyond
    tolerance_pct, sorted by parameter name for a deterministic result.

    A functional/performance result is judged against the baseline, not
    a fixed spec alone -- a parameter can drift beyond its allowed
    tolerance and still sit inside the equipment's overall performance
    envelope, which is why the comparison is explicit. Raises ValueError
    if a baseline parameter is missing from the current measurements
    (an incomplete functional/performance run).
    """
    missing = sorted(name for name in baseline_measurements if name not in current_measurements)
    if missing:
        raise ValueError(f"functional test missing baseline parameters: {missing}")

    degraded = []
    for name in sorted(baseline_measurements):
        baseline_value = baseline_measurements[name]
        current_value = current_measurements[name]
        if baseline_value == 0:
            deviation_pct = 0.0 if current_value == 0 else float("inf")
        else:
            deviation_pct = abs(current_value - baseline_value) / abs(baseline_value) * 100.0
        if deviation_pct > tolerance_pct:
            degraded.append(name)
    return degraded


def check_physical_configuration(
    measured_mass: float,
    reference_mass: float,
    mass_tolerance_pct: float,
    visual_anomaly_detected: bool,
) -> str:
    """Physical configuration verdict: mass properties plus visual
    inspection.

    Either a mass outside tolerance of the reference value or a reported
    visual anomaly (e.g. loose hardware, cracks, contamination) is a
    configuration discrepancy; a mass in tolerance does not excuse a
    reported visual anomaly.
    """
    if reference_mass == 0:
        raise ValueError("reference_mass must be non-zero")
    mass_deviation_pct = abs(measured_mass - reference_mass) / abs(reference_mass) * 100.0
    mass_within_tolerance = mass_deviation_pct <= mass_tolerance_pct
    if visual_anomaly_detected or not mass_within_tolerance:
        return "configuration_discrepancy"
    return "as_configured"


def check_launch_configuration(
    current_configuration: str,
    required_launch_configuration: str,
    represents_launch_environment: bool,
) -> bool:
    """Launch configuration verdict for one test point.

    Only applies when the test represents the launch environment (e.g. a
    mechanical test); a test that does not represent the launch
    environment (e.g. a bench functional test) is exempt and always
    returns True.
    """
    if not represents_launch_environment:
        return True
    return current_configuration == required_launch_configuration


def evaluate_test_point(point: dict) -> dict:
    """General test disposition for one sequence point dict.

    Required keys: position, anomaly_suspected, baseline_measurements,
    current_measurements, tolerance_pct, measured_mass, reference_mass,
    mass_tolerance_pct, visual_anomaly_detected,
    represents_launch_environment, current_configuration,
    required_launch_configuration. Checks run in gating order: functional
    degradation first, then physical configuration, then launch
    configuration. Returns a new dict; does not mutate the input.
    """
    depth = required_functional_depth(point["position"], point["anomaly_suspected"])
    degraded_parameters = evaluate_functional_performance(
        point["baseline_measurements"], point["current_measurements"], point["tolerance_pct"]
    )
    configuration_status = check_physical_configuration(
        point["measured_mass"],
        point["reference_mass"],
        point["mass_tolerance_pct"],
        point["visual_anomaly_detected"],
    )
    launch_configuration_ok = check_launch_configuration(
        point["current_configuration"],
        point["required_launch_configuration"],
        point["represents_launch_environment"],
    )

    if degraded_parameters:
        verdict = "functional_degradation"
    elif configuration_status != "as_configured":
        verdict = "configuration_discrepancy"
    elif not launch_configuration_ok:
        verdict = "launch_configuration_mismatch"
    else:
        verdict = "pass"

    return {
        "position": point["position"],
        "functional_depth": depth,
        "degraded_parameters": degraded_parameters,
        "configuration_status": configuration_status,
        "launch_configuration_ok": launch_configuration_ok,
        "verdict": verdict,
    }


def build_sequence_dispositions(points: list) -> list:
    """Disposition for every test point, in input order."""
    return [evaluate_test_point(point) for point in points]


def missing_mandatory_positions(points: list) -> list:
    """Mandatory positions (baseline, final) absent from the sequence,
    in canonical order -- a sequence cannot close the general test
    requirements without a full-coverage endpoint at each end.
    """
    positions_present = {point["position"] for point in points}
    return [pos for pos in ("baseline", "final") if pos not in positions_present]


def close_out_general_test_sequence(points: list, dispositions: list) -> tuple:
    """Closure verdict for the general test requirements across a
    sequence.

    Returns (all_clear, missing_positions, open_items): all_clear is True
    only when both mandatory positions are present and every disposition
    is a pass; open_items lists the position/verdict pairs still blocking
    closure, in input order.
    """
    missing_positions = missing_mandatory_positions(points)
    open_items = [
        {"position": entry["position"], "verdict": entry["verdict"]}
        for entry in dispositions
        if entry["verdict"] != "pass"
    ]
    all_clear = not missing_positions and not open_items
    return (all_clear, missing_positions, open_items)
