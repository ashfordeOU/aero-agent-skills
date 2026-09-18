"""Application of a paint system by an approved method, to the specified build.

Anchor: ECSS-Q-ST-70-31C application clause -- applying the selected paint
system by a method the specification approves, in enough passes to reach the
specified dry film, inside the recoat interval and inside the environmental
window the material was qualified in. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the method against the methods approved for the paint system and the
   item, because a method nobody qualified does not become acceptable by
   producing a nice-looking film.
2. Convert the specified dry film into the wet film the applicator has to lay
   down, through the material's volume solids.
3. Size the job: passes needed at the method's per-pass build, theoretical
   coverage, and the paint volume the area needs once transfer efficiency is
   taken off.
4. Check the elapsed time since the previous coat against the two-sided recoat
   interval, and the application-area conditions against their window.
5. Close with one disposition and every finding named.
"""

import math

__all__ = [
    "APPLICATION_TOLERANCE",
    "APPROVED_METHODS",
    "METHOD_PER_PASS_DFT_UM",
    "METHOD_TRANSFER_EFFICIENCY",
    "METHODS_FOR_THIN_UNIFORM_FILMS",
    "DEFAULT_APPLICATION_TEMPERATURE_C",
    "DEFAULT_MAX_RELATIVE_HUMIDITY_PCT",
    "DISPOSITIONS",
    "normalize_key",
    "method_per_pass_dft_um",
    "wet_film_thickness_um",
    "passes_required",
    "theoretical_coverage_m2_per_l",
    "paint_volume_required_l",
    "method_findings",
    "recoat_findings",
    "environment_findings",
    "assess_application",
]

# Films are quoted in micrometres and compared against bounds they land on.
APPLICATION_TOLERANCE = 1e-9

APPROVED_METHODS = (
    "conventional-spray",
    "hvlp-spray",
    "airless-spray",
    "brush",
    "roller",
    "dip",
)

# Dry film a single competent pass lays down, in micrometres.
METHOD_PER_PASS_DFT_UM = {
    "conventional-spray": 20.0,
    "hvlp-spray": 25.0,
    "airless-spray": 40.0,
    "brush": 35.0,
    "roller": 30.0,
    "dip": 45.0,
}

# Fraction of the paint leaving the applicator that lands on the item.
METHOD_TRANSFER_EFFICIENCY = {
    "conventional-spray": 0.35,
    "hvlp-spray": 0.65,
    "airless-spray": 0.55,
    "brush": 0.95,
    "roller": 0.90,
    "dip": 0.98,
}

# Methods that can hold a thin, uniform, thermo-optically graded film.
METHODS_FOR_THIN_UNIFORM_FILMS = ("conventional-spray", "hvlp-spray", "airless-spray")

DEFAULT_APPLICATION_TEMPERATURE_C = (15.0, 30.0)
DEFAULT_MAX_RELATIVE_HUMIDITY_PCT = 70.0

DISPOSITIONS = ("compliant", "rework-required", "method-not-approved")


