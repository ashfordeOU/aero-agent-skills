"""Telemetry source-identification assessment.

Anchor: ECSS-E-ST-50C clause 5.5.3 (each telemetry data unit carries an
unambiguous identification of the source that produced it). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each declared telemetry stream: spacecraft identifier, on-board
   source (application process) identifier, optional virtual channel.
2. Form the (spacecraft, source) identifier tuple and group by it; a group
   with more than one stream is an ambiguity the receiver cannot resolve.
3. Size the identifier fields two ways -- the width needed to enumerate the
   distinct sources, and the width needed to carry the largest value issued
   -- and take the larger as the requirement.
4. Compare the requirement with the declared header field widths and report
   every identifier value that overflows its field.
5. Screen the retirement history: an identifier re-issued before the ground
   ambiguity window has elapsed denotes two different sources at once.
"""

import math

__all__ = [
    "WINDOW_TOLERANCE_S",
    "validate_stream",
    "validate_stream_set",
    "identifier_tuple",
    "duplicate_tuples",
    "enumeration_bits",
    "value_bits",
    "required_field_bits",
    "field_overflows",
    "ambiguity_window_s",
    "premature_reuses",
    "assess_source_identification",
]

# The reuse comparison is an elapsed time against a summed window: an exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of shortening the declared window.
WINDOW_TOLERANCE_S = 1e-9


