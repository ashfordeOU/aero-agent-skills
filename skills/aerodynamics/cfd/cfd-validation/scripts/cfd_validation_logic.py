#!/usr/bin/env python3
"""CFD validation logic (pure Python 3, stdlib only).

Implements the validation workflow of AIAA G-077-1998 and ASME V&V 20-2009
at the level of a leaf utility module:

  - select_validation_case: pick the reference case for a flow regime and
    application (NACA 0012 / NACA 4412 airfoil, ONERA M6 transonic wing,
    DLR-F6 transport wing-body, zero-pressure-gradient flat plate).
  - relative_error / rms_error / max_error: comparison metrics for
    integrated quantities and distributed (Cp, Cf) data.
  - richardson_extrapolation: 3-mesh grid convergence sanity check with
    apparent order and Roache grid convergence index.
  - validation_verdict: PASS/FAIL against a tolerance band.
  - validation_uncertainty: U_val combined in quadrature from error sources.
  - report_skeleton: markdown skeleton of a validation report.

All functions are deterministic, offline and raise ValueError on invalid
input. Contract test: scripts/test_cfd_validation.py.
"""

import math

# ---------------------------------------------------------------------------
# Validation case catalog
# ---------------------------------------------------------------------------

VALIDATION_CASES = {
    "naca-0012": {
        "case_id": "naca-0012",
        "name": "NACA 0012 airfoil",
        "regime": "incompressible",
        "application": "airfoil",
        "conditions": {"mach": 0.30, "reynolds": 6.0e6, "alpha_deg": 0.0},
        "reference": {"cd": 0.0081, "cl": 0.0},
        "data_source": "NACA TR 824 (Abbott and von Doenhoff) classic 2D section data; "
                       "Cd ~ 0.0081 at M=0.30, Re=6e6 is the classic validation anchor",
        "quantities": ["cd", "cl", "cp"],
    },
    "naca-4412": {
        "case_id": "naca-4412",
        "name": "NACA 4412 airfoil (cambered)",
        "regime": "incompressible",
        "application": "airfoil",
        "conditions": {"mach": 0.15, "reynolds": 3.1e6, "alpha_deg": 0.0},
        "reference": {"cd": 0.0090, "cl": 0.24},
        "data_source": "NACA TR 824 cambered section data; nominal values at Re=3.1e6, "
                       "confirm from the primary data sheet before judging",
        "quantities": ["cl", "cd", "cp"],
    },
    "onera-m6": {
        "case_id": "onera-m6",
        "name": "ONERA M6 wing",
        "regime": "transonic",
        "application": "wing",
        "conditions": {"mach": 0.84, "reynolds": 11.72e6, "alpha_deg": 3.06},
        "reference": {"cd": 0.0163, "cl": 0.266},
        "data_source": "AGARD-AR-138 (Schmitt and Charpin, 1979) ONERA M6 wing pressure "
                       "data; nominal CL/CD at M=0.84, Re=11.72e6, alpha=3.06 deg",
        "quantities": ["cp", "cd", "cl"],
    },
    "dlr-f6": {
        "case_id": "dlr-f6",
        "name": "DLR-F6 wing-body transport",
        "regime": "transonic",
        "application": "wing-body",
        "conditions": {"mach": 0.75, "reynolds": 3.0e6, "cl_target": 0.5},
        "reference": {"cd": 0.0299, "cl": 0.5},
        "data_source": "DLR-F6 wing-body, AIAA Drag Prediction Workshop series; "
                       "nominal CD ~ 0.0299 at CL=0.5, M=0.75, Re=3e6 (participant mean)",
        "quantities": ["cd", "cl", "cp"],
    },
    "flat-plate": {
        "case_id": "flat-plate",
        "name": "Zero-pressure-gradient flat plate",
        "regime": "incompressible",
        "application": "flat-plate",
        "conditions": {"flow": "zero pressure gradient, smooth wall", "reference_length": "Rex-based"},
        "reference": {
            "cf_laminar": 1.328 / math.sqrt(1.0e6),
            "cf_turbulent": 0.074 * (1.0e6 ** -0.2),
            "formula_laminar": "Cf = 1.328 / sqrt(Rex) (Blasius solution)",
            "formula_turbulent": "Cf = 0.074 / Rex^0.2 (Schlichting average skin friction)",
        },
        "data_source": "Blasius laminar boundary layer solution and Schlichting "
                       "turbulent skin friction correlation, zero-pressure-gradient flat plate",
        "quantities": ["cf", "u_e", "delta_star"],
    },
}