def normalize_key(value, label):
    """Return a trimmed lower-case key, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    return v


def _positive(value, label):
    v = _real(value, label)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def _non_negative(value, label):
    v = _real(value, label)
    if v < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, v))
    return v


def _fraction(value, label):
    v = _positive(value, label)
    if v > 1.0:
        raise ValueError("%s must not exceed 1.0, got %g" % (label, v))
    return v


def method_per_pass_dft_um(method):
    """Return the dry film one pass of this method lays down."""
    key = normalize_key(method, "application method")
    if key not in METHOD_PER_PASS_DFT_UM:
        raise ValueError("application method '%s' is not one of %s"
                         % (key, list(APPROVED_METHODS)))
    return METHOD_PER_PASS_DFT_UM[key]


def wet_film_thickness_um(dft_um, volume_solids_fraction):
    """Return the wet film that dries to the specified dry film."""
    dft = _positive(dft_um, "dft_um")
    solids = _fraction(volume_solids_fraction, "volume_solids_fraction")
    return dft / solids


def passes_required(target_dft_um, per_pass_dft_um):
    """Return how many passes of that build reach the specified dry film."""
    target = _positive(target_dft_um, "target_dft_um")
    per_pass = _positive(per_pass_dft_um, "per_pass_dft_um")
    exact = target / per_pass
    whole = math.floor(exact)
    if math.isclose(exact, whole, rel_tol=0.0, abs_tol=APPLICATION_TOLERANCE):
        return max(1, int(whole))
    return int(whole) + 1


def theoretical_coverage_m2_per_l(dft_um, volume_solids_fraction):
    """Return the area one litre covers at the specified dry film, before losses."""
    dft = _positive(dft_um, "dft_um")
    solids = _fraction(volume_solids_fraction, "volume_solids_fraction")
    return solids * 1000.0 / dft


def paint_volume_required_l(area_m2, dft_um, volume_solids_fraction, transfer_efficiency):
    """Return the paint volume the job needs once transfer losses are taken off."""
    area = _positive(area_m2, "area_m2")
    efficiency = _fraction(transfer_efficiency, "transfer_efficiency")
    coverage = theoretical_coverage_m2_per_l(dft_um, volume_solids_fraction)
    return area / coverage / efficiency


def method_findings(method, requirement):
    """Return the reasons a method is not approved for this item."""
    key = normalize_key(method, "application method")
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    findings = []
    if key not in APPROVED_METHODS:
        return ["application-method-not-recognised"]
    approved = requirement.get("approved_methods")
    if approved is not None:
        if not isinstance(approved, (list, tuple)):
            raise ValueError("approved_methods must be a sequence")
        allowed = {normalize_key(m, "approved method") for m in approved}
        if key not in allowed:
            findings.append("method-not-on-the-approved-list")
    if requirement.get("thermo_optical_surface") and key not in METHODS_FOR_THIN_UNIFORM_FILMS:
        findings.append("method-cannot-hold-a-thermo-optical-film")
    if requirement.get("keep_out_areas") and key == "dip":
        findings.append("dip-cannot-respect-a-keep-out-area")
    return findings


def recoat_findings(elapsed_h, min_interval_h, max_interval_h):
    """Return the recoat-interval findings for the time since the previous coat."""
    elapsed = _non_negative(elapsed_h, "elapsed_h")
    low = _non_negative(min_interval_h, "min_interval_h")
    high = _positive(max_interval_h, "max_interval_h")
    if low >= high:
        raise ValueError("min interval %g is not below max interval %g" % (low, high))
    findings = []
    if elapsed < low and not math.isclose(elapsed, low, rel_tol=0.0,
                                          abs_tol=APPLICATION_TOLERANCE):
        findings.append("recoated-before-the-minimum-interval")
    if elapsed > high and not math.isclose(elapsed, high, rel_tol=0.0,
                                           abs_tol=APPLICATION_TOLERANCE):
        findings.append("recoated-after-the-maximum-interval")
    return findings


def environment_findings(temperature_c, relative_humidity_pct, window=None, max_rh=None):
    """Return the application-area conditions that sit outside their window."""
    temp = _real(temperature_c, "temperature_c")
    humidity = _non_negative(relative_humidity_pct, "relative_humidity_pct")
    if humidity > 100.0:
        raise ValueError("relative_humidity_pct must not exceed 100, got %g" % humidity)
    band = window or DEFAULT_APPLICATION_TEMPERATURE_C
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("window must be a (minimum, maximum) pair")
    low = _real(band[0], "window minimum")
    high = _real(band[1], "window maximum")
    if low >= high:
        raise ValueError("window minimum %g is not below maximum %g" % (low, high))
    ceiling = DEFAULT_MAX_RELATIVE_HUMIDITY_PCT if max_rh is None else _non_negative(
        max_rh, "max_rh")
    findings = []
    if temp < low and not math.isclose(temp, low, rel_tol=0.0, abs_tol=APPLICATION_TOLERANCE):
        findings.append("application-temperature-below-window")
    if temp > high and not math.isclose(temp, high, rel_tol=0.0, abs_tol=APPLICATION_TOLERANCE):
        findings.append("application-temperature-above-window")
    if humidity > ceiling and not math.isclose(humidity, ceiling, rel_tol=0.0,
                                               abs_tol=APPLICATION_TOLERANCE):
        findings.append("application-humidity-over-ceiling")
    return findings


def assess_application(record):
    """Return the application disposition, the wet film and the job sizing."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("method", "target_dft_um", "volume_solids_fraction", "area_m2",
                "temperature_c", "relative_humidity_pct"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    method = normalize_key(record["method"], "application method")
    approval = method_findings(method, record)
    if approval:
        return {
            "disposition": "method-not-approved",
            "findings": approval,
            "wft_um": None,
            "passes": None,
            "volume_l": None,
        }
    per_pass = record.get("per_pass_dft_um", method_per_pass_dft_um(method))
    wft = wet_film_thickness_um(record["target_dft_um"], record["volume_solids_fraction"])
    passes = passes_required(record["target_dft_um"], per_pass)
    efficiency = record.get(
        "transfer_efficiency", METHOD_TRANSFER_EFFICIENCY.get(method, 0.5)
    )
    volume = paint_volume_required_l(
        record["area_m2"], record["target_dft_um"],
        record["volume_solids_fraction"], efficiency,
    )
    findings = []
    if "elapsed_since_previous_coat_h" in record:
        findings.extend(recoat_findings(
            record["elapsed_since_previous_coat_h"],
            record.get("min_recoat_interval_h", 4.0),
            record.get("max_recoat_interval_h", 72.0),
        ))
    findings.extend(environment_findings(
        record["temperature_c"], record["relative_humidity_pct"],
        record.get("temperature_window"), record.get("max_relative_humidity_pct"),
    ))
    return {
        "disposition": "rework-required" if findings else "compliant",
        "findings": findings,
        "wft_um": wft,
        "passes": passes,
        "volume_l": volume,
    }
