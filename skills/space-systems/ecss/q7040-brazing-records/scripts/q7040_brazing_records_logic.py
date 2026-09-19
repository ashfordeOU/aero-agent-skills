#!/usr/bin/env python3
"""Brazement records: procedure, operator, furnace data and inspection.

Anchor: ECSS-Q-ST-70-40 records clause on brazing of space hardware. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

A brazed joint cannot be re-opened to see how it was made, so the record
is the joint's only history. Four things have to be in it and each fails
differently.

The procedure. A brazement is made to a written brazing procedure, and
that procedure is backed by a qualification record made on coupons. The
procedure reference alone is a pointer; the qualification record is what
says the pointer leads anywhere.

The operator. Brazing is a manual-skill process even inside a furnace,
because the assembly, the filler placement and the fixturing are done by
hand. An operator qualification therefore expires on a date, and it also
lapses through disuse: an operator who has not run the process for
longer than the continuity interval is no longer current, whatever the
certificate expiry says.

The furnace run. The thermal profile is the process. A run identity with
no trace behind it records that a furnace was switched on. The trace has
to carry the ramp, the soak temperature, the soak duration and the
cooling rate, and the atmosphere log has to carry the vacuum level or
the dew point, because an inert-gas cycle with a wet atmosphere is a
different process from the one that was qualified.

The inspection. The result closes the record; without it the brazement
has a history and no verdict.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

PROCESS_TORCH = "torch-brazing"
PROCESS_INDUCTION = "induction-brazing"
PROCESS_FURNACE_VACUUM = "furnace-brazing-vacuum"
PROCESS_FURNACE_INERT = "furnace-brazing-inert-gas"

PROCESSES = (
    PROCESS_TORCH,
    PROCESS_INDUCTION,
    PROCESS_FURNACE_VACUUM,
    PROCESS_FURNACE_INERT,
)

_FURNACE_PROCESSES = frozenset((PROCESS_FURNACE_VACUUM, PROCESS_FURNACE_INERT))

FIELD_PROCEDURE_REFERENCE = "brazing-procedure-specification-reference"
FIELD_QUALIFICATION_RECORD = "procedure-qualification-record-reference"
FIELD_OPERATOR_IDENTITY = "operator-identity-and-qualification-reference"
FIELD_JOINT_IDENTITY = "joint-and-assembly-identity"
FIELD_FILLER_BATCH = "filler-metal-batch-identity"
FIELD_FLUX_BATCH = "flux-batch-identity"
FIELD_BRAZE_DATE = "braze-date"
FIELD_FURNACE_RUN = "furnace-run-identity"
FIELD_THERMAL_PROFILE = "furnace-thermal-profile-trace"
FIELD_ATMOSPHERE_LOG = "furnace-atmosphere-or-vacuum-log"
FIELD_INSPECTION_RESULT = "joint-inspection-result-record"

RECORD_FIELDS = (
    FIELD_PROCEDURE_REFERENCE,
    FIELD_QUALIFICATION_RECORD,
    FIELD_OPERATOR_IDENTITY,
    FIELD_JOINT_IDENTITY,
    FIELD_FILLER_BATCH,
    FIELD_FLUX_BATCH,
    FIELD_BRAZE_DATE,
    FIELD_FURNACE_RUN,
    FIELD_THERMAL_PROFILE,
    FIELD_ATMOSPHERE_LOG,
    FIELD_INSPECTION_RESULT,
)

_BASE_FIELDS = (
    FIELD_PROCEDURE_REFERENCE,
    FIELD_QUALIFICATION_RECORD,
    FIELD_OPERATOR_IDENTITY,
    FIELD_JOINT_IDENTITY,
    FIELD_FILLER_BATCH,
    FIELD_BRAZE_DATE,
)

PROFILE_RAMP_RATE = "ramp-rate-to-soak"
PROFILE_SOAK_TEMPERATURE = "soak-temperature"
PROFILE_SOAK_DURATION = "soak-duration"
PROFILE_COOLING_RATE = "controlled-cooling-rate"
PROFILE_LOAD_THERMOCOUPLES = "load-thermocouple-channels"

PROFILE_CHANNELS = (
    PROFILE_RAMP_RATE,
    PROFILE_SOAK_TEMPERATURE,
    PROFILE_SOAK_DURATION,
    PROFILE_COOLING_RATE,
    PROFILE_LOAD_THERMOCOUPLES,
)

# A furnace load is instrumented with at least this many load thermocouples
# so a cold corner of the load cannot hide behind the control channel.
MINIMUM_LOAD_THERMOCOUPLES = 2

# Days an operator may go without running the process before currency lapses.
DEFAULT_CONTINUITY_DAYS = 180

OPERATOR_CURRENT = "operator-current"
OPERATOR_EXPIRED = "operator-certificate-expired"
OPERATOR_LAPSED = "operator-continuity-lapsed"

VERDICT_COMPLETE = "brazement-record-complete"
VERDICT_INCOMPLETE = "brazement-record-incomplete"


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_date(name, value):
    if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
        raise ValueError("%s must be a datetime.date, got %r" % (name, value))
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def required_record_fields(process, uses_flux):
    """Fields the brazement record owes for this process."""
    _require_choice("process", process, PROCESSES)
    if not isinstance(uses_flux, bool):
        raise ValueError("uses_flux must be True or False, got %r" % (uses_flux,))
    fields = list(_BASE_FIELDS)
    if uses_flux:
        fields.append(FIELD_FLUX_BATCH)
    if process in _FURNACE_PROCESSES:
        fields.append(FIELD_FURNACE_RUN)
        fields.append(FIELD_THERMAL_PROFILE)
        fields.append(FIELD_ATMOSPHERE_LOG)
    fields.append(FIELD_INSPECTION_RESULT)
    return fields


def missing_record_fields(process, uses_flux, fields_present):
    """Required fields not on the record, in the order they were owed."""
    required = required_record_fields(process, uses_flux)
    if not isinstance(fields_present, (list, tuple, set)):
        raise ValueError("fields_present must be a sequence of field names")
    present = set()
    for name in fields_present:
        present.add(_require_choice("record field", name, RECORD_FIELDS))
    return [name for name in required if name not in present]


def operator_currency(
    certificate_expiry, last_process_run, braze_date, continuity_days=None
):
    """Whether the operator was current for the process on the braze date."""
    expiry = _require_date("certificate_expiry", certificate_expiry)
    last_run = _require_date("last_process_run", last_process_run)
    brazed = _require_date("braze_date", braze_date)
    limit = DEFAULT_CONTINUITY_DAYS if continuity_days is None else continuity_days
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError(
            "continuity_days must be a positive integer, got %r" % (continuity_days,)
        )
    if last_run > brazed:
        raise ValueError(
            "the operator's last recorded run (%s) is after the braze date "
            "(%s); the record is inconsistent" % (last_run, brazed)
        )
    gap = (brazed - last_run).days
    if brazed > expiry:
        status = OPERATOR_EXPIRED
    elif gap > limit:
        status = OPERATOR_LAPSED
    else:
        status = OPERATOR_CURRENT
    return {
        "status": status,
        "current": status == OPERATOR_CURRENT,
        "days_since_last_run": gap,
        "continuity_limit_days": limit,
        "days_to_certificate_expiry": (expiry - brazed).days,
    }


def furnace_data_gaps(run):
    """Channels the furnace run record does not actually carry."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))
    _require_identifier("run_id", run.get("run_id"))
    channels = run.get("channels_recorded", [])
    if not isinstance(channels, (list, tuple, set)):
        raise ValueError("channels_recorded must be a sequence of channel names")
    present = set()
    for name in channels:
        present.add(_require_choice("profile channel", name, PROFILE_CHANNELS))
    gaps = [name for name in PROFILE_CHANNELS if name not in present]
    thermocouples = run.get("load_thermocouples", 0)
    if isinstance(thermocouples, bool) or not isinstance(thermocouples, int):
        raise ValueError(
            "load_thermocouples must be an integer, got %r" % (thermocouples,)
        )
    if thermocouples < 0:
        raise ValueError("load_thermocouples cannot be negative")
    findings = []
    for name in gaps:
        findings.append("the furnace run record carries no %s" % name)
    if thermocouples < MINIMUM_LOAD_THERMOCOUPLES:
        findings.append(
            "the load carried %d thermocouple(s) against a minimum of %d; a "
            "cold corner of the load cannot be distinguished from the control "
            "channel" % (thermocouples, MINIMUM_LOAD_THERMOCOUPLES)
        )
    return {
        "run_id": run["run_id"],
        "missing_channels": gaps,
        "load_thermocouples": thermocouples,
        "instrumented": thermocouples >= MINIMUM_LOAD_THERMOCOUPLES,
        "complete": not findings,
        "findings": findings,
    }


