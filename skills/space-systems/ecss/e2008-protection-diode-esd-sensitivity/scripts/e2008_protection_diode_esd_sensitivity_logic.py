"""Handling and storage regime for ESD-sensitive protection diodes.

Anchor: ECSS-E-ST-20-08C clause 9.10.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protection diode found sensitive to electrostatic discharge is not
protected by a policy. It is protected when the voltage it can actually
see, everywhere it is touched, packed or left standing, stays under the
voltage it is known to survive. This module grades that claim on five
arms, and each arm has a way of going quietly green.

    sensitivity     derived, not declared. A withstand voltage only means
                    something against the discharge model it was measured
                    with, so the band is derived from the pair
    controls        every obliged control is graded three ways, not one:
                    present, measured inside its OWN band, and verified
                    recently enough for that measurement to still stand.
                    A wrist strap measured in band eleven months ago is
                    not a verified wrist strap
    packaging       shielding and dissipative are not the same claim. A
                    dissipative bag bleeds charge off its own surface; it
                    does not keep an external field off the part
    storage         two-sided on both axes. A store that is too humid is
                    a corrosion problem, but a store that is too DRY is
                    an ESD problem, because dry air is what lets handling
                    build charge in the first place. A floor without a
                    ceiling, or a ceiling without a floor, is half a
                    check. Shelf life already spent is graded with it
    residual charge charge measured on the part is not the finding. The
                    finding is the voltage that charge delivers across
                    the package capacitance, taken against the withstand
                    voltage with the declared margin applied

The verdict is the conjunction: one obliged control out of band, one
stale verification, a merely dissipative bag on a band-1 part, a store
below its humidity floor or a residual charge that clears the withstand
voltage only without the margin each leave the regime deficient.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "BAND_TOLERANCE",
    "CONTROL_ABSENT",
    "CONTROL_COMPLIANT",
    "CONTROL_OUT_OF_BAND",
    "CONTROL_REQUIREMENTS",
    "CONTROL_VERIFICATION_STALE",
    "DEFAULT_SENSITIVITY_THRESHOLDS",
    "DISCHARGE_MODELS",
    "ESD_BANDS",
    "ESD_NOT_SENSITIVE",
    "MINIMUM_PACKAGING",
    "OBLIGED_CONTROLS",
    "PACKAGING_LADDER",
    "REGIME_COMPLIANT",
    "REGIME_DEFICIENT",
    "band_rank",
    "evaluate_handling_regime",
    "grade_control",
    "grade_controls",
    "grade_packaging",
    "grade_residual_charge",
    "grade_storage",
    "normalize_discharge_model",
    "normalize_packaging",
    "obliged_controls",
    "packaging_rank",
    "residual_voltage_from_charge",
    "sensitivity_band",
    "validate_thresholds",
]

DISCHARGE_MODELS = (
    "human-body-model",
    "machine-model",
    "charged-device-model",
)

ESD_NOT_SENSITIVE = "esd-not-sensitive"

# Most sensitive first. A lower index is a part that survives less.
ESD_BANDS = ("esd-band-1", "esd-band-2", "esd-band-3", ESD_NOT_SENSITIVE)

# Working convention for this pack, not standard text: a withstand
# voltage BELOW the listed volts places the part in that band, and the
# same voltage means different things under different discharge models,
# which is exactly why the model travels with the number. A caller with
# a project-specific table passes its own through the spec.
DEFAULT_SENSITIVITY_THRESHOLDS = {
    "human-body-model": (
        ("esd-band-1", 250.0),
        ("esd-band-2", 1000.0),
        ("esd-band-3", 4000.0),
    ),
    "machine-model": (
        ("esd-band-1", 100.0),
        ("esd-band-2", 200.0),
        ("esd-band-3", 400.0),
    ),
    "charged-device-model": (
        ("esd-band-1", 125.0),
        ("esd-band-2", 250.0),
        ("esd-band-3", 500.0),
    ),
}

# Each obliged control is graded inside its own band AND against the age
# of the measurement that put it there. low, high, unit, max_age_days.
CONTROL_REQUIREMENTS = {
    "wrist-strap-ground-path": (7.5e5, 3.5e7, "ohm", 1.0),
    "worksurface-ground-path": (1.0e6, 1.0e9, "ohm", 30.0),
    "floor-footwear-ground-path": (1.0e5, 1.0e9, "ohm", 7.0),
    "ionizer-offset": (-50.0, 50.0, "volt", 180.0),
    "terminal-shorting-bar": (0.0, 10.0, "ohm", 90.0),
}

# A more sensitive part owes more controls. Shorting the terminals is the
# control a discrete diode has and a bonded cell does not: leads left
# open are an antenna for a field the package never sees otherwise.
OBLIGED_CONTROLS = {
    "esd-band-1": (
        "wrist-strap-ground-path",
        "worksurface-ground-path",
        "floor-footwear-ground-path",
        "ionizer-offset",
        "terminal-shorting-bar",
    ),
    "esd-band-2": (
        "wrist-strap-ground-path",
        "worksurface-ground-path",
        "floor-footwear-ground-path",
        "terminal-shorting-bar",
    ),
    "esd-band-3": (
        "wrist-strap-ground-path",
        "worksurface-ground-path",
        "floor-footwear-ground-path",
    ),
    ESD_NOT_SENSITIVE: (),
}

# Weakest first. Shielding is a different claim from dissipative, not a
# better grade of the same claim.
PACKAGING_LADDER = (
    "unprotected",
    "antistatic-only",
    "dissipative",
    "shielding",
)

MINIMUM_PACKAGING = {
    "esd-band-1": "shielding",
    "esd-band-2": "shielding",
    "esd-band-3": "dissipative",
    ESD_NOT_SENSITIVE: "antistatic-only",
}

CONTROL_COMPLIANT = "control-compliant"
CONTROL_ABSENT = "control-absent"
CONTROL_OUT_OF_BAND = "control-outside-its-band"
CONTROL_VERIFICATION_STALE = "control-verification-stale"

REGIME_COMPLIANT = "handling-regime-compliant"
REGIME_DEFICIENT = "handling-regime-deficient"

# Bands and envelopes arrive as decimal literals and measurements arrive
# as floats. A value that should sit exactly on its limit must not pass on
# one platform and fail on another, so every comparison absorbs
# representation error at a named, relative tolerance.
BAND_TOLERANCE = 1e-9


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _number(value, label):
    """Return a finite float, refusing a bool, a string or a non-number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _tolerance(*bounds):
    """Return the absolute tolerance to use around the given bounds."""
    span = 1.0
    for bound in bounds:
        span = max(span, abs(bound))
    return BAND_TOLERANCE * span


