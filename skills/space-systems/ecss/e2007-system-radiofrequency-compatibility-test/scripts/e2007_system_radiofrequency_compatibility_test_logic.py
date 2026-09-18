"""System-level radiofrequency compatibility test matrix.

Anchor: ECSS-E-ST-20-07C clause 5.3.8 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Enumerate, for every onboard emitter, the emission products the
   system test has to account for: the fundamental, the harmonic series
   up to the declared order, and each declared spurious line.
2. Drop the products that this clause puts outside its own test. A
   passive intermodulation product is generated in the passive hardware
   rather than by the emitter, and it is verified by a separate
   dedicated activity; carrying it in this matrix hides the cases this
   test does own. Excluded products are still reported, by name and
   reason, so the exclusion is visible rather than silent.
3. Couple each in-scope product into each receiver through the declared
   antenna gains and the pair isolation, and decide whether the product
   lands inside the receiver passband or outside it, where the receiver
   rejection applies.
4. Compare the coupled level with the effective susceptibility of the
   receiver and take the margin. A pair whose margin falls short of the
   required value, and every pair coupling in band at all, has to be
   exercised at system level rather than argued on paper.
5. Confirm that the executed matrix actually covers every case the
   analysis made mandatory, and that the two units of a mandatory case
   can be powered in a common operating mode - a case whose units never
   run together is not a case.

Levels are in dBm, gains and isolation in dB, frequencies in MHz, so
every step of the coupling chain is an addition and the margin is exact
arithmetic rather than a ratio of powers.

Stdlib only, offline, deterministic.
"""

MECHANISM_FUNDAMENTAL = "fundamental"
MECHANISM_HARMONIC = "harmonic"
MECHANISM_SPURIOUS = "spurious"
MECHANISM_PASSIVE_INTERMODULATION = "passive-intermodulation"
VALID_MECHANISMS = (
    MECHANISM_FUNDAMENTAL,
    MECHANISM_HARMONIC,
    MECHANISM_SPURIOUS,
    MECHANISM_PASSIVE_INTERMODULATION,
)

# Clause 5.3.8 scopes the system compatibility test to emitter-generated
# products; passive intermodulation is verified by its own activity.
EXCLUDED_MECHANISMS = (MECHANISM_PASSIVE_INTERMODULATION,)

RESULT_PASS = "pass"
RESULT_FAIL = "fail"
VALID_RESULTS = (RESULT_PASS, RESULT_FAIL)

BAND_IN = "in-band"
BAND_OUT = "out-of-band"

# Default harmonic order the matrix is built out to, and the extra
# fall-off each further order brings beyond the declared suppression.
DEFAULT_MAX_HARMONIC_ORDER = 5
HARMONIC_ROLLOFF_DB_PER_ORDER = 6.0

# Margin a coupled product must keep below the receiver susceptibility
# before the pair can be argued rather than exercised.
DEFAULT_REQUIRED_MARGIN_DB = 6.0

# A margin is a difference of decibel sums and a passband edge is a
# halved bandwidth, so a case sitting exactly on a bound can land a few
# units in the last place either side. These tolerances are far below
# any instrument resolution and absorb that representation error
# without relaxing the bound itself.
MARGIN_TOLERANCE_DB = 1.0e-9
FREQUENCY_TOLERANCE_MHZ = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _modes(label, value):
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("%s must be a non-empty sequence of mode names" % label)
    modes = []
    for mode in value:
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError("%s entries must be non-empty strings" % label)
        modes.append(mode)
    return tuple(modes)