def assess_brazement_record(case):
    """Whether the brazement record closes on its own evidence."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    brazement_id = _require_identifier("brazement_id", case.get("brazement_id"))
    process = _require_choice("process", case.get("process"), PROCESSES)
    uses_flux = case.get("uses_flux")
    if not isinstance(uses_flux, bool):
        raise ValueError("uses_flux must be True or False, got %r" % (uses_flux,))
    braze_date = _require_date("braze_date", case.get("braze_date"))
    gaps = missing_record_fields(process, uses_flux, case.get("fields_present", []))

    findings = []
    if gaps:
        findings.append(
            "%d required record field(s) are not on the brazement record: %s"
            % (len(gaps), ", ".join(gaps))
        )

    operator = operator_currency(
        case.get("operator_certificate_expiry"),
        case.get("operator_last_process_run"),
        braze_date,
        case.get("continuity_days"),
    )
    if operator["status"] == OPERATOR_EXPIRED:
        findings.append(
            "the operator's qualification expired %d day(s) before the braze"
            % abs(operator["days_to_certificate_expiry"])
        )
    elif operator["status"] == OPERATOR_LAPSED:
        findings.append(
            "the operator had not run the process for %d day(s) against a %d "
            "day continuity interval"
            % (operator["days_since_last_run"], operator["continuity_limit_days"])
        )

    furnace = None
    if process in _FURNACE_PROCESSES:
        run = case.get("furnace_run")
        if run is None:
            findings.append(
                "a furnace process was recorded with no furnace run data at all"
            )
        else:
            furnace = furnace_data_gaps(run)
            findings.extend(furnace["findings"])

    complete = not findings
    return {
        "brazement_id": brazement_id,
        "process": process,
        "braze_date": braze_date,
        "required_fields": required_record_fields(process, uses_flux),
        "missing_fields": gaps,
        "operator": operator,
        "furnace_run": furnace,
        "verdict": VERDICT_COMPLETE if complete else VERDICT_INCOMPLETE,
        "record_closes": complete,
        "findings": findings,
    }
