"""Qualification methods and generic performance demonstration.

Anchor: ECSS-E-ST-31-02C clauses 5.5.3, 5.5.4 and 5.5.5.1 (the verification
methods a qualification requirement may be closed by, and the generic
performance demonstration every two-phase heat transport item owes: survival
of the worst mechanical loads, safe-life or fatigue substantiation, and a
leak-before-burst pressure boundary). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Allocate a verification method to each requirement from its kind and its
   criticality, and grade the proposed allocation against it on a strength
   ordering, so a weaker method than the requirement warrants is a finding.
2. Size the worst-case mechanical design load from the limit load and the
   design factor, and reduce the allowable against it to a margin of safety.
3. Grade a safe-life or fatigue demonstration: the demonstrated cycle count
   has to cover the service life multiplied by the scatter factor.
4. Grade the leak-before-burst property of the pressure boundary: the critical
   flaw depth implied by the fracture toughness and the hoop stress has to
   exceed the wall thickness, so a growing flaw vents the item before it
   destabilises.
5. Aggregate the three into one generic-performance verdict with the findings
   that produced it.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "METHOD_STRENGTH",
    "REQUIREMENT_KINDS",
    "VERIFICATION_METHODS",
    "allocate_method",
    "grade_method_allocation",
    "design_load",
    "margin_of_safety",
    "worst_case_load_case",
    "safe_life_demonstration",
    "hoop_stress",
    "critical_flaw_depth",
    "leak_before_burst",
    "assess_generic_performance",
]

# Margins and ratios are differences and quotients of engineering figures that
# frequently land exactly on their limit. Absorb the representation error of
# the comparison here, never the limit itself.
MARGIN_TOLERANCE = 1e-9

VERIFICATION_METHODS = (
    "review-of-design",
    "inspection",
    "analysis",
    "analysis-supported-by-test",
    "test",
)

# Higher is stronger; a proposal below the required strength is a finding.
METHOD_STRENGTH = {name: index for index, name in enumerate(VERIFICATION_METHODS)}

REQUIREMENT_KINDS = (
    "performance",
    "structural",
    "leak-tightness",
    "dimensional",
    "documentation",
)


def _real(value, label, positive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def allocate_method(requirement):
    """Return the verification method a requirement warrants, and why."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    for key in ("id", "kind", "safety_critical"):
        if key not in requirement:
            raise ValueError("requirement missing required key '%s'" % key)
    ident = requirement["id"]
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("requirement 'id' must be a non-empty string")
    kind = requirement["kind"]
    if not isinstance(kind, str) or kind.strip().lower() not in REQUIREMENT_KINDS:
        raise ValueError(
            "requirement kind must be one of %s, got %r" % (", ".join(REQUIREMENT_KINDS), kind)
        )
    kind = kind.strip().lower()
    if not isinstance(requirement["safety_critical"], bool):
        raise ValueError("requirement 'safety_critical' must be a boolean")
    correlated = requirement.get("correlated_test_evidence", False)
    if not isinstance(correlated, bool):
        raise ValueError("requirement 'correlated_test_evidence' must be a boolean")
    if requirement["safety_critical"]:
        return {
            "id": ident.strip(),
            "required_method": "test",
            "rationale": "safety-critical requirements are demonstrated by test",
        }
    if kind in ("performance", "leak-tightness"):
        return {
            "id": ident.strip(),
            "required_method": "test",
            "rationale": "%s behaviour is not predictable to the accuracy the requirement needs"
            % kind,
        }
    if kind == "structural":
        if correlated:
            return {
                "id": ident.strip(),
                "required_method": "analysis-supported-by-test",
                "rationale": "a correlated model carries the structural case",
            }
        return {
            "id": ident.strip(),
            "required_method": "test",
            "rationale": "an uncorrelated structural model cannot close the case alone",
        }
    if kind == "dimensional":
        return {
            "id": ident.strip(),
            "required_method": "inspection",
            "rationale": "the property is measurable on the delivered article",
        }
    return {
        "id": ident.strip(),
        "required_method": "review-of-design",
        "rationale": "the requirement is closed by examining the design data",
    }


def grade_method_allocation(requirement):
    """Compare the proposed method with the one the requirement warrants."""
    allocation = allocate_method(requirement)
    proposed = requirement.get("proposed_method", allocation["required_method"])
    if not isinstance(proposed, str) or proposed.strip().lower() not in METHOD_STRENGTH:
        raise ValueError(
            "proposed method must be one of %s, got %r"
            % (", ".join(VERIFICATION_METHODS), proposed)
        )
    proposed = proposed.strip().lower()
    required = allocation["required_method"]
    adequate = METHOD_STRENGTH[proposed] >= METHOD_STRENGTH[required]
    finding = None
    if not adequate:
        finding = "requirement '%s' proposes '%s' where '%s' is warranted: %s" % (
            allocation["id"],
            proposed,
            required,
            allocation["rationale"],
        )
    return {
        "id": allocation["id"],
        "required_method": required,
        "proposed_method": proposed,
        "rationale": allocation["rationale"],
        "adequate": adequate,
        "finding": finding,
    }


def design_load(limit_load, design_factor):
    """Return the design load the item is sized against."""
    limit = _real(limit_load, "limit_load")
    factor = _real(design_factor, "design_factor")
    if factor < 1.0:
        raise ValueError("design_factor must be at least 1.0, got %g" % factor)
    return limit * factor


def margin_of_safety(allowable, applied_load):
    """Return the margin of safety of an allowable against an applied load."""
    allow = _real(allowable, "allowable")
    applied = _real(applied_load, "applied_load")
    return allow / applied - 1.0


