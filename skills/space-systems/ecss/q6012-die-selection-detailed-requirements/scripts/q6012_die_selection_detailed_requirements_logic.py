"""Detailed selection criteria one microwave die satisfies to enter a design.

Anchor: ECSS-Q-ST-60-12 clause 5.1.2 (die selection -- the specific criteria a
candidate die meets once it has passed the baseline rules). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the design duty: the band edges the die is graded at, the bias
   rails applied, the dissipation, the base-plate temperature, the derating
   policy and the life the equipment owes.
2. Grade the radio-frequency criteria at the worst band edge: small-signal
   gain, output power at compression, noise figure and both return losses.
3. Grade the bias rails against the die ratings after the derating factors are
   applied, so the applied value is compared with a derated limit and never
   with the absolute maximum.
4. Form the channel temperature from the dissipation and the junction-to-case
   thermal path, and compare it with the derated channel-temperature limit.
5. Project the median life at that channel temperature from the rated life and
   the activation energy, and compare it with the required life.
6. Grade handling and assembly: electrostatic-sensitivity category against the
   line capability, and bond-pad metallisation against the assembly route.
7. Collect the unmet mandatory criteria and the evidence gaps; a die is
   selectable only when no mandatory criterion is unmet and no mandatory datum
   is missing.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "BOLTZMANN_EV_PER_K",
    "ABSOLUTE_ZERO_C",
    "ESD_CATEGORY_ORDER",
    "ASSEMBLY_ROUTES",
    "MANDATORY_CRITERIA",
    "kelvin",
    "channel_temperature_c",
    "derated_limit",
    "criterion_verdict",
    "arrhenius_life_hours",
    "evaluate_rf_criteria",
    "evaluate_bias_criteria",
    "evaluate_thermal_criteria",
    "evaluate_reliability_criteria",
    "evaluate_handling_criteria",
    "evidence_findings",
    "assess_detailed_requirements",
]

# Every comparison below is a difference of measured quantities, several of
# them routed through exp/log. An exactly compliant case can land a unit in the
# last place on the wrong side; absorb that here, never by relaxing a limit.
MARGIN_TOLERANCE = 1e-9

BOLTZMANN_EV_PER_K = 8.617333262e-5
ABSOLUTE_ZERO_C = -273.15

# Ordered from the most fragile part to the most robust; a die is acceptable
# when the line can handle its category, i.e. the line index is no larger.
ESD_CATEGORY_ORDER = ("class-0", "class-1a", "class-1b", "class-1c", "class-2")
ASSEMBLY_ROUTES = ("die-attach-and-wire-bond", "flip-chip", "hermetic-package")

MANDATORY_CRITERIA = (
    "small-signal-gain-db",
    "output-power-dbm",
    "noise-figure-db",
    "input-return-loss-db",
    "output-return-loss-db",
    "drain-voltage-v",
    "drain-current-ma",
    "channel-temperature-c",
    "projected-life-hours",
    "esd-sensitivity-category",
    "bond-pad-compatibility",
)


def _number(value, label):
    """Return value as a finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _number(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _non_negative(value, label):
    out = _number(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def kelvin(temperature_c):
    """Return an absolute temperature in kelvin, refusing sub-absolute input."""
    value = _number(temperature_c, "temperature_c")
    if value <= ABSOLUTE_ZERO_C:
        raise ValueError("temperature %g C is at or below absolute zero" % value)
    return value - ABSOLUTE_ZERO_C


def channel_temperature_c(base_temperature_c, dissipated_power_w, thermal_resistance_c_per_w):
    """Return the channel temperature reached through the junction-to-case path."""
    base = _number(base_temperature_c, "base_temperature_c")
    if base <= ABSOLUTE_ZERO_C:
        raise ValueError("base_temperature_c %g is at or below absolute zero" % base)
    power = _non_negative(dissipated_power_w, "dissipated_power_w")
    resistance = _positive(thermal_resistance_c_per_w, "thermal_resistance_c_per_w")
    return base + power * resistance


def derated_limit(rated_limit, derating_factor):
    """Return the usable limit after the derating factor is applied."""
    limit = _number(rated_limit, "rated_limit")
    factor = _number(derating_factor, "derating_factor")
    if not (0.0 < factor <= 1.0):
        raise ValueError("derating_factor must lie in (0, 1], got %r" % (derating_factor,))
    return limit * factor


def criterion_verdict(name, value, limit, sense, mandatory=True):
    """Return the verdict record for one criterion.

    sense 'max' means the applied value stays at or below the limit; sense
    'min' means it stays at or above it. The margin is always positive when
    the criterion is met.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("criterion name must be a non-empty string")
    if sense not in ("max", "min"):
        raise ValueError("sense must be 'max' or 'min', got %r" % (sense,))
    if not isinstance(mandatory, bool):
        raise ValueError("mandatory must be a boolean")
    if value is None:
        return {
            "name": name, "value": None, "limit": None, "sense": sense,
            "margin": None, "met": False, "mandatory": mandatory, "evidence": False,
        }
    numeric_value = _number(value, "%s value" % name)
    numeric_limit = _number(limit, "%s limit" % name)
    margin = (numeric_limit - numeric_value) if sense == "max" else (numeric_value - numeric_limit)
    return {
        "name": name, "value": numeric_value, "limit": numeric_limit, "sense": sense,
        "margin": margin, "met": margin >= -MARGIN_TOLERANCE,
        "mandatory": mandatory, "evidence": True,
    }


def arrhenius_life_hours(rated_life_hours, rated_temperature_c, operating_temperature_c,
                         activation_energy_ev):
    """Return the median life projected from the rated point to the operating point."""
    rated_life = _positive(rated_life_hours, "rated_life_hours")
    energy = _positive(activation_energy_ev, "activation_energy_ev")
    rated_k = kelvin(rated_temperature_c)
    operating_k = kelvin(operating_temperature_c)
    exponent = (energy / BOLTZMANN_EV_PER_K) * (1.0 / operating_k - 1.0 / rated_k)
    return rated_life * math.exp(exponent)


def _require_keys(mapping, keys, label):
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in keys:
        if key not in mapping:
            raise ValueError("%s missing required key '%s'" % (label, key))


def evaluate_rf_criteria(die, design):
    """Return the radio-frequency criterion verdicts at the graded band edge."""
    _require_keys(die, (), "die")
    _require_keys(design, ("required_gain_db", "required_output_power_dbm",
                           "max_noise_figure_db", "min_return_loss_db"), "design")
    return [
        criterion_verdict("small-signal-gain-db", die.get("gain_db"),
                          _number(design["required_gain_db"], "required_gain_db"), "min"),
        criterion_verdict("output-power-dbm", die.get("output_power_dbm"),
                          _number(design["required_output_power_dbm"],
                                  "required_output_power_dbm"), "min"),
        criterion_verdict("noise-figure-db", die.get("noise_figure_db"),
                          _non_negative(design["max_noise_figure_db"],
                                        "max_noise_figure_db"), "max"),
        criterion_verdict("input-return-loss-db", die.get("input_return_loss_db"),
                          _non_negative(design["min_return_loss_db"],
                                        "min_return_loss_db"), "min"),
        criterion_verdict("output-return-loss-db", die.get("output_return_loss_db"),
                          _non_negative(design["min_return_loss_db"],
                                        "min_return_loss_db"), "min"),
    ]


def evaluate_bias_criteria(die, design):
    """Return the bias criterion verdicts against the derated die ratings."""
    _require_keys(design, ("applied_drain_voltage_v", "applied_drain_current_ma",
                           "voltage_derating_factor", "current_derating_factor"), "design")
    voltage_limit = None
    if die.get("max_drain_voltage_v") is not None:
        voltage_limit = derated_limit(
            _positive(die["max_drain_voltage_v"], "max_drain_voltage_v"),
            design["voltage_derating_factor"],
        )
    current_limit = None
    if die.get("max_drain_current_ma") is not None:
        current_limit = derated_limit(
            _positive(die["max_drain_current_ma"], "max_drain_current_ma"),
            design["current_derating_factor"],
        )
    applied_v = _non_negative(design["applied_drain_voltage_v"], "applied_drain_voltage_v")
    applied_i = _non_negative(design["applied_drain_current_ma"], "applied_drain_current_ma")
    return [
        criterion_verdict("drain-voltage-v",
                          None if voltage_limit is None else applied_v,
                          voltage_limit, "max"),
        criterion_verdict("drain-current-ma",
                          None if current_limit is None else applied_i,
                          current_limit, "max"),
    ]


def evaluate_thermal_criteria(die, design):
    """Return the channel-temperature verdict after the thermal derating."""
    _require_keys(design, ("base_temperature_c", "dissipated_power_w",
                           "channel_temperature_derating_c"), "design")
    if die.get("thermal_resistance_c_per_w") is None or \
            die.get("max_channel_temperature_c") is None:
        return [criterion_verdict("channel-temperature-c", None, None, "max")]
    reached = channel_temperature_c(
        design["base_temperature_c"], design["dissipated_power_w"],
        die["thermal_resistance_c_per_w"],
    )
    allowed = _number(die["max_channel_temperature_c"], "max_channel_temperature_c") - \
        _non_negative(design["channel_temperature_derating_c"],
                      "channel_temperature_derating_c")
    return [criterion_verdict("channel-temperature-c", reached, allowed, "max")]


def evaluate_reliability_criteria(die, design):
    """Return the projected-life verdict at the reached channel temperature."""
    _require_keys(design, ("required_life_hours", "base_temperature_c",
                           "dissipated_power_w"), "design")
    needed = _positive(design["required_life_hours"], "required_life_hours")
    for key in ("rated_life_hours", "rated_life_temperature_c",
                "activation_energy_ev", "thermal_resistance_c_per_w"):
        if die.get(key) is None:
            return [criterion_verdict("projected-life-hours", None, None, "min")]
    reached = channel_temperature_c(
        design["base_temperature_c"], design["dissipated_power_w"],
        die["thermal_resistance_c_per_w"],
    )
    projected = arrhenius_life_hours(
        die["rated_life_hours"], die["rated_life_temperature_c"], reached,
        die["activation_energy_ev"],
    )
    return [criterion_verdict("projected-life-hours", projected, needed, "min")]


def evaluate_handling_criteria(die, design):
    """Return the electrostatic-sensitivity and bond-pad compatibility verdicts."""
    _require_keys(design, ("line_esd_capability", "assembly_route"), "design")
    line = design["line_esd_capability"]
    if line not in ESD_CATEGORY_ORDER:
        raise ValueError("line_esd_capability %r is not a recognised category" % (line,))
    route = design["assembly_route"]
    if route not in ASSEMBLY_ROUTES:
        raise ValueError("assembly_route %r is not recognised" % (route,))

    category = die.get("esd_sensitivity_category")
    if category is None:
        esd = criterion_verdict("esd-sensitivity-category", None, None, "min")
    else:
        if category not in ESD_CATEGORY_ORDER:
            raise ValueError("esd_sensitivity_category %r is not recognised" % (category,))
        esd = criterion_verdict(
            "esd-sensitivity-category",
            float(ESD_CATEGORY_ORDER.index(category)),
            float(ESD_CATEGORY_ORDER.index(line)), "min",
        )

    pads = die.get("bond_pad_routes")
    if pads is None:
        pad = criterion_verdict("bond-pad-compatibility", None, None, "min")
    else:
        if not isinstance(pads, (list, tuple)) or not pads:
            raise ValueError("bond_pad_routes must be a non-empty sequence when given")
        for item in pads:
            if item not in ASSEMBLY_ROUTES:
                raise ValueError("bond pad route %r is not recognised" % (item,))
        pad = criterion_verdict(
            "bond-pad-compatibility", 1.0 if route in pads else 0.0, 1.0, "min",
        )
    return [esd, pad]


def evidence_findings(die):
    """Return the evidence gaps a candidate die still owes."""
    if not isinstance(die, dict):
        raise ValueError("die must be a mapping")
    gaps = []
    for key, detail in (
        ("screening_level", "no screening level is on record for the die"),
        ("lot_acceptance_reference", "no lot-acceptance reference is on record"),
        ("process_monitor_reference", "no process-monitor reference is on record"),
    ):
        value = die.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            gaps.append({"code": key.replace("_", "-") + "-absent", "detail": detail})
    return gaps


def assess_detailed_requirements(die, design):
    """Run the full clause 5.1.2 detailed criteria assessment for one die."""
    if not isinstance(die, dict):
        raise ValueError("die must be a mapping")
    if not isinstance(design, dict):
        raise ValueError("design must be a mapping")
    verdicts = []
    verdicts.extend(evaluate_rf_criteria(die, design))
    verdicts.extend(evaluate_bias_criteria(die, design))
    verdicts.extend(evaluate_thermal_criteria(die, design))
    verdicts.extend(evaluate_reliability_criteria(die, design))
    verdicts.extend(evaluate_handling_criteria(die, design))

    names = [v["name"] for v in verdicts]
    for required in MANDATORY_CRITERIA:
        if required not in names:
            raise ValueError("criterion '%s' was not evaluated" % required)

    unmet = [v for v in verdicts if v["mandatory"] and v["evidence"] and not v["met"]]
    missing = [v for v in verdicts if v["mandatory"] and not v["evidence"]]
    gaps = evidence_findings(die)
    findings = []
    for verdict in unmet:
        findings.append("%s is short by %.6g" % (verdict["name"], -verdict["margin"]))
    for verdict in missing:
        findings.append("%s has no value on record" % verdict["name"])
    for gap in gaps:
        findings.append(gap["detail"])
    return {
        "verdicts": verdicts,
        "unmet": unmet,
        "missing": missing,
        "evidence_gaps": gaps,
        "findings": findings,
        "selectable": not unmet and not missing and not gaps,
    }
