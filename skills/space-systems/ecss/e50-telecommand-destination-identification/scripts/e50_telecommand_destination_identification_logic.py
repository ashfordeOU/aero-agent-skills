"""Destination identification for telecommands on a shared uplink.

Anchor: ECSS-E-ST-50C clause 5.4.10 (telecommand destination identification).
One normative item, paraphrased into an implementable procedure; no standard
text is reproduced.

Every telecommand has to say unambiguously which spacecraft, and which
on-board application inside it, is meant to act on it. The failure guarded
against is a command accepted by the wrong recipient -- a co-located
constellation member, a rideshare companion, a formation partner within the
same antenna beam.

Procedure implemented here
--------------------------
1. Validate the spacecraft-identifier field: width in bits, identifiers inside
   the address space that width provides, and no identifier used twice in the
   co-visible set.
2. Measure the separation of the assigned identifier set as the minimum
   pairwise Hamming distance, computed on exact integers, and derive from it
   how many bit errors the field can detect and how many it can correct.
3. Validate the application identifier of each command against the applications
   the destination spacecraft declares.
4. Reject an unset or broadcast destination on any command that is not
   explicitly declared broadcast-safe.
5. Report the address-space use, the separation, the per-command verdicts and a
   finding list.
"""

__all__ = [
    "BROADCAST_ID",
    "address_space_size",
    "hamming_distance",
    "minimum_separation",
    "detectable_bit_errors",
    "correctable_bit_errors",
    "validate_identifier_set",
    "evaluate_command_destination",
    "assess_destination_identification",
]

# The reserved all-ones pattern every receiver in the beam accepts.
BROADCAST_ID = "broadcast"


def _require_field_width(value, label):
    """Return an identifier field width in bits."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least one bit, got %d" % (label, value))
    if value > 64:
        raise ValueError("%s of %d bits is outside any realistic frame field" % (label, value))
    return value


def _require_identifier(value, label, field_bits):
    """Return a non-negative identifier that fits the field."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    if value >= address_space_size(field_bits):
        raise ValueError(
            "%s %d does not fit a %d bit field" % (label, value, field_bits)
        )
    return value


def address_space_size(field_bits):
    """Return how many distinct identifiers a field of this width carries."""
    bits = _require_field_width(field_bits, "field_bits")
    return 1 << bits


