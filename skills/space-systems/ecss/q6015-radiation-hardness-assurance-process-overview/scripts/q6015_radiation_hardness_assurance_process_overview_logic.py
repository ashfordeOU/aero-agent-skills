"""Radiation hardness assurance flow, mission environment down to part level.

Anchor: ECSS-Q-ST-60-15C clause 4.1 (the overview of the hardness assurance
process: how a mission radiation environment is carried through system
requirements, shielding and part-level specified levels into a margin each
part has to hold). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared process stages against the canonical flow: every
   stage recognized, none declared twice, none out of order, and every absent
   stage named on its own.
2. Validate the mission environment: the environment quantity, its value at a
   stated reference shielding thickness, and the mission duration it covers.
3. Carry that environment down to each part's own location by interpolating a
   tabulated dose-depth curve in log-log space, refusing a local shielding
   thickness the curve does not span rather than extrapolating it.
4. Apply the declared design factor to obtain the part-level specified level,
   which is the number the part is procured and verified against.
5. Divide each part's demonstrated capability by its specified level to obtain
   the radiation design margin, and compare that margin with the required
   value under a named tolerance so an exact equality passes.
6. Return the stage assessment, the per-part specified levels and margins, and
   a verdict carrying every finding.
"""

import math

__all__ = [
    "RHA_STAGES",
    "ENVIRONMENT_QUANTITIES",
    "DEFAULT_REQUIRED_MARGIN",
    "MARGIN_TOLERANCE",
    "MIN_DESIGN_FACTOR",
    "normalize_token",
    "validate_quantity",
    "validate_stage",
    "assess_stage_sequence",
    "stage_completeness",
    "validate_environment",
    "validate_dose_depth_curve",
    "local_environment_level",
    "specified_level",
    "design_margin",
    "margin_holds",
    "assess_part",
    "assess_assurance_flow",
]

# The canonical order of the hardness assurance flow, environment first and
# close-out last.
RHA_STAGES = (
    "mission-environment-definition",
    "system-radiation-requirements",
    "shielding-and-geometry-analysis",
    "part-level-specified-levels",
    "part-capability-data-collection",
    "design-margin-evaluation",
    "lot-radiation-verification-testing",
    "mitigation-and-rework-decision",
    "assurance-report-close-out",
)

# The environment quantities the flow can be run for.
ENVIRONMENT_QUANTITIES = (
    "total-ionising-dose",
    "displacement-damage-dose",
    "single-event-environment",
)

# The margin a part is expected to hold unless the project declares another.
DEFAULT_REQUIRED_MARGIN = 2.0

# The margin is a quotient of two measured levels; a part sitting exactly on
# its required margin must not fail on representation alone.
MARGIN_TOLERANCE = 1e-9

# A design factor below unity would reduce the level the part is held to.
MIN_DESIGN_FACTOR = 1.0


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _positive_number(value, label):
    """Return a strictly positive real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %g" % (label, number))
    return number


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_quantity(value):
    """Return the validated environment quantity token."""
    token = normalize_token(value, "environment quantity")
    if token not in ENVIRONMENT_QUANTITIES:
        raise ValueError(
            "environment quantity '%s' is not recognized; expected one of %s"
            % (token, ", ".join(ENVIRONMENT_QUANTITIES))
        )
    return token


def validate_stage(value):
    """Return the validated assurance stage token."""
    token = normalize_token(value, "stage")
    if token not in RHA_STAGES:
        raise ValueError(
            "stage '%s' is not part of the assurance flow; expected one of %s"
            % (token, ", ".join(RHA_STAGES))
        )
    return token


def assess_stage_sequence(stages):
    """Return the declared flow's absent stages and its order findings."""
    if not isinstance(stages, (list, tuple)):
        raise ValueError("stages must be a sequence")
    declared = []
    for value in stages:
        token = validate_stage(value)
        if token in declared:
            raise ValueError("stage '%s' is declared twice" % token)
        declared.append(token)

    absent = [s for s in RHA_STAGES if s not in declared]

    order_findings = []
    ranks = [RHA_STAGES.index(s) for s in declared]
    for index in range(1, len(ranks)):
        if ranks[index] < ranks[index - 1]:
            order_findings.append(
                "stage '%s' is declared after '%s', which follows it in the flow"
                % (declared[index], declared[index - 1])
            )

    return {
        "declared": declared,
        "absent_stages": absent,
        "order_findings": order_findings,
        "in_order": not order_findings,
    }


def stage_completeness(stages):
    """Return the fraction of the canonical flow the declaration carries."""
    assessment = assess_stage_sequence(stages)
    return (len(RHA_STAGES) - len(assessment["absent_stages"])) / float(len(RHA_STAGES))


def validate_environment(environment):
    """Return the validated mission environment the flow starts from."""
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping")
    for key in ("quantity", "reference_thickness_mm", "level", "mission_years"):
        if key not in environment:
            raise ValueError("environment missing required key '%s'" % key)
    return {
        "quantity": validate_quantity(environment["quantity"]),
        "reference_thickness_mm": _positive_number(
            environment["reference_thickness_mm"], "reference_thickness_mm"
        ),
        "level": _positive_number(environment["level"], "environment level"),
        "mission_years": _positive_number(
            environment["mission_years"], "mission_years"
        ),
    }


