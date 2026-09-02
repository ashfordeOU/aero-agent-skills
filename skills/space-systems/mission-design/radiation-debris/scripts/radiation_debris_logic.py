"""Space radiation and orbital debris environment assessment math.

Deterministic, offline, stdlib-only helpers for a spacecraft mission
design radiation and debris assessment: trapped radiation belt (van
Allen) dose rate versus altitude and inclination with a simplified
AE-8/AP-8 style flux band model, solar particle event fluence with a
power law spectrum, single-event upset rate with the rectangular
parallelepiped (RPP) model from the saturation cross-section and a LET
spectrum, total ionizing dose behind shielding with exponential
attenuation, and the orbital debris collision probability from the
debris flux, spacecraft cross-section, and mission life.

Units: altitude in km, inclination in degrees, dose rate in rad(Si) per
day, mission years in years, shielding in mm of aluminum, cross-section
in cm^2 (device) or m^2 (spacecraft), flux in particles per cm^2 per
day (LET spectrum) or debris particles per m^2 per year.

The models are simplified engineering proxies: they reproduce the shape
of the AE-8/AP-8 and ORDEM/MASTER environment families (two belt
peaks, power law spectra, exponential shielding attenuation, a debris
density peak near 800 km) with closed form expressions that are
deterministic and cheap. They are trend tools for mission design, not
flight qualification data.

Contract exercised by scripts/test_radiation_debris.py.
"""

import math

# ---------------------------------------------------------------------------
# Trapped radiation belts (simplified AE-8/AP-8 style flux bands)
# ---------------------------------------------------------------------------

INNER_BELT_PEAK_KM = 3500.0   # proton belt altitude peak
INNER_BELT_WIDTH_KM = 1200.0  # proton belt half-width
INNER_BELT_PEAK_RATE = 60.0   # rad(Si)/day at the proton belt peak
OUTER_BELT_PEAK_KM = 20000.0  # electron belt altitude peak
OUTER_BELT_WIDTH_KM = 7000.0  # electron belt half-width
OUTER_BELT_PEAK_RATE = 200.0  # rad(Si)/day at the electron belt peak
EQUATORIAL_FACTOR = 0.3       # inclination factor at 0 deg


def inclination_factor(inclination_deg):
    """Return the fraction of orbit time spent in the belt region.

    An equatorial orbit (0 deg) skims the belt edges and sees the
    smallest fraction; a polar orbit (90 deg) crosses the full belt
    structure every orbit. The factor is symmetric about 90 deg
    (cosine squared), so 80 deg and 100 deg give the same value.

    Raises ValueError for an inclination outside [0, 180] degrees.
    """
    if not 0.0 <= inclination_deg <= 180.0:
        raise ValueError("inclination_deg must be in [0, 180], got %r" % (inclination_deg,))
    rad = math.radians(inclination_deg)
    return EQUATORIAL_FACTOR + (1.0 - EQUATORIAL_FACTOR) * (1.0 - math.cos(rad) ** 2)


def trapped_belt_dose_rate(altitude_km, inclination_deg):
    """Return the unshielded trapped belt dose rate in rad(Si)/day.

    Two Gaussian flux bands: a proton belt peaking near 3500 km and an
    electron belt peaking near 20000 km, scaled by the inclination
    factor. At the proton belt peak in a polar orbit the rate is about
    62 rad/day; at 600 km in a near-polar low earth orbit it is a
    fraction of a rad per day, which is why low earth orbit missions
    accumulate their dose slowly.

    Raises ValueError for a negative altitude or an inclination outside
    [0, 180] degrees.
    """
    if altitude_km < 0.0:
        raise ValueError("altitude_km must be >= 0, got %r" % (altitude_km,))
    inner = INNER_BELT_PEAK_RATE * math.exp(
        -(((altitude_km - INNER_BELT_PEAK_KM) / INNER_BELT_WIDTH_KM) ** 2)
    )
    outer = OUTER_BELT_PEAK_RATE * math.exp(
        -(((altitude_km - OUTER_BELT_PEAK_KM) / OUTER_BELT_WIDTH_KM) ** 2)
    )
    return (inner + outer) * inclination_factor(inclination_deg)


# ---------------------------------------------------------------------------
# Solar particle events (simplified integral fluence power law)
# ---------------------------------------------------------------------------

SPE_REF_FLUENCE = 1e8    # protons/cm^2 above the reference energy per year
SPE_REF_ENERGY_MEV = 10.0
SPE_SPECTRAL_INDEX = 3.0


