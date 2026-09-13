"""Discharge-test run conformance for solar-array coupons.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.5.3 (running the electrostatic-discharge
test on an array coupon with purpose-built instrumentation at defined
settings). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the coupon under test and the chamber conditions the run was
   carried out in (pressure window, temperature window).
2. For every defined bias setting, size the discharge the purpose-built
   circuit can deliver: the energy stored on the external capacitance,
   E = 0.5 * C * V^2, and the peak arc current the series resistance allows,
   I = |V| / R.
3. Derive the decay constant of that circuit, tau = R * C, and check that the
   transient recorder samples fast enough to resolve it and that the current
   probe spans the peak the circuit can drive. Instrumentation that cannot
   resolve the event makes the run unusable however many discharges it logged.
4. Compare the discharges actually recorded at each setting with the number
   planned and with the number the test requirement calls for.
5. Reject the run outright when a sustained arc was observed: a discharge that
   the primary power keeps feeding is a different event from the transient the
   coupon test is characterising.
"""

import math

__all__ = [
    "ENERGY_TOLERANCE_J",
    "PRESSURE_TOLERANCE_PA",
    "MIN_SAMPLES_PER_DECAY",
    "DEFAULT_MAX_CHAMBER_PRESSURE_PA",
    "DEFAULT_TEMPERATURE_WINDOW_C",
    "stored_energy_j",
    "decay_time_constant_s",
    "peak_arc_current_a",
    "samples_per_decay",
    "recorder_resolves_decay",
    "probe_spans_peak",
    "validate_coupon",
    "validate_chamber",
    "evaluate_setting",
    "assess_esd_test_run",
]

# Energy and sample-count comparisons are products of floats that can land a
# few ULPs either side of an exact bound. Absorb the representation error here
# rather than by loosening the test requirement itself.
ENERGY_TOLERANCE_J = 1e-9
COUNT_TOLERANCE = 1e-9
PRESSURE_TOLERANCE_PA = 1e-12

# A transient recorder needs this many samples across one decay constant
# before the arc waveform is reconstructable rather than merely detected.
MIN_SAMPLES_PER_DECAY = 10.0

# Coupon discharge testing runs in vacuum; above this the gas itself starts to
# carry the discharge and the result is not the coupon's behaviour.
DEFAULT_MAX_CHAMBER_PRESSURE_PA = 1.0e-3

# Default coupon temperature window in degrees Celsius for the run.
DEFAULT_TEMPERATURE_WINDOW_C = (-100.0, 80.0)


def _real(label, value, allow_zero=False, allow_negative=False):
    """Return value as a validated float."""
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


