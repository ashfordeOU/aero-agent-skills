"""Radiation environment definition for a space-material degradation test.

Anchor: ECSS-Q-ST-70-06C, environment clause -- turning a predicted mission
into the numbers an irradiation campaign is specified with: a differential
particle spectrum, the integrated flux and fluence it implies over the mission
phases, and the ultraviolet dose expressed in equivalent sun hours.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate a differential particle spectrum: strictly increasing energies,
   non-negative differential flux, at least two tabulated points.
2. Integrate the spectrum over an energy window by the trapezoidal rule, with
   the window edges interpolated inside the bins they fall in, to obtain the
   integral flux above (or between) the energies of interest.
3. Accumulate the mission across its phases: each phase carries its own
   duration, exposed duty fraction, spectrum scaling and illuminated fraction.
4. Convert the illuminated time into equivalent sun hours at the declared
   solar ultraviolet intensity, so an eclipsed orbit is not charged for its
   shadow time.
5. Compare the energy window the facility can produce with the window the
   mission spectrum occupies and report the uncovered part.
6. Return the specification the campaign is written against, with findings.
"""

import math

__all__ = [
    "SECONDS_PER_YEAR",
    "SOLAR_UV_IRRADIANCE_W_M2",
    "SPECTRUM_COVERAGE_TOLERANCE",
    "validate_spectrum",
    "differential_flux_at",
    "integral_flux",
    "energy_window",
    "phase_particle_fluence",
    "phase_uv_dose_esh",
    "uv_dose_from_irradiance",
    "coverage_findings",
    "define_environment",
]

SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0

# Reference ultraviolet content of the air-mass-zero solar spectrum below
# 400 nm, used as the denominator of an equivalent sun hour.
SOLAR_UV_IRRADIANCE_W_M2 = 118.0

# Energies agree to this relative tolerance before a coverage shortfall is
# raised; a facility limit quoted to the same figure is not a shortfall.
SPECTRUM_COVERAGE_TOLERANCE = 1e-9


