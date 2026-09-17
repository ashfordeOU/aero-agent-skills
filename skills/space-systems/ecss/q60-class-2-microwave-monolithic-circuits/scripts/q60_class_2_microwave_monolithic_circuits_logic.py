#!/usr/bin/env python3
"""Design, choice, purchase and use of a class 2 microwave monolithic circuit.

Anchor: ECSS-Q-ST-60C clause 5.6.5 (design, selection, procurement and use of
microwave monolithic integrated circuits in class 2 equipment). Paraphrased
into an implementable procedure; no standard text is reproduced.

Class 2 widens the source base a monolithic microwave part may be drawn from
and pays for the width with evidence the project builds itself. The part is
bought as a component and used as a circuit, so the decision has two halves
that do not separate: what the source route and the delivery form oblige
before the part arrives, and what the radio-frequency chain then does to it.
This module decides both halves together and returns one disposition.

Procedure implemented here
--------------------------
1. Validate the case: the semiconductor technology, the source route, the
   delivery form, both frequency bands, the two-stage thermal path and the
   drive levels.
2. Measure the guard band between the operating band and the band the part was
   actually characterized over, at both edges.
3. Resolve the junction temperature across the die-to-case and the
   case-to-baseplate resistances and take its margin against the class 2
   derating limit.
4. Take the drive utilisation as a share of rated drive and the output backoff
   in decibels against the compression point.
5. Assemble the compensating evidence the source route, the delivery form and
   the electrostatic withstand oblige, and return the disposition.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "MMIC_TECHNOLOGIES",
    "SOURCE_ROUTES",
    "DELIVERY_FORMS",
    "EVIDENCE_BY_SOURCE_ROUTE",
    "BARE_DIE_EVIDENCE",
    "PLASTIC_ENCAPSULATED_EVIDENCE",
    "ESD_CONTROL_LEVELS",
    "DEFAULT_CLASS2_MMIC_POLICY",
    "ADMISSIBLE_AS_PROCURED",
    "ADMISSIBLE_WITH_EVIDENCE",
    "APPLICATION_NONCONFORMING",
    "NOT_ADMISSIBLE",
    "validate_class2_mmic_policy",
    "validate_class2_mmic_case",
    "band_guard_margins_ghz",
    "junction_temperature_c",
    "junction_temperature_margin_c",
    "drive_utilisation",
    "output_backoff_db",
    "esd_control_level",
    "compensating_evidence",
    "application_findings",
    "assess_class2_mmic",
]

# The technology decides what the die is made of, and with it the radiation
# behaviour, the thermal path and the screening that is meaningful.
MMIC_TECHNOLOGIES = (
    "gaas-phemt",
    "gaas-mesfet",
    "gan-hemt",
    "sige-bicmos",
    "inp-hbt",
)

# Where the part is drawn from, strongest demonstration first. Class 2 admits
# the commercial catalogue route that class 1 does not, and charges evidence
# for it.
SOURCE_ROUTES = (
    "space-qualified-catalogue",
    "qualified-foundry-custom",
    "commercial-foundry",
    "commercial-catalogue",
)

DELIVERY_FORMS = ("hermetic-packaged", "plastic-encapsulated", "bare-die")

EVIDENCE_BY_SOURCE_ROUTE = {
    "space-qualified-catalogue": ("lot-acceptance-testing",),
    "qualified-foundry-custom": (
        "foundry-process-survey",
        "evaluation-programme",
        "lot-acceptance-testing",
    ),
    "commercial-foundry": (
        "foundry-process-survey",
        "evaluation-programme",
        "radiation-evaluation",
        "lot-acceptance-testing",
        "construction-analysis",
    ),
    "commercial-catalogue": (
        "manufacturer-survey",
        "evaluation-programme",
        "radiation-evaluation",
        "upscreening-programme",
        "lot-acceptance-testing",
        "construction-analysis",
    ),
}

# A die delivered without its package moves hermeticity, visual inspection and
# the attach process onto the equipment builder.
BARE_DIE_EVIDENCE = (
    "bare-die-visual-inspection",
    "die-attach-and-interconnect-qualification",
    "cavity-seal-and-hermeticity-demonstration",
)

# A plastic body is permeable and moves moisture and popcorn behaviour onto
# the project instead.
PLASTIC_ENCAPSULATED_EVIDENCE = (
    "moisture-sensitivity-level-determination",
    "temperature-humidity-bias-demonstration",
)

# Human body model withstand thresholds in volts, ascending; the first band the
# withstand voltage falls below names the control level.
ESD_CONTROL_LEVELS = (
    (125.0, "esd-control-level-0a"),
    (250.0, "esd-control-level-0b"),
    (500.0, "esd-control-level-1a"),
    (1000.0, "esd-control-level-1b"),
    (2000.0, "esd-control-level-2"),
    (4000.0, "esd-control-level-3a"),
    (float("inf"), "esd-control-level-3b-or-above"),
)

DEFAULT_CLASS2_MMIC_POLICY = {
    # Junction temperature the class 2 derating rules cap the die at.
    "max_junction_temperature_c": 125.0,
    # Share of the rated drive the application may apply.
    "max_drive_utilisation": 0.85,
    # Guard band demanded at each edge of the characterized sweep, in GHz.
    "min_band_guard_ghz": 0.0,
    # Backoff demanded below the compression point, in decibels.
    "min_output_backoff_db": 1.0,
    # Electrostatic withstand below which reinforced controls attach.
    "esd_reinforced_threshold_v": 500.0,
    # Whether a plain commercial catalogue part may be taken to class 2.
    "allow_commercial_catalogue": True,
}

_ABSOLUTE_ZERO_C = -273.15

ADMISSIBLE_AS_PROCURED = "class-2-mmic-admissible-as-procured"
ADMISSIBLE_WITH_EVIDENCE = "class-2-mmic-admissible-with-compensating-evidence"
APPLICATION_NONCONFORMING = "class-2-mmic-application-nonconforming"
NOT_ADMISSIBLE = "class-2-mmic-not-admissible"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A junction temperature, a drive utilisation and a backoff in decibels are
    all computed, so a case sitting exactly on its limit can land a few units
    in the last place the wrong side of it. The limit is never moved; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_class2_mmic_policy(policy=None):
    """Return a complete class 2 selection policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_CLASS2_MMIC_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("class 2 mmic policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_CLASS2_MMIC_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_CLASS2_MMIC_POLICY:
            raise ValueError("unknown class 2 mmic policy key %r" % (key,))
        merged[key] = value
    limit = _require_number(
        "max_junction_temperature_c", merged["max_junction_temperature_c"]
    )
    if limit <= _ABSOLUTE_ZERO_C:
        raise ValueError("max_junction_temperature_c must be above absolute zero")
    utilisation = _require_positive(
        "max_drive_utilisation", merged["max_drive_utilisation"]
    )
    if utilisation > 1.0:
        raise ValueError(
            "max_drive_utilisation must not exceed 1.0, got %r" % (utilisation,)
        )
    _require_non_negative("min_band_guard_ghz", merged["min_band_guard_ghz"])
    _require_non_negative("min_output_backoff_db", merged["min_output_backoff_db"])
    _require_positive(
        "esd_reinforced_threshold_v", merged["esd_reinforced_threshold_v"]
    )
    if not isinstance(merged["allow_commercial_catalogue"], bool):
        raise ValueError("allow_commercial_catalogue must be a boolean")
    return merged


def _require_band(name, low, high):
    low = _require_positive("%s_low_ghz" % name, low)
    high = _require_positive("%s_high_ghz" % name, high)
    if high <= low:
        raise ValueError(
            "%s band is inverted or empty: %g GHz to %g GHz" % (name, low, high)
        )
    return low, high


def band_guard_margins_ghz(
    operating_low_ghz,
    operating_high_ghz,
    characterized_low_ghz,
    characterized_high_ghz,
):
    """Guard band at each edge between the operating and characterized sweeps.

    A positive lower guard means the application starts above the lowest
    frequency the part was measured at; a positive upper guard means it stops
    below the highest. A negative guard is the width the chain runs on data
    that was never taken.
    """
    op_low, op_high = _require_band("operating", operating_low_ghz, operating_high_ghz)
    ch_low, ch_high = _require_band(
        "characterized", characterized_low_ghz, characterized_high_ghz
    )
    lower = op_low - ch_low
    upper = ch_high - op_high
    return {
        "lower_guard_ghz": lower,
        "upper_guard_ghz": upper,
        "narrowest_guard_ghz": min(lower, upper),
        "uncharacterized_span_ghz": max(0.0, -lower) + max(0.0, -upper),
    }


def junction_temperature_c(
    baseplate_temperature_c,
    junction_to_case_c_per_w,
    case_to_baseplate_c_per_w,
    dissipated_power_w,
):
    """Junction temperature reached across the two-stage thermal path."""
    base = _require_number("baseplate_temperature_c", baseplate_temperature_c)
    if base <= _ABSOLUTE_ZERO_C:
        raise ValueError("baseplate_temperature_c must be above absolute zero")
    r_jc = _require_non_negative(
        "junction_to_case_c_per_w", junction_to_case_c_per_w
    )
    r_cb = _require_non_negative(
        "case_to_baseplate_c_per_w", case_to_baseplate_c_per_w
    )
    power = _require_non_negative("dissipated_power_w", dissipated_power_w)
    return base + (r_jc + r_cb) * power


def junction_temperature_margin_c(junction_c, limit_c):
    """How far the junction sits below its limit; negative is a breach."""
    junction = _require_number("junction_c", junction_c)
    limit = _require_number("limit_c", limit_c)
    return limit - junction


def drive_utilisation(applied_drive_w, rated_drive_w):
    """Applied radio-frequency drive as a share of the rated drive."""
    applied = _require_non_negative("applied_drive_w", applied_drive_w)
    rated = _require_positive("rated_drive_w", rated_drive_w)
    return applied / rated


def output_backoff_db(applied_drive_w, compression_point_w):
    """Backoff of the applied drive below the compression point, in decibels.

    Positive means the stage runs below compression. The value is a ratio of
    powers turned into decibels, which is the representation a link budget
    quotes; comparing it against a limit is done with the tolerant helpers
    because a logarithm is not correctly rounded.
    """
    applied = _require_positive("applied_drive_w", applied_drive_w)
    compression = _require_positive("compression_point_w", compression_point_w)
    return 10.0 * math.log10(compression / applied)


def esd_control_level(withstand_voltage_v):
    """Handling control level named by the human body model withstand voltage."""
    voltage = _require_positive("withstand_voltage_v", withstand_voltage_v)
    for threshold, name in ESD_CONTROL_LEVELS:
        if voltage < threshold:
            return name
    return ESD_CONTROL_LEVELS[-1][1]


def compensating_evidence(
    source_route, delivery_form, withstand_voltage_v=None, policy=None
):
    """Evidence the route, the delivery form and the sensitivity oblige."""
    _require_choice("source_route", source_route, SOURCE_ROUTES)
    _require_choice("delivery_form", delivery_form, DELIVERY_FORMS)
    resolved = validate_class2_mmic_policy(policy)
    evidence = list(EVIDENCE_BY_SOURCE_ROUTE[source_route])
    if delivery_form == "bare-die":
        extra = BARE_DIE_EVIDENCE
    elif delivery_form == "plastic-encapsulated":
        extra = PLASTIC_ENCAPSULATED_EVIDENCE
    else:
        extra = ()
    for item in extra:
        if item not in evidence:
            evidence.append(item)
    if withstand_voltage_v is not None:
        voltage = _require_positive("withstand_voltage_v", withstand_voltage_v)
        if voltage < resolved["esd_reinforced_threshold_v"]:
            item = "reinforced-electrostatic-discharge-controls"
            if item not in evidence:
                evidence.append(item)
    return tuple(evidence)


def application_findings(case, policy=None):
    """Band, thermal and drive findings the chain raises against the part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    resolved = validate_class2_mmic_policy(policy)
    findings = []

    guards = band_guard_margins_ghz(
        case.get("operating_low_ghz"),
        case.get("operating_high_ghz"),
        case.get("characterized_low_ghz"),
        case.get("characterized_high_ghz"),
    )
    band_ok = _at_least(
        guards["narrowest_guard_ghz"], resolved["min_band_guard_ghz"]
    )
    if not band_ok:
        findings.append(
            "the chain runs %.3f GHz on frequencies the part was never measured at"
            % guards["uncharacterized_span_ghz"]
        )

    junction = junction_temperature_c(
        case.get("baseplate_temperature_c"),
        case.get("junction_to_case_c_per_w"),
        case.get("case_to_baseplate_c_per_w"),
        case.get("dissipated_power_w"),
    )
    margin = junction_temperature_margin_c(
        junction, resolved["max_junction_temperature_c"]
    )
    thermal_ok = _at_most(junction, resolved["max_junction_temperature_c"])
    if not thermal_ok:
        findings.append(
            "the junction reaches %.2f C against a %.2f C class 2 derating limit"
            % (junction, resolved["max_junction_temperature_c"])
        )

    utilisation = drive_utilisation(
        case.get("applied_drive_w"), case.get("rated_drive_w")
    )
    drive_ok = _at_most(utilisation, resolved["max_drive_utilisation"])
    if not drive_ok:
        findings.append(
            "the applied drive is %.3f of rated against a %.3f derating limit"
            % (utilisation, resolved["max_drive_utilisation"])
        )

    backoff = output_backoff_db(
        case.get("applied_drive_w"), case.get("compression_point_w")
    )
    backoff_ok = _at_least(backoff, resolved["min_output_backoff_db"])
    if not backoff_ok:
        findings.append(
            "the stage sits %.3f dB below compression against a %.3f dB floor"
            % (backoff, resolved["min_output_backoff_db"])
        )

    return {
        "lower_guard_ghz": guards["lower_guard_ghz"],
        "upper_guard_ghz": guards["upper_guard_ghz"],
        "uncharacterized_span_ghz": guards["uncharacterized_span_ghz"],
        "band_ok": band_ok,
        "junction_temperature_c": junction,
        "junction_temperature_margin_c": margin,
        "thermal_ok": thermal_ok,
        "drive_utilisation": utilisation,
        "drive_ok": drive_ok,
        "output_backoff_db": backoff,
        "backoff_ok": backoff_ok,
        "findings": findings,
    }


def validate_class2_mmic_case(case):
    """Check a class 2 selection case names every field the decision needs."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    _require_choice("technology", case.get("technology"), MMIC_TECHNOLOGIES)
    _require_choice("source_route", case.get("source_route"), SOURCE_ROUTES)
    _require_choice("delivery_form", case.get("delivery_form"), DELIVERY_FORMS)
    for field in (
        "operating_low_ghz",
        "operating_high_ghz",
        "characterized_low_ghz",
        "characterized_high_ghz",
        "baseplate_temperature_c",
        "junction_to_case_c_per_w",
        "case_to_baseplate_c_per_w",
        "dissipated_power_w",
        "applied_drive_w",
        "rated_drive_w",
        "compression_point_w",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    return case


def assess_class2_mmic(case, policy=None):
    """Full clause 5.6.5 class 2 decision with evidence and a disposition."""
    validate_class2_mmic_case(case)
    resolved = validate_class2_mmic_policy(policy)
    application = application_findings(case, resolved)
    findings = list(application["findings"])

    source_route = case["source_route"]
    route_admissible = True
    if source_route == "commercial-catalogue" and not resolved[
        "allow_commercial_catalogue"
    ]:
        findings.append(
            "the project policy does not admit a commercial catalogue part at class 2"
        )
        route_admissible = False

    withstand = case.get("esd_withstand_voltage_v")
    control_level = (
        esd_control_level(withstand) if withstand is not None else None
    )
    evidence = compensating_evidence(
        source_route, case["delivery_form"], withstand, resolved
    )
    beyond_catalogue = tuple(
        item
        for item in evidence
        if item not in EVIDENCE_BY_SOURCE_ROUTE["space-qualified-catalogue"]
    )

    application_ok = (
        application["band_ok"]
        and application["thermal_ok"]
        and application["drive_ok"]
        and application["backoff_ok"]
    )

    if not route_admissible:
        disposition = NOT_ADMISSIBLE
    elif not application_ok:
        disposition = APPLICATION_NONCONFORMING
    elif beyond_catalogue:
        disposition = ADMISSIBLE_WITH_EVIDENCE
    else:
        disposition = ADMISSIBLE_AS_PROCURED

    return {
        "disposition": disposition,
        "admissible": disposition
        in (ADMISSIBLE_AS_PROCURED, ADMISSIBLE_WITH_EVIDENCE),
        "technology": case["technology"],
        "source_route": source_route,
        "delivery_form": case["delivery_form"],
        "lower_guard_ghz": application["lower_guard_ghz"],
        "upper_guard_ghz": application["upper_guard_ghz"],
        "uncharacterized_span_ghz": application["uncharacterized_span_ghz"],
        "junction_temperature_c": application["junction_temperature_c"],
        "junction_temperature_margin_c": application["junction_temperature_margin_c"],
        "drive_utilisation": application["drive_utilisation"],
        "output_backoff_db": application["output_backoff_db"],
        "esd_control_level": control_level,
        "compensating_evidence": evidence,
        "evidence_beyond_catalogue": beyond_catalogue,
        "findings": findings,
    }
