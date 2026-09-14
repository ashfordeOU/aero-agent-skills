"""MMIC application envelope at the lowest commercial assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.6.5 (application of microwave monolithic
integrated circuits where the programme works at the lowest commercial
assurance class). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the construction the part actually declares. A technology and a
   package form that are not in the recognised set close the assessment: a
   channel ceiling cannot be looked up for a device nobody has described.
2. Fold a pulsed duty cycle into an effective dissipation, so a part run in
   bursts is graded on what it dissipates rather than on its peak.
3. Raise the channel temperature from the baseplate along the declared
   thermal path, and take the margin against the applied ceiling: the lower
   of the technology ceiling and the part rating, with the allowance the
   lowest class holds back removed from it.
4. Invert the same path twice to publish the envelope rather than only the
   verdict: the dissipation the application may still spend at this baseplate
   and the baseplate it may still reach at this dissipation.
5. Cap the applied drive at a derated share of the rated input.
6. Oblige humidity control behind a non-hermetic package, and size the lot
   sample the application owes in place of the screening it did not buy.

All arithmetic here is linear so the result is the same on every platform.
"""

import math

__all__ = [
    "ENVELOPE_TOLERANCE",
    "TECHNOLOGY_CHANNEL_CEILING_C",
    "PACKAGE_FORMS",
    "NON_HERMETIC_FORMS",
    "MOISTURE_OBLIGATION",
    "LOWEST_CLASS_CHANNEL_ALLOWANCE_K",
    "DEFAULT_DRIVE_DERATING",
    "DEFAULT_LOT_SAMPLE_PERCENT",
    "MINIMUM_LOT_SAMPLE",
    "APPLICATION_VERDICTS",
    "validate_identifier",
    "technology_ceiling",
    "package_form",
    "effective_dissipation",
    "channel_temperature",
    "applied_channel_ceiling",
    "allowed_dissipation",
    "allowed_baseplate",
    "lot_sample_size",
    "assess_mmic_application",
]

# Margins are sums and quotients of decimal inputs that can land a few ULPs
# either side of a bound they should sit exactly on. Absorb that here, never
# by moving the bound.
ENVELOPE_TOLERANCE = 1e-9

# Channel ceiling in degrees Celsius that each recognised technology is graded
# against before the lowest-class allowance is held back.
TECHNOLOGY_CHANNEL_CEILING_C = {
    "gaas-phemt": 150.0,
    "gaas-mesfet": 150.0,
    "gaas-hbt": 150.0,
    "gan-hemt": 200.0,
    "inp-hemt": 125.0,
    "sige-bicmos": 125.0,
    "silicon-cmos": 125.0,
}

PACKAGE_FORMS = (
    "bare-die-on-carrier",
    "hermetic-ceramic",
    "hermetic-metal",
    "plastic-overmoulded",
)

NON_HERMETIC_FORMS = ("bare-die-on-carrier", "plastic-overmoulded")

MOISTURE_OBLIGATION = "humidity-controlled-assembly-and-storage"

# Degrees held back from the channel ceiling because the lowest class buys no
# part-level evaluation to stand behind the manufacturer's figure.
LOWEST_CLASS_CHANNEL_ALLOWANCE_K = 20.0

# Share of the rated input power a lowest-class application may drive.
DEFAULT_DRIVE_DERATING = 0.8

# Integer percent of a delivered lot the application samples in place of the
# lot acceptance the lowest class did not buy, and the floor under it.
DEFAULT_LOT_SAMPLE_PERCENT = 5
MINIMUM_LOT_SAMPLE = 3

APPLICATION_VERDICTS = (
    "application-accepted",
    "accepted-with-moisture-obligation",
    "reduce-applied-stress",
    "refuse-undeclared-construction",
)


