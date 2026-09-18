#!/usr/bin/env python3
"""Deciding whether a dissipative switch failure is still protected once the
two earlier provisions have both been ruled out.

Anchor: ECSS-E-ST-20-20C clause 5.2.14.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause adds a third protection to a dissipative switch, and it adds it
conditionally: it is owed only where neither of the two earlier provisions
can apply. So the assessment is ordered, not a checklist:

    provision one    the dissipative element carries the stuck-on case on
                     its own derated continuous rating. Where it does, the
                     failure is survived by the part itself and nothing
                     further is owed
    provision two    an off-command path reaches the switch without passing
                     through anything the failure took with it. Where one
                     does, the failure is commanded away
    backup           only where neither holds. It has to cover the mode in
                     question, stand clear of the elements that failed, and
                     act before the element runs up to its temperature limit

A backup that shares a part with the switch it protects is not a backup, it
is the same failure counted twice. A backup that acts after the dissipative
element has passed its limit did not protect it either; it recorded the
event.

A provision nobody tested is not a provision that failed. It leaves the
ordering undecided, so it is reported ahead of everything else.

The ratings, deratings and time margins below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FAIL_STUCK_CONDUCTING = "stuck-conducting"
FAIL_STUCK_OPEN = "stuck-open"
FAIL_LOSS_OF_MODULATION = "loss-of-modulation"
FAIL_OSCILLATING_DRIVE = "oscillating-drive"

DISSIPATIVE_FAILURE_MODES = (
    FAIL_STUCK_CONDUCTING,
    FAIL_STUCK_OPEN,
    FAIL_LOSS_OF_MODULATION,
    FAIL_OSCILLATING_DRIVE,
)

# Modes that leave the element dissipating, so a thermal run-up bounds the
# time any backup has to act in. A stuck-open switch stops dissipating; its
# hazard is the lost dissipation function, and only the policy ceiling
# bounds the backup there.
DISSIPATING_MODES = (
    FAIL_STUCK_CONDUCTING,
    FAIL_LOSS_OF_MODULATION,
    FAIL_OSCILLATING_DRIVE,
)

PROVISION_CONTINUOUS_RATING = "continuous-dissipation-rating"
PROVISION_INDEPENDENT_OFF_COMMAND = "independent-off-command"

EARLIER_PROVISIONS = (
    PROVISION_CONTINUOUS_RATING,
    PROVISION_INDEPENDENT_OFF_COMMAND,
)

BACKUP_THERMAL_CUTOUT = "backup-thermal-cutout"
BACKUP_SERIES_FUSE = "backup-series-fuse"
BACKUP_UPSTREAM_LCL = "backup-upstream-lcl"
BACKUP_REDUNDANT_SHUNT = "backup-redundant-shunt-switch"
BACKUP_DRIVE_WATCHDOG = "backup-drive-watchdog"

BACKUP_DEVICES = (
    BACKUP_THERMAL_CUTOUT,
    BACKUP_SERIES_FUSE,
    BACKUP_UPSTREAM_LCL,
    BACKUP_REDUNDANT_SHUNT,
    BACKUP_DRIVE_WATCHDOG,
)

BACKUP_COVERAGE = {
    BACKUP_THERMAL_CUTOUT: (FAIL_STUCK_CONDUCTING, FAIL_LOSS_OF_MODULATION),
    BACKUP_SERIES_FUSE: (FAIL_STUCK_CONDUCTING,),
    BACKUP_UPSTREAM_LCL: (
        FAIL_STUCK_CONDUCTING,
        FAIL_LOSS_OF_MODULATION,
        FAIL_OSCILLATING_DRIVE,
    ),
    BACKUP_REDUNDANT_SHUNT: (FAIL_STUCK_OPEN,),
    BACKUP_DRIVE_WATCHDOG: (FAIL_LOSS_OF_MODULATION, FAIL_OSCILLATING_DRIVE),
}

BACKUP_NOT_EVALUATED = "dissipative-backup-not-evaluated"
BACKUP_NOT_REQUIRED = "earlier-provision-applies"
BACKUP_MISSING = "dissipative-backup-missing"
BACKUP_COVERAGE_GAP = "dissipative-backup-coverage-gap"
BACKUP_NOT_INDEPENDENT = "dissipative-backup-not-independent"
BACKUP_TOO_SLOW = "dissipative-backup-acts-too-late"
BACKUP_ADEQUATE = "dissipative-backup-adequate"

CHANNEL_VERDICTS = (
    BACKUP_NOT_EVALUATED,
    BACKUP_NOT_REQUIRED,
    BACKUP_MISSING,
    BACKUP_COVERAGE_GAP,
    BACKUP_NOT_INDEPENDENT,
    BACKUP_TOO_SLOW,
    BACKUP_ADEQUATE,
)

DEFAULT_BACKUP_POLICY = {
    "dissipation_derating": 0.80,
    "min_thermal_time_margin": 2.0,
    "max_backup_action_time_s": 60.0,
}

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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, floor):
    """value >= floor, absorbing floating-point representation error."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_element_names(name, value):
    """A list of part identifiers, deduplicated and refused when malformed."""
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (name, value))
    named = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "%s entries must be non-empty strings, got %r" % (name, item)
            )
        named.append(item.strip())
    if len(set(named)) != len(named):
        raise ValueError("%s names the same element twice: %r" % (name, value))
    return tuple(named)


