"""Additional provisions for class 1 EEE parts used at high voltage or high microwave power.

Anchor: ECSS-Q-ST-60C clause 4.6.7 (additional provisions for class 1 parts in
high voltage and high power microwave use). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the application can be assessed at all: a part with no
   traceable identity, no stated rating, no stated electrode gap, or a working
   voltage above its own rating is stopped before any provision is derived.
2. Measure the electrical stress the application actually imposes: the voltage
   utilisation against the part rating, the pressure-gap product against the
   corona onset window, and the frequency-gap product against the multipaction
   susceptibility bound.
3. Record the design findings those measurements raise.
4. Derive the additional provisions the application owes from its voltage,
   ambient pressure, encapsulation state, microwave power and gap geometry.
5. Compare the provisions already closed against the owed set and return the
   outstanding ones and the coverage fraction.
6. Return one disposition: provisions-satisfied, provisions-outstanding,
   provisions-nonconforming or application-not-admissible.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "PROVISIONS",
    "BASELINE_PROVISIONS",
    "HIGH_VOLTAGE_THRESHOLD_V",
    "HIGH_MICROWAVE_POWER_THRESHOLD_W",
    "VOLTAGE_UTILISATION_LIMIT",
    "CORONA_PRESSURE_WINDOW_PA",
    "MULTIPACTION_FD_LIMIT_GHZ_MM",
    "application_admissibility",
    "voltage_utilisation",
    "voltage_utilisation_acceptable",
    "pressure_gap_product",
    "within_corona_window",
    "multipaction_fd_product",
    "multipaction_susceptible",
    "design_findings",
    "required_provisions",
    "ordered_provisions",
    "outstanding_provisions",
    "provision_coverage",
    "application_disposition",
    "assess_class_1_high_voltage_application",
]

# Utilisation ratios, pressure-gap products and frequency-gap products are
# float quotients and products; a case sitting exactly on a bound can land a
# few ULP on the wrong side. Absorb the representation error here, never by
# moving the bound itself.
BOUND_TOLERANCE = 1e-9

# Every additional provision, in the order it is performed. A provision is
# named once and ordered here so two engineers derive the same sequence.
PROVISIONS = (
    "high-voltage-design-review",
    "insulation-coordination-analysis",
    "partial-discharge-measurement",
    "corona-onset-verification",
    "encapsulation-and-venting-verification",
    "multipaction-analysis",
    "microwave-power-handling-verification",
    "high-voltage-lot-acceptance-test",
)

_PROVISION_ORDER = {name: index for index, name in enumerate(PROVISIONS)}

# Provisions a class 1 high voltage or high power microwave application owes
# whatever its geometry and ambient.
BASELINE_PROVISIONS = (
    "high-voltage-design-review",
    "insulation-coordination-analysis",
    "high-voltage-lot-acceptance-test",
)

# Working voltage at or above which the application counts as high voltage and
# owes a partial discharge measurement.
HIGH_VOLTAGE_THRESHOLD_V = 100.0

# Peak microwave power at or above which the application counts as high power.
HIGH_MICROWAVE_POWER_THRESHOLD_W = 10.0

# Fraction of the part rating the working voltage may occupy in class 1 use.
VOLTAGE_UTILISATION_LIMIT = 0.5

# Ambient pressure band, in pascal, where partial discharge onset is lowest and
# an unencapsulated gap breaks down at a fraction of its sea level voltage.
# Both bounds belong to the window.
CORONA_PRESSURE_WINDOW_PA = (1.0, 10000.0)

# Frequency-gap product, in gigahertz millimetre, at or below which a gap
# carrying microwave power is susceptible to a resonant electron avalanche.
MULTIPACTION_FD_LIMIT_GHZ_MM = 10.0


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_positive(value, label):
    """Return a validated strictly positive float or raise."""
    number = _require_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_flag(value, label):
    """Return a validated boolean or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(float(value))


def application_admissibility(application):
    """Return the reasons a high voltage application cannot be assessed.

    An empty list means the provisions may be derived. The reasons are ordered
    from identity outwards, because a part nobody can name is not a derating
    problem.
    """
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping, got %r" % (application,))
    reasons = []
    identity = application.get("part_id")
    if not isinstance(identity, str) or not identity.strip():
        reasons.append("part-identity-not-traceable")
    rated = application.get("rated_voltage_v")
    if not _is_number(rated) or float(rated) <= 0.0:
        reasons.append("rated-voltage-not-stated")
    gap = application.get("electrode_gap_mm")
    if not _is_number(gap) or float(gap) <= 0.0:
        reasons.append("electrode-gap-not-stated")
    working = application.get("working_voltage_v")
    if not _is_number(working) or float(working) < 0.0:
        reasons.append("working-voltage-not-stated")
    elif _is_number(rated) and float(rated) > 0.0:
        if float(working) > float(rated) * (1.0 + BOUND_TOLERANCE):
            reasons.append("working-voltage-exceeds-part-rating")
    return reasons


