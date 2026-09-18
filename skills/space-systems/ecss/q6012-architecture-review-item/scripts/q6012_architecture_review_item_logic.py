"""Architecture review item: the chosen topology against the electrical requirements.

Anchor: ECSS-Q-ST-60-12C clause 7.3.2 (the design review item that examines the
chosen topology and block structure of a microwave monolithic circuit against
the electrical design requirements). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every declared block of the proposed chain: its function, small
   signal gain, noise figure, output third-order intercept and DC draw.
2. Cascade the chain: gain adds in dB, noise figure propagates through the
   Friis contribution of each stage divided by the gain ahead of it, and the
   output intercepts combine as reciprocals referred to the chain output.
3. Check the topology realises every function the requirement set asks for,
   naming both the functions no block provides and the blocks no requirement
   asked for.
4. Turn each computed figure into a signed margin against its minimum or
   maximum limit and report every requirement the block structure cannot meet.

All conversions use math.log10 and the ** operator, which are not correctly
rounded and differ in the last place between platforms, so every equality
decision in this module goes through an explicit tolerance rather than a bare
comparison.
"""

import math

__all__ = [
    "REQUIREMENT_SENSE",
    "MARGIN_TOLERANCE",
    "db_to_linear",
    "linear_to_db",
    "validate_block",
    "normalise_chain",
    "cascade_gain_db",
    "cascade_noise_figure_db",
    "cascade_output_ip3_dbm",
    "total_dc_power_mw",
    "chain_performance",
    "topology_coverage",
    "requirement_margins",
    "assess_architecture_review",
]

# Which way each electrical figure has to clear its limit.
REQUIREMENT_SENSE = {
    "gain_db": "min",
    "noise_figure_db": "max",
    "output_ip3_dbm": "min",
    "dc_power_mw": "max",
}

# A margin is a difference of logarithms; a design sitting exactly on its limit
# can land a few ULPs on the wrong side, and math.log10 rounds differently
# across platforms. Absorb that here instead of relaxing the limit.
MARGIN_TOLERANCE = 1e-9


def _require_real(value, label, minimum=None):
    """Return value as a finite float, refusing bools and out-of-range input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and number < minimum:
        raise ValueError("%s must be at least %g, got %g" % (label, minimum, number))
    return number


def db_to_linear(value_db):
    """Return the power ratio corresponding to a decibel value."""
    return 10.0 ** (_require_real(value_db, "value_db") / 10.0)


def linear_to_db(ratio):
    """Return the decibel value of a strictly positive power ratio."""
    number = _require_real(ratio, "ratio")
    if number <= 0.0:
        raise ValueError("ratio must be strictly positive, got %g" % number)
    return 10.0 * math.log10(number)


def validate_block(entry):
    """Return one normalised block record.

    entry keys: name, function, gain_db, noise_figure_db, output_ip3_dbm,
    optional dc_power_mw (defaults 0.0).
    """
    if not isinstance(entry, dict):
        raise ValueError("block entry must be a mapping, got %r" % (entry,))
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("block name must be a non-empty string, got %r" % (name,))
    function = entry.get("function")
    if not isinstance(function, str) or not function.strip():
        raise ValueError("block %s has no function label" % name)
    gain_db = _require_real(entry.get("gain_db"), "gain_db of %s" % name)
    noise_figure_db = _require_real(
        entry.get("noise_figure_db"), "noise_figure_db of %s" % name, minimum=0.0
    )
    output_ip3_dbm = _require_real(
        entry.get("output_ip3_dbm"), "output_ip3_dbm of %s" % name
    )
    dc_power_mw = _require_real(
        entry.get("dc_power_mw", 0.0), "dc_power_mw of %s" % name, minimum=0.0
    )
    return {
        "name": name.strip(),
        "function": function.strip(),
        "gain_db": gain_db,
        "noise_figure_db": noise_figure_db,
        "output_ip3_dbm": output_ip3_dbm,
        "dc_power_mw": dc_power_mw,
    }


def normalise_chain(entries):
    """Return the validated block chain in declared signal order."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("chain must be a non-empty sequence of block entries")
    chain = [validate_block(entry) for entry in entries]
    seen = set()
    for block in chain:
        if block["name"] in seen:
            raise ValueError("block %s declared twice" % block["name"])
        seen.add(block["name"])
    return chain


def cascade_gain_db(chain):
    """Return the small-signal gain of the chain: decibels add in cascade."""
    if not chain:
        raise ValueError("chain must hold at least one block")
    return math.fsum(block["gain_db"] for block in chain)


