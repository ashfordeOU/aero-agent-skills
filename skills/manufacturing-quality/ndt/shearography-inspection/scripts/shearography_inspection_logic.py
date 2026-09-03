"""Shearography inspection logic for the shearography-inspection NDT leaf.

Pure Python stdlib, deterministic, offline.

Unit conventions (documented in the SKILL body):
- wavelength in nm, shear distance in mm, phase in radians.
- The phase-to-strain relation is delta_phi = (4 * pi / lambda) * shear *
  strain_gradient with lambda the laser wavelength and shear the lateral
  shear distance in the SAME length unit as the gradient denominator; the
  module converts mm and nm to meters consistently, so the returned strain
  is the dimensionless out-of-plane displacement gradient d(w)/dx, which
  for the worked example (0.5 rad, 5 mm shear, 532 nm) evaluates to about
  4.23e-6, i.e. about 4.23 micron/m (1 micron/m = 1e-6 strain).
- Load steps: vacuum delta pressure in mbar keyed by laminate thickness in
  mm, thermal temperature rise in deg C, vibration frequency band index in
  Hz. All values are documented TYPICAL values for aerospace laminates;
  the approved NDT procedure governs the real inspection.

Standards: AS9100 referenced, not reproduced (STANDARDS-REF).
"""

import math

# Module constants (documented typical values; input can override).
LASER_WAVELENGTH_NM = 532.0   # typical frequency-doubled Nd:YAG laser
NOISE_FLOOR_PHASE_RAD = 0.1   # typical phase noise floor in radians
MIN_SNR = 3.0                 # defect signal must exceed noise by this factor
COVERAGE_MIN = 0.85           # part fraction that must carry valid phase data
SHEAR_DIVISOR = 2.0           # typical rule: shear ~ half the min defect size
REVIEW_BAND = 0.2             # disposition review band fraction of the limit
TYPICAL_LOAD_STEPS = {
    "vacuum": {2.0: 20.0, 6.0: 40.0, 12.0: 60.0},
    "thermal": 5.0,
    "vibration": 30.0,
}


def _require_finite(*values):
    """Raise ValueError when any value is non-finite (NaN or infinite)."""
    for value in values:
        if not math.isfinite(value):
            raise ValueError("non-finite value is not physical: %r" % (value,))


