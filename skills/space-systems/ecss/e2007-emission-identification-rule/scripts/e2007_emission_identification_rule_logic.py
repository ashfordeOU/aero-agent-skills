#!/usr/bin/env python3
"""Emission identification rule logic (ECSS-E-ST-20-07C, 5.2.9.2).

Offline, deterministic, standard-library only. The clause makes one
demand: every emission found during a survey is measured with the
bandwidth its frequency range prescribes, whatever character the signal
is judged to have. The module therefore:

* normalizes the character an emission was recorded under, without ever
  letting that character change a bandwidth or a verdict,
* decides whether the bandwidth a receiver was set to is the prescribed
  one, and quantifies the level error a substitution would carry,
* refuses an emission left out of the record on character grounds,
* grades every emission against its limit whether or not it was
  reported, and names the ones that have to be reported,
* groups the survey by character and detects a bandwidth that tracks
  the character instead of the range,
* accepts or refuses the survey as a whole.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "RECOGNIZED_CHARACTERS",
    "normalize_character",
    "is_prescribed_bandwidth",
    "bandwidth_level_error_db",
    "exceeds_limit",
    "evaluate_emission",
    "character_neutrality_audit",
    "reportable_emissions",
    "assess_emission_survey",
]

# Absorbs binary-representation error when a ratio or a logarithm lands a
# few units in the last place away from an exactly-met value. It never
# widens a limit.
REL_TOL = 1e-9

# Characters a survey may record against an emission. The list exists so
# that a record can be validated, not so that the character can be acted
# on: every one of these is measured the same way.
RECOGNIZED_CHARACTERS = (
    "narrowband",
    "broadband",
    "impulsive",
    "continuous",
    "undetermined",
)

_EMISSION_KEYS = (
    "id",
    "frequency_hz",
    "character",
    "prescribed_bandwidth_hz",
    "applied_bandwidth_hz",
    "level_dbuv",
    "limit_dbuv",
    "reported",
    "omitted_reason",
)

_REQUIRED_KEYS = (
    "id",
    "frequency_hz",
    "character",
    "prescribed_bandwidth_hz",
    "applied_bandwidth_hz",
    "level_dbuv",
)


def _finding(code, subject, detail):
    """Build one survey finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _same(left, right):
    """Equality that absorbs binary-representation error."""
    return left == right or math.isclose(left, right, rel_tol=REL_TOL, abs_tol=0.0)


def normalize_character(character):
    """Reduce a recorded signal character to its canonical spelling."""
    if not isinstance(character, str):
        raise ValueError(
            "character must be a string, got %s" % type(character).__name__
        )
    text = character.strip().lower().replace("_", "-").replace(" ", "-")
    if not text:
        raise ValueError("character must not be blank")
    if text in ("broad-band", "broadband"):
        text = "broadband"
    elif text in ("narrow-band", "narrowband"):
        text = "narrowband"
    elif text in ("unknown", "undetermined", "not-determined"):
        text = "undetermined"
    if text not in RECOGNIZED_CHARACTERS:
        raise ValueError(
            "character %r is not one of %s" % (character, ", ".join(RECOGNIZED_CHARACTERS))
        )
    return text


def is_prescribed_bandwidth(applied_bandwidth_hz, prescribed_bandwidth_hz):
    """True when the receiver was set to the bandwidth the range fixes."""
    applied = _as_positive_float(applied_bandwidth_hz, "applied_bandwidth_hz")
    prescribed = _as_positive_float(
        prescribed_bandwidth_hz, "prescribed_bandwidth_hz"
    )
    return _same(applied, prescribed)


def bandwidth_level_error_db(applied_bandwidth_hz, prescribed_bandwidth_hz):
    """Level error a bandwidth substitution carries into the record, in dB.

    A survey that measures in one bandwidth and reports against a limit
    written for another is off by the ratio of the two, taken as a
    voltage ratio. The value is reported so the size of the substitution
    is visible; it is never used to correct a level back onto the limit.
    """
    applied = _as_positive_float(applied_bandwidth_hz, "applied_bandwidth_hz")
    prescribed = _as_positive_float(
        prescribed_bandwidth_hz, "prescribed_bandwidth_hz"
    )
    return 20.0 * math.log10(applied / prescribed)


def exceeds_limit(level_dbuv, limit_dbuv):
    """True when a level sits above its limit, character notwithstanding."""
    level = _as_float(level_dbuv, "level_dbuv")
    limit = _as_float(limit_dbuv, "limit_dbuv")
    if level <= limit:
        return False
    return not math.isclose(level, limit, rel_tol=0.0, abs_tol=REL_TOL)


