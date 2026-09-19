"""Doppler shift and Doppler rate on a space communication link.

Anchor: ECSS-E-ST-50C clause 5.6.11.1 -- Doppler shift and Doppler rate.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the link works across the Doppler the
geometry actually produces. Two quantities fall out of the radial motion
between the two ends and both have to be inside what the receiver can do:

  shift -- carrier frequency times radial velocity over the speed of light,
           the offset the receiver has to find before it can lock;
  rate  -- carrier frequency times radial acceleration over the speed of
           light, the sweep the receiver has to follow once it has locked.

Neither is judged on its own. The offset the receiver must search is the
Doppler shift widened by the frequency uncertainty of both oscillators, and
the rate is judged against what the tracking loop can follow, which is a
different number from the acquisition range. A link can pass one and fail the
other, so the assessment names which limit binds.

All arithmetic here is multiplication and division of finite floats: no
exponentiation and no logarithm, because those are not correctly rounded and
would make an exact-bound verdict depend on the build host.
"""

import math

__all__ = [
    "SPEED_OF_LIGHT_M_S",
    "WITHIN_CAPABILITY",
    "SHIFT_EXCEEDS_ACQUISITION",
    "RATE_EXCEEDS_TRACKING",
    "REL_TOL",
    "validate_frequency_hz",
    "validate_speed_m_s",
    "validate_acceleration_m_s2",
    "validate_ppm",
    "doppler_shift_hz",
    "doppler_rate_hz_s",
    "oscillator_uncertainty_hz",
    "total_uncertainty_hz",
    "required_sweep_range_hz",
    "sweep_dwell_time_s",
    "max_radial_velocity_m_s",
    "max_radial_acceleration_m_s2",
    "assess_doppler",
]

SPEED_OF_LIGHT_M_S = 299792458.0

WITHIN_CAPABILITY = "within-capability"
SHIFT_EXCEEDS_ACQUISITION = "shift-exceeds-acquisition"
RATE_EXCEEDS_TRACKING = "rate-exceeds-tracking"

# Relative tolerance for every bound comparison, so a geometry sized to land
# exactly on a receiver limit is accepted on every platform rather than on some.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_frequency_hz(value, name="carrier_hz"):
    """Return a strictly positive carrier frequency in hertz."""
    frequency = _validate_number(value, name)
    if frequency <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return frequency


def validate_speed_m_s(value, name="radial_velocity_m_s"):
    """Return a radial velocity in metres per second, signed, below light speed.

    The sign carries the direction: closing is negative range rate and raises
    the received frequency, opening lowers it. Dropping the sign throws away
    half the information a sweep plan needs.
    """
    speed = _validate_number(value, name)
    if abs(speed) >= SPEED_OF_LIGHT_M_S:
        raise ValueError("%s must be below the speed of light, got %r" % (name, value))
    return speed


def validate_acceleration_m_s2(value, name="radial_acceleration_m_s2"):
    """Return a signed radial acceleration in metres per second squared."""
    return _validate_number(value, name)


def validate_ppm(value, name="stability_ppm"):
    """Return a non-negative oscillator stability in parts per million."""
    ppm = _validate_number(value, name)
    if ppm < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return ppm


def doppler_shift_hz(carrier_hz, radial_velocity_m_s):
    """Return the Doppler offset of the carrier, signed.

    Positive means the received carrier is above the transmitted one, which is
    the closing case.
    """
    carrier = validate_frequency_hz(carrier_hz)
    velocity = validate_speed_m_s(radial_velocity_m_s)
    return -carrier * velocity / SPEED_OF_LIGHT_M_S


def doppler_rate_hz_s(carrier_hz, radial_acceleration_m_s2):
    """Return the rate at which the Doppler offset moves, signed."""
    carrier = validate_frequency_hz(carrier_hz)
    acceleration = validate_acceleration_m_s2(radial_acceleration_m_s2)
    return -carrier * acceleration / SPEED_OF_LIGHT_M_S


def oscillator_uncertainty_hz(carrier_hz, stability_ppm):
    """Return the frequency error a reference of this stability contributes."""
    carrier = validate_frequency_hz(carrier_hz)
    ppm = validate_ppm(stability_ppm)
    return carrier * ppm / 1000000.0


def total_uncertainty_hz(carrier_hz, radial_velocity_m_s, stability_ppm):
    """Return how far off the nominal the carrier can be, worst case.

    Doppler and oscillator error add: the receiver has to search the sum, not
    whichever of the two is larger.
    """
    shift = doppler_shift_hz(carrier_hz, radial_velocity_m_s)
    return abs(shift) + oscillator_uncertainty_hz(carrier_hz, stability_ppm)


def required_sweep_range_hz(carrier_hz, radial_velocity_m_s, stability_ppm):
    """Return the full width the acquisition sweep has to cover.

    The offset can fall either side of nominal, so the sweep spans twice the
    worst-case uncertainty.
    """
    return 2.0 * total_uncertainty_hz(carrier_hz, radial_velocity_m_s, stability_ppm)


def sweep_dwell_time_s(sweep_range_hz, sweep_rate_hz_s):
    """Return the time one acquisition sweep across that range takes."""
    span = _validate_number(sweep_range_hz, "sweep_range_hz")
    if span < 0.0:
        raise ValueError("sweep_range_hz must not be negative, got %r" % sweep_range_hz)
    rate = _validate_number(sweep_rate_hz_s, "sweep_rate_hz_s")
    if rate <= 0.0:
        raise ValueError("sweep_rate_hz_s must be greater than zero, got %r" % sweep_rate_hz_s)
    return span / rate


