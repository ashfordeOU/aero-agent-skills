"""Spacecraft parabolic antenna aperture sizing, pure stdlib.

Reverse-direction sizing: the antenna gain is an INPUT handed over from the
forward communication link design (the communication-link-budget sibling);
this module converts a required gain into the reflector diameter through the
aperture efficiency, then reports the achieved gain of the sized aperture,
the half-power beamwidth, the pointing accuracy budget with its pointing
loss, and the receive gain-over-temperature G/T figure of merit.

Units conventions, matching the communication-link-budget sibling:
- length: meters (m); frequency: hertz (Hz); c = 299792458 m/s
- gains and losses: dB (positive); aperture gain linear ratio where stated
- noise temperature: kelvin (K); Boltzmann k = 1.380649e-23 J/K
- data rate: bits per second (bps); G/T: dB/K

Non-positive physical inputs raise ValueError with a clear message. All
functions are deterministic (no RNG) and depend only on the math module.
"""

import math

ETA_APERTURE_DEFAULT = 0.6          # typical parabolic reflector aperture efficiency
K_BOLTZ = 1.380649e-23              # Boltzmann constant, J/K
LIGHT_SPEED = 299792458.0           # speed of light, m/s
POINTING_FRACTION = 0.1             # allowed pointing error as a fraction of the 3 dB beamwidth
POINTING_LOSS_COEF = 12.0           # dB per (theta_e / theta_3dB)**2, small-error approximation


def wavelength(freq_hz):
    """Wavelength lambda = c / f in meters.

    Args:
        freq_hz: operating frequency in hertz, must be > 0.
    Returns:
        float: wavelength in meters.
    Raises:
        ValueError: if freq_hz <= 0.
    """
    if freq_hz <= 0:
        raise ValueError("freq_hz must be > 0 (got %r)" % (freq_hz,))
    return LIGHT_SPEED / freq_hz


def gain_from_aperture(diameter_m, wavelength_m, eta=ETA_APERTURE_DEFAULT):
    """Aperture antenna gain from the reflector diameter.

    G = eta * (pi * D / lambda)**2 is the linear gain; gain_db is
    10 * log10(G).

    Args:
        diameter_m: reflector diameter in meters, must be > 0.
        wavelength_m: operating wavelength in meters, must be > 0.
        eta: aperture efficiency, must be in (0, 1].
    Returns:
        tuple (gain_lin, gain_db): linear gain ratio and gain in dB.
    Raises:
        ValueError: if diameter_m <= 0, wavelength_m <= 0, or eta not in (0, 1].
    """
    if diameter_m <= 0:
        raise ValueError("diameter_m must be > 0 (got %r)" % (diameter_m,))
    if wavelength_m <= 0:
        raise ValueError("wavelength_m must be > 0 (got %r)" % (wavelength_m,))
    if eta <= 0 or eta > 1:
        raise ValueError("eta must be in (0, 1] (got %r)" % (eta,))
    gain_lin = eta * (math.pi * diameter_m / wavelength_m) ** 2
    return gain_lin, 10.0 * math.log10(gain_lin)


def aperture_from_gain(gain_db, wavelength_m, eta=ETA_APERTURE_DEFAULT):
    """Reflector diameter that delivers a required gain at the wavelength.

    D = (lambda / pi) * sqrt(G_lin / eta) with G_lin = 10**(gain_db / 10).

    Args:
        gain_db: required antenna gain in dB, must be > 0 (aperture antennas
            have gain above unity).
        wavelength_m: operating wavelength in meters, must be > 0.
        eta: aperture efficiency, must be in (0, 1].
    Returns:
        float: reflector diameter in meters.
    Raises:
        ValueError: if gain_db <= 0, wavelength_m <= 0, or eta not in (0, 1].
    """
    if gain_db <= 0:
        raise ValueError("gain_db must be > 0 (got %r)" % (gain_db,))
    if wavelength_m <= 0:
        raise ValueError("wavelength_m must be > 0 (got %r)" % (wavelength_m,))
    if eta <= 0 or eta > 1:
        raise ValueError("eta must be in (0, 1] (got %r)" % (eta,))
    gain_lin = 10.0 ** (gain_db / 10.0)
    return (wavelength_m / math.pi) * math.sqrt(gain_lin / eta)


def required_gain_db(margin_db, path_loss_db, other_losses_db,
                     data_rate_bps, noise_temp_k, transmit_power_dbw):
    """Required antenna gain that closes the link at the data rate.

    G_req = margin_db + path_loss_db + other_losses_db
            + 10 * log10(k * T * R) - transmit_power_dbw.

    The terms are supplied by the forward link design; this leaf takes the
    resulting required gain as its sizing input.

    Args:
        margin_db: margin over threshold in dB.
        path_loss_db: path loss term in dB (positive).
        other_losses_db: additional positive losses in dB.
        data_rate_bps: data rate in bits per second, must be > 0.
        noise_temp_k: system noise temperature in kelvin, must be > 0.
        transmit_power_dbw: transmit power in dBW.
    Returns:
        float: required antenna gain in dB.
    Raises:
        ValueError: if data_rate_bps <= 0 or noise_temp_k <= 0.
    """
    if data_rate_bps <= 0:
        raise ValueError("data_rate_bps must be > 0 (got %r)" % (data_rate_bps,))
    if noise_temp_k <= 0:
        raise ValueError("noise_temp_k must be > 0 (got %r)" % (noise_temp_k,))
    return (margin_db + path_loss_db + other_losses_db
            + 10.0 * math.log10(K_BOLTZ * noise_temp_k * data_rate_bps)
            - transmit_power_dbw)


