"""DO-160 section 20 radio frequency susceptibility (RF immunity) math.

Deterministic, offline, stdlib-only helpers for RF susceptibility test
planning per DO-160 (RTCA, EUROCAE twin ED-14): radiated and conducted
immunity levels, field strength from amplifier power, antenna gain, and
distance, dB unit conversions (dBuV/m, dBuA, dBm), free-space power
flux density, amplitude-modulation peak levels, calibration margins,
and CS114 category current-limit steps. All units are SI: field in V/m,
power in W, gain linear, distance in m, frequency in Hz.

Summary reference only; category limit tables must be verified against
the current DO-160 revision before test planning (standards-map.yaml,
brief 06).

Contract exercised by scripts/test_radio_frequency_susceptibility.py.
"""

import math

FREE_SPACE_IMPEDANCE = 377.0  # ohms, plane-wave free space
SPEED_OF_LIGHT = 2.99792458e8  # m/s


def wavelength_from_frequency(frequency_hz):
    """Return the free-space wavelength in m for a frequency in Hz.

    lambda = c / f. Anchor: 1 GHz gives about 0.2998 m. Used to confirm
    the test setup sits in the far field of the radiating antenna.

    Raises ValueError for a non-positive frequency.
    """
    if frequency_hz <= 0:
        raise ValueError("frequency must be > 0, got %r" % (frequency_hz,))
    return SPEED_OF_LIGHT / frequency_hz


def far_field_boundary(antenna_aperture_m, wavelength_m):
    """Return the Fraunhofer far-field distance in m for an antenna.

    R = 2 * D**2 / lambda, with D the largest antenna aperture
    dimension. Beyond R the far-field relation E = sqrt(30 * P * G) / d
    is valid for the RS103 setup. Anchor: a 1 m aperture at 0.3 m
    wavelength gives about 6.667 m.

    Raises ValueError for a negative aperture or non-positive wavelength.
    """
    if antenna_aperture_m < 0:
        raise ValueError("aperture must be >= 0, got %r" % (antenna_aperture_m,))
    if wavelength_m <= 0:
        raise ValueError("wavelength must be > 0, got %r" % (wavelength_m,))
    return 2.0 * antenna_aperture_m * antenna_aperture_m / wavelength_m


def vm_from_dbu_vm(dbu_vm):
    """Return field strength in V/m for a level in dBuV/m.

    E = 10 ** (level / 20) * 1e-6. Anchor: 120 dBuV/m equals 1 V/m.
    """
    return 10.0 ** (dbu_vm / 20.0) * 1e-6


def dbu_vm_from_vm(field_vm):
    """Return the field strength level in dBuV/m for V/m.

    level = 20 * log10(E / 1e-6). Anchor: 1 V/m equals 120 dBuV/m.
    """
    if field_vm < 0:
        raise ValueError("field must be >= 0, got %r" % (field_vm,))
    if field_vm == 0:
        raise ValueError("field must be > 0 to express in dB, got 0")
    return 20.0 * math.log10(field_vm / 1e-6)


def amp_from_dbu_a(dbu_a):
    """Return current in A for a level in dBuA.

    I = 10 ** (level / 20) * 1e-6. Anchor: 120 dBuA equals 1 A.
    """
    return 10.0 ** (dbu_a / 20.0) * 1e-6


def dbu_a_from_amp(current_a):
    """Return the current level in dBuA for A.

    level = 20 * log10(I / 1e-6). Anchor: 1 A equals 120 dBuA.
    """
    if current_a < 0:
        raise ValueError("current must be >= 0, got %r" % (current_a,))
    if current_a == 0:
        raise ValueError("current must be > 0 to express in dB, got 0")
    return 20.0 * math.log10(current_a / 1e-6)


def watt_from_dbm(dbm):
    """Return power in W for a level in dBm.

    P = 10 ** (level / 10) * 1e-3. Anchor: 30 dBm equals 1 W.
    """
    return 10.0 ** (dbm / 10.0) * 1e-3


def dbm_from_watt(power_w):
    """Return the power level in dBm for W.

    level = 10 * log10(P / 1e-3). Anchor: 1 W equals 30 dBm.
    """
    if power_w < 0:
        raise ValueError("power must be >= 0, got %r" % (power_w,))
    if power_w == 0:
        raise ValueError("power must be > 0 to express in dB, got 0")
    return 10.0 * math.log10(power_w / 1e-3)


def gain_db_to_linear(gain_db):
    """Return linear antenna gain for a gain in dBi/dB.

    G = 10 ** (gain_db / 10). Anchor: 3 dB is about 1.9953.
    """
    return 10.0 ** (gain_db / 10.0)