def _real(value, label, allow_zero=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _fraction(value, label):
    number = _real(value, label)
    if number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return number


def validate_spectrum(points):
    """Return the differential spectrum as a list of (energy_mev, flux) floats."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("spectrum needs at least two (energy_mev, differential_flux) points")
    cleaned = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("spectrum point %d must be a (energy_mev, flux) pair" % index)
        energy = _real(point[0], "spectrum energy at index %d" % index, allow_zero=False)
        flux = _real(point[1], "spectrum flux at index %d" % index)
        if cleaned and energy <= cleaned[-1][0]:
            raise ValueError(
                "spectrum energies must strictly increase; %g follows %g"
                % (energy, cleaned[-1][0])
            )
        cleaned.append((energy, flux))
    if all(flux == 0.0 for _, flux in cleaned):
        raise ValueError("spectrum carries no flux at any tabulated energy")
    return cleaned


def energy_window(spectrum):
    """Return the (lowest, highest) tabulated energy of the spectrum in MeV."""
    cleaned = validate_spectrum(spectrum)
    return (cleaned[0][0], cleaned[-1][0])


def differential_flux_at(spectrum, energy_mev):
    """Return the differential flux at an energy inside the tabulated window."""
    cleaned = validate_spectrum(spectrum)
    energy = _real(energy_mev, "energy_mev", allow_zero=False)
    low, high = cleaned[0][0], cleaned[-1][0]
    if energy < low or energy > high:
        raise ValueError(
            "energy %g MeV lies outside the tabulated window [%g, %g]" % (energy, low, high)
        )
    for (e0, f0), (e1, f1) in zip(cleaned, cleaned[1:]):
        if e0 <= energy <= e1:
            if e1 == e0:
                return f0
            weight = (energy - e0) / (e1 - e0)
            return f0 + weight * (f1 - f0)
    return cleaned[-1][1]


def integral_flux(spectrum, e_min=None, e_max=None):
    """Return the integral flux over an energy window, per cm^2 per second."""
    cleaned = validate_spectrum(spectrum)
    low, high = cleaned[0][0], cleaned[-1][0]
    start = low if e_min is None else _real(e_min, "e_min", allow_zero=False)
    stop = high if e_max is None else _real(e_max, "e_max", allow_zero=False)
    if start < low or stop > high:
        raise ValueError(
            "integration window [%g, %g] leaves the tabulated window [%g, %g]"
            % (start, stop, low, high)
        )
    if start > stop:
        raise ValueError("e_min %g exceeds e_max %g" % (start, stop))
    if start == stop:
        return 0.0
    nodes = [start]
    for energy, _flux in cleaned:
        if start < energy < stop:
            nodes.append(energy)
    nodes.append(stop)
    total = 0.0
    for a, b in zip(nodes, nodes[1:]):
        fa = differential_flux_at(cleaned, a)
        fb = differential_flux_at(cleaned, b)
        total += 0.5 * (fa + fb) * (b - a)
    return total


def phase_particle_fluence(spectrum, years, duty_fraction=1.0, scaling=1.0,
                           e_min=None, e_max=None):
    """Return the particle fluence accumulated in one mission phase."""
    duration = _real(years, "years", allow_zero=False)
    duty = _fraction(duty_fraction, "duty_fraction")
    factor = _real(scaling, "scaling", allow_zero=False)
    flux = integral_flux(spectrum, e_min, e_max)
    return flux * factor * duty * duration * SECONDS_PER_YEAR


def uv_dose_from_irradiance(irradiance_w_m2, hours):
    """Return the equivalent sun hours delivered by a measured UV irradiance."""
    irradiance = _real(irradiance_w_m2, "irradiance_w_m2")
    duration = _real(hours, "hours")
    return irradiance * duration / SOLAR_UV_IRRADIANCE_W_M2


def phase_uv_dose_esh(sun_fraction, years, intensity_suns=1.0):
    """Return the equivalent sun hours a mission phase delivers."""
    fraction = _fraction(sun_fraction, "sun_fraction")
    duration = _real(years, "years", allow_zero=False)
    intensity = _real(intensity_suns, "intensity_suns", allow_zero=False)
    return fraction * intensity * duration * SECONDS_PER_YEAR / 3600.0


def coverage_findings(facility_window, mission_window):
    """Return the findings raised when a facility cannot span the mission window."""
    for label, window in (("facility_window", facility_window),
                          ("mission_window", mission_window)):
        if not isinstance(window, (list, tuple)) or len(window) != 2:
            raise ValueError("%s must be an (e_low, e_high) pair" % label)
    f_low = _real(facility_window[0], "facility e_low", allow_zero=False)
    f_high = _real(facility_window[1], "facility e_high", allow_zero=False)
    m_low = _real(mission_window[0], "mission e_low", allow_zero=False)
    m_high = _real(mission_window[1], "mission e_high", allow_zero=False)
    if f_low > f_high:
        raise ValueError("facility window is inverted")
    if m_low > m_high:
        raise ValueError("mission window is inverted")
    findings = []
    if f_low > m_low and not math.isclose(
        f_low, m_low, rel_tol=SPECTRUM_COVERAGE_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "facility starts at %.4g MeV, mission spectrum starts at %.4g MeV" % (f_low, m_low)
        )
    if f_high < m_high and not math.isclose(
        f_high, m_high, rel_tol=SPECTRUM_COVERAGE_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "facility stops at %.4g MeV, mission spectrum reaches %.4g MeV" % (f_high, m_high)
        )
    return findings


def define_environment(spec):
    """Build the environment definition an irradiation campaign is written to.

    spec keys: spectrum, phases (each with years and optional duty_fraction,
    scaling, sun_fraction, intensity_suns), optional e_min, e_max,
    facility_window.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("spectrum", "phases"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    phases = spec["phases"]
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("spec['phases'] must be a non-empty sequence")
    spectrum = validate_spectrum(spec["spectrum"])
    e_min = spec.get("e_min")
    e_max = spec.get("e_max")
    records = []
    total_fluence = 0.0
    total_esh = 0.0
    total_years = 0.0
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict) or "years" not in phase:
            raise ValueError("phase %d must be a mapping carrying 'years'" % index)
        fluence = phase_particle_fluence(
            spectrum,
            phase["years"],
            phase.get("duty_fraction", 1.0),
            phase.get("scaling", 1.0),
            e_min,
            e_max,
        )
        esh = phase_uv_dose_esh(
            phase.get("sun_fraction", 0.0),
            phase["years"],
            phase.get("intensity_suns", 1.0),
        )
        records.append(
            {
                "name": phase.get("name", "phase-%d" % (index + 1)),
                "years": float(phase["years"]),
                "particle_fluence": fluence,
                "uv_dose_esh": esh,
            }
        )
        total_fluence += fluence
        total_esh += esh
        total_years += float(phase["years"])
    window = energy_window(spectrum)
    findings = []
    if spec.get("facility_window") is not None:
        findings.extend(coverage_findings(spec["facility_window"], window))
    if total_fluence == 0.0:
        findings.append("integrated mission fluence is zero over the requested energy window")
    if total_esh == 0.0:
        findings.append("no mission phase is illuminated; no ultraviolet exposure is defined")
    return {
        "phases": records,
        "mission_years": total_years,
        "integral_flux": integral_flux(spectrum, e_min, e_max),
        "particle_fluence": total_fluence,
        "uv_dose_esh": total_esh,
        "energy_window_mev": window,
        "findings": findings,
        "definition_complete": not findings,
    }
