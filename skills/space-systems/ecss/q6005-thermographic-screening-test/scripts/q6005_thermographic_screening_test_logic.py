"""Thermographic screening of a powered hybrid before its package is sealed.

Anchor: ECSS-Q-ST-60-05 clause 10.3.2 (the infrared imaging of a biased
hybrid circuit, performed while the package is still open, to reveal surface
temperatures the design did not predict).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The image is only as good as the setup that took it. If the detector
  cannot put enough pixels across the smallest feature that matters, a hot
  spot the size of a bond pad is averaged into its surroundings and the
  screen reports a clean unit.
* An infrared camera measures radiance, not temperature. Without the
  emissivity of the surface and the temperature of what it reflects, the
  reading is a number with no units anyone can defend, so the correction is
  applied before anything is compared.
* Every comparison is a rise above the reference the unit sat in, not an
  absolute reading. A workshop five degrees warmer would otherwise turn a
  whole batch into hot spots.
* A site is judged twice: against the absolute surface temperature nothing
  is allowed to exceed, and against the rise the design predicted for that
  site. The first catches a site that will not survive; the second catches a
  site that is not behaving like the circuit that was designed.
* A site far colder than its prediction is an anomaly too. An open bond or a
  part that never turned on dissipates nothing, and a screen that only looks
  for heat walks straight past it.
* The screen runs before the package is sealed, because the value of finding
  the defect is the ability to open nothing and repair it directly.
* The setup index is weighted credit over total weight, and it gates the
  result rather than averaging into it: an inadequate setup makes the screen
  invalid instead of making it a pass with reservations.
"""

from __future__ import annotations

import math

# Absolute zero, for the radiometric correction that has to run in kelvin.
KELVIN_OFFSET = 273.15

# Pixels the detector has to put across the smallest feature of interest
# before a hot spot that size can be separated from its surroundings.
MINIMUM_PIXELS_ACROSS_FEATURE = 3.0

# Surface temperature no site on a screened hybrid is allowed to reach.
MAXIMUM_SURFACE_TEMPERATURE_C = 125.0

# Ratios of the observed rise to the predicted rise, and what each means.
CRITICAL_EXCURSION_RATIO = 2.0
MAJOR_EXCURSION_RATIO = 1.5
MINOR_EXCURSION_RATIO = 1.2
COLD_SITE_RATIO = 0.5

# Time the unit is held biased before the image is taken.
MINIMUM_STABILIZATION_SECONDS = 60.0

# Setup conditions and the share of the imaging argument each supplies.
SETUP_CONDITIONS = {
    "detector-resolves-the-smallest-feature": 1.0,
    "surface-emissivity-known-and-applied": 1.0,
    "reflected-background-temperature-recorded": 0.8,
    "bias-applied-at-the-specified-condition": 1.0,
    "thermal-stabilization-dwell-completed": 0.9,
    "package-still-open-at-capture": 1.0,
    "reference-ambient-temperature-recorded": 0.7,
}

# Conditions without which the image cannot be read at all.
MANDATORY_SETUP_CONDITIONS = (
    "detector-resolves-the-smallest-feature",
    "surface-emissivity-known-and-applied",
    "bias-applied-at-the-specified-condition",
    "thermal-stabilization-dwell-completed",
    "package-still-open-at-capture",
)

SETUP_STATE_CREDIT = {
    "met-and-recorded": 1.0,
    "met-not-recorded": 0.6,
    "not-met": 0.0,
}

SITE_CATEGORIES = (
    "nominal-site",
    "minor-hot-spot",
    "major-hot-spot",
    "critical-hot-spot",
    "cold-site-anomaly",
)

# Setup index a readable thermographic screen has to reach.
ACCEPTANCE_INDEX = 0.85

# Ratios and corrected temperatures are computed, not tabulated; a case meant
# to sit on a bound can land a few units in the last place away from it.
THERMOGRAPHIC_TOLERANCE = 1e-9