# (regime, application) -> primary case id. Aliases are normalized first.
_CASE_ROUTES = {
    ("incompressible", "airfoil"): "naca-0012",
    ("subsonic", "airfoil"): "naca-0012",
    ("incompressible", "flat-plate"): "flat-plate",
    ("boundary-layer", "flat-plate"): "flat-plate",
    ("transonic", "wing"): "onera-m6",
    ("transonic", "wing-body"): "dlr-f6",
    ("transport", "wing-body"): "dlr-f6",
    ("transport", "wing"): "dlr-f6",
}

_ALTERNATIVES = {
    "naca-0012": ["naca-4412"],
    "naca-4412": ["naca-0012"],
    "onera-m6": [],
    "dlr-f6": [],
    "flat-plate": [],
}

_REGIME_ALIASES = {
    "low-speed": "incompressible",
    "low speed": "incompressible",
    "lowspeed": "incompressible",
    "subsonic": "incompressible",
    "boundary-layer": "boundary-layer",
    "boundary layer": "boundary-layer",
    "flat-plate": "flat-plate",
    "flat plate": "flat-plate",
    "transport": "transport",
    "transonic": "transonic",
}

_APPLICATION_ALIASES = {
    "2d-airfoil": "airfoil",
    "2d airfoil": "airfoil",
    "airfoil": "airfoil",
    "airfoil-section": "airfoil",
    "airfoil section": "airfoil",
    "wing": "wing",
    "3d-wing": "wing",
    "3d wing": "wing",
    "wing-body": "wing-body",
    "wing body": "wing-body",
    "wingbody": "wing-body",
    "transport": "wing-body",
    "flat-plate": "flat-plate",
    "flat plate": "flat-plate",
    "boundary-layer": "flat-plate",
    "boundary layer": "flat-plate",
}


def _norm_regime(flow_regime):
    key = str(flow_regime).strip().lower()
    return _REGIME_ALIASES.get(key, key)


def _norm_application(application):
    key = str(application).strip().lower()
    return _APPLICATION_ALIASES.get(key, key)


def select_validation_case(flow_regime, application):
    """Return the reference validation case dict for a flow regime + application.

    Supported routes (see _CASE_ROUTES):
      incompressible + airfoil        -> NACA 0012 (alt: NACA 4412)
      incompressible + flat-plate     -> zero-pressure-gradient flat plate
      boundary-layer + flat-plate     -> zero-pressure-gradient flat plate
      transonic + wing                -> ONERA M6
      transonic/transport + wing-body -> DLR-F6

    Raises ValueError for an unsupported regime/application combination or
    for empty/blank inputs.
    """
    regime = _norm_regime(flow_regime)
    application = _norm_application(application)
    if not regime or not application:
        raise ValueError("flow_regime and application must be non-empty")
    route = (regime, application)
    if route not in _CASE_ROUTES:
        supported = ", ".join(
            "%s + %s" % (r, a) for (r, a) in sorted(_CASE_ROUTES)
        )
        raise ValueError(
            "no validation case for regime '%s' with application '%s'; "
            "supported: %s" % (regime, application, supported)
        )
    case_id = _CASE_ROUTES[route]
    case = dict(VALIDATION_CASES[case_id])
    case["alternatives"] = list(_ALTERNATIVES.get(case_id, []))
    return case


# ---------------------------------------------------------------------------
# Comparison metrics
# ---------------------------------------------------------------------------

def _require_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))


def relative_error(computed, reference):
    """Relative error |computed - reference| / |reference| as a fraction.

    Raises ValueError when reference is zero or inputs are not numeric.
    """
    _require_number(computed, "computed")
    _require_number(reference, "reference")
    if reference == 0.0:
        raise ValueError("relative_error undefined for zero reference; use mode='absolute'")
    return abs(computed - reference) / abs(reference)


def _require_distributions(computed_seq, reference_seq):
    if len(computed_seq) != len(reference_seq):
        raise ValueError(
            "computed and reference sequences must have equal length "
            "(%d vs %d)" % (len(computed_seq), len(reference_seq))
        )
    if len(computed_seq) == 0:
        raise ValueError("sequences must be non-empty")
    for i, (c, r) in enumerate(zip(computed_seq, reference_seq)):
        _require_number(c, "computed[%d]" % i)
        _require_number(r, "reference[%d]" % i)


def rms_error(computed_seq, reference_seq):
    """RMS error over a distribution: sqrt(mean((c - r)^2))."""
    _require_distributions(computed_seq, reference_seq)
    n = len(computed_seq)
    total = 0.0
    for c, r in zip(computed_seq, reference_seq):
        d = c - r
        total += d * d
    return math.sqrt(total / n)


