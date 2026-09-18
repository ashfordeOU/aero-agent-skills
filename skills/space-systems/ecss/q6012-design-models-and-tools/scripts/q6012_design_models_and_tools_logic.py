"""Acceptance of the models, design kit and tools an MMIC development runs on.

Anchor: ECSS-Q-ST-60-12C clause 5.3 (the simulation models, design kits and
software used while a monolithic microwave circuit is developed). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the usage envelope the design actually exercises: the frequency
   span, the bias span and the temperature span, plus the process release the
   wafers are to be fabricated to.
2. For every model in the kit, compare its validated envelope with that usage
   envelope on each axis and report the coverage, so a model used outside the
   data it was fitted to is named rather than silently extrapolated.
3. Match each model's process release against the release being fabricated; a
   model fitted to a superseded release is a finding on the kit, not on the
   design.
4. Hold the measurement-correlation error of each model inside its tolerance.
5. Require electromagnetic verification of passive structures once the usage
   band reaches the frequency where a lumped equivalent stops holding.
6. Require the simulation tools themselves to be version-controlled and to
   carry validation evidence.
7. Return one verdict naming the most severe thing that stops the kit being
   accepted, with the per-model coverage behind it.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "MODEL_KINDS",
    "DEFAULT_MODEL_POLICY",
    "STATUS_PRECEDENCE",
    "DESIGN_KIT_ACCEPTABLE",
    "MODEL_ENVELOPE_EXCEEDED",
    "MODEL_PROCESS_RELEASE_MISMATCH",
    "MODEL_CORRELATION_EXCEEDED",
    "PASSIVE_EM_VERIFICATION_MISSING",
    "TOOL_NOT_VERSION_CONTROLLED",
    "TOOL_VALIDATION_EVIDENCE_MISSING",
    "validate_model_policy",
    "validate_span",
    "span_overlap",
    "axis_coverage",
    "validate_usage_envelope",
    "validate_model",
    "envelope_coverage",
    "assess_model",
    "validate_tool",
    "assess_tool",
    "model_acceptance_fraction",
    "assess_design_kit",
]

# Coverage and error comparisons are ratios of measured quantities: a value
# that is physically exactly on its bound can land a few ULP either side.
# Absorb that here instead of relaxing the engineering limit.
COVERAGE_TOLERANCE = 1e-9

# The kinds of model a microwave design kit carries. A passive model stands
# for a printed structure whose behaviour is geometric; an active model stands
# for a device fitted to measured data.
MODEL_KINDS = ("active-device", "passive-structure", "interconnect", "package")

DESIGN_KIT_ACCEPTABLE = "design-kit-acceptable"
MODEL_ENVELOPE_EXCEEDED = "model-usage-envelope-exceeded"
MODEL_PROCESS_RELEASE_MISMATCH = "model-process-release-mismatch"
MODEL_CORRELATION_EXCEEDED = "model-correlation-error-exceeded"
PASSIVE_EM_VERIFICATION_MISSING = "passive-electromagnetic-verification-missing"
TOOL_NOT_VERSION_CONTROLLED = "simulation-tool-not-version-controlled"
TOOL_VALIDATION_EVIDENCE_MISSING = "simulation-tool-validation-evidence-missing"

# Most severe first: the verdict names the worst thing found, so that a kit
# with several defects does not report the mildest one.
STATUS_PRECEDENCE = (
    MODEL_PROCESS_RELEASE_MISMATCH,
    MODEL_ENVELOPE_EXCEEDED,
    PASSIVE_EM_VERIFICATION_MISSING,
    MODEL_CORRELATION_EXCEEDED,
    TOOL_NOT_VERSION_CONTROLLED,
    TOOL_VALIDATION_EVIDENCE_MISSING,
)

DEFAULT_MODEL_POLICY = {
    # Correlation error between model and measurement, in percent.
    "max_correlation_error_pct": 5.0,
    # Above this frequency a passive structure needs electromagnetic
    # verification rather than a lumped equivalent.
    "em_required_above_ghz": 20.0,
    # Fraction of the usage envelope a model's validated envelope must cover
    # on every axis.
    "min_axis_coverage": 1.0,
    # Whether a model may be used outside the envelope it was validated over.
    "allow_envelope_extrapolation": False,
    # Whether the simulation tools must be version-controlled.
    "require_tool_version_control": True,
}


def _is_real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_model_policy(policy=None):
    """Return a complete model policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_MODEL_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("model policy must be a mapping")
    merged = dict(DEFAULT_MODEL_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_MODEL_POLICY:
            raise ValueError("unknown model policy key %r" % (key,))
        default = DEFAULT_MODEL_POLICY[key]
        if isinstance(default, bool):
            if not isinstance(value, bool):
                raise ValueError("%s must be a boolean" % key)
        else:
            if not _is_real(value):
                raise ValueError("%s must be a real number" % key)
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError("%s must be non-negative and finite" % key)
            value = float(value)
        merged[key] = value
    if merged["min_axis_coverage"] > 1.0:
        raise ValueError("min_axis_coverage cannot exceed 1.0")
    return merged


def validate_span(span, label, positive=False):
    """Return a validated (low, high) span as floats."""
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low, high = span
    for name, value in (("%s low" % label, low), ("%s high" % label, high)):
        if not _is_real(value):
            raise ValueError("%s must be a real number" % name)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % name)
        if positive and float(value) <= 0.0:
            raise ValueError("%s must be positive, got %r" % (name, value))
    low = float(low)
    high = float(high)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def span_overlap(usage, validated):
    """Return the width of the overlap between a usage and a validated span."""
    u_low, u_high = usage
    v_low, v_high = validated
    return max(0.0, min(u_high, v_high) - max(u_low, v_low))


