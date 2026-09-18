#!/usr/bin/env python3
"""Hermetically encapsulated chip procurement logic (ECSS-Q-ST-60-05 8.4).

Deterministic, offline, stdlib-only helpers for chips bought already
sealed inside their own hermetic enclosure:

- confirm every mandatory purchasing provision is declared rather than
  left blank, absent or written as an unknown,
- derive the fine-leak reject limit the sealed cavity volume earns from
  the band schedule,
- hold the measured equivalent standard leak rate against that limit at
  the exact boundary,
- refuse to credit a fine-leak reading behind a failed gross-leak test,
- hold the internal moisture content against its ceiling.

Anchor: ECSS-Q-ST-60-05 clause 8.4 (paraphrased provisions only).
"""

import math

# Provisions the purchase specification owes for a pre-sealed chip. A
# provision left blank is a missing provision, never a zero.
MANDATORY_PROVISIONS = (
    "seal_method",
    "cavity_volume_cc",
    "gross_leak_method",
    "fine_leak_method",
    "internal_moisture_limit_ppmv",
    "lot_date_code_traceability",
    "screening_level",
    "storage_and_handling",
)

# Values that look declared but say nothing.
NULL_TOKENS = frozenset({"", "tbd", "tbc", "n/a", "na", "none", "unknown", "-"})

# Fine-leak reject limit in atm cm3/s by sealed cavity volume in cm3. A
# larger cavity dilutes a given leak, so its limit is looser.
FINE_LEAK_BANDS = (
    (0.01, 5e-8),
    (0.4, 1e-7),
    (math.inf, 1e-6),
)

DEFAULT_MOISTURE_LIMIT_PPMV = 5000.0

# Leak rates and their limits are floats; a reading that sits exactly on
# its limit can evaluate a few ULPs high. The tolerance absorbs that
# representation error only - the limit is never relaxed.
REL_TOL = 1e-9
ABS_TOL = 1e-30