def voltage_utilisation(working_voltage_v, rated_voltage_v):
    """Return the fraction of the part rating the working voltage occupies."""
    working = _require_number(working_voltage_v, "working_voltage_v")
    rated = _require_positive(rated_voltage_v, "rated_voltage_v")
    return working / rated


def voltage_utilisation_acceptable(utilisation):
    """Return whether a utilisation sits at or under the class 1 limit."""
    ratio = _require_number(utilisation, "utilisation")
    return ratio <= VOLTAGE_UTILISATION_LIMIT + BOUND_TOLERANCE


def pressure_gap_product(pressure_pa, gap_mm):
    """Return the pressure-gap product in pascal metre."""
    pressure = _require_number(pressure_pa, "pressure_pa")
    gap = _require_positive(gap_mm, "gap_mm")
    return pressure * gap / 1000.0


def within_corona_window(pressure_pa):
    """Return whether an ambient pressure sits inside the corona onset window.

    Both bounds belong to the window: a part sitting exactly on a bound is
    inside it, because the bound is where the onset voltage is already low.
    """
    pressure = _require_number(pressure_pa, "pressure_pa")
    low, high = CORONA_PRESSURE_WINDOW_PA
    return (pressure >= low - BOUND_TOLERANCE) and (pressure <= high + BOUND_TOLERANCE)


def multipaction_fd_product(frequency_ghz, gap_mm):
    """Return the frequency-gap product in gigahertz millimetre."""
    frequency = _require_number(frequency_ghz, "frequency_ghz")
    gap = _require_positive(gap_mm, "gap_mm")
    return frequency * gap


def multipaction_susceptible(fd_product, peak_power_w):
    """Return whether a powered gap sits in the multipaction susceptible band.

    The bound belongs to the susceptible band; a gap exactly on it is treated
    as susceptible, because the cost of the analysis is far below the cost of
    a discharge in orbit.
    """
    product = _require_number(fd_product, "fd_product")
    power = _require_number(peak_power_w, "peak_power_w")
    if product <= 0.0:
        return False
    if power < HIGH_MICROWAVE_POWER_THRESHOLD_W - BOUND_TOLERANCE:
        return False
    return product <= MULTIPACTION_FD_LIMIT_GHZ_MM + BOUND_TOLERANCE


def design_findings(application):
    """Return the design nonconformities the application raises.

    application keys read here: working_voltage_v, rated_voltage_v,
    operating_pressure_pa, encapsulated and vented.
    """
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping, got %r" % (application,))
    findings = []
    utilisation = voltage_utilisation(application.get("working_voltage_v", 0.0),
                                      application.get("rated_voltage_v"))
    if not voltage_utilisation_acceptable(utilisation):
        findings.append("voltage-utilisation-above-class-1-limit")
    pressure = _require_number(application.get("operating_pressure_pa", 0.0),
                               "operating_pressure_pa")
    encapsulated = _require_flag(application.get("encapsulated", False), "encapsulated")
    vented = _require_flag(application.get("vented", False), "vented")
    if within_corona_window(pressure) and not encapsulated:
        findings.append("unencapsulated-gap-inside-corona-window")
    if encapsulated and not vented:
        findings.append("sealed-cavity-without-vent-path")
    return findings


def ordered_provisions(provisions):
    """Return the provisions in performance order, rejecting unknown names."""
    if not isinstance(provisions, (list, tuple, set, frozenset)):
        raise ValueError("provisions must be a sequence or set")
    names = []
    for item in provisions:
        name = _require_text(item, "provision").casefold()
        if name not in _PROVISION_ORDER:
            raise ValueError(
                "unknown provision %r; expected one of %r" % (item, list(PROVISIONS))
            )
        if name in names:
            raise ValueError("provision %r listed twice" % name)
        names.append(name)
    return sorted(names, key=lambda name: _PROVISION_ORDER[name])


