#!/usr/bin/env python3
"""Magnetic moment test setup, ECSS-E-ST-20-07C clause 5.4.5.2.

Paraphrased procedure, no verbatim standard text. The clause has the unit
placed in an area whose ambient field is compensated away, so that what the
magnetometers see is the unit's own intrinsic moment and not the site. This
module turns that into a deterministic assessment of a setup:

  residual field after compensation -> is the area really compensated
  largest unit dimension            -> separation at which a point dipole holds
  moment + separation               -> field the sensors are asked to resolve
  field vs sensor noise floor       -> is that field usable
  fixture and nearby hardware       -> what compensation cannot remove

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Residual fields, separations and field strengths are
# floats, so a requirement that is exactly met can land a few units in the last
# place short. The tolerances absorb that representation error only.
FIELD_REL_TOL = 1e-12
FIELD_ABS_TOL = 1e-9
LENGTH_REL_TOL = 1e-12
LENGTH_ABS_TOL = 1e-12
RATIO_REL_TOL = 1e-12
RATIO_ABS_TOL = 1e-12

# Axial dipole field in nanotesla at distance r metres from a moment m A*m^2:
# (mu0 / 4*pi) * 2m / r^3, expressed in nT -> 1e9 * 1e-7 * 2 = 200.
MU0_OVER_4PI_T_M_PER_A = 1e-7
NT_PER_T = 1e9
AXIAL_DIPOLE_NT_COEFF = NT_PER_T * MU0_OVER_4PI_T_M_PER_A * 2.0

# Separations closer than this multiple of the unit's largest dimension stop
# behaving like a single point source, so an intrinsic moment read there is a
# near-field artefact of the unit's internal layout.
DEFAULT_DIPOLE_DISTANCE_RATIO = 3.0

# The unit's own field has to stand clear of the magnetometer noise floor
# before a moment derived from it means anything.
DEFAULT_MIN_SNR = 10.0
THIN_MARGIN_FACTOR = 3.0

# How far above the stated compensation tolerance a residual may sit before
# the area stops counting as partially compensated at all.
PARTIAL_COMPENSATION_FACTOR = 5.0

STATE_COMPENSATED = "compensated"
STATE_PARTIAL = "partially-compensated"
STATE_UNCOMPENSATED = "uncompensated"
COMPENSATION_STATES = (STATE_COMPENSATED, STATE_PARTIAL, STATE_UNCOMPENSATED)

SETUP_READY = "setup-ready"
SETUP_DEFICIENT = "setup-deficient"


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


def at_most(value, bound, rel_tol=FIELD_REL_TOL, abs_tol=FIELD_ABS_TOL):
    """True when a value stays at or under a bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=rel_tol, abs_tol=abs_tol)


