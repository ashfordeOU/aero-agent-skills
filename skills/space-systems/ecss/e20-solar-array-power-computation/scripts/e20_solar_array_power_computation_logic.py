"""ECSS-E-ST-20C clause 5.5.3 -- solar array power computation logic.

Deterministic, offline, stdlib-only helpers that predict solar array output
from cell-level current-voltage measurements taken under the photovoltaic
assembly standard. The procedure is a paraphrase of the clause intent; no
standard text is reproduced here.

Chain in one line: validate the measured record and its provenance, screen
it on fill factor, correct the maximum-power point to the operating
temperature / solar distance / incidence angle, apply particle-fluence and
optical retention, assemble series-parallel sections, then compare the
predicted power against the demand.
"""

import math

REFERENCE_TEMPERATURE_C = 28.0
REFERENCE_IRRADIANCE_W_M2 = 1367.0
REFERENCE_FLUENCE_1MEV_E_CM2 = 1.0e13
FILL_FACTOR_BAND = (0.55, 0.92)

UNCATEGORIZED_PROVENANCE = "uncategorized-provenance"

MEASURED_PROVENANCE_WEIGHTS = {
    "assembly-measured": 1.00,
    "coupon-measured": 0.98,
    "lot-sample-measured": 0.96,
}

UNTRACEABLE_SOURCES = frozenset(
    {"catalogue-datasheet", "analytical-estimate", "heritage-assumption"}
)

DEFAULT_SECTION_LOSSES = {
    "string_mismatch": 0.02,
    "interconnect": 0.01,
    "harness": 0.015,
    "blocking_diode_v": 0.75,
}

DEFAULT_CURRENT_TEMP_COEFF_PER_C = 4.6e-4
DEFAULT_VOLTAGE_TEMP_COEFF_PER_C = -2.2e-3


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _require_fraction(value, label):
    frac = _require_number(value, label)
    if not 0.0 <= frac < 1.0:
        raise ValueError("%s must be in [0, 1), got %r" % (label, frac))
    return frac


def categorize_provenance(source):
    """Map a measurement source onto a provenance category.

    A traceable measurement keeps its own category name; a datasheet,
    estimate or heritage value is categorized as untraceable. An unknown
    token is an input error, not a category.
    """
    if not isinstance(source, str) or not source.strip():
        raise ValueError("provenance source must be a non-empty string")
    token = source.strip().lower()
    if token in MEASURED_PROVENANCE_WEIGHTS:
        return token
    if token in UNTRACEABLE_SOURCES:
        return UNCATEGORIZED_PROVENANCE
    raise ValueError("unknown provenance source %r" % (source,))


def provenance_weight(category):
    """Confidence weight of a traceable provenance category."""
    if category == UNCATEGORIZED_PROVENANCE:
        raise ValueError(
            "untraceable provenance carries no confidence weight; "
            "the record is not admissible for a clause 5.5.3 prediction"
        )
    if category not in MEASURED_PROVENANCE_WEIGHTS:
        raise ValueError("unknown provenance category %r" % (category,))
    return MEASURED_PROVENANCE_WEIGHTS[category]


def fill_factor(record):
    """Fill factor of a current-voltage record (dimensionless)."""
    isc = _require_number(record.get("isc_a", 0.0), "isc_a")
    voc = _require_number(record.get("voc_v", 0.0), "voc_v")
    imp = _require_number(record.get("imp_a", 0.0), "imp_a")
    vmp = _require_number(record.get("vmp_v", 0.0), "vmp_v")
    if isc <= 0.0 or voc <= 0.0:
        raise ValueError("isc_a and voc_v must both be > 0 to form a fill factor")
    return (imp * vmp) / (isc * voc)


def validate_cell_measurement(record):
    """Normalise one measured cell record, raising ValueError on bad input."""
    if not isinstance(record, dict):
        raise ValueError("measurement must be a mapping, got %r" % (type(record).__name__,))
    cell_id = record.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("cell_id must be a non-empty string")
    isc = _require_number(record.get("isc_a", 0.0), "isc_a")
    voc = _require_number(record.get("voc_v", 0.0), "voc_v")
    imp = _require_number(record.get("imp_a", 0.0), "imp_a")
    vmp = _require_number(record.get("vmp_v", 0.0), "vmp_v")
    if isc <= 0.0:
        raise ValueError("cell %r: isc_a must be > 0" % cell_id)
    if voc <= 0.0:
        raise ValueError("cell %r: voc_v must be > 0" % cell_id)
    if not 0.0 < imp < isc:
        raise ValueError("cell %r: imp_a must satisfy 0 < imp_a < isc_a" % cell_id)
    if not 0.0 < vmp < voc:
        raise ValueError("cell %r: vmp_v must satisfy 0 < vmp_v < voc_v" % cell_id)
    factor = fill_factor(record)
    low, high = FILL_FACTOR_BAND
    if not low <= factor <= high:
        raise ValueError(
            "cell %r: fill factor %.4f outside the plausible band %.2f-%.2f; "
            "the record mixes conditions or cell types" % (cell_id, factor, low, high)
        )
    category = categorize_provenance(record.get("provenance", ""))
    return {
        "cell_id": cell_id,
        "isc_a": isc,
        "voc_v": voc,
        "imp_a": imp,
        "vmp_v": vmp,
        "fill_factor": factor,
        "provenance": category,
    }