def validate_emitter(emitter):
    """Validate one emitter record and return a normalized copy."""
    if not isinstance(emitter, dict):
        raise ValueError("emitter must be a mapping")
    emitter_id = emitter.get("id")
    if not isinstance(emitter_id, str) or not emitter_id.strip():
        raise ValueError("emitter needs a non-empty string id")
    frequency = _numeric("emitter %s frequency_mhz" % emitter_id,
                         emitter.get("frequency_mhz"))
    if frequency <= 0.0:
        raise ValueError("emitter %s frequency_mhz must be positive" % emitter_id)
    spurious = emitter.get("spurious_lines", [])
    if not isinstance(spurious, (list, tuple)):
        raise ValueError("emitter %s spurious_lines must be a sequence" % emitter_id)
    lines = []
    for line in spurious:
        if not isinstance(line, dict):
            raise ValueError("emitter %s spurious line must be a mapping" % emitter_id)
        line_frequency = _numeric(
            "emitter %s spurious frequency_mhz" % emitter_id, line.get("frequency_mhz")
        )
        if line_frequency <= 0.0:
            raise ValueError(
                "emitter %s spurious frequency_mhz must be positive" % emitter_id
            )
        mechanism = line.get("mechanism", MECHANISM_SPURIOUS)
        if mechanism not in VALID_MECHANISMS:
            raise ValueError(
                "emitter %s spurious line has unknown mechanism %r (expected one of %s)"
                % (emitter_id, mechanism, ", ".join(VALID_MECHANISMS))
            )
        lines.append(
            {
                "frequency_mhz": line_frequency,
                "level_dbc": _numeric(
                    "emitter %s spurious level_dbc" % emitter_id,
                    line.get("level_dbc", -60.0),
                ),
                "mechanism": mechanism,
            }
        )
    return {
        "id": emitter_id,
        "frequency_mhz": frequency,
        "power_dbm": _numeric("emitter %s power_dbm" % emitter_id,
                              emitter.get("power_dbm")),
        "antenna_gain_dbi": _numeric(
            "emitter %s antenna_gain_dbi" % emitter_id,
            emitter.get("antenna_gain_dbi", 0.0),
        ),
        "harmonic_suppression_db": _numeric(
            "emitter %s harmonic_suppression_db" % emitter_id,
            emitter.get("harmonic_suppression_db", 40.0),
            0.0,
        ),
        "spurious_lines": tuple(lines),
        "operating_modes": _modes(
            "emitter %s operating_modes" % emitter_id,
            emitter.get("operating_modes", ("transmit",)),
        ),
    }


def validate_receiver(receiver):
    """Validate one receiver record and return a normalized copy."""
    if not isinstance(receiver, dict):
        raise ValueError("receiver must be a mapping")
    receiver_id = receiver.get("id")
    if not isinstance(receiver_id, str) or not receiver_id.strip():
        raise ValueError("receiver needs a non-empty string id")
    centre = _numeric("receiver %s centre_frequency_mhz" % receiver_id,
                      receiver.get("centre_frequency_mhz"))
    if centre <= 0.0:
        raise ValueError("receiver %s centre_frequency_mhz must be positive" % receiver_id)
    bandwidth = _numeric("receiver %s bandwidth_mhz" % receiver_id,
                         receiver.get("bandwidth_mhz"))
    if bandwidth <= 0.0:
        raise ValueError("receiver %s bandwidth_mhz must be positive" % receiver_id)
    return {
        "id": receiver_id,
        "centre_frequency_mhz": centre,
        "bandwidth_mhz": bandwidth,
        "susceptibility_dbm": _numeric(
            "receiver %s susceptibility_dbm" % receiver_id,
            receiver.get("susceptibility_dbm"),
        ),
        "antenna_gain_dbi": _numeric(
            "receiver %s antenna_gain_dbi" % receiver_id,
            receiver.get("antenna_gain_dbi", 0.0),
        ),
        "out_of_band_rejection_db": _numeric(
            "receiver %s out_of_band_rejection_db" % receiver_id,
            receiver.get("out_of_band_rejection_db", 30.0),
            0.0,
        ),
        "operating_modes": _modes(
            "receiver %s operating_modes" % receiver_id,
            receiver.get("operating_modes", ("receive",)),
        ),
    }


def emission_products(emitter, max_harmonic_order=DEFAULT_MAX_HARMONIC_ORDER):
    """Products one emitter puts on the system test matrix."""
    norm = validate_emitter(emitter)
    if not isinstance(max_harmonic_order, int) or isinstance(max_harmonic_order, bool):
        raise ValueError("max_harmonic_order must be an integer")
    if max_harmonic_order < 1:
        raise ValueError("max_harmonic_order must be >= 1")
    products = [
        {
            "emitter_id": norm["id"],
            "frequency_mhz": norm["frequency_mhz"],
            "level_dbm": norm["power_dbm"],
            "mechanism": MECHANISM_FUNDAMENTAL,
            "order": 1,
        }
    ]
    for order in range(2, max_harmonic_order + 1):
        products.append(
            {
                "emitter_id": norm["id"],
                "frequency_mhz": norm["frequency_mhz"] * order,
                "level_dbm": norm["power_dbm"]
                - norm["harmonic_suppression_db"]
                - HARMONIC_ROLLOFF_DB_PER_ORDER * (order - 2),
                "mechanism": MECHANISM_HARMONIC,
                "order": order,
            }
        )
    for line in norm["spurious_lines"]:
        products.append(
            {
                "emitter_id": norm["id"],
                "frequency_mhz": line["frequency_mhz"],
                "level_dbm": norm["power_dbm"] + line["level_dbc"],
                "mechanism": line["mechanism"],
                "order": 1,
            }
        )
    return products