def _within(value, low, high):
    """Return True when value sits inside the closed band, limits included."""
    tol = _tolerance(low, high)
    return (value >= low - tol) and (value <= high + tol)


def _below(value, limit):
    """Return True when value sits strictly below a limit it may touch."""
    return value < limit - _tolerance(limit)


def normalize_discharge_model(model, label="discharge model"):
    """Return a recognized discharge model name."""
    if not isinstance(model, str):
        raise ValueError("%s must be a string, got %r" % (label, model))
    cleaned = model.strip().lower()
    if cleaned not in DISCHARGE_MODELS:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, model, ", ".join(DISCHARGE_MODELS))
        )
    return cleaned


def normalize_packaging(category, label="packaging category"):
    """Return a recognized packaging category."""
    if not isinstance(category, str):
        raise ValueError("%s must be a string, got %r" % (label, category))
    cleaned = category.strip().lower()
    if cleaned not in PACKAGING_LADDER:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, category, ", ".join(PACKAGING_LADDER))
        )
    return cleaned


def packaging_rank(category):
    """Return the ladder position of a packaging category; higher protects more."""
    return PACKAGING_LADDER.index(normalize_packaging(category))


def band_rank(band):
    """Return the sensitivity position of a band; lower survives less."""
    if not isinstance(band, str) or band.strip().lower() not in ESD_BANDS:
        raise ValueError(
            "unrecognized sensitivity band %r; recognized: %s"
            % (band, ", ".join(ESD_BANDS))
        )
    return ESD_BANDS.index(band.strip().lower())


