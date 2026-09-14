#!/usr/bin/env python3
"""Putting the whole protection diode population into the ambient pressure
chamber, then judging the contact adherence that follows.

Anchor: ECSS-E-ST-20-08C clause 9.6.6.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause loads all of the protection diodes into the chamber, at
ambient pressure, for the declared dwell, and only then pulls their
contacts. Each of those words does work:

    all of them       the run is a population run, not a sample run.
                      Devices left on the bench are not covered by the
                      result, and a partial load is reported as partial
                      rather than averaged across what did go in
    ambient pressure  the conditioning happens in the band the clause
                      names. A chamber that drifted out of it ran a
                      different conditioning, and every device inside
                      reached an unknown state
    the declared dwell    the dwell is what turns a tray of devices into
                      conditioned devices. Short dwell, no conditioning,
                      and the pull that follows describes an as-received
                      joint
    then pulled       adherence is judged after the chamber, at up to
                      three sites per device: the anode terminal, the
                      cathode terminal and the die attach beneath them

Tray geometry is part of the conditioning rather than housekeeping.
Packages sitting edge to edge shadow each other from the circulating
air, so the tray carries a packing cap and each device carries a
terminal clearance; a tray filled past the cap has conditioned its outer
ring and warmed everything inside it.

A device is sentenced by its weakest site, because a string does not
care which of its joints let go, and a single detached site fails the
lot outright rather than being diluted into a reject fraction: detachment
is a different event from a low reading.

The bands, caps, floors and fractions below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANODE_TERMINAL = "anode-terminal"
CATHODE_TERMINAL = "cathode-terminal"
DIE_ATTACH = "die-attach"

ATTACHMENT_SITES = (ANODE_TERMINAL, CATHODE_TERMINAL, DIE_ATTACH)

ADHERENT = "adherent"
BELOW_LIMIT = "below-limit"
DETACHED = "detached"

ADHERENCE_CATEGORIES = (ADHERENT, BELOW_LIMIT, DETACHED)

LOT_NOT_EVALUATED = "diode-adherence-lot-not-evaluated"
CONDITIONING_DEFICIENT = "diode-chamber-conditioning-deficient"
LOT_FAILED = "diode-adherence-lot-failed"
LOT_PASSED = "diode-adherence-lot-passed"

RUN_VERDICTS = (
    LOT_NOT_EVALUATED,
    CONDITIONING_DEFICIENT,
    LOT_FAILED,
    LOT_PASSED,
)

DEFAULT_DIODE_LOADING_POLICY = {
    "min_chamber_pressure_kpa": 86.0,
    "max_chamber_pressure_kpa": 106.0,
    "max_tray_packing_fraction": 0.70,
    "min_terminal_clearance_mm": 2.0,
    "min_soak_dwell_h": 24.0,
    "min_pull_load_n": 2.0,
    "detached_load_n": 0.2,
    "max_reject_fraction": 0.05,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_diode_loading_policy(policy):
    """Check a diode chamber loading and acceptance policy is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    low = _require_positive(
        "min_chamber_pressure_kpa", policy.get("min_chamber_pressure_kpa")
    )
    high = _require_positive(
        "max_chamber_pressure_kpa", policy.get("max_chamber_pressure_kpa")
    )
    if not low < high:
        raise ValueError(
            "min_chamber_pressure_kpa %g must sit below max_chamber_pressure_kpa "
            "%g" % (low, high)
        )
    _require_fraction(
        "max_tray_packing_fraction", policy.get("max_tray_packing_fraction")
    )
    _require_positive(
        "min_terminal_clearance_mm", policy.get("min_terminal_clearance_mm")
    )
    _require_positive("min_soak_dwell_h", policy.get("min_soak_dwell_h"))
    pull = _require_positive("min_pull_load_n", policy.get("min_pull_load_n"))
    detached = _require_positive("detached_load_n", policy.get("detached_load_n"))
    if detached >= pull:
        raise ValueError(
            "detached_load_n %g must sit below the min_pull_load_n %g it is a "
            "detachment threshold under" % (detached, pull)
        )
    _require_fraction("max_reject_fraction", policy.get("max_reject_fraction"))
    return policy


def load_completeness(loaded_devices, population_devices):
    """Share of the protection diode population that went into the chamber."""
    loaded = _require_count("loaded_devices", loaded_devices)
    population = _require_count("population_devices", population_devices)
    if loaded > population:
        raise ValueError(
            "loaded_devices %d cannot exceed the %d devices in the population"
            % (loaded, population)
        )
    return loaded / population


def tray_packing_fraction(tray):
    """Share of the tray footprint the loaded packages cover."""
    if not isinstance(tray, dict):
        raise ValueError("tray must be a mapping, got %r" % (tray,))
    area = _require_positive("tray tray_area_mm2", tray.get("tray_area_mm2"))
    footprint = _require_positive(
        "tray package_footprint_mm2", tray.get("package_footprint_mm2")
    )
    count = _require_count("tray device_count", tray.get("device_count"))
    occupied = footprint * count
    if occupied > area and not math.isclose(
        occupied, area, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "the load covers %g mm2 of a %g mm2 tray, which does not fit"
            % (occupied, area)
        )
    return occupied / area


def chamber_pressure_in_band(
    chamber_pressure_kpa, policy=DEFAULT_DIODE_LOADING_POLICY
):
    """True when the chamber sits inside the declared ambient band."""
    validate_diode_loading_policy(policy)
    pressure = _require_positive("chamber_pressure_kpa", chamber_pressure_kpa)
    return _at_least(
        pressure, float(policy["min_chamber_pressure_kpa"])
    ) and _at_most(pressure, float(policy["max_chamber_pressure_kpa"]))


