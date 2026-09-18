"""Command protection assessment for a spacecraft telecommand uplink.

Anchor: ECSS-E-ST-50C clause 5.4.6 (command encryption). Two normative items
are carried here, paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Sort every command in the uplink dictionary by its hazard category into the
   protection duty it owes: none, authentication alone, or authentication with
   encryption of the command content.
2. Reduce the declared cryptographic suite -- algorithm, key length, mode --
   to an effective strength in bits, because a nominal key length is not the
   strength a two-key or short-block construction actually delivers.
3. Hold that effective strength against the floor the highest protected hazard
   category sets, and refuse a suite that is merely present but under-strength.
4. Budget the key schedule over the mission: the number of commands a single
   key is allowed to protect against the number the mission will send between
   rotations, so an adequate algorithm with an exhausted key is still a
   finding.
5. Report the protection duty, the strength verdict and the key budget
   together, with an explicit finding list rather than a single boolean.
"""

import math

__all__ = [
    "USAGE_TOLERANCE",
    "PROTECTION_NONE",
    "PROTECTION_AUTHENTICATE",
    "PROTECTION_AUTHENTICATE_AND_ENCRYPT",
    "HAZARD_CATEGORIES",
    "SUITE_STRENGTH_FACTORS",
    "STRENGTH_FLOOR_BITS",
    "required_protection",
    "effective_key_bits",
    "strength_floor_bits",
    "commands_per_key_period",
    "key_usage_ratio",
    "categorize_commands",
    "assess_command_encryption",
]

# A usage ratio that lands exactly on 1.0 is a representation question, not an
# engineering one; absorb it here instead of relaxing the per-key limit.
USAGE_TOLERANCE = 1e-9

PROTECTION_NONE = "none"
PROTECTION_AUTHENTICATE = "authenticate"
PROTECTION_AUTHENTICATE_AND_ENCRYPT = "authenticate-and-encrypt"

# Hazard category -> (protection duty, strength floor in bits). A routine
# command carries no duty; a mission-critical command must be provably from
# the ground; a hazardous or a security-relevant command must additionally not
# be readable in transit, because its content is itself the intelligence.
HAZARD_CATEGORIES = {
    "routine": (PROTECTION_NONE, 0),
    "mission-critical": (PROTECTION_AUTHENTICATE, 112),
    "hazardous": (PROTECTION_AUTHENTICATE_AND_ENCRYPT, 128),
    "security-relevant": (PROTECTION_AUTHENTICATE_AND_ENCRYPT, 128),
}

# Declared key length is not delivered strength. A two-key triple construction
# loses more than half its nominal length to a meet-in-the-middle attack, and a
# counter mode over a short block is limited by the block, not by the key.
SUITE_STRENGTH_FACTORS = {
    "aes": 1.0,
    "triple-des-three-key": 0.4375,
    "triple-des-two-key": 0.5,
    "single-des": 1.0,
    "legacy-stream": 0.5,
}

STRENGTH_FLOOR_BITS = 112


def _require_number(value, label, positive=True, allow_zero=False):
    """Return value as a float after rejecting bools, non-numbers and non-finites."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive:
        if allow_zero:
            if number < 0.0:
                raise ValueError("%s must be non-negative, got %r" % (label, value))
        elif number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _require_int(value, label, minimum=1):
    """Return value as an int after rejecting bools and out-of-range values."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def required_protection(hazard_category):
    """Return the protection duty a hazard category places on a command."""
    if not isinstance(hazard_category, str):
        raise ValueError("hazard_category must be a string, got %r" % (hazard_category,))
    key = hazard_category.strip().lower()
    if key not in HAZARD_CATEGORIES:
        raise ValueError(
            "unknown hazard category %r; known: %s"
            % (hazard_category, ", ".join(sorted(HAZARD_CATEGORIES)))
        )
    return HAZARD_CATEGORIES[key][0]


def strength_floor_bits(hazard_category):
    """Return the effective-strength floor in bits for a hazard category."""
    if not isinstance(hazard_category, str):
        raise ValueError("hazard_category must be a string, got %r" % (hazard_category,))
    key = hazard_category.strip().lower()
    if key not in HAZARD_CATEGORIES:
        raise ValueError("unknown hazard category %r" % (hazard_category,))
    return HAZARD_CATEGORIES[key][1]


def effective_key_bits(algorithm, key_bits, block_bits=128):
    """Reduce a declared suite to the strength in bits it actually delivers.

    The key length is capped by the block size of the construction, because a
    cipher cannot deliver more distinguishing work than its block affords, and
    is then scaled by the known structural loss of the algorithm family.
    """
    if not isinstance(algorithm, str):
        raise ValueError("algorithm must be a string, got %r" % (algorithm,))
    name = algorithm.strip().lower()
    if name not in SUITE_STRENGTH_FACTORS:
        raise ValueError(
            "unknown algorithm %r; known: %s"
            % (algorithm, ", ".join(sorted(SUITE_STRENGTH_FACTORS)))
        )
    bits = _require_int(key_bits, "key_bits", minimum=1)
    block = _require_int(block_bits, "block_bits", minimum=8)
    scaled = bits * SUITE_STRENGTH_FACTORS[name]
    capped = min(scaled, float(2 * block))
    return math.floor(capped + USAGE_TOLERANCE)