def correct_to_operating_point(
    record,
    temperature_c,
    solar_distance_au=1.0,
    sun_incidence_deg=0.0,
    current_temp_coeff_per_c=DEFAULT_CURRENT_TEMP_COEFF_PER_C,
    voltage_temp_coeff_per_c=DEFAULT_VOLTAGE_TEMP_COEFF_PER_C,
    reference_temperature_c=REFERENCE_TEMPERATURE_C,
):
    """Correct a measured maximum-power point to an operating condition."""
    imp = _require_number(record.get("imp_a", 0.0), "imp_a")
    vmp = _require_number(record.get("vmp_v", 0.0), "vmp_v")
    if imp <= 0.0 or vmp <= 0.0:
        raise ValueError("record must carry positive imp_a and vmp_v")
    temp = _require_number(temperature_c, "temperature_c")
    if temp <= -273.15:
        raise ValueError("temperature_c is at or below absolute zero")
    distance = _require_number(solar_distance_au, "solar_distance_au")
    if distance <= 0.0:
        raise ValueError("solar_distance_au must be > 0")
    incidence = _require_number(sun_incidence_deg, "sun_incidence_deg")
    if not 0.0 <= incidence < 90.0:
        raise ValueError("sun_incidence_deg must be in [0, 90)")
    ci = _require_number(current_temp_coeff_per_c, "current_temp_coeff_per_c")
    if ci < 0.0:
        raise ValueError("current_temp_coeff_per_c must be >= 0 for a photovoltaic cell")
    cv = _require_number(voltage_temp_coeff_per_c, "voltage_temp_coeff_per_c")
    if cv > 0.0:
        raise ValueError("voltage_temp_coeff_per_c must be <= 0 for a photovoltaic cell")
    t_ref = _require_number(reference_temperature_c, "reference_temperature_c")
    delta_t = temp - t_ref
    intensity_ratio = (1.0 / distance) ** 2 * math.cos(math.radians(incidence))
    corrected_i = imp * intensity_ratio * (1.0 + ci * delta_t)
    corrected_v = vmp * (1.0 + cv * delta_t)
    if corrected_i <= 0.0 or corrected_v <= 0.0:
        raise ValueError(
            "operating point drives the corrected maximum-power point to zero; "
            "the condition is outside the correction model"
        )
    return {
        "imp_a": corrected_i,
        "vmp_v": corrected_v,
        "pmp_w": corrected_i * corrected_v,
        "intensity_ratio": intensity_ratio,
        "irradiance_w_m2": REFERENCE_IRRADIANCE_W_M2 * intensity_ratio,
    }


def retention_factor(
    fluence_1mev_e_cm2,
    ultraviolet_loss=0.02,
    coverglass_loss=0.03,
    fluence_coefficient=0.12,
    reference_fluence=REFERENCE_FLUENCE_1MEV_E_CM2,
):
    """Combined particle-fluence, ultraviolet and coverglass power retention."""
    fluence = _require_number(fluence_1mev_e_cm2, "fluence_1mev_e_cm2")
    if fluence < 0.0:
        raise ValueError("fluence_1mev_e_cm2 must be >= 0")
    uv = _require_fraction(ultraviolet_loss, "ultraviolet_loss")
    cover = _require_fraction(coverglass_loss, "coverglass_loss")
    coeff = _require_number(fluence_coefficient, "fluence_coefficient")
    if not 0.0 < coeff < 1.0:
        raise ValueError("fluence_coefficient must be in (0, 1)")
    ref = _require_number(reference_fluence, "reference_fluence")
    if ref <= 0.0:
        raise ValueError("reference_fluence must be > 0")
    radiation = 1.0 - coeff * math.log10(1.0 + fluence / ref)
    if radiation <= 0.0:
        raise ValueError(
            "fluence drives retention to zero; the cell is outside the "
            "logarithmic degradation model, not at zero power"
        )
    return radiation * (1.0 - uv) * (1.0 - cover)