def required_provisions(application):
    """Return the additional provisions the application owes, in order.

    application keys read here: working_voltage_v, operating_pressure_pa,
    encapsulated, vented, microwave_peak_power_w, microwave_frequency_ghz and
    electrode_gap_mm.
    """
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping, got %r" % (application,))
    owed = set(BASELINE_PROVISIONS)
    working = _require_number(application.get("working_voltage_v", 0.0),
                              "working_voltage_v")
    if working >= HIGH_VOLTAGE_THRESHOLD_V - BOUND_TOLERANCE:
        owed.add("partial-discharge-measurement")
    pressure = _require_number(application.get("operating_pressure_pa", 0.0),
                               "operating_pressure_pa")
    encapsulated = _require_flag(application.get("encapsulated", False), "encapsulated")
    vented = _require_flag(application.get("vented", False), "vented")
    if within_corona_window(pressure):
        owed.add("corona-onset-verification")
    if not (encapsulated and vented):
        owed.add("encapsulation-and-venting-verification")
    power = _require_number(application.get("microwave_peak_power_w", 0.0),
                            "microwave_peak_power_w")
    if power >= HIGH_MICROWAVE_POWER_THRESHOLD_W - BOUND_TOLERANCE:
        owed.add("microwave-power-handling-verification")
    frequency = _require_number(application.get("microwave_frequency_ghz", 0.0),
                                "microwave_frequency_ghz")
    gap = _require_positive(application.get("electrode_gap_mm"), "electrode_gap_mm")
    if multipaction_susceptible(multipaction_fd_product(frequency, gap), power):
        owed.add("multipaction-analysis")
    return ordered_provisions(owed)


def outstanding_provisions(owed, closed):
    """Return the owed provisions not yet closed, in performance order."""
    owed_names = ordered_provisions(owed)
    if not isinstance(closed, (list, tuple, set, frozenset)):
        raise ValueError("closed must be a sequence or set")
    done = set()
    for item in closed:
        name = _require_text(item, "closed provision").casefold()
        if name not in _PROVISION_ORDER:
            raise ValueError(
                "unknown provision %r; expected one of %r" % (item, list(PROVISIONS))
            )
        done.add(name)
    return [name for name in owed_names if name not in done]


def provision_coverage(owed, closed):
    """Return the fraction of the owed provisions already closed."""
    owed_names = ordered_provisions(owed)
    if not owed_names:
        raise ValueError("owed must name at least one provision")
    remaining = outstanding_provisions(owed_names, closed)
    return (len(owed_names) - len(remaining)) / float(len(owed_names))


def application_disposition(admissibility_reasons, findings, remaining):
    """Return the disposition implied by the assessment state."""
    for label, value in (("admissibility_reasons", admissibility_reasons),
                         ("findings", findings), ("remaining", remaining)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence, got %r" % (label, value))
    if admissibility_reasons:
        return "application-not-admissible"
    if findings:
        return "provisions-nonconforming"
    if remaining:
        return "provisions-outstanding"
    return "provisions-satisfied"


def assess_class_1_high_voltage_application(application):
    """Assess one clause 4.6.7 high voltage or high power microwave application.

    application keys: part_id, rated_voltage_v, working_voltage_v,
    electrode_gap_mm, and the optional operating_pressure_pa, encapsulated,
    vented, microwave_peak_power_w, microwave_frequency_ghz and
    provisions_closed.
    """
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping")
    reasons = application_admissibility(application)
    if reasons:
        return {
            "admissibility_reasons": reasons,
            "admissible": False,
            "voltage_utilisation": None,
            "fd_product_ghz_mm": None,
            "pressure_gap_product_pa_m": None,
            "findings": [],
            "provisions": [],
            "outstanding_provisions": [],
            "provision_coverage": 0.0,
            "disposition": "application-not-admissible",
            "cleared_for_flight": False,
        }
    utilisation = voltage_utilisation(application.get("working_voltage_v", 0.0),
                                      application["rated_voltage_v"])
    gap = _require_positive(application["electrode_gap_mm"], "electrode_gap_mm")
    fd_product = multipaction_fd_product(
        application.get("microwave_frequency_ghz", 0.0), gap)
    pd_product = pressure_gap_product(
        application.get("operating_pressure_pa", 0.0), gap)
    findings = design_findings(application)
    owed = required_provisions(application)
    closed = application.get("provisions_closed", [])
    remaining = outstanding_provisions(owed, closed)
    coverage = provision_coverage(owed, closed)
    disposition = application_disposition(reasons, findings, remaining)
    return {
        "admissibility_reasons": reasons,
        "admissible": True,
        "voltage_utilisation": utilisation,
        "fd_product_ghz_mm": fd_product,
        "pressure_gap_product_pa_m": pd_product,
        "findings": findings,
        "provisions": owed,
        "outstanding_provisions": remaining,
        "provision_coverage": coverage,
        "disposition": disposition,
        "cleared_for_flight": disposition == "provisions-satisfied",
    }
