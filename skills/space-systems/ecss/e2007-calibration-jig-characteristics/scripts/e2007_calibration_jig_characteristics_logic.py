#!/usr/bin/env python3
"""Calibration jig characteristics logic (ECSS-E-ST-20-07C, 5.2.8.3).

Offline, deterministic, standard-library only. The module qualifies the
coaxial fixture used when a current is measured on the conductor of a
transmission line:

* characteristic impedance of the fixture from its conductor geometry
  and the dielectric filling the annulus,
* match of that impedance to the nominal reference, and the residual
  standing-wave ratio the mismatch produces,
* radial clearance left for the conductor inside the fixture bore,
* insertion loss of the through path and screening of the enclosure,
* usable frequency span against the span the calibration needs,
* injected calibration current derived from the applied power,
* transfer impedance of the probe under calibration, in decibel-ohms,
* fit-for-use verdict on one fixture and on a set of fixtures.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "NOMINAL_IMPEDANCE_OHM",
    "IMPEDANCE_TOLERANCE_FRACTION",
    "MAX_INSERTION_LOSS_DB",
    "MAX_STANDING_WAVE_RATIO",
    "MIN_SCREENING_ATTENUATION_DB",
    "MIN_RADIAL_CLEARANCE_M",
    "coaxial_characteristic_impedance",
    "standing_wave_ratio",
    "radial_clearance_m",
    "check_impedance_match",
    "check_radial_clearance",
    "check_insertion_loss",
    "check_screening_attenuation",
    "check_usable_span",
    "insertion_loss_db",
    "injected_current_a",
    "transfer_impedance_db_ohm",
    "evaluate_calibration_jig",
    "assess_calibration_jig_set",
]

# Absorbs binary-representation error when a value computed as a product,
# a difference or a logarithm lands a few units in the last place outside
# an exactly-met limit. It never widens the limit itself.
REL_TOL = 1e-9

# The fixture presents the same reference impedance as the generator and
# the measuring receiver it sits between.
NOMINAL_IMPEDANCE_OHM = 50.0

# The realised impedance may deviate from that reference by this fraction.
IMPEDANCE_TOLERANCE_FRACTION = 0.02

# Through-path loss the fixture may introduce, in dB.
MAX_INSERTION_LOSS_DB = 0.5

# Standing-wave ratio the residual mismatch may produce.
MAX_STANDING_WAVE_RATIO = 1.2

# Screening the fixture enclosure provides so that the injected current
# stays on the conductor under measurement, in dB.
MIN_SCREENING_ATTENUATION_DB = 40.0

# Radial gap left between the conductor and the fixture bore, in metres.
MIN_RADIAL_CLEARANCE_M = 0.001

# Intrinsic impedance of free space divided by two pi, in ohms. The
# coaxial line impedance is this factor times the natural logarithm of the
# diameter ratio, divided by the square root of the relative permittivity.
_IMPEDANCE_FACTOR_OHM = 376.730313668 / (2.0 * math.pi)

_JIG_KEYS = (
    "id",
    "bore_diameter_m",
    "conductor_diameter_m",
    "relative_permittivity",
    "insertion_loss_db",
    "screening_attenuation_db",
    "usable_lower_hz",
    "usable_upper_hz",
)

_REQUIRED_JIG_KEYS = (
    "id",
    "bore_diameter_m",
    "conductor_diameter_m",
    "insertion_loss_db",
    "screening_attenuation_db",
    "usable_lower_hz",
    "usable_upper_hz",
)


def _finding(code, subject, detail):
    """Build one qualification finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _as_non_negative_float(value, label):
    number = _as_float(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _at_most(value, limit):
    """Upper-limit comparison that absorbs binary-representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=0.0)


def _at_least(value, limit):
    """Lower-limit comparison that absorbs binary-representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=0.0)