def spe_fluence(energy_mev, mission_years, ref_fluence=SPE_REF_FLUENCE,
                ref_energy_mev=SPE_REF_ENERGY_MEV, spectral_index=SPE_SPECTRAL_INDEX):
    """Return the integral solar particle event fluence in protons/cm^2.

    Integral fluence above the given energy for the mission life:
    Phi = ref_fluence * (E / E_ref)^(-spectral_index) * mission_years.
    The reference is the order of a 1-in-5-year worst-week event above
    10 MeV. A 1-year mission at 10 MeV gives exactly 1e8 protons/cm^2;
    at 100 MeV the fluence drops by a factor of 1000.

    Raises ValueError for a non-positive energy, mission years, or
    spectral index, or a non-positive reference fluence.
    """
    if energy_mev <= 0.0:
        raise ValueError("energy_mev must be > 0, got %r" % (energy_mev,))
    if mission_years <= 0.0:
        raise ValueError("mission_years must be > 0, got %r" % (mission_years,))
    if ref_fluence <= 0.0:
        raise ValueError("ref_fluence must be > 0, got %r" % (ref_fluence,))
    if ref_energy_mev <= 0.0:
        raise ValueError("ref_energy_mev must be > 0, got %r" % (ref_energy_mev,))
    if spectral_index <= 0.0:
        raise ValueError("spectral_index must be > 0, got %r" % (spectral_index,))
    return ref_fluence * (energy_mev / ref_energy_mev) ** (-spectral_index) * mission_years


# ---------------------------------------------------------------------------
# Single-event effects (RPP model, Weibull cross-section fit)
# ---------------------------------------------------------------------------

def rpp_cross_section(let_mev_cm2_mg, sigma_sat, let_threshold, width, shape=1.0):
    """Return the upset cross-section in cm^2 at the given LET.

    Weibull fit of the rectangular parallelepiped (RPP) model:
    sigma = sigma_sat * (1 - exp(-((LET - L0) / W)^S)) for LET above
    the threshold L0, and zero below. With LET exactly at the threshold
    the cross-section is exactly 0.

    Raises ValueError for a non-positive saturation cross-section,
    width, or shape, or a negative threshold.
    """
    if sigma_sat <= 0.0:
        raise ValueError("sigma_sat must be > 0, got %r" % (sigma_sat,))
    if let_threshold < 0.0:
        raise ValueError("let_threshold must be >= 0, got %r" % (let_threshold,))
    if width <= 0.0:
        raise ValueError("width must be > 0, got %r" % (width,))
    if shape <= 0.0:
        raise ValueError("shape must be > 0, got %r" % (shape,))
    if let_mev_cm2_mg <= let_threshold:
        return 0.0
    return sigma_sat * (1.0 - math.exp(-(((let_mev_cm2_mg - let_threshold) / width) ** shape)))


def power_law_let_spectrum(k, exponent, let_min, let_max, bins=100):
    """Return a deterministic LET spectrum as (LET, differential flux) pairs.

    Log-spaced bins from let_min to let_max; each bin carries the
    differential flux k * LET^(-exponent) evaluated at the geometric
    mean LET of the bin, in particles per cm^2 per day per
    (MeV cm^2/mg). Raises ValueError for invalid bounds or parameters.
    """
    if k <= 0.0:
        raise ValueError("k must be > 0, got %r" % (k,))
    if exponent <= 0.0:
        raise ValueError("exponent must be > 0, got %r" % (exponent,))
    if let_min <= 0.0 or let_max <= let_min:
        raise ValueError("need 0 < let_min < let_max, got %r, %r" % (let_min, let_max))
    if bins < 1:
        raise ValueError("bins must be >= 1, got %r" % (bins,))
    log_lo = math.log(let_min)
    log_hi = math.log(let_max)
    spectrum = []
    for i in range(bins):
        l_edge = math.exp(log_lo + (log_hi - log_lo) * i / bins)
        h_edge = math.exp(log_lo + (log_hi - log_lo) * (i + 1) / bins)
        let = math.sqrt(l_edge * h_edge)
        flux = k * let ** (-exponent)
        spectrum.append((let, flux))
    return spectrum


