"""Absolute-time parameter definition, encoding and decoding.

Anchor: ECSS-E-ST-70-41C clause 7.3.10 (absolute time data type, four
normative items). Paraphrased into an implementable procedure; no
standard text is reproduced.

What the clause is for. An absolute-time parameter names a moment: the
generation time in a data field header, the release time of a time-
tagged command, the start of a housekeeping collection interval. Unlike
an engineering value it is not a number with a unit -- it is a count in
a time code, and the code has to be agreed before either end can read
it.

Three things the definition fixes and the packet does not carry:

* the code -- an unsegmented counter of seconds and fractions (CUC), or
  a day-segmented counter of days and milliseconds within the day (CDS);
* the field widths -- how many octets of coarse count and how many of
  fine count, which together fix both the resolution and the span;
* the epoch -- the moment the count is measured from, either the agency
  epoch or a mission epoch declared once for the whole system.

Because none of the three travels with the value, a ground system that
assumes any of them reads a plausible wrong time rather than failing.
A one-octet difference in the fine field is a factor of 256 in
resolution; a different epoch is an offset of years.

Two consequences this module enforces. The value is truncated down to
the resolution the fine field gives, never rounded, so an encoded time
never names a moment later than the one it came from. And a time
outside the span the coarse field covers is refused rather than
wrapped: a wrapped count is a valid-looking time in the wrong century.

Stdlib only, offline, deterministic.
"""

import math

__all__ = [
    "CUC_MIN_COARSE_OCTETS",
    "CUC_MAX_COARSE_OCTETS",
    "CUC_MIN_FINE_OCTETS",
    "CUC_MAX_FINE_OCTETS",
    "SECONDS_PER_DAY",
    "EPOCH_OFFSETS_S",
    "epoch_offset_s",
    "validate_cuc_spec",
    "cuc_resolution_s",
    "cuc_span_s",
    "encode_cuc",
    "decode_cuc",
    "validate_cds_spec",
    "cds_resolution_s",
    "cds_span_s",
    "encode_cds",
    "decode_cds",
    "rebase_epoch",
    "assess_absolute_time_definition",
]

CUC_MIN_COARSE_OCTETS = 1
CUC_MAX_COARSE_OCTETS = 7
CUC_MIN_FINE_OCTETS = 0
CUC_MAX_FINE_OCTETS = 6

SECONDS_PER_DAY = 86400
_MS_PER_DAY = SECONDS_PER_DAY * 1000

