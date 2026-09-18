"""Telemetry authentication and encryption assessment.

Anchor: ECSS-E-ST-50C clause 5.5.7 (telemetry is authenticated and/or
encrypted where the mission security requirements call for it). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each telemetry stream and the protection it declares.
2. Map the stream's sensitivity tier onto the services it owes, and compare
   with the services actually applied; confidentiality without integrity is
   refused outright.
3. Compute the per-frame overhead of tag, initialisation vector and block
   padding, and the useful throughput that survives it.
4. Compare the useful throughput with the demand the stream must carry.
5. Size the key against the protection period, and compare the frames sent
   under one key with the span of the uniqueness counter.
"""

import math

__all__ = [
    "THROUGHPUT_TOLERANCE_BPS",
    "TIER_SERVICES",
    "MINIMUM_KEY_BITS_BY_PERIOD",
    "validate_stream",
    "validate_stream_set",
    "services_owed",
    "service_gaps",
    "protection_overhead_bits",
    "useful_throughput_bps",
    "minimum_key_bits",
    "key_strength_findings",
    "frames_under_one_key",
    "counter_span",
    "counter_exhaustion_findings",
    "assess_telemetry_protection",
]

# The throughput comparison is a product against a declared demand: an exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of relaxing the demand.
THROUGHPUT_TOLERANCE_BPS = 1e-9

# Sensitivity tiers, from the openly published through to the stream whose
# disclosure would itself be the incident. Each tier names the services owed.
TIER_SERVICES = {
    "open": {"authentication": False, "confidentiality": False},
    "attributable": {"authentication": True, "confidentiality": False},
    "sensitive": {"authentication": True, "confidentiality": True},
    "critical": {"authentication": True, "confidentiality": True},
}

# Minimum symmetric key length credible for a given protection period, in
# whole years. Read as: a period at or below the key applies.
MINIMUM_KEY_BITS_BY_PERIOD = ((1, 112), (10, 128), (30, 256))


def _require_text(value, label):
    """Return a non-empty stripped string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _require_positive(value, label):
    """Return a positive finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_positive_int(value, label):
    """Return a positive integer or raise."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_flag(value, label):
    """Return a boolean or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_stream(stream):
    """Return a normalised protected-telemetry stream record."""
    if not isinstance(stream, dict):
        raise ValueError("stream must be a mapping, got %r" % (stream,))
    for key in ("name", "tier", "frame_payload_bits", "frame_rate_hz"):
        if key not in stream:
            raise ValueError("stream missing required key '%s'" % key)
    tier = _require_text(stream["tier"], "tier")
    if tier not in TIER_SERVICES:
        raise ValueError(
            "tier %r is not one of %s" % (tier, ", ".join(sorted(TIER_SERVICES)))
        )
    return {
        "name": _require_text(stream["name"], "name"),
        "tier": tier,
        "frame_payload_bits": _require_positive_int(
            stream["frame_payload_bits"], "frame_payload_bits"
        ),
        "frame_rate_hz": _require_positive(stream["frame_rate_hz"], "frame_rate_hz"),
        "authentication_applied": _require_flag(
            stream.get("authentication_applied", False), "authentication_applied"
        ),
        "confidentiality_applied": _require_flag(
            stream.get("confidentiality_applied", False), "confidentiality_applied"
        ),
    }


def validate_stream_set(streams):
    """Return the validated stream list; names must be unique and non-empty."""
    if isinstance(streams, dict) or not isinstance(streams, (list, tuple)):
        raise ValueError("streams must be a sequence of stream mappings")
    if not streams:
        raise ValueError("the stream set must not be empty")
    records = [validate_stream(item) for item in streams]
    seen = set()
    for record in records:
        if record["name"] in seen:
            raise ValueError("duplicate stream name '%s'" % record["name"])
        seen.add(record["name"])
    return records


def services_owed(tier):
    """Return the services a sensitivity tier owes."""
    name = _require_text(tier, "tier")
    if name not in TIER_SERVICES:
        raise ValueError(
            "tier %r is not one of %s" % (name, ", ".join(sorted(TIER_SERVICES)))
        )
    return dict(TIER_SERVICES[name])


def service_gaps(stream):
    """Return the findings where the applied services fall short of the tier."""
    record = validate_stream(stream)
    owed = services_owed(record["tier"])
    findings = []
    if owed["authentication"] and not record["authentication_applied"]:
        findings.append(
            "stream '%s' is tier '%s' and owes authentication, which is not applied"
            % (record["name"], record["tier"])
        )
    if owed["confidentiality"] and not record["confidentiality_applied"]:
        findings.append(
            "stream '%s' is tier '%s' and owes confidentiality, which is not applied"
            % (record["name"], record["tier"])
        )
    if record["confidentiality_applied"] and not record["authentication_applied"]:
        findings.append(
            "stream '%s' is encrypted without an integrity service; a modified frame "
            "still decrypts and the receiver cannot detect it" % record["name"]
        )
    return findings