def categorize_pull_result(load_n, policy=DEFAULT_DIODE_LOADING_POLICY):
    """Group one site reading as adherent, below limit or detached."""
    validate_diode_loading_policy(policy)
    load = _require_non_negative("load_n", load_n)
    if _at_least(load, float(policy["min_pull_load_n"])):
        return ADHERENT
    if _at_most(load, float(policy["detached_load_n"])):
        return DETACHED
    return BELOW_LIMIT


def sentence_device(device, policy=DEFAULT_DIODE_LOADING_POLICY):
    """Sentence one device by the weakest of the sites reported for it."""
    validate_diode_loading_policy(policy)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    sites = device.get("sites")
    if not isinstance(sites, dict) or not sites:
        raise ValueError(
            "device is missing a non-empty sites mapping, got %r" % (sites,)
        )
    per_site = {}
    for name, load in sites.items():
        if name not in ATTACHMENT_SITES:
            raise ValueError(
                "unrecognised attachment site %r; known sites are %s"
                % (name, ", ".join(ATTACHMENT_SITES))
            )
        per_site[name] = categorize_pull_result(load, policy)
    if DETACHED in per_site.values():
        worst = DETACHED
    elif BELOW_LIMIT in per_site.values():
        worst = BELOW_LIMIT
    else:
        worst = ADHERENT
    return {
        "id": device.get("id"),
        "site_categories": per_site,
        "category": worst,
    }


def assess_diode_adherence_run(run, policy=DEFAULT_DIODE_LOADING_POLICY):
    """Full clause 9.6.6.2.2 judgement for one diode adherence run."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))
    validate_diode_loading_policy(policy)
    population = run.get("population")
    if not isinstance(population, dict):
        raise ValueError("run is missing a population block")
    chamber = run.get("chamber")
    if not isinstance(chamber, dict):
        raise ValueError("run is missing a chamber block")
    devices = run.get("devices")
    if not isinstance(devices, list) or not devices:
        raise ValueError("run is missing a non-empty devices list")

    population_count = _require_count(
        "population diode_count", population.get("diode_count")
    )
    loaded = _require_count(
        "chamber loaded_diode_count", chamber.get("loaded_diode_count")
    )
    pressure = _require_positive(
        "chamber pressure_kpa", chamber.get("pressure_kpa")
    )
    dwell = _require_positive("chamber soak_dwell_h", chamber.get("soak_dwell_h"))
    clearance = _require_positive(
        "chamber terminal_clearance_mm", chamber.get("terminal_clearance_mm")
    )
    completeness = load_completeness(loaded, population_count)
    packing = tray_packing_fraction(
        {
            "tray_area_mm2": chamber.get("tray_area_mm2"),
            "package_footprint_mm2": chamber.get("package_footprint_mm2"),
            "device_count": loaded,
        }
    )

    sentences = [sentence_device(device, policy) for device in devices]
    detached = [s for s in sentences if s["category"] == DETACHED]
    below = [s for s in sentences if s["category"] == BELOW_LIMIT]
    reject_fraction = (len(detached) + len(below)) / len(sentences)

    findings = []
    result = {
        "population_devices": population_count,
        "loaded_devices": loaded,
        "load_completeness": completeness,
        "tray_packing_fraction": packing,
        "pressure_in_band": chamber_pressure_in_band(pressure, policy),
        "sentences": sentences,
        "detached_devices": len(detached),
        "below_limit_devices": len(below),
        "reject_fraction": reject_fraction,
        "findings": findings,
    }

    partial = loaded < population_count
    if partial:
        findings.append(
            "the chamber took %d of the %d protection diodes, so the devices "
            "left out are not covered by this result"
            % (loaded, population_count)
        )

    conditioning = []
    if not result["pressure_in_band"]:
        conditioning.append(
            "the chamber held %.2f kPa, outside the %.2f to %.2f kPa ambient "
            "band this conditioning is run in"
            % (
                pressure,
                float(policy["min_chamber_pressure_kpa"]),
                float(policy["max_chamber_pressure_kpa"]),
            )
        )
    if not _at_most(packing, float(policy["max_tray_packing_fraction"])):
        conditioning.append(
            "the tray is packed to %.4f against the %.4f cap that keeps the air "
            "reaching every package"
            % (packing, float(policy["max_tray_packing_fraction"]))
        )
    if not _at_least(clearance, float(policy["min_terminal_clearance_mm"])):
        conditioning.append(
            "terminals stand %.3f mm clear against the %.3f mm minimum"
            % (clearance, float(policy["min_terminal_clearance_mm"]))
        )
    if not _at_least(dwell, float(policy["min_soak_dwell_h"])):
        conditioning.append(
            "the soak dwell is %.2f h against the %.2f h that conditions the "
            "devices at all" % (dwell, float(policy["min_soak_dwell_h"]))
        )
    findings.extend(conditioning)

    if detached:
        findings.append(
            "%d device(s) came apart at a site rather than reading low"
            % (len(detached),)
        )
    if not _at_most(reject_fraction, float(policy["max_reject_fraction"])):
        findings.append(
            "%.4f of the devices pulled fall short against the %.4f the lot "
            "allows" % (reject_fraction, float(policy["max_reject_fraction"]))
        )

    if partial:
        result["verdict"] = LOT_NOT_EVALUATED
    elif conditioning:
        result["verdict"] = CONDITIONING_DEFICIENT
    elif detached or not _at_most(
        reject_fraction, float(policy["max_reject_fraction"])
    ):
        result["verdict"] = LOT_FAILED
    else:
        result["verdict"] = LOT_PASSED
    return result