def validate_backup_policy(policy):
    """Check a backup policy is usable before any provision is tested."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    derating = _require_positive(
        "dissipation_derating", policy.get("dissipation_derating")
    )
    if not _at_most(derating, 1.0):
        raise ValueError(
            "dissipation_derating %g exceeds one, so the policy would credit "
            "the element with more than its own rating" % (derating,)
        )
    margin = _require_positive(
        "min_thermal_time_margin", policy.get("min_thermal_time_margin")
    )
    if not _at_least(margin, 1.0):
        raise ValueError(
            "min_thermal_time_margin %g is below one, so the policy accepts a "
            "backup acting after the temperature limit" % (margin,)
        )
    _require_positive(
        "max_backup_action_time_s", policy.get("max_backup_action_time_s")
    )
    return policy


def categorize_failure_mode(mode):
    """Name a dissipative switch failure mode, refusing anything unknown."""
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("failure mode must be a non-empty string, got %r" % (mode,))
    name = mode.strip()
    if name not in DISSIPATIVE_FAILURE_MODES:
        raise ValueError(
            "unrecognised dissipative failure mode %r; known modes are %s"
            % (name, ", ".join(DISSIPATIVE_FAILURE_MODES))
        )
    return name


def categorize_backup_device(device):
    """Name a backup protection device, refusing anything unknown."""
    if not isinstance(device, str) or not device.strip():
        raise ValueError("backup device must be a non-empty string, got %r" % (device,))
    name = device.strip()
    if name not in BACKUP_DEVICES:
        raise ValueError(
            "unrecognised backup device %r; known devices are %s"
            % (name, ", ".join(BACKUP_DEVICES))
        )
    return name


def derated_dissipation_capability_w(rating_w, derating):
    """What the element may be credited with continuously, after derating."""
    rating = _require_positive("element_continuous_rating_w", rating_w)
    factor = _require_positive("dissipation_derating", derating)
    if not _at_most(factor, 1.0):
        raise ValueError("dissipation_derating %g exceeds one" % (factor,))
    return rating * factor


def time_to_thermal_limit_s(
    dissipation_w, thermal_capacity_j_per_k, initial_temperature_c, limit_temperature_c
):
    """How long the element takes to run from where it sits to its limit."""
    power = _require_positive("dissipation_w", dissipation_w)
    capacity = _require_positive(
        "thermal_capacity_j_per_k", thermal_capacity_j_per_k
    )
    start = _require_number("initial_temperature_c", initial_temperature_c)
    limit = _require_number("limit_temperature_c", limit_temperature_c)
    if not limit > start:
        raise ValueError(
            "limit_temperature_c %g is not above initial_temperature_c %g, so "
            "the element is already past its limit" % (limit, start)
        )
    return capacity * (limit - start) / power


def continuous_rating_provision_applies(channel, policy=DEFAULT_BACKUP_POLICY):
    """Does the element carry the stuck-on case on its own derated rating."""
    validate_backup_policy(policy)
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    worst_case = _require_non_negative(
        "worst_case_dissipation_w", channel.get("worst_case_dissipation_w")
    )
    capability = derated_dissipation_capability_w(
        channel.get("element_continuous_rating_w"),
        policy.get("dissipation_derating"),
    )
    return _at_most(worst_case, capability)


def independent_off_command_paths(channel):
    """Off-command paths that share no element with the failed switch."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    switch_elements = set(
        _require_element_names("switch_elements", channel.get("switch_elements"))
    )
    paths = channel.get("off_command_paths")
    if not isinstance(paths, (list, tuple)):
        raise ValueError("off_command_paths must be a sequence, got %r" % (paths,))
    independent = []
    seen = set()
    for path in paths:
        if not isinstance(path, dict):
            raise ValueError("off-command path must be a mapping, got %r" % (path,))
        path_id = path.get("id")
        if not isinstance(path_id, str) or not path_id.strip():
            raise ValueError("off-command path needs a non-empty id, got %r" % (path,))
        path_id = path_id.strip()
        if path_id in seen:
            raise ValueError("off-command path %r declared twice" % (path_id,))
        seen.add(path_id)
        shared = set(
            _require_element_names("shared_elements", path.get("shared_elements"))
        )
        if not shared & switch_elements:
            independent.append(path_id)
    return tuple(independent)