VERDICTS = (
    "thermographic-screen-passed",
    "thermographic-screen-passed-with-open-actions",
    "unit-rejected-on-thermographic-screen",
    "thermographic-screen-invalid",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return ``value`` as a strictly positive finite float or raise."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _kelvin(value, label):
    """Return a celsius reading as kelvin, rejecting anything below zero K."""
    number = _real(value, label)
    kelvin = number + KELVIN_OFFSET
    if kelvin <= 0.0:
        raise ValueError("%s must be above absolute zero, got %r" % (label, value))
    return kelvin


def pixels_across_feature(feature_size_um, pixel_pitch_um):
    """How many detector pixels fall across the smallest feature of interest."""
    feature = _positive(feature_size_um, "feature_size_um")
    pitch = _positive(pixel_pitch_um, "pixel_pitch_um")
    return feature / pitch


def resolution_is_adequate(feature_size_um, pixel_pitch_um):
    """True when the detector can separate the feature from its surroundings."""
    pixels = pixels_across_feature(feature_size_um, pixel_pitch_um)
    return pixels >= MINIMUM_PIXELS_ACROSS_FEATURE - THERMOGRAPHIC_TOLERANCE


def corrected_surface_temperature_c(
    indicated_temperature_c, emissivity, reflected_temperature_c
):
    """Surface temperature once emissivity and the reflected background are removed.

    The camera reports the temperature a perfect emitter would have to reach
    to send it that radiance. Backing the reflected part out has to happen in
    radiance, which means kelvin and fourth powers, so the arithmetic runs in
    kelvin and comes back in celsius.
    """
    eps = _real(emissivity, "emissivity")
    if eps <= 0.0 or eps > 1.0:
        raise ValueError("emissivity must lie in (0, 1], got %r" % (emissivity,))
    indicated_k = _kelvin(indicated_temperature_c, "indicated_temperature_c")
    reflected_k = _kelvin(reflected_temperature_c, "reflected_temperature_c")
    radiance = (indicated_k ** 4 - (1.0 - eps) * reflected_k ** 4) / eps
    if radiance <= 0.0:
        raise ValueError(
            "the reflected background exceeds the indicated radiance; "
            "emissivity %r cannot be correct" % (emissivity,)
        )
    return radiance ** 0.25 - KELVIN_OFFSET


def temperature_rise_k(site_temperature_c, reference_temperature_c):
    """Rise of a site above the reference the unit was sitting in."""
    site = _real(site_temperature_c, "site_temperature_c")
    reference = _real(reference_temperature_c, "reference_temperature_c")
    rise = site - reference
    if rise < -THERMOGRAPHIC_TOLERANCE:
        raise ValueError(
            "a biased site cannot sit below the reference (%r below %r)"
            % (site_temperature_c, reference_temperature_c)
        )
    return max(rise, 0.0)


def excursion_ratio(observed_rise_k, predicted_rise_k):
    """Observed rise over the rise the design predicted for that site."""
    observed = _real(observed_rise_k, "observed_rise_k")
    if observed < 0.0:
        raise ValueError("observed_rise_k must not be negative, got %r" % (observed_rise_k,))
    predicted = _positive(predicted_rise_k, "predicted_rise_k")
    return observed / predicted


def categorize_site(site, reference_temperature_c):
    """Group one imaged site by how far it departs from what was predicted.

    The absolute surface limit is read first, because a site over it will not
    survive whatever the design predicted for it.
    """
    if not isinstance(site, dict):
        raise ValueError("site must be a mapping, got %r" % (type(site).__name__,))
    site_id = site.get("site_id")
    if not isinstance(site_id, str) or not site_id.strip():
        raise ValueError("site_id must be a non-empty string, got %r" % (site_id,))
    measured = _real(site.get("surface_temperature_c"), "surface_temperature_c")
    rise = temperature_rise_k(measured, reference_temperature_c)
    ratio = excursion_ratio(rise, site.get("predicted_rise_k"))
    if measured >= MAXIMUM_SURFACE_TEMPERATURE_C - THERMOGRAPHIC_TOLERANCE:
        return "critical-hot-spot"
    if ratio >= CRITICAL_EXCURSION_RATIO - THERMOGRAPHIC_TOLERANCE:
        return "critical-hot-spot"
    if ratio >= MAJOR_EXCURSION_RATIO - THERMOGRAPHIC_TOLERANCE:
        return "major-hot-spot"
    if ratio >= MINOR_EXCURSION_RATIO - THERMOGRAPHIC_TOLERANCE:
        return "minor-hot-spot"
    if ratio <= COLD_SITE_RATIO + THERMOGRAPHIC_TOLERANCE:
        return "cold-site-anomaly"
    return "nominal-site"


def setup_condition_weight(name):
    """Share of the imaging argument one setup condition supplies."""
    if name not in SETUP_CONDITIONS:
        raise ValueError(
            "unknown setup condition %r (known: %s)"
            % (name, ", ".join(sorted(SETUP_CONDITIONS)))
        )
    return SETUP_CONDITIONS[name]


def setup_state_credit(state):
    """Credit a setup-condition state earns."""
    if state not in SETUP_STATE_CREDIT:
        raise ValueError(
            "unknown setup state %r (known: %s)"
            % (state, ", ".join(sorted(SETUP_STATE_CREDIT)))
        )
    return SETUP_STATE_CREDIT[state]


def assess_setup_condition(name, state):
    """Grade one setup condition into a credit and its findings."""
    weight = setup_condition_weight(name)
    credit = setup_state_credit(state)
    mandatory = name in MANDATORY_SETUP_CONDITIONS
    findings = []
    if state == "not-met":
        findings.append("setup-condition-not-met")
    elif state == "met-not-recorded":
        findings.append("setup-condition-not-recorded")
    mandatory_missing = mandatory and state == "not-met"
    if mandatory_missing:
        findings.append("mandatory-setup-condition-not-met")
    return {
        "condition": name,
        "state": state,
        "mandatory": mandatory,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_missing": mandatory_missing,
        "findings": findings,
    }


def setup_index(records):
    """Weighted credit of a set of graded setup conditions over total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("a thermographic screen must carry at least one condition")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total setup weight must be positive")
    return earned / total_weight


def assess_thermographic_screen(
    unit_id,
    reference_temperature_c,
    stabilization_seconds,
    sites,
    setup=None,
):
    """Grade one thermographic screening run and name a single verdict."""
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("unit_id must be a non-empty string, got %r" % (unit_id,))
    if setup is None:
        setup = {}
    if not isinstance(setup, dict):
        raise ValueError("setup must be a mapping, got %r" % (type(setup).__name__,))
    for name in setup:
        setup_condition_weight(name)  # validation only
    if not isinstance(sites, (list, tuple)) or len(sites) == 0:
        raise ValueError("a thermographic screen must image at least one site")

    dwell = _real(stabilization_seconds, "stabilization_seconds")
    if dwell < 0.0:
        raise ValueError("stabilization_seconds must not be negative, got %r" % (dwell,))
    dwell_met = dwell >= MINIMUM_STABILIZATION_SECONDS - THERMOGRAPHIC_TOLERANCE

    states = dict(setup)
    if "thermal-stabilization-dwell-completed" not in states:
        states["thermal-stabilization-dwell-completed"] = (
            "met-and-recorded" if dwell_met else "not-met"
        )
    elif not dwell_met:
        states["thermal-stabilization-dwell-completed"] = "not-met"

    setup_records = []
    for name in sorted(SETUP_CONDITIONS):
        state = states.get(name, "not-met")
        if not isinstance(state, str):
            raise ValueError("setup state must be a string, got %r" % (state,))
        setup_records.append(assess_setup_condition(name, state))
    index = setup_index(setup_records)

    findings = []
    for record in setup_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["condition"], "finding": finding, "detail": record["state"]}
            )

    seen = set()
    site_records = []
    for raw in sites:
        category = categorize_site(raw, reference_temperature_c)
        site_id = raw["site_id"]
        if site_id in seen:
            raise ValueError("duplicate imaged site %r" % (site_id,))
        seen.add(site_id)
        rise = temperature_rise_k(raw["surface_temperature_c"], reference_temperature_c)
        ratio = excursion_ratio(rise, raw["predicted_rise_k"])
        site_records.append(
            {
                "site_id": site_id,
                "surface_temperature_c": _real(
                    raw["surface_temperature_c"], "surface_temperature_c"
                ),
                "rise_k": rise,
                "excursion_ratio": ratio,
                "category": category,
            }
        )
        if category != "nominal-site":
            findings.append(
                {"item": site_id, "finding": category, "detail": "ratio %.3f" % (ratio,)}
            )

    invalid = (
        any(record["mandatory_missing"] for record in setup_records)
        or index < ACCEPTANCE_INDEX - THERMOGRAPHIC_TOLERANCE
    )
    rejecting = {"critical-hot-spot", "major-hot-spot", "cold-site-anomaly"}
    rejected = any(record["category"] in rejecting for record in site_records)

    if invalid:
        verdict = "thermographic-screen-invalid"
    elif rejected:
        verdict = "unit-rejected-on-thermographic-screen"
    elif findings:
        verdict = "thermographic-screen-passed-with-open-actions"
    else:
        verdict = "thermographic-screen-passed"

    return {
        "unit_id": unit_id,
        "reference_temperature_c": _real(
            reference_temperature_c, "reference_temperature_c"
        ),
        "stabilization_seconds": dwell,
        "stabilization_met": dwell_met,
        "setup_records": setup_records,
        "setup_index": index,
        "site_records": site_records,
        "findings": findings,
        "verdict": verdict,
        "unit_passed": verdict
        in (
            "thermographic-screen-passed",
            "thermographic-screen-passed-with-open-actions",
        ),
    }