def _require_text(value, label):
    """Return a non-empty stripped string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _require_identifier(value, label):
    """Return a non-negative integer identifier or raise."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _require_non_negative(value, label):
    """Return a non-negative finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def validate_stream(stream):
    """Return a normalised telemetry stream record."""
    if not isinstance(stream, dict):
        raise ValueError("stream must be a mapping, got %r" % (stream,))
    for key in ("name", "spacecraft_id", "source_id"):
        if key not in stream:
            raise ValueError("stream missing required key '%s'" % key)
    channel = stream.get("virtual_channel")
    if channel is not None:
        channel = _require_identifier(channel, "virtual_channel")
    return {
        "name": _require_text(stream["name"], "name"),
        "spacecraft_id": _require_identifier(stream["spacecraft_id"], "spacecraft_id"),
        "source_id": _require_identifier(stream["source_id"], "source_id"),
        "virtual_channel": channel,
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


def identifier_tuple(stream):
    """Return the (spacecraft_id, source_id) identification tuple of a stream."""
    record = validate_stream(stream)
    return (record["spacecraft_id"], record["source_id"])


def duplicate_tuples(streams):
    """Return {tuple: sorted stream names} for every tuple claimed twice."""
    records = validate_stream_set(streams)
    groups = {}
    for record in records:
        key = (record["spacecraft_id"], record["source_id"])
        groups.setdefault(key, []).append(record["name"])
    return dict(
        (key, sorted(names)) for key, names in groups.items() if len(names) > 1
    )


def enumeration_bits(count):
    """Return the minimum field width needed to enumerate `count` distinct values."""
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count <= 0:
        raise ValueError("count must be positive, got %d" % count)
    if count == 1:
        return 1
    return (count - 1).bit_length()


def value_bits(value):
    """Return the minimum field width needed to carry an identifier value."""
    identifier = _require_identifier(value, "identifier value")
    if identifier == 0:
        return 1
    return identifier.bit_length()


def required_field_bits(values):
    """Return the field width required by a set of issued identifier values."""
    if isinstance(values, dict) or not isinstance(values, (list, tuple, set, frozenset)):
        raise ValueError("values must be a sequence of identifier values")
    issued = [_require_identifier(v, "identifier value") for v in values]
    if not issued:
        raise ValueError("values must contain at least one identifier")
    distinct = sorted(set(issued))
    return max(enumeration_bits(len(distinct)), value_bits(max(distinct)))


def field_overflows(streams, spacecraft_id_bits, source_id_bits):
    """Return the findings for identifier values that do not fit their fields."""
    records = validate_stream_set(streams)
    for label, width in (
        ("spacecraft_id_bits", spacecraft_id_bits),
        ("source_id_bits", source_id_bits),
    ):
        if not isinstance(width, int) or isinstance(width, bool):
            raise ValueError("%s must be an integer, got %r" % (label, width))
        if width <= 0:
            raise ValueError("%s must be positive, got %d" % (label, width))
    findings = []
    for record in records:
        if value_bits(record["spacecraft_id"]) > spacecraft_id_bits:
            findings.append(
                "stream '%s' spacecraft identifier %d needs %d bits but the field "
                "carries %d" % (
                    record["name"], record["spacecraft_id"],
                    value_bits(record["spacecraft_id"]), spacecraft_id_bits,
                )
            )
        if value_bits(record["source_id"]) > source_id_bits:
            findings.append(
                "stream '%s' source identifier %d needs %d bits but the field "
                "carries %d" % (
                    record["name"], record["source_id"],
                    value_bits(record["source_id"]), source_id_bits,
                )
            )
    return findings


def ambiguity_window_s(storage_retention_s, playback_delay_s, archive_ingest_s=0.0):
    """Return the ground ambiguity window an identifier must stay retired for."""
    retention = _require_non_negative(storage_retention_s, "storage_retention_s")
    playback = _require_non_negative(playback_delay_s, "playback_delay_s")
    ingest = _require_non_negative(archive_ingest_s, "archive_ingest_s")
    return retention + playback + ingest


def premature_reuses(reuse_records, window_s):
    """Return the findings for identifiers re-issued inside the ambiguity window."""
    if isinstance(reuse_records, dict) or not isinstance(reuse_records, (list, tuple)):
        raise ValueError("reuse_records must be a sequence of reuse mappings")
    window = _require_non_negative(window_s, "window_s")
    findings = []
    for entry in reuse_records:
        if not isinstance(entry, dict):
            raise ValueError("reuse record must be a mapping, got %r" % (entry,))
        for key in ("source_id", "elapsed_since_retirement_s"):
            if key not in entry:
                raise ValueError("reuse record missing required key '%s'" % key)
        identifier = _require_identifier(entry["source_id"], "source_id")
        elapsed = _require_non_negative(
            entry["elapsed_since_retirement_s"], "elapsed_since_retirement_s"
        )
        if math.isclose(elapsed, window, rel_tol=0.0, abs_tol=WINDOW_TOLERANCE_S):
            continue
        if elapsed < window:
            findings.append(
                "source identifier %d was re-issued %.6g s after retirement, inside "
                "the %.6g s ground ambiguity window" % (identifier, elapsed, window)
            )
    return findings


def assess_source_identification(spec):
    """Run the full clause 5.5.3 source-identification assessment.

    spec keys: streams, spacecraft_id_bits, source_id_bits, optional
    storage_retention_s, playback_delay_s, archive_ingest_s, reuses and
    channel_used_as_identifier.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("streams", "spacecraft_id_bits", "source_id_bits"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    records = validate_stream_set(spec["streams"])
    duplicates = duplicate_tuples(records)
    overflow = field_overflows(records, spec["spacecraft_id_bits"], spec["source_id_bits"])
    window = ambiguity_window_s(
        spec.get("storage_retention_s", 0.0),
        spec.get("playback_delay_s", 0.0),
        spec.get("archive_ingest_s", 0.0),
    )
    reuse_findings = premature_reuses(spec.get("reuses", []), window)

    channel_as_identifier = spec.get("channel_used_as_identifier", False)
    if not isinstance(channel_as_identifier, bool):
        raise ValueError("channel_used_as_identifier must be a boolean")

    findings = []
    for key in sorted(duplicates):
        findings.append(
            "spacecraft %d source %d is claimed by more than one stream: %s"
            % (key[0], key[1], ", ".join(duplicates[key]))
        )
    findings.extend(overflow)
    findings.extend(reuse_findings)
    if channel_as_identifier:
        findings.append(
            "the virtual channel is being read as the source identification; it is a "
            "transport route and changes with the downlink plan"
        )

    return {
        "tuples": dict(
            (r["name"], (r["spacecraft_id"], r["source_id"])) for r in records
        ),
        "duplicate_tuples": duplicates,
        "required_spacecraft_id_bits": required_field_bits(
            [r["spacecraft_id"] for r in records]
        ),
        "required_source_id_bits": required_field_bits(
            [r["source_id"] for r in records]
        ),
        "ambiguity_window_s": window,
        "compliant": not findings,
        "findings": findings,
    }