def seu_rate(sigma_sat, let_threshold, width, shape, spectrum):
    """Return the single-event upset rate in upsets per device per day.

    RPP model: sum over the LET spectrum of the Weibull cross-section
    at each LET times the differential flux at that LET. The rate
    scales linearly with the saturation cross-section: doubling
    sigma_sat doubles the rate. A spectrum entirely below the
    threshold gives exactly 0 upsets per day.

    Raises ValueError for invalid device parameters or an empty or
    malformed spectrum.
    """
    if sigma_sat <= 0.0:
        raise ValueError("sigma_sat must be > 0, got %r" % (sigma_sat,))
    if let_threshold < 0.0:
        raise ValueError("let_threshold must be >= 0, got %r" % (let_threshold,))
    if width <= 0.0:
        raise ValueError("width must be > 0, got %r" % (width,))
    if shape <= 0.0:
        raise ValueError("shape must be > 0, got %r" % (shape,))
    if not spectrum:
        raise ValueError("spectrum must not be empty")
    rate = 0.0
    for pair in spectrum:
        let, flux = pair
        sigma = rpp_cross_section(let, sigma_sat, let_threshold, width, shape)
        rate += sigma * flux
    return rate


# ---------------------------------------------------------------------------
# Total ionizing dose versus shielding (exponential attenuation)
# ---------------------------------------------------------------------------

DAYS_PER_YEAR = 365.25
ELECTRON_LAMBDA_MM = 3.0   # 1/e attenuation length, electron component
PROTON_LAMBDA_MM = 60.0    # 1/e attenuation length, proton component
DEFAULT_ELECTRON_FRACTION = 0.7


def tid_after_shielding(dose_rate_rad_day, mission_years, shielding_mm_al,
                        electron_fraction=DEFAULT_ELECTRON_FRACTION,
                        electron_lambda_mm=ELECTRON_LAMBDA_MM,
                        proton_lambda_mm=PROTON_LAMBDA_MM):
    """Return the mission total ionizing dose in krad(Si) behind shielding.

    Two-component exponential attenuation: the electron component
    (default 70 percent of the unshielded dose) is absorbed quickly
    (3 mm aluminum 1/e length), the proton component (30 percent)
    penetrates much further (60 mm 1/e length). The shielded dose is
    always below the unshielded dose and falls monotonically with
    shielding thickness.

    Raises ValueError for a negative dose rate or shielding, a
    non-positive mission life or attenuation length, or an electron
    fraction outside [0, 1].
    """
    if dose_rate_rad_day < 0.0:
        raise ValueError("dose_rate_rad_day must be >= 0, got %r" % (dose_rate_rad_day,))
    if mission_years <= 0.0:
        raise ValueError("mission_years must be > 0, got %r" % (mission_years,))
    if shielding_mm_al < 0.0:
        raise ValueError("shielding_mm_al must be >= 0, got %r" % (shielding_mm_al,))
    if not 0.0 <= electron_fraction <= 1.0:
        raise ValueError("electron_fraction must be in [0, 1], got %r" % (electron_fraction,))
    if electron_lambda_mm <= 0.0 or proton_lambda_mm <= 0.0:
        raise ValueError("attenuation lengths must be > 0")
    unshielded_rad = dose_rate_rad_day * DAYS_PER_YEAR * mission_years
    electron_part = electron_fraction * math.exp(-shielding_mm_al / electron_lambda_mm)
    proton_part = (1.0 - electron_fraction) * math.exp(-shielding_mm_al / proton_lambda_mm)
    return unshielded_rad * (electron_part + proton_part) / 1000.0


def shielding_for_dose_limit(dose_rate_rad_day, mission_years, dose_limit_krad,
                             electron_fraction=DEFAULT_ELECTRON_FRACTION,
                             max_shielding_mm=200.0):
    """Return the minimum aluminum shielding in mm meeting the dose limit.

    Bisection over [0, max_shielding_mm] of tid_after_shielding;
    returns the smallest thickness whose total ionizing dose is at most
    the limit. Returns None when even the maximum shielding cannot
    meet the limit (the proton component floor sits above it).

    Raises ValueError for a non-positive dose limit or mission life, or
    a negative dose rate or maximum shielding.
    """
    if dose_rate_rad_day < 0.0:
        raise ValueError("dose_rate_rad_day must be >= 0, got %r" % (dose_rate_rad_day,))
    if mission_years <= 0.0:
        raise ValueError("mission_years must be > 0, got %r" % (mission_years,))
    if dose_limit_krad <= 0.0:
        raise ValueError("dose_limit_krad must be > 0, got %r" % (dose_limit_krad,))
    if max_shielding_mm <= 0.0:
        raise ValueError("max_shielding_mm must be > 0, got %r" % (max_shielding_mm,))
    if tid_after_shielding(dose_rate_rad_day, mission_years, max_shielding_mm,
                           electron_fraction=electron_fraction) > dose_limit_krad:
        return None
    lo, hi = 0.0, max_shielding_mm
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if tid_after_shielding(dose_rate_rad_day, mission_years, mid,
                               electron_fraction=electron_fraction) <= dose_limit_krad:
            hi = mid
        else:
            lo = mid
    return hi