def validate_thresholds(thresholds):
    """Return a validated withstand-voltage threshold table.

    The table has to name every discharge model and has to rise: a band
    ladder whose limits do not increase cannot place a part at all.
    """
    if not isinstance(thresholds, dict):
        raise ValueError("sensitivity thresholds must be a mapping")
    out = {}
    for model in DISCHARGE_MODELS:
        if model not in thresholds:
            raise ValueError("sensitivity thresholds missing model '%s'" % model)
        rows = thresholds[model]
        if not isinstance(rows, (list, tuple)) or not rows:
            raise ValueError("sensitivity thresholds for %s must be a sequence" % model)
        validated = []
        previous = None
        for index, row in enumerate(rows):
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                raise ValueError(
                    "%s threshold[%d] must be a (band, volts) pair" % (model, index)
                )
            band = row[0]
            if not isinstance(band, str) or band.strip().lower() not in ESD_BANDS:
                raise ValueError(
                    "%s threshold[%d] names unrecognized band %r" % (model, index, band)
                )
            band = band.strip().lower()
            if band == ESD_NOT_SENSITIVE:
                raise ValueError(
                    "%s threshold[%d] may not put a limit on '%s'"
                    % (model, index, ESD_NOT_SENSITIVE)
                )
            limit = _number(row[1], "%s threshold[%d] volts" % (model, index))
            if limit <= 0.0:
                raise ValueError(
                    "%s threshold[%d] volts must be positive, got %r"
                    % (model, index, limit)
                )
            if previous is not None and limit <= previous:
                raise ValueError(
                    "%s thresholds must rise; %r follows %r" % (model, limit, previous)
                )
            previous = limit
            validated.append((band, limit))
        out[model] = tuple(validated)
    return out


def sensitivity_band(withstand_voltage, discharge_model, thresholds=None):
    """Derive the sensitivity band from a withstand voltage and its model.

    Sensitivity is derived, not declared, and it is derived against the
    model the voltage was measured with: the same number places a part in
    different bands under different models. A voltage sitting exactly on a
    limit falls into the less sensitive band, and the comparison absorbs
    representation error rather than moving the limit.
    """
    volts = _number(withstand_voltage, "withstand voltage")
    if volts <= 0.0:
        raise ValueError("withstand voltage must be positive, got %r" % (volts,))
    model = normalize_discharge_model(discharge_model)
    table = validate_thresholds(
        DEFAULT_SENSITIVITY_THRESHOLDS if thresholds is None else thresholds
    )
    for band, limit in table[model]:
        if _below(volts, limit):
            return band
    return ESD_NOT_SENSITIVE


def obliged_controls(band):
    """Return the controls the regime owes at this sensitivity band."""
    band_rank(band)
    return OBLIGED_CONTROLS[band.strip().lower()]