def is_in_test_scope(mechanism):
    """True when this clause's system test owns the product mechanism."""
    if mechanism not in VALID_MECHANISMS:
        raise ValueError(
            "unknown mechanism %r (expected one of %s)"
            % (mechanism, ", ".join(VALID_MECHANISMS))
        )
    return mechanism not in EXCLUDED_MECHANISMS


def band_of_product(product_frequency_mhz, receiver):
    """Whether a product lands inside the receiver passband."""
    frequency = _numeric("product_frequency_mhz", product_frequency_mhz)
    if frequency <= 0.0:
        raise ValueError("product_frequency_mhz must be positive")
    norm = validate_receiver(receiver)
    half = norm["bandwidth_mhz"] / 2.0
    separation = abs(frequency - norm["centre_frequency_mhz"])
    if separation <= half + FREQUENCY_TOLERANCE_MHZ:
        return BAND_IN
    return BAND_OUT


def coupled_level_dbm(product_level_dbm, emitter_gain_dbi, receiver_gain_dbi,
                      isolation_db):
    """Level a product presents at the receiver input, in dBm."""
    level = _numeric("product_level_dbm", product_level_dbm)
    tx_gain = _numeric("emitter_gain_dbi", emitter_gain_dbi)
    rx_gain = _numeric("receiver_gain_dbi", receiver_gain_dbi)
    isolation = _numeric("isolation_db", isolation_db, 0.0)
    return level + tx_gain + rx_gain - isolation


def effective_susceptibility_dbm(receiver, band):
    """Receiver susceptibility with the out-of-band rejection applied."""
    norm = validate_receiver(receiver)
    if band not in (BAND_IN, BAND_OUT):
        raise ValueError("band must be %r or %r, got %r" % (BAND_IN, BAND_OUT, band))
    if band == BAND_IN:
        return norm["susceptibility_dbm"]
    return norm["susceptibility_dbm"] + norm["out_of_band_rejection_db"]


def interference_margin_db(coupled_dbm, susceptibility_dbm):
    """Margin between the coupled level and the susceptibility, in dB."""
    coupled = _numeric("coupled_dbm", coupled_dbm)
    threshold = _numeric("susceptibility_dbm", susceptibility_dbm)
    return threshold - coupled


def modes_can_coexist(emitter, receiver):
    """True when the two units share at least one operating mode."""
    tx = validate_emitter(emitter)
    rx = validate_receiver(receiver)
    return bool(set(tx["operating_modes"]) & set(rx["operating_modes"]))


def isolation_for_pair(isolations, emitter_id, receiver_id):
    """Declared isolation for one emitter/receiver pair, in dB."""
    if not isinstance(isolations, dict):
        raise ValueError("isolations must be a mapping")
    key = (emitter_id, receiver_id)
    if key not in isolations:
        raise ValueError(
            "no declared isolation for pair %s -> %s" % (emitter_id, receiver_id)
        )
    return _numeric("isolation for %s -> %s" % (emitter_id, receiver_id),
                    isolations[key], 0.0)


