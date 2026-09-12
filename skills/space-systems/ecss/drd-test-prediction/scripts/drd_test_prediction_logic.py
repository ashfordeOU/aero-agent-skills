"""
Test prediction logic for ECSS-E-ST-32C Annex Q (DRD-TP).

Implements deterministic checks for structural test prediction reports:
  - test case validation (load factor bounds, direction)
  - linear scaling of FEM baseline predictions
  - safety-abort threshold computation
  - instrument measurement-range checks
  - analysis-to-test correlation band computation
  - full report assembly

stdlib only -- no external dependencies.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

# Recognised structural load directions (ECSS axes convention + generic types)
VALID_DIRECTIONS: frozenset = frozenset({
    "X", "Y", "Z", "-X", "-Y", "-Z",
    "lateral", "axial", "random", "acoustic",
})

# Test load factor bounds per E-ST-32C structural qualification envelope
LOAD_FACTOR_MIN: float = 0.0   # exclusive lower bound
LOAD_FACTOR_MAX: float = 2.0   # inclusive upper bound

# Default abort margin applied over predicted absolute peak (20 % above peak)
DEFAULT_ABORT_MARGIN: float = 1.20

# Default correlation acceptance band (±% of predicted value)
DEFAULT_CORRELATION_BAND_PCT: float = 10.0


@dataclass
class TestCase:
    """One test load case (a specific load factor applied in a given direction)."""
    case_id: str
    load_factor: float
    direction: str


@dataclass
class BaselinePrediction:
    """FEM prediction at unit load factor for one quantity at one monitoring point."""
    test_point_id: str
    quantity: str   # e.g. "displacement_mm", "force_N", "stress_MPa", "frequency_Hz"
    value: float    # signed value at load_factor = 1.0


@dataclass
class InstrumentRange:
    """Full-scale measurement range of the instrument assigned to a monitoring point/quantity."""
    test_point_id: str
    quantity: str
    max_measurable: float   # positive upper bound of the instrument range


@dataclass
class ValidationError:
    """Structured finding from any validation step."""
    code: str
    message: str


@dataclass
class PredictedPoint:
    """Assembled prediction for one monitoring point/quantity within one test case."""
    test_point_id: str
    quantity: str
    predicted_value: float
    abort_threshold: float
    correlation_lower: float
    correlation_upper: float
    instrument_ok: bool


# ---------------------------------------------------------------------------
# Primitive checks
# ---------------------------------------------------------------------------

def validate_test_case(tc: TestCase) -> List[ValidationError]:
    """Return validation errors for a test case; empty list means valid."""
    errors: List[ValidationError] = []
    if tc.load_factor <= LOAD_FACTOR_MIN:
        errors.append(ValidationError(
            code="INVALID_LOAD_FACTOR",
            message=(
                f"Case '{tc.case_id}': load_factor must be > {LOAD_FACTOR_MIN},"
                f" got {tc.load_factor}"
            ),
        ))
    if tc.load_factor > LOAD_FACTOR_MAX:
        errors.append(ValidationError(
            code="LOAD_FACTOR_EXCEEDS_MAX",
            message=(
                f"Case '{tc.case_id}': load_factor {tc.load_factor} exceeds"
                f" maximum {LOAD_FACTOR_MAX}"
            ),
        ))
    if tc.direction not in VALID_DIRECTIONS:
        errors.append(ValidationError(
            code="INVALID_DIRECTION",
            message=(
                f"Case '{tc.case_id}': direction '{tc.direction}'"
                f" not in {sorted(VALID_DIRECTIONS)}"
            ),
        ))
    return errors


def scale_prediction(base_value: float, load_factor: float) -> float:
    """Scale a FEM baseline prediction by the test load factor (linear FEM assumption)."""
    if load_factor < 0:
        raise ValueError(
            f"load_factor must be non-negative, got {load_factor}"
        )
    return base_value * load_factor


def compute_abort_threshold(predicted_peak: float, margin: float = DEFAULT_ABORT_MARGIN) -> float:
    """
    Return the abort threshold = predicted_peak * margin.

    predicted_peak must be non-negative (pass abs() before calling).
    margin must be strictly greater than 1.0.
    """
    if margin <= 1.0:
        raise ValueError(f"Abort margin must be > 1.0, got {margin}")
    if predicted_peak < 0:
        raise ValueError(f"predicted_peak must be non-negative, got {predicted_peak}")
    return predicted_peak * margin


def check_abort_threshold(predicted: float, abort_limit: float) -> bool:
    """Return True if predicted response is strictly below the abort limit."""
    if abort_limit <= 0:
        raise ValueError(f"abort_limit must be > 0, got {abort_limit}")
    return predicted < abort_limit


def check_instrument_range(
    predicted: float, instrument: InstrumentRange
) -> Optional[ValidationError]:
    """
    Return a ValidationError when the predicted value exceeds the instrument range.

    predicted must be non-negative (pass abs() before calling).
    Returns None when the instrument can cover the predicted value.
    """
    if predicted > instrument.max_measurable:
        return ValidationError(
            code="INSTRUMENT_OVERRANGE",
            message=(
                f"Point '{instrument.test_point_id}' {instrument.quantity}:"
                f" predicted {predicted:.4g} exceeds instrument range"
                f" {instrument.max_measurable:.4g}"
            ),
        )
    return None


def compute_correlation_band(
    predicted: float,
    band_pct: float = DEFAULT_CORRELATION_BAND_PCT,
) -> Tuple[float, float]:
    """
    Return (lower, upper) acceptance bounds around a predicted value.

    band_pct must be in the open interval (0, 100).
    predicted must be non-negative.
    """
    if band_pct <= 0 or band_pct >= 100:
        raise ValueError(f"band_pct must be in (0, 100), got {band_pct}")
    if predicted < 0:
        raise ValueError(f"predicted must be non-negative, got {predicted}")
    factor = band_pct / 100.0
    return (predicted * (1.0 - factor), predicted * (1.0 + factor))


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def build_test_prediction(
    test_cases: List[TestCase],
    base_predictions: List[BaselinePrediction],
    instrument_ranges: List[InstrumentRange],
    abort_margin: float = DEFAULT_ABORT_MARGIN,
    correlation_band_pct: float = DEFAULT_CORRELATION_BAND_PCT,
) -> Dict:
    """
    Assemble the full test prediction report structure.

    Returns:
        {
            "errors":  list[ValidationError]   -- all findings (invalid inputs,
                       overrange, missing instrument definitions)
            "results": dict[case_id -> list[PredictedPoint]]  -- one entry per
                       valid test case; absent for rejected cases
        }
    """
    errors: List[ValidationError] = []
    results: Dict[str, List[PredictedPoint]] = {}

    # Index instrument ranges for O(1) lookup by (test_point_id, quantity)
    range_index: Dict[Tuple[str, str], InstrumentRange] = {
        (ir.test_point_id, ir.quantity): ir for ir in instrument_ranges
    }

    for tc in test_cases:
        tc_errors = validate_test_case(tc)
        if tc_errors:
            errors.extend(tc_errors)
            continue  # skip prediction for invalid cases

        case_points: List[PredictedPoint] = []
        for bp in base_predictions:
            predicted = scale_prediction(bp.value, tc.load_factor)
            abs_predicted = abs(predicted)

            abort = compute_abort_threshold(abs_predicted, abort_margin)
            lo, hi = compute_correlation_band(abs_predicted, correlation_band_pct)

            ir = range_index.get((bp.test_point_id, bp.quantity))
            if ir is None:
                errors.append(ValidationError(
                    code="MISSING_INSTRUMENT_RANGE",
                    message=(
                        f"No instrument range defined for point '{bp.test_point_id}'"
                        f" quantity '{bp.quantity}'"
                    ),
                ))
                instrument_ok = False
            else:
                range_error = check_instrument_range(abs_predicted, ir)
                if range_error is not None:
                    errors.append(range_error)
                instrument_ok = range_error is None

            case_points.append(PredictedPoint(
                test_point_id=bp.test_point_id,
                quantity=bp.quantity,
                predicted_value=predicted,
                abort_threshold=abort,
                correlation_lower=lo,
                correlation_upper=hi,
                instrument_ok=instrument_ok,
            ))

        results[tc.case_id] = case_points

    return {"errors": errors, "results": results}