def _mapping(label, value, required_keys):
    """Return value as a mapping carrying every required key."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in required_keys:
        if key not in value:
            raise ValueError("%s is missing required key '%s'" % (label, key))
    return value


def stored_energy_j(capacitance_f, bias_voltage_v):
    """Return the energy stored on the external capacitance at a bias setting."""
    capacitance = _real("capacitance_f", capacitance_f)
    bias = _real("bias_voltage_v", bias_voltage_v, allow_negative=True)
    if bias == 0.0:
        raise ValueError("bias_voltage_v must be non-zero for a discharge setting")
    return 0.5 * capacitance * bias * bias


def decay_time_constant_s(series_resistance_ohm, capacitance_f):
    """Return the decay constant of the discharge circuit in seconds."""
    resistance = _real("series_resistance_ohm", series_resistance_ohm)
    capacitance = _real("capacitance_f", capacitance_f)
    return resistance * capacitance


def peak_arc_current_a(bias_voltage_v, series_resistance_ohm):
    """Return the peak arc current the series resistance permits."""
    bias = _real("bias_voltage_v", bias_voltage_v, allow_negative=True)
    if bias == 0.0:
        raise ValueError("bias_voltage_v must be non-zero for a discharge setting")
    resistance = _real("series_resistance_ohm", series_resistance_ohm)
    return abs(bias) / resistance


def samples_per_decay(sample_rate_hz, time_constant_s):
    """Return how many recorder samples fall inside one decay constant."""
    rate = _real("sample_rate_hz", sample_rate_hz)
    tau = _real("time_constant_s", time_constant_s)
    return rate * tau


def recorder_resolves_decay(sample_rate_hz, time_constant_s,
                            min_samples=MIN_SAMPLES_PER_DECAY):
    """Return True when the recorder samples the decay densely enough."""
    floor = _real("min_samples", min_samples)
    samples = samples_per_decay(sample_rate_hz, time_constant_s)
    if math.isclose(samples, floor, rel_tol=0.0, abs_tol=COUNT_TOLERANCE):
        return True
    return samples > floor


def probe_spans_peak(probe_range_a, peak_current):
    """Return True when the current probe range covers the peak arc current."""
    probe = _real("probe_range_a", probe_range_a)
    peak = _real("peak_current", peak_current)
    if math.isclose(probe, peak, rel_tol=0.0, abs_tol=COUNT_TOLERANCE):
        return True
    return probe > peak


def validate_coupon(coupon):
    """Return the validated coupon description for the run."""
    data = _mapping("coupon", coupon, ("cell_count", "active_area_cm2"))
    return {
        "cell_count": _count("coupon['cell_count']", data["cell_count"], allow_zero=False),
        "active_area_cm2": _real("coupon['active_area_cm2']", data["active_area_cm2"]),
    }


def validate_chamber(chamber):
    """Return (conditions, findings) for the chamber the run was carried out in."""
    data = _mapping("chamber", chamber, ("pressure_pa", "temperature_c"))
    pressure = _real("chamber['pressure_pa']", data["pressure_pa"])
    temperature = _real(
        "chamber['temperature_c']", data["temperature_c"], allow_negative=True
    )
    max_pressure = _real(
        "chamber['max_pressure_pa']",
        data.get("max_pressure_pa", DEFAULT_MAX_CHAMBER_PRESSURE_PA),
    )
    window = data.get("temperature_window_c", DEFAULT_TEMPERATURE_WINDOW_C)
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("chamber['temperature_window_c'] must be a (low, high) pair")
    low = _real("temperature_window_c[0]", window[0], allow_negative=True)
    high = _real("temperature_window_c[1]", window[1], allow_negative=True)
    if low > high:
        raise ValueError(
            "chamber temperature window is inverted: %g above %g" % (low, high)
        )
    findings = []
    if pressure > max_pressure and not math.isclose(
        pressure, max_pressure, rel_tol=0.0, abs_tol=PRESSURE_TOLERANCE_PA
    ):
        findings.append(
            "chamber pressure %g Pa exceeds the %g Pa ceiling for a vacuum "
            "discharge run" % (pressure, max_pressure)
        )
    if temperature < low or temperature > high:
        findings.append(
            "coupon temperature %g C sits outside the [%g, %g] C test window"
            % (temperature, low, high)
        )
    conditions = {
        "pressure_pa": pressure,
        "temperature_c": temperature,
        "max_pressure_pa": max_pressure,
        "temperature_window_c": (low, high),
    }
    return conditions, findings


def evaluate_setting(setting, circuit, instrumentation, required_energy_j,
                     required_discharges):
    """Evaluate one defined bias setting of the run and return its record."""
    data = _mapping(
        "setting", setting,
        ("bias_voltage_v", "discharges_planned", "discharges_recorded"),
    )
    circuit_data = _mapping(
        "discharge_circuit", circuit, ("capacitance_f", "series_resistance_ohm")
    )
    instrument_data = _mapping(
        "instrumentation", instrumentation, ("sample_rate_hz", "current_probe_range_a")
    )
    bias = _real("setting['bias_voltage_v']", data["bias_voltage_v"], allow_negative=True)
    if bias == 0.0:
        raise ValueError("setting['bias_voltage_v'] must be non-zero")
    planned = _count("setting['discharges_planned']", data["discharges_planned"],
                     allow_zero=False)
    recorded = _count("setting['discharges_recorded']", data["discharges_recorded"])
    capacitance = _real("discharge_circuit['capacitance_f']", circuit_data["capacitance_f"])
    resistance = _real(
        "discharge_circuit['series_resistance_ohm']",
        circuit_data["series_resistance_ohm"],
    )
    rate = _real("instrumentation['sample_rate_hz']", instrument_data["sample_rate_hz"])
    probe = _real(
        "instrumentation['current_probe_range_a']",
        instrument_data["current_probe_range_a"],
    )
    energy = stored_energy_j(capacitance, bias)
    tau = decay_time_constant_s(resistance, capacitance)
    peak = peak_arc_current_a(bias, resistance)
    samples = samples_per_decay(rate, tau)
    energy_ok = energy > required_energy_j or math.isclose(
        energy, required_energy_j, rel_tol=0.0, abs_tol=ENERGY_TOLERANCE_J
    )
    recorder_ok = recorder_resolves_decay(rate, tau)
    probe_ok = probe_spans_peak(probe, peak)
    findings = []
    if not energy_ok:
        findings.append(
            "bias %g V stores %.6g J, below the %.6g J the discharge requirement "
            "calls for" % (bias, energy, required_energy_j)
        )
    if not recorder_ok:
        findings.append(
            "recorder places %.4g samples across the %.4g s decay, fewer than the "
            "%g needed to reconstruct the arc" % (samples, tau, MIN_SAMPLES_PER_DECAY)
        )
    if not probe_ok:
        findings.append(
            "current probe range %.6g A does not span the %.6g A peak the circuit "
            "can drive at bias %g V" % (probe, peak, bias)
        )
    if planned < required_discharges:
        findings.append(
            "bias %g V plans %d discharges, fewer than the %d required per setting"
            % (bias, planned, required_discharges)
        )
    if recorded < planned:
        findings.append(
            "bias %g V recorded %d of %d planned discharges" % (bias, recorded, planned)
        )
    return {
        "bias_voltage_v": bias,
        "stored_energy_j": energy,
        "time_constant_s": tau,
        "peak_arc_current_a": peak,
        "samples_per_decay": samples,
        "discharges_planned": planned,
        "discharges_recorded": recorded,
        "energy_adequate": energy_ok,
        "recorder_adequate": recorder_ok,
        "probe_adequate": probe_ok,
        "conforms": not findings,
        "findings": findings,
    }


def assess_esd_test_run(spec):
    """Run the full clause 5.5.1.5.3 discharge-test conformance assessment.

    spec keys: coupon, chamber, discharge_circuit, instrumentation, settings
    (non-empty list of bias settings), required (discharge_energy_j and
    discharges_per_setting), optional observed (sustained_arc flag).
    """
    data = _mapping(
        "spec", spec,
        ("coupon", "chamber", "discharge_circuit", "instrumentation", "settings",
         "required"),
    )
    coupon = validate_coupon(data["coupon"])
    conditions, findings = validate_chamber(data["chamber"])
    required = _mapping(
        "spec['required']", data["required"],
        ("discharge_energy_j", "discharges_per_setting"),
    )
    required_energy = _real(
        "required['discharge_energy_j']", required["discharge_energy_j"]
    )
    required_discharges = _count(
        "required['discharges_per_setting']", required["discharges_per_setting"],
        allow_zero=False,
    )
    settings = data["settings"]
    if not isinstance(settings, (list, tuple)) or not settings:
        raise ValueError("spec['settings'] must be a non-empty sequence of bias settings")
    records = []
    seen = []
    for setting in settings:
        record = evaluate_setting(
            setting,
            data["discharge_circuit"],
            data["instrumentation"],
            required_energy,
            required_discharges,
        )
        for previous in seen:
            if math.isclose(previous, record["bias_voltage_v"], rel_tol=1e-12,
                            abs_tol=1e-12):
                raise ValueError(
                    "bias setting %g V is defined twice in spec['settings']"
                    % record["bias_voltage_v"]
                )
        seen.append(record["bias_voltage_v"])
        records.append(record)
        findings.extend(record["findings"])
    observed = data.get("observed") or {}
    if not isinstance(observed, dict):
        raise ValueError("spec['observed'] must be a mapping when supplied")
    sustained = observed.get("sustained_arc", False)
    if not isinstance(sustained, bool):
        raise ValueError("observed['sustained_arc'] must be a boolean")
    if sustained:
        findings.append(
            "a sustained arc was observed; the run characterises a power-fed event, "
            "not the coupon transient the test calls for"
        )
    planned_total = sum(record["discharges_planned"] for record in records)
    recorded_total = sum(record["discharges_recorded"] for record in records)
    return {
        "coupon": coupon,
        "chamber": conditions,
        "setting_records": records,
        "total_discharges_planned": planned_total,
        "total_discharges_recorded": recorded_total,
        "sustained_arc": sustained,
        "findings": findings,
        "valid": not findings,
    }