def at_least(value, bound, rel_tol=FIELD_REL_TOL, abs_tol=FIELD_ABS_TOL):
    """True when a value reaches a bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=rel_tol, abs_tol=abs_tol)


def residual_field_magnitude_nt(bx_nt, by_nt, bz_nt):
    """Vector magnitude of the field left in the area after compensation."""
    bx = _scalar(bx_nt, "residual_bx_nt")
    by = _scalar(by_nt, "residual_by_nt")
    bz = _scalar(bz_nt, "residual_bz_nt")
    return math.sqrt(bx * bx + by * by + bz * bz)


def compensation_grouping(residual_nt, tolerance_nt):
    """Group the compensated area by how much field it still carries."""
    residual = _scalar(residual_nt, "residual_nt")
    tolerance = _scalar(tolerance_nt, "tolerance_nt")
    if residual < 0.0:
        raise ValueError("residual_nt must be >= 0, got %g" % residual)
    if tolerance <= 0.0:
        raise ValueError("tolerance_nt must be > 0, got %g" % tolerance)
    if at_most(residual, tolerance):
        return STATE_COMPENSATED
    if at_most(residual, tolerance * PARTIAL_COMPENSATION_FACTOR):
        return STATE_PARTIAL
    return STATE_UNCOMPENSATED


def minimum_separation_m(largest_dimension_m, ratio=DEFAULT_DIPOLE_DISTANCE_RATIO):
    """Closest sensor separation at which the unit still reads as one dipole."""
    dimension = _scalar(largest_dimension_m, "largest_dimension_m")
    factor = _scalar(ratio, "ratio")
    if dimension <= 0.0:
        raise ValueError("largest_dimension_m must be > 0, got %g" % dimension)
    if factor < 1.0:
        raise ValueError("ratio must be >= 1, got %g" % factor)
    return dimension * factor


def axial_dipole_field_nt(moment_am2, distance_m):
    """Field on the dipole axis, in nanotesla, from a moment at a distance."""
    moment = _scalar(moment_am2, "moment_am2")
    distance = _scalar(distance_m, "distance_m")
    if moment <= 0.0:
        raise ValueError("moment_am2 must be > 0, got %g" % moment)
    if distance <= 0.0:
        raise ValueError("distance_m must be > 0, got %g" % distance)
    return AXIAL_DIPOLE_NT_COEFF * moment / (distance * distance * distance)


def signal_to_noise_ratio(field_nt, noise_floor_nt):
    """How far the unit's own field stands above the magnetometer noise."""
    field = _scalar(field_nt, "field_nt")
    noise = _scalar(noise_floor_nt, "noise_floor_nt")
    if field < 0.0:
        raise ValueError("field_nt must be >= 0, got %g" % field)
    if noise <= 0.0:
        raise ValueError("noise_floor_nt must be > 0, got %g" % noise)
    return field / noise


def validate_setup(config):
    """Validate a moment-test setup record and return it normalized.

    Required: residual_bx_nt, residual_by_nt, residual_bz_nt (finite),
    compensation_tolerance_nt (> 0), largest_dimension_m (> 0),
    measurement_distance_m (> 0), expected_moment_am2 (> 0),
    sensor_noise_floor_nt (> 0), compensation_active, non_magnetic_fixture and
    ferromagnetic_items_present (booleans).
    """
    where = "setup"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)

    residual = {
        key: _number(config, key, where)
        for key in ("residual_bx_nt", "residual_by_nt", "residual_bz_nt")
    }

    tolerance = _number(config, "compensation_tolerance_nt", where)
    if tolerance <= 0.0:
        raise ValueError(
            "%s: compensation_tolerance_nt must be > 0, got %g" % (where, tolerance)
        )
    dimension = _number(config, "largest_dimension_m", where)
    if dimension <= 0.0:
        raise ValueError(
            "%s: largest_dimension_m must be > 0, got %g" % (where, dimension)
        )
    distance = _number(config, "measurement_distance_m", where)
    if distance <= 0.0:
        raise ValueError(
            "%s: measurement_distance_m must be > 0, got %g" % (where, distance)
        )
    moment = _number(config, "expected_moment_am2", where)
    if moment <= 0.0:
        raise ValueError(
            "%s: expected_moment_am2 must be > 0, got %g" % (where, moment)
        )
    noise = _number(config, "sensor_noise_floor_nt", where)
    if noise <= 0.0:
        raise ValueError(
            "%s: sensor_noise_floor_nt must be > 0, got %g" % (where, noise)
        )

    out = {
        "compensation_tolerance_nt": tolerance,
        "largest_dimension_m": dimension,
        "measurement_distance_m": distance,
        "expected_moment_am2": moment,
        "sensor_noise_floor_nt": noise,
        "compensation_active": _flag(config, "compensation_active", where),
        "non_magnetic_fixture": _flag(config, "non_magnetic_fixture", where),
        "ferromagnetic_items_present": _flag(
            config, "ferromagnetic_items_present", where
        ),
    }
    out.update(residual)
    return out