def coaxial_characteristic_impedance(
    bore_diameter_m, conductor_diameter_m, relative_permittivity=1.0
):
    """Characteristic impedance of the coaxial fixture, in ohms.

    The fixture is an air- or dielectric-filled annulus between the
    conductor under measurement and the fixture bore.
    """
    bore = _as_positive_float(bore_diameter_m, "bore_diameter_m")
    conductor = _as_positive_float(conductor_diameter_m, "conductor_diameter_m")
    permittivity = _as_float(relative_permittivity, "relative_permittivity")
    if permittivity < 1.0:
        raise ValueError(
            "relative_permittivity must be at least one, got %r" % (relative_permittivity,)
        )
    if bore <= conductor:
        raise ValueError(
            "bore diameter %r must exceed the conductor diameter %r"
            % (bore_diameter_m, conductor_diameter_m)
        )
    return _IMPEDANCE_FACTOR_OHM * math.log(bore / conductor) / math.sqrt(permittivity)


def standing_wave_ratio(measured_ohm, reference_ohm=NOMINAL_IMPEDANCE_OHM):
    """Standing-wave ratio produced by a real impedance mismatch."""
    measured = _as_positive_float(measured_ohm, "measured_ohm")
    reference = _as_positive_float(reference_ohm, "reference_ohm")
    return max(measured, reference) / min(measured, reference)


def radial_clearance_m(bore_diameter_m, conductor_diameter_m):
    """Radial gap between the conductor and the fixture bore, in metres."""
    bore = _as_positive_float(bore_diameter_m, "bore_diameter_m")
    conductor = _as_positive_float(conductor_diameter_m, "conductor_diameter_m")
    if bore <= conductor:
        raise ValueError(
            "bore diameter %r must exceed the conductor diameter %r"
            % (bore_diameter_m, conductor_diameter_m)
        )
    return (bore - conductor) / 2.0


def check_impedance_match(
    measured_ohm,
    reference_ohm=NOMINAL_IMPEDANCE_OHM,
    fraction=IMPEDANCE_TOLERANCE_FRACTION,
    max_ratio=MAX_STANDING_WAVE_RATIO,
):
    """Check the realised impedance and the mismatch it leaves behind."""
    measured = _as_positive_float(measured_ohm, "measured_ohm")
    reference = _as_positive_float(reference_ohm, "reference_ohm")
    allowance = _as_positive_float(fraction, "fraction")
    ratio_limit = _as_positive_float(max_ratio, "max_ratio")
    if ratio_limit < 1.0:
        raise ValueError("max_ratio must be at least one, got %r" % (max_ratio,))
    allowed = reference * allowance
    deviation = abs(measured - reference)
    ratio = standing_wave_ratio(measured, reference)
    return {
        "quantity": "characteristic-impedance",
        "measured_ohm": measured,
        "reference_ohm": reference,
        "deviation_ohm": deviation,
        "allowed_ohm": allowed,
        "percent": (measured - reference) / reference * 100.0,
        "standing_wave_ratio": ratio,
        "max_standing_wave_ratio": ratio_limit,
        "within": _at_most(deviation, allowed),
        "ratio_within": _at_most(ratio, ratio_limit),
    }


def check_radial_clearance(
    bore_diameter_m, conductor_diameter_m, minimum_m=MIN_RADIAL_CLEARANCE_M
):
    """Check that the conductor sits clear of the fixture bore."""
    minimum = _as_positive_float(minimum_m, "minimum_m")
    clearance = radial_clearance_m(bore_diameter_m, conductor_diameter_m)
    return {
        "quantity": "radial-clearance",
        "clearance_m": clearance,
        "required_m": minimum,
        "within": _at_least(clearance, minimum),
    }


def check_insertion_loss(loss_db, limit_db=MAX_INSERTION_LOSS_DB):
    """Check the through-path loss the fixture introduces."""
    loss = _as_non_negative_float(loss_db, "loss_db")
    limit = _as_positive_float(limit_db, "limit_db")
    return {
        "quantity": "insertion-loss",
        "loss_db": loss,
        "allowed_db": limit,
        "margin_db": limit - loss,
        "within": _at_most(loss, limit),
    }