def gain_linear_to_db(gain_linear):
    """Return gain in dB for a linear gain.

    gain_db = 10 * log10(G). Anchor: linear 2.0 is about 3.0103 dB.
    """
    if gain_linear <= 0:
        raise ValueError("linear gain must be > 0, got %r" % (gain_linear,))
    return 10.0 * math.log10(gain_linear)


def field_strength_from_power(power_w, antenna_gain, distance_m):
    """Return far-field strength E in V/m from radiated power.

    E = sqrt(30 * P * G) / d, with P in W, G linear, d in m. This is the
    free-space far-field relation used to size the RS103 radiated
    susceptibility calibration setup. Anchor: 100 W into an isotropic
    radiator at 10 m gives sqrt(3000) / 10, about 5.477 V/m.

    Raises ValueError for negative power, gain, or distance.
    """
    if power_w < 0:
        raise ValueError("power must be >= 0, got %r" % (power_w,))
    if antenna_gain < 0:
        raise ValueError("gain must be >= 0, got %r" % (antenna_gain,))
    if distance_m <= 0:
        raise ValueError("distance must be > 0, got %r" % (distance_m,))
    return math.sqrt(30.0 * power_w * antenna_gain) / distance_m


def power_for_field_strength(field_vm, antenna_gain, distance_m):
    """Return radiated power P in W needed for a field E in V/m.

    Inverting E = sqrt(30 * P * G) / d gives P = E**2 * d**2 / (30 * G).
    Anchor: 5.477 V/m at 10 m with unity gain needs 100 W (round trip).

    Raises ValueError for negative field, gain, or distance.
    """
    if field_vm < 0:
        raise ValueError("field must be >= 0, got %r" % (field_vm,))
    if antenna_gain < 0:
        raise ValueError("gain must be >= 0, got %r" % (antenna_gain,))
    if distance_m <= 0:
        raise ValueError("distance must be > 0, got %r" % (distance_m,))
    if antenna_gain == 0:
        raise ValueError("gain must be > 0 to compute power, got 0")
    return field_vm * field_vm * distance_m * distance_m / (30.0 * antenna_gain)


def power_flux_density(field_vm):
    """Return plane-wave power flux density S in W/m2 for E in V/m.

    S = E**2 / 377. Anchor: 100 V/m gives 26.525 W/m2.
    """
    if field_vm < 0:
        raise ValueError("field must be >= 0, got %r" % (field_vm,))
    return field_vm * field_vm / FREE_SPACE_IMPEDANCE


def field_from_power_flux_density(flux_w_m2):
    """Return field strength E in V/m for flux density S in W/m2.

    E = sqrt(S * 377). Anchor: 26.525 W/m2 gives about 100 V/m.
    """
    if flux_w_m2 < 0:
        raise ValueError("flux must be >= 0, got %r" % (flux_w_m2,))
    return math.sqrt(flux_w_m2 * FREE_SPACE_IMPEDANCE)


def am_peak_field(carrier_field_vm, modulation_depth):
    """Return the instantaneous peak field of an AM-modulated carrier.

    The RS103 modulated test field peaks at E * (1 + m), with m the
    modulation depth (0 to 1). Anchor: 100 V/m at 80 percent depth
    peaks at 180 V/m.

    Raises ValueError when modulation depth is outside [0, 1].
    """
    if carrier_field_vm < 0:
        raise ValueError("carrier field must be >= 0, got %r" % (carrier_field_vm,))
    if not (0.0 <= modulation_depth <= 1.0):
        raise ValueError(
            "modulation depth must be in [0, 1], got %r" % (modulation_depth,)
        )
    return carrier_field_vm * (1.0 + modulation_depth)


def am_average_power(carrier_power_w, modulation_depth):
    """Return average power of an AM-modulated carrier.

    Average power is P * (1 + m**2 / 2). Anchor: 100 W at 80 percent
    depth averages 132 W.

    Raises ValueError when modulation depth is outside [0, 1].
    """
    if carrier_power_w < 0:
        raise ValueError("carrier power must be >= 0, got %r" % (carrier_power_w,))
    if not (0.0 <= modulation_depth <= 1.0):
        raise ValueError(
            "modulation depth must be in [0, 1], got %r" % (modulation_depth,)
        )
    return carrier_power_w * (1.0 + modulation_depth * modulation_depth / 2.0)


