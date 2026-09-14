"""Bare solar cell electrical performance behind a solar generator design decision.

Anchor: ECSS-E-ST-20-08C clause 7.5.3. The procedure below is a paraphrase of
the clause intent and reproduces none of its text: the electrical parameters of
bare cells are measured so that the numbers a solar generator is sized on
come from the cells that will fly rather than from a supplier brochure.

Procedure implemented here
--------------------------
1. Hold every measurement to the reference illumination and the cell
   temperature window. A parameter read off a drifting bench describes the
   bench, and a generator sized on it inherits the drift.
2. Derive maximum power, fill factor and conversion efficiency from the
   recorded current and voltage pairs rather than accepting them as declared
   numbers. The derivation is what ties the four measured quantities together.
3. Refuse a point set whose maximum power pair sits outside its own short
   circuit current or open circuit voltage. Such a set is not a weak cell, it
   is an inconsistent record.
4. Reduce the measured lot to a mean, a spread and a worst case. A single cell
   supports no design decision; the width of the population is what sizes a
   string, and the lot has to be wide enough to have a width at all.
5. Report the design power a generator can be built on, taken as a lower
   statistical bound on the lot and never above the worst cell actually
   measured.
"""

import math

__all__ = [
    "TOLERANCE",
    "DEFAULT_REFERENCE_IRRADIANCE_W_M2",
    "DEFAULT_REFERENCE_TEMPERATURE_C",
    "IRRADIANCE_TOLERANCE_FRACTION",
    "TEMPERATURE_TOLERANCE_C",
    "FILL_FACTOR_FLOOR",
    "FILL_FACTOR_CEILING",
    "MIN_DESIGN_LOT_SIZE",
    "DESIGN_SIGMA_MULTIPLIER",
    "maximum_power_w",
    "fill_factor",
    "conversion_efficiency",
    "conditions_within_window",
    "fill_factor_plausible",
    "lot_statistics",
    "design_power_w",
    "evaluate_cell",
    "assess_bare_cell_electrical_performance",
]

# Powers, fill factors and efficiencies are products and quotients of floats, so
# a cell built exactly to a declared limit can land a few units in the last
# place the wrong side of it. Absorb that representation error here rather than
# by loosening the declared limit itself.
TOLERANCE = 1e-9

# Air-mass-zero reference conditions the bare cell parameters are expressed at.
DEFAULT_REFERENCE_IRRADIANCE_W_M2 = 1367.0
DEFAULT_REFERENCE_TEMPERATURE_C = 28.0

# Outside these the reading is a bench artefact, not a cell parameter.
IRRADIANCE_TOLERANCE_FRACTION = 0.02
TEMPERATURE_TOLERANCE_C = 2.0

# A fill factor outside this range is not a bad cell, it is a bad record: the
# four measured quantities do not describe one characteristic curve.
FILL_FACTOR_FLOOR = 0.50
FILL_FACTOR_CEILING = 0.95

# Fewer cells than this carry no usable spread, so no design decision rests on
# them however good each individual reading looks.
MIN_DESIGN_LOT_SIZE = 5

# The lower statistical bound the design power is taken at.
DESIGN_SIGMA_MULTIPLIER = 3.0