def build_test_matrix(system):
    """Build every emitter/receiver/product case for the system test."""
    if not isinstance(system, dict):
        raise ValueError("system must be a mapping")
    emitters = system.get("emitters")
    receivers = system.get("receivers")
    if not isinstance(emitters, list) or not emitters:
        raise ValueError("system needs a non-empty emitters list")
    if not isinstance(receivers, list) or not receivers:
        raise ValueError("system needs a non-empty receivers list")
    isolations = system.get("isolations", {})
    required_margin = _numeric(
        "required_margin_db",
        system.get("required_margin_db", DEFAULT_REQUIRED_MARGIN_DB),
    )
    max_order = system.get("max_harmonic_order", DEFAULT_MAX_HARMONIC_ORDER)

    normalized_emitters = []
    seen = set()
    for emitter in emitters:
        norm = validate_emitter(emitter)
        if norm["id"] in seen:
            raise ValueError("duplicate emitter id %r" % (norm["id"],))
        seen.add(norm["id"])
        normalized_emitters.append(norm)
    normalized_receivers = []
    seen = set()
    for receiver in receivers:
        norm = validate_receiver(receiver)
        if norm["id"] in seen:
            raise ValueError("duplicate receiver id %r" % (norm["id"],))
        seen.add(norm["id"])
        normalized_receivers.append(norm)

    cases = []
    excluded = []
    for emitter in normalized_emitters:
        for product in emission_products(emitter, max_order):
            for receiver in normalized_receivers:
                case_id = "%s/%s/%s/%d" % (
                    emitter["id"], receiver["id"], product["mechanism"],
                    product["order"],
                )
                if not is_in_test_scope(product["mechanism"]):
                    excluded.append(
                        {
                            "id": case_id,
                            "emitter_id": emitter["id"],
                            "receiver_id": receiver["id"],
                            "mechanism": product["mechanism"],
                            "reason": "passive-intermodulation-outside-this-test",
                        }
                    )
                    continue
                isolation = isolation_for_pair(isolations, emitter["id"], receiver["id"])
                band = band_of_product(product["frequency_mhz"], receiver)
                coupled = coupled_level_dbm(
                    product["level_dbm"], emitter["antenna_gain_dbi"],
                    receiver["antenna_gain_dbi"], isolation,
                )
                threshold = effective_susceptibility_dbm(receiver, band)
                margin = interference_margin_db(coupled, threshold)
                coexist = bool(
                    set(emitter["operating_modes"]) & set(receiver["operating_modes"])
                )
                mandatory = coexist and (
                    band == BAND_IN
                    or margin < required_margin - MARGIN_TOLERANCE_DB
                )
                cases.append(
                    {
                        "id": case_id,
                        "emitter_id": emitter["id"],
                        "receiver_id": receiver["id"],
                        "mechanism": product["mechanism"],
                        "order": product["order"],
                        "frequency_mhz": product["frequency_mhz"],
                        "coupled_dbm": coupled,
                        "band": band,
                        "susceptibility_dbm": threshold,
                        "margin_db": margin,
                        "modes_coexist": coexist,
                        "mandatory": mandatory,
                    }
                )
    return {
        "cases": cases,
        "excluded": excluded,
        "required_margin_db": required_margin,
    }


def mandatory_case_ids(matrix):
    """Identifiers of the cases the system test has to exercise."""
    if not isinstance(matrix, dict) or "cases" not in matrix:
        raise ValueError("matrix must be a build_test_matrix result")
    return [case["id"] for case in matrix["cases"] if case["mandatory"]]


def validate_case_results(case_results):
    """Validate the executed-case result map and return a normalized copy."""
    if case_results is None:
        return {}
    if not isinstance(case_results, dict):
        raise ValueError("case_results must be a mapping of case id to result")
    normalized = {}
    for case_id, result in case_results.items():
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_results keys must be non-empty strings")
        if result not in VALID_RESULTS:
            raise ValueError(
                "case %s has unknown result %r (expected one of %s)"
                % (case_id, result, ", ".join(VALID_RESULTS))
            )
        normalized[case_id] = result
    return normalized


def check_matrix_coverage(matrix, case_results):
    """Findings for mandatory cases the executed matrix never ran."""
    results = validate_case_results(case_results)
    findings = []
    for case_id in mandatory_case_ids(matrix):
        if case_id not in results:
            findings.append("mandatory-case-not-exercised:%s" % case_id)
    known = set(case["id"] for case in matrix["cases"])
    for case_id in sorted(set(results) - known):
        findings.append("executed-case-absent-from-the-matrix:%s" % case_id)
    return findings


def check_margins(matrix, case_results=None):
    """Findings for margin shortfalls the system test did not clear."""
    results = validate_case_results(case_results)
    required = matrix["required_margin_db"]
    findings = []
    for case in matrix["cases"]:
        if not case["modes_coexist"]:
            continue
        if case["margin_db"] >= required - MARGIN_TOLERANCE_DB:
            continue
        result = results.get(case["id"])
        if result == "fail":
            findings.append("system-test-demonstrated-interference:%s" % case["id"])
        elif result != "pass":
            findings.append("interference-margin-below-required:%s" % case["id"])
    return findings


def assess_rf_compatibility(system):
    """Assess one system radiofrequency compatibility test against clause 5.3.8."""
    matrix = build_test_matrix(system)
    results = validate_case_results(system.get("case_results"))
    findings = list(check_margins(matrix, results))
    findings.extend(check_matrix_coverage(matrix, results))
    return {
        "cases": matrix["cases"],
        "excluded": matrix["excluded"],
        "mandatory_ids": mandatory_case_ids(matrix),
        "required_margin_db": matrix["required_margin_db"],
        "findings": findings,
        "compliant": not findings,
    }
