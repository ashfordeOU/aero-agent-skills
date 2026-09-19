"""Thermal telemetry, commanding and on-board software interface requirements.

Anchor: ECSS-E-ST-31C clauses 4.3.5 and 4.3.6 (interface requirements
towards the data handling subsystem and towards on-board software).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every thermal telemetry channel: the temperature span its
   acquisition chain covers, the converter width, the sensor tolerance, the
   residual chain error and the sampling period.
2. Turn the span and the converter width into a quantisation step, and
   combine half that step with the sensor and chain errors on a root-sum-
   square basis to get the temperature knowledge the channel delivers;
   compare it with the knowledge the monitored item requires.
3. Grade the sampling period against the thermal time constant of the item:
   a control loop or a transient reconstruction needs several samples per
   time constant, not one.
4. Sum the channel bit rates into the telemetry bandwidth the data handling
   subsystem has to carry, and compare it with the allocation.
5. Check every heater control line the on-board software owns: the monitor
   limits and the control setpoints must be strictly ordered, a command
   identifier, a status telemetry identifier and a limit pair must all be
   declared, and the control deadband must be wide enough relative to the
   channel knowledge that the loop does not chatter on measurement noise.
"""

import math

__all__ = [
    "MIN_SAMPLES_PER_TIME_CONSTANT",
    "DEADBAND_KNOWLEDGE_FACTOR",
    "KNOWLEDGE_TOLERANCE_K",
    "validate_positive",
    "quantisation_step_k",
    "channel_knowledge_k",
    "samples_per_time_constant",
    "channel_bit_rate_bps",
    "evaluate_channel",
    "telemetry_bandwidth_bps",
    "validate_limit_ordering",
    "deadband_adequate",
    "predicted_cycle_period_s",
    "evaluate_control_line",
    "assess_tm_tc_interfaces",
]

# A transient the software has to follow needs several samples inside the
# item time constant; one sample per time constant reconstructs nothing.
MIN_SAMPLES_PER_TIME_CONSTANT = 5.0

# The control deadband has to stand clear of the measurement knowledge, or
# the loop switches on noise rather than on temperature.
DEADBAND_KNOWLEDGE_FACTOR = 2.0

# Knowledge comparisons are root-sum-square results against a requirement;
# absorb the representation error at the boundary rather than relaxing the
# required accuracy.
KNOWLEDGE_TOLERANCE_K = 1e-9