def _real(label, value, allow_zero=False, allow_negative=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if not allow_negative:
        if allow_zero and number < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
        if not allow_zero and number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _count(label, value, allow_zero=True):
    """Return value as a validated non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    if not allow_zero and value == 0:
        raise ValueError("%s must be greater than zero" % label)
    return value


def _mapping(label, value, required_keys=()):
    """Return value as a mapping carrying every required key."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in required_keys:
        if key not in value:
            raise ValueError("%s is missing required key '%s'" % (label, key))
    return value


def _identifier(label, value):
    """Return value as a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _not_above(value, limit):
    """Return True when value sits at or below limit, edge included."""
    return value < limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=TOLERANCE)


def _not_below(value, limit):
    """Return True when value sits at or above limit, edge included."""
    return value > limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=TOLERANCE)


def maximum_power_w(impp_a, vmpp_v):
    """Return the maximum power point in watts from its current and voltage."""
    current = _real("impp_a", impp_a)
    voltage = _real("vmpp_v", vmpp_v)
    return current * voltage


def fill_factor(isc_a, voc_v, impp_a, vmpp_v):
    """Return the fill factor of one bare cell from its four measured points."""
    short_circuit = _real("isc_a", isc_a)
    open_circuit = _real("voc_v", voc_v)
    current = _real("impp_a", impp_a)
    voltage = _real("vmpp_v", vmpp_v)
    if not _not_above(current, short_circuit):
        raise ValueError(
            "maximum power current %g A sits above the short circuit current "
            "%g A; the four points do not describe one curve"
            % (current, short_circuit)
        )
    if not _not_above(voltage, open_circuit):
        raise ValueError(
            "maximum power voltage %g V sits above the open circuit voltage "
            "%g V; the four points do not describe one curve"
            % (voltage, open_circuit)
        )
    return (current * voltage) / (short_circuit * open_circuit)


def conversion_efficiency(
    pmpp_w, area_cm2, irradiance_w_m2=DEFAULT_REFERENCE_IRRADIANCE_W_M2
):
    """Return the conversion efficiency of a bare cell as a bare fraction."""
    power = _real("pmpp_w", pmpp_w)
    area = _real("area_cm2", area_cm2)
    irradiance = _real("irradiance_w_m2", irradiance_w_m2)
    incident = irradiance * area * 1.0e-4
    return power / incident


def conditions_within_window(
    irradiance_w_m2,
    temperature_c,
    reference_irradiance_w_m2=DEFAULT_REFERENCE_IRRADIANCE_W_M2,
    reference_temperature_c=DEFAULT_REFERENCE_TEMPERATURE_C,
    irradiance_fraction=IRRADIANCE_TOLERANCE_FRACTION,
    temperature_span_c=TEMPERATURE_TOLERANCE_C,
):
    """Return True when the measurement sat inside the declared bench window."""
    irradiance = _real("irradiance_w_m2", irradiance_w_m2)
    temperature = _real("temperature_c", temperature_c, allow_negative=True)
    reference = _real("reference_irradiance_w_m2", reference_irradiance_w_m2)
    reference_t = _real(
        "reference_temperature_c", reference_temperature_c, allow_negative=True
    )
    fraction = _real("irradiance_fraction", irradiance_fraction)
    span = _real("temperature_span_c", temperature_span_c)
    irradiance_gap = abs(irradiance - reference) / reference
    temperature_gap = abs(temperature - reference_t)
    return _not_above(irradiance_gap, fraction) and _not_above(temperature_gap, span)


def fill_factor_plausible(value, floor=FILL_FACTOR_FLOOR, ceiling=FILL_FACTOR_CEILING):
    """Return True when a fill factor could belong to a real characteristic curve."""
    factor = _real("value", value)
    low = _real("floor", floor)
    high = _real("ceiling", ceiling)
    if low > high:
        raise ValueError("plausibility band is inverted: %g above %g" % (low, high))
    return _not_below(factor, low) and _not_above(factor, high)


def lot_statistics(values):
    """Return count, mean, sample spread and extremes of a measured lot."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence of measurements")
    numbers = [_real("values entry", entry) for entry in values]
    count = len(numbers)
    mean = sum(numbers) / count
    if count > 1:
        squares = sum((number - mean) * (number - mean) for number in numbers)
        spread = math.sqrt(squares / (count - 1))
    else:
        spread = 0.0
    return {
        "count": count,
        "mean": mean,
        "spread": spread,
        "minimum": min(numbers),
        "maximum": max(numbers),
    }


def design_power_w(stats, sigma_multiplier=DESIGN_SIGMA_MULTIPLIER):
    """Return the per-cell power a generator sizing case can be built on."""
    data = _mapping("stats", stats, ("mean", "spread", "minimum"))
    mean = _real("stats['mean']", data["mean"])
    spread = _real("stats['spread']", data["spread"], allow_zero=True)
    worst = _real("stats['minimum']", data["minimum"])
    multiplier = _real("sigma_multiplier", sigma_multiplier, allow_zero=True)
    bound = mean - multiplier * spread
    return min(bound, worst)