def commands_per_key_period(command_rate_per_day, rotation_interval_days):
    """Return how many commands a single key is asked to protect between rotations."""
    rate = _require_number(command_rate_per_day, "command_rate_per_day", allow_zero=True)
    interval = _require_number(rotation_interval_days, "rotation_interval_days")
    return rate * interval


def key_usage_ratio(command_rate_per_day, rotation_interval_days, commands_per_key_limit):
    """Return the fraction of a key's allowed usage the rotation interval consumes."""
    used = commands_per_key_period(command_rate_per_day, rotation_interval_days)
    limit = _require_number(commands_per_key_limit, "commands_per_key_limit")
    return used / limit


def categorize_commands(commands):
    """Group an uplink dictionary by the protection duty each command owes.

    Returns a mapping duty -> list of command names, plus the strictest
    strength floor any command in the dictionary demands.
    """
    if not isinstance(commands, (list, tuple)) or not commands:
        raise ValueError("commands must be a non-empty sequence of command records")
    grouped = {
        PROTECTION_NONE: [],
        PROTECTION_AUTHENTICATE: [],
        PROTECTION_AUTHENTICATE_AND_ENCRYPT: [],
    }
    floor = 0
    seen = set()
    for index, record in enumerate(commands):
        if not isinstance(record, dict):
            raise ValueError("commands[%d] must be a mapping" % index)
        for key in ("name", "hazard_category"):
            if key not in record:
                raise ValueError("commands[%d] missing '%s'" % (index, key))
        name = record["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("commands[%d] name must be a non-empty string" % index)
        if name in seen:
            raise ValueError("duplicate command name %r in the uplink dictionary" % name)
        seen.add(name)
        duty = required_protection(record["hazard_category"])
        grouped[duty].append(name)
        floor = max(floor, strength_floor_bits(record["hazard_category"]))
    return {"grouped": grouped, "strength_floor_bits": floor}


def assess_command_encryption(spec):
    """Run the full clause 5.4.6 command-protection assessment.

    spec keys: commands (sequence of {name, hazard_category}), algorithm,
    key_bits, optional block_bits, protection_provided (one of the protection
    constants), command_rate_per_day, rotation_interval_days,
    commands_per_key_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "commands",
        "algorithm",
        "key_bits",
        "protection_provided",
        "command_rate_per_day",
        "rotation_interval_days",
        "commands_per_key_limit",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    provided = spec["protection_provided"]
    if provided not in (
        PROTECTION_NONE,
        PROTECTION_AUTHENTICATE,
        PROTECTION_AUTHENTICATE_AND_ENCRYPT,
    ):
        raise ValueError("protection_provided %r is not a known protection duty" % (provided,))

    grouping = categorize_commands(spec["commands"])
    grouped = grouping["grouped"]
    floor = grouping["strength_floor_bits"]

    ladder = {
        PROTECTION_NONE: 0,
        PROTECTION_AUTHENTICATE: 1,
        PROTECTION_AUTHENTICATE_AND_ENCRYPT: 2,
    }
    demanded = PROTECTION_NONE
    for duty in (PROTECTION_AUTHENTICATE_AND_ENCRYPT, PROTECTION_AUTHENTICATE):
        if grouped[duty]:
            demanded = duty
            break

    strength = effective_key_bits(
        spec["algorithm"], spec["key_bits"], spec.get("block_bits", 128)
    )
    usage = key_usage_ratio(
        spec["command_rate_per_day"],
        spec["rotation_interval_days"],
        spec["commands_per_key_limit"],
    )

    findings = []
    duty_met = ladder[provided] >= ladder[demanded]
    if not duty_met:
        findings.append(
            "uplink provides %s but %d command(s) demand %s"
            % (provided, len(grouped[demanded]), demanded)
        )
    strength_met = strength >= floor
    if not strength_met:
        findings.append(
            "effective strength %d bit is below the %d bit floor the protected commands set"
            % (strength, floor)
        )
    key_budget_met = usage < 1.0 or math.isclose(
        usage, 1.0, rel_tol=0.0, abs_tol=USAGE_TOLERANCE
    )
    if not key_budget_met:
        findings.append(
            "rotation interval consumes %.3f of the per-key command limit" % usage
        )
    if demanded == PROTECTION_NONE and provided != PROTECTION_NONE:
        findings.append(
            "protection is applied but no command in the dictionary demands it; "
            "confirm the hazard categorization is complete"
        )

    return {
        "grouped": grouped,
        "demanded_protection": demanded,
        "provided_protection": provided,
        "effective_key_bits": strength,
        "strength_floor_bits": floor,
        "key_usage_ratio": usage,
        "duty_met": duty_met,
        "strength_met": strength_met,
        "key_budget_met": key_budget_met,
        "compliant": duty_met and strength_met and key_budget_met,
        "findings": findings,
    }
