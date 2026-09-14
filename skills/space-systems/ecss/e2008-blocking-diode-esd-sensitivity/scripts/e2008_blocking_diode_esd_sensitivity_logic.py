"""Handling and storage regime for ESD-sensitive blocking diodes.

Anchor: ECSS-E-ST-20-08C clause 12.10.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A blocking diode found sensitive to electrostatic discharge is not
protected by a policy and it is not protected by the best bench it ever
sat on. It travels a ROUTE -- goods-in, kitting, the test bench, staking,
the store -- and the voltage it can see is set by the worst place it
passed through, not by the average of them. So this module grades the
route rather than a regime, and names the station where the part was first
exposed.

    sensitivity   derived, not declared, and derived against a named
                  discharge model. The same withstand voltage sits in a
                  different band under a human body model than under a
                  machine model, so a number quoted without its model
                  places nothing at all. A voltage exactly on a band limit
                  belongs to the less sensitive band
    route         every station is graded on three things: whether it is a
                  designated protected area at all, whether each obliged
                  control is present, inside its OWN measured band and
                  verified recently enough for that measurement to still
                  stand, and whether the packaging the part TRAVELLED IN to
                  reach it met the minimum the band obliges. A shielded
                  bench reached by an unshielded walk is a part that was
                  already stressed before it arrived
    storage       two-sided on both axes, and the humidity FLOOR is the one
                  an ESD regime exists for. Too humid is a corrosion
                  problem; too dry is the ESD problem, because dry air is
                  what lets ordinary handling build the charge everything
                  else is there to bleed away. Shelf life already spent is
                  graded beside it
    residual      charge measured on the part is not the finding. The
                  finding is the voltage that charge delivers across the
                  package capacitance, taken against the withstand voltage
                  with the declared margin applied

Four compliant stations out of five is not a compliant route, and a
control nobody offered is graded absent rather than skipped -- otherwise a
station that owes five controls and reports four reads as green.

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
    "DEFAULT_WITHSTAND_THRESHOLDS",
    "DISCHARGE_MODELS",
    "EPA_REQUIRED_BANDS",
    "ESD_NOT_SENSITIVE",
    "MINIMUM_TRANSFER_PACKAGING",
    "OBLIGED_CONTROLS",
    "REGIME_COMPLIANT",
    "REGIME_DEFICIENT",
    "SENSITIVITY_BANDS",
    "STORAGE_HUMIDITY_BAND",
    "STORAGE_TEMPERATURE_BAND",
    "TRANSFER_PACKAGING_LADDER",
    "band_rank",
    "evaluate_handling_regime",
    "grade_control",
    "grade_residual_charge",
    "grade_route",
    "grade_station",
    "grade_storage",
    "normalize_discharge_model",
    "normalize_transfer_packaging",
    "obliged_controls",
    "residual_voltage_from_charge",
    "sensitivity_band",
    "transfer_rank",
    "validate_thresholds",
]

DISCHARGE_MODELS = (
    "human-body-model",
    "machine-model",
    "charged-device-model",
)

ESD_NOT_SENSITIVE = "esd-not-sensitive"

# Most sensitive first. A lower index is a part that survives less.
SENSITIVITY_BANDS = ("esd-band-a", "esd-band-b", "esd-band-c", ESD_NOT_SENSITIVE)

# Working convention for this pack, not standard text: a withstand voltage
# strictly BELOW the listed volts places the part in that band, and the
# same voltage means different things under different discharge models,
# which is exactly why the model travels with the number. A caller with a
# project table passes its own through the spec.
DEFAULT_WITHSTAND_THRESHOLDS = {
    "human-body-model": (
        ("esd-band-a", 250.0),
        ("esd-band-b", 1000.0),
        ("esd-band-c", 4000.0),
    ),
    "machine-model": (
        ("esd-band-a", 100.0),
        ("esd-band-b", 200.0),
        ("esd-band-c", 400.0),
    ),
    "charged-device-model": (
        ("esd-band-a", 125.0),
        ("esd-band-b", 250.0),
        ("esd-band-c", 500.0),
    ),
}

# Each obliged control is graded inside its own band AND against the age
# of the measurement that put it there: low, high, unit, max_age_days.
CONTROL_REQUIREMENTS = {
    "wrist-strap-ground-path": (7.5e5, 3.5e7, "ohm", 1.0),
    "bench-mat-ground-path": (1.0e6, 1.0e9, "ohm", 30.0),
    "epa-floor-ground-path": (1.0e5, 1.0e9, "ohm", 7.0),
    "ionizer-balance-offset": (-50.0, 50.0, "volt", 180.0),
    "lead-shorting-clip-resistance": (0.0, 10.0, "ohm", 90.0),
}

# A more sensitive part owes more controls. Shorting the leads is the
# control a discrete blocking diode owes and a bonded article does not:
# leads left open are an antenna for a field the package never sees
# otherwise, and a clip measuring kilohms is not a short.
OBLIGED_CONTROLS = {
    "esd-band-a": (
        "wrist-strap-ground-path",
        "bench-mat-ground-path",
        "epa-floor-ground-path",
        "ionizer-balance-offset",
        "lead-shorting-clip-resistance",
    ),
    "esd-band-b": (
        "wrist-strap-ground-path",
        "bench-mat-ground-path",
        "epa-floor-ground-path",
        "lead-shorting-clip-resistance",
    ),
    "esd-band-c": (
        "wrist-strap-ground-path",
        "bench-mat-ground-path",
    ),
    ESD_NOT_SENSITIVE: (),
}

EPA_REQUIRED_BANDS = ("esd-band-a", "esd-band-b", "esd-band-c")

# Weakest first. Shielding is a different claim from dissipative, not a
# better grade of the same claim: a dissipative bag bleeds charge off its
# own surface and does nothing about an external field.
TRANSFER_PACKAGING_LADDER = (
    "unprotected",
    "antistatic-only",
    "dissipative",
    "shielding",
)

MINIMUM_TRANSFER_PACKAGING = {
    "esd-band-a": "shielding",
    "esd-band-b": "shielding",
    "esd-band-c": "dissipative",
    ESD_NOT_SENSITIVE: "antistatic-only",
}

# Two-sided on both axes. The humidity FLOOR is the ESD limit.
STORAGE_TEMPERATURE_BAND = (15.0, 30.0)
STORAGE_HUMIDITY_BAND = (30.0, 60.0)

CONTROL_COMPLIANT = "control-compliant"
CONTROL_ABSENT = "control-absent"
CONTROL_OUT_OF_BAND = "control-outside-its-band"
CONTROL_VERIFICATION_STALE = "control-verification-stale"

REGIME_COMPLIANT = "handling-regime-compliant"
REGIME_DEFICIENT = "handling-regime-deficient"

# Bands arrive as decimal literals and measurements arrive as floats. A
# value that should sit exactly on its limit must not pass on one platform
# and fail on another, so every comparison absorbs representation error at
# a named, relative tolerance.
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


def _positive(value, label):
    """Return a strictly positive finite float."""
    value = _number(value, label)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
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


def _at_most(value, limit):
    """Return True when value does not exceed a limit it may sit on."""
    return value <= limit + _tolerance(limit)


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


def normalize_transfer_packaging(category, label="transfer packaging"):
    """Return a recognized transfer packaging category."""
    if not isinstance(category, str):
        raise ValueError("%s must be a string, got %r" % (label, category))
    cleaned = category.strip().lower()
    if cleaned not in TRANSFER_PACKAGING_LADDER:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, category, ", ".join(TRANSFER_PACKAGING_LADDER))
        )
    return cleaned


def transfer_rank(category):
    """Return the ladder position of a packaging category; higher protects more."""
    return TRANSFER_PACKAGING_LADDER.index(normalize_transfer_packaging(category))


def band_rank(band):
    """Return the sensitivity position of a band; lower survives less."""
    if not isinstance(band, str) or band.strip().lower() not in SENSITIVITY_BANDS:
        raise ValueError(
            "unrecognized sensitivity band %r; recognized: %s"
            % (band, ", ".join(SENSITIVITY_BANDS))
        )
    return SENSITIVITY_BANDS.index(band.strip().lower())


def validate_thresholds(thresholds):
    """Return a validated withstand-voltage threshold table.

    The table has to name every discharge model and every band below the
    not-sensitive one, and each model's limits have to rise: a table whose
    limits do not rise cannot place a part at all.
    """
    if not isinstance(thresholds, dict):
        raise ValueError("thresholds must be a mapping of discharge model to limits")
    out = {}
    for model in DISCHARGE_MODELS:
        if model not in thresholds:
            raise ValueError("thresholds must name discharge model '%s'" % model)
        rows = thresholds[model]
        if not isinstance(rows, (list, tuple)) or len(rows) != len(SENSITIVITY_BANDS) - 1:
            raise ValueError(
                "thresholds for %s must carry %d rising band limits"
                % (model, len(SENSITIVITY_BANDS) - 1)
            )
        limits = []
        previous = None
        for index, row in enumerate(rows):
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                raise ValueError(
                    "thresholds[%s][%d] must be a (band, volts) pair" % (model, index)
                )
            band, volts = row
            if band != SENSITIVITY_BANDS[index]:
                raise ValueError(
                    "thresholds[%s][%d] must name band %s, got %r"
                    % (model, index, SENSITIVITY_BANDS[index], band)
                )
            volts = _positive(volts, "thresholds[%s][%d] volts" % (model, index))
            if previous is not None and volts <= previous:
                raise ValueError(
                    "thresholds for %s must rise; %r follows %r" % (model, volts, previous)
                )
            previous = volts
            limits.append((band, volts))
        out[model] = tuple(limits)
    return out


def sensitivity_band(withstand_voltage, discharge_model, thresholds=None):
    """Derive the sensitivity band from the withstand voltage and its model.

    A withstand voltage sitting exactly on a band limit belongs to the LESS
    sensitive band, and the comparison absorbs representation error rather
    than moving the limit.
    """
    volts = _positive(withstand_voltage, "withstand_voltage")
    model = normalize_discharge_model(discharge_model)
    table = validate_thresholds(
        DEFAULT_WITHSTAND_THRESHOLDS if thresholds is None else thresholds
    )
    for band, limit in table[model]:
        if _below(volts, limit):
            return band
    return ESD_NOT_SENSITIVE


def obliged_controls(band):
    """Return the controls this sensitivity band obliges."""
    band_rank(band)
    return OBLIGED_CONTROLS[band.strip().lower()]


def grade_control(name, offered, label="station"):
    """Grade one obliged control on presence, own band and verification age.

    Presence is the weakest third of the question. A ground path measured
    outside its own band is not a ground path, and a measurement whose
    verification interval has run out no longer says anything about the
    bench the part was on today.
    """
    if name not in CONTROL_REQUIREMENTS:
        raise ValueError(
            "unrecognized control %r; recognized: %s"
            % (name, ", ".join(sorted(CONTROL_REQUIREMENTS)))
        )
    low, high, unit, max_age = CONTROL_REQUIREMENTS[name]
    if offered is None:
        return {
            "control": name,
            "status": CONTROL_ABSENT,
            "measured_value": None,
            "unit": unit,
            "in_band": False,
            "verification_current": False,
            "finding": "%s owes control %s and offered none" % (label, name),
        }
    if not isinstance(offered, dict):
        raise ValueError("%s control %s must be a mapping or None" % (label, name))
    for key in ("measured_value", "verification_age_days"):
        if key not in offered:
            raise ValueError("%s control %s missing key '%s'" % (label, name, key))
    value = _number(offered["measured_value"], "%s control %s measured_value" % (label, name))
    age = _number(
        offered["verification_age_days"], "%s control %s verification_age_days" % (label, name)
    )
    if age < 0.0:
        raise ValueError(
            "%s control %s verification_age_days must not be negative, got %r"
            % (label, name, age)
        )
    in_band = _within(value, low, high)
    current = _at_most(age, max_age)
    if not in_band:
        status = CONTROL_OUT_OF_BAND
        finding = (
            "%s measured %s at %g %s, outside its band of %g to %g %s"
            % (label, name, value, unit, low, high, unit)
        )
    elif not current:
        status = CONTROL_VERIFICATION_STALE
        finding = (
            "%s last verified %s %g days ago, past its %g day interval, so the "
            "measurement no longer stands" % (label, name, age, max_age)
        )
    else:
        status = CONTROL_COMPLIANT
        finding = None
    return {
        "control": name,
        "status": status,
        "measured_value": value,
        "unit": unit,
        "in_band": in_band,
        "verification_current": current,
        "finding": finding,
    }


def grade_station(station, band):
    """Grade one station of the route: protected area, controls, arrival packaging."""
    if not isinstance(station, dict):
        raise ValueError("station must be a mapping")
    for key in ("station_id", "epa_designated", "transfer_packaging", "controls"):
        if key not in station:
            raise ValueError("station missing required key '%s'" % key)
    station_id = _identifier(station["station_id"], "station_id")
    label = "station %s" % station_id
    band = band.strip().lower()
    band_rank(band)

    epa = station["epa_designated"]
    if not isinstance(epa, bool):
        raise ValueError("%s epa_designated must be a boolean, got %r" % (label, epa))
    findings = []
    epa_ok = True
    if band in EPA_REQUIRED_BANDS and not epa:
        epa_ok = False
        findings.append(
            "%s is not a designated protected area, which band %s obliges"
            % (label, band)
        )

    offered = station["controls"]
    if not isinstance(offered, (list, tuple)):
        raise ValueError("%s controls must be a sequence" % label)
    by_name = {}
    for index, entry in enumerate(offered):
        if not isinstance(entry, dict) or "control" not in entry:
            raise ValueError("%s controls[%d] must name a control" % (label, index))
        name = entry["control"]
        if name in by_name:
            raise ValueError("%s offers control %s twice" % (label, name))
        by_name[name] = entry

    owed = obliged_controls(band)
    graded = tuple(grade_control(name, by_name.get(name), label) for name in owed)
    findings.extend(g["finding"] for g in graded if g["finding"])
    unowed = tuple(sorted(name for name in by_name if name not in owed))
    for name in unowed:
        if name not in CONTROL_REQUIREMENTS:
            raise ValueError("%s offers unrecognized control %r" % (label, name))

    arrival = normalize_transfer_packaging(
        station["transfer_packaging"], "%s transfer_packaging" % label
    )
    minimum = MINIMUM_TRANSFER_PACKAGING[band]
    transfer_ok = transfer_rank(arrival) >= transfer_rank(minimum)
    if not transfer_ok:
        findings.append(
            "%s was reached in %s packaging where band %s obliges at least %s, so "
            "the part was already exposed on the way in"
            % (label, arrival, band, minimum)
        )

    return {
        "station_id": station_id,
        "epa_designated": epa,
        "epa_ok": epa_ok,
        "transfer_packaging": arrival,
        "minimum_transfer_packaging": minimum,
        "transfer_ok": transfer_ok,
        "controls": graded,
        "unobliged_controls": unowed,
        "findings": findings,
        "compliant": not findings,
    }


def grade_route(stations, band):
    """Grade every station in order and name where the part was first exposed.

    The route is only as good as its worst station, so the verdict is the
    conjunction and the governing station is the first deficient one: that
    is the point the part stopped being protected, and every station after
    it inherited a part that had already seen a field.
    """
    if not isinstance(stations, (list, tuple)) or not stations:
        raise ValueError("route must carry at least one station")
    graded = []
    seen = set()
    for station in stations:
        result = grade_station(station, band)
        if result["station_id"] in seen:
            raise ValueError("station %s appears twice in the route" % result["station_id"])
        seen.add(result["station_id"])
        graded.append(result)
    first_deficient = None
    for index, result in enumerate(graded):
        if not result["compliant"]:
            first_deficient = index
            break
    findings = []
    for result in graded:
        findings.extend(result["findings"])
    return {
        "stations": tuple(graded),
        "station_count": len(graded),
        "compliant_station_count": sum(1 for r in graded if r["compliant"]),
        "first_exposure_index": first_deficient,
        "governing_station_id": (
            None if first_deficient is None else graded[first_deficient]["station_id"]
        ),
        "findings": findings,
        "compliant": first_deficient is None,
    }


def grade_storage(storage):
    """Grade the store on two-sided temperature and humidity, and shelf life.

    The humidity floor is the reading an ESD regime exists for: a store
    that is too dry is what lets ordinary handling build charge, so a
    ceiling without a floor is half a check.
    """
    if not isinstance(storage, dict):
        raise ValueError("storage must be a mapping")
    for key in (
        "temperature_c",
        "relative_humidity_pct",
        "declared_shelf_life_days",
        "elapsed_shelf_life_days",
    ):
        if key not in storage:
            raise ValueError("storage missing required key '%s'" % key)
    temperature = _number(storage["temperature_c"], "temperature_c")
    humidity = _number(storage["relative_humidity_pct"], "relative_humidity_pct")
    if not 0.0 <= humidity <= 100.0:
        raise ValueError(
            "relative_humidity_pct must lie between 0 and 100, got %r" % (humidity,)
        )
    declared = _positive(storage["declared_shelf_life_days"], "declared_shelf_life_days")
    elapsed = _number(storage["elapsed_shelf_life_days"], "elapsed_shelf_life_days")
    if elapsed < 0.0:
        raise ValueError("elapsed_shelf_life_days must not be negative, got %r" % (elapsed,))

    t_low, t_high = STORAGE_TEMPERATURE_BAND
    h_low, h_high = STORAGE_HUMIDITY_BAND
    findings = []
    if temperature < t_low - _tolerance(t_low, t_high):
        findings.append(
            "store sits at %g C, below its floor of %g C" % (temperature, t_low)
        )
    elif temperature > t_high + _tolerance(t_low, t_high):
        findings.append(
            "store sits at %g C, above its ceiling of %g C" % (temperature, t_high)
        )
    if humidity < h_low - _tolerance(h_low, h_high):
        findings.append(
            "store sits at %g %% relative humidity, below the %g %% ESD floor, which "
            "is the dry end handling charges the part at" % (humidity, h_low)
        )
    elif humidity > h_high + _tolerance(h_low, h_high):
        findings.append(
            "store sits at %g %% relative humidity, above its %g %% ceiling"
            % (humidity, h_high)
        )
    spent = elapsed / declared
    if not _at_most(elapsed, declared):
        findings.append(
            "shelf life is spent: %g of %g declared days have elapsed"
            % (elapsed, declared)
        )
    return {
        "temperature_c": temperature,
        "relative_humidity_pct": humidity,
        "temperature_band": STORAGE_TEMPERATURE_BAND,
        "humidity_band": STORAGE_HUMIDITY_BAND,
        "shelf_life_spent_fraction": spent,
        "findings": findings,
        "compliant": not findings,
    }


def residual_voltage_from_charge(charge_coulomb, package_capacitance_farad):
    """Return the voltage a residual charge delivers across the package.

    Charge is not a stress. The voltage it delivers is, and a smaller
    package capacitance turns the same charge into more volts.
    """
    charge = _number(charge_coulomb, "charge_coulomb")
    if charge < 0.0:
        raise ValueError("charge_coulomb must not be negative, got %r" % (charge,))
    capacitance = _positive(
        package_capacitance_farad, "package_capacitance_farad"
    )
    return charge / capacitance


def grade_residual_charge(residual, withstand_voltage):
    """Compare the delivered voltage, with the declared margin, against withstand."""
    if not isinstance(residual, dict):
        raise ValueError("residual must be a mapping")
    for key in ("charge_coulomb", "package_capacitance_farad", "margin_factor"):
        if key not in residual:
            raise ValueError("residual missing required key '%s'" % key)
    margin = _number(residual["margin_factor"], "margin_factor")
    if margin < 1.0:
        raise ValueError(
            "margin_factor must be at least 1.0, got %r; a factor below one makes "
            "the check easier than the limit it is protecting" % (margin,)
        )
    withstand = _positive(withstand_voltage, "withstand_voltage")
    delivered = residual_voltage_from_charge(
        residual["charge_coulomb"], residual["package_capacitance_farad"]
    )
    stress = delivered * margin
    cleared = _at_most(stress, withstand)
    findings = []
    if not cleared:
        findings.append(
            "residual charge delivers %g V across the package, %g V with the "
            "declared margin, against a withstand voltage of %g V"
            % (delivered, stress, withstand)
        )
    return {
        "delivered_voltage_v": delivered,
        "margin_factor": margin,
        "stress_voltage_v": stress,
        "withstand_voltage_v": withstand,
        "findings": findings,
        "compliant": cleared,
    }


def evaluate_handling_regime(spec):
    """Run the clause 12.10.2 regime check over one blocking diode route.

    spec keys: item_id, withstand_voltage_v, discharge_model, route,
    storage, residual; optional thresholds.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "item_id",
        "withstand_voltage_v",
        "discharge_model",
        "route",
        "storage",
        "residual",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    item_id = _identifier(spec["item_id"], "item_id")
    band = sensitivity_band(
        spec["withstand_voltage_v"], spec["discharge_model"], spec.get("thresholds")
    )
    route = grade_route(spec["route"], band)
    storage = grade_storage(spec["storage"])
    residual = grade_residual_charge(spec["residual"], spec["withstand_voltage_v"])

    findings = list(route["findings"]) + list(storage["findings"]) + list(
        residual["findings"]
    )
    return {
        "item_id": item_id,
        "discharge_model": normalize_discharge_model(spec["discharge_model"]),
        "sensitivity_band": band,
        "obliged_controls": obliged_controls(band),
        "minimum_transfer_packaging": MINIMUM_TRANSFER_PACKAGING[band],
        "route": route,
        "storage": storage,
        "residual": residual,
        "findings": findings,
        "verdict": REGIME_COMPLIANT if not findings else REGIME_DEFICIENT,
        "compliant": not findings,
    }