def check_screening_attenuation(
    attenuation_db, minimum_db=MIN_SCREENING_ATTENUATION_DB
):
    """Check the screening the fixture enclosure provides."""
    attenuation = _as_non_negative_float(attenuation_db, "attenuation_db")
    minimum = _as_positive_float(minimum_db, "minimum_db")
    return {
        "quantity": "screening-attenuation",
        "attenuation_db": attenuation,
        "required_db": minimum,
        "margin_db": attenuation - minimum,
        "within": _at_least(attenuation, minimum),
    }


def check_usable_span(
    usable_lower_hz, usable_upper_hz, required_lower_hz, required_upper_hz
):
    """Check that the fixture is usable across the whole calibration span."""
    usable_lower = _as_positive_float(usable_lower_hz, "usable_lower_hz")
    usable_upper = _as_positive_float(usable_upper_hz, "usable_upper_hz")
    required_lower = _as_positive_float(required_lower_hz, "required_lower_hz")
    required_upper = _as_positive_float(required_upper_hz, "required_upper_hz")
    if usable_upper <= usable_lower:
        raise ValueError(
            "usable span must ascend: %r does not exceed %r"
            % (usable_upper_hz, usable_lower_hz)
        )
    if required_upper <= required_lower:
        raise ValueError(
            "required span must ascend: %r does not exceed %r"
            % (required_upper_hz, required_lower_hz)
        )
    low_shortfall = max(0.0, usable_lower - required_lower)
    high_shortfall = max(0.0, required_upper - usable_upper)
    covers = (
        _at_most(usable_lower, required_lower)
        and _at_least(usable_upper, required_upper)
    )
    return {
        "quantity": "usable-span",
        "usable_lower_hz": usable_lower,
        "usable_upper_hz": usable_upper,
        "required_lower_hz": required_lower,
        "required_upper_hz": required_upper,
        "low_shortfall_hz": low_shortfall,
        "high_shortfall_hz": high_shortfall,
        "within": covers,
    }


def insertion_loss_db(input_power_w, output_power_w):
    """Through-path loss from the power in and the power out, in dB."""
    supplied = _as_positive_float(input_power_w, "input_power_w")
    delivered = _as_positive_float(output_power_w, "output_power_w")
    if delivered > supplied and not math.isclose(
        delivered, supplied, rel_tol=REL_TOL, abs_tol=0.0
    ):
        raise ValueError(
            "a passive fixture cannot deliver %r W from %r W"
            % (output_power_w, input_power_w)
        )
    return 10.0 * math.log10(supplied / delivered)


def injected_current_a(power_w, impedance_ohm=NOMINAL_IMPEDANCE_OHM):
    """Calibration current the applied power drives through the fixture."""
    power = _as_non_negative_float(power_w, "power_w")
    impedance = _as_positive_float(impedance_ohm, "impedance_ohm")
    return math.sqrt(power / impedance)


def transfer_impedance_db_ohm(output_voltage_v, current_a):
    """Transfer impedance of the probe under calibration, in dB-ohms."""
    voltage = _as_positive_float(output_voltage_v, "output_voltage_v")
    current = _as_positive_float(current_a, "current_a")
    return 20.0 * math.log10(voltage / current)


