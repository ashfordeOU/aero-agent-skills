"""Complementary crimping requirements for a space electrical harness.

Anchor: ECSS-Q-ST-20-30C clause 7.4 (complementary ECSS crimping requirements
sitting on top of the IPC crimp-termination workmanship chapter). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve which limit governs a crimp characteristic. The complementary
   clause takes precedence over the delegated workmanship criterion wherever
   both speak, so the governing value is chosen by SOURCE, not by tightness,
   and a complementary value that is looser than the delegated one is reported
   as a deliberate relaxation rather than silently replaced by the tighter one.
2. Grade a measured crimp height against the window the contact and wire gauge
   carry, absorbing representation error at the window edge with a tolerance.
3. Size the tensile sample the lot owes from a sampling fraction and a floor,
   and grade every pull against the minimum force its gauge carries.
4. Refuse the construction defects the complementary clause rules out: an
   unqualified second wire in a barrel, solder anywhere in the crimp, a missing
   insulation support where the contact provides one.
5. Confirm the crimping tool's calibration is still inside its interval, and
   roll every per-crimp record up into one lot verdict with named findings.
"""

import math

__all__ = [
    "HEIGHT_TOLERANCE_MM",
    "FORCE_TOLERANCE_N",
    "REQUIREMENT_SOURCES",
    "normalize_source",
    "governing_limit",
    "crimp_height_window",
    "crimp_height_verdict",
    "minimum_pull_force_n",
    "pull_sample_size",
    "grade_pull_sample",
    "evaluate_crimp",
    "tool_calibration_current",
    "assess_crimp_lot",
]

# A crimp height sitting exactly on a window edge is inside the window. The
# equality is a floating-point representation question, absorbed here instead
# of by moving the engineering limit.
HEIGHT_TOLERANCE_MM = 1e-9

# Same argument on the tensile side: a pull that lands exactly on the minimum
# force meets it.
FORCE_TOLERANCE_N = 1e-9

# The two places a crimp criterion can come from. "complementary" is the ECSS
# clause; "delegated" is the workmanship chapter it is layered onto.
REQUIREMENT_SOURCES = ("complementary", "delegated")

# The sample a lot owes can never fall below this many crimps, whatever the
# sampling fraction works out to.
MIN_PULL_SAMPLES = 3


