"""Shielding, Faraday caps and safety caps on initiator circuits.

Anchor: ECSS-E-ST-33-11C clauses 4.10.3 to 4.10.5 -- electromagnetic shielding
of the initiation circuit and the protective caps fitted to it. Paraphrased
into an implementable procedure; no standard text is reproduced.

Three protections, each covering a state the others do not.

Shielding covers the mated, installed circuit. An external field couples into
the firing loop and arrives at the bridgewire as power; the shield attenuates
it, and what is left has to sit below the no-fire power by the margin the
project set. The inverse is the shield effectiveness the design needs, which
is the number that actually goes on a drawing.

A Faraday cap covers the demated connector on the initiator side. With the
harness off, the initiator pins are an antenna with a bridgewire across them,
and the cap shorts the pins to each other and to the case so there is no loop
and no potential to develop.

A safety cap covers the operation. It is fitted from the moment the item is
received until an authorised removal point late in the sequence, and it goes
back on if the sequence is interrupted. Checking it is checking an ordered
list of ground operations against a stated authorisation point, which is the
part a static margin calculation cannot see.
"""

import math

__all__ = [
    "PROTECTED",
    "MARGIN_SHORT",
    "CAP_DEFECT",
    "UNPROTECTED",
    "REL_TOL",
    "ABS_TOL_DB",
    "FARADAY_REQUIREMENTS",
    "validate_positive",
    "validate_non_negative",
    "validate_db",
    "power_attenuation_factor",
    "field_attenuation_factor",
    "shielded_power_w",
    "no_fire_margin_db",
    "required_shield_db",
    "faraday_cap_findings",
    "safety_cap_findings",
    "assess_initiator_protection",
]

PROTECTED = "protected"
MARGIN_SHORT = "margin-short"
CAP_DEFECT = "cap-defect"
UNPROTECTED = "unprotected"

# Relative tolerance on ratios and an absolute one on decibel comparisons, so a
# design sized to land exactly on its margin is graded the same way on every
# platform. Decibels come from log10, which is not correctly rounded.
REL_TOL = 1e-9
ABS_TOL_DB = 1e-9