def _require_positive(value, name):
    """Raise ValueError when a physically positive quantity is not positive."""
    _require_finite(value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def strain_from_phase(phase_rad, shear_mm, wavelength_nm=LASER_WAVELENGTH_NM):
    """Relative strain (m/m) implied by a measured shearography phase.

    strain = phase * wavelength_nm * 1e-9 / (4 * pi * shear_mm * 1e-3)
    from delta_phi = (4 * pi / lambda) * shear * strain_gradient.
    Raises ValueError on non-positive shear or non-finite inputs.
    """
    _require_finite(phase_rad, shear_mm, wavelength_nm)
    if wavelength_nm <= 0.0:
        raise ValueError("wavelength must be positive, got %r" % (wavelength_nm,))
    _require_positive(shear_mm, "shear_mm")
    return phase_rad * wavelength_nm * 1e-9 / (4.0 * math.pi * shear_mm * 1e-3)


def phase_for_strain(strain, shear_mm, wavelength_nm=LASER_WAVELENGTH_NM):
    """Phase in radians implied by a relative strain (inverse conversion).

    Inverse of strain_from_phase; round-trip identity holds within float
    precision (tested within 1e-12). Raises ValueError on non-positive
    shear or non-finite inputs.
    """
    _require_finite(strain, shear_mm, wavelength_nm)
    if wavelength_nm <= 0.0:
        raise ValueError("wavelength must be positive, got %r" % (wavelength_nm,))
    _require_positive(shear_mm, "shear_mm")
    return strain * 4.0 * math.pi * shear_mm * 1e-3 / (wavelength_nm * 1e-9)


def min_detectable_strain(noise_floor_rad, shear_mm,
                          wavelength_nm=LASER_WAVELENGTH_NM):
    """Minimum detectable relative strain for the given noise floor.

    MIN_SNR times the single-frame noise strain of the same setup:
    strain = MIN_SNR * noise_floor * wavelength / (4 * pi * shear).
    Raises ValueError on non-positive shear, negative noise floor, or
    non-finite inputs.
    """
    _require_finite(noise_floor_rad, shear_mm, wavelength_nm)
    if noise_floor_rad < 0.0:
        raise ValueError("noise floor must be non-negative, got %r"
                         % (noise_floor_rad,))
    if wavelength_nm <= 0.0:
        raise ValueError("wavelength must be positive, got %r" % (wavelength_nm,))
    _require_positive(shear_mm, "shear_mm")
    single_frame = noise_floor_rad * wavelength_nm * 1e-9 \
        / (4.0 * math.pi * shear_mm * 1e-3)
    return MIN_SNR * single_frame


def shear_for_defect(defect_size_mm):
    """Shear distance (mm) for a minimum defect size of interest.

    shear = defect_size_mm / SHEAR_DIVISOR (typical rule: shear about half
    the minimum defect size). Raises ValueError on non-positive defect.
    """
    _require_positive(defect_size_mm, "defect_size_mm")
    return defect_size_mm / SHEAR_DIVISOR


def select_load(part_thickness_mm, load_type):
    """Typical load step value for a laminate thickness and load type.

    vacuum: linear interpolation (and edge extrapolation) over the
    TYPICAL_LOAD_STEPS vacuum thickness breakpoints (mm -> mbar).
    thermal: typical temperature rise in deg C (constant typical value).
    vibration: typical frequency band index in Hz (constant typical value,
    documented 100-1000 Hz sweep).
    Raises ValueError on non-positive thickness, unknown load_type, or
    non-finite thickness.
    """
    _require_positive(part_thickness_mm, "part_thickness_mm")
    if load_type not in TYPICAL_LOAD_STEPS:
        raise ValueError("unknown load_type %r, expected one of %s"
                         % (load_type, sorted(TYPICAL_LOAD_STEPS)))
    entry = TYPICAL_LOAD_STEPS[load_type]
    if not isinstance(entry, dict):
        return float(entry)
    thicknesses = sorted(entry)
    if part_thickness_mm <= thicknesses[0]:
        lo_t, hi_t = thicknesses[0], thicknesses[1]
        slope = (entry[hi_t] - entry[lo_t]) / (hi_t - lo_t)
        return entry[lo_t] + slope * (part_thickness_mm - lo_t)
    if part_thickness_mm >= thicknesses[-1]:
        lo_t, hi_t = thicknesses[-2], thicknesses[-1]
        slope = (entry[hi_t] - entry[lo_t]) / (hi_t - lo_t)
        return entry[hi_t] + slope * (part_thickness_mm - hi_t)
    for lo_t, hi_t in zip(thicknesses, thicknesses[1:]):
        if lo_t <= part_thickness_mm <= hi_t:
            slope = (entry[hi_t] - entry[lo_t]) / (hi_t - lo_t)
            return entry[lo_t] + slope * (part_thickness_mm - lo_t)
    raise AssertionError("unreachable interpolation state")


def scan_plan(part_area_m2, fov_area_m2, overlap):
    """Scan plan passes and overlap area for a part and a field of view.

    passes = ceil(part_area_m2 / (fov_area_m2 * (1 - overlap))); the
    overlap_area is the redundant imaged area, passes * fov_area * overlap.
    Raises ValueError on non-positive areas, overlap outside [0, 0.95], or
    non-finite inputs.
    """
    _require_finite(part_area_m2, fov_area_m2, overlap)
    _require_positive(part_area_m2, "part_area_m2")
    _require_positive(fov_area_m2, "fov_area_m2")
    if overlap < 0.0 or overlap > 0.95:
        raise ValueError("overlap must be within [0, 0.95], got %r" % (overlap,))
    passes = int(math.ceil(part_area_m2 / (fov_area_m2 * (1.0 - overlap))))
    return {"passes": passes, "overlap_area": passes * fov_area_m2 * overlap}


def anomaly_disposition(anomaly_size_mm, allow_size_mm, snr):
    """Disposition verdict for a measured anomaly against an allowable size.

    Verdict rules:
    - reject when anomaly_size_mm >= allow_size_mm * (1 + REVIEW_BAND), the
      anomaly clearly exceeds the allowable beyond the review band;
    - review when the anomaly exceeds the allowable but stays within the
      REVIEW_BAND (20%) above the limit, or when snr < MIN_SNR;
    - accept when anomaly_size_mm <= allow_size_mm and snr >= MIN_SNR.
    Returns {"verdict": ..., "reasons": [...]}. Raises ValueError on
    negative anomaly size, non-positive allowable size, negative snr, or
    non-finite inputs.
    """
    _require_finite(anomaly_size_mm, allow_size_mm, snr)
    if anomaly_size_mm < 0.0:
        raise ValueError("anomaly size must be non-negative, got %r"
                         % (anomaly_size_mm,))
    _require_positive(allow_size_mm, "allow_size_mm")
    if snr < 0.0:
        raise ValueError("snr must be non-negative, got %r" % (snr,))
    band_limit = allow_size_mm * (1.0 + REVIEW_BAND)
    reasons = []
    if anomaly_size_mm >= band_limit:
        reasons.append("anomaly %g mm is at or above %g mm, the allowable "
                       "plus the %g review band" % (anomaly_size_mm,
                                                    band_limit, REVIEW_BAND))
        return {"verdict": "reject", "reasons": reasons}
    if anomaly_size_mm > allow_size_mm:
        reasons.append("anomaly %g mm exceeds the allowable %g mm but lies "
                       "within the %g review band" % (anomaly_size_mm,
                                                      allow_size_mm,
                                                      REVIEW_BAND))
        if snr < MIN_SNR:
            reasons.append("snr %g is below MIN_SNR %g"
                           % (snr, MIN_SNR))
        return {"verdict": "review", "reasons": reasons}
    if snr < MIN_SNR:
        reasons.append("anomaly %g mm is within the allowable %g mm but snr "
                       "%g is below MIN_SNR %g" % (anomaly_size_mm,
                                                   allow_size_mm, snr,
                                                   MIN_SNR))
        return {"verdict": "review", "reasons": reasons}
    reasons.append("anomaly %g mm is within the allowable %g mm and snr %g "
                   "meets MIN_SNR %g" % (anomaly_size_mm, allow_size_mm,
                                         snr, MIN_SNR))
    return {"verdict": "accept", "reasons": reasons}


def summarize(part_thickness_mm, part_area_m2, fov_area_m2, overlap,
              min_defect_mm, load_type, phase_rad, anomaly_size_mm,
              allow_size_mm, snr, wavelength_nm=LASER_WAVELENGTH_NM,
              noise_floor_rad=NOISE_FLOOR_PHASE_RAD):
    """Full planning summary for the SKILL worked example.

    Returns the shear distance, min detectable strain, load step, scan
    plan with the COVERAGE_MIN check, the anomaly strain estimate, and the
    disposition verdict in one dict. Raises ValueError via the underlying
    model functions on non-physical inputs.
    """
    _require_finite(part_thickness_mm, part_area_m2, fov_area_m2, overlap,
                    min_defect_mm, phase_rad, anomaly_size_mm,
                    allow_size_mm, snr, wavelength_nm, noise_floor_rad)
    shear_mm = shear_for_defect(min_defect_mm)
    load_value = select_load(part_thickness_mm, load_type)
    plan = scan_plan(part_area_m2, fov_area_m2, overlap)
    covered_area = plan["passes"] * fov_area_m2 * (1.0 - overlap)
    coverage_ok = min(1.0, covered_area / part_area_m2) >= COVERAGE_MIN
    min_detect = min_detectable_strain(noise_floor_rad, shear_mm,
                                       wavelength_nm)
    anomaly_strain = strain_from_phase(phase_rad, shear_mm, wavelength_nm)
    disposition = anomaly_disposition(anomaly_size_mm, allow_size_mm, snr)
    return {
        "shear_mm": shear_mm,
        "min_detectable_strain": min_detect,
        "load_value": load_value,
        "load_type": load_type,
        "passes": plan["passes"],
        "overlap_area": plan["overlap_area"],
        "coverage_ok": coverage_ok,
        "anomaly_strain": anomaly_strain,
        "verdict": disposition["verdict"],
        "reasons": disposition["reasons"],
    }