def _require_number(value, label, positive=True):
    """Return value as a float after rejecting non-numbers and non-finites."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if positive and number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def normalize_source(source):
    """Fold a requirement-source spelling onto its canonical token."""
    if not isinstance(source, str):
        raise ValueError("requirement source must be a string")
    token = source.strip().lower().replace("_", "-")
    aliases = {
        "complementary": "complementary",
        "ecss": "complementary",
        "ecss-complementary": "complementary",
        "delegated": "delegated",
        "workmanship": "delegated",
        "delegated-workmanship": "delegated",
    }
    if token not in aliases:
        raise ValueError("unrecognized requirement source %r" % (source,))
    return aliases[token]


def governing_limit(complementary_value, delegated_value, sense):
    """Return the governing limit and how the two sources relate.

    sense is "min" when a larger number is the tighter requirement (a minimum
    force) and "max" when a smaller number is (a maximum resistance).
    """
    if sense not in ("min", "max"):
        raise ValueError("sense must be 'min' or 'max', got %r" % (sense,))
    if complementary_value is None and delegated_value is None:
        raise ValueError("at least one of the two sources must carry a value")
    if complementary_value is None:
        value = _require_number(delegated_value, "delegated_value", positive=False)
        return {"value": value, "source": "delegated", "relaxation": False}
    value = _require_number(complementary_value, "complementary_value", positive=False)
    if delegated_value is None:
        return {"value": value, "source": "complementary", "relaxation": False}
    other = _require_number(delegated_value, "delegated_value", positive=False)
    if sense == "min":
        relaxation = value < other
    else:
        relaxation = value > other
    return {"value": value, "source": "complementary", "relaxation": bool(relaxation)}


def crimp_height_window(nominal_mm, tolerance_mm):
    """Return the (low, high) crimp-height window in millimetres."""
    nominal = _require_number(nominal_mm, "nominal_mm")
    tolerance = _require_number(tolerance_mm, "tolerance_mm")
    if tolerance >= nominal:
        raise ValueError("tolerance_mm %g must be smaller than nominal_mm %g" % (tolerance, nominal))
    return (nominal - tolerance, nominal + tolerance)


def crimp_height_verdict(measured_mm, nominal_mm, tolerance_mm):
    """Grade one measured crimp height against its window."""
    measured = _require_number(measured_mm, "measured_mm")
    low, high = crimp_height_window(nominal_mm, tolerance_mm)
    inside = (measured >= low - HEIGHT_TOLERANCE_MM) and (measured <= high + HEIGHT_TOLERANCE_MM)
    return {
        "measured_mm": measured,
        "window_mm": (low, high),
        "deviation_mm": measured - float(nominal_mm),
        "inside_window": bool(inside),
    }


def minimum_pull_force_n(gauge_awg, force_table):
    """Return the minimum tensile force a gauge carries; refuse an untabulated gauge."""
    if not isinstance(gauge_awg, int) or isinstance(gauge_awg, bool):
        raise ValueError("gauge_awg must be an integer wire gauge")
    if not isinstance(force_table, dict) or not force_table:
        raise ValueError("force_table must be a non-empty mapping of gauge to force")
    if gauge_awg not in force_table:
        raise ValueError(
            "gauge %d is not tabulated; extrapolating a tensile minimum is refused" % gauge_awg
        )
    return _require_number(force_table[gauge_awg], "force_table[%d]" % gauge_awg)


def pull_sample_size(lot_size, sampling_fraction, minimum_samples=MIN_PULL_SAMPLES):
    """Return how many crimps of a lot owe a destructive pull test."""
    if not isinstance(lot_size, int) or isinstance(lot_size, bool):
        raise ValueError("lot_size must be an integer")
    if lot_size <= 0:
        raise ValueError("lot_size must be positive, got %d" % lot_size)
    fraction = _require_number(sampling_fraction, "sampling_fraction")
    if fraction > 1.0:
        raise ValueError("sampling_fraction must not exceed 1.0, got %g" % fraction)
    if not isinstance(minimum_samples, int) or isinstance(minimum_samples, bool):
        raise ValueError("minimum_samples must be an integer")
    if minimum_samples <= 0:
        raise ValueError("minimum_samples must be positive, got %d" % minimum_samples)
    scaled = int(math.ceil(lot_size * fraction - 1e-12))
    return min(lot_size, max(scaled, minimum_samples))


def grade_pull_sample(forces_n, minimum_force_n):
    """Grade a tensile sample; every pull must reach the minimum, not the mean."""
    if not isinstance(forces_n, (list, tuple)) or not forces_n:
        raise ValueError("forces_n must be a non-empty sequence of tensile results")
    minimum = _require_number(minimum_force_n, "minimum_force_n")
    results = []
    for index, force in enumerate(forces_n):
        value = _require_number(force, "forces_n[%d]" % index)
        meets = value > minimum or math.isclose(
            value, minimum, rel_tol=0.0, abs_tol=FORCE_TOLERANCE_N
        )
        results.append({"index": index, "force_n": value, "meets_minimum": bool(meets)})
    shortfalls = [r for r in results if not r["meets_minimum"]]
    return {
        "results": results,
        "minimum_force_n": minimum,
        "lowest_force_n": min(r["force_n"] for r in results),
        "shortfall_count": len(shortfalls),
        "sample_passes": not shortfalls,
    }


def evaluate_crimp(record, force_table):
    """Evaluate one crimp record and return its findings."""
    if not isinstance(record, dict):
        raise ValueError("crimp record must be a mapping")
    for key in ("id", "gauge_awg", "measured_height_mm", "nominal_height_mm", "height_tolerance_mm"):
        if key not in record:
            raise ValueError("crimp record missing required key '%s'" % key)
    identifier = record["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("crimp record id must be a non-empty string")
    height = crimp_height_verdict(
        record["measured_height_mm"],
        record["nominal_height_mm"],
        record["height_tolerance_mm"],
    )
    findings = []
    if not height["inside_window"]:
        findings.append(
            "crimp %s height %.4f mm is outside the window [%.4f, %.4f] mm"
            % (identifier, height["measured_mm"], height["window_mm"][0], height["window_mm"][1])
        )
    wires = record.get("wires_in_barrel", 1)
    if not isinstance(wires, int) or isinstance(wires, bool) or wires < 1:
        raise ValueError("wires_in_barrel must be an integer of at least 1")
    if wires > 1 and not record.get("multiple_wire_crimp_qualified", False):
        findings.append(
            "crimp %s holds %d wires in one barrel with no qualified multiple-wire process"
            % (identifier, wires)
        )
    if record.get("solder_present", False):
        findings.append("crimp %s carries solder in the barrel" % identifier)
    if record.get("contact_has_insulation_support", False) and not record.get(
        "insulation_supported", False
    ):
        findings.append("crimp %s leaves the contact's insulation support unengaged" % identifier)
    minimum = minimum_pull_force_n(record["gauge_awg"], force_table)
    return {
        "id": identifier,
        "gauge_awg": record["gauge_awg"],
        "height": height,
        "minimum_pull_force_n": minimum,
        "findings": findings,
        "conforming": not findings,
    }


def tool_calibration_current(days_since_calibration, interval_days):
    """Return True while the crimping tool's calibration is still inside its interval."""
    if not isinstance(days_since_calibration, int) or isinstance(days_since_calibration, bool):
        raise ValueError("days_since_calibration must be an integer")
    if days_since_calibration < 0:
        raise ValueError("days_since_calibration must not be negative")
    if not isinstance(interval_days, int) or isinstance(interval_days, bool):
        raise ValueError("interval_days must be an integer")
    if interval_days <= 0:
        raise ValueError("interval_days must be positive")
    return days_since_calibration <= interval_days


