"""Security services on a space communication system.

Anchor: ECSS-E-ST-50C clause 5.8.3 -- security.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the communication system protects the data
it carries according to how sensitive that data is. Three questions decide
whether it does, and all three are answerable from a design sheet:

  coverage  -- the services a flow declares against the services its
               sensitivity group needs; integrity, authentication, replay
               protection and confidentiality each stop a different attack,
               and one of them does not substitute for another;
  cost      -- what the tag, the initialisation vector and the replay counter
               take from every frame, and what payload rate is left;
  lifetime  -- how long a key lasts before the replay counter space or the
               declared per-key frame limit runs out, against how long the
               design has to go without rekeying.

Counter spaces are computed with integer bit arithmetic, so a width sitting
exactly on a power of two comes out the same on every host.
"""

import math

__all__ = [
    "COMPLETE",
    "DEFICIENT",
    "SENSITIVITY_SERVICES",
    "KNOWN_SERVICES",
    "REL_TOL",
    "validate_positive",
    "validate_nonnegative",
    "validate_count",
    "validate_width",
    "validate_sensitivity",
    "required_services",
    "service_coverage",
    "security_overhead_bits",
    "security_overhead_fraction",
    "protected_payload_bps",
    "counter_space",
    "rekey_interval_s",
    "min_counter_bits",
    "assess_security",
]

COMPLETE = "security-services-complete"
DEFICIENT = "security-services-deficient"

# What each sensitivity group has to have done to it. The groups are ordered
# by how much protection they need, and each one keeps everything the lighter
# group asked for.
SENSITIVITY_SERVICES = {
    "routine": frozenset(["integrity"]),
    "sensitive": frozenset(["integrity", "authentication", "replay-protection"]),
    "critical": frozenset(
        ["integrity", "authentication", "replay-protection", "confidentiality"]
    ),
}

KNOWN_SERVICES = frozenset(
    ["integrity", "authentication", "replay-protection", "confidentiality"]
)

