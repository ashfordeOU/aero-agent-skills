"""Telemetry-in-the-blind assessment.

Anchor: ECSS-E-ST-50C clause 5.5.4 (the spacecraft transmits telemetry the
ground can acquire when no uplink has been received). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the blind downlink configuration and the uplink-loss timeout.
2. Compare the configured timeout with the maximum the mission allows before
   blind telemetry has to be radiating.
3. Screen modulation, coding and rate against the set the receiving station
   can acquire with no uplink, and screen for any parameter that is only
   reachable through a telecommand.
4. Compute the worst-case free-space loss at maximum range and close the
   blind link budget to an energy-per-bit margin in decibel.
5. Report the achieved margin and the highest blind rate the budget would
   support at zero margin.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE_DB",
    "TIME_TOLERANCE_S",
    "BOLTZMANN_DBW_PER_K_HZ",
    "validate_blind_configuration",
    "free_space_loss_db",
    "rate_term_db",
    "blind_link_margin_db",
    "supportable_rate_bps",
    "arming_findings",
    "default_configuration_findings",
    "command_dependency_findings",
    "assess_telemetry_in_the_blind",
]

# Margin and timeout comparisons are differences that can land a few ULPs on
# the wrong side of an exact equality. Absorb the representation error here
# instead of relaxing the engineering limit.
MARGIN_TOLERANCE_DB = 1e-9
TIME_TOLERANCE_S = 1e-9

# Boltzmann constant expressed in dBW per kelvin per hertz.
BOLTZMANN_DBW_PER_K_HZ = -228.6


def _require_text(value, label):
    """Return a non-empty stripped string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _require_positive(value, label):
    """Return a positive finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_real(value, label):
    """Return a finite float of either sign or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _require_name_set(value, label):
    """Return a frozenset of acquirable option names or raise."""
    if isinstance(value, str) or not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence of names, got %r" % (label, value))
    names = set(_require_text(item, "%s entry" % label) for item in value)
    if not names:
        raise ValueError("%s must name at least one option" % label)
    return frozenset(names)