def max_error(computed_seq, reference_seq):
    """Maximum local error over a distribution: max(|c - r|)."""
    _require_distributions(computed_seq, reference_seq)
    return max(abs(c - r) for c, r in zip(computed_seq, reference_seq))


# ---------------------------------------------------------------------------
# Richardson extrapolation (grid convergence sanity)
# ---------------------------------------------------------------------------

def richardson_extrapolation(values, refinement_ratio=2.0):
    """3-mesh Richardson extrapolation.

    values: [finest, medium, coarsest] solution values on meshes with
    constant refinement ratio h2/h1 = h3/h2 = refinement_ratio.

    Returns dict with apparent order p, the extrapolated (infinite-grid)
    value, and Roache's grid convergence index (GCI, safety factor 1.25):

      p        = ln((f3-f2)/(f2-f1)) / ln(r)
      f_exact  = f1 + (f1 - f2) / (r^p - 1)
      GCI      = 1.25 * |f1 - f2| / (r^p - 1)

    Raises ValueError for wrong length, non-monotone data, zero mesh-to-mesh
    change, or refinement_ratio <= 1.
    """
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        raise ValueError("richardson_extrapolation needs exactly 3 values (finest, medium, coarsest)")
    for i, v in enumerate(values):
        _require_number(v, "values[%d]" % i)
    _require_number(refinement_ratio, "refinement_ratio")
    if refinement_ratio <= 1.0:
        raise ValueError("refinement_ratio must be > 1, got %r" % (refinement_ratio,))
    f1, f2, f3 = (float(v) for v in values)
    e12 = f2 - f1
    e23 = f3 - f2
    if e12 == 0.0 or e23 == 0.0:
        raise ValueError("zero change between mesh levels; grid convergence not meaningful")
    if e12 * e23 <= 0.0:
        raise ValueError(
            "non-monotone mesh sequence (f3-f2 and f2-f1 must share sign); "
            "Richardson extrapolation is not valid"
        )
    ratio = e23 / e12
    if ratio <= 0.0:
        raise ValueError("non-monotone mesh sequence; Richardson extrapolation is not valid")
    p = math.log(ratio) / math.log(refinement_ratio)
    denom = refinement_ratio ** p - 1.0
    # f_exact = f1 + (f1 - f2) / (r^p - 1) = f1 - e12 / (r^p - 1)
    extrapolated = f1 - e12 / denom
    gci = 1.25 * abs(e12) / denom
    return {
        "apparent_order": p,
        "extrapolated": extrapolated,
        "gci": gci,
        "finest_value": f1,
        "refinement_ratio": float(refinement_ratio),
        "monotone": True,
    }


# ---------------------------------------------------------------------------
# Validation verdict
# ---------------------------------------------------------------------------

def validation_verdict(computed, reference, tolerance=0.05, mode="relative"):
    """Judge a computed quantity against a reference within a tolerance band.

    mode 'relative' (default): error = |c - r| / |r|, reference must be non-zero.
    mode 'absolute':           error = |c - r|.

    Returns {"passed": bool, "metric": str, "error": float, "tolerance": float,
             "verdict": "PASS"|"FAIL", "margin": tolerance - error}.
    Raises ValueError for tolerance <= 0, unknown mode, zero reference in
    relative mode, or non-numeric inputs.
    """
    _require_number(computed, "computed")
    _require_number(reference, "reference")
    _require_number(tolerance, "tolerance")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be > 0, got %r" % (tolerance,))
    if mode not in ("relative", "absolute"):
        raise ValueError("mode must be 'relative' or 'absolute', got %r" % (mode,))
    if mode == "relative":
        if reference == 0.0:
            raise ValueError("relative verdict undefined for zero reference; use mode='absolute'")
        error = abs(computed - reference) / abs(reference)
    else:
        error = abs(computed - reference)
    passed = error <= tolerance
    return {
        "passed": passed,
        "metric": "%s-error" % mode,
        "error": error,
        "tolerance": float(tolerance),
        "verdict": "PASS" if passed else "FAIL",
        "margin": float(tolerance) - error,
    }


# ---------------------------------------------------------------------------
# Validation uncertainty
# ---------------------------------------------------------------------------