REL_TOL = 1e-9


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_nonnegative(value, name="value"):
    """Return a non-negative float."""
    number = _number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive float."""
    number = _number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_count(value, name="count"):
    """Return a strictly positive whole count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number" % name)
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def validate_width(value, name="width_bits"):
    """Return a field width in whole bits, zero meaning the field is absent."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of bits" % name)
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def validate_sensitivity(value):
    """Return a known sensitivity group name."""
    if not isinstance(value, str):
        raise ValueError("sensitivity must be a string")
    name = value.strip().lower()
    if name not in SENSITIVITY_SERVICES:
        raise ValueError(
            "unknown sensitivity %r; expected one of %s"
            % (value, ", ".join(sorted(SENSITIVITY_SERVICES)))
        )
    return name


def required_services(sensitivity):
    """Return the services a flow of this sensitivity group needs."""
    return SENSITIVITY_SERVICES[validate_sensitivity(sensitivity)]


def service_coverage(sensitivity, declared):
    """Compare the services a flow declares against the ones it needs."""
    needed = required_services(sensitivity)
    if not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("declared services must be a sequence or set")
    names = set()
    for item in declared:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each declared service must be a non-empty string")
        names.add(item.strip().lower())
    unknown = sorted(names - KNOWN_SERVICES)
    if unknown:
        raise ValueError("unknown security service: %s" % ", ".join(unknown))
    return {
        "sensitivity": validate_sensitivity(sensitivity),
        "required": sorted(needed),
        "present": sorted(names & needed),
        "missing": sorted(needed - names),
        "beyond_requirement": sorted(names - needed),
        "complete": not (needed - names),
    }


def security_overhead_bits(tag_bits, iv_bits, counter_bits):
    """Return what the security services add to every frame."""
    return (
        validate_width(tag_bits, "tag_bits")
        + validate_width(iv_bits, "iv_bits")
        + validate_width(counter_bits, "counter_bits")
    )


def security_overhead_fraction(overhead_bits, payload_bits):
    """Return the share of a protected frame spent on security."""
    overhead = validate_width(overhead_bits, "overhead_bits")
    payload = validate_positive(payload_bits, "payload_bits")
    return overhead / (overhead + payload)


def protected_payload_bps(capacity_bps, overhead_bits, payload_bits):
    """Return the payload rate the link delivers once the frames are protected."""
    capacity = validate_positive(capacity_bps, "capacity_bps")
    return capacity * (
        1.0 - security_overhead_fraction(overhead_bits, payload_bits)
    )


def counter_space(counter_bits):
    """Return how many frames a replay counter of this width can number."""
    width = validate_width(counter_bits, "counter_bits")
    if width == 0:
        return 0
    return 1 << width


def rekey_interval_s(counter_bits, frame_rate_per_s, key_frame_limit):
    """Return how long one key lasts, and which bound ended it.

    A key is retired at whichever comes first: the replay counter running out
    of numbers, or the per-key frame limit the cryptographic design imposes.
    """
    rate = validate_positive(frame_rate_per_s, "frame_rate_per_s")
    limit = validate_count(key_frame_limit, "key_frame_limit")
    space = counter_space(counter_bits)
    if space == 0:
        raise ValueError("a replay counter of zero width numbers no frames")
    frames = min(space, limit)
    return {
        "counter_space": space,
        "key_frame_limit": limit,
        "frames": frames,
        "interval_s": frames / rate,
        "binding_bound": "replay-counter" if space <= limit else "key-frame-limit",
    }


def min_counter_bits(frame_rate_per_s, lifetime_s):
    """Return the narrowest replay counter that survives the key lifetime."""
    rate = validate_positive(frame_rate_per_s, "frame_rate_per_s")
    lifetime = validate_positive(lifetime_s, "lifetime_s")
    exact = rate * lifetime
    needed = int(math.ceil(exact - REL_TOL * exact))
    if needed < 1:
        needed = 1
    if needed == 1:
        return 1
    return (needed - 1).bit_length()


def assess_security(
    flows,
    tag_bits,
    iv_bits,
    counter_bits,
    payload_bits,
    capacity_bps,
    overhead_allowance,
    frame_rate_per_s,
    key_frame_limit,
    required_key_lifetime_s,
):
    """Grade the security a communication system applies to its data flows."""
    if not isinstance(flows, (list, tuple)) or not flows:
        raise ValueError("flows must be a non-empty sequence")
    allowance = validate_positive(overhead_allowance, "overhead_allowance")
    if allowance > 1.0:
        raise ValueError("overhead_allowance must be a fraction of the frame")
    required_lifetime = validate_positive(
        required_key_lifetime_s, "required_key_lifetime_s"
    )

    findings = []
    graded_flows = []
    for flow in flows:
        if not isinstance(flow, dict):
            raise ValueError("flow must be a mapping")
        name = flow.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("flow name must be a non-empty string")
        coverage = service_coverage(flow.get("sensitivity"), flow.get("services", []))
        coverage["name"] = name.strip()
        graded_flows.append(coverage)
        if coverage["missing"]:
            findings.append(
                "%s is a %s flow and declares no %s"
                % (
                    coverage["name"],
                    coverage["sensitivity"],
                    ", ".join(coverage["missing"]),
                )
            )

    overhead = security_overhead_bits(tag_bits, iv_bits, counter_bits)
    fraction = security_overhead_fraction(overhead, payload_bits)
    overhead_ok = fraction <= allowance + REL_TOL * allowance
    if not overhead_ok:
        findings.append(
            "security takes %.6g of each frame against a %.6g allowance; at this "
            "overhead a frame has to carry at least %.6g bit of payload"
            % (fraction, allowance, overhead * (1.0 - allowance) / allowance)
        )

    key = rekey_interval_s(counter_bits, frame_rate_per_s, key_frame_limit)
    lifetime_ok = key["interval_s"] >= required_lifetime - REL_TOL * required_lifetime
    needed_counter = min_counter_bits(frame_rate_per_s, required_lifetime)
    if not lifetime_ok:
        if key["binding_bound"] == "replay-counter":
            findings.append(
                "the replay counter runs out after %.6g s against a %.6g s key "
                "lifetime; %d bit carries it, and a counter that wraps under one "
                "key stops protecting against replay"
                % (key["interval_s"], required_lifetime, needed_counter)
            )
        else:
            findings.append(
                "the per-key frame limit is reached after %.6g s against a %.6g s "
                "key lifetime; the counter is not the bound, the key schedule is"
                % (key["interval_s"], required_lifetime)
            )

    coverage_ok = all(f["complete"] for f in graded_flows)
    return {
        "flows": graded_flows,
        "overhead_bits": overhead,
        "overhead_fraction": fraction,
        "overhead_allowance": allowance,
        "overhead_within_allowance": overhead_ok,
        "protected_payload_bps": protected_payload_bps(
            capacity_bps, overhead, payload_bits
        ),
        "key": key,
        "required_key_lifetime_s": required_lifetime,
        "required_counter_bits": needed_counter,
        "key_lifetime_met": lifetime_ok,
        "coverage_complete": coverage_ok,
        "verdict": COMPLETE
        if (coverage_ok and overhead_ok and lifetime_ok)
        else DEFICIENT,
        "findings": findings,
    }