def validate_blind_configuration(config):
    """Return a normalised blind downlink configuration record."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping, got %r" % (config,))
    for key in ("frequency_mhz", "bit_rate_bps", "modulation", "coding",
                "uplink_loss_timeout_s"):
        if key not in config:
            raise ValueError("configuration missing required key '%s'" % key)
    needs_command = config.get("command_dependent_parameters", [])
    if isinstance(needs_command, str) or not isinstance(needs_command, (list, tuple)):
        raise ValueError("command_dependent_parameters must be a sequence of names")
    return {
        "frequency_mhz": _require_positive(config["frequency_mhz"], "frequency_mhz"),
        "bit_rate_bps": _require_positive(config["bit_rate_bps"], "bit_rate_bps"),
        "modulation": _require_text(config["modulation"], "modulation"),
        "coding": _require_text(config["coding"], "coding"),
        "uplink_loss_timeout_s": _require_positive(
            config["uplink_loss_timeout_s"], "uplink_loss_timeout_s"
        ),
        "command_dependent_parameters": [
            _require_text(item, "command-dependent parameter") for item in needs_command
        ],
    }


def free_space_loss_db(range_km, frequency_mhz):
    """Return the free-space path loss in decibel at a range and frequency."""
    distance = _require_positive(range_km, "range_km")
    frequency = _require_positive(frequency_mhz, "frequency_mhz")
    return 32.44 + 20.0 * math.log10(distance) + 20.0 * math.log10(frequency)


def rate_term_db(bit_rate_bps):
    """Return the decibel penalty of carrying a given bit rate."""
    rate = _require_positive(bit_rate_bps, "bit_rate_bps")
    return 10.0 * math.log10(rate)


def blind_link_margin_db(budget):
    """Return the achieved energy-per-bit margin of the blind downlink in decibel.

    budget keys: eirp_dbw, range_km, frequency_mhz, bit_rate_bps,
    station_g_over_t_dbk, required_ebn0_db, optional atmospheric_loss_db,
    polarisation_loss_db and implementation_loss_db.
    """
    if not isinstance(budget, dict):
        raise ValueError("budget must be a mapping")
    for key in ("eirp_dbw", "range_km", "frequency_mhz", "bit_rate_bps",
                "station_g_over_t_dbk", "required_ebn0_db"):
        if key not in budget:
            raise ValueError("budget missing required key '%s'" % key)
    eirp = _require_real(budget["eirp_dbw"], "eirp_dbw")
    g_over_t = _require_real(budget["station_g_over_t_dbk"], "station_g_over_t_dbk")
    required = _require_real(budget["required_ebn0_db"], "required_ebn0_db")
    atmospheric = _require_real(budget.get("atmospheric_loss_db", 0.0), "atmospheric_loss_db")
    polarisation = _require_real(budget.get("polarisation_loss_db", 0.0), "polarisation_loss_db")
    implementation = _require_real(
        budget.get("implementation_loss_db", 0.0), "implementation_loss_db"
    )
    for label, value in (
        ("atmospheric_loss_db", atmospheric),
        ("polarisation_loss_db", polarisation),
        ("implementation_loss_db", implementation),
    ):
        if value < 0.0:
            raise ValueError("%s is a loss and must be non-negative, got %g" % (label, value))
    path = free_space_loss_db(budget["range_km"], budget["frequency_mhz"])
    received_ebn0 = (
        eirp
        - path
        - atmospheric
        - polarisation
        + g_over_t
        - BOLTZMANN_DBW_PER_K_HZ
        - rate_term_db(budget["bit_rate_bps"])
    )
    return received_ebn0 - required - implementation


def supportable_rate_bps(budget):
    """Return the blind bit rate at which the same budget closes with zero margin."""
    margin = blind_link_margin_db(budget)
    rate = _require_positive(budget["bit_rate_bps"], "bit_rate_bps")
    return rate * math.pow(10.0, margin / 10.0)


def arming_findings(configured_timeout_s, required_max_timeout_s):
    """Return the findings for a blind mode that arms later than the mission allows."""
    configured = _require_positive(configured_timeout_s, "uplink_loss_timeout_s")
    allowed = _require_positive(required_max_timeout_s, "required_max_timeout_s")
    if math.isclose(configured, allowed, rel_tol=0.0, abs_tol=TIME_TOLERANCE_S):
        return []
    if configured > allowed:
        return [
            "blind mode arms %.6g s after uplink loss, later than the %.6g s the "
            "mission allows" % (configured, allowed)
        ]
    return []


def default_configuration_findings(config, acquirable):
    """Return the findings for parameters outside the station's blind-acquisition set."""
    record = validate_blind_configuration(config)
    if not isinstance(acquirable, dict):
        raise ValueError("acquirable must be a mapping of parameter to allowed values")
    for key in ("modulation", "coding", "bit_rate_bps"):
        if key not in acquirable:
            raise ValueError("acquirable missing required key '%s'" % key)
    findings = []
    for key in ("modulation", "coding"):
        allowed = _require_name_set(acquirable[key], "acquirable %s" % key)
        if record[key] not in allowed:
            findings.append(
                "blind %s '%s' is not one the station can acquire without an uplink"
                % (key, record[key])
            )
    rates = acquirable["bit_rate_bps"]
    if isinstance(rates, str) or not isinstance(rates, (list, tuple, set, frozenset)):
        raise ValueError("acquirable bit_rate_bps must be a sequence of rates")
    allowed_rates = [_require_positive(r, "acquirable bit rate") for r in rates]
    if not allowed_rates:
        raise ValueError("acquirable bit_rate_bps must list at least one rate")
    matched = any(
        math.isclose(record["bit_rate_bps"], r, rel_tol=1e-12, abs_tol=0.0)
        for r in allowed_rates
    )
    if not matched:
        findings.append(
            "blind bit rate %.6g bit/s is not a rate the station is configured to "
            "demodulate without an uplink" % record["bit_rate_bps"]
        )
    return findings


def command_dependency_findings(config):
    """Return the findings for blind parameters reachable only through a telecommand."""
    record = validate_blind_configuration(config)
    return [
        "blind parameter '%s' is set by telecommand, so it is unavailable in the "
        "state that triggers the mode" % name
        for name in record["command_dependent_parameters"]
    ]


def assess_telemetry_in_the_blind(spec):
    """Run the full clause 5.5.4 telemetry-in-the-blind assessment.

    spec keys: configuration, required_max_timeout_s, acquirable, budget.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("configuration", "required_max_timeout_s", "acquirable", "budget"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    record = validate_blind_configuration(spec["configuration"])
    budget = dict(spec["budget"])
    budget.setdefault("frequency_mhz", record["frequency_mhz"])
    budget.setdefault("bit_rate_bps", record["bit_rate_bps"])

    findings = []
    findings.extend(arming_findings(
        record["uplink_loss_timeout_s"], spec["required_max_timeout_s"]
    ))
    findings.extend(default_configuration_findings(record, spec["acquirable"]))
    findings.extend(command_dependency_findings(record))

    margin = blind_link_margin_db(budget)
    closes = margin > 0.0 or math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB
    )
    if not closes:
        findings.append(
            "worst-case blind link margin is %.3f dB at %.6g bit/s; the downlink does "
            "not close" % (margin, budget["bit_rate_bps"])
        )

    return {
        "configuration": record,
        "free_space_loss_db": free_space_loss_db(
            budget["range_km"], budget["frequency_mhz"]
        ),
        "margin_db": margin,
        "link_closes": closes,
        "supportable_rate_bps": supportable_rate_bps(budget),
        "compliant": not findings,
        "findings": findings,
    }