def protection_overhead_bits(stream, tag_bits, iv_bits, block_bits):
    """Return the per-frame overhead the applied protection costs, in bits."""
    record = validate_stream(stream)
    tag = _require_positive_int(tag_bits, "tag_bits")
    initialisation = _require_positive_int(iv_bits, "iv_bits")
    block = _require_positive_int(block_bits, "block_bits")
    overhead = 0
    if record["authentication_applied"]:
        overhead += tag
    if record["confidentiality_applied"]:
        overhead += initialisation
        overhead += (-record["frame_payload_bits"]) % block
    return overhead


def useful_throughput_bps(stream, overhead_bits):
    """Return the payload throughput that survives the per-frame overhead."""
    record = validate_stream(stream)
    if not isinstance(overhead_bits, int) or isinstance(overhead_bits, bool):
        raise ValueError("overhead_bits must be an integer, got %r" % (overhead_bits,))
    if overhead_bits < 0:
        raise ValueError("overhead_bits must be non-negative, got %d" % overhead_bits)
    remaining = record["frame_payload_bits"] - overhead_bits
    if remaining <= 0:
        return 0.0
    return remaining * record["frame_rate_hz"]


def minimum_key_bits(protection_years):
    """Return the minimum symmetric key length for a protection period in years."""
    years = _require_positive(protection_years, "protection_years")
    for bound, bits in MINIMUM_KEY_BITS_BY_PERIOD:
        if years <= bound:
            return bits
    return MINIMUM_KEY_BITS_BY_PERIOD[-1][1]


def key_strength_findings(key_bits, protection_years):
    """Return the findings for a key too short for the period it must stand."""
    declared = _require_positive_int(key_bits, "key_bits")
    needed = minimum_key_bits(protection_years)
    if declared < needed:
        return [
            "key length %d bits is below the %d bits credible over a %g year "
            "protection period" % (declared, needed, float(protection_years))
        ]
    return []


def frames_under_one_key(frame_rate_hz, key_period_s):
    """Return the number of frames sent under one key."""
    rate = _require_positive(frame_rate_hz, "frame_rate_hz")
    period = _require_positive(key_period_s, "key_period_s")
    return rate * period


def counter_span(counter_bits):
    """Return the number of distinct values a uniqueness counter can take."""
    bits = _require_positive_int(counter_bits, "counter_bits")
    return 2 ** bits


def counter_exhaustion_findings(stream, counter_bits, key_period_s):
    """Return the findings for a counter that wraps inside one key period."""
    record = validate_stream(stream)
    if not record["confidentiality_applied"]:
        return []
    span = counter_span(counter_bits)
    frames = frames_under_one_key(record["frame_rate_hz"], key_period_s)
    if math.isclose(frames, float(span), rel_tol=1e-12, abs_tol=0.0):
        return []
    if frames > float(span):
        return [
            "stream '%s' sends %.6g frames under one key but the %d bit counter holds "
            "%d values; two frames would share an initialisation vector"
            % (record["name"], frames, counter_bits, span)
        ]
    return []


def assess_telemetry_protection(spec):
    """Run the full clause 5.5.7 telemetry protection assessment.

    spec keys: streams, tag_bits, iv_bits, block_bits, key_bits,
    protection_years, counter_bits, key_period_s, optional demand_bps map.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("streams", "tag_bits", "iv_bits", "block_bits", "key_bits",
                "protection_years", "counter_bits", "key_period_s"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    records = validate_stream_set(spec["streams"])
    demands = spec.get("demand_bps", {})
    if not isinstance(demands, dict):
        raise ValueError("demand_bps must be a mapping of stream name to bit rate")

    findings = []
    findings.extend(key_strength_findings(spec["key_bits"], spec["protection_years"]))

    per_stream = {}
    for record in records:
        name = record["name"]
        findings.extend(service_gaps(record))
        overhead = protection_overhead_bits(
            record, spec["tag_bits"], spec["iv_bits"], spec["block_bits"]
        )
        throughput = useful_throughput_bps(record, overhead)
        carries = True
        if name in demands:
            demand = _require_positive(demands[name], "demand for '%s'" % name)
            carries = throughput > demand or math.isclose(
                throughput, demand, rel_tol=0.0, abs_tol=THROUGHPUT_TOLERANCE_BPS
            )
            if not carries:
                findings.append(
                    "stream '%s' carries %.6g bit/s after protection overhead but has "
                    "to carry %.6g bit/s" % (name, throughput, demand)
                )
        findings.extend(
            counter_exhaustion_findings(record, spec["counter_bits"], spec["key_period_s"])
        )
        per_stream[name] = {
            "tier": record["tier"],
            "services_owed": services_owed(record["tier"]),
            "overhead_bits": overhead,
            "useful_throughput_bps": throughput,
            "carries_demand": carries,
        }

    return {
        "per_stream": per_stream,
        "minimum_key_bits": minimum_key_bits(spec["protection_years"]),
        "counter_span": counter_span(spec["counter_bits"]),
        "compliant": not findings,
        "findings": findings,
    }