def validate_dose_depth_curve(curve):
    """Return a validated dose-depth curve, ascending in shielding thickness.

    Each point is a (thickness in millimetres, environment level) pair. The
    level must fall as shielding is added; a curve that rises with thickness
    is a data error, not a shielding result.
    """
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("dose-depth curve must hold at least two points")
    points = []
    for index, point in enumerate(curve):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("curve point %d must be a (thickness, level) pair" % index)
        thickness = _positive_number(point[0], "curve point %d thickness" % index)
        level = _positive_number(point[1], "curve point %d level" % index)
        points.append((thickness, level))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError(
                "curve thicknesses must ascend; point %d is %g mm after %g mm"
                % (index, points[index][0], points[index - 1][0])
            )
        if points[index][1] > points[index - 1][1]:
            raise ValueError(
                "curve level rises from %g to %g as shielding is added"
                % (points[index - 1][1], points[index][1])
            )
    return points


def local_environment_level(curve, thickness_mm):
    """Return the environment level behind a local shielding thickness.

    Interpolation is linear in log thickness against log level, which is how a
    dose-depth curve behaves between tabulated points. A thickness the curve
    does not span is refused: the curve shape differs outside its span, so
    extrapolating it would invent data. A thickness landing exactly on a
    tabulated point returns that point's level unchanged rather than routing
    it through a logarithm.
    """
    points = validate_dose_depth_curve(curve)
    thickness = _positive_number(thickness_mm, "local shielding thickness")
    low = points[0][0]
    high = points[-1][0]
    if thickness < low or thickness > high:
        raise ValueError(
            "local shielding %g mm is outside the curve span %g-%g mm"
            % (thickness, low, high)
        )
    for node_thickness, node_level in points:
        if node_thickness == thickness:
            return node_level
    for index in range(1, len(points)):
        t1, l1 = points[index - 1]
        t2, l2 = points[index]
        if t1 < thickness < t2:
            span = math.log(t2) - math.log(t1)
            frac = (math.log(thickness) - math.log(t1)) / span
            return math.exp(math.log(l1) + frac * (math.log(l2) - math.log(l1)))
    raise ValueError("local shielding %g mm could not be bracketed" % thickness)


def specified_level(local_level, design_factor):
    """Return the part-level specified level the part is held to."""
    level = _positive_number(local_level, "local level")
    factor = _positive_number(design_factor, "design factor")
    if factor < MIN_DESIGN_FACTOR:
        raise ValueError(
            "design factor %g would hold the part below its environment" % factor
        )
    return level * factor


def design_margin(capability, specified):
    """Return the radiation design margin a part holds."""
    cap = _positive_number(capability, "part capability")
    spec = _positive_number(specified, "specified level")
    return cap / spec


def margin_holds(margin, required):
    """Return whether a margin meets its requirement, equality included."""
    value = _positive_number(margin, "margin")
    needed = _positive_number(required, "required margin")
    if math.isclose(value, needed, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0):
        return True
    return value > needed


def assess_part(part, curve, environment, required_margin=None):
    """Return one part carried from the mission environment to its margin."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("part_number", "local_shielding_mm", "design_factor", "capability"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)

    env = validate_environment(environment)
    needed = (
        DEFAULT_REQUIRED_MARGIN
        if required_margin is None
        else _positive_number(required_margin, "required margin")
    )

    part_number = _require_text(part["part_number"], "part_number")
    local = local_environment_level(curve, part["local_shielding_mm"])
    spec = specified_level(local, part["design_factor"])
    capability = _positive_number(part["capability"], "part capability")
    margin = design_margin(capability, spec)
    holds = margin_holds(margin, needed)

    findings = []
    if not holds:
        findings.append(
            "part '%s' holds a margin of %.4g against a required %.4g"
            % (part_number, margin, needed)
        )
    if local > env["level"]:
        findings.append(
            "part '%s' sees more than the reference environment behind its shielding"
            % part_number
        )

    return {
        "part_number": part_number,
        "quantity": env["quantity"],
        "local_shielding_mm": _positive_number(
            part["local_shielding_mm"], "local_shielding_mm"
        ),
        "local_level": local,
        "design_factor": _positive_number(part["design_factor"], "design_factor"),
        "specified_level": spec,
        "capability": capability,
        "margin": margin,
        "required_margin": needed,
        "margin_holds": holds,
        "findings": findings,
    }


def assess_assurance_flow(flow):
    """Run the full clause 4.1 assessment of one assurance flow.

    flow keys: environment, dose_depth_curve, stages, parts, and optionally
    required_margin.
    """
    if not isinstance(flow, dict):
        raise ValueError("flow must be a mapping")
    for key in ("environment", "dose_depth_curve", "stages", "parts"):
        if key not in flow:
            raise ValueError("flow missing required key '%s'" % key)

    environment = validate_environment(flow["environment"])
    curve = validate_dose_depth_curve(flow["dose_depth_curve"])
    stages = assess_stage_sequence(flow["stages"])
    completeness = stage_completeness(flow["stages"])

    raw_parts = flow["parts"]
    if not isinstance(raw_parts, (list, tuple)) or not raw_parts:
        raise ValueError("parts must be a non-empty sequence")

    findings = list(stages["order_findings"])
    for stage in stages["absent_stages"]:
        findings.append("assurance stage '%s' is not in the declared flow" % stage)

    parts = []
    seen = set()
    for raw in raw_parts:
        assessed = assess_part(raw, curve, environment, flow.get("required_margin"))
        if assessed["part_number"] in seen:
            raise ValueError(
                "part '%s' is carried through the flow twice" % assessed["part_number"]
            )
        seen.add(assessed["part_number"])
        parts.append(assessed)
        findings.extend(assessed["findings"])

    worst = min(parts, key=lambda p: p["margin"])

    return {
        "environment": environment,
        "stages": stages,
        "stage_completeness": completeness,
        "parts": parts,
        "worst_case_part": worst["part_number"],
        "worst_case_margin": worst["margin"],
        "flow_acceptable": not findings,
        "findings": findings,
    }
