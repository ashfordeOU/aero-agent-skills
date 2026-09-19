#!/usr/bin/env python3
"""Control of the test specimen, ECSS-Q-ST-20-07C clause 5.7.4.3.

Paraphrased clause intent, no verbatim standard text. A customer's test
item arriving at a test centre is inspected, identified uniquely inside
that centre, recorded in the build it actually arrived in, and held in
an unbroken custody chain until it leaves. This module turns an intake
record into a deterministic disposition:

  marking vs register        -> is this item distinguishable in-house
  declared vs as-received    -> did the build that arrived match
  weighed vs declared mass   -> the cheap independent configuration check
  accompanying documents     -> can the item be handled and tested at all
  custody events             -> is any period unaccounted for

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Masses and allowances are floats, so an item
# exactly on its allowance can compute a few units in the last place
# outside it. The tolerance absorbs that representation error only; it
# never widens the allowance the customer declared.
REL_TOL = 1e-12
ABS_TOL = 1e-12

REQUIRED_DOCUMENTS = (
    "declared-configuration-list",
    "handling-instruction",
    "shipping-note",
)

# Markings that name a type or a placeholder rather than an object.
PLACEHOLDER_MARKINGS = ("n/a", "na", "none", "tbd", "unmarked", "unknown")

SPECIMEN_ACCEPTED = "specimen-accepted"
SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE = "specimen-accepted-with-nonconformance"
SPECIMEN_QUARANTINED = "specimen-quarantined"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def normalise(text):
    """Collapse case and whitespace so formatting is not a difference."""
    if not isinstance(text, str):
        raise ValueError("text: must be a string, got %r" % (text,))
    return " ".join(text.lower().split())


def validate_specimen_record(record):
    """Validate a specimen intake record and return it normalized."""
    where = "specimen"
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)

    out = {}
    for key in ("identifier", "declared_configuration", "as_received_configuration"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s: %s must be a non-empty string" % (where, key))
        out[key] = value.strip()

    for key in (
        "receipt_inspection_performed",
        "damage_observed",
        "protective_packaging_intact",
    ):
        out[key] = _flag(record, key, where)

    for key in ("mass_kg", "declared_mass_kg", "mass_allowance_kg"):
        value = _number(record, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        out[key] = value

    documents = record.get("accompanying_documents", [])
    if not isinstance(documents, (list, tuple)):
        raise ValueError("%s: accompanying_documents must be a sequence" % where)
    out["accompanying_documents"] = sorted(
        {normalise(str(doc)) for doc in documents if str(doc).strip()}
    )
    return out


def identification_findings(identifier, register):
    """Report a marking that is a placeholder or already used in the centre."""
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("identifier must be a non-empty string")
    if not isinstance(register, (list, tuple, set, frozenset)):
        raise ValueError("register must be a sequence or set of held markings")
    marking = normalise(identifier)
    held = {normalise(str(entry)) for entry in register}
    out = []
    if marking in PLACEHOLDER_MARKINGS:
        out.append(
            "the marking %r names no object, so the item cannot be told apart from "
            "anything else on the floor" % identifier.strip()
        )
    if marking in held:
        out.append(
            "the marking %r is already held against another item in the centre "
            "register" % identifier.strip()
        )
    return out


def configuration_matches(declared, as_received):
    """True when the build that arrived is the build the customer declared."""
    return normalise(declared) == normalise(as_received)


def mass_within_allowance(mass_kg, declared_mass_kg, allowance_kg):
    """True when the weighed mass sits inside the declared allowance."""
    weighed = _scalar(mass_kg, "mass_kg")
    declared = _scalar(declared_mass_kg, "declared_mass_kg")
    allowance = _scalar(allowance_kg, "allowance_kg")
    if weighed <= 0.0:
        raise ValueError("mass_kg must be > 0, got %g" % weighed)
    if declared <= 0.0:
        raise ValueError("declared_mass_kg must be > 0, got %g" % declared)
    if allowance <= 0.0:
        raise ValueError("allowance_kg must be > 0, got %g" % allowance)
    return at_most(abs(weighed - declared), allowance)


def missing_documents(supplied, required=REQUIRED_DOCUMENTS):
    """List the accompanying documents that did not arrive with the item."""
    if not isinstance(supplied, (list, tuple, set, frozenset)):
        raise ValueError("supplied: must be a sequence of document names")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required: must be a non-empty sequence of document names")
    have = {normalise(str(doc)) for doc in supplied if str(doc).strip()}
    return sorted(name for name in required if normalise(name) not in have)


def validate_custody_events(events):
    """Validate the custody chain and return it in time order."""
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("events: must be a non-empty sequence of custody handovers")
    out = []
    previous_time = None
    for index, event in enumerate(events):
        where = "events[%d]" % index
        if not isinstance(event, dict):
            raise ValueError("%s: record must be a mapping" % where)
        time_s = _number(event, "time_s", where)
        entry = {"time_s": time_s}
        for key in ("released_by", "received_by"):
            value = event.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("%s: %s must be a non-empty string" % (where, key))
            entry[key] = value.strip()
        if previous_time is not None and not time_s > previous_time:
            raise ValueError(
                "%s: handover at %g does not follow the previous one at %g"
                % (where, time_s, previous_time)
            )
        previous_time = time_s
        out.append(entry)
    return out


def custody_chain_findings(events):
    """Report every join where the chain of holders does not connect."""
    chain = validate_custody_events(events)
    out = []
    for index in range(1, len(chain)):
        previous = chain[index - 1]
        current = chain[index]
        if normalise(previous["received_by"]) != normalise(current["released_by"]):
            out.append(
                "custody passes from %s to %s at %g but the next handover is "
                "released by %s, leaving that period unaccounted for"
                % (
                    previous["released_by"],
                    previous["received_by"],
                    current["time_s"],
                    current["released_by"],
                )
            )
    return out


def specimen_disposition(findings, nonconformances, quarantine_reasons):
    """Grade the intake into accepted, accepted against a raised NCR, or held."""
    for name, value in (
        ("findings", findings),
        ("nonconformances", nonconformances),
        ("quarantine_reasons", quarantine_reasons),
    ):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s: must be a sequence" % name)
    if quarantine_reasons:
        return SPECIMEN_QUARANTINED
    if nonconformances or findings:
        return SPECIMEN_ACCEPTED_WITH_NONCONFORMANCE
    return SPECIMEN_ACCEPTED


def assess_specimen_control(record, register=(), events=None):
    """Full clause 5.7.4.3 intake assessment of one customer test item."""
    specimen = validate_specimen_record(record)
    identification = identification_findings(specimen["identifier"], register)
    matches = configuration_matches(
        specimen["declared_configuration"], specimen["as_received_configuration"]
    )
    mass_ok = mass_within_allowance(
        specimen["mass_kg"], specimen["declared_mass_kg"], specimen["mass_allowance_kg"]
    )
    documents = missing_documents(specimen["accompanying_documents"])
    chain = custody_chain_findings(events) if events else []

    nonconformances = []
    quarantine = []

    if not specimen["receipt_inspection_performed"]:
        quarantine.append(
            "no receipt inspection was carried out, so the state the item arrived "
            "in was never recorded"
        )
    if specimen["damage_observed"]:
        quarantine.append(
            "damage was observed on receipt and the item is held until the customer "
            "dispositions it"
        )
    if chain:
        quarantine.extend(chain)

    if not specimen["protective_packaging_intact"]:
        nonconformances.append(
            "the protective packaging did not arrive intact, so nothing evidences "
            "what the item saw in transit"
        )
    if not matches:
        nonconformances.append(
            "the as-received build %r is not the declared build %r"
            % (
                specimen["as_received_configuration"],
                specimen["declared_configuration"],
            )
        )
    if not mass_ok:
        nonconformances.append(
            "weighed mass %g kg differs from the declared %g kg by more than the "
            "%g kg allowance"
            % (
                specimen["mass_kg"],
                specimen["declared_mass_kg"],
                specimen["mass_allowance_kg"],
            )
        )
    for name in documents:
        nonconformances.append("the %s did not arrive with the item" % name)

    return {
        "specimen": specimen,
        "identification_findings": identification,
        "configuration_matches": matches,
        "mass_within_allowance": mass_ok,
        "missing_documents": documents,
        "custody_findings": chain,
        "nonconformances": nonconformances,
        "quarantine_reasons": quarantine,
        "disposition": specimen_disposition(identification, nonconformances, quarantine),
    }
