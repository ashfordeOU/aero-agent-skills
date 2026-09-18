"""Initiator-only conformance profile for a SpaceWire RMAP implementation.

Anchor: ECSS-E-ST-50-52C clause 5.8.2.2 (requirements placed on an
implementation that takes the initiator role only). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise and validate a declared RMAP conformance profile: the role word,
   the capability tokens claimed, the transaction-identifier width and the
   outstanding-transaction budget.
2. Derive, from the declared role, the capability set the device owes and the
   capability set it has no business claiming, so an initiator-only device is
   graded against initiator duties instead of the full protocol.
3. Grade the identifier arithmetic: an initiator that asks for replies has to
   be able to tell them apart, so a non-zero identifier width is owed and the
   outstanding-transaction budget must fit inside the identifier space.
4. Grade the reply timeout against a round-trip estimate built from the link
   rate, the bytes on the wire in each direction and the declared target
   turnaround.
5. Return a conformance record: owed-but-missing capabilities, claimed-but-
   out-of-scope capabilities, the identifier and timeout findings, and a
   single conformant flag.
"""

import math

__all__ = [
    "ROLE_INITIATOR_ONLY",
    "ROLE_TARGET_ONLY",
    "ROLE_INITIATOR_AND_TARGET",
    "ROLES",
    "INITIATOR_DUTIES",
    "TARGET_DUTIES",
    "ALL_CAPABILITIES",
    "BITS_PER_CHARACTER",
    "TIMEOUT_TOLERANCE_MS",
    "validate_profile",
    "owed_capabilities",
    "out_of_scope_capabilities",
    "identifier_space",
    "missing_capabilities",
    "surplus_capabilities",
    "round_trip_estimate_ms",
    "grade_identifier_budget",
    "grade_reply_timeout",
    "assess_initiator_only",
]

ROLE_INITIATOR_ONLY = "initiator-only"
ROLE_TARGET_ONLY = "target-only"
ROLE_INITIATOR_AND_TARGET = "initiator-and-target"
ROLES = (ROLE_INITIATOR_ONLY, ROLE_TARGET_ONLY, ROLE_INITIATOR_AND_TARGET)

# Duties that belong to the command-issuing side of a transaction.
INITIATOR_DUTIES = (
    "command-transmission",
    "header-crc-generation",
    "data-crc-generation",
    "transaction-identifier-allocation",
    "reply-address-generation",
    "reply-reception",
    "status-code-interpretation",
)

# Duties that belong to the command-servicing side of a transaction. An
# initiator-only device never runs these, so claiming one is a scope error.
TARGET_DUTIES = (
    "destination-key-authorisation",
    "memory-access-execution",
    "reply-generation",
    "status-code-generation",
    "verify-buffer-management",
    "command-authorisation-policy",
)

ALL_CAPABILITIES = tuple(sorted(set(INITIATOR_DUTIES) | set(TARGET_DUTIES)))

# A character on the serial link costs ten bit times once the parity and
# control bit are counted alongside the eight data bits.
BITS_PER_CHARACTER = 10

# Timeout comparisons are a difference of two float millisecond values; absorb
# the representation error here instead of relaxing the engineering budget.
TIMEOUT_TOLERANCE_MS = 1e-9