def evaluate_calibration_jig(jig, required_lower_hz, required_upper_hz):
    """Qualify one fixture against every characteristic the clause fixes."""
    if not isinstance(jig, dict):
        raise ValueError("jig must be a mapping, got %s" % type(jig).__name__)
    unknown = [key for key in jig if key not in _JIG_KEYS]
    if unknown:
        raise ValueError("jig carries unknown key(s): %s" % ", ".join(sorted(unknown)))
    missing = [key for key in _REQUIRED_JIG_KEYS if key not in jig]
    if missing:
        raise ValueError("jig is missing required key(s): %s" % ", ".join(missing))
    if not isinstance(jig["id"], str) or not jig["id"].strip():
        raise ValueError("jig id must be a non-blank string")
    identifier = jig["id"].strip()

    impedance = coaxial_characteristic_impedance(
        jig["bore_diameter_m"],
        jig["conductor_diameter_m"],
        jig.get("relative_permittivity", 1.0),
    )
    checks = {
        "impedance": check_impedance_match(impedance),
        "clearance": check_radial_clearance(
            jig["bore_diameter_m"], jig["conductor_diameter_m"]
        ),
        "insertion_loss": check_insertion_loss(jig["insertion_loss_db"]),
        "screening": check_screening_attenuation(jig["screening_attenuation_db"]),
        "span": check_usable_span(
            jig["usable_lower_hz"],
            jig["usable_upper_hz"],
            required_lower_hz,
            required_upper_hz,
        ),
    }
    findings = []
    if not checks["impedance"]["within"]:
        findings.append(
            _finding(
                "impedance-out-of-band",
                identifier,
                "geometry realises %.4f ohm against a %.4f ohm reference "
                "(allowed %.4f ohm)"
                % (
                    checks["impedance"]["measured_ohm"],
                    checks["impedance"]["reference_ohm"],
                    checks["impedance"]["allowed_ohm"],
                ),
            )
        )
    if not checks["impedance"]["ratio_within"]:
        findings.append(
            _finding(
                "standing-wave-ratio-too-high",
                identifier,
                "mismatch leaves a ratio of %.4f against a %.4f limit"
                % (
                    checks["impedance"]["standing_wave_ratio"],
                    checks["impedance"]["max_standing_wave_ratio"],
                ),
            )
        )
    if not checks["clearance"]["within"]:
        findings.append(
            _finding(
                "radial-clearance-too-small",
                identifier,
                "conductor leaves %.5f m against the %.5f m required"
                % (
                    checks["clearance"]["clearance_m"],
                    checks["clearance"]["required_m"],
                ),
            )
        )
    if not checks["insertion_loss"]["within"]:
        findings.append(
            _finding(
                "insertion-loss-too-high",
                identifier,
                "through path loses %.4f dB against a %.4f dB limit"
                % (
                    checks["insertion_loss"]["loss_db"],
                    checks["insertion_loss"]["allowed_db"],
                ),
            )
        )
    if not checks["screening"]["within"]:
        findings.append(
            _finding(
                "screening-too-low",
                identifier,
                "enclosure screens %.4f dB against the %.4f dB required"
                % (
                    checks["screening"]["attenuation_db"],
                    checks["screening"]["required_db"],
                ),
            )
        )
    if not checks["span"]["within"]:
        findings.append(
            _finding(
                "span-does-not-cover",
                identifier,
                "usable from %.6g Hz to %.6g Hz against a calibration span of "
                "%.6g Hz to %.6g Hz"
                % (
                    checks["span"]["usable_lower_hz"],
                    checks["span"]["usable_upper_hz"],
                    checks["span"]["required_lower_hz"],
                    checks["span"]["required_upper_hz"],
                ),
            )
        )
    return {
        "id": identifier,
        "characteristic_impedance_ohm": impedance,
        "checks": checks,
        "findings": findings,
        "fit_for_use": not findings,
    }


def assess_calibration_jig_set(jigs, required_lower_hz, required_upper_hz):
    """Qualify a set of fixtures offered for one calibration span."""
    if isinstance(jigs, (str, bytes)) or not hasattr(jigs, "__iter__"):
        raise ValueError("jigs must be an iterable of fixture records")
    evaluated = [
        evaluate_calibration_jig(jig, required_lower_hz, required_upper_hz)
        for jig in jigs
    ]
    if not evaluated:
        raise ValueError("at least one fixture is required")
    seen = set()
    for record in evaluated:
        if record["id"] in seen:
            raise ValueError("fixture %r appears twice" % record["id"])
        seen.add(record["id"])
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])
    usable = [record for record in evaluated if record["fit_for_use"]]
    if not usable:
        findings.append(
            _finding(
                "no-usable-fixture",
                "calibration-set",
                "none of the %d offered fixtures qualifies for the span"
                % len(evaluated),
            )
        )
    return {
        "verdict": "fit-for-use" if usable and not [
            record for record in evaluated if not record["fit_for_use"]
        ] else ("partially-usable" if usable else "not-usable"),
        "accepted": bool(usable),
        "fixtures": evaluated,
        "fixture_count": len(evaluated),
        "usable_ids": [record["id"] for record in usable],
        "findings": findings,
        "usable_fraction": len(usable) / float(len(evaluated)),
    }