def max_radial_velocity_m_s(carrier_hz, acquisition_range_hz, stability_ppm=0.0):
    """Return the radial velocity that just fills the receiver acquisition range.

    Zero means the oscillator error alone already fills it, so no motion at all
    is tolerable and the reference, not the geometry, is the problem.
    """
    carrier = validate_frequency_hz(carrier_hz)
    span = _validate_number(acquisition_range_hz, "acquisition_range_hz")
    if span <= 0.0:
        raise ValueError("acquisition_range_hz must be greater than zero, got %r" % acquisition_range_hz)
    room = span - oscillator_uncertainty_hz(carrier, stability_ppm)
    if room < 0.0:
        return 0.0
    return room * SPEED_OF_LIGHT_M_S / carrier


def max_radial_acceleration_m_s2(carrier_hz, tracking_rate_hz_s):
    """Return the radial acceleration the tracking loop can just follow."""
    carrier = validate_frequency_hz(carrier_hz)
    rate = _validate_number(tracking_rate_hz_s, "tracking_rate_hz_s")
    if rate <= 0.0:
        raise ValueError("tracking_rate_hz_s must be greater than zero, got %r" % tracking_rate_hz_s)
    return rate * SPEED_OF_LIGHT_M_S / carrier


def assess_doppler(
    carrier_hz,
    radial_velocity_m_s,
    radial_acceleration_m_s2,
    acquisition_range_hz,
    tracking_rate_hz_s,
    stability_ppm=0.0,
):
    """Assess one link geometry against what the receiver can acquire and track."""
    carrier = validate_frequency_hz(carrier_hz)
    velocity = validate_speed_m_s(radial_velocity_m_s)
    acceleration = validate_acceleration_m_s2(radial_acceleration_m_s2)
    acq = _validate_number(acquisition_range_hz, "acquisition_range_hz")
    if acq <= 0.0:
        raise ValueError("acquisition_range_hz must be greater than zero, got %r" % acquisition_range_hz)
    track = _validate_number(tracking_rate_hz_s, "tracking_rate_hz_s")
    if track <= 0.0:
        raise ValueError("tracking_rate_hz_s must be greater than zero, got %r" % tracking_rate_hz_s)
    ppm = validate_ppm(stability_ppm)
    shift = -carrier * velocity / SPEED_OF_LIGHT_M_S
    rate = -carrier * acceleration / SPEED_OF_LIGHT_M_S
    oscillator = carrier * ppm / 1000000.0
    uncertainty = abs(shift) + oscillator
    acq_tolerance = REL_TOL * max(acq, 1.0)
    shift_ok = uncertainty <= acq + acq_tolerance
    track_tolerance = REL_TOL * max(track, 1.0)
    rate_ok = abs(rate) <= track + track_tolerance
    if not shift_ok:
        verdict = SHIFT_EXCEEDS_ACQUISITION
    elif not rate_ok:
        verdict = RATE_EXCEEDS_TRACKING
    else:
        verdict = WITHIN_CAPABILITY
    findings = []
    if not shift_ok:
        findings.append(
            "worst-case offset of %.6g Hz exceeds the %.6g Hz acquisition range; the "
            "geometry tolerated at this reference is %.6g m/s of radial velocity"
            % (uncertainty, acq, max_radial_velocity_m_s(carrier, acq, ppm))
        )
        if oscillator > abs(shift):
            findings.append(
                "oscillator error of %.6g Hz is larger than the %.6g Hz Doppler; a better "
                "reference buys more than a wider sweep" % (oscillator, abs(shift))
            )
    if not rate_ok:
        findings.append(
            "Doppler rate of %.6g Hz/s exceeds the %.6g Hz/s the loop can follow; the "
            "radial acceleration tolerated is %.6g m/s2"
            % (abs(rate), track, max_radial_acceleration_m_s2(carrier, track))
        )
    if shift_ok and rate_ok:
        binding = "acquisition" if uncertainty / acq >= abs(rate) / track else "tracking"
    elif not shift_ok:
        binding = "acquisition"
    else:
        binding = "tracking"
    return {
        "carrier_hz": carrier,
        "radial_velocity_m_s": velocity,
        "radial_acceleration_m_s2": acceleration,
        "doppler_shift_hz": shift,
        "doppler_rate_hz_s": rate,
        "oscillator_uncertainty_hz": oscillator,
        "total_uncertainty_hz": uncertainty,
        "required_sweep_range_hz": 2.0 * uncertainty,
        "acquisition_range_hz": acq,
        "tracking_rate_hz_s": track,
        "acquisition_margin_hz": acq - uncertainty,
        "tracking_margin_hz_s": track - abs(rate),
        "max_radial_velocity_m_s": max_radial_velocity_m_s(carrier, acq, ppm),
        "max_radial_acceleration_m_s2": max_radial_acceleration_m_s2(carrier, track),
        "binding_limit": binding,
        "shift_within_acquisition": shift_ok,
        "rate_within_tracking": rate_ok,
        "verdict": verdict,
        "findings": findings,
    }