def evaluate_cell(cell, limits):
    """Evaluate one bare cell record against the declared acceptance limits."""
    data = _mapping(
        "cell",
        cell,
        ("id", "isc_a", "voc_v", "impp_a", "vmpp_v", "area_cm2",
         "irradiance_w_m2", "temperature_c"),
    )
    cell_id = _identifier("cell['id']", data["id"])
    short_circuit = _real("cell['isc_a']", data["isc_a"])
    open_circuit = _real("cell['voc_v']", data["voc_v"])
    current = _real("cell['impp_a']", data["impp_a"])
    voltage = _real("cell['vmpp_v']", data["vmpp_v"])
    area = _real("cell['area_cm2']", data["area_cm2"])
    irradiance = _real("cell['irradiance_w_m2']", data["irradiance_w_m2"])
    temperature = _real(
        "cell['temperature_c']", data["temperature_c"], allow_negative=True
    )
    bounds = _mapping("limits", limits, ("min_pmpp_w", "min_efficiency"))
    min_power = _real("limits['min_pmpp_w']", bounds["min_pmpp_w"])
    min_efficiency = _real("limits['min_efficiency']", bounds["min_efficiency"])

    power = maximum_power_w(current, voltage)
    factor = fill_factor(short_circuit, open_circuit, current, voltage)
    efficiency = conversion_efficiency(power, area, DEFAULT_REFERENCE_IRRADIANCE_W_M2)
    correctable = conditions_within_window(irradiance, temperature)
    plausible = fill_factor_plausible(factor)
    power_ok = _not_below(power, min_power)
    efficiency_ok = _not_below(efficiency, min_efficiency)

    findings = []
    if not correctable:
        findings.append(
            "cell %s was read at %g W/m2 and %g C, outside the declared "
            "measurement window" % (cell_id, irradiance, temperature)
        )
    if not plausible:
        findings.append(
            "cell %s returns a fill factor of %.4f, which no single "
            "characteristic curve produces" % (cell_id, factor)
        )
    if not power_ok:
        findings.append(
            "cell %s peaks at %.6g W, below the declared %.6g W"
            % (cell_id, power, min_power)
        )
    if not efficiency_ok:
        findings.append(
            "cell %s converts %.4f of the incident power, below the declared "
            "%.4f" % (cell_id, efficiency, min_efficiency)
        )
    return {
        "id": cell_id,
        "pmpp_w": power,
        "fill_factor": factor,
        "efficiency": efficiency,
        "conditions_within_window": correctable,
        "fill_factor_plausible": plausible,
        "meets_power": power_ok,
        "meets_efficiency": efficiency_ok,
        "conforms": not findings,
        "findings": findings,
    }


def assess_bare_cell_electrical_performance(spec):
    """Run the full clause 7.5.3 bare cell electrical performance assessment.

    spec keys: cells (a non-empty sequence of bare cell records), limits
    (min_pmpp_w, min_efficiency), an optional sigma_multiplier for the design
    bound and an optional min_lot_size below which no design decision rests on
    the lot.
    """
    data = _mapping("spec", spec, ("cells", "limits"))
    cells = data["cells"]
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError("spec['cells'] must be a non-empty sequence of records")
    min_lot = _count(
        "spec['min_lot_size']", data.get("min_lot_size", MIN_DESIGN_LOT_SIZE),
        allow_zero=False,
    )
    multiplier = _real(
        "spec['sigma_multiplier']",
        data.get("sigma_multiplier", DESIGN_SIGMA_MULTIPLIER),
        allow_zero=True,
    )
    records = []
    findings = []
    seen = set()
    for cell in cells:
        record = evaluate_cell(cell, data["limits"])
        if record["id"] in seen:
            raise ValueError(
                "cell id '%s' appears twice in spec['cells']" % record["id"]
            )
        seen.add(record["id"])
        records.append(record)
        findings.extend(record["findings"])

    power_stats = lot_statistics([record["pmpp_w"] for record in records])
    efficiency_stats = lot_statistics([record["efficiency"] for record in records])
    design_power = design_power_w(power_stats, multiplier)
    if power_stats["count"] < min_lot:
        findings.append(
            "the lot holds %d cells, fewer than the %d a generator sizing case "
            "needs before its spread means anything"
            % (power_stats["count"], min_lot)
        )
    if design_power <= 0.0:
        findings.append(
            "the lower bound on cell power lands at %.6g W, so the measured "
            "spread swallows the mean and no sizing case survives it"
            % design_power
        )
    conforming = sum(1 for record in records if record["conforms"])
    return {
        "cell_records": records,
        "cells_assessed": len(records),
        "cells_conforming": conforming,
        "cells_rejected": len(records) - conforming,
        "power_statistics": power_stats,
        "efficiency_statistics": efficiency_stats,
        "design_power_w": design_power,
        "sigma_multiplier": multiplier,
        "findings": findings,
        "valid": not findings,
    }
