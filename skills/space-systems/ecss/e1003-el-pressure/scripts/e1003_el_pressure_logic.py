"""
ECSS-E-ST-10C §6.5.3 element pressure test logic.

Implements deterministic, offline checks for the four element pressure test
types: proof, pressure cycling, design burst, and leak.  All functions return
explicit pass/fail verdicts plus a findings list so every failure path is
auditable.  No third-party dependencies -- stdlib only.
"""

DEFAULT_PROOF_FACTOR = 1.5      # proof pressure = MEOP × proof_factor
DEFAULT_BURST_FACTOR = 2.0      # design burst pressure = MEOP × burst_factor
DEFAULT_LEAK_RATE_LIMIT_PA_M3_S = 1e-6  # Pa·m³/s illustrative allowable


class PressureTestError(ValueError):
    """Raised when input parameters are physically invalid."""


def compute_proof_pressure(meop_pa: float, proof_factor: float = DEFAULT_PROOF_FACTOR) -> float:
    """Return the required proof pressure in Pa."""
    if meop_pa <= 0:
        raise PressureTestError(f"MEOP must be positive, got {meop_pa}")
    if proof_factor < 1.0:
        raise PressureTestError(f"Proof factor must be >= 1.0, got {proof_factor}")
    return meop_pa * proof_factor


def compute_burst_pressure(meop_pa: float, burst_factor: float = DEFAULT_BURST_FACTOR) -> float:
    """Return the required design burst pressure in Pa."""
    if meop_pa <= 0:
        raise PressureTestError(f"MEOP must be positive, got {meop_pa}")
    if burst_factor < 1.0:
        raise PressureTestError(f"Burst factor must be >= 1.0, got {burst_factor}")
    return meop_pa * burst_factor


def check_proof_test(
    applied_pressure_pa: float,
    meop_pa: float,
    hold_duration_s: float,
    required_hold_s: float,
    deformation_detected: bool = False,
    leak_detected: bool = False,
    proof_factor: float = DEFAULT_PROOF_FACTOR,
) -> dict:
    """
    Evaluate a proof pressure test result.

    Returns a dict with:
      passed   -- True when all criteria are met
      findings -- list of strings describing each failed criterion
    """
    required_proof = compute_proof_pressure(meop_pa, proof_factor)
    findings = []

    if applied_pressure_pa < required_proof:
        findings.append(
            f"Applied pressure {applied_pressure_pa:.1f} Pa is below the required "
            f"proof pressure {required_proof:.1f} Pa (MEOP {meop_pa:.1f} Pa "
            f"× factor {proof_factor})."
        )
    if hold_duration_s < required_hold_s:
        findings.append(
            f"Hold duration {hold_duration_s:.1f} s is below the required "
            f"{required_hold_s:.1f} s."
        )
    if deformation_detected:
        findings.append(
            "Permanent deformation was observed during the proof pressure hold."
        )
    if leak_detected:
        findings.append(
            "Leakage was detected during the proof pressure hold."
        )

    return {"passed": len(findings) == 0, "findings": findings}


def check_pressure_cycling(
    cycles_completed: int,
    cycles_required: int,
    min_pressure_pa: float,
    max_pressure_pa: float,
    meop_pa: float,
    leak_detected: bool = False,
    deformation_detected: bool = False,
) -> dict:
    """
    Evaluate a pressure cycling test result.

    Returns a dict with:
      passed   -- True when all criteria are met
      findings -- list of strings describing each failed criterion
    """
    findings = []

    if min_pressure_pa < 0:
        findings.append(
            f"Min cycling pressure {min_pressure_pa:.1f} Pa must be >= 0."
        )
    if max_pressure_pa <= min_pressure_pa:
        findings.append(
            f"Max cycling pressure {max_pressure_pa:.1f} Pa must exceed "
            f"min cycling pressure {min_pressure_pa:.1f} Pa."
        )
    if cycles_completed < cycles_required:
        findings.append(
            f"Completed cycle count {cycles_completed} is below the required "
            f"{cycles_required} cycles."
        )
    if leak_detected:
        findings.append(
            "Leakage was detected during pressure cycling."
        )
    if deformation_detected:
        findings.append(
            "Permanent deformation was detected after pressure cycling."
        )

    return {"passed": len(findings) == 0, "findings": findings}


