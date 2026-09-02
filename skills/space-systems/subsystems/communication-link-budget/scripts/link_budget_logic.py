"""Spacecraft communications link budget (Friis equation), pure stdlib.

One units convention per quantity, stated once:
- distance: meters (m); frequency: hertz (Hz); c = 299792458 m/s
- power and EIRP: dBW; gains and losses: dB (positive losses subtract)
- noise temperature: kelvin (K); Boltzmann k = 1.380649e-23 J/K
- data rate: bits per second (bps); C/N0: dB-Hz; Eb/N0 and margin: dB

The chain follows the classic link budget: free-space path loss,
EIRP, received power, carrier-to-noise density ratio, and the margin
of Eb/N0 against the required value at the data rate. Non-positive
physical inputs raise ValueError with a clear message; there is no
Watt/dBW mixing anywhere (all power quantities are dBW).
"""

import math

C = 299792458.0          # speed of light, m/s
BOLTZMANN = 1.380649e-23  # J/K
K_DB = 228.6             # 10*log10(1/k) with k in J/K, referenced to 1 K


def free_space_path_loss(distance_m, freq_hz):
    """Free-space path loss in dB: L_fs = 20*log10(4*pi*d/lambda), lambda = c/f.

    Args:
        distance_m: slant range in meters, must be > 0.
        freq_hz: carrier frequency in hertz, must be > 0.
    Returns:
        float: path loss in dB.
    Raises:
        ValueError: if distance_m <= 0 or freq_hz <= 0.
    """
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0 (got %r)" % (distance_m,))
    if freq_hz <= 0:
        raise ValueError("freq_hz must be > 0 (got %r)" % (freq_hz,))
    wavelength = C / freq_hz
    return 20.0 * math.log10(4.0 * math.pi * distance_m / wavelength)


def eirp_dbw(power_dbw, gain_db):
    """Equivalent isotropic radiated power in dBW: EIRP = power + gain."""
    return power_dbw + gain_db


def received_power_dbw(eirp_dbw, rx_gain_db, path_loss_db, other_losses_db=0.0):
    """Received power in dBW: Pr = EIRP + Gr - L_fs - L_other.

    Args:
        eirp_dbw: transmitter EIRP in dBW.
        rx_gain_db: receiver antenna gain in dB.
        path_loss_db: free-space path loss in dB (positive).
        other_losses_db: additional positive losses in dB (default 0.0).
    Returns:
        float: received power in dBW.
    """
    return eirp_dbw + rx_gain_db - path_loss_db - other_losses_db


def cno_db_hz(pr_dbw, noise_temp_k):
    """Carrier-to-noise density ratio in dB-Hz: C/N0 = Pr + 228.6 - 10*log10(T).

    Args:
        pr_dbw: received power in dBW.
        noise_temp_k: system noise temperature in kelvin, must be > 0.
    Returns:
        float: C/N0 in dB-Hz.
    Raises:
        ValueError: if noise_temp_k <= 0.
    """
    if noise_temp_k <= 0:
        raise ValueError("noise_temp_k must be > 0 (got %r)" % (noise_temp_k,))
    return pr_dbw + K_DB - 10.0 * math.log10(noise_temp_k)


def link_margin(cno_db_hz, data_rate_bps, required_ebno_db):
    """Link margin from C/N0, data rate, and required Eb/N0.

    Eb/N0 = C/N0 - 10*log10(R); margin = Eb/N0 - required.

    Args:
        cno_db_hz: carrier-to-noise density ratio in dB-Hz.
        data_rate_bps: bit rate in bits per second, must be > 0.
        required_ebno_db: required Eb/N0 in dB (modulation and coding
            threshold from the link design).
    Returns:
        dict: {"ebno_db": float, "margin_db": float, "ok": bool}
            where ok is True when margin_db >= 0.
    Raises:
        ValueError: if data_rate_bps <= 0.
    """
    if data_rate_bps <= 0:
        raise ValueError("data_rate_bps must be > 0 (got %r)" % (data_rate_bps,))
    ebno = cno_db_hz - 10.0 * math.log10(data_rate_bps)
    margin = ebno - required_ebno_db
    return {"ebno_db": ebno, "margin_db": margin, "ok": margin >= 0.0}