def hamming_distance(first, second):
    """Return the number of bit positions in which two identifiers differ."""
    for label, value in (("first", first), ("second", second)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
        if value < 0:
            raise ValueError("%s must be non-negative, got %d" % (label, value))
    return bin(first ^ second).count("1")


def minimum_separation(identifiers):
    """Return the smallest Hamming distance between any two assigned identifiers."""
    if not isinstance(identifiers, (list, tuple)):
        raise ValueError("identifiers must be a sequence")
    if len(identifiers) < 2:
        raise ValueError("separation needs at least two assigned identifiers")
    smallest = None
    for i in range(len(identifiers)):
        for j in range(i + 1, len(identifiers)):
            distance = hamming_distance(identifiers[i], identifiers[j])
            if distance == 0:
                raise ValueError(
                    "identifier %d is assigned twice; the set is not unique" % identifiers[i]
                )
            if smallest is None or distance < smallest:
                smallest = distance
    return smallest


def detectable_bit_errors(separation):
    """Return how many bit errors a set with this separation always detects."""
    if not isinstance(separation, int) or isinstance(separation, bool):
        raise ValueError("separation must be an integer, got %r" % (separation,))
    if separation < 1:
        raise ValueError("separation must be at least one, got %d" % separation)
    return separation - 1


def correctable_bit_errors(separation):
    """Return how many bit errors a set with this separation always corrects."""
    return (detectable_bit_errors(separation)) // 2


def validate_identifier_set(field_bits, identifiers):
    """Validate the co-visible spacecraft identifier assignment."""
    bits = _require_field_width(field_bits, "field_bits")
    if not isinstance(identifiers, (list, tuple)) or not identifiers:
        raise ValueError("identifiers must be a non-empty sequence")
    checked = [
        _require_identifier(value, "identifiers[%d]" % index, bits)
        for index, value in enumerate(identifiers)
    ]
    capacity = address_space_size(bits)
    separation = minimum_separation(checked) if len(checked) > 1 else bits
    return {
        "field_bits": bits,
        "identifiers": checked,
        "capacity": capacity,
        "assigned": len(checked),
        "occupancy": len(checked) / capacity,
        "separation": separation,
        "detectable_bit_errors": detectable_bit_errors(separation),
        "correctable_bit_errors": correctable_bit_errors(separation),
    }


def evaluate_command_destination(command, assignment, applications):
    """Return the destination verdict for one telecommand."""
    if not isinstance(command, dict):
        raise ValueError("command must be a mapping")
    for key in ("name", "spacecraft_id", "application_id"):
        if key not in command:
            raise ValueError("command missing '%s'" % key)
    name = command["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("command name must be a non-empty string")
    broadcast_safe = command.get("broadcast_safe", False)
    if not isinstance(broadcast_safe, bool):
        raise ValueError("command %r 'broadcast_safe' must be a bool" % name)

    problems = []
    spacecraft_id = command["spacecraft_id"]
    if spacecraft_id is None:
        problems.append("destination spacecraft is unset")
    elif spacecraft_id == BROADCAST_ID:
        if not broadcast_safe:
            problems.append("addressed to every receiver in the beam without being broadcast-safe")
    else:
        _require_identifier(spacecraft_id, "spacecraft_id", assignment["field_bits"])
        if spacecraft_id not in assignment["identifiers"]:
            problems.append("spacecraft identifier %d is not in the assigned set" % spacecraft_id)

    application_id = command["application_id"]
    if application_id is None:
        problems.append("destination application is unset")
    elif not isinstance(application_id, int) or isinstance(application_id, bool):
        raise ValueError("command %r application_id must be an integer or None" % name)
    elif application_id not in applications:
        problems.append("application identifier %d is not declared on board" % application_id)

    return {
        "name": name,
        "spacecraft_id": spacecraft_id,
        "application_id": application_id,
        "unambiguous": not problems,
        "problems": problems,
    }


def assess_destination_identification(spec):
    """Run the full clause 5.4.10 destination-identification assessment.

    spec keys: field_bits, assigned_ids, applications (sequence of application
    identifiers declared on board), commands (sequence of {name, spacecraft_id,
    application_id, optional broadcast_safe}), optional required_separation.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("field_bits", "assigned_ids", "applications", "commands"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    assignment = validate_identifier_set(spec["field_bits"], spec["assigned_ids"])
    applications = spec["applications"]
    if not isinstance(applications, (list, tuple)) or not applications:
        raise ValueError("applications must be a non-empty sequence")
    for index, value in enumerate(applications):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("applications[%d] must be a non-negative integer" % index)
    if len(set(applications)) != len(applications):
        raise ValueError("an application identifier is declared twice")
    commands = spec["commands"]
    if not isinstance(commands, (list, tuple)) or not commands:
        raise ValueError("commands must be a non-empty sequence")
    required_separation = spec.get("required_separation", 1)
    if not isinstance(required_separation, int) or isinstance(required_separation, bool):
        raise ValueError("required_separation must be an integer")
    if required_separation < 1:
        raise ValueError("required_separation must be at least one")

    records = []
    seen = set()
    for command in commands:
        record = evaluate_command_destination(command, assignment, set(applications))
        if record["name"] in seen:
            raise ValueError("duplicate command name %r" % record["name"])
        seen.add(record["name"])
        records.append(record)

    findings = []
    separation_met = assignment["separation"] >= required_separation
    if not separation_met:
        findings.append(
            "assigned identifiers are separated by %d bit(s); %d required"
            % (assignment["separation"], required_separation)
        )
    for record in records:
        for problem in record["problems"]:
            findings.append("command %s: %s" % (record["name"], problem))

    return {
        "assignment": assignment,
        "records": records,
        "separation_met": separation_met,
        "ambiguous_commands": [r["name"] for r in records if not r["unambiguous"]],
        "compliant": separation_met and all(r["unambiguous"] for r in records),
        "findings": findings,
    }