def dose_verdict(tid_krad, limit_krad):
    """Return the dose margin verdict against the component limit.

    ADEQUATE when the dose sits at least 20 percent below the limit,
    MARGINAL when it is below but within 20 percent, EXCEEDED when the
    dose is at or above the limit. Raises ValueError for a negative
    dose or a non-positive limit.
    """
    if tid_krad < 0.0:
        raise ValueError("tid_krad must be >= 0, got %r" % (tid_krad,))
    if limit_krad <= 0.0:
        raise ValueError("limit_krad must be > 0, got %r" % (limit_krad,))
    margin = (limit_krad - tid_krad) / limit_krad
    if margin <= 0.0:
        return "EXCEEDED"
    if margin < 0.2:
        return "MARGINAL"
    return "ADEQUATE"


# ---------------------------------------------------------------------------
# Orbital debris environment (simplified flux and collision probability)
# ---------------------------------------------------------------------------

DEBRIS_PEAK_ALTITUDE_KM = 850.0
DEBRIS_BAND_WIDTH_KM = 300.0
DEBRIS_PEAK_FLUX = 5e-5          # particles > 1 cm per m^2 per year
DEBRIS_SIZE_INDEX = 2.6          # cumulative size power law exponent


def debris_flux_per_m2_yr(altitude_km, min_size_cm=1.0):
    """Return the debris flux in particles per m^2 per year.

    A Gaussian density band peaking near 850 km (where the catalogued
    debris population is densest) scaled by a power law size
    distribution: flux at size s is flux_at_1cm * (s / 1cm)^(-2.6).
    At the peak altitude for 1 cm particles the flux is exactly 5e-5
    per m^2 per year; at 550 km the band factor is exp(-1), so the flux
    drops by about 63 percent.

    Raises ValueError for a negative altitude or a non-positive size.
    """
    if altitude_km < 0.0:
        raise ValueError("altitude_km must be >= 0, got %r" % (altitude_km,))
    if min_size_cm <= 0.0:
        raise ValueError("min_size_cm must be > 0, got %r" % (min_size_cm,))
    band = math.exp(-(((altitude_km - DEBRIS_PEAK_ALTITUDE_KM) / DEBRIS_BAND_WIDTH_KM) ** 2))
    size_factor = (min_size_cm / 1.0) ** (-DEBRIS_SIZE_INDEX)
    return DEBRIS_PEAK_FLUX * band * size_factor


def collision_probability(flux_per_m2_yr, cross_section_m2, mission_years):
    """Return the debris collision probability over the mission life.

    Poisson statistics: the expected number of collisions is
    lambda = flux * area * time and the probability of at least one
    collision is 1 - exp(-lambda). For a small lambda the probability
    is approximately lambda; a zero mission life or zero cross-section
    gives exactly 0.

    Raises ValueError for a negative flux or cross-section or a
    non-positive mission life.
    """
    if flux_per_m2_yr < 0.0:
        raise ValueError("flux_per_m2_yr must be >= 0, got %r" % (flux_per_m2_yr,))
    if cross_section_m2 < 0.0:
        raise ValueError("cross_section_m2 must be >= 0, got %r" % (cross_section_m2,))
    if mission_years <= 0.0:
        raise ValueError("mission_years must be > 0, got %r" % (mission_years,))
    lam = flux_per_m2_yr * cross_section_m2 * mission_years
    return 1.0 - math.exp(-lam)


def debris_verdict(probability, low_threshold=0.01, high_threshold=0.1):
    """Return the debris risk verdict for the collision probability.

    LOW below the low threshold, MODERATE between the thresholds, HIGH
    at or above the high threshold. Raises ValueError for a probability
    outside [0, 1] or non-positive thresholds.
    """
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0, 1], got %r" % (probability,))
    if low_threshold <= 0.0 or high_threshold <= low_threshold:
        raise ValueError("need 0 < low_threshold < high_threshold")
    if probability >= high_threshold:
        return "HIGH"
    if probability >= low_threshold:
        return "MODERATE"
    return "LOW"


# ---------------------------------------------------------------------------
# Assessment class
# ---------------------------------------------------------------------------

