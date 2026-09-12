"""
Stress-free thermoelastic deformation check logic.

Implements the verification procedure described in ECSS-E-ST-32C §5.6
(paraphrased): a finite element model subjected to a uniform temperature
change with stress-free boundary conditions must produce negligible
stress residuals while nodal displacements match the expected free
thermal expansion α·ΔT·L.

Three checks are performed:
  1. Temperature uniformity — the applied thermal load must be spatially
     uniform across all elements before the stress check is valid.
  2. Element stress residual — each element's stress must be below the
     fraction of the characteristic thermoelastic stress scale E·α·|ΔT|.
  3. Displacement residual — each node's computed displacement must match
     the expected free-expansion displacement within a given tolerance.
"""

import math
from enum import Enum


class CheckStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"


# ---------------------------------------------------------------------------
# Data carriers (plain classes — no external dependencies)
# ---------------------------------------------------------------------------

class ElementData:
    """Input data for a single finite element."""

    def __init__(self, element_id, youngs_modulus, cte, delta_T,
                 stress_xx, stress_yy, stress_zz):
        self.element_id = element_id
        self.youngs_modulus = youngs_modulus   # [Pa]
        self.cte = cte                          # coefficient of thermal expansion [1/°C]
        self.delta_T = delta_T                  # applied temperature change [°C]
        self.stress_xx = stress_xx              # [Pa]
        self.stress_yy = stress_yy              # [Pa]
        self.stress_zz = stress_zz              # [Pa]


class NodeDisplacement:
    """Computed and expected displacement for a single node."""

    def __init__(self, node_id, dx, dy, dz,
                 expected_dx=0.0, expected_dy=0.0, expected_dz=0.0):
        self.node_id = node_id
        self.dx = dx                    # computed [m]
        self.dy = dy
        self.dz = dz
        self.expected_dx = expected_dx  # analytical free-expansion [m]
        self.expected_dy = expected_dy
        self.expected_dz = expected_dz


# ---------------------------------------------------------------------------
# Result carriers
# ---------------------------------------------------------------------------

class ElementStressResult:
    def __init__(self, element_id, max_stress, tolerance, ratio, status, message):
        self.element_id = element_id
        self.max_stress = max_stress
        self.tolerance = tolerance
        self.ratio = ratio
        self.status = status
        self.message = message


class DisplacementResult:
    def __init__(self, node_id, residual, tolerance, status, message):
        self.node_id = node_id
        self.residual = residual
        self.tolerance = tolerance
        self.status = status
        self.message = message


class TemperatureUniformityResult:
    def __init__(self, spread, tolerance, uniform, status, message):
        self.spread = spread
        self.tolerance = tolerance
        self.uniform = uniform
        self.status = status
        self.message = message


class ThermoelasticCheckSummary:
    def __init__(self, overall, temperature_result,
                 element_results, node_results,
                 failed_elements, failed_nodes):
        self.overall = overall
        self.temperature_result = temperature_result
        self.element_results = element_results
        self.node_results = node_results
        self.failed_elements = failed_elements
        self.failed_nodes = failed_nodes
        self.n_elements_checked = len(element_results)
        self.n_nodes_checked = len(node_results)
        self.n_elements_failed = len(failed_elements)
        self.n_nodes_failed = len(failed_nodes)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def compute_stress_tolerance(youngs_modulus, cte, delta_T, fraction=1e-6):
    """
    Return the stress threshold below which an element is considered
    stress-free: fraction × E × α × |ΔT|.

    When ΔT == 0 the expected stress is zero; return fraction × E as a
    numerical floor so the comparison remains well-defined.

    Raises ValueError for physically invalid inputs.
    """
    if youngs_modulus <= 0:
        raise ValueError(
            f"Young's modulus must be positive, got {youngs_modulus}"
        )
    if cte < 0:
        raise ValueError(
            f"CTE must be non-negative, got {cte}"
        )
    if fraction <= 0:
        raise ValueError(
            f"Fraction must be positive, got {fraction}"
        )
    if delta_T == 0:
        return fraction * youngs_modulus
    return fraction * youngs_modulus * abs(cte * delta_T)


def check_element_stress(element, fraction=1e-6):
    """
    Verify that the element stress residual is negligible relative to
    the characteristic thermoelastic stress scale E·α·|ΔT|.

    Returns an ElementStressResult with PASS or FAIL status.
    Raises ValueError for invalid element properties.
    """
    if element.youngs_modulus <= 0:
        raise ValueError(
            f"Element {element.element_id}: "
            f"Young's modulus must be positive, got {element.youngs_modulus}"
        )
    if element.cte < 0:
        raise ValueError(
            f"Element {element.element_id}: "
            f"CTE must be non-negative, got {element.cte}"
        )

    max_stress = max(
        abs(element.stress_xx),
        abs(element.stress_yy),
        abs(element.stress_zz),
    )

    tolerance = compute_stress_tolerance(
        element.youngs_modulus, element.cte, element.delta_T, fraction
    )

    if tolerance == 0.0:
        ratio = 0.0 if max_stress == 0.0 else float("inf")
    else:
        ratio = max_stress / tolerance

    if ratio <= 1.0:
        status = CheckStatus.PASS
        message = (
            f"Element {element.element_id}: stress-free check PASSED "
            f"(max_stress={max_stress:.3e} Pa, tolerance={tolerance:.3e} Pa, "
            f"ratio={ratio:.3e})"
        )
    else:
        status = CheckStatus.FAIL
        message = (
            f"Element {element.element_id}: stress-free check FAILED — "
            f"max_stress={max_stress:.3e} Pa exceeds tolerance={tolerance:.3e} Pa "
            f"(ratio={ratio:.3e}); check for CTE mismatch or spurious constraint"
        )

    return ElementStressResult(
        element_id=element.element_id,
        max_stress=max_stress,
        tolerance=tolerance,
        ratio=ratio,
        status=status,
        message=message,
    )


