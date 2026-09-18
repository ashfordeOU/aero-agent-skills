"""Simulation-results review item of a die-form MMIC design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.4 (design review -- the simulation-results
item). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Build the corner matrix the review demands: the full cross product of the
   declared process corners, temperature extremes and supply extremes. A
   simulation set is reviewable only once that matrix is covered, so missing
   corners are reported before any number is graded.
2. Normalise the delivered runs onto that matrix, refusing a duplicated corner
   and naming any run that sits at a corner the matrix never asked for.
3. For each specification parameter, collect its value at every covered corner
   and take the WORST one in the direction the specification is written: a
   minimum-type target (gain, output power) is worst at its lowest sample, a
   maximum-type target (noise figure, current draw, return loss magnitude) is
   worst at its highest.
4. Grade that worst sample against the target, reporting a signed margin in the
   parameter's own units and as a fraction of the target, so a marginal
   parameter is visible as a number rather than as a pass or fail flag.
5. Emit findings for the three failure shapes the item exists to catch: an
   incomplete corner matrix, a parameter not reported at every covered corner,
   and a parameter whose samples do not move across the corners at all, which
   means the sweep did not actually reach it.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "DIRECTIONS",
    "required_corner_set",
    "corner_key",
    "corner_label",
    "normalise_runs",
    "missing_corners",
    "extra_corners",
    "parameter_samples",
    "worst_corner",
    "parameter_margin",
    "margin_fraction",
    "corner_spread",
    "evaluate_parameter",
    "review_simulation_results",
]

# A margin is a difference of two quantities that have both been through a
# simulator and a unit conversion, so a parameter that sits exactly on its
# target can land a few ULPs either side. Absorb the representation error here
# instead of moving the specification target.
MARGIN_TOLERANCE = 1e-9

# Grid coordinates are rounded to this many decimals before they become dict
# keys, so that a temperature written -30 and one written -30.0 are one corner.
_KEY_DECIMALS = 6

DIRECTIONS = ("min", "max")


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _text(label, value):
    """Return a non-empty stripped identifier or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % label)
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def _distinct_reals(label, values, positive=False):
    """Return an ordered list of distinct finite axis values or raise."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("%s must be a non-empty sequence" % label)
    out = []
    for index, item in enumerate(values):
        one = _positive("%s[%d]" % (label, index), item) if positive \
            else _real("%s[%d]" % (label, index), item)
        rounded = round(one, _KEY_DECIMALS)
        if rounded in out:
            raise ValueError("%s repeats the value %g" % (label, one))
        out.append(rounded)
    return sorted(out)


def required_corner_set(process_corners, temperatures_c, supplies_v):
    """Return the sorted cross product of the three declared corner axes."""
    if not isinstance(process_corners, (list, tuple)) or not process_corners:
        raise ValueError("process_corners must be a non-empty sequence")
    processes = []
    for index, item in enumerate(process_corners):
        name = _text("process_corners[%d]" % index, item).lower()
        if name in processes:
            raise ValueError("process_corners repeats '%s'" % name)
        processes.append(name)
    temperatures = _distinct_reals("temperatures_c", temperatures_c)
    supplies = _distinct_reals("supplies_v", supplies_v, positive=True)
    return [
        (process, temperature, supply)
        for process in sorted(processes)
        for temperature in temperatures
        for supply in supplies
    ]


def corner_key(run):
    """Return the normalised (process, temperature, supply) key of one run."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping")
    process = _text("run process", run.get("process", "")).lower()
    temperature = round(_real("run temperature_c", run.get("temperature_c")), _KEY_DECIMALS)
    supply = round(_positive("run supply_v", run.get("supply_v")), _KEY_DECIMALS)
    return (process, temperature, supply)


def corner_label(key):
    """Return a human-readable label for a normalised corner key."""
    if not isinstance(key, (list, tuple)) or len(key) != 3:
        raise ValueError("corner key must be a (process, temperature, supply) triple")
    return "%s @ %gC @ %gV" % (key[0], key[1], key[2])


def normalise_runs(runs):
    """Return {corner key: values mapping} for the delivered simulation runs."""
    if not isinstance(runs, (list, tuple)) or not runs:
        raise ValueError("runs must be a non-empty sequence")
    table = {}
    for index, run in enumerate(runs):
        key = corner_key(run)
        if key in table:
            raise ValueError("corner %s is reported twice" % corner_label(key))
        values = run.get("values")
        if not isinstance(values, dict) or not values:
            raise ValueError("runs[%d] must carry a non-empty 'values' mapping" % index)
        cleaned = {}
        for name, value in values.items():
            cleaned[_text("value name in run %d" % index, name)] = _real(
                "%s at %s" % (name, corner_label(key)), value
            )
        table[key] = cleaned
    return table


def missing_corners(required, provided):
    """Return the required corners with no delivered run, in matrix order."""
    if not isinstance(required, (list, tuple)):
        raise ValueError("required must be a sequence of corner keys")
    if not isinstance(provided, dict):
        raise ValueError("provided must be the mapping returned by normalise_runs")
    return [key for key in required if key not in provided]


def extra_corners(required, provided):
    """Return the delivered corners the declared matrix never asked for."""
    if not isinstance(required, (list, tuple)):
        raise ValueError("required must be a sequence of corner keys")
    if not isinstance(provided, dict):
        raise ValueError("provided must be the mapping returned by normalise_runs")
    wanted = set(tuple(key) for key in required)
    return sorted(key for key in provided if key not in wanted)


def parameter_samples(name, provided, corners):
    """Return {corner key: value} for one parameter over the covered corners."""
    label = _text("parameter name", name)
    if not isinstance(provided, dict):
        raise ValueError("provided must be the mapping returned by normalise_runs")
    samples = {}
    absent = []
    for key in corners:
        if key not in provided:
            continue
        values = provided[key]
        if label not in values:
            absent.append(key)
            continue
        samples[key] = values[label]
    return samples, absent