def validate_positive(label, value, allow_zero=False):
    """Return value as a positive finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, out))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def quantisation_step_k(span_k, converter_bits):
    """Return the temperature step of one converter count, in kelvin."""
    span = validate_positive("span_k", span_k)
    if not isinstance(converter_bits, int) or isinstance(converter_bits, bool):
        raise ValueError("converter_bits must be an integer, got %r" % (converter_bits,))
    if converter_bits < 2:
        raise ValueError("converter_bits must be at least two, got %d" % converter_bits)
    if converter_bits > 32:
        raise ValueError(
            "converter_bits above 32 is not a thermal acquisition chain, got %d"
            % converter_bits
        )
    return span / float((1 << converter_bits) - 1)


def channel_knowledge_k(step_k, sensor_tolerance_k, chain_error_k):
    """Return the root-sum-square temperature knowledge of a channel."""
    step = validate_positive("step_k", step_k)
    sensor = validate_positive("sensor_tolerance_k", sensor_tolerance_k, allow_zero=True)
    chain = validate_positive("chain_error_k", chain_error_k, allow_zero=True)
    half_step = step / 2.0
    return math.sqrt(half_step * half_step + sensor * sensor + chain * chain)


def samples_per_time_constant(time_constant_s, sample_period_s):
    """Return how many samples fall inside one item thermal time constant."""
    tau = validate_positive("time_constant_s", time_constant_s)
    period = validate_positive("sample_period_s", sample_period_s)
    return tau / period


def channel_bit_rate_bps(converter_bits, sample_period_s):
    """Return the telemetry rate one channel contributes, in bits per second."""
    if not isinstance(converter_bits, int) or isinstance(converter_bits, bool):
        raise ValueError("converter_bits must be an integer, got %r" % (converter_bits,))
    if converter_bits < 2:
        raise ValueError("converter_bits must be at least two, got %d" % converter_bits)
    period = validate_positive("sample_period_s", sample_period_s)
    return converter_bits / period


def evaluate_channel(channel):
    """Evaluate one thermal telemetry channel and return its record."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping")
    for key in ("name", "span_k", "converter_bits", "sensor_tolerance_k",
                "chain_error_k", "sample_period_s", "required_knowledge_k",
                "time_constant_s"):
        if key not in channel:
            raise ValueError("channel record missing required key %r" % key)
    step = quantisation_step_k(channel["span_k"], channel["converter_bits"])
    knowledge = channel_knowledge_k(
        step, channel["sensor_tolerance_k"], channel["chain_error_k"]
    )
    required = validate_positive("required_knowledge_k", channel["required_knowledge_k"])
    knowledge_ok = knowledge < required or math.isclose(
        knowledge, required, rel_tol=0.0, abs_tol=KNOWLEDGE_TOLERANCE_K
    )
    samples = samples_per_time_constant(
        channel["time_constant_s"], channel["sample_period_s"]
    )
    sampling_ok = samples > MIN_SAMPLES_PER_TIME_CONSTANT or math.isclose(
        samples, MIN_SAMPLES_PER_TIME_CONSTANT, rel_tol=1e-12, abs_tol=0.0
    )
    rate = channel_bit_rate_bps(channel["converter_bits"], channel["sample_period_s"])
    findings = []
    if not knowledge_ok:
        findings.append(
            "%s: knowledge %.4f K is coarser than the %.4f K the item requires"
            % (channel["name"], knowledge, required)
        )
    if not sampling_ok:
        findings.append(
            "%s: %.2f samples per time constant is below the %.1f a transient "
            "reconstruction needs"
            % (channel["name"], samples, MIN_SAMPLES_PER_TIME_CONSTANT)
        )
    return {
        "name": channel["name"],
        "quantisation_step_k": step,
        "knowledge_k": knowledge,
        "required_knowledge_k": required,
        "samples_per_time_constant": samples,
        "bit_rate_bps": rate,
        "compliant": knowledge_ok and sampling_ok,
        "findings": findings,
    }