def grade_control(control, requirement_id=None):
    """Grade one control on presence, its own band, and verification age.

    Present is one third of the question. A ground path measured outside
    its band is not a ground path, and a measurement older than the
    interval it is verified on no longer says anything about today.
    """
    if not isinstance(control, dict):
        raise ValueError("control must be a mapping")
    for key in ("control_id", "present"):
        if key not in control:
            raise ValueError("control missing required key '%s'" % key)
    control_id = _identifier(control["control_id"], "control_id").lower()
    if requirement_id is not None and control_id != requirement_id:
        raise ValueError(
            "control %s does not answer requirement %s" % (control_id, requirement_id)
        )
    if control_id not in CONTROL_REQUIREMENTS:
        raise ValueError(
            "unrecognized control %r; recognized: %s"
            % (control_id, ", ".join(sorted(CONTROL_REQUIREMENTS)))
        )
    present = control["present"]
    if not isinstance(present, bool):
        raise ValueError(
            "control %s present must be a boolean, got %r" % (control_id, present)
        )
    low, high, unit, max_age = CONTROL_REQUIREMENTS[control_id]

    reasons = []
    if not present:
        return {
            "control_id": control_id,
            "present": False,
            "measured_value": None,
            "unit": unit,
            "band": (low, high),
            "in_band": False,
            "days_since_verification": None,
            "max_age_days": max_age,
            "verification_current": False,
            "state": CONTROL_ABSENT,
            "compliant": False,
            "reasons": ("obliged control %s is not in place" % control_id,),
        }

    for key in ("measured_value", "days_since_verification"):
        if key not in control:
            raise ValueError(
                "control %s is present but missing key '%s'" % (control_id, key)
            )
    value = _number(
        control["measured_value"], "control %s measured_value" % control_id
    )
    age = _number(
        control["days_since_verification"],
        "control %s days_since_verification" % control_id,
    )
    if age < 0.0:
        raise ValueError(
            "control %s days_since_verification must not be negative, got %r"
            % (control_id, age)
        )

    in_band = _within(value, low, high)
    if not in_band:
        reasons.append(
            "control %s measures %g %s, outside its band %g to %g %s"
            % (control_id, value, unit, low, high, unit)
        )
    current = age <= max_age + _tolerance(max_age)
    if not current:
        reasons.append(
            "control %s was last verified %g days ago, past its %g day interval"
            % (control_id, age, max_age)
        )

    if not in_band:
        state = CONTROL_OUT_OF_BAND
    elif not current:
        state = CONTROL_VERIFICATION_STALE
    else:
        state = CONTROL_COMPLIANT

    return {
        "control_id": control_id,
        "present": True,
        "measured_value": value,
        "unit": unit,
        "band": (low, high),
        "in_band": in_band,
        "days_since_verification": age,
        "max_age_days": max_age,
        "verification_current": current,
        "state": state,
        "compliant": state == CONTROL_COMPLIANT,
        "reasons": tuple(reasons),
    }


def grade_controls(controls, band):
    """Grade every control the band obliges, refusing a repeated entry.

    A control that was never offered is graded absent rather than skipped:
    a regime that owes five controls and reports four passes is a regime
    that reported four.
    """
    if not isinstance(controls, (list, tuple)):
        raise ValueError("controls must be a sequence of control mappings")
    offered = {}
    for index, control in enumerate(controls):
        if not isinstance(control, dict) or "control_id" not in control:
            raise ValueError("controls[%d] must be a mapping with a control_id" % index)
        control_id = _identifier(
            control["control_id"], "controls[%d] control_id" % index
        ).lower()
        if control_id in offered:
            raise ValueError("control %s is offered twice" % control_id)
        offered[control_id] = control

    required = obliged_controls(band)
    graded = []
    for control_id in required:
        entry = offered.get(control_id)
        if entry is None:
            entry = {"control_id": control_id, "present": False}
        graded.append(grade_control(entry, control_id))
    extra = tuple(sorted(c for c in offered if c not in required))
    return {
        "band": band.strip().lower(),
        "required_control_ids": required,
        "controls": tuple(graded),
        "deficient_control_ids": tuple(
            g["control_id"] for g in graded if not g["compliant"]
        ),
        "not_obliged_control_ids": extra,
        "all_compliant": all(g["compliant"] for g in graded),
    }