def axis_coverage(usage, validated, label="axis"):
    """Return the fraction of the usage span the validated span covers."""
    u_low, u_high = validate_span(usage, "usage %s" % label)
    v_low, v_high = validate_span(validated, "validated %s" % label)
    width = u_high - u_low
    if width <= 0.0:
        inside = (v_low - COVERAGE_TOLERANCE) <= u_low <= (v_high + COVERAGE_TOLERANCE)
        return 1.0 if inside else 0.0
    fraction = span_overlap((u_low, u_high), (v_low, v_high)) / width
    if fraction < 0.0:
        return 0.0
    if fraction > 1.0:
        return 1.0
    return fraction


def validate_usage_envelope(envelope):
    """Return the validated usage envelope of the design."""
    if not isinstance(envelope, dict):
        raise ValueError("usage envelope must be a mapping")
    for key in ("frequency_ghz", "bias_v", "temperature_c", "process_release"):
        if key not in envelope:
            raise ValueError("usage envelope missing required key '%s'" % key)
    release = envelope["process_release"]
    if not isinstance(release, str) or not release.strip():
        raise ValueError("process_release must be a non-empty string")
    return {
        "frequency_ghz": validate_span(envelope["frequency_ghz"], "frequency_ghz", positive=True),
        "bias_v": validate_span(envelope["bias_v"], "bias_v"),
        "temperature_c": validate_span(envelope["temperature_c"], "temperature_c"),
        "process_release": release.strip(),
    }