def _at_most(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def _as_float(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (field, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (field, value))
    return number


def _as_bool(value, field):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean outcome, got %r" % (field, value))
    return value


def is_declared(value):
    """True when a provision value actually says something.

    None, a blank string and the usual placeholder tokens are not
    declarations - an undeclared provision is unknown, not satisfied.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, str):
        return value.strip().lower() not in NULL_TOKENS
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def check_provision_coverage(spec, required=MANDATORY_PROVISIONS):
    """Group the mandatory purchasing provisions as declared or missing."""
    if not isinstance(spec, dict):
        raise ValueError("purchase specification must be a mapping, got %r" % (spec,))
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required provision list must be non-empty")
    declared = []
    missing = []
    for name in required:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("provision names must be non-empty strings")
        key = name.strip()
        if is_declared(spec.get(key)):
            declared.append(key)
        else:
            missing.append(key)
    extra = sorted(set(spec) - set(n.strip() for n in required))
    return {
        "declared": declared,
        "missing": missing,
        "additional": extra,
        "complete": not missing,
    }


def fine_leak_reject_limit(cavity_volume_cc):
    """Fine-leak reject limit earned by a sealed cavity of this volume.

    Raises ValueError on a non-positive or non-finite volume - a package
    with no declared cavity volume has no limit to be graded against.
    """
    volume = _as_float(cavity_volume_cc, "cavity_volume_cc")
    if volume <= 0.0:
        raise ValueError(
            "cavity_volume_cc must be > 0, got %r" % (cavity_volume_cc,)
        )
    for upper, limit in FINE_LEAK_BANDS:
        if volume <= upper:
            return limit
    raise ValueError("no fine-leak band covers %r cm3" % (cavity_volume_cc,))


def evaluate_fine_leak(measured_rate, cavity_volume_cc):
    """Grade one equivalent standard leak rate against its band limit."""
    rate = _as_float(measured_rate, "measured_rate")
    if rate < 0.0:
        raise ValueError("measured_rate must be >= 0, got %r" % (measured_rate,))
    limit = fine_leak_reject_limit(cavity_volume_cc)
    within = _at_most(rate, limit)
    return {
        "measured_rate": rate,
        "limit": limit,
        "margin": limit - rate,
        "within_limit": within,
    }


def evaluate_moisture(moisture_ppmv, limit_ppmv=DEFAULT_MOISTURE_LIMIT_PPMV):
    """Grade the internal moisture content against its ceiling."""
    measured = _as_float(moisture_ppmv, "moisture_ppmv")
    if measured < 0.0:
        raise ValueError("moisture_ppmv must be >= 0, got %r" % (moisture_ppmv,))
    ceiling = _as_float(limit_ppmv, "limit_ppmv")
    if ceiling <= 0.0:
        raise ValueError("limit_ppmv must be > 0, got %r" % (limit_ppmv,))
    return {
        "moisture_ppmv": measured,
        "limit_ppmv": ceiling,
        "within_limit": _at_most(measured, ceiling),
    }


def validate_seal_evidence(evidence):
    """Normalize the seal-integrity evidence delivered with the chips.

    evidence keys: gross_leak_passed (bool), fine_leak_rate (number) and
    moisture_ppmv (number). Raises ValueError on any malformed field.
    """
    if not isinstance(evidence, dict):
        raise ValueError("seal evidence must be a mapping, got %r" % (evidence,))
    gross = _as_bool(evidence.get("gross_leak_passed"), "gross_leak_passed")
    rate = _as_float(evidence.get("fine_leak_rate"), "fine_leak_rate")
    if rate < 0.0:
        raise ValueError("fine_leak_rate must be >= 0, got %r" % (rate,))
    moisture = evidence.get("moisture_ppmv")
    if moisture is not None:
        moisture = _as_float(moisture, "moisture_ppmv")
    return {
        "gross_leak_passed": gross,
        "fine_leak_rate": rate,
        "moisture_ppmv": moisture,
    }


def assess_hermetic_procurement(spec, evidence, required=MANDATORY_PROVISIONS):
    """Grade a whole clause 8.4 pre-sealed chip procurement.

    Returns a report dict with the provision coverage, the seal-integrity
    evaluations and the findings. cleared is True only when findings is
    empty.
    """
    coverage = check_provision_coverage(spec, required)
    seal = validate_seal_evidence(evidence)
    findings = []
    for name in coverage["missing"]:
        findings.append("purchasing provision %s is not declared" % name)
    fine = None
    moisture = None
    if is_declared(spec.get("cavity_volume_cc")):
        fine = evaluate_fine_leak(seal["fine_leak_rate"], spec["cavity_volume_cc"])
        if not seal["gross_leak_passed"]:
            findings.append(
                "gross-leak test failed: the %.3e atm cm3/s fine-leak reading "
                "cannot be credited behind it" % fine["measured_rate"]
            )
        elif not fine["within_limit"]:
            findings.append(
                "equivalent standard leak rate %.3e atm cm3/s exceeds the "
                "%.3e atm cm3/s limit for a %.4f cm3 cavity"
                % (
                    fine["measured_rate"],
                    fine["limit"],
                    _as_float(spec["cavity_volume_cc"], "cavity_volume_cc"),
                )
            )
    else:
        findings.append(
            "sealed cavity volume is not declared: no fine-leak limit can be derived"
        )
        if not seal["gross_leak_passed"]:
            findings.append("gross-leak test failed")
    if seal["moisture_ppmv"] is None:
        findings.append("internal moisture content was not reported")
    elif is_declared(spec.get("internal_moisture_limit_ppmv")):
        moisture = evaluate_moisture(
            seal["moisture_ppmv"], spec["internal_moisture_limit_ppmv"]
        )
        if not moisture["within_limit"]:
            findings.append(
                "internal moisture %.1f ppmv exceeds the %.1f ppmv ceiling"
                % (moisture["moisture_ppmv"], moisture["limit_ppmv"])
            )
    return {
        "coverage": coverage,
        "seal_evidence": seal,
        "fine_leak": fine,
        "moisture": moisture,
        "gross_leak_passed": seal["gross_leak_passed"],
        "findings": findings,
        "cleared": not findings,
    }


def format_procurement_report(report):
    """Render a procurement assessment as deterministic plain-text lines."""
    fine = report["fine_leak"]
    moisture = report["moisture"]
    lines = [
        "hermetically encapsulated chip procurement: %s"
        % ("CLEARED" if report["cleared"] else "NOT CLEARED"),
        "provisions declared=%d missing=%d gross-leak=%s"
        % (
            len(report["coverage"]["declared"]),
            len(report["coverage"]["missing"]),
            "pass" if report["gross_leak_passed"] else "fail",
        ),
    ]
    if fine is not None:
        lines.append(
            "  fine-leak rate=%.3e limit=%.3e within=%s"
            % (fine["measured_rate"], fine["limit"], "yes" if fine["within_limit"] else "no")
        )
    if moisture is not None:
        lines.append(
            "  moisture=%.1f ppmv ceiling=%.1f ppmv within=%s"
            % (
                moisture["moisture_ppmv"],
                moisture["limit_ppmv"],
                "yes" if moisture["within_limit"] else "no",
            )
        )
    for finding in report["findings"]:
        lines.append("  FINDING: %s" % finding)
    return "\n".join(lines)