class RadiationDebrisAssessment(object):
    """A mission radiation and debris environment assessment.

    Holds the orbit (altitude, inclination), the mission life, the
    shielding, the device single-event parameters and LET spectrum, and
    the spacecraft debris cross-section; computes the trapped belt dose
    rate, the solar particle event fluence, the total ionizing dose
    behind shielding, the single-event upset rate, the debris collision
    probability, and the dose and debris verdicts.
    """

    def __init__(self, altitude_km, inclination_deg, mission_years,
                 shielding_mm_al, sigma_sat, let_threshold, width, shape,
                 spectrum, cross_section_m2, min_size_cm=1.0,
                 dose_limit_krad=50.0):
        if altitude_km < 0.0:
            raise ValueError("altitude_km must be >= 0, got %r" % (altitude_km,))
        if not 0.0 <= inclination_deg <= 180.0:
            raise ValueError("inclination_deg must be in [0, 180], got %r" % (inclination_deg,))
        if mission_years <= 0.0:
            raise ValueError("mission_years must be > 0, got %r" % (mission_years,))
        if shielding_mm_al < 0.0:
            raise ValueError("shielding_mm_al must be >= 0, got %r" % (shielding_mm_al,))
        if sigma_sat <= 0.0:
            raise ValueError("sigma_sat must be > 0, got %r" % (sigma_sat,))
        if let_threshold < 0.0:
            raise ValueError("let_threshold must be >= 0, got %r" % (let_threshold,))
        if width <= 0.0 or shape <= 0.0:
            raise ValueError("width and shape must be > 0")
        if not spectrum:
            raise ValueError("spectrum must not be empty")
        if cross_section_m2 < 0.0:
            raise ValueError("cross_section_m2 must be >= 0, got %r" % (cross_section_m2,))
        if min_size_cm <= 0.0:
            raise ValueError("min_size_cm must be > 0, got %r" % (min_size_cm,))
        if dose_limit_krad <= 0.0:
            raise ValueError("dose_limit_krad must be > 0, got %r" % (dose_limit_krad,))
        self.altitude_km = float(altitude_km)
        self.inclination_deg = float(inclination_deg)
        self.mission_years = float(mission_years)
        self.shielding_mm_al = float(shielding_mm_al)
        self.sigma_sat = float(sigma_sat)
        self.let_threshold = float(let_threshold)
        self.width = float(width)
        self.shape = float(shape)
        self.spectrum = [(float(a), float(b)) for a, b in spectrum]
        self.cross_section_m2 = float(cross_section_m2)
        self.min_size_cm = float(min_size_cm)
        self.dose_limit_krad = float(dose_limit_krad)

    def dose_rate_rad_day(self):
        """Return the unshielded trapped belt dose rate in rad(Si)/day."""
        return trapped_belt_dose_rate(self.altitude_km, self.inclination_deg)

    def tid_krad(self):
        """Return the mission total ionizing dose in krad(Si) behind shielding."""
        return tid_after_shielding(self.dose_rate_rad_day(), self.mission_years,
                                   self.shielding_mm_al)

    def seu_rate_per_day(self):
        """Return the single-event upset rate in upsets per device per day."""
        return seu_rate(self.sigma_sat, self.let_threshold, self.width,
                        self.shape, self.spectrum)

    def debris_flux_per_m2_yr(self):
        """Return the debris flux in particles per m^2 per year."""
        return debris_flux_per_m2_yr(self.altitude_km, self.min_size_cm)

    def collision_probability(self):
        """Return the debris collision probability over the mission life."""
        return collision_probability(self.debris_flux_per_m2_yr(),
                                     self.cross_section_m2, self.mission_years)

    def dose_verdict(self):
        """Return the dose verdict against the component limit."""
        return dose_verdict(self.tid_krad(), self.dose_limit_krad)

    def debris_verdict(self):
        """Return the debris risk verdict."""
        return debris_verdict(self.collision_probability())

    def report(self):
        """Return a dict summary of the environment assessment."""
        return {
            "altitude_km": self.altitude_km,
            "inclination_deg": self.inclination_deg,
            "mission_years": self.mission_years,
            "shielding_mm_al": self.shielding_mm_al,
            "dose_rate_rad_day": self.dose_rate_rad_day(),
            "tid_krad": self.tid_krad(),
            "dose_limit_krad": self.dose_limit_krad,
            "dose_verdict": self.dose_verdict(),
            "seu_rate_per_day": self.seu_rate_per_day(),
            "debris_flux_per_m2_yr": self.debris_flux_per_m2_yr(),
            "collision_probability": self.collision_probability(),
            "debris_verdict": self.debris_verdict(),
        }