def worst_corner(samples, direction):
    """Return the (corner, value) worst in the direction the target is written."""
    if direction not in DIRECTIONS:
        raise ValueError("direction must be one of %s, got %r" % (DIRECTIONS, direction))
    if not isinstance(samples, dict) or not samples:
        raise ValueError("samples must be a non-empty mapping of corner keys to values")
    worst_key = None
    worst_value = None
    for key in sorted(samples):
        value = samples[key]
        if worst_key is None:
            worst_key, worst_value = key, value
            continue
        if direction == "min":
            if value < worst_value:
                worst_key, worst_value = key, value
        elif value > worst_value:
            worst_key, worst_value = key, value
    return worst_key, worst_value


def parameter_margin(worst_value, target, direction):
    """Return the signed margin; positive means the target is met."""
    if direction not in DIRECTIONS:
        raise ValueError("direction must be one of %s, got %r" % (DIRECTIONS, direction))
    value = _real("worst_value", worst_value)
    goal = _real("target", target)
    return value - goal if direction == "min" else goal - value


def margin_fraction(margin, target):
    """Return the margin as a fraction of the target magnitude."""
    value = _real("margin", margin)
    goal = _real("target", target)
    if goal == 0.0:
        raise ValueError("a zero target has no fractional margin; report the absolute margin")
    return value / abs(goal)


def corner_spread(samples):
    """Return the spread between the highest and lowest sample of a parameter."""
    if not isinstance(samples, dict) or not samples:
        raise ValueError("samples must be a non-empty mapping of corner keys to values")
    values = list(samples.values())
    return max(values) - min(values)


def evaluate_parameter(parameter, provided, corners):
    """Grade one specification parameter across the covered corner set."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping")
    name = _text("parameter name", parameter.get("name", ""))
    direction = parameter.get("direction")
    if direction not in DIRECTIONS:
        raise ValueError(
            "parameter '%s' direction must be one of %s, got %r" % (name, DIRECTIONS, direction)
        )
    target = _real("parameter '%s' target" % name, parameter.get("target"))
    unit = _text("parameter '%s' unit" % name, parameter.get("unit", ""))

    samples, absent = parameter_samples(name, provided, corners)
    findings = []
    for key in absent:
        findings.append("%s is not reported at corner %s" % (name, corner_label(key)))
    if not samples:
        return {
            "name": name,
            "direction": direction,
            "target": target,
            "unit": unit,
            "samples": {},
            "worst_corner": None,
            "worst_value": None,
            "margin": None,
            "margin_fraction": None,
            "spread": None,
            "meets_target": False,
            "findings": findings + ["%s has no reported value at any covered corner" % name],
        }

    key, value = worst_corner(samples, direction)
    margin = parameter_margin(value, target, direction)
    fraction = None if target == 0.0 else margin_fraction(margin, target)
    spread = corner_spread(samples)
    meets = margin >= 0.0 or math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)
    if not meets:
        findings.append(
            "%s worst corner %s gives %g %s against a %s target of %g %s (margin %g %s)"
            % (name, corner_label(key), value, unit, direction, target, unit, margin, unit)
        )
    if len(samples) > 1 and math.isclose(spread, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE):
        findings.append(
            "%s is reported identically at all %d covered corners; the sweep did not reach it"
            % (name, len(samples))
        )
    return {
        "name": name,
        "direction": direction,
        "target": target,
        "unit": unit,
        "samples": samples,
        "worst_corner": key,
        "worst_value": value,
        "margin": margin,
        "margin_fraction": fraction,
        "spread": spread,
        "meets_target": meets,
        "findings": findings,
    }


def review_simulation_results(package):
    """Run the whole clause 7.3.4 simulation-results review item.

    package keys: process_corners, temperatures_c, supplies_v, parameters
    (each carrying name, direction, target, unit) and runs (each carrying
    process, temperature_c, supply_v and a values mapping).
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    for key in ("process_corners", "temperatures_c", "supplies_v", "parameters", "runs"):
        if key not in package:
            raise ValueError("package missing required key '%s'" % key)
    parameters = package["parameters"]
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("package['parameters'] must be a non-empty sequence")

    required = required_corner_set(
        package["process_corners"], package["temperatures_c"], package["supplies_v"]
    )
    provided = normalise_runs(package["runs"])
    absent = missing_corners(required, provided)
    surplus = extra_corners(required, provided)
    covered = [key for key in required if key in provided]

    findings = []
    for key in absent:
        findings.append("corner %s of the declared matrix has no simulation run" % corner_label(key))
    for key in surplus:
        findings.append(
            "run at %s sits outside the declared corner matrix" % corner_label(key)
        )

    graded = []
    seen = set()
    for parameter in parameters:
        record = evaluate_parameter(parameter, provided, covered)
        if record["name"] in seen:
            raise ValueError("parameter '%s' is graded twice" % record["name"])
        seen.add(record["name"])
        graded.append(record)
        findings.extend(record["findings"])

    worst = None
    for record in graded:
        if record["margin_fraction"] is None:
            continue
        if worst is None or record["margin_fraction"] < worst["margin_fraction"]:
            worst = record
    return {
        "required_corner_count": len(required),
        "covered_corner_count": len(covered),
        "missing_corners": absent,
        "extra_corners": surplus,
        "parameters": graded,
        "tightest_parameter": None if worst is None else worst["name"],
        "tightest_margin_fraction": None if worst is None else worst["margin_fraction"],
        "findings": findings,
        "item_passed": not findings,
    }