# Offsets, in seconds, of a named epoch after the agency epoch. A mission
# epoch is declared once for the whole system; it is never inferred from a
# value that happens to look recent.
EPOCH_OFFSETS_S = {
    "agency": 0,
    "mission-2000": 1325376000,
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(label, value):
    if not _is_real(value):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite" % label)
    return out


def epoch_offset_s(name):
    """Return the offset in seconds of a named epoch after the agency epoch."""
    if not isinstance(name, str):
        raise ValueError("epoch name must be a string, got %r" % (name,))
    if name not in EPOCH_OFFSETS_S:
        raise ValueError(
            "unknown epoch %r; the mission definition must name one of %s"
            % (name, ", ".join(sorted(EPOCH_OFFSETS_S)))
        )
    return EPOCH_OFFSETS_S[name]


def validate_cuc_spec(coarse_octets, fine_octets, epoch="agency"):
    """Return a normalised unsegmented (CUC) absolute-time definition."""
    if not _is_int(coarse_octets):
        raise ValueError("coarse_octets must be an integer, got %r" % (coarse_octets,))
    if not _is_int(fine_octets):
        raise ValueError("fine_octets must be an integer, got %r" % (fine_octets,))
    if not CUC_MIN_COARSE_OCTETS <= coarse_octets <= CUC_MAX_COARSE_OCTETS:
        raise ValueError(
            "coarse_octets must be %d..%d, got %d"
            % (CUC_MIN_COARSE_OCTETS, CUC_MAX_COARSE_OCTETS, coarse_octets)
        )
    if not CUC_MIN_FINE_OCTETS <= fine_octets <= CUC_MAX_FINE_OCTETS:
        raise ValueError(
            "fine_octets must be %d..%d, got %d"
            % (CUC_MIN_FINE_OCTETS, CUC_MAX_FINE_OCTETS, fine_octets)
        )
    return {
        "code": "cuc",
        "coarse_octets": coarse_octets,
        "fine_octets": fine_octets,
        "epoch": epoch,
        "epoch_offset_s": epoch_offset_s(epoch),
        "field_octets": coarse_octets + fine_octets,
    }


def cuc_resolution_s(spec):
    """Return the resolution in seconds a CUC definition gives."""
    return 1.0 / float(1 << (8 * spec["fine_octets"]))


def cuc_span_s(spec):
    """Return the exclusive upper bound in seconds the coarse field covers."""
    return 1 << (8 * spec["coarse_octets"])


def encode_cuc(seconds_since_epoch, spec):
    """Encode a time into its coarse and fine counts, truncated downwards."""
    value = _finite("seconds_since_epoch", seconds_since_epoch)
    if value < 0.0:
        raise ValueError(
            "an absolute time is a count forward from the epoch; %g is before it" % value
        )
    units = 1 << (8 * spec["fine_octets"])
    ticks = int(math.floor(value * units))
    coarse, fine = divmod(ticks, units)
    if coarse >= cuc_span_s(spec):
        raise ValueError(
            "time %g s is outside the %d s span of a %d-octet coarse field; a wrapped count "
            "is a valid-looking time in the wrong era"
            % (value, cuc_span_s(spec), spec["coarse_octets"])
        )
    return {"coarse": coarse, "fine": fine, "ticks": ticks}


def decode_cuc(coarse, fine, spec):
    """Recover the seconds since the epoch from a coarse and fine count."""
    if not _is_int(coarse) or not _is_int(fine):
        raise ValueError("coarse and fine counts must be integers")
    if coarse < 0 or fine < 0:
        raise ValueError("coarse and fine counts are unsigned")
    units = 1 << (8 * spec["fine_octets"])
    if fine >= units:
        raise ValueError(
            "fine count %d does not fit a %d-octet fine field" % (fine, spec["fine_octets"])
        )
    if coarse >= cuc_span_s(spec):
        raise ValueError(
            "coarse count %d does not fit a %d-octet coarse field"
            % (coarse, spec["coarse_octets"])
        )
    return coarse + float(fine) / float(units)


def validate_cds_spec(day_octets, submillisecond_units=0, epoch="agency"):
    """Return a normalised day-segmented (CDS) absolute-time definition."""
    if not _is_int(day_octets):
        raise ValueError("day_octets must be an integer, got %r" % (day_octets,))
    if day_octets not in (2, 3):
        raise ValueError("day_octets must be 2 or 3, got %d" % day_octets)
    if submillisecond_units not in (0, 1, 2):
        raise ValueError(
            "submillisecond_units must be 0 (none), 1 (microsecond) or 2 (picosecond), got %r"
            % (submillisecond_units,)
        )
    return {
        "code": "cds",
        "day_octets": day_octets,
        "submillisecond_units": submillisecond_units,
        "epoch": epoch,
        "epoch_offset_s": epoch_offset_s(epoch),
        "field_octets": day_octets + 4 + 2 * submillisecond_units,
    }


def cds_resolution_s(spec):
    """Return the resolution in seconds a CDS definition gives."""
    if spec["submillisecond_units"] == 0:
        return 1e-3
    if spec["submillisecond_units"] == 1:
        return 1e-6
    return 1e-12


def cds_span_s(spec):
    """Return the exclusive upper bound in seconds the day field covers."""
    return (1 << (8 * spec["day_octets"])) * SECONDS_PER_DAY


def encode_cds(seconds_since_epoch, spec):
    """Encode a time into day and millisecond-of-day counts, truncated down."""
    value = _finite("seconds_since_epoch", seconds_since_epoch)
    if value < 0.0:
        raise ValueError(
            "an absolute time is a count forward from the epoch; %g is before it" % value
        )
    total_ms = int(math.floor(value * 1000.0))
    day, ms_of_day = divmod(total_ms, _MS_PER_DAY)
    if day >= (1 << (8 * spec["day_octets"])):
        raise ValueError(
            "time %g s needs day %d, outside the %d-octet day field"
            % (value, day, spec["day_octets"])
        )
    return {"day": day, "ms_of_day": ms_of_day}


def decode_cds(day, ms_of_day, spec):
    """Recover the seconds since the epoch from a day and millisecond count."""
    if not _is_int(day) or not _is_int(ms_of_day):
        raise ValueError("day and ms_of_day must be integers")
    if day < 0 or ms_of_day < 0:
        raise ValueError("day and ms_of_day are unsigned")
    if ms_of_day >= _MS_PER_DAY:
        raise ValueError("ms_of_day %d is not inside a day" % ms_of_day)
    if day >= (1 << (8 * spec["day_octets"])):
        raise ValueError("day %d does not fit a %d-octet day field" % (day, spec["day_octets"]))
    return day * float(SECONDS_PER_DAY) + ms_of_day / 1000.0


def rebase_epoch(seconds, from_epoch, to_epoch):
    """Restate a time measured from one named epoch against another."""
    value = _finite("seconds", seconds)
    shifted = value + epoch_offset_s(from_epoch) - epoch_offset_s(to_epoch)
    if shifted < 0.0:
        raise ValueError(
            "the time falls before the %r epoch; restating it there would need a negative "
            "absolute count" % (to_epoch,)
        )
    return shifted


def assess_absolute_time_definition(spec, samples=None, required_resolution_s=None,
                                    mission_end_s=None):
    """Assess a definition against its samples, resolution need and mission span."""
    if not isinstance(spec, dict) or spec.get("code") not in ("cuc", "cds"):
        raise ValueError("spec must be a validated CUC or CDS definition")
    if spec["code"] == "cuc":
        resolution = cuc_resolution_s(spec)
        span = float(cuc_span_s(spec))
        encode = lambda value: encode_cuc(value, spec)
        decode = lambda enc: decode_cuc(enc["coarse"], enc["fine"], spec)
    else:
        resolution = cds_resolution_s(spec)
        span = float(cds_span_s(spec))
        encode = lambda value: encode_cds(value, spec)
        decode = lambda enc: decode_cds(enc["day"], enc["ms_of_day"], spec)
    findings = []
    if required_resolution_s is not None:
        needed = _finite("required_resolution_s", required_resolution_s)
        if needed <= 0.0:
            raise ValueError("required_resolution_s must be positive")
        if resolution > needed * (1.0 + 1e-12):
            findings.append(
                "the definition resolves to %.12g s, coarser than the %.12g s required"
                % (resolution, needed)
            )
    if mission_end_s is not None:
        end = _finite("mission_end_s", mission_end_s)
        if end < 0.0:
            raise ValueError("mission_end_s must be non-negative")
        if end >= span:
            findings.append(
                "the coarse field spans %.12g s, short of the mission end at %.12g s"
                % (span, end)
            )
    encoded = []
    refused = []
    worst_error = 0.0
    for sample in samples or []:
        try:
            enc = encode(sample)
        except ValueError as exc:
            refused.append({"value": sample, "reason": str(exc)})
            continue
        back = decode(enc)
        error = float(sample) - back
        # A millisecond scaling is not exact in binary, so an encode that
        # landed on the boundary can read a few ULPs the wrong way. Only a
        # genuine step backwards is a finding.
        if error < -resolution * 1e-6:
            findings.append(
                "encoding %.12g s produced %.12g s, later than the moment it came from"
                % (sample, back)
            )
        worst_error = max(worst_error, abs(error))
        encoded.append({"value": float(sample), "encoded": enc, "decoded": back,
                        "truncation_s": error})
    if refused:
        findings.append("%d of %d sample times fall outside the definition"
                        % (len(refused), len(samples or [])))
    if worst_error > resolution * (1.0 + 1e-9):
        findings.append(
            "worst truncation %.12g s exceeds the %.12g s resolution" % (worst_error, resolution)
        )
    return {
        "resolution_s": resolution,
        "span_s": span,
        "field_octets": spec["field_octets"],
        "epoch": spec["epoch"],
        "encoded": encoded,
        "refused": refused,
        "worst_truncation_s": worst_error,
        "findings": findings,
        "adequate": not findings,
    }