def _resolve_losses(losses):
    resolved = dict(DEFAULT_SECTION_LOSSES)
    if losses is not None:
        if not isinstance(losses, dict):
            raise ValueError("losses must be a mapping")
        unknown = sorted(set(losses) - set(DEFAULT_SECTION_LOSSES))
        if unknown:
            raise ValueError("losses has unknown keys: %s" % ", ".join(unknown))
        resolved.update(losses)
    for key in ("string_mismatch", "interconnect", "harness"):
        resolved[key] = _require_fraction(resolved[key], key)
    diode = _require_number(resolved["blocking_diode_v"], "blocking_diode_v")
    if diode < 0.0:
        raise ValueError("blocking_diode_v must be >= 0")
    resolved["blocking_diode_v"] = diode
    return resolved


def section_output(corrected, series_count, parallel_count, retention=1.0, losses=None):
    """Predicted power of one series-parallel section, in watts."""
    if not isinstance(corrected, dict):
        raise ValueError("corrected must be a mapping with imp_a and vmp_v")
    imp = _require_number(corrected.get("imp_a", 0.0), "imp_a")
    vmp = _require_number(corrected.get("vmp_v", 0.0), "vmp_v")
    if imp <= 0.0 or vmp <= 0.0:
        raise ValueError("corrected imp_a and vmp_v must both be > 0")
    if isinstance(series_count, bool) or not isinstance(series_count, int):
        raise ValueError("series_count must be an integer")
    if isinstance(parallel_count, bool) or not isinstance(parallel_count, int):
        raise ValueError("parallel_count must be an integer")
    if series_count < 1 or parallel_count < 1:
        raise ValueError("series_count and parallel_count must both be >= 1")
    keep = _require_number(retention, "retention")
    if not 0.0 < keep <= 1.0:
        raise ValueError("retention must be in (0, 1], got %r" % keep)
    loss = _resolve_losses(losses)
    string_voltage = vmp * series_count - loss["blocking_diode_v"]
    if string_voltage <= 0.0:
        raise ValueError(
            "blocking-diode drop meets or exceeds the string voltage; "
            "the section cannot deliver power"
        )
    string_current = (
        imp
        * parallel_count
        * (1.0 - loss["string_mismatch"])
        * (1.0 - loss["interconnect"])
    )
    power = string_voltage * string_current * (1.0 - loss["harness"]) * keep
    return {
        "string_voltage_v": string_voltage,
        "string_current_a": string_current,
        "power_w": power,
        "retention": keep,
    }


def predict_array_output(sections, demanded_power_w, required_margin=0.05, losses=None):
    """Predict total array power from measured sections and grade the margin."""
    if not isinstance(sections, (list, tuple)) or not sections:
        raise ValueError("sections must be a non-empty list of section records")
    demand = _require_number(demanded_power_w, "demanded_power_w")
    if demand <= 0.0:
        raise ValueError("demanded_power_w must be > 0")
    margin_floor = _require_number(required_margin, "required_margin")
    if margin_floor < 0.0:
        raise ValueError("required_margin must be >= 0")
    findings = []
    detail = []
    total = 0.0
    for entry in sections:
        if not isinstance(entry, dict):
            raise ValueError("each section must be a mapping")
        section_id = entry.get("section_id")
        if not isinstance(section_id, str) or not section_id.strip():
            raise ValueError("section_id must be a non-empty string")
        record = validate_cell_measurement(entry.get("measurement", {}))
        if record["provenance"] == UNCATEGORIZED_PROVENANCE:
            findings.append(
                "section %r rests on an untraceable cell value; clause 5.5.3 "
                "requires a measured record" % section_id
            )
            detail.append(
                {
                    "section_id": section_id,
                    "admissible": False,
                    "predicted_power_w": 0.0,
                    "provenance": record["provenance"],
                }
            )
            continue
        weight = provenance_weight(record["provenance"])
        corrected = correct_to_operating_point(
            record,
            entry.get("temperature_c", REFERENCE_TEMPERATURE_C),
            entry.get("solar_distance_au", 1.0),
            entry.get("sun_incidence_deg", 0.0),
        )
        keep = retention_factor(entry.get("fluence_1mev_e_cm2", 0.0))
        output = section_output(
            corrected,
            entry.get("series_count", 1),
            entry.get("parallel_count", 1),
            keep,
            losses,
        )
        predicted = output["power_w"] * weight
        total += predicted
        detail.append(
            {
                "section_id": section_id,
                "admissible": True,
                "predicted_power_w": predicted,
                "provenance": record["provenance"],
                "confidence_weight": weight,
                "retention": keep,
                "string_voltage_v": output["string_voltage_v"],
                "string_current_a": output["string_current_a"],
            }
        )
    margin = total / demand - 1.0
    if margin < margin_floor:
        findings.append(
            "predicted power %.2f W leaves margin %.4f below the required %.4f"
            % (total, margin, margin_floor)
        )
    return {
        "predicted_power_w": total,
        "demanded_power_w": demand,
        "margin": margin,
        "required_margin": margin_floor,
        "sections": detail,
        "findings": findings,
        "compliant": not findings,
    }
