#!/usr/bin/env python3
"""ECSS-E-ST-10-04C §9.2.2.3 SEP peak-flux logic (paraphrase).

Pure stdlib, no network. This module is a deterministic paraphrase of
ECSS-E-ST-10-04C clause 9.2.2.3 practice: solar energetic particle
(SEP) peak proton flux, computed with a JPL-type worst-case model, is
used for single event effect (SEE) rate worst-case analyses -- a
different product from the mission-duration integrated fluence of
clause 9.2.2.2 (ESP model, cumulative degradation and total dose).

Peak flux is modelled as an integral flux above a proton energy
threshold, J(>E) = A * (E / E_ref) ** (-gamma), with A and gamma set
per confidence level (illustrative worst-case parameters; higher
confidence level means a larger, more conservative peak flux). Energy
channels, confidence levels, and analysis purposes are validated
against fixed sets; unknown values raise ValueError.
"""

ENERGY_CHANNELS_MEV = (1, 4, 10, 30, 60, 100, 150)

CONFIDENCE_LEVELS = (90, 95, 99)

_ENERGY_REF_MEV = 10.0

_MODEL_PARAMS = {
    90: {"A": 1.0e3, "gamma": 2.4},
    95: {"A": 3.0e3, "gamma": 2.3},
    99: {"A": 1.0e4, "gamma": 2.1},
}

ANALYSIS_PURPOSES = {
    "see-rate-worst-case": True,
    "single-event-upset-worst-case": True,
    "single-event-latchup-worst-case": True,
    "total-fluence-degradation": False,
    "total-ionizing-dose": False,
}

_MAX_PEAK_WINDOW_HOURS = 24.0


def peak_flux_applicable(analysis_purpose):
    """Return whether a JPL-type peak-flux model applies to a purpose.

    Accepts see-rate-worst-case, single-event-upset-worst-case,
    single-event-latchup-worst-case, total-fluence-degradation, and
    total-ionizing-dose (case-insensitive). The first three need peak
    flux (True); the last two need the §9.2.2.2 ESP fluence model
    instead (False). Unknown purposes raise ValueError.
    """
    if not isinstance(analysis_purpose, str):
        raise ValueError(
            "analysis_purpose must be a string, got %r" % (analysis_purpose,)
        )
    key = analysis_purpose.strip().lower()
    if key not in ANALYSIS_PURPOSES:
        raise ValueError(
            "unknown analysis purpose %r; expected one of %s"
            % (analysis_purpose, ", ".join(sorted(ANALYSIS_PURPOSES)))
        )
    return ANALYSIS_PURPOSES[key]


def select_energy_channel(device_see_threshold_mev):
    """Return the smallest standard energy channel covering a device threshold.

    device_see_threshold_mev is the device's SEE-sensitive proton
    energy threshold in MeV; it must be a positive number. Returns the
    smallest value from ENERGY_CHANNELS_MEV that is >= the threshold.
    Raises ValueError for a non-positive threshold or one above the
    highest standard channel (150 MeV).
    """
    if not isinstance(device_see_threshold_mev, (int, float)) or isinstance(
        device_see_threshold_mev, bool
    ):
        raise ValueError(
            "device_see_threshold_mev must be a number, got %r"
            % (device_see_threshold_mev,)
        )
    if device_see_threshold_mev <= 0:
        raise ValueError(
            "device_see_threshold_mev must be positive, got %r"
            % (device_see_threshold_mev,)
        )
    for channel in ENERGY_CHANNELS_MEV:
        if channel >= device_see_threshold_mev:
            return channel
    raise ValueError(
        "device_see_threshold_mev %r exceeds the highest standard channel "
        "(%s MeV); consult the mission RES for an extended-energy model"
        % (device_see_threshold_mev, ENERGY_CHANNELS_MEV[-1])
    )