def grade_packaging(category, band):
    """Grade the packaging against the minimum the band obliges."""
    actual = normalize_packaging(category)
    band_rank(band)
    minimum = MINIMUM_PACKAGING[band.strip().lower()]
    adequate = packaging_rank(actual) >= packaging_rank(minimum)
    reasons = []
    if not adequate:
        reasons.append(
            "packaging is %s where band %s obliges at least %s; a bag that bleeds "
            "its own surface charge does not keep an external field off the part"
            % (actual, band.strip().lower(), minimum)
        )
    return {
        "packaging_category": actual,
        "minimum_category": minimum,
        "adequate": adequate,
        "reasons": tuple(reasons),
    }


def grade_storage(envelope, observed):
    """Grade the storage store on two-sided temperature and humidity bands.

    Humidity carries a floor as well as a ceiling, and the floor is the
    one an ESD regime exists for: a store drier than its floor is where
    handling builds the charge the rest of the regime then has to bleed
    off. Shelf life already spent is graded alongside.
    """
    if not isinstance(envelope, dict):
        raise ValueError("storage envelope must be a mapping")
    if not isinstance(observed, dict):
        raise ValueError("observed storage conditions must be a mapping")
    for key in ("temperature_c", "relative_humidity_pct", "shelf_life_days"):
        if key not in envelope:
            raise ValueError("storage envelope missing required key '%s'" % key)
    for key in ("temperature_c", "relative_humidity_pct", "days_in_storage"):
        if key not in observed:
            raise ValueError("observed storage missing required key '%s'" % key)

    bands = {}
    for key in ("temperature_c", "relative_humidity_pct"):
        pair = envelope[key]
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(
                "storage envelope %s must be a (low, high) pair, got %r" % (key, pair)
            )
        low = _number(pair[0], "storage envelope %s low" % key)
        high = _number(pair[1], "storage envelope %s high" % key)
        if low >= high:
            raise ValueError(
                "storage envelope %s low %r must sit below high %r" % (key, low, high)
            )
        bands[key] = (low, high)

    rh_low, rh_high = bands["relative_humidity_pct"]
    if rh_low < 0.0 or rh_high > 100.0:
        raise ValueError(
            "relative humidity band must lie between 0 and 100 percent, got %r"
            % (bands["relative_humidity_pct"],)
        )

    shelf_life = _number(envelope["shelf_life_days"], "shelf_life_days")
    if shelf_life <= 0.0:
        raise ValueError("shelf_life_days must be positive, got %r" % (shelf_life,))
    days = _number(observed["days_in_storage"], "days_in_storage")
    if days < 0.0:
        raise ValueError("days_in_storage must not be negative, got %r" % (days,))

    reasons = []
    results = {}
    for key, label in (
        ("temperature_c", "temperature"),
        ("relative_humidity_pct", "relative humidity"),
    ):
        low, high = bands[key]
        value = _number(observed[key], "observed %s" % key)
        inside = _within(value, low, high)
        results[key] = {"value": value, "band": (low, high), "inside": inside}
        if not inside:
            side = "below its floor" if value < low else "above its ceiling"
            reasons.append(
                "store %s is %g, %s of %g to %g" % (label, value, side, low, high)
            )

    life_left = shelf_life - days
    within_life = days <= shelf_life + _tolerance(shelf_life)
    if not within_life:
        reasons.append(
            "part has stood %g days against a %g day shelf life" % (days, shelf_life)
        )

    return {
        "temperature": results["temperature_c"],
        "relative_humidity": results["relative_humidity_pct"],
        "shelf_life_days": shelf_life,
        "days_in_storage": days,
        "shelf_life_days_remaining": life_left,
        "within_shelf_life": within_life,
        "compliant": not reasons,
        "reasons": tuple(reasons),
    }


