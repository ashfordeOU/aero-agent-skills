"""
Alignment, dimensional-stability, and geometry-control logic.
Implements checks for ECSS-E-ST-32C clauses 4.6.3.19–4.6.3.21.
Stdlib only — no external dependencies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any

# Recognised axis identifiers: rotational (arcsec) and translational (mm).
ROTATIONAL_AXES = {"rx", "ry", "rz"}
TRANSLATIONAL_AXES = {"tx", "ty", "tz"}
KNOWN_AXES = ROTATIONAL_AXES | TRANSLATIONAL_AXES

# Recognised dimensional-stability drivers (clause 4.6.3.20).
KNOWN_DRIVERS = {"thermal", "hygroscopic", "creep", "other"}

# Recognised geometry form types (clause 4.6.3.21).
KNOWN_GEOMETRY_TYPES = {
    "flatness",
    "straightness",
    "circularity",
    "cylindricity",
    "parallelism",
    "perpendicularity",
    "angularity",
    "runout",
}


class CheckStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"   # input data problem — must be resolved before results are used


@dataclass
class AlignmentMeasurement:
    """Single-axis alignment measurement for one component."""
    component_id: str
    axis: str              # one of KNOWN_AXES
    measured_value: float  # arcsec for rotational, mm for translational
    allowable_tolerance: float  # symmetric half-band, same unit; must be > 0
    unit: str              # "arcsec" or "mm"

    def check(self) -> Dict[str, Any]:
        if self.axis not in KNOWN_AXES:
            return {
                "status": CheckStatus.ERROR,
                "reason": f"Unknown axis '{self.axis}' for component '{self.component_id}'",
            }
        if self.allowable_tolerance <= 0:
            return {
                "status": CheckStatus.ERROR,
                "reason": (
                    f"Non-positive tolerance {self.allowable_tolerance} {self.unit} "
                    f"for '{self.component_id}/{self.axis}' — resolve against ICD before checking"
                ),
            }
        margin = self.allowable_tolerance - abs(self.measured_value)
        if margin >= 0:
            return {"status": CheckStatus.PASS, "margin": margin, "unit": self.unit}
        return {
            "status": CheckStatus.FAIL,
            "exceedance": abs(margin),
            "unit": self.unit,
            "reason": (
                f"Measured |{self.measured_value}| {self.unit} exceeds allowable "
                f"±{self.allowable_tolerance} {self.unit} on axis '{self.axis}'"
            ),
        }


@dataclass
class DimensionalStabilityMeasurement:
    """Dimensional change measurement for one component and one driver."""
    component_id: str
    baseline_dimension: float   # mm, reference pre-environment value
    measured_dimension: float   # mm, post-environment value
    stability_budget: float     # mm, maximum allowable absolute change; must be > 0
    driver: str                 # one of KNOWN_DRIVERS

    def check(self) -> Dict[str, Any]:
        if self.driver not in KNOWN_DRIVERS:
            return {
                "status": CheckStatus.ERROR,
                "reason": (
                    f"Unknown driver '{self.driver}' for '{self.component_id}' — "
                    f"must be one of {sorted(KNOWN_DRIVERS)}"
                ),
            }
        if self.stability_budget <= 0:
            return {
                "status": CheckStatus.ERROR,
                "reason": (
                    f"Non-positive stability budget {self.stability_budget} mm "
                    f"for '{self.component_id}' — resolve against ICD before checking"
                ),
            }
        delta = abs(self.measured_dimension - self.baseline_dimension)
        margin = self.stability_budget - delta
        if margin >= 0:
            return {
                "status": CheckStatus.PASS,
                "dimensional_change_mm": delta,
                "margin_mm": margin,
                "driver": self.driver,
            }
        return {
            "status": CheckStatus.FAIL,
            "dimensional_change_mm": delta,
            "exceedance_mm": abs(margin),
            "driver": self.driver,
            "reason": (
                f"Dimensional change {delta:.6f} mm exceeds stability budget "
                f"{self.stability_budget} mm for '{self.component_id}' (driver: {self.driver})"
            ),
        }


@dataclass
class GeometryControlMeasurement:
    """Single geometry-form deviation measurement for one component."""
    component_id: str
    geometry_type: str         # one of KNOWN_GEOMETRY_TYPES
    measured_deviation: float  # mm, non-negative magnitude
    allowable_deviation: float # mm, must be > 0

    def check(self) -> Dict[str, Any]:
        if self.geometry_type not in KNOWN_GEOMETRY_TYPES:
            return {
                "status": CheckStatus.ERROR,
                "reason": (
                    f"Unknown geometry type '{self.geometry_type}' for '{self.component_id}' — "
                    f"must be one of {sorted(KNOWN_GEOMETRY_TYPES)}"
                ),
            }
        if self.allowable_deviation <= 0:
            return {
                "status": CheckStatus.ERROR,
                "reason": (
                    f"Non-positive allowable deviation {self.allowable_deviation} mm "
                    f"for '{self.component_id}/{self.geometry_type}'"
                ),
            }
        if self.measured_deviation < 0:
            return {
                "status": CheckStatus.ERROR,
                "reason": (
                    f"Negative measured deviation {self.measured_deviation} mm for "
                    f"'{self.component_id}/{self.geometry_type}' — form error is a magnitude"
                ),
            }
        margin = self.allowable_deviation - self.measured_deviation
        if margin >= 0:
            return {"status": CheckStatus.PASS, "margin_mm": margin}
        return {
            "status": CheckStatus.FAIL,
            "exceedance_mm": abs(margin),
            "reason": (
                f"Form deviation {self.measured_deviation} mm exceeds allowable "
                f"{self.allowable_deviation} mm for '{self.component_id}/{self.geometry_type}'"
            ),
        }


def run_alignment_checks(measurements: List[AlignmentMeasurement]) -> List[Dict[str, Any]]:
    """Return per-axis check results for every alignment measurement."""
    results = []
    for m in measurements:
        result = m.check()
        results.append(
            {"component_id": m.component_id, "axis": m.axis, "check_type": "alignment", **result}
        )
    return results


def run_dimensional_stability_checks(
    measurements: List[DimensionalStabilityMeasurement],
) -> List[Dict[str, Any]]:
    """Return per-driver check results for every dimensional stability measurement."""
    results = []
    for m in measurements:
        result = m.check()
        results.append(
            {"component_id": m.component_id, "driver": m.driver, "check_type": "dimensional_stability", **result}
        )
    return results


def run_geometry_control_checks(
    measurements: List[GeometryControlMeasurement],
) -> List[Dict[str, Any]]:
    """Return per-form-type check results for every geometry control measurement."""
    results = []
    for m in measurements:
        result = m.check()
        results.append(
            {
                "component_id": m.component_id,
                "geometry_type": m.geometry_type,
                "check_type": "geometry_control",
                **result,
            }
        )
    return results


def aggregate_compliance(
    alignment_results: List[Dict[str, Any]],
    stability_results: List[Dict[str, Any]],
    geometry_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Combine results from all three check types into a single compliance summary.
    Status is PASS only when there are zero failures and zero errors across all checks.
    """
    all_results = alignment_results + stability_results + geometry_results
    failures = [r for r in all_results if r["status"] == CheckStatus.FAIL]
    errors = [r for r in all_results if r["status"] == CheckStatus.ERROR]
    passes = [r for r in all_results if r["status"] == CheckStatus.PASS]

    if errors:
        overall = CheckStatus.ERROR
    elif failures:
        overall = CheckStatus.FAIL
    else:
        overall = CheckStatus.PASS

    return {
        "overall_status": overall,
        "total_checks": len(all_results),
        "passed": len(passes),
        "failed": len(failures),
        "errors": len(errors),
        "failures": failures,
        "input_errors": errors,
    }