def integral_peak_flux(confidence_level, energy_threshold_mev):
    """Return the JPL-type worst-case integral peak flux above a threshold.

    confidence_level must be one of CONFIDENCE_LEVELS (90, 95, 99).
    energy_threshold_mev must be a positive number. Returns the
    integral flux above energy_threshold_mev, in protons/cm^2/s/sr,
    from J(>E) = A * (E / E_ref) ** (-gamma) with the A, gamma pair for
    the given confidence level. Raises ValueError for an unsupported
    confidence level or a non-positive threshold.
    """
    if confidence_level not in _MODEL_PARAMS:
        raise ValueError(
            "unsupported confidence_level %r; expected one of %s"
            % (confidence_level, sorted(_MODEL_PARAMS))
        )
    if not isinstance(energy_threshold_mev, (int, float)) or isinstance(
        energy_threshold_mev, bool
    ):
        raise ValueError(
            "energy_threshold_mev must be a number, got %r" % (energy_threshold_mev,)
        )
    if energy_threshold_mev <= 0:
        raise ValueError(
            "energy_threshold_mev must be positive, got %r" % (energy_threshold_mev,)
        )
    params = _MODEL_PARAMS[confidence_level]
    return params["A"] * (energy_threshold_mev / _ENERGY_REF_MEV) ** (-params["gamma"])


def worst_case_window_check(duration_hours):
    """Classify a worst-case analysis window as peak-flux or fluence scope.

    duration_hours is the length of the worst-case analysis window in
    hours; it must be positive. Returns a dict with 'duration_hours'
    and 'window_class': 'short-duration-peak-window' when duration_hours
    is at most 24 hours (the JPL-type peak-flux worst-case window), else
    'exceeds-peak-window-use-fluence-model'. Raises ValueError for a
    non-positive duration.
    """
    if not isinstance(duration_hours, (int, float)) or isinstance(
        duration_hours, bool
    ):
        raise ValueError("duration_hours must be a number, got %r" % (duration_hours,))
    if duration_hours <= 0:
        raise ValueError("duration_hours must be positive, got %r" % (duration_hours,))
    window_class = (
        "short-duration-peak-window"
        if duration_hours <= _MAX_PEAK_WINDOW_HOURS
        else "exceeds-peak-window-use-fluence-model"
    )
    return {"duration_hours": duration_hours, "window_class": window_class}


def peakflux_worst_case_verdict(
    analysis_purpose, confidence_level, device_see_threshold_mev, duration_hours
):
    """Build the overall SEP peak-flux worst-case verdict.

    Combines peak_flux_applicable, select_energy_channel,
    integral_peak_flux, and worst_case_window_check. Returns a dict
    with 'applicable' (bool), 'energy_channel_mev', 'peak_flux',
    'window', and 'status'. When the analysis purpose does not need
    peak flux, 'status' is 'use-sep-fluence-model-9-2-2-2' and
    'energy_channel_mev'/'peak_flux' are None. When the window exceeds
    the short-duration peak-flux scope, 'status' is
    'window-too-long-use-fluence-model'. Otherwise 'status' is
    'peak-flux-worst-case-ready'. Propagates ValueError from any step.
    """
    applicable = peak_flux_applicable(analysis_purpose)
    window = worst_case_window_check(duration_hours)
    if not applicable:
        return {
            "applicable": False,
            "energy_channel_mev": None,
            "peak_flux": None,
            "window": window,
            "status": "use-sep-fluence-model-9-2-2-2",
        }
    channel = select_energy_channel(device_see_threshold_mev)
    flux = integral_peak_flux(confidence_level, channel)
    status = (
        "peak-flux-worst-case-ready"
        if window["window_class"] == "short-duration-peak-window"
        else "window-too-long-use-fluence-model"
    )
    return {
        "applicable": True,
        "energy_channel_mev": channel,
        "peak_flux": flux,
        "window": window,
        "status": status,
    }


if __name__ == "__main__":
    import doctest

    doctest.testmod()