def independent_off_command_provision_applies(channel):
    """Is at least one off-command path clear of the failure."""
    return bool(independent_off_command_paths(channel))


def backup_covers_mode(device, mode):
    """Does this backup device answer this failure mode at all."""
    name = categorize_backup_device(device)
    return categorize_failure_mode(mode) in BACKUP_COVERAGE[name]


def backup_shared_elements(channel):
    """Parts the declared backup has in common with the switch it protects."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    backup = channel.get("backup")
    if not isinstance(backup, dict):
        raise ValueError("backup must be a mapping, got %r" % (backup,))
    switch_elements = set(
        _require_element_names("switch_elements", channel.get("switch_elements"))
    )
    shared = set(
        _require_element_names("shared_elements", backup.get("shared_elements"))
    )
    return tuple(sorted(shared & switch_elements))


def assess_backup_protection(channel, policy=DEFAULT_BACKUP_POLICY):
    """Full clause 5.2.14.3.1 judgement of one dissipative switch channel."""
    validate_backup_policy(policy)
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))

    mode = categorize_failure_mode(channel.get("failure_mode"))
    findings = []

    untested = []
    if (
        channel.get("worst_case_dissipation_w") is None
        or channel.get("element_continuous_rating_w") is None
    ):
        untested.append(PROVISION_CONTINUOUS_RATING)
    if channel.get("off_command_paths") is None:
        untested.append(PROVISION_INDEPENDENT_OFF_COMMAND)

    result = {
        "failure_mode": mode,
        "untested_provisions": untested,
        "applicable_provisions": [],
        "backup_required": None,
        "backup_device": None,
        "covering": None,
        "shared_elements": (),
        "time_to_limit_s": None,
        "action_time_s": None,
        "findings": findings,
    }

    if untested:
        for provision in untested:
            findings.append(
                "%s was never tested, so whether a backup is owed at all is "
                "undecided rather than answered" % (provision,)
            )
        result["verdict"] = BACKUP_NOT_EVALUATED
        return result

    applicable = []
    if continuous_rating_provision_applies(channel, policy):
        applicable.append(PROVISION_CONTINUOUS_RATING)
    if independent_off_command_provision_applies(channel):
        applicable.append(PROVISION_INDEPENDENT_OFF_COMMAND)
    result["applicable_provisions"] = applicable

    if applicable:
        result["backup_required"] = False
        result["verdict"] = BACKUP_NOT_REQUIRED
        return result

    result["backup_required"] = True
    backup = channel.get("backup")
    if backup is None:
        findings.append(
            "neither earlier provision applies to %s and no backup protection "
            "is declared, so the failure is unprotected" % (mode,)
        )
        result["verdict"] = BACKUP_MISSING
        return result
    if not isinstance(backup, dict):
        raise ValueError("backup must be a mapping, got %r" % (backup,))

    device = categorize_backup_device(backup.get("device"))
    result["backup_device"] = device
    covering = backup_covers_mode(device, mode)
    result["covering"] = covering

    if not covering:
        findings.append(
            "%s does not answer %s, so the backup is present on the schematic "
            "and absent from the argument" % (device, mode)
        )
        result["verdict"] = BACKUP_COVERAGE_GAP
        return result

    shared = backup_shared_elements(channel)
    result["shared_elements"] = shared
    if shared:
        findings.append(
            "%s shares %s with the switch it protects, so one failure takes "
            "both" % (device, ", ".join(shared))
        )
        result["verdict"] = BACKUP_NOT_INDEPENDENT
        return result

    action_time = _require_positive("action_time_s", backup.get("action_time_s"))
    result["action_time_s"] = action_time

    ceiling = float(policy["max_backup_action_time_s"])
    if not _at_most(action_time, ceiling):
        findings.append(
            "%s acts in %.4f s against the %.4f s the policy allows any backup"
            % (device, action_time, ceiling)
        )
        result["verdict"] = BACKUP_TOO_SLOW
        return result

    if mode in DISSIPATING_MODES:
        time_to_limit = time_to_thermal_limit_s(
            channel.get("worst_case_dissipation_w"),
            channel.get("thermal_capacity_j_per_k"),
            channel.get("initial_temperature_c"),
            channel.get("limit_temperature_c"),
        )
        result["time_to_limit_s"] = time_to_limit
        margin = float(policy["min_thermal_time_margin"])
        if not _at_most(action_time * margin, time_to_limit):
            findings.append(
                "%s acts in %.4f s and the element reaches its limit in %.4f "
                "s, which does not hold the %.2f time margin"
                % (device, action_time, time_to_limit, margin)
            )
            result["verdict"] = BACKUP_TOO_SLOW
            return result

    result["verdict"] = BACKUP_ADEQUATE
    return result