def telemetry_bandwidth_bps(records):
    """Return the summed telemetry bandwidth of a channel record set."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of channel records")
    total = 0.0
    for record in records:
        if not isinstance(record, dict) or "bit_rate_bps" not in record:
            raise ValueError("each record must carry 'bit_rate_bps'")
        total += float(record["bit_rate_bps"])
    return total


def validate_limit_ordering(low_alarm_c, switch_on_c, switch_off_c, high_alarm_c):
    """Return the validated monitor and control limit set, strictly ordered."""
    values = []
    for label, value in (("low_alarm_c", low_alarm_c), ("switch_on_c", switch_on_c),
                         ("switch_off_c", switch_off_c), ("high_alarm_c", high_alarm_c)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
        values.append(float(value))
    for index in range(1, len(values)):
        if values[index] <= values[index - 1]:
            raise ValueError(
                "monitor and control limits must strictly increase as "
                "low alarm, switch on, switch off, high alarm; got %s"
                % (values,)
            )
    return tuple(values)


def deadband_adequate(deadband_k, knowledge_k):
    """Return True when the deadband stands clear of the channel knowledge."""
    deadband = validate_positive("deadband_k", deadband_k)
    knowledge = validate_positive("knowledge_k", knowledge_k)
    floor = DEADBAND_KNOWLEDGE_FACTOR * knowledge
    return deadband > floor or math.isclose(deadband, floor, rel_tol=1e-12, abs_tol=0.0)


def predicted_cycle_period_s(deadband_k, heating_rate_k_per_s, cooling_rate_k_per_s):
    """Return the predicted thermostatic cycle period of a heater line."""
    deadband = validate_positive("deadband_k", deadband_k)
    heating = validate_positive("heating_rate_k_per_s", heating_rate_k_per_s)
    cooling = validate_positive("cooling_rate_k_per_s", cooling_rate_k_per_s)
    return deadband / heating + deadband / cooling


def evaluate_control_line(line, knowledge_k):
    """Evaluate one software-owned heater control line and return its record."""
    if not isinstance(line, dict):
        raise ValueError("line must be a mapping")
    for key in ("name", "command_id", "status_telemetry_id", "low_alarm_c",
                "switch_on_c", "switch_off_c", "high_alarm_c",
                "heating_rate_k_per_s", "cooling_rate_k_per_s"):
        if key not in line:
            raise ValueError("control line record missing required key %r" % key)
    for key in ("command_id", "status_telemetry_id"):
        if not isinstance(line[key], str) or not line[key].strip():
            raise ValueError(
                "%s of control line %r must be a non-empty identifier"
                % (key, line["name"])
            )
    limits = validate_limit_ordering(
        line["low_alarm_c"], line["switch_on_c"],
        line["switch_off_c"], line["high_alarm_c"],
    )
    deadband = limits[2] - limits[1]
    adequate = deadband_adequate(deadband, knowledge_k)
    period = predicted_cycle_period_s(
        deadband, line["heating_rate_k_per_s"], line["cooling_rate_k_per_s"]
    )
    findings = []
    if not adequate:
        findings.append(
            "%s: deadband %.4f K is not clear of %.1f times the %.4f K channel "
            "knowledge; the loop will switch on measurement noise"
            % (line["name"], deadband, DEADBAND_KNOWLEDGE_FACTOR, knowledge_k)
        )
    return {
        "name": line["name"],
        "limits_c": limits,
        "deadband_k": deadband,
        "deadband_adequate": adequate,
        "predicted_cycle_period_s": period,
        "compliant": adequate,
        "findings": findings,
    }


def assess_tm_tc_interfaces(spec):
    """Run the full clause 4.3.5 and 4.3.6 interface assessment.

    spec keys: channels, control_lines, bandwidth_allocation_bps.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("channels", "control_lines", "bandwidth_allocation_bps"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    channels = spec["channels"]
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("spec['channels'] must be a non-empty sequence")
    lines = spec["control_lines"]
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("spec['control_lines'] must be a non-empty sequence")
    channel_records = [evaluate_channel(channel) for channel in channels]
    knowledge_by_name = {r["name"]: r["knowledge_k"] for r in channel_records}
    if len(knowledge_by_name) != len(channel_records):
        raise ValueError("two telemetry channels share a name; records cannot be traced")
    line_records = []
    for line in lines:
        if not isinstance(line, dict) or "channel" not in line:
            raise ValueError("each control line must name the 'channel' it reads")
        if line["channel"] not in knowledge_by_name:
            raise ValueError(
                "control line %r reads channel %r, which is not declared"
                % (line.get("name", "unnamed"), line["channel"])
            )
        line_records.append(
            evaluate_control_line(line, knowledge_by_name[line["channel"]])
        )
    bandwidth = telemetry_bandwidth_bps(channel_records)
    allocation = validate_positive(
        "bandwidth_allocation_bps", spec["bandwidth_allocation_bps"]
    )
    bandwidth_ok = bandwidth < allocation or math.isclose(
        bandwidth, allocation, rel_tol=1e-12, abs_tol=0.0
    )
    findings = []
    for record in channel_records:
        findings.extend(record["findings"])
    for record in line_records:
        findings.extend(record["findings"])
    if not bandwidth_ok:
        findings.append(
            "thermal telemetry bandwidth %.3f bit/s exceeds the %.3f bit/s "
            "allocated by the data handling subsystem" % (bandwidth, allocation)
        )
    return {
        "channels": channel_records,
        "control_lines": line_records,
        "telemetry_bandwidth_bps": bandwidth,
        "bandwidth_allocation_bps": allocation,
        "compliant": bandwidth_ok
        and all(r["compliant"] for r in channel_records)
        and all(r["compliant"] for r in line_records),
        "findings": findings,
    }