def separation_findings(setup, ratio=DEFAULT_DIPOLE_DISTANCE_RATIO):
    """Report a sensor separation too close for a point-dipole reading."""
    distance = _number(setup, "measurement_distance_m", "setup")
    dimension = _number(setup, "largest_dimension_m", "setup")
    required = minimum_separation_m(dimension, ratio)
    if at_least(distance, required, LENGTH_REL_TOL, LENGTH_ABS_TOL):
        return []
    return [
        "sensors sit %g m from a unit %g m across; %g m is the closest "
        "separation that still reads as one dipole" % (distance, dimension, required)
    ]


def fixture_findings(setup):
    """Report hardware in the area that compensation cannot take out."""
    if not isinstance(setup, dict):
        raise ValueError("setup: record must be a mapping")
    for key in ("ferromagnetic_items_present", "non_magnetic_fixture"):
        if key not in setup:
            raise ValueError("setup: missing required field %r" % key)
    out = []
    if setup["ferromagnetic_items_present"]:
        out.append(
            "ferromagnetic hardware shares the compensated area; its own moment "
            "adds to the unit's and no coil setting removes it"
        )
    return out


def assess_magnetic_moment_test_setup(
    config,
    ratio=DEFAULT_DIPOLE_DISTANCE_RATIO,
    min_snr=DEFAULT_MIN_SNR,
):
    """Full clause 5.4.5.2 assessment of an intrinsic-moment test setup."""
    setup = validate_setup(config)
    required_snr = _scalar(min_snr, "min_snr")
    if required_snr <= 0.0:
        raise ValueError("min_snr must be > 0, got %g" % required_snr)

    residual = residual_field_magnitude_nt(
        setup["residual_bx_nt"], setup["residual_by_nt"], setup["residual_bz_nt"]
    )
    grouping = compensation_grouping(residual, setup["compensation_tolerance_nt"])
    required_distance = minimum_separation_m(setup["largest_dimension_m"], ratio)
    field = axial_dipole_field_nt(
        setup["expected_moment_am2"], setup["measurement_distance_m"]
    )
    snr = signal_to_noise_ratio(field, setup["sensor_noise_floor_nt"])

    findings = []
    if not setup["compensation_active"]:
        findings.append(
            "the compensation system is not running, so the area carries the site "
            "field and no intrinsic moment can be separated from it"
        )
    if grouping != STATE_COMPENSATED:
        findings.append(
            "residual field %g nT is %s against a %g nT tolerance; the area is %s"
            % (
                residual,
                "above",
                setup["compensation_tolerance_nt"],
                grouping,
            )
        )
    findings.extend(separation_findings(setup, ratio))
    if not at_least(snr, required_snr, RATIO_REL_TOL, RATIO_ABS_TOL):
        findings.append(
            "expected field %g nT stands only %g times above the %g nT noise "
            "floor; %g times is the working minimum"
            % (field, snr, setup["sensor_noise_floor_nt"], required_snr)
        )
    findings.extend(fixture_findings(setup))

    limitations = []
    if not setup["non_magnetic_fixture"]:
        limitations.append(
            "the holding fixture is not declared non-magnetic, so part of the "
            "reading may belong to the fixture rather than the unit"
        )
    if at_least(snr, required_snr, RATIO_REL_TOL, RATIO_ABS_TOL) and not at_least(
        snr, required_snr * THIN_MARGIN_FACTOR, RATIO_REL_TOL, RATIO_ABS_TOL
    ):
        limitations.append(
            "margin over the noise floor is %g times, workable but thin; a drifting "
            "floor will eat it during a long run" % snr
        )

    return {
        "setup": setup,
        "residual_field_nt": residual,
        "compensation_grouping": grouping,
        "minimum_separation_m": required_distance,
        "expected_field_nt": field,
        "signal_to_noise_ratio": snr,
        "findings": findings,
        "limitations": limitations,
        "verdict": SETUP_READY if not findings else SETUP_DEFICIENT,
    }