def assess_crimp_lot(spec):
    """Run the whole clause 7.4 complementary-crimping assessment on one lot.

    spec keys: crimps (sequence of records), force_table, sampling_fraction,
    pull_forces_n, optional minimum_samples, days_since_calibration,
    calibration_interval_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("crimps", "force_table", "sampling_fraction", "pull_forces_n"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    crimps = spec["crimps"]
    if not isinstance(crimps, (list, tuple)) or not crimps:
        raise ValueError("spec['crimps'] must be a non-empty sequence")
    force_table = spec["force_table"]
    records = []
    seen = set()
    for crimp in crimps:
        evaluated = evaluate_crimp(crimp, force_table)
        if evaluated["id"] in seen:
            raise ValueError("duplicate crimp identifier %r" % evaluated["id"])
        seen.add(evaluated["id"])
        records.append(evaluated)
    required_samples = pull_sample_size(
        len(records),
        spec["sampling_fraction"],
        spec.get("minimum_samples", MIN_PULL_SAMPLES),
    )
    governing_minimum = max(r["minimum_pull_force_n"] for r in records)
    pull = grade_pull_sample(spec["pull_forces_n"], governing_minimum)
    findings = []
    for record in records:
        findings.extend(record["findings"])
    if len(spec["pull_forces_n"]) < required_samples:
        findings.append(
            "tensile sample of %d is short of the %d pulls this lot of %d owes"
            % (len(spec["pull_forces_n"]), required_samples, len(records))
        )
    if not pull["sample_passes"]:
        findings.append(
            "%d pull(s) fell below the %.2f N minimum, lowest %.2f N"
            % (pull["shortfall_count"], pull["minimum_force_n"], pull["lowest_force_n"])
        )
    calibration_ok = True
    if "days_since_calibration" in spec:
        calibration_ok = tool_calibration_current(
            spec["days_since_calibration"], spec.get("calibration_interval_days", 180)
        )
        if not calibration_ok:
            findings.append("crimping tool calibration has lapsed; the lot has no valid tool record")
    return {
        "records": records,
        "required_pull_samples": required_samples,
        "pull": pull,
        "tool_calibration_current": calibration_ok,
        "findings": findings,
        "compliant": not findings,
    }