def _require_real(value, label, positive=False, non_negative=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if positive and number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    if non_negative and number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def validate_profile(profile):
    """Return a normalised copy of a declared RMAP conformance profile."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping")
    role = profile.get("role")
    if role not in ROLES:
        raise ValueError("role must be one of %s, got %r" % (", ".join(ROLES), role))

    raw = profile.get("capabilities", [])
    if isinstance(raw, str) or not isinstance(raw, (list, tuple, set, frozenset)):
        raise ValueError("capabilities must be a sequence of capability tokens")
    capabilities = []
    for token in raw:
        if not isinstance(token, str) or not token.strip():
            raise ValueError("capability token must be a non-empty string, got %r" % (token,))
        name = token.strip()
        if name not in ALL_CAPABILITIES:
            raise ValueError("unknown capability token %r" % (name,))
        if name not in capabilities:
            capabilities.append(name)

    bits = profile.get("transaction_identifier_bits", 0)
    if not isinstance(bits, int) or isinstance(bits, bool):
        raise ValueError("transaction_identifier_bits must be an integer")
    if bits < 0:
        raise ValueError("transaction_identifier_bits must be non-negative, got %d" % bits)

    outstanding = profile.get("max_outstanding_transactions", 1)
    if not isinstance(outstanding, int) or isinstance(outstanding, bool):
        raise ValueError("max_outstanding_transactions must be an integer")
    if outstanding < 1:
        raise ValueError("max_outstanding_transactions must be at least 1, got %d" % outstanding)

    acknowledged = profile.get("issues_acknowledged_commands", True)
    if not isinstance(acknowledged, bool):
        raise ValueError("issues_acknowledged_commands must be a boolean")

    normalised = {
        "role": role,
        "capabilities": sorted(capabilities),
        "transaction_identifier_bits": bits,
        "max_outstanding_transactions": outstanding,
        "issues_acknowledged_commands": acknowledged,
    }
    for key in ("link_rate_mbit_s", "command_bytes", "reply_bytes",
                "target_turnaround_ms", "reply_timeout_ms"):
        if key in profile and profile[key] is not None:
            normalised[key] = profile[key]
    return normalised


def owed_capabilities(role):
    """Return the capability tokens the declared role has to deliver."""
    if role not in ROLES:
        raise ValueError("unknown role %r" % (role,))
    if role == ROLE_INITIATOR_ONLY:
        return tuple(sorted(INITIATOR_DUTIES))
    if role == ROLE_TARGET_ONLY:
        return tuple(sorted(TARGET_DUTIES))
    return ALL_CAPABILITIES


def out_of_scope_capabilities(role):
    """Return the capability tokens the declared role must not claim."""
    if role not in ROLES:
        raise ValueError("unknown role %r" % (role,))
    if role == ROLE_INITIATOR_ONLY:
        return tuple(sorted(set(TARGET_DUTIES) - set(INITIATOR_DUTIES)))
    if role == ROLE_TARGET_ONLY:
        return tuple(sorted(set(INITIATOR_DUTIES) - set(TARGET_DUTIES)))
    return ()


def identifier_space(bits):
    """Return how many transactions a identifier field of this width separates."""
    if not isinstance(bits, int) or isinstance(bits, bool):
        raise ValueError("bits must be an integer")
    if bits < 0:
        raise ValueError("bits must be non-negative, got %d" % bits)
    return 1 << bits


def missing_capabilities(profile):
    """Return the owed capability tokens the profile does not claim."""
    norm = validate_profile(profile)
    claimed = set(norm["capabilities"])
    return tuple(t for t in owed_capabilities(norm["role"]) if t not in claimed)


def surplus_capabilities(profile):
    """Return the claimed capability tokens that lie outside the declared role."""
    norm = validate_profile(profile)
    claimed = set(norm["capabilities"])
    return tuple(t for t in out_of_scope_capabilities(norm["role"]) if t in claimed)


def round_trip_estimate_ms(link_rate_mbit_s, command_bytes, reply_bytes,
                           target_turnaround_ms=0.0):
    """Return the estimated command-to-reply round trip in milliseconds."""
    rate = _require_real(link_rate_mbit_s, "link_rate_mbit_s", positive=True)
    out_bytes = _require_real(command_bytes, "command_bytes", positive=True)
    back_bytes = _require_real(reply_bytes, "reply_bytes", positive=True)
    turnaround = _require_real(target_turnaround_ms, "target_turnaround_ms", non_negative=True)
    characters = out_bytes + back_bytes
    # bit times / (Mbit/s) already lands in microseconds; divide by 1000 for ms.
    serial_ms = (characters * BITS_PER_CHARACTER) / rate / 1000.0
    return serial_ms + turnaround


def grade_identifier_budget(profile):
    """Return the identifier-width findings for a profile."""
    norm = validate_profile(profile)
    findings = []
    bits = norm["transaction_identifier_bits"]
    outstanding = norm["max_outstanding_transactions"]
    space = identifier_space(bits)
    if norm["issues_acknowledged_commands"]:
        if bits == 0:
            findings.append(
                "acknowledged commands are issued but the transaction identifier "
                "field has zero width, so replies cannot be matched to commands"
            )
        elif outstanding > space:
            findings.append(
                "up to %d transactions are allowed outstanding but a %d-bit "
                "identifier separates only %d of them" % (outstanding, bits, space)
            )
    elif outstanding > 1:
        findings.append(
            "no acknowledged commands are issued, so %d outstanding transactions "
            "cannot be tracked by reply" % outstanding
        )
    return {"identifier_space": space, "findings": findings}


def grade_reply_timeout(profile):
    """Return the reply-timeout finding for a profile, when timing is declared."""
    norm = validate_profile(profile)
    keys = ("link_rate_mbit_s", "command_bytes", "reply_bytes", "reply_timeout_ms")
    if not all(key in norm for key in keys):
        return {"evaluated": False, "findings": []}
    estimate = round_trip_estimate_ms(
        norm["link_rate_mbit_s"],
        norm["command_bytes"],
        norm["reply_bytes"],
        norm.get("target_turnaround_ms", 0.0),
    )
    timeout = _require_real(norm["reply_timeout_ms"], "reply_timeout_ms", positive=True)
    adequate = timeout > estimate or math.isclose(
        timeout, estimate, rel_tol=0.0, abs_tol=TIMEOUT_TOLERANCE_MS
    )
    findings = []
    if not adequate:
        findings.append(
            "reply timeout %.6f ms is shorter than the %.6f ms round-trip estimate"
            % (timeout, estimate)
        )
    return {
        "evaluated": True,
        "round_trip_estimate_ms": estimate,
        "reply_timeout_ms": timeout,
        "adequate": adequate,
        "findings": findings,
    }


def assess_initiator_only(profile):
    """Grade a declared profile against the initiator-only clause."""
    norm = validate_profile(profile)
    missing = missing_capabilities(norm)
    surplus = surplus_capabilities(norm)
    identifiers = grade_identifier_budget(norm)
    timeout = grade_reply_timeout(norm)

    findings = []
    if norm["role"] != ROLE_INITIATOR_ONLY:
        findings.append(
            "profile declares the %s role, so the initiator-only clause is not the "
            "governing one" % norm["role"]
        )
    for token in missing:
        findings.append("owed initiator duty not claimed: %s" % token)
    for token in surplus:
        findings.append("target-side duty claimed by an initiator-only device: %s" % token)
    findings.extend(identifiers["findings"])
    findings.extend(timeout["findings"])

    return {
        "role": norm["role"],
        "capabilities": norm["capabilities"],
        "missing_capabilities": list(missing),
        "surplus_capabilities": list(surplus),
        "identifier_space": identifiers["identifier_space"],
        "reply_timeout": timeout,
        "findings": findings,
        "conformant": not findings,
    }