def apply_margin_db(power_w, margin_db):
    """Return the power level raised by a calibration margin in dB.

    Calibration margins (for example 6 dB) raise the amplifier power by
    a factor 10 ** (margin_db / 10). Anchor: 100 W with 6 dB gives
    about 398.1 W.
    """
    if power_w < 0:
        raise ValueError("power must be >= 0, got %r" % (power_w,))
    return power_w * 10.0 ** (margin_db / 10.0)


def field_with_margin_db(field_vm, margin_db):
    """Return the field level raised by a calibration margin in dB.

    Field margin uses the 20 log10 convention: E * 10 ** (margin / 20).
    Anchor: 100 V/m with 6 dB gives about 199.5 V/m.
    """
    if field_vm < 0:
        raise ValueError("field must be >= 0, got %r" % (field_vm,))
    return field_vm * 10.0 ** (margin_db / 20.0)


def amplifier_power_with_cable_loss(antenna_power_w, cable_loss_db):
    """Return amplifier output power needed to deliver antenna power.

    Cable and fixture loss L in dB requires P_amp = P_ant * 10 ** (L / 10).
    Anchor: 1500 W at the antenna with 3 dB of cable loss needs 3000 W.
    """
    if antenna_power_w < 0:
        raise ValueError("antenna power must be >= 0, got %r" % (antenna_power_w,))
    return antenna_power_w * 10.0 ** (cable_loss_db / 10.0)


def required_amp_power_for_test(field_vm, distance_m, antenna_gain_db, cable_loss_db, margin_db):
    """Return amplifier power in W for a full RS103 calibration budget.

    Combines the far-field relation, antenna gain, cable loss, and
    calibration margin: P = E**2 * d**2 / (30 * G) * 10**(L/10) *
    10**(M/10), with G linear from antenna_gain_db. This is the
    headline sizing number for a radiated immunity test setup.

    Anchor: 100 V/m at 3 m with 3 dB gain, 3 dB cable loss, and 6 dB
    margin needs about 11970 W.
    """
    if field_vm < 0:
        raise ValueError("field must be >= 0, got %r" % (field_vm,))
    if distance_m <= 0:
        raise ValueError("distance must be > 0, got %r" % (distance_m,))
    gain_linear = gain_db_to_linear(antenna_gain_db)
    base = power_for_field_strength(field_vm, gain_linear, distance_m)
    with_cable = amplifier_power_with_cable_loss(base, cable_loss_db)
    return apply_margin_db(with_cable, margin_db)


# CS114 conducted susceptibility category steps, summary reference only.
# Adjacent categories differ by 10 dBuA; the category A base level is
# published in DO-160 section 20 and must be verified per revision.
_CS114_CATEGORY_OFFSETS = {
    "A": 0.0,
    "B": 10.0,
    "C": 20.0,
    "D": 30.0,
    "E": 40.0,
    "F": 50.0,
    "G": 60.0,
    "H": 70.0,
    "J": 80.0,
}
_CS114_BASE_LIMIT_DBU_A = 55.7  # dBuA, category A base, summary reference only


def cs114_category_offset(category):
    """Return the CS114 current-limit offset in dBuA for a category.

    Category A is the base, each later category steps up 10 dBuA
    (A: 0, B: 10, ..., J: 80 dBuA). Raises ValueError for a category
    not in the published set.
    """
    key = str(category).upper()
    if key not in _CS114_CATEGORY_OFFSETS:
        raise ValueError(
            "CS114 category must be one of %s, got %r"
            % (sorted(_CS114_CATEGORY_OFFSETS), category)
        )
    return _CS114_CATEGORY_OFFSETS[key]


def cs114_limit_dbu_a(category, base_limit_dbu_a=_CS114_BASE_LIMIT_DBU_A):
    """Return the CS114 current limit in dBuA for a category.

    limit = base + offset, with the 10 dBuA category step pattern.
    Summary reference only; verify the published base against the
    current DO-160 revision before test planning.
    """
    return base_limit_dbu_a + cs114_category_offset(category)


def margin_check_dbu(measured_dbu, limit_dbu):
    """Return the immunity margin in dB and the pass verdict.

    margin = limit - measured. Non-negative margin is a pass, negative
    is a fail against the susceptibility limit.
    """
    margin = limit_dbu - measured_dbu
    return margin, margin >= 0


def in_frequency_band(frequency_hz, band_lo_hz, band_hi_hz):
    """Return whether a frequency lies inside a half-open band.

    Includes the low edge, excludes the high edge. Used to confirm a
    test frequency sits inside the RS103 radiated band for the category.
    """
    return band_lo_hz <= frequency_hz < band_hi_hz