# What a Faraday cap has to do to count as one.
FARADAY_REQUIREMENTS = (
    "shorts_pin_to_pin",
    "shorts_pin_to_case",
    "fitted_when_demated",
)


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive value."""
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_non_negative(value, name="value"):
    """Return a value of zero or more."""
    number = _validate_number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_db(value, name="shield_db"):
    """Return a shield effectiveness in decibels of zero or more.

    A negative effectiveness would mean the shield amplifies what it is there
    to attenuate, which is a sign error rather than a design.
    """
    return validate_non_negative(value, name)


def power_attenuation_factor(shield_db):
    """Return the factor a shield divides incident power by."""
    db = validate_db(shield_db)
    return 10.0 ** (db / 10.0)


def field_attenuation_factor(shield_db):
    """Return the factor a shield divides an incident field strength by."""
    db = validate_db(shield_db)
    return 10.0 ** (db / 20.0)


def shielded_power_w(incident_power_w, shield_db):
    """Return the power that reaches the bridgewire through the shield."""
    incident = validate_non_negative(incident_power_w, "incident_power_w")
    return incident / power_attenuation_factor(shield_db)


def no_fire_margin_db(incident_power_w, shield_db, no_fire_power_w):
    """Return how far below the no-fire power the shielded pickup sits.

    None means the margin is unbounded: no power couples in at all, and a
    finite decibel figure there would be an invention.
    """
    incident = validate_non_negative(incident_power_w, "incident_power_w")
    no_fire = validate_positive(no_fire_power_w, "no_fire_power_w")
    delivered = shielded_power_w(incident, shield_db)
    if delivered == 0.0:
        return None
    return 10.0 * math.log10(no_fire / delivered)


def required_shield_db(incident_power_w, no_fire_power_w, required_margin_db):
    """Return the shield effectiveness the required margin asks for.

    Zero means the unshielded pickup already clears the margin, so the shield
    is there for other reasons and not for this one.
    """
    incident = validate_non_negative(incident_power_w, "incident_power_w")
    no_fire = validate_positive(no_fire_power_w, "no_fire_power_w")
    margin = validate_db(required_margin_db, "required_margin_db")
    if incident == 0.0:
        return 0.0
    needed = 10.0 * math.log10(incident / no_fire) + margin
    if needed < 0.0:
        return 0.0
    return needed


def faraday_cap_findings(declared):
    """Return what a declared Faraday cap does not do."""
    if not isinstance(declared, dict):
        raise ValueError("declared must be a mapping of feature names to booleans")
    findings = []
    for feature in FARADAY_REQUIREMENTS:
        value = declared.get(feature, False)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean, got %r" % (feature, value))
        if not value:
            findings.append(
                "Faraday cap does not provide %s, so a demated initiator is an "
                "open antenna across its bridgewire" % feature
            )
    return findings


def safety_cap_findings(steps, authorised_removal_step):
    """Return where a ground operation sequence leaves an initiator bare.

    `steps` is an ordered list of mappings, each with a name and a boolean
    saying whether the safety cap is fitted during that step. The cap has to be
    fitted for every step up to the authorised removal point, and refitted for
    any step after it that is an interruption.
    """
    if isinstance(steps, (str, bytes, dict)) or not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple of mappings")
    if len(steps) == 0:
        raise ValueError("steps must name at least one ground operation")
    if not isinstance(authorised_removal_step, str) or not authorised_removal_step.strip():
        raise ValueError("authorised_removal_step must be a non-empty step name")
    names = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("steps[%d] must be a mapping" % index)
        name = step.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("steps[%d] needs a non-empty name" % index)
        fitted = step.get("cap_fitted", False)
        if not isinstance(fitted, bool):
            raise ValueError("steps[%d].cap_fitted must be a boolean" % index)
        interrupted = step.get("interrupted", False)
        if not isinstance(interrupted, bool):
            raise ValueError("steps[%d].interrupted must be a boolean" % index)
        names.append(name)
    target = authorised_removal_step.strip()
    if target not in names:
        raise ValueError(
            "authorised_removal_step %r is not one of the steps given" % target
        )
    removal_index = names.index(target)
    findings = []
    for index, step in enumerate(steps):
        name = step["name"]
        fitted = step.get("cap_fitted", False)
        interrupted = step.get("interrupted", False)
        if index < removal_index and not fitted:
            findings.append(
                "safety cap is off during %r, which runs before the authorised "
                "removal at %r" % (name, target)
            )
        if index > removal_index and interrupted and not fitted:
            findings.append(
                "sequence is interrupted at %r with the safety cap off; it goes "
                "back on for an interruption" % name
            )
    return findings


def assess_initiator_protection(
    incident_power_w,
    shield_db,
    no_fire_power_w,
    required_margin_db,
    faraday_declared,
    steps,
    authorised_removal_step,
):
    """Grade the shielding and the caps on one initiator circuit."""
    incident = validate_non_negative(incident_power_w, "incident_power_w")
    shield = validate_db(shield_db)
    no_fire = validate_positive(no_fire_power_w, "no_fire_power_w")
    required = validate_db(required_margin_db, "required_margin_db")
    delivered = shielded_power_w(incident, shield)
    margin = no_fire_margin_db(incident, shield, no_fire)
    needed = required_shield_db(incident, no_fire, required)
    cap_findings = list(faraday_cap_findings(faraday_declared))
    cap_findings.extend(safety_cap_findings(steps, authorised_removal_step))
    findings = []
    fires = delivered > no_fire * (1.0 + REL_TOL)
    short = margin is not None and margin < required - ABS_TOL_DB
    if fires:
        findings.append(
            "shielded pickup of %.6g W exceeds the no-fire power of %.6g W; the "
            "circuit can be set off by the field it is exposed to"
            % (delivered, no_fire)
        )
    elif short:
        findings.append(
            "shielded pickup sits %.6g dB below the no-fire power against a "
            "required margin of %.6g dB" % (margin, required)
        )
    if fires or short:
        findings.append(
            "a shield effectiveness of at least %.6g dB reaches the required "
            "margin against this field" % needed
        )
    findings.extend(cap_findings)
    if fires:
        verdict = UNPROTECTED
    elif cap_findings:
        verdict = CAP_DEFECT
    elif short:
        verdict = MARGIN_SHORT
    else:
        verdict = PROTECTED
    return {
        "incident_power_w": incident,
        "shield_db": shield,
        "shielded_power_w": delivered,
        "no_fire_power_w": no_fire,
        "no_fire_margin_db": margin,
        "required_margin_db": required,
        "required_shield_db": needed,
        "faraday_findings": faraday_cap_findings(faraday_declared),
        "safety_cap_findings": safety_cap_findings(steps, authorised_removal_step),
        "verdict": verdict,
        "findings": findings,
    }