def validation_uncertainty(sources):
    """Combine validation error sources into U_val by quadrature.

    sources: dict {source_name: magnitude} or iterable of (name, magnitude).
    Magnitudes are standard uncertainties (same units as the quantity).

    Returns {"u_val": sqrt(sum u_i^2), "sources": {...}, "dominant": name}.
    Raises ValueError for empty input, negative or non-numeric magnitudes.
    """
    if isinstance(sources, dict):
        items = list(sources.items())
    elif isinstance(sources, (list, tuple)):
        items = list(sources)
    else:
        raise ValueError("sources must be a dict or a list of (name, magnitude) pairs")
    if not items:
        raise ValueError("sources must not be empty")
    out = {}
    total = 0.0
    for name, magnitude in items:
        _require_number(magnitude, "magnitude of %r" % (name,))
        if magnitude < 0.0:
            raise ValueError("uncertainty magnitude must be >= 0, got %r" % (magnitude,))
        out[str(name)] = float(magnitude)
        total += float(magnitude) ** 2
    u_val = math.sqrt(total)
    dominant = max(out, key=lambda k: out[k])
    return {"u_val": u_val, "sources": out, "dominant": dominant}


# ---------------------------------------------------------------------------
# Validation report skeleton
# ---------------------------------------------------------------------------

def report_skeleton(case, metrics=None, verdict=None, uncertainty=None):
    """Build a markdown validation report skeleton (deterministic, offline).

    case: dict from select_validation_case (or a case id string).
    metrics: optional dict of {quantity: value} to tabulate.
    verdict: optional dict from validation_verdict.
    uncertainty: optional dict from validation_uncertainty.

    Returns a multi-section markdown string. Raises ValueError for a case
    that is neither a known case id nor a dict with case_id.
    """
    if isinstance(case, str):
        case_id = case
        if case_id not in VALIDATION_CASES:
            raise ValueError("unknown case id %r" % (case_id,))
        case = VALIDATION_CASES[case_id]
    if not isinstance(case, dict) or "case_id" not in case:
        raise ValueError("case must be a dict from select_validation_case or a known case id")

    name = case.get("name", case["case_id"])
    conditions = case.get("conditions", {})
    reference = case.get("reference", {})
    data_source = case.get("data_source", "")

    lines = ["# CFD Validation Report", ""]
    lines.append("## Case")
    lines.append("- Case: %s (%s)" % (name, case["case_id"]))
    lines.append("- Regime: %s, application: %s" % (case.get("regime", "?"), case.get("application", "?")))
    lines.append("")
    lines.append("## Test Conditions")
    for key, value in conditions.items():
        lines.append("- %s: %s" % (key, value))
    lines.append("")
    lines.append("## Reference Data")
    for key, value in reference.items():
        lines.append("- %s: %s" % (key, value))
    if data_source:
        lines.append("- Source: %s" % data_source)
    lines.append("")

    lines.append("## Comparison Metrics")
    if metrics:
        for key, value in metrics.items():
            lines.append("- %s: %s" % (key, value))
    else:
        lines.append("- (add relative_error, rms_error, max_error values here)")
    lines.append("")

    lines.append("## Verdict")
    if verdict:
        lines.append(
            "- %s: error %s vs tolerance %s (margin %s)"
            % (verdict.get("verdict", "?"), verdict.get("error", "?"),
               verdict.get("tolerance", "?"), verdict.get("margin", "?"))
        )
    else:
        lines.append("- (add validation_verdict output here)")
    lines.append("")

    lines.append("## Validation Uncertainty")
    if uncertainty:
        lines.append("- U_val: %s (dominant source: %s)" % (uncertainty.get("u_val", "?"), uncertainty.get("dominant", "?")))
    else:
        lines.append("- (add validation_uncertainty output here)")
    lines.append("")

    lines.append("## Validation Workflow")
    lines.append("1. Select the reference case for the flow regime and application.")
    lines.append("2. Run the CFD analysis on at least three mesh levels.")
    lines.append("3. Compute comparison metrics against the reference data.")
    lines.append("4. Check grid convergence with Richardson extrapolation.")
    lines.append("5. Judge the verdict against the tolerance band.")
    lines.append("6. Combine error sources into U_val and document assumptions.")
    lines.append("")

    lines.append("## Conclusions")
    lines.append("- (state whether the code is validated for this application and within which band)")
    lines.append("")
    lines.append("## References")
    lines.append("- %s" % (data_source if data_source else "(reference data source)"))
    lines.append("- AIAA G-077-1998 Guide for the Verification and Validation of CFD Simulations")
    lines.append("- ASME V&V 20-2009 Standard for Verification and Validation in CFD and Heat Transfer")
    lines.append("")
    return "\n".join(lines)
