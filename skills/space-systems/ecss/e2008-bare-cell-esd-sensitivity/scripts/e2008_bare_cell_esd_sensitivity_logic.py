"""Handling and storage of electrostatic-discharge-sensitive bare cells.

Anchor: ECSS-E-ST-20-08C clause 7.9.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The question this clause asks is narrow and quantitative: did the way a
sensitive bare cell was handled, packed and stored keep the voltage it
could actually see below the voltage it is known to survive? Everything
here serves that one comparison.

Four things make it go wrong, and each one is a separate step below.

    the wrong number      a withstand voltage is only meaningful with the
                          discharge model it was measured against. A
                          charged-device figure read as a human-body
                          figure moves a cell several bands up the
                          sensitivity ladder and every control obligation
                          is then drawn from the wrong row
    a present control     a wrist strap that is fitted and a wrist strap
                          whose ground path lies inside its band are
                          different statements. And the band has a floor
                          as well as a ceiling: a path resistance below
                          the floor is a personnel-safety defect, not a
                          better ground, so a control can fail by being
                          too good a conductor
    dissipative packing   packaging that dissipates its own charge does
                          not stop an external field reaching what is
                          inside. Only shielding packaging carries a cell
                          outside the protected area; dissipative and
                          conductive packing are inside-only, and
                          insulative packing is never right
    a quiet envelope      storage is a slow accumulation, not an event.
                          Humidity below the envelope raises tribocharging
                          on every movement, humidity above it invites
                          condensation, and shelf life already spent is
                          consumed whether or not anything was observed

The final step turns the residual charge a handling step is known to
leave into the voltage it would deliver into the cell: V = Q / C, taken
against the cell's own capacitance and compared with the withstand
voltage under a required margin factor. A control set can be complete and
still leave more charge than the cell survives, which is why the
arithmetic runs after the checklist rather than instead of it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "CONTROL_RESISTANCE_BANDS",
    "DISCHARGE_MODELS",
    "PACKAGING_CATEGORIES",
    "REGIME_ACCEPTED",
    "REGIME_REJECTED",
    "REQUIRED_CONTROLS",
    "SENSITIVITY_BANDS",
    "STORAGE_ENVELOPE",
    "assess_packaging",
    "assess_protected_area",
    "assess_storage",
    "categorize_sensitivity",
    "evaluate_handling_regime",
    "normalize_discharge_model",
    "normalize_packaging_category",
    "required_controls",
    "residual_charge_voltage",
    "validate_capacitance",
    "validate_resistance",
    "validate_withstand_voltage",
]

# Each discharge model has its own band table because each one injects
# charge differently. A figure measured under one model cannot be read
# against the bands of another.
DISCHARGE_MODELS = ("human-body-model", "charged-device-model", "machine-model")

# Bands run most sensitive first. Each entry is (name, lower volt bound
# inclusive, upper volt bound exclusive) for the named model.
SENSITIVITY_BANDS = {
    "human-body-model": (
        ("esd-band-1-most-sensitive", 0.0, 250.0),
        ("esd-band-2-sensitive", 250.0, 1000.0),
        ("esd-band-3-moderate", 1000.0, 4000.0),
        ("esd-band-4-least-sensitive", 4000.0, float("inf")),
    ),
    "charged-device-model": (
        ("esd-band-1-most-sensitive", 0.0, 125.0),
        ("esd-band-2-sensitive", 125.0, 250.0),
        ("esd-band-3-moderate", 250.0, 500.0),
        ("esd-band-4-least-sensitive", 500.0, float("inf")),
    ),
    "machine-model": (
        ("esd-band-1-most-sensitive", 0.0, 100.0),
        ("esd-band-2-sensitive", 100.0, 200.0),
        ("esd-band-3-moderate", 200.0, 400.0),
        ("esd-band-4-least-sensitive", 400.0, float("inf")),
    ),
}

# What each band obliges inside the protected area. More sensitive bands
# inherit everything the less sensitive ones owe and add to it.
REQUIRED_CONTROLS = {
    "esd-band-4-least-sensitive": (
        "esd-protected-area-marking",
        "grounded-work-surface",
    ),
    "esd-band-3-moderate": (
        "esd-protected-area-marking",
        "grounded-work-surface",
        "operator-wrist-strap",
    ),
    "esd-band-2-sensitive": (
        "esd-protected-area-marking",
        "grounded-work-surface",
        "operator-wrist-strap",
        "grounded-floor-and-footwear",
    ),
    "esd-band-1-most-sensitive": (
        "esd-protected-area-marking",
        "grounded-work-surface",
        "operator-wrist-strap",
        "grounded-floor-and-footwear",
        "air-ionizer",
    ),
}

# Ground-path resistance bands in ohms, inclusive at both ends. The lower
# bound is a personnel-safety floor: a path below it is a defect, not a
# better ground. A control with no band is graded on presence only.
CONTROL_RESISTANCE_BANDS = {
    "operator-wrist-strap": (7.5e5, 3.5e7),
    "grounded-work-surface": (1.0e4, 1.0e9),
    "grounded-floor-and-footwear": (1.0e5, 1.0e9),
}

PACKAGING_CATEGORIES = ("shielding", "dissipative", "conductive", "insulative")

# Relative humidity in per cent and temperature in degrees celsius,
# inclusive at both ends.
STORAGE_ENVELOPE = {
    "relative_humidity_percent": (30.0, 60.0),
    "temperature_celsius": (15.0, 30.0),
}

REGIME_ACCEPTED = "handling-regime-accepted"
REGIME_REJECTED = "handling-regime-rejected"


def _positive(value, label):
    """Return a strictly positive real number, refusing a bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _real(value, label):
    """Return a finite real number, refusing a bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def normalize_discharge_model(model):
    """Return a recognized discharge model, refusing anything else."""
    if not isinstance(model, str):
        raise ValueError("discharge_model must be a string, got %r" % (model,))
    cleaned = model.strip().lower()
    if cleaned not in DISCHARGE_MODELS:
        raise ValueError(
            "unrecognized discharge_model %r; recognized: %s"
            % (model, ", ".join(DISCHARGE_MODELS))
        )
    return cleaned


def normalize_packaging_category(category):
    """Return a recognized packaging category, refusing anything else."""
    if not isinstance(category, str):
        raise ValueError("packaging category must be a string, got %r" % (category,))
    cleaned = category.strip().lower()
    if cleaned not in PACKAGING_CATEGORIES:
        raise ValueError(
            "unrecognized packaging category %r; recognized: %s"
            % (category, ", ".join(PACKAGING_CATEGORIES))
        )
    return cleaned


def validate_withstand_voltage(volts):
    """Return a usable withstand voltage in volts."""
    return _positive(volts, "withstand_voltage_v")


def validate_capacitance(farads):
    """Return a usable cell capacitance in farads."""
    return _positive(farads, "cell_capacitance_f")


def validate_resistance(ohms, label="resistance_ohm"):
    """Return a usable ground-path resistance in ohms."""
    return _positive(ohms, label)


def categorize_sensitivity(withstand_voltage_v, discharge_model):
    """Group a bare cell into its sensitivity band for the stated model.

    The model is required rather than defaulted: the same number means a
    different band under each model, and a defaulted model is how a
    charged-device figure ends up read as a human-body figure.
    """
    volts = validate_withstand_voltage(withstand_voltage_v)
    model = normalize_discharge_model(discharge_model)
    for name, low, high in SENSITIVITY_BANDS[model]:
        if low <= volts < high:
            return {
                "discharge_model": model,
                "withstand_voltage_v": volts,
                "band": name,
                "band_lower_v": low,
                "band_upper_v": high,
                "sensitive": name != "esd-band-4-least-sensitive",
            }
    raise ValueError(
        "withstand voltage %r falls in no band of model %s" % (volts, model)
    )


def required_controls(band):
    """Return the controls a sensitivity band obliges, in catalogue order."""
    if not isinstance(band, str) or band.strip() not in REQUIRED_CONTROLS:
        raise ValueError(
            "unrecognized sensitivity band %r; recognized: %s"
            % (band, ", ".join(sorted(REQUIRED_CONTROLS)))
        )
    return tuple(REQUIRED_CONTROLS[band.strip()])


def assess_protected_area(band, controls):
    """Grade the obliged controls inside their own bands, not on presence.

    controls maps a control name to either True/False for a presence-only
    control, or to its measured ground-path resistance in ohms.
    """
    owed = required_controls(band)
    if not isinstance(controls, dict):
        raise ValueError("controls must be a mapping of control name to state")
    unknown = sorted(set(controls) - set(owed))
    graded = []
    findings = []
    for control in owed:
        if control not in controls:
            findings.append(
                "band %s obliges '%s' and the regime does not state it" % (band, control)
            )
            graded.append({"control": control, "present": False, "accepted": False})
            continue
        state = controls[control]
        band_limits = CONTROL_RESISTANCE_BANDS.get(control)
        if band_limits is None:
            if not isinstance(state, bool):
                raise ValueError(
                    "control '%s' is graded on presence and takes a boolean, got %r"
                    % (control, state)
                )
            accepted = state
            if not accepted:
                findings.append("obliged control '%s' is absent" % control)
            graded.append(
                {"control": control, "present": state, "accepted": accepted}
            )
            continue
        low, high = band_limits
        if isinstance(state, bool):
            raise ValueError(
                "control '%s' carries a ground path and needs a measured "
                "resistance in ohms, not %r" % (control, state)
            )
        measured = validate_resistance(state, "control '%s' resistance" % control)
        accepted = low <= measured <= high
        if measured < low:
            findings.append(
                "control '%s' measures %.3g ohm, below the %.3g ohm floor; a path "
                "that low is a personnel-safety defect rather than a better ground"
                % (control, measured, low)
            )
        elif measured > high:
            findings.append(
                "control '%s' measures %.3g ohm, above the %.3g ohm ceiling, so it "
                "is fitted and is not a ground" % (control, measured, high)
            )
        graded.append(
            {
                "control": control,
                "present": True,
                "resistance_ohm": measured,
                "band_low_ohm": low,
                "band_high_ohm": high,
                "accepted": accepted,
            }
        )
    for control in unknown:
        findings.append(
            "the regime states '%s', which band %s does not oblige; an unowed "
            "control is not evidence for an owed one" % (control, band)
        )
    return {
        "band": band,
        "required_controls": owed,
        "controls": tuple(graded),
        "unowed_controls": tuple(unknown),
        "findings": findings,
        "accepted": not findings,
    }


def assess_packaging(category, leaves_protected_area):
    """Decide whether the packing category suits where the cell travels."""
    cleaned = normalize_packaging_category(category)
    if not isinstance(leaves_protected_area, bool):
        raise ValueError(
            "leaves_protected_area must be a boolean, got %r"
            % (leaves_protected_area,)
        )
    findings = []
    shields = cleaned == "shielding"
    if cleaned == "insulative":
        findings.append(
            "insulative packaging charges by contact and is never a protection"
        )
    elif leaves_protected_area and not shields:
        findings.append(
            "packaging is '%s', which dissipates its own charge and does not "
            "shield an external field, yet the cell leaves the protected area"
            % cleaned
        )
    return {
        "category": cleaned,
        "shields": shields,
        "leaves_protected_area": leaves_protected_area,
        "findings": findings,
        "accepted": not findings,
    }


def assess_storage(conditions):
    """Grade the storage envelope and the shelf life already spent.

    conditions keys: relative_humidity_percent, temperature_celsius,
    days_stored, declared_shelf_life_days.
    """
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be a mapping")
    for key in (
        "relative_humidity_percent",
        "temperature_celsius",
        "days_stored",
        "declared_shelf_life_days",
    ):
        if key not in conditions:
            raise ValueError("storage conditions missing key '%s'" % key)
    humidity = _real(
        conditions["relative_humidity_percent"], "relative_humidity_percent"
    )
    if not 0.0 <= humidity <= 100.0:
        raise ValueError(
            "relative_humidity_percent must lie between 0 and 100, got %r" % humidity
        )
    temperature = _real(conditions["temperature_celsius"], "temperature_celsius")
    days = conditions["days_stored"]
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise ValueError("days_stored must be a non-negative integer, got %r" % (days,))
    shelf_life = conditions["declared_shelf_life_days"]
    if isinstance(shelf_life, bool) or not isinstance(shelf_life, int):
        raise ValueError(
            "declared_shelf_life_days must be an integer, got %r" % (shelf_life,)
        )
    if shelf_life <= 0:
        raise ValueError(
            "declared_shelf_life_days must be positive, got %d" % shelf_life
        )

    findings = []
    rh_low, rh_high = STORAGE_ENVELOPE["relative_humidity_percent"]
    t_low, t_high = STORAGE_ENVELOPE["temperature_celsius"]
    if humidity < rh_low:
        findings.append(
            "stored at %.3g per cent relative humidity, below the %.3g per cent "
            "floor, where every movement tribocharges harder" % (humidity, rh_low)
        )
    elif humidity > rh_high:
        findings.append(
            "stored at %.3g per cent relative humidity, above the %.3g per cent "
            "ceiling, where condensation and corrosion take over"
            % (humidity, rh_high)
        )
    if temperature < t_low or temperature > t_high:
        findings.append(
            "stored at %.3g degrees celsius, outside the %.3g to %.3g degree "
            "envelope" % (temperature, t_low, t_high)
        )
    spent = days / float(shelf_life)
    if days > shelf_life:
        findings.append(
            "stored %d days against a declared shelf life of %d days; shelf life "
            "is consumed whether or not anything was observed" % (days, shelf_life)
        )
    return {
        "relative_humidity_percent": humidity,
        "temperature_celsius": temperature,
        "days_stored": days,
        "declared_shelf_life_days": shelf_life,
        "shelf_life_fraction_spent": spent,
        "within_envelope": not findings,
        "findings": findings,
        "accepted": not findings,
    }


def residual_charge_voltage(charge_coulomb, cell_capacitance_f):
    """Return the voltage a residual charge would deliver into the cell."""
    charge = _real(charge_coulomb, "residual_charge_c")
    if charge < 0.0:
        raise ValueError("residual_charge_c must be non-negative, got %r" % charge)
    capacitance = validate_capacitance(cell_capacitance_f)
    return charge / capacitance


def evaluate_handling_regime(spec):
    """Run the clause 7.9.2 check over one handling and storage regime.

    spec keys: cell_id, withstand_voltage_v, discharge_model,
    cell_capacitance_f, residual_charge_c, required_margin_factor,
    controls, packaging_category, leaves_protected_area, storage.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "cell_id",
        "withstand_voltage_v",
        "discharge_model",
        "cell_capacitance_f",
        "residual_charge_c",
        "required_margin_factor",
        "controls",
        "packaging_category",
        "leaves_protected_area",
        "storage",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if not isinstance(spec["cell_id"], str) or not spec["cell_id"].strip():
        raise ValueError("cell_id must be a non-empty string")
    cell_id = spec["cell_id"].strip()

    sensitivity = categorize_sensitivity(
        spec["withstand_voltage_v"], spec["discharge_model"]
    )
    area = assess_protected_area(sensitivity["band"], spec["controls"])
    packaging = assess_packaging(
        spec["packaging_category"], spec["leaves_protected_area"]
    )
    storage = assess_storage(spec["storage"])

    margin_factor = _positive(
        spec["required_margin_factor"], "required_margin_factor"
    )
    if margin_factor < 1.0:
        raise ValueError(
            "required_margin_factor must be at least 1, got %r" % margin_factor
        )
    delivered = residual_charge_voltage(
        spec["residual_charge_c"], spec["cell_capacitance_f"]
    )
    withstand = sensitivity["withstand_voltage_v"]
    allowed = withstand / margin_factor
    charge_findings = []
    if delivered > allowed:
        charge_findings.append(
            "the regime leaves a residual charge worth %.4g V into this cell, "
            "against %.4g V allowed once the required margin factor of %.4g is "
            "applied to a %.4g V withstand"
            % (delivered, allowed, margin_factor, withstand)
        )

    findings = (
        list(area["findings"])
        + list(packaging["findings"])
        + list(storage["findings"])
        + charge_findings
    )
    return {
        "cell_id": cell_id,
        "sensitivity": sensitivity,
        "protected_area": area,
        "packaging": packaging,
        "storage": storage,
        "delivered_voltage_v": delivered,
        "allowed_voltage_v": allowed,
        "required_margin_factor": margin_factor,
        "achieved_margin_factor": (
            withstand / delivered if delivered > 0.0 else float("inf")
        ),
        "findings": findings,
        "verdict": REGIME_ACCEPTED if not findings else REGIME_REJECTED,
        "accepted": not findings,
    }