def validate_model(model):
    """Return a validated design-kit model record."""
    if not isinstance(model, dict):
        raise ValueError("model must be a mapping")
    for key in ("id", "kind", "frequency_ghz", "bias_v", "temperature_c",
                "process_release", "correlation_error_pct"):
        if key not in model:
            raise ValueError("model missing required key '%s'" % key)
    identifier = model["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("model id must be a non-empty string")
    kind = model["kind"]
    if kind not in MODEL_KINDS:
        raise ValueError("unknown model kind %r" % (kind,))
    release = model["process_release"]
    if not isinstance(release, str) or not release.strip():
        raise ValueError("model process_release must be a non-empty string")
    error = model["correlation_error_pct"]
    if not _is_real(error):
        raise ValueError("correlation_error_pct must be a real number")
    error = float(error)
    if not math.isfinite(error) or error < 0.0:
        raise ValueError("correlation_error_pct must be non-negative and finite")
    em_verified = model.get("em_verified", False)
    if not isinstance(em_verified, bool):
        raise ValueError("em_verified must be a boolean")
    return {
        "id": identifier.strip(),
        "kind": kind,
        "frequency_ghz": validate_span(model["frequency_ghz"], "model frequency_ghz", positive=True),
        "bias_v": validate_span(model["bias_v"], "model bias_v"),
        "temperature_c": validate_span(model["temperature_c"], "model temperature_c"),
        "process_release": release.strip(),
        "correlation_error_pct": error,
        "em_verified": em_verified,
    }


def envelope_coverage(model, envelope):
    """Return the per-axis coverage of the usage envelope by one model."""
    record = validate_model(model)
    usage = validate_usage_envelope(envelope)
    axes = {}
    for axis in ("frequency_ghz", "bias_v", "temperature_c"):
        axes[axis] = axis_coverage(usage[axis], record[axis], label=axis)
    worst_axis = min(axes, key=lambda name: (axes[name], name))
    volume = 1.0
    for value in axes.values():
        volume *= value
    axes_out = dict(axes)
    axes_out["worst_axis"] = worst_axis
    axes_out["worst_coverage"] = axes[worst_axis]
    axes_out["volume_coverage"] = volume
    return axes_out


def assess_model(model, envelope, policy=None):
    """Assess one model against the usage envelope and return its record."""
    rules = validate_model_policy(policy)
    record = validate_model(model)
    usage = validate_usage_envelope(envelope)
    coverage = envelope_coverage(record, usage)
    findings = []
    statuses = []
    if not rules["allow_envelope_extrapolation"]:
        if coverage["worst_coverage"] < rules["min_axis_coverage"] - COVERAGE_TOLERANCE:
            statuses.append(MODEL_ENVELOPE_EXCEEDED)
            findings.append(
                "model %s covers only %.3f of the used %s span; it would be "
                "extrapolated outside the data it was fitted to"
                % (record["id"], coverage["worst_coverage"], coverage["worst_axis"])
            )
    if record["process_release"] != usage["process_release"]:
        statuses.append(MODEL_PROCESS_RELEASE_MISMATCH)
        findings.append(
            "model %s is fitted to process release %s, the wafers are to be run on %s"
            % (record["id"], record["process_release"], usage["process_release"])
        )
    if record["correlation_error_pct"] > rules["max_correlation_error_pct"] + COVERAGE_TOLERANCE:
        statuses.append(MODEL_CORRELATION_EXCEEDED)
        findings.append(
            "model %s correlates to measurement within %.2f%%, the tolerance is %.2f%%"
            % (record["id"], record["correlation_error_pct"], rules["max_correlation_error_pct"])
        )
    if record["kind"] == "passive-structure" and not record["em_verified"]:
        if usage["frequency_ghz"][1] >= rules["em_required_above_ghz"] - COVERAGE_TOLERANCE:
            statuses.append(PASSIVE_EM_VERIFICATION_MISSING)
            findings.append(
                "passive model %s carries no electromagnetic verification and the band "
                "reaches %.2f GHz" % (record["id"], usage["frequency_ghz"][1])
            )
    record = dict(record)
    record["coverage"] = coverage
    record["statuses"] = statuses
    record["findings"] = findings
    record["acceptable"] = not statuses
    return record


def validate_tool(tool):
    """Return a validated simulation-tool record."""
    if not isinstance(tool, dict):
        raise ValueError("tool must be a mapping")
    for key in ("name", "version"):
        if key not in tool:
            raise ValueError("tool missing required key '%s'" % key)
        if not isinstance(tool[key], str) or not tool[key].strip():
            raise ValueError("tool %s must be a non-empty string" % key)
    for key in ("version_controlled", "validation_evidence"):
        value = tool.get(key, False)
        if not isinstance(value, bool):
            raise ValueError("tool %s must be a boolean" % key)
    return {
        "name": tool["name"].strip(),
        "version": tool["version"].strip(),
        "version_controlled": bool(tool.get("version_controlled", False)),
        "validation_evidence": bool(tool.get("validation_evidence", False)),
    }


def assess_tool(tool, policy=None):
    """Assess one simulation tool and return its record."""
    rules = validate_model_policy(policy)
    record = validate_tool(tool)
    statuses = []
    findings = []
    if rules["require_tool_version_control"] and not record["version_controlled"]:
        statuses.append(TOOL_NOT_VERSION_CONTROLLED)
        findings.append(
            "tool %s %s is not under version control, so a simulation cannot be repeated"
            % (record["name"], record["version"])
        )
    if not record["validation_evidence"]:
        statuses.append(TOOL_VALIDATION_EVIDENCE_MISSING)
        findings.append(
            "tool %s %s carries no validation evidence for the analyses it is used for"
            % (record["name"], record["version"])
        )
    record = dict(record)
    record["statuses"] = statuses
    record["findings"] = findings
    record["acceptable"] = not statuses
    return record


def model_acceptance_fraction(records):
    """Return the fraction of assessed models that carry no finding."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of model records")
    accepted = 0
    for record in records:
        if not isinstance(record, dict) or "acceptable" not in record:
            raise ValueError("each record must be a mapping carrying 'acceptable'")
        if record["acceptable"]:
            accepted += 1
    return accepted / float(len(records))


def _worst_status(statuses):
    for status in STATUS_PRECEDENCE:
        if status in statuses:
            return status
    return DESIGN_KIT_ACCEPTABLE


def assess_design_kit(spec):
    """Run the full clause 5.3 model, kit and tool acceptance.

    spec keys: usage_envelope, models (non-empty), tools (non-empty),
    optional policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("usage_envelope", "models", "tools"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    models = spec["models"]
    tools = spec["tools"]
    if not isinstance(models, (list, tuple)) or not models:
        raise ValueError("spec['models'] must be a non-empty sequence")
    if not isinstance(tools, (list, tuple)) or not tools:
        raise ValueError("spec['tools'] must be a non-empty sequence")
    rules = validate_model_policy(spec.get("policy"))
    envelope = validate_usage_envelope(spec["usage_envelope"])
    model_records = [assess_model(model, envelope, rules) for model in models]
    seen = set()
    for record in model_records:
        if record["id"] in seen:
            raise ValueError("duplicate model id %r in the kit" % (record["id"],))
        seen.add(record["id"])
    tool_records = [assess_tool(tool, rules) for tool in tools]
    statuses = []
    findings = []
    for record in model_records + tool_records:
        statuses.extend(record["statuses"])
        findings.extend(record["findings"])
    verdict = _worst_status(statuses)
    return {
        "usage_envelope": envelope,
        "models": model_records,
        "tools": tool_records,
        "model_acceptance_fraction": model_acceptance_fraction(model_records),
        "verdict": verdict,
        "findings": findings,
        "acceptable": verdict == DESIGN_KIT_ACCEPTABLE,
    }
