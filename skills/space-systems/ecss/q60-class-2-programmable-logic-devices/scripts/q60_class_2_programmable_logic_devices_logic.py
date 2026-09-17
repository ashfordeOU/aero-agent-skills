#!/usr/bin/env python3
"""Development, reuse and maintenance of a class 2 programmable logic device.

Anchor: ECSS-Q-ST-60C clause 5.6.4 (development, reuse and maintenance rules
for programmable logic devices used in class 2 equipment). Paraphrased into an
implementable procedure; no standard text is reproduced.

A programmable logic device is bought like a component and behaves like a
design. The component half is covered by the general procurement rules. The
design half is not: it has to be developed against something, reused against
something, and kept correct for as long as the equipment flies. Clause 5.6.4
is about that half, and for class 2 the weight sits on maintenance — what has
to be in the archive for the design to be touchable again, and what the
configuration technology obliges the project to keep doing once the unit has
shipped.

Procedure implemented here
--------------------------
1. Validate the case: configuration technology, declared design baseline, the
   archive the project holds, the toolchain record behind it, and the mission
   the device is being flown on.
2. Take the archive gaps against what the declared baseline demands, and the
   share of the required archive actually held.
3. Decide whether the toolchain behind the archive can still be stood up.
4. Attach the in-service duties the configuration technology carries, plus the
   duty that follows from permitting reconfiguration after delivery.
5. Turn those duties into a review count over the mission in integer
   arithmetic, and route the design: full development, delta verification,
   reviewed reuse, or nothing at all while the archive is short.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "CONFIGURATION_TECHNOLOGIES",
    "DESIGN_BASELINES",
    "ARCHIVE_ARTEFACTS",
    "REQUIRED_ARTEFACTS_BY_BASELINE",
    "IN_SERVICE_DUTIES",
    "DUTY_REVIEW_INTERVAL_MONTHS",
    "FIELD_RECONFIGURATION_DUTY",
    "REPROGRAMMABLE_TECHNOLOGIES",
    "DEFAULT_MAINTENANCE_POLICY",
    "FULL_DEVELOPMENT",
    "DELTA_VERIFICATION",
    "REVIEWED_REUSE",
    "ARCHIVE_INCOMPLETE",
    "TOOLCHAIN_NOT_REPRODUCIBLE",
    "FIELD_RECONFIGURATION_ON_ONE_TIME_DEVICE",
    "validate_maintenance_policy",
    "required_artefacts",
    "validate_archive",
    "archive_gaps",
    "archive_completeness",
    "validate_toolchain_record",
    "toolchain_is_reproducible",
    "in_service_duties",
    "duty_review_count",
    "maintenance_schedule",
    "route_pld_design",
    "assess_pld_case",
]

CONFIGURATION_TECHNOLOGIES = (
    "antifuse-one-time-programmable",
    "flash-reprogrammable",
    "eeprom-reprogrammable",
    "sram-volatile-configuration",
)

# Technologies whose configuration can be rewritten after delivery.
REPROGRAMMABLE_TECHNOLOGIES = (
    "flash-reprogrammable",
    "eeprom-reprogrammable",
    "sram-volatile-configuration",
)

DESIGN_BASELINES = ("new-design", "modified-reuse", "unchanged-reuse")

ARCHIVE_ARTEFACTS = (
    "design-source-archive",
    "synthesis-and-place-route-constraints",
    "post-route-netlist",
    "programming-image-checksum",
    "functional-verification-testbench",
    "toolchain-version-record",
    "device-programming-record",
    "design-change-log",
)

# What each declared baseline has to hold before it can be maintained.
REQUIRED_ARTEFACTS_BY_BASELINE = {
    "new-design": ARCHIVE_ARTEFACTS,
    "modified-reuse": ARCHIVE_ARTEFACTS,
    "unchanged-reuse": (
        "design-source-archive",
        "post-route-netlist",
        "programming-image-checksum",
        "functional-verification-testbench",
        "toolchain-version-record",
        "device-programming-record",
    ),
}

# What the configuration technology obliges the project to keep doing.
IN_SERVICE_DUTIES = {
    "antifuse-one-time-programmable": (
        "programming-yield-and-verify-record",
        "no-field-reconfiguration-control",
    ),
    "flash-reprogrammable": (
        "configuration-write-protection-control",
        "reprogramming-configuration-control",
        "programming-cycle-count-tracking",
    ),
    "eeprom-reprogrammable": (
        "configuration-write-protection-control",
        "reprogramming-configuration-control",
        "configuration-retention-margin-review",
    ),
    "sram-volatile-configuration": (
        "configuration-memory-integrity-monitoring",
        "configuration-reload-or-scrub-provision",
        "power-up-configuration-timing-control",
    ),
}

FIELD_RECONFIGURATION_DUTY = "in-flight-reconfiguration-rehearsal-and-rollback"

# How often each duty comes round, in whole months.
DUTY_REVIEW_INTERVAL_MONTHS = {
    "programming-yield-and-verify-record": 24,
    "no-field-reconfiguration-control": 24,
    "configuration-write-protection-control": 12,
    "reprogramming-configuration-control": 12,
    "programming-cycle-count-tracking": 12,
    "configuration-retention-margin-review": 18,
    "configuration-memory-integrity-monitoring": 6,
    "configuration-reload-or-scrub-provision": 6,
    "power-up-configuration-timing-control": 12,
    FIELD_RECONFIGURATION_DUTY: 6,
}

DEFAULT_MAINTENANCE_POLICY = {
    # Class 2 accepts a toolchain supported for at least this long past the
    # month the archive was closed.
    "toolchain_support_margin_months": 24,
}

FULL_DEVELOPMENT = "pld-full-development-flow"
DELTA_VERIFICATION = "pld-delta-verification-flow"
REVIEWED_REUSE = "pld-reviewed-reuse-flow"
ARCHIVE_INCOMPLETE = "pld-maintenance-archive-incomplete"
TOOLCHAIN_NOT_REPRODUCIBLE = "pld-toolchain-not-reproducible"
FIELD_RECONFIGURATION_ON_ONE_TIME_DEVICE = (
    "field-reconfiguration-declared-on-one-time-programmable-device"
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def validate_maintenance_policy(policy=None):
    """Validate the maintenance policy, returning the default when omitted."""
    if policy is None:
        return dict(DEFAULT_MAINTENANCE_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (type(policy).__name__,))
    merged = dict(DEFAULT_MAINTENANCE_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_MAINTENANCE_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = value
    margin = merged["toolchain_support_margin_months"]
    if not _is_int(margin) or margin < 0:
        raise ValueError(
            "toolchain_support_margin_months must be a non-negative integer, got %r"
            % (margin,)
        )
    return merged


def required_artefacts(baseline):
    """Archive artefacts a declared design baseline has to hold."""
    if baseline not in REQUIRED_ARTEFACTS_BY_BASELINE:
        raise ValueError(
            "unknown design baseline %r (known: %s)"
            % (baseline, ", ".join(DESIGN_BASELINES))
        )
    return REQUIRED_ARTEFACTS_BY_BASELINE[baseline]


def validate_archive(archive):
    """Validate the archive listing and reject an artefact nobody defined."""
    if not isinstance(archive, (list, tuple, set, frozenset)):
        raise ValueError(
            "archive must be a list, tuple or set, got %r" % (type(archive).__name__,)
        )
    held = []
    for item in archive:
        _require_text("archive entry", item)
        if item not in ARCHIVE_ARTEFACTS:
            raise ValueError(
                "unknown archive artefact %r (known: %s)"
                % (item, ", ".join(ARCHIVE_ARTEFACTS))
            )
        if item in held:
            raise ValueError("duplicate archive artefact %r" % (item,))
        held.append(item)
    return tuple(held)


def archive_gaps(baseline, archive):
    """Required artefacts the archive does not hold, in declaration order."""
    held = set(validate_archive(archive))
    return tuple(item for item in required_artefacts(baseline) if item not in held)


def archive_completeness(baseline, archive):
    """Share of the required archive the project actually holds."""
    required = required_artefacts(baseline)
    gaps = archive_gaps(baseline, archive)
    return (len(required) - len(gaps)) / len(required)


def validate_toolchain_record(record):
    """Validate the toolchain record standing behind the archived design."""
    if not isinstance(record, dict):
        raise ValueError(
            "toolchain record must be a mapping, got %r" % (type(record).__name__,)
        )
    _require_text("toolchain name", record.get("tool_name"))
    _require_text("toolchain version", record.get("tool_version"))
    installer = record.get("installer_archived")
    if not isinstance(installer, bool):
        raise ValueError(
            "installer_archived must be a boolean, got %r" % (installer,)
        )
    licence = record.get("licence_available")
    if not isinstance(licence, bool):
        raise ValueError("licence_available must be a boolean, got %r" % (licence,))
    supported = record.get("supported_for_months")
    if not _is_int(supported) or supported < 0:
        raise ValueError(
            "supported_for_months must be a non-negative integer, got %r" % (supported,)
        )
    return {
        "tool_name": record["tool_name"],
        "tool_version": record["tool_version"],
        "installer_archived": installer,
        "licence_available": licence,
        "supported_for_months": supported,
    }


def toolchain_is_reproducible(record, policy=None):
    """True when the archived toolchain can still be stood up and run."""
    merged = validate_maintenance_policy(policy)
    validated = validate_toolchain_record(record)
    if not validated["installer_archived"] or not validated["licence_available"]:
        return False
    return (
        validated["supported_for_months"] >= merged["toolchain_support_margin_months"]
    )


def in_service_duties(technology, field_reconfiguration_permitted=False):
    """Duties the configuration technology carries once the unit has shipped."""
    if technology not in IN_SERVICE_DUTIES:
        raise ValueError(
            "unknown configuration technology %r (known: %s)"
            % (technology, ", ".join(CONFIGURATION_TECHNOLOGIES))
        )
    if not isinstance(field_reconfiguration_permitted, bool):
        raise ValueError(
            "field_reconfiguration_permitted must be a boolean, got %r"
            % (field_reconfiguration_permitted,)
        )
    duties = list(IN_SERVICE_DUTIES[technology])
    if field_reconfiguration_permitted and technology in REPROGRAMMABLE_TECHNOLOGIES:
        duties.append(FIELD_RECONFIGURATION_DUTY)
    return tuple(duties)


def duty_review_count(duty, mission_duration_months):
    """How many times a duty comes round over a mission, rounded up."""
    if duty not in DUTY_REVIEW_INTERVAL_MONTHS:
        raise ValueError("unknown in-service duty %r" % (duty,))
    if not _is_int(mission_duration_months) or mission_duration_months < 1:
        raise ValueError(
            "mission_duration_months must be an integer of at least one, got %r"
            % (mission_duration_months,)
        )
    interval = DUTY_REVIEW_INTERVAL_MONTHS[duty]
    return -(-mission_duration_months // interval)


def maintenance_schedule(technology, mission_duration_months,
                         field_reconfiguration_permitted=False):
    """Per-duty interval and review count for a mission of a given length."""
    duties = in_service_duties(technology, field_reconfiguration_permitted)
    schedule = []
    for duty in duties:
        schedule.append(
            {
                "duty": duty,
                "interval_months": DUTY_REVIEW_INTERVAL_MONTHS[duty],
                "reviews": duty_review_count(duty, mission_duration_months),
            }
        )
    return tuple(schedule)


def route_pld_design(baseline, archive, toolchain, policy=None):
    """Route the design from its baseline, its archive and its toolchain."""
    gaps = archive_gaps(baseline, archive)
    reproducible = toolchain_is_reproducible(toolchain, policy)
    findings = []
    if not reproducible:
        findings.append(TOOLCHAIN_NOT_REPRODUCIBLE)
    if gaps:
        return {"route": ARCHIVE_INCOMPLETE, "gaps": gaps, "findings": tuple(findings)}
    if baseline == "new-design":
        route = FULL_DEVELOPMENT
    elif baseline == "modified-reuse":
        route = DELTA_VERIFICATION
    elif reproducible:
        route = REVIEWED_REUSE
    else:
        route = DELTA_VERIFICATION
    return {"route": route, "gaps": (), "findings": tuple(findings)}


def assess_pld_case(case, policy=None):
    """Route a class 2 programmable logic device and schedule its maintenance."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    for key in ("technology", "baseline", "archive", "toolchain",
                "mission_duration_months"):
        if key not in case:
            raise ValueError("case has no %r" % (key,))
    technology = case["technology"]
    if technology not in CONFIGURATION_TECHNOLOGIES:
        raise ValueError(
            "technology must be one of %s, got %r"
            % (", ".join(CONFIGURATION_TECHNOLOGIES), technology)
        )
    baseline = case["baseline"]
    permitted = case.get("field_reconfiguration_permitted", False)
    if not isinstance(permitted, bool):
        raise ValueError(
            "field_reconfiguration_permitted must be a boolean, got %r" % (permitted,)
        )
    routing = route_pld_design(baseline, case["archive"], case["toolchain"], policy)
    findings = list(routing["findings"])
    if permitted and technology not in REPROGRAMMABLE_TECHNOLOGIES:
        findings.append(FIELD_RECONFIGURATION_ON_ONE_TIME_DEVICE)
    schedule = maintenance_schedule(
        technology, case["mission_duration_months"], permitted
    )
    return {
        "technology": technology,
        "baseline": baseline,
        "route": routing["route"],
        "archive_gaps": routing["gaps"],
        "archive_completeness": archive_completeness(baseline, case["archive"]),
        "toolchain_reproducible": toolchain_is_reproducible(case["toolchain"], policy),
        "in_service_duties": tuple(entry["duty"] for entry in schedule),
        "maintenance_schedule": schedule,
        "total_reviews": sum(entry["reviews"] for entry in schedule),
        "findings": tuple(findings),
        "maintainable": routing["route"] != ARCHIVE_INCOMPLETE and not findings,
    }
