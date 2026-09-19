"""Additional mechanism control-design rules: accuracy, noise, command limiting.

Anchor: ECSS-E-ST-33-01C clause 4.7.8.5 (mechanism control system -- the design
rules that sit beside loop shaping: the positioning accuracy the loop has to
deliver, the sensor noise it is allowed to pass, and the limiting that keeps a
command inside what the actuator and the structure can take). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Build the accuracy budget from its two kinds of contributor: systematic
   terms that add directly (sensor bias, alignment offset, thermal drift,
   backlash offset) and random terms that combine in quadrature (sensor noise,
   quantization, disturbance response), the random part expanded by the
   declared coverage factor.
2. Turn the sensor description into random contributors the loop actually
   passes: encoder quantization as its step over the square root of twelve,
   and broadband noise as its density integrated over the closed-loop noise
   bandwidth.
3. Grade the total against the allocated accuracy, and name the contributor
   that drives it.
4. Apply command limiting to a commanded profile -- magnitude clamp first,
   then rate clamp over the sample interval -- and report which samples were
   limited and by how much.
5. Grade the actuator torque or force demand against what is available for the
   required margin, and report every finding: accuracy shortfall, a noise term
   dominating the budget, an undeclared limiter, saturated commands and an
   actuator margin shortfall.
"""

import math

__all__ = [
    "COMPARISON_TOLERANCE",
    "DOMINANCE_FRACTION",
    "validate_positive",
    "validate_non_negative",
    "validate_terms",
    "quantization_sigma",
    "noise_sigma_in_band",
    "combine_systematic",
    "combine_random",
    "accuracy_budget",
    "dominant_contributor",
    "assess_accuracy",
    "limit_command",
    "apply_command_limits",
    "actuator_margin",
    "assess_additional_requirements",
]

# Budget and margin comparisons can land a few ULPs either side of an exact
# equality. Absorb the representation error here, never by relaxing the limit.
COMPARISON_TOLERANCE = 1e-9

# A single contributor holding this share of the expanded budget is reported
# as the driver, because reducing anything else cannot recover the budget.
DOMINANCE_FRACTION = 0.5


def validate_positive(value, label):
    """Return value as a positive finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_non_negative(value, label):
    """Return value as a non-negative finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def validate_terms(terms, label):
    """Return a mapping of named error contributors as non-negative floats."""
    if terms is None:
        return {}
    if not isinstance(terms, dict):
        raise ValueError("%s must be a mapping of name to magnitude" % label)
    validated = {}
    for name, value in terms.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("%s keys must be non-empty strings" % label)
        validated[name] = validate_non_negative(value, "%s[%r]" % (label, name))
    return validated


def quantization_sigma(step):
    """Return the standard deviation a uniform quantization step contributes."""
    lsb = validate_positive(step, "step")
    return lsb / math.sqrt(12.0)


def noise_sigma_in_band(noise_density, noise_bandwidth_hz):
    """Return the noise a spectral density contributes over a noise bandwidth."""
    density = validate_non_negative(noise_density, "noise_density")
    bandwidth = validate_positive(noise_bandwidth_hz, "noise_bandwidth_hz")
    return density * math.sqrt(bandwidth)


def combine_systematic(terms):
    """Return the direct sum of the systematic contributors."""
    validated = validate_terms(terms, "systematic_terms")
    return math.fsum(validated.values())


def combine_random(terms):
    """Return the root-sum-square of the random contributors."""
    validated = validate_terms(terms, "random_terms")
    return math.sqrt(math.fsum(value * value for value in validated.values()))


def accuracy_budget(systematic_terms, random_terms, coverage_factor=3.0):
    """Return the expanded accuracy budget and its two parts."""
    k = validate_positive(coverage_factor, "coverage_factor")
    systematic = combine_systematic(systematic_terms)
    random_part = combine_random(random_terms)
    return {
        "systematic_total": systematic,
        "random_sigma": random_part,
        "coverage_factor": k,
        "expanded_total": systematic + k * random_part,
    }