def evaluate_emission(emission):
    """Evaluate one recorded emission against the identification rule."""
    if not isinstance(emission, dict):
        raise ValueError(
            "emission must be a mapping, got %s" % type(emission).__name__
        )
    unknown = [key for key in emission if key not in _EMISSION_KEYS]
    if unknown:
        raise ValueError(
            "emission carries unknown key(s): %s" % ", ".join(sorted(unknown))
        )
    missing = [key for key in _REQUIRED_KEYS if key not in emission]
    if missing:
        raise ValueError(
            "emission is missing required key(s): %s" % ", ".join(missing)
        )
    if not isinstance(emission["id"], str) or not emission["id"].strip():
        raise ValueError("emission id must be a non-blank string")
    identifier = emission["id"].strip()
    frequency = _as_positive_float(emission["frequency_hz"], "frequency_hz")
    character = normalize_character(emission["character"])
    prescribed = _as_positive_float(
        emission["prescribed_bandwidth_hz"], "prescribed_bandwidth_hz"
    )
    applied = _as_positive_float(
        emission["applied_bandwidth_hz"], "applied_bandwidth_hz"
    )
    level = _as_float(emission["level_dbuv"], "level_dbuv")
    limit = None
    if "limit_dbuv" in emission:
        limit = _as_float(emission["limit_dbuv"], "limit_dbuv")
    reported = emission.get("reported", True)
    if not isinstance(reported, bool):
        raise ValueError("reported must be true or false when it is given")
    omitted_reason = emission.get("omitted_reason")
    if omitted_reason is not None and (
        not isinstance(omitted_reason, str) or not omitted_reason.strip()
    ):
        raise ValueError("omitted_reason must be a non-blank string when it is given")

    as_prescribed = _same(applied, prescribed)
    level_error = bandwidth_level_error_db(applied, prescribed)
    over_limit = None if limit is None else exceeds_limit(level, limit)

    findings = []
    if not as_prescribed:
        findings.append(
            _finding(
                "bandwidth-not-as-prescribed",
                identifier,
                "measured in %.6g Hz where the range prescribes %.6g Hz, a "
                "%.3f dB shift on the recorded level"
                % (applied, prescribed, level_error),
            )
        )
    if omitted_reason is not None:
        findings.append(
            _finding(
                "character-based-omission",
                identifier,
                "left out of the record on the grounds %r; the rule admits no "
                "omission by signal character" % omitted_reason.strip(),
            )
        )
    if over_limit and not reported:
        findings.append(
            _finding(
                "emission-not-reported",
                identifier,
                "sits %.3f dB above its limit but is marked unreported"
                % (level - limit),
            )
        )
    return {
        "id": identifier,
        "frequency_hz": frequency,
        "character": character,
        "prescribed_bandwidth_hz": prescribed,
        "applied_bandwidth_hz": applied,
        "bandwidth_ratio": applied / prescribed,
        "bandwidth_level_error_db": level_error,
        "as_prescribed": as_prescribed,
        "level_dbuv": level,
        "limit_dbuv": limit,
        "exceeds_limit": over_limit,
        "reported": reported,
        "findings": findings,
        "conforming": not findings,
    }


def character_neutrality_audit(records):
    """Group a survey by character and look for a character-driven bandwidth."""
    if isinstance(records, (str, bytes)) or not hasattr(records, "__iter__"):
        raise ValueError("records must be an iterable of evaluated emissions")
    groups = {}
    for record in records:
        if not isinstance(record, dict) or "character" not in record:
            raise ValueError("every record must be an evaluated emission")
        group = groups.setdefault(
            record["character"],
            {"character": record["character"], "count": 0, "deviating": 0, "ratios": []},
        )
        group["count"] += 1
        if not record["as_prescribed"]:
            group["deviating"] += 1
        group["ratios"].append(record["bandwidth_ratio"])
    if not groups:
        raise ValueError("a survey must contain at least one emission")
    for group in groups.values():
        unique = []
        for ratio in group["ratios"]:
            if not any(_same(ratio, seen) for seen in unique):
                unique.append(ratio)
        group["unique_ratios"] = unique
        group["uniform_ratio"] = unique[0] if len(unique) == 1 else None
    neutral_groups = [g for g in groups.values() if g["deviating"] == 0]
    findings = []
    for character in sorted(groups):
        group = groups[character]
        systematic = (
            group["deviating"] == group["count"]
            and group["uniform_ratio"] is not None
            and not _same(group["uniform_ratio"], 1.0)
        )
        if systematic and neutral_groups:
            findings.append(
                _finding(
                    "character-dependent-bandwidth",
                    character,
                    "every %s emission was taken at %.4f times the prescribed "
                    "bandwidth while other characters were taken as prescribed"
                    % (character, group["uniform_ratio"]),
                )
            )
    return {
        "groups": [groups[character] for character in sorted(groups)],
        "character_count": len(groups),
        "findings": findings,
        "neutral": not findings,
    }


def reportable_emissions(records):
    """Identifiers of emissions above their limit, whatever their character."""
    if isinstance(records, (str, bytes)) or not hasattr(records, "__iter__"):
        raise ValueError("records must be an iterable of evaluated emissions")
    return [
        record["id"]
        for record in records
        if record.get("exceeds_limit") is True
    ]


def assess_emission_survey(emissions):
    """Assess a whole emission survey against the identification rule."""
    if isinstance(emissions, (str, bytes)) or not hasattr(emissions, "__iter__"):
        raise ValueError("emissions must be an iterable of emission records")
    evaluated = [evaluate_emission(emission) for emission in emissions]
    if not evaluated:
        raise ValueError("a survey must contain at least one emission")
    seen = set()
    for record in evaluated:
        if record["id"] in seen:
            raise ValueError("emission %r appears twice" % record["id"])
        seen.add(record["id"])
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])
    audit = character_neutrality_audit(evaluated)
    findings.extend(audit["findings"])
    reportable = reportable_emissions(evaluated)
    graded = [record for record in evaluated if record["exceeds_limit"] is not None]
    accepted = not findings
    return {
        "verdict": "character-neutral" if accepted else "non-conforming",
        "accepted": accepted,
        "emissions": evaluated,
        "emission_count": len(evaluated),
        "graded_count": len(graded),
        "reportable_ids": reportable,
        "character_audit": audit,
        "findings": findings,
        "as_prescribed_fraction": sum(1 for r in evaluated if r["as_prescribed"])
        / float(len(evaluated)),
    }