def half_power_beamwidth(diameter_m, wavelength_m):
    """Half-power beamwidth of a circular aperture in degrees.

    theta_3dB = 70 * lambda / D, the standard lambda/D approximation for a
    uniformly illuminated circular aperture.

    Args:
        diameter_m: reflector diameter in meters, must be > 0.
        wavelength_m: operating wavelength in meters, must be > 0.
    Returns:
        float: half-power beamwidth in degrees.
    Raises:
        ValueError: if diameter_m <= 0 or wavelength_m <= 0.
    """
    if diameter_m <= 0:
        raise ValueError("diameter_m must be > 0 (got %r)" % (diameter_m,))
    if wavelength_m <= 0:
        raise ValueError("wavelength_m must be > 0 (got %r)" % (wavelength_m,))
    return 70.0 * wavelength_m / diameter_m


def pointing_budget(theta_3db_deg, pointing_fraction=POINTING_FRACTION):
    """Pointing accuracy budget from the beamwidth and the allowed fraction.

    allowed_error_deg = theta_3dB * pointing_fraction; pointing_loss_db =
    12 * pointing_fraction**2 in the standard small-error approximation.

    Args:
        theta_3db_deg: half-power beamwidth in degrees, must be > 0.
        pointing_fraction: allowed pointing error as a fraction of the
            beamwidth, must be >= 0 (default 0.1).
    Returns:
        dict: {"allowed_error_deg": float, "pointing_loss_db": float}.
    Raises:
        ValueError: if theta_3db_deg <= 0 or pointing_fraction < 0.
    """
    if theta_3db_deg <= 0:
        raise ValueError("theta_3db_deg must be > 0 (got %r)" % (theta_3db_deg,))
    if pointing_fraction < 0:
        raise ValueError("pointing_fraction must be >= 0 (got %r)"
                         % (pointing_fraction,))
    allowed = theta_3db_deg * pointing_fraction
    loss = POINTING_LOSS_COEF * pointing_fraction ** 2
    return {"allowed_error_deg": allowed, "pointing_loss_db": loss}


def gain_over_temperature(receive_gain_db, noise_temp_k):
    """Receive gain-over-temperature figure of merit in dB/K.

    G/T = receive_gain_db - 10 * log10(noise_temp_k).

    Args:
        receive_gain_db: receive antenna gain in dB.
        noise_temp_k: system noise temperature in kelvin, must be > 0.
    Returns:
        float: G/T in dB/K.
    Raises:
        ValueError: if noise_temp_k <= 0.
    """
    if noise_temp_k <= 0:
        raise ValueError("noise_temp_k must be > 0 (got %r)" % (noise_temp_k,))
    return receive_gain_db - 10.0 * math.log10(noise_temp_k)


def antenna_sizing(required_gain_db, freq_hz, eta=ETA_APERTURE_DEFAULT,
                   noise_temp_k=None, pointing_fraction=POINTING_FRACTION):
    """Size the reflector aperture from a required gain, end to end.

    Args:
        required_gain_db: required antenna gain in dB, must be > 0.
        freq_hz: operating frequency in hertz, must be > 0.
        eta: aperture efficiency, must be in (0, 1].
        noise_temp_k: system noise temperature in kelvin for the G/T term;
            None (default) omits the G/T term.
        pointing_fraction: allowed pointing error as a fraction of the
            beamwidth, must be >= 0.
    Returns:
        dict: {"wavelength_m", "diameter_m", "achieved_gain_db",
            "beamwidth_deg", "pointing_allowed_deg", "pointing_loss_db",
            "gain_over_temperature_dbK" (None when noise_temp_k is None),
            "gain_error_db"} where gain_error_db = achieved - required and
            is near zero because the aperture is sized to close the gain.
    Raises:
        ValueError: propagated from the component checks on non-physical
            inputs.
    """
    wave = wavelength(freq_hz)
    diameter = aperture_from_gain(required_gain_db, wave, eta)
    _, achieved_db = gain_from_aperture(diameter, wave, eta)
    beam = half_power_beamwidth(diameter, wave)
    pointing = pointing_budget(beam, pointing_fraction)
    g_over_t = None
    if noise_temp_k is not None:
        g_over_t = gain_over_temperature(achieved_db, noise_temp_k)
    return {
        "wavelength_m": wave,
        "diameter_m": diameter,
        "achieved_gain_db": achieved_db,
        "beamwidth_deg": beam,
        "pointing_allowed_deg": pointing["allowed_error_deg"],
        "pointing_loss_db": pointing["pointing_loss_db"],
        "gain_over_temperature_dbK": g_over_t,
        "gain_error_db": achieved_db - required_gain_db,
    }