def cascade_noise_figure_db(chain):
    """Return the chain noise figure from the Friis stage contributions."""
    if not chain:
        raise ValueError("chain must hold at least one block")
    total_factor = 0.0
    gain_ahead = 1.0
    for index, block in enumerate(chain):
        factor = db_to_linear(block["noise_figure_db"])
        if index == 0:
            total_factor = factor
        else:
            total_factor += (factor - 1.0) / gain_ahead
        gain_ahead *= db_to_linear(block["gain_db"])
    if total_factor <= 0.0:
        raise ValueError("cascaded noise factor collapsed to %g" % total_factor)
    return linear_to_db(total_factor)


def cascade_output_ip3_dbm(chain):
    """Return the chain output third-order intercept referred to the output."""
    if not chain:
        raise ValueError("chain must hold at least one block")
    reciprocal = 0.0
    for index, block in enumerate(chain):
        gain_after = 1.0
        for downstream in chain[index + 1:]:
            gain_after *= db_to_linear(downstream["gain_db"])
        stage_output_mw = db_to_linear(block["output_ip3_dbm"]) * gain_after
        if stage_output_mw <= 0.0:
            raise ValueError("block %s referred to a non-positive intercept" % block["name"])
        reciprocal += 1.0 / stage_output_mw
    if reciprocal <= 0.0:
        raise ValueError("cascaded intercept reciprocal collapsed to %g" % reciprocal)
    return linear_to_db(1.0 / reciprocal)


def total_dc_power_mw(chain):
    """Return the DC draw of the whole block structure."""
    if not chain:
        raise ValueError("chain must hold at least one block")
    return math.fsum(block["dc_power_mw"] for block in chain)


def chain_performance(chain):
    """Return every computed electrical figure of the proposed topology."""
    return {
        "gain_db": cascade_gain_db(chain),
        "noise_figure_db": cascade_noise_figure_db(chain),
        "output_ip3_dbm": cascade_output_ip3_dbm(chain),
        "dc_power_mw": total_dc_power_mw(chain),
    }


def topology_coverage(chain, required_functions):
    """Return which required functions the block structure realises."""
    if not isinstance(required_functions, (list, tuple)) or not required_functions:
        raise ValueError("required_functions must be a non-empty sequence")
    provided = set()
    for block in chain:
        provided.add(block["function"])
    missing = []
    for function in required_functions:
        if not isinstance(function, str) or not function.strip():
            raise ValueError("required function must be a non-empty string")
        if function.strip() not in provided:
            missing.append(function.strip())
    wanted = {f.strip() for f in required_functions}
    unrequested = sorted(provided - wanted)
    return {
        "provided_functions": sorted(provided),
        "missing_functions": missing,
        "unrequested_functions": unrequested,
        "covered": not missing,
        "coverage_fraction": (len(wanted) - len(missing)) / len(wanted),
    }


def requirement_margins(performance, requirements):
    """Return the signed margin of each required figure against its limit."""
    if not isinstance(performance, dict):
        raise ValueError("performance must be a mapping of metric to value")
    if not isinstance(requirements, dict) or not requirements:
        raise ValueError("requirements must be a non-empty mapping of metric to limit")
    margins = {}
    for metric, limit in requirements.items():
        if metric not in REQUIREMENT_SENSE:
            raise ValueError(
                "requirement %r is not one of %s"
                % (metric, ", ".join(sorted(REQUIREMENT_SENSE)))
            )
        if metric not in performance:
            raise ValueError("performance carries no value for %s" % metric)
        limit_value = _require_real(limit, "limit of %s" % metric)
        value = _require_real(performance[metric], "performance %s" % metric)
        sense = REQUIREMENT_SENSE[metric]
        margin = value - limit_value if sense == "min" else limit_value - value
        margins[metric] = {
            "value": value,
            "limit": limit_value,
            "sense": sense,
            "margin": margin,
            "met": margin > 0.0 or math.isclose(
                margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
            ),
        }
    return margins


def assess_architecture_review(spec):
    """Run the full clause 7.3.2 architecture review item.

    spec keys: blocks (sequence of block entries), requirements (mapping of
    metric to limit), optional required_functions.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("blocks", "requirements"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    chain = normalise_chain(spec["blocks"])
    performance = chain_performance(chain)
    margins = requirement_margins(performance, spec["requirements"])
    coverage = None
    if spec.get("required_functions"):
        coverage = topology_coverage(chain, spec["required_functions"])
    findings = []
    for metric in sorted(margins):
        record = margins[metric]
        if not record["met"]:
            findings.append(
                "%s is %.4f against a %s limit of %.4f, short by %.4f"
                % (metric, record["value"], record["sense"], record["limit"],
                   -record["margin"])
            )
    if coverage is not None and coverage["missing_functions"]:
        findings.append(
            "topology realises no block for: %s" % ", ".join(coverage["missing_functions"])
        )
    accepted = not findings
    return {
        "chain": chain,
        "performance": performance,
        "margins": margins,
        "coverage": coverage,
        "findings": findings,
        "accepted": accepted,
    }