def check_burst_test(
    applied_pressure_pa: float,
    meop_pa: float,
    burst_occurred: bool = False,
    burst_factor: float = DEFAULT_BURST_FACTOR,
) -> dict:
    """
    Evaluate a design burst pressure test result.

    The item must sustain the design burst pressure without rupture.  A run
    where the applied pressure never reached the design burst pressure is
    inconclusive and is recorded as a finding.

    Returns a dict with:
      passed   -- True when all criteria are met
      findings -- list of strings describing each failed criterion
    """
    required_burst = compute_burst_pressure(meop_pa, burst_factor)
    findings = []

    if applied_pressure_pa < required_burst:
        findings.append(
            f"Applied pressure {applied_pressure_pa:.1f} Pa did not reach the "
            f"design burst pressure {required_burst:.1f} Pa (MEOP {meop_pa:.1f} Pa "
            f"× factor {burst_factor}); test result is inconclusive."
        )
    if burst_occurred:
        findings.append(
            "The item ruptured during the burst test, indicating insufficient "
            "structural margin at or below the design burst pressure."
        )

    return {"passed": len(findings) == 0, "findings": findings}


def check_leak_test(
    measured_leak_rate_pa_m3_s: float,
    allowable_leak_rate_pa_m3_s: float = DEFAULT_LEAK_RATE_LIMIT_PA_M3_S,
) -> dict:
    """
    Evaluate a leak test result.

    Returns a dict with:
      passed   -- True when the measured rate does not exceed the allowable
      findings -- list of strings describing each failed criterion
      margin   -- allowable minus measured (positive means within budget)
    """
    if allowable_leak_rate_pa_m3_s <= 0:
        raise PressureTestError(
            f"Allowable leak rate must be positive, got {allowable_leak_rate_pa_m3_s}"
        )

    findings = []
    margin = allowable_leak_rate_pa_m3_s - measured_leak_rate_pa_m3_s

    if measured_leak_rate_pa_m3_s > allowable_leak_rate_pa_m3_s:
        findings.append(
            f"Measured leak rate {measured_leak_rate_pa_m3_s:.3e} Pa·m³/s exceeds "
            f"the allowable {allowable_leak_rate_pa_m3_s:.3e} Pa·m³/s "
            f"(margin {margin:.3e} Pa·m³/s)."
        )

    return {
        "passed": len(findings) == 0,
        "findings": findings,
        "margin": margin,
    }


def run_pressure_test_sequence(meop_pa: float, test_results: dict) -> dict:
    """
    Orchestrate the full pressure test sequence for one element.

    test_results is a dict whose keys select which tests to run:
      "proof"   : {applied_pa, hold_s, required_hold_s, deformation (opt), leak (opt)}
      "cycling" : {cycles_done, cycles_req, min_pa, max_pa, leak (opt), deformation (opt)}
      "burst"   : {applied_pa, burst_occurred (opt)}
      "leak"    : {measured_pa_m3_s, allowable_pa_m3_s (opt)}

    Returns:
      overall_passed -- True only when every included test passed
      tests          -- dict mapping test name to its individual result dict
    """
    results = {}
    overall_pass = True

    if "proof" in test_results:
        p = test_results["proof"]
        r = check_proof_test(
            applied_pressure_pa=p["applied_pa"],
            meop_pa=meop_pa,
            hold_duration_s=p["hold_s"],
            required_hold_s=p["required_hold_s"],
            deformation_detected=p.get("deformation", False),
            leak_detected=p.get("leak", False),
        )
        results["proof"] = r
        if not r["passed"]:
            overall_pass = False

    if "cycling" in test_results:
        c = test_results["cycling"]
        r = check_pressure_cycling(
            cycles_completed=c["cycles_done"],
            cycles_required=c["cycles_req"],
            min_pressure_pa=c["min_pa"],
            max_pressure_pa=c["max_pa"],
            meop_pa=meop_pa,
            leak_detected=c.get("leak", False),
            deformation_detected=c.get("deformation", False),
        )
        results["cycling"] = r
        if not r["passed"]:
            overall_pass = False

    if "burst" in test_results:
        b = test_results["burst"]
        r = check_burst_test(
            applied_pressure_pa=b["applied_pa"],
            meop_pa=meop_pa,
            burst_occurred=b.get("burst_occurred", False),
        )
        results["burst"] = r
        if not r["passed"]:
            overall_pass = False

    if "leak" in test_results:
        lk = test_results["leak"]
        r = check_leak_test(
            measured_leak_rate_pa_m3_s=lk["measured_pa_m3_s"],
            allowable_leak_rate_pa_m3_s=lk.get(
                "allowable_pa_m3_s", DEFAULT_LEAK_RATE_LIMIT_PA_M3_S
            ),
        )
        results["leak"] = r
        if not r["passed"]:
            overall_pass = False

    return {"overall_passed": overall_pass, "tests": results}