def worst_case_load_case(load_cases, design_factor, allowable):
    """Return the governing load case and its margin over a set of cases."""
    if not isinstance(load_cases, (list, tuple)) or not load_cases:
        raise ValueError("load_cases must be a non-empty sequence")
    worst = None
    for index, case in enumerate(load_cases):
        if not isinstance(case, dict) or "name" not in case or "limit_load" not in case:
            raise ValueError("load_cases[%d] needs 'name' and 'limit_load'" % index)
        name = case["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("load_cases[%d] 'name' must be a non-empty string" % index)
        factor = case.get("design_factor", design_factor)
        value = design_load(case["limit_load"], factor)
        record = {
            "name": name.strip(),
            "limit_load": float(case["limit_load"]),
            "design_factor": float(factor),
            "design_load": value,
            "margin_of_safety": margin_of_safety(allowable, value),
        }
        if worst is None or record["design_load"] > worst["design_load"]:
            worst = record
        elif math.isclose(
            record["design_load"], worst["design_load"], rel_tol=1e-12, abs_tol=0.0
        ) and record["name"] < worst["name"]:
            worst = record
    worst["compliant"] = worst["margin_of_safety"] > 0.0 or math.isclose(
        worst["margin_of_safety"], 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    return worst


def safe_life_demonstration(service_cycles, scatter_factor, demonstrated_cycles):
    """Return the safe-life verdict for a cycle-counted fatigue demonstration."""
    service = _real(service_cycles, "service_cycles")
    scatter = _real(scatter_factor, "scatter_factor")
    demonstrated = _real(demonstrated_cycles, "demonstrated_cycles")
    if scatter < 1.0:
        raise ValueError("scatter_factor must be at least 1.0, got %g" % scatter)
    required = service * scatter
    compliant = demonstrated > required or math.isclose(
        demonstrated, required, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )
    return {
        "service_cycles": service,
        "scatter_factor": scatter,
        "required_cycles": required,
        "demonstrated_cycles": demonstrated,
        "coverage_ratio": demonstrated / required,
        "compliant": compliant,
    }


def hoop_stress(pressure, inner_radius, wall_thickness):
    """Return the thin-wall hoop stress of a pressurised tube."""
    p = _real(pressure, "pressure")
    r = _real(inner_radius, "inner_radius")
    t = _real(wall_thickness, "wall_thickness")
    if t >= r:
        raise ValueError(
            "wall_thickness %g is not thin against inner_radius %g; the thin-wall "
            "relation does not apply" % (t, r)
        )
    return p * r / t


def critical_flaw_depth(fracture_toughness, applied_stress, geometry_factor=1.0):
    """Return the critical flaw depth for a stress and a fracture toughness."""
    k = _real(fracture_toughness, "fracture_toughness")
    s = _real(applied_stress, "applied_stress")
    y = _real(geometry_factor, "geometry_factor")
    ratio = k / (y * s)
    return (ratio * ratio) / math.pi


def leak_before_burst(fracture_toughness, pressure, inner_radius, wall_thickness,
                      geometry_factor=1.0, required_ratio=1.0):
    """Return the leak-before-burst verdict for a pressure boundary."""
    required = _real(required_ratio, "required_ratio")
    stress = hoop_stress(pressure, inner_radius, wall_thickness)
    depth = critical_flaw_depth(fracture_toughness, stress, geometry_factor)
    t = float(wall_thickness)
    ratio = depth / t
    satisfied = ratio > required or math.isclose(
        ratio, required, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )
    return {
        "hoop_stress": stress,
        "critical_flaw_depth": depth,
        "wall_thickness": t,
        "depth_to_thickness_ratio": ratio,
        "required_ratio": required,
        "satisfied": satisfied,
    }


def assess_generic_performance(spec):
    """Run the full clause 5.5.3/5.5.4/5.5.5.1 assessment.

    spec keys: requirements (sequence), load_cases (sequence), design_factor,
    allowable, service_cycles, scatter_factor, demonstrated_cycles, pressure,
    inner_radius, wall_thickness, fracture_toughness, optional
    geometry_factor and required_lbb_ratio.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "requirements",
        "load_cases",
        "design_factor",
        "allowable",
        "service_cycles",
        "scatter_factor",
        "demonstrated_cycles",
        "pressure",
        "inner_radius",
        "wall_thickness",
        "fracture_toughness",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    requirements = spec["requirements"]
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("requirements must be a non-empty sequence")
    allocations = [grade_method_allocation(item) for item in requirements]
    mechanical = worst_case_load_case(
        spec["load_cases"], spec["design_factor"], spec["allowable"]
    )
    fatigue = safe_life_demonstration(
        spec["service_cycles"], spec["scatter_factor"], spec["demonstrated_cycles"]
    )
    lbb = leak_before_burst(
        spec["fracture_toughness"],
        spec["pressure"],
        spec["inner_radius"],
        spec["wall_thickness"],
        spec.get("geometry_factor", 1.0),
        spec.get("required_lbb_ratio", 1.0),
    )
    findings = [a["finding"] for a in allocations if a["finding"]]
    if not mechanical["compliant"]:
        findings.append(
            "governing load case '%s' leaves a margin of safety of %.4f"
            % (mechanical["name"], mechanical["margin_of_safety"])
        )
    if not fatigue["compliant"]:
        findings.append(
            "safe-life demonstration covers %.4f of the scatter-factored life"
            % fatigue["coverage_ratio"]
        )
    if not lbb["satisfied"]:
        findings.append(
            "critical flaw depth is %.4f of the wall thickness; the boundary bursts "
            "before it leaks" % lbb["depth_to_thickness_ratio"]
        )
    return {
        "method_allocations": allocations,
        "mechanical": mechanical,
        "safe_life": fatigue,
        "leak_before_burst": lbb,
        "findings": findings,
        "compliant": not findings,
    }