def validate_identifier(value, label):
    """Return a non-blank stripped identifier, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_number(value, label):
    """Return a finite real number, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_positive(value, label):
    """Return a strictly positive finite real number, or raise."""
    number = _require_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _require_non_negative(value, label):
    """Return a non-negative finite real number, or raise."""
    number = _require_number(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _require_fraction(value, label):
    """Return a finite real number inside the unit interval, or raise."""
    number = _require_number(value, label)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return number


def _within(value, bound):
    """Return True when value stays at or under a bound, an exact landing in."""
    return value < bound or math.isclose(
        value, bound, rel_tol=0.0, abs_tol=ENVELOPE_TOLERANCE
    )


def technology_ceiling(technology):
    """Return the channel ceiling of a recognised MMIC technology."""
    name = validate_identifier(technology, "technology").lower()
    if name not in TECHNOLOGY_CHANNEL_CEILING_C:
        raise ValueError(
            "technology %s is not in the recognised set; a channel ceiling "
            "cannot be looked up for an undeclared construction" % name
        )
    return TECHNOLOGY_CHANNEL_CEILING_C[name]


def package_form(form):
    """Return a recognised package form, or raise."""
    name = validate_identifier(form, "package form").lower()
    if name not in PACKAGE_FORMS:
        raise ValueError("package form %s is not in the recognised set" % name)
    return name


def effective_dissipation(peak_watts, duty_cycle=1.0):
    """Return the dissipation a pulsed part presents to its thermal path."""
    peak = _require_non_negative(peak_watts, "peak dissipation")
    duty = _require_fraction(duty_cycle, "duty cycle")
    if duty <= 0.0:
        raise ValueError("duty cycle must be positive")
    return peak * duty


def channel_temperature(baseplate_c, dissipation_w, thermal_resistance_k_per_w):
    """Return the channel temperature reached along the declared path."""
    base = _require_number(baseplate_c, "baseplate temperature")
    power = _require_non_negative(dissipation_w, "dissipation")
    path = _require_positive(thermal_resistance_k_per_w, "thermal resistance")
    return base + power * path


def applied_channel_ceiling(technology, rated_channel_c, allowance_k=None):
    """Return the ceiling the application is graded against."""
    ceiling = technology_ceiling(technology)
    rated = _require_number(rated_channel_c, "rated channel temperature")
    allowance = _require_non_negative(
        LOWEST_CLASS_CHANNEL_ALLOWANCE_K if allowance_k is None else allowance_k,
        "channel allowance",
    )
    applied = min(ceiling, rated) - allowance
    if applied <= 0.0:
        raise ValueError(
            "the allowance leaves no usable channel ceiling for %s" % technology
        )
    return applied


def allowed_dissipation(ceiling_c, baseplate_c, thermal_resistance_k_per_w):
    """Return the dissipation still available at this baseplate temperature."""
    ceiling = _require_number(ceiling_c, "channel ceiling")
    base = _require_number(baseplate_c, "baseplate temperature")
    path = _require_positive(thermal_resistance_k_per_w, "thermal resistance")
    headroom = ceiling - base
    if headroom <= 0.0:
        return 0.0
    return headroom / path


def allowed_baseplate(ceiling_c, dissipation_w, thermal_resistance_k_per_w):
    """Return the baseplate temperature still available at this dissipation."""
    ceiling = _require_number(ceiling_c, "channel ceiling")
    power = _require_non_negative(dissipation_w, "dissipation")
    path = _require_positive(thermal_resistance_k_per_w, "thermal resistance")
    return ceiling - power * path


def lot_sample_size(lot_size, percent=None, minimum=None):
    """Return the devices sampled from a delivered lot, by exact integer rule."""
    if isinstance(lot_size, bool) or not isinstance(lot_size, int):
        raise ValueError("lot_size must be an integer, got %r" % (lot_size,))
    if lot_size <= 0:
        raise ValueError("lot_size must be positive, got %d" % lot_size)
    share = DEFAULT_LOT_SAMPLE_PERCENT if percent is None else percent
    if isinstance(share, bool) or not isinstance(share, int):
        raise ValueError("percent must be an integer, got %r" % (share,))
    if share <= 0 or share > 100:
        raise ValueError("percent must lie in (0, 100], got %d" % share)
    floor = MINIMUM_LOT_SAMPLE if minimum is None else minimum
    if isinstance(floor, bool) or not isinstance(floor, int):
        raise ValueError("minimum must be an integer, got %r" % (floor,))
    if floor < 1:
        raise ValueError("minimum must be at least one device")
    proportional = -(-lot_size * share // 100)
    return min(lot_size, max(floor, proportional))


def assess_mmic_application(record):
    """Run the full clause 6.6.5 lowest-class MMIC application assessment.

    record keys: reference, technology, package_form, rated_channel_c,
    baseplate_c, peak_dissipation_w, thermal_resistance_k_per_w,
    rated_input_w, applied_input_w, lot_size. Optional keys: duty_cycle,
    humidity_controlled, drive_derating, channel_allowance_k,
    lot_sample_percent.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in (
        "reference",
        "technology",
        "package_form",
        "rated_channel_c",
        "baseplate_c",
        "peak_dissipation_w",
        "thermal_resistance_k_per_w",
        "rated_input_w",
        "applied_input_w",
        "lot_size",
    ):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    reference = validate_identifier(record["reference"], "part reference")

    # Input typing is an error the caller has to fix; an unrecognised
    # construction is a verdict this clause owes an answer to. Validate the
    # numbers first so the two never get confused for one another.
    rated_channel = _require_number(
        record["rated_channel_c"], "rated channel temperature"
    )
    allowance = _require_non_negative(
        record.get("channel_allowance_k", LOWEST_CLASS_CHANNEL_ALLOWANCE_K),
        "channel allowance",
    )

    construction_findings = []
    technology = None
    ceiling = None
    form = None
    try:
        technology_ceiling(record["technology"])
        technology = validate_identifier(record["technology"], "technology").lower()
    except ValueError as error:
        construction_findings.append(
            {"severity": 0, "reference": reference, "detail": str(error)}
        )
    try:
        form = package_form(record["package_form"])
    except ValueError as error:
        construction_findings.append(
            {"severity": 0, "reference": reference, "detail": str(error)}
        )
    if technology is not None:
        ceiling = applied_channel_ceiling(technology, rated_channel, allowance)

    if construction_findings:
        return {
            "reference": reference,
            "technology": technology,
            "package_form": form,
            "applied_channel_ceiling_c": ceiling,
            "effective_dissipation_w": None,
            "channel_temperature_c": None,
            "channel_margin_k": None,
            "channel_within_ceiling": False,
            "allowed_dissipation_w": None,
            "allowed_baseplate_c": None,
            "drive_cap_w": None,
            "drive_margin_w": None,
            "drive_within_cap": False,
            "moisture_obligations": (),
            "lot_sample_size": None,
            "findings": sorted(
                construction_findings, key=lambda item: item["detail"]
            ),
            "verdict": "refuse-undeclared-construction",
        }

    path = _require_positive(
        record["thermal_resistance_k_per_w"], "thermal resistance"
    )
    dissipation = effective_dissipation(
        record["peak_dissipation_w"], record.get("duty_cycle", 1.0)
    )
    baseplate = _require_number(record["baseplate_c"], "baseplate temperature")
    channel = channel_temperature(baseplate, dissipation, path)
    channel_margin = ceiling - channel
    channel_ok = _within(channel, ceiling)

    derating = _require_fraction(
        record.get("drive_derating", DEFAULT_DRIVE_DERATING), "drive derating"
    )
    if derating <= 0.0:
        raise ValueError("drive derating must be positive")
    rated_input = _require_positive(record["rated_input_w"], "rated input power")
    applied_input = _require_non_negative(
        record["applied_input_w"], "applied input power"
    )
    drive_cap = rated_input * derating
    drive_ok = _within(applied_input, drive_cap)

    humidity_controlled = record.get("humidity_controlled", False)
    if not isinstance(humidity_controlled, bool):
        raise ValueError("humidity_controlled must be a boolean")
    obligations = ()
    if form in NON_HERMETIC_FORMS and not humidity_controlled:
        obligations = (MOISTURE_OBLIGATION,)

    sample = lot_sample_size(
        record["lot_size"], record.get("lot_sample_percent")
    )

    findings = []
    if not channel_ok:
        findings.append(
            {
                "severity": 0,
                "reference": reference,
                "detail": "channel reaches %.4f C against a %.4f C applied "
                "ceiling" % (channel, ceiling),
            }
        )
    if not drive_ok:
        findings.append(
            {
                "severity": 0,
                "reference": reference,
                "detail": "applied drive of %.4f W exceeds the %.4f W derated "
                "cap" % (applied_input, drive_cap),
            }
        )
    if obligations:
        findings.append(
            {
                "severity": 1,
                "reference": reference,
                "detail": "a %s package carries the %s obligation"
                % (form, MOISTURE_OBLIGATION),
            }
        )
    findings.sort(key=lambda item: (item["severity"], item["detail"]))

    if not channel_ok or not drive_ok:
        verdict = "reduce-applied-stress"
    elif obligations:
        verdict = "accepted-with-moisture-obligation"
    else:
        verdict = "application-accepted"

    return {
        "reference": reference,
        "technology": technology,
        "package_form": form,
        "applied_channel_ceiling_c": ceiling,
        "effective_dissipation_w": dissipation,
        "channel_temperature_c": channel,
        "channel_margin_k": channel_margin,
        "channel_within_ceiling": channel_ok,
        "allowed_dissipation_w": allowed_dissipation(ceiling, baseplate, path),
        "allowed_baseplate_c": allowed_baseplate(ceiling, dissipation, path),
        "drive_cap_w": drive_cap,
        "drive_margin_w": drive_cap - applied_input,
        "drive_within_cap": drive_ok,
        "moisture_obligations": obligations,
        "lot_sample_size": sample,
        "findings": findings,
        "verdict": verdict,
    }