def dominant_contributor(systematic_terms, random_terms, coverage_factor=3.0):
    """Return the contributor holding the largest share of the expanded budget."""
    k = validate_positive(coverage_factor, "coverage_factor")
    systematic = validate_terms(systematic_terms, "systematic_terms")
    random_part = validate_terms(random_terms, "random_terms")
    shares = {}
    for name, value in systematic.items():
        shares[name] = value
    for name, value in random_part.items():
        if name in shares:
            raise ValueError("contributor %r declared as both systematic and random" % name)
        shares[name] = k * value
    if not shares:
        raise ValueError("no contributors declared; the budget cannot be attributed")
    total = math.fsum(shares.values())
    name = sorted(shares.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
    fraction = 0.0 if total == 0.0 else shares[name] / total
    return {"name": name, "contribution": shares[name], "fraction": fraction}


def assess_accuracy(spec):
    """Grade the positioning accuracy budget against the allocated accuracy."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "allocated_accuracy" not in spec:
        raise ValueError("spec missing required key 'allocated_accuracy'")
    allocated = validate_positive(spec["allocated_accuracy"], "allocated_accuracy")
    systematic = dict(validate_terms(spec.get("systematic_terms"), "systematic_terms"))
    random_part = dict(validate_terms(spec.get("random_terms"), "random_terms"))
    if spec.get("sensor_quantization_step") is not None:
        random_part["sensor-quantization"] = quantization_sigma(
            spec["sensor_quantization_step"]
        )
    if spec.get("sensor_noise_density") is not None:
        if spec.get("noise_bandwidth_hz") is None:
            raise ValueError(
                "sensor_noise_density needs noise_bandwidth_hz to become an error term"
            )
        random_part["sensor-noise"] = noise_sigma_in_band(
            spec["sensor_noise_density"], spec["noise_bandwidth_hz"]
        )
    if not systematic and not random_part:
        raise ValueError("no accuracy contributors declared")
    coverage = spec.get("coverage_factor", 3.0)
    budget = accuracy_budget(systematic, random_part, coverage)
    driver = dominant_contributor(systematic, random_part, coverage)
    total = budget["expanded_total"]
    met = total < allocated or math.isclose(
        total, allocated, rel_tol=COMPARISON_TOLERANCE, abs_tol=0.0
    )
    return {
        "allocated_accuracy": allocated,
        "systematic_total": budget["systematic_total"],
        "random_sigma": budget["random_sigma"],
        "coverage_factor": budget["coverage_factor"],
        "expanded_total": total,
        "utilisation": total / allocated,
        "accuracy_met": met,
        "driver": driver,
        "random_terms": random_part,
        "systematic_terms": systematic,
    }


def limit_command(command, previous, magnitude_limit, rate_limit, sample_time_s):
    """Clamp one command sample in magnitude, then in rate over the interval."""
    for label, value in (("command", command), ("previous", previous)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    limit = validate_positive(magnitude_limit, "magnitude_limit")
    rate = validate_positive(rate_limit, "rate_limit")
    dt = validate_positive(sample_time_s, "sample_time_s")
    requested = float(command)
    magnitude_limited = max(-limit, min(limit, requested))
    step = rate * dt
    lower = float(previous) - step
    upper = float(previous) + step
    applied = max(lower, min(upper, magnitude_limited))
    return {
        "requested": requested,
        "applied": applied,
        "magnitude_saturated": abs(requested) > limit
        and not math.isclose(abs(requested), limit, rel_tol=COMPARISON_TOLERANCE),
        "rate_saturated": abs(magnitude_limited - float(previous)) > step
        and not math.isclose(
            abs(magnitude_limited - float(previous)), step, rel_tol=COMPARISON_TOLERANCE
        ),
    }


def apply_command_limits(commands, initial, magnitude_limit, rate_limit, sample_time_s):
    """Run a commanded profile through the limiter and report every clamp."""
    if not isinstance(commands, (list, tuple)) or not commands:
        raise ValueError("commands must be a non-empty sequence")
    previous = initial
    if not isinstance(previous, (int, float)) or isinstance(previous, bool):
        raise ValueError("initial must be a real number")
    records = []
    for index, command in enumerate(commands):
        record = limit_command(
            command, previous, magnitude_limit, rate_limit, sample_time_s
        )
        record["index"] = index
        records.append(record)
        previous = record["applied"]
    return records


def actuator_margin(required_effort, available_effort):
    """Return the actuator capability margin as a fraction of the demand."""
    required = validate_positive(required_effort, "required_effort")
    available = validate_positive(available_effort, "available_effort")
    return (available - required) / required


def assess_additional_requirements(spec):
    """Run the full clause 4.7.8.5 additional control-design assessment.

    spec keys: allocated_accuracy plus systematic_terms and/or random_terms
    (optionally sensor_quantization_step, sensor_noise_density and
    noise_bandwidth_hz), optional coverage_factor; command_profile with
    initial_command, magnitude_limit, rate_limit and sample_time_s when a
    limiter is declared; required_effort, available_effort and
    required_actuator_margin when actuator capability is graded.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    accuracy = assess_accuracy(spec)
    findings = []
    if not accuracy["accuracy_met"]:
        findings.append(
            "accuracy budget %.6g exceeds the allocated %.6g"
            % (accuracy["expanded_total"], accuracy["allocated_accuracy"])
        )
    driver = accuracy["driver"]
    if driver["fraction"] > DOMINANCE_FRACTION and driver["name"] in accuracy[
        "random_terms"
    ]:
        findings.append(
            "random term %r holds %.1f%% of the budget; the loop passes more sensor "
            "noise than everything else combined"
            % (driver["name"], 100.0 * driver["fraction"])
        )
    limiting = None
    profile = spec.get("command_profile")
    if profile is None:
        findings.append(
            "no command limiter declared; magnitude and rate clamping are required "
            "before a command reaches the actuator"
        )
    else:
        if not isinstance(profile, dict):
            raise ValueError("command_profile must be a mapping")
        for key in ("commands", "magnitude_limit", "rate_limit", "sample_time_s"):
            if key not in profile:
                raise ValueError("command_profile missing required key '%s'" % key)
        records = apply_command_limits(
            profile["commands"],
            profile.get("initial_command", 0.0),
            profile["magnitude_limit"],
            profile["rate_limit"],
            profile["sample_time_s"],
        )
        magnitude_hits = [r["index"] for r in records if r["magnitude_saturated"]]
        rate_hits = [r["index"] for r in records if r["rate_saturated"]]
        limiting = {
            "records": records,
            "magnitude_saturated_samples": magnitude_hits,
            "rate_saturated_samples": rate_hits,
        }
        if magnitude_hits:
            findings.append(
                "command magnitude limit reached at sample(s) %s"
                % ", ".join(str(i) for i in magnitude_hits)
            )
        if rate_hits:
            findings.append(
                "command rate limit reached at sample(s) %s"
                % ", ".join(str(i) for i in rate_hits)
            )
    capability = None
    if spec.get("required_effort") is not None:
        if spec.get("available_effort") is None:
            raise ValueError("required_effort needs available_effort to be graded")
        achieved = actuator_margin(spec["required_effort"], spec["available_effort"])
        needed = validate_non_negative(
            spec.get("required_actuator_margin", 0.0), "required_actuator_margin"
        )
        met = achieved > needed or math.isclose(
            achieved, needed, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE
        )
        capability = {
            "achieved_margin": achieved,
            "required_margin": needed,
            "margin_met": met,
        }
        if not met:
            findings.append(
                "actuator margin %.4f is below the required %.4f" % (achieved, needed)
            )
    return {
        "accuracy": accuracy,
        "limiting": limiting,
        "capability": capability,
        "compliant": not findings,
        "findings": findings,
    }