def residual_voltage_from_charge(charge_nc, capacitance_pf):
    """Return the voltage a residual charge delivers across a capacitance.

    Charge in nanocoulombs over capacitance in picofarads is a ratio of
    1e-9 to 1e-12, so the volts are a thousand times the ratio. The
    conversion is written as one multiplication rather than a power so it
    rounds the same on every platform.
    """
    charge = _number(charge_nc, "residual_charge_nc")
    capacitance = _number(capacitance_pf, "package_capacitance_pf")
    if charge < 0.0:
        raise ValueError("residual_charge_nc must not be negative, got %r" % (charge,))
    if capacitance <= 0.0:
        raise ValueError(
            "package_capacitance_pf must be positive, got %r" % (capacitance,)
        )
    return 1000.0 * charge / capacitance


def grade_residual_charge(charge_nc, capacitance_pf, withstand_voltage, margin_factor):
    """Turn a residual charge into volts and grade it against the withstand.

    The charge is not the finding. The voltage it delivers is, and it is
    taken against the withstand voltage with the declared margin applied,
    so a part that clears the limit only on the nose is still reported.
    """
    volts = residual_voltage_from_charge(charge_nc, capacitance_pf)
    withstand = _number(withstand_voltage, "withstand voltage")
    if withstand <= 0.0:
        raise ValueError("withstand voltage must be positive, got %r" % (withstand,))
    margin = _number(margin_factor, "margin_factor")
    if margin < 1.0:
        raise ValueError(
            "margin_factor must be at least 1, got %r; a margin below one asks the "
            "part to survive more than it is rated for" % (margin,)
        )
    demanded = volts * margin
    clears = demanded <= withstand + _tolerance(withstand)
    reasons = []
    if not clears:
        reasons.append(
            "residual charge delivers %g V which, with the declared margin of %g, "
            "demands %g V against a withstand voltage of %g V"
            % (volts, margin, demanded, withstand)
        )
    return {
        "residual_voltage_v": volts,
        "margin_factor": margin,
        "demanded_voltage_v": demanded,
        "withstand_voltage_v": withstand,
        "utilisation": demanded / withstand,
        "clears": clears,
        "reasons": tuple(reasons),
    }


def evaluate_handling_regime(spec):
    """Run the clause 9.10.2 handling and storage check over one diode.

    spec keys: item_id, withstand_voltage_v, discharge_model, controls,
    packaging_category, storage_envelope, storage_observed,
    residual_charge_nc, package_capacitance_pf, margin_factor, and an
    optional sensitivity_thresholds table.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "item_id",
        "withstand_voltage_v",
        "discharge_model",
        "controls",
        "packaging_category",
        "storage_envelope",
        "storage_observed",
        "residual_charge_nc",
        "package_capacitance_pf",
        "margin_factor",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    item_id = _identifier(spec["item_id"], "item_id")
    band = sensitivity_band(
        spec["withstand_voltage_v"],
        spec["discharge_model"],
        spec.get("sensitivity_thresholds"),
    )
    controls = grade_controls(spec["controls"], band)
    packaging = grade_packaging(spec["packaging_category"], band)
    storage = grade_storage(spec["storage_envelope"], spec["storage_observed"])
    residual = grade_residual_charge(
        spec["residual_charge_nc"],
        spec["package_capacitance_pf"],
        spec["withstand_voltage_v"],
        spec["margin_factor"],
    )

    findings = []
    for graded in controls["controls"]:
        findings.extend(graded["reasons"])
    findings.extend(packaging["reasons"])
    findings.extend(storage["reasons"])
    findings.extend(residual["reasons"])

    return {
        "item_id": item_id,
        "discharge_model": normalize_discharge_model(spec["discharge_model"]),
        "withstand_voltage_v": _number(
            spec["withstand_voltage_v"], "withstand_voltage_v"
        ),
        "sensitivity_band": band,
        "sensitivity_rank": band_rank(band),
        "esd_sensitive": band != ESD_NOT_SENSITIVE,
        "controls": controls,
        "packaging": packaging,
        "storage": storage,
        "residual_charge": residual,
        "findings": findings,
        "verdict": REGIME_COMPLIANT if not findings else REGIME_DEFICIENT,
        "compliant": not findings,
    }