# max - min cannot represent an exact-boundary spread: for element
# temperatures 100.0 and 100.01 the subtraction yields
# 0.010000000000005116, i.e. 5.1e-15 ABOVE a 0.01 tolerance, so a load case
# sitting exactly on the allowed spread reads as FAIL. Absorb that IEEE-754
# representation error. This does not widen the engineering tolerance - a
# genuinely non-uniform field is orders of magnitude past it - and mirrors
# INTERACTION_TOLERANCE in local-yielding-and-buckling-functionality.
UNIFORMITY_REL_TOL = 1e-9
UNIFORMITY_ABS_TOL = 1e-12


def _within_tolerance(spread, tolerance):
    """True when spread is at or below tolerance, boundary included."""
    return spread <= tolerance or math.isclose(
        spread, tolerance, rel_tol=UNIFORMITY_REL_TOL, abs_tol=UNIFORMITY_ABS_TOL)


def check_temperature_uniformity(element_temperatures, tolerance=0.01):
    """
    Confirm that the applied temperature is uniform across all elements.

    element_temperatures: dict mapping element_id -> temperature [°C]
    tolerance: maximum allowed spread (max − min) in °C.

    Returns a TemperatureUniformityResult with PASS or FAIL.
    Raises ValueError if the mapping is empty.
    """
    if not element_temperatures:
        raise ValueError("element_temperatures must not be empty")

    temps = list(element_temperatures.values())
    t_min = min(temps)
    t_max = max(temps)
    spread = t_max - t_min

    if _within_tolerance(spread, tolerance):
        status = CheckStatus.PASS
        message = (
            f"Temperature uniformity PASSED "
            f"(spread={spread:.4f} °C <= tolerance={tolerance:.4f} °C)"
        )
        uniform = True
    else:
        status = CheckStatus.FAIL
        message = (
            f"Temperature uniformity FAILED — "
            f"spread={spread:.4f} °C exceeds tolerance={tolerance:.4f} °C; "
            f"correct the thermal load before evaluating stress residuals"
        )
        uniform = False

    return TemperatureUniformityResult(
        spread=spread,
        tolerance=tolerance,
        uniform=uniform,
        status=status,
        message=message,
    )


def check_displacement_residual(node, tolerance=1e-6):
    """
    Verify that the computed nodal displacement matches the expected
    free thermal expansion displacement within the given tolerance.

    tolerance: maximum allowed Euclidean residual [m].
    Returns a DisplacementResult with PASS or FAIL.
    """
    residual = (
        (node.dx - node.expected_dx) ** 2
        + (node.dy - node.expected_dy) ** 2
        + (node.dz - node.expected_dz) ** 2
    ) ** 0.5

    if residual <= tolerance:
        status = CheckStatus.PASS
        message = (
            f"Node {node.node_id}: displacement residual PASSED "
            f"(residual={residual:.3e} m <= tolerance={tolerance:.3e} m)"
        )
    else:
        status = CheckStatus.FAIL
        message = (
            f"Node {node.node_id}: displacement residual FAILED — "
            f"residual={residual:.3e} m exceeds tolerance={tolerance:.3e} m; "
            f"check for constraint interference or CTE inconsistency"
        )

    return DisplacementResult(
        node_id=node.node_id,
        residual=residual,
        tolerance=tolerance,
        status=status,
        message=message,
    )


def run_thermoelastic_check(
    elements,
    nodes,
    element_temperatures,
    stress_fraction=1e-6,
    displacement_tolerance=1e-6,
    temperature_tolerance=0.01,
):
    """
    Execute the full stress-free thermoelastic check per ECSS-E-ST-32C §5.6.

    Steps:
      1. Verify temperature uniformity.
      2. Check stress residual for each element.
      3. Check displacement residual for each node.
      4. Aggregate results.

    Returns a ThermoelasticCheckSummary.
    Raises ValueError if inputs are empty or physically invalid.
    """
    if not elements:
        raise ValueError("elements list must not be empty")
    if not nodes:
        raise ValueError("nodes list must not be empty")

    temp_result = check_temperature_uniformity(
        element_temperatures, temperature_tolerance
    )

    element_results = [
        check_element_stress(e, stress_fraction) for e in elements
    ]

    node_results = [
        check_displacement_residual(n, displacement_tolerance) for n in nodes
    ]

    failed_elements = [r for r in element_results if r.status == CheckStatus.FAIL]
    failed_nodes = [r for r in node_results if r.status == CheckStatus.FAIL]

    all_pass = (
        temp_result.status == CheckStatus.PASS
        and not failed_elements
        and not failed_nodes
    )

    return ThermoelasticCheckSummary(
        overall=CheckStatus.PASS if all_pass else CheckStatus.FAIL,
        temperature_result=temp_result,
        element_results=element_results,
        node_results=node_results,
        failed_elements=failed_elements,
        failed_nodes=failed_nodes,
    )
