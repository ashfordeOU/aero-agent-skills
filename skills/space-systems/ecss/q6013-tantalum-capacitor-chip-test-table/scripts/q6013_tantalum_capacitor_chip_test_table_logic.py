"""Solid electrolyte tantalum chip test-matrix evaluation for an EEE lot.

Anchor: ECSS-Q-ST-60-13C Table 8-2 (the test matrix applied to solid
electrolyte tantalum capacitor chips: which test groups are run, on what
sample of the lot, and against which derived limits). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the sample and accept number for the lot from a banded sampling
   plan. The band is chosen by lot size, and a lot above the top band of the
   declared plan is refused rather than judged on the largest band there
   happens to be.
2. Check the declared matrix covers every required test group for a solid
   electrolyte tantalum chip, and that no group is declared twice.
3. Derive the DC leakage limit from the capacitance-voltage product of the
   part rather than reading a single number: the allowance scales with C*V
   and never falls below a declared floor for the smallest parts.
4. Apply the voltage derating that a solid electrolyte tantalum part needs
   for a surge-tolerant application, and refuse an application voltage above
   the derated ceiling.
5. Take each row's failures against the band accept number, take the
   measured leakage and equivalent series resistance against their limits,
   and confirm the surge-current group ran the declared number of cycles.
6. Hold the lot when ANY row rejects; rows are not averaged, and a row that
   used its accept number in full is reported as marginal.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "REQUIRED_TEST_GROUPS",
    "DEFAULT_SAMPLE_PLAN",
    "DEFAULT_LEAKAGE_FACTOR_UA_PER_UF_V",
    "DEFAULT_LEAKAGE_FLOOR_UA",
    "DEFAULT_DERATING_FACTOR",
    "validate_lot_size",
    "sample_plan_band",
    "leakage_limit_ua",
    "derated_voltage_v",
    "check_application_voltage",
    "matrix_coverage",
    "row_verdict",
    "assess_tantalum_chip_test_table",
]

# Derived limits are products and ratios of decimal quantities, so an exact
# equality at a limit can land a few ULPs on the wrong side. Absorb that
# representation error here, never by relaxing the limit itself.
LIMIT_TOLERANCE = 1e-9

# The test groups a solid electrolyte tantalum chip matrix has to cover.
# Surge current and DC leakage are the two that separate this matrix from a
# ceramic one: the dielectric is grown on the anode, so an inrush event and a
# leakage drift are the failure modes the programme exists to find.
REQUIRED_TEST_GROUPS = (
    "visual-inspection",
    "electrical-measurement",
    "dc-leakage",
    "esr-measurement",
    "surge-current",
    "thermal-shock",
    "life-test",
    "solderability",
    "destructive-physical-analysis",
)

# Banded sampling plan: (largest lot in the band, sample size, accept number).
# A lot larger than the top band needs a declared extension of the plan.
DEFAULT_SAMPLE_PLAN = (
    (25, 5, 0),
    (50, 8, 0),
    (150, 13, 0),
    (500, 20, 1),
    (1200, 32, 1),
    (3200, 50, 2),
)

# DC leakage allowance scales with the capacitance-voltage product; the floor
# keeps the smallest parts from being held to an unmeasurable current.
DEFAULT_LEAKAGE_FACTOR_UA_PER_UF_V = 0.01
DEFAULT_LEAKAGE_FLOOR_UA = 0.5

# Voltage derating applied to a solid electrolyte tantalum part in a
# surge-capable application.
DEFAULT_DERATING_FACTOR = 0.5


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def validate_lot_size(lot_size):
    """Return the validated device count of the lot the matrix applies to."""
    size = _count("lot_size", lot_size)
    if size < 1:
        raise ValueError("lot_size must be at least one device, got %d" % size)
    return size


def _validate_plan(plan):
    """Return a sampling plan as ordered (max_lot, sample, accept) triples."""
    if not isinstance(plan, (list, tuple)) or not plan:
        raise ValueError("sampling plan must be a non-empty sequence of bands")
    bands = []
    for index, band in enumerate(plan):
        if not isinstance(band, (list, tuple)) or len(band) != 3:
            raise ValueError("plan[%d] must be a (max_lot, sample, accept) triple" % index)
        max_lot = _count("plan[%d] band ceiling" % index, band[0])
        sample = _count("plan[%d] sample size" % index, band[1])
        accept = _count("plan[%d] accept number" % index, band[2])
        if max_lot < 1:
            raise ValueError("plan[%d] band ceiling must be at least one device" % index)
        if sample < 1:
            raise ValueError("plan[%d] sample must be at least one device" % index)
        if accept > sample:
            raise ValueError(
                "plan[%d] accept number %d exceeds its sample of %d" % (index, accept, sample)
            )
        bands.append((max_lot, sample, accept))
    for i in range(1, len(bands)):
        if bands[i][0] <= bands[i - 1][0]:
            raise ValueError("sampling plan band ceilings must strictly increase (index %d)" % i)
    return bands


def sample_plan_band(lot_size, plan=None):
    """Return the (sample_size, accept_number) band the lot falls into."""
    size = validate_lot_size(lot_size)
    bands = _validate_plan(DEFAULT_SAMPLE_PLAN if plan is None else plan)
    for max_lot, sample, accept in bands:
        if size <= max_lot:
            if sample > size:
                return (size, min(accept, size))
            return (sample, accept)
    raise ValueError(
        "lot of %d devices is above the top band of the plan (%d); declare an extended plan"
        % (size, bands[-1][0])
    )


def leakage_limit_ua(capacitance_uf, rated_voltage_v,
                     factor=DEFAULT_LEAKAGE_FACTOR_UA_PER_UF_V,
                     floor_ua=DEFAULT_LEAKAGE_FLOOR_UA):
    """Return the DC leakage allowance in microamps for a part's C*V product."""
    capacitance = _positive("capacitance_uf", capacitance_uf)
    voltage = _positive("rated_voltage_v", rated_voltage_v)
    scale = _positive("leakage factor", factor)
    floor = _positive("leakage floor", floor_ua)
    scaled = scale * capacitance * voltage
    return scaled if scaled > floor else floor


def derated_voltage_v(rated_voltage_v, derating_factor=DEFAULT_DERATING_FACTOR):
    """Return the ceiling an application may put across a rated tantalum part."""
    rated = _positive("rated_voltage_v", rated_voltage_v)
    factor = _real("derating_factor", derating_factor)
    if factor <= 0.0 or factor > 1.0:
        raise ValueError("derating_factor must lie in (0, 1], got %g" % factor)
    return rated * factor


def check_application_voltage(applied_voltage_v, rated_voltage_v,
                              derating_factor=DEFAULT_DERATING_FACTOR):
    """Return the derating record for an application voltage on a rated part."""
    applied = _positive("applied_voltage_v", applied_voltage_v)
    ceiling = derated_voltage_v(rated_voltage_v, derating_factor)
    return {
        "applied_voltage_v": applied,
        "derated_ceiling_v": ceiling,
        "within_derating": applied <= ceiling + LIMIT_TOLERANCE,
    }


def matrix_coverage(entries):
    """Return the coverage record of a declared matrix against the required groups."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of matrix rows")
    seen = []
    duplicates = []
    unknown = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        group = entry.get("group")
        if not isinstance(group, str) or not group.strip():
            raise ValueError("entries[%d] needs a non-empty 'group'" % index)
        group = group.strip()
        if group in seen and group not in duplicates:
            duplicates.append(group)
        if group not in seen:
            seen.append(group)
        if group not in REQUIRED_TEST_GROUPS and group not in unknown:
            unknown.append(group)
    missing = [g for g in REQUIRED_TEST_GROUPS if g not in seen]
    return {
        "declared": seen,
        "missing": missing,
        "duplicated": duplicates,
        "unrecognized": unknown,
        "complete": not missing and not duplicates,
    }


def row_verdict(entry, sample_size, accept_number):
    """Return the verdict record for one row of the tantalum chip matrix.

    entry keys: group, method, failures and, where the row measures one, an
    optional leakage_ua, leakage_limit_ua, esr_ohm, esr_limit_ohm,
    surge_cycles and required_surge_cycles.
    """
    if not isinstance(entry, dict):
        raise ValueError("a matrix row must be a mapping, got %r" % (entry,))
    for key in ("group", "method", "failures"):
        if key not in entry:
            raise ValueError("matrix row missing required key '%s'" % key)
    group = entry["group"]
    if not isinstance(group, str) or not group.strip():
        raise ValueError("matrix row needs a non-empty 'group'")
    method = entry["method"]
    if not isinstance(method, str) or not method.strip():
        raise ValueError("matrix row needs a non-empty 'method' reference")
    sample = _count("sample_size", sample_size)
    accept = _count("accept_number", accept_number)
    if sample < 1:
        raise ValueError("sample_size must be at least one device")
    if accept > sample:
        raise ValueError("accept number %d exceeds the sample of %d" % (accept, sample))
    failures = _count("failures", entry["failures"])
    if failures > sample:
        raise ValueError(
            "row '%s' reports %d failures in a sample of %d"
            % (group.strip(), failures, sample)
        )
    name = group.strip()
    findings = []
    if failures > accept:
        findings.append(
            "row '%s' took %d failures against an accept number of %d" % (name, failures, accept)
        )
    if "leakage_ua" in entry:
        measured = _real("leakage_ua", entry["leakage_ua"])
        if measured < 0.0:
            raise ValueError("leakage_ua must be non-negative, got %g" % measured)
        if "leakage_limit_ua" not in entry:
            raise ValueError("row '%s' measures leakage with no leakage_limit_ua" % name)
        allowance = _positive("leakage_limit_ua", entry["leakage_limit_ua"])
        if measured > allowance + LIMIT_TOLERANCE:
            findings.append(
                "row '%s' leakage %.4f uA is above its C*V allowance of %.4f uA"
                % (name, measured, allowance)
            )
    if "esr_ohm" in entry:
        measured = _positive("esr_ohm", entry["esr_ohm"])
        if "esr_limit_ohm" not in entry:
            raise ValueError("row '%s' measures ESR with no esr_limit_ohm" % name)
        allowance = _positive("esr_limit_ohm", entry["esr_limit_ohm"])
        if measured > allowance + LIMIT_TOLERANCE:
            findings.append(
                "row '%s' ESR %.4f ohm is above its limit of %.4f ohm"
                % (name, measured, allowance)
            )
    if "surge_cycles" in entry:
        ran = _count("surge_cycles", entry["surge_cycles"])
        required = _count("required_surge_cycles", entry.get("required_surge_cycles", 0))
        if ran < required:
            findings.append(
                "row '%s' ran %d surge cycles against the %d required" % (name, ran, required)
            )
    accepted = not findings
    return {
        "group": name,
        "method": method.strip(),
        "sample_size": sample,
        "accept_number": accept,
        "failures": failures,
        "accepted": accepted,
        "marginal": accepted and accept > 0 and failures == accept,
        "findings": findings,
    }


def assess_tantalum_chip_test_table(spec):
    """Run the full Table 8-2 solid electrolyte tantalum chip matrix assessment.

    spec keys: lot_size, entries; optional sample_plan, capacitance_uf,
    rated_voltage_v, applied_voltage_v, derating_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "entries"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot_size = validate_lot_size(spec["lot_size"])
    sample_size, accept_number = sample_plan_band(lot_size, spec.get("sample_plan"))
    coverage = matrix_coverage(spec["entries"])
    rows = [row_verdict(entry, sample_size, accept_number) for entry in spec["entries"]]
    findings = []
    for group in coverage["missing"]:
        findings.append("required test group '%s' is absent from the matrix" % group)
    for group in coverage["duplicated"]:
        findings.append("test group '%s' is declared more than once" % group)
    for row in rows:
        findings.extend(row["findings"])
    allowance = None
    if "capacitance_uf" in spec and "rated_voltage_v" in spec:
        allowance = leakage_limit_ua(
            spec["capacitance_uf"],
            spec["rated_voltage_v"],
            spec.get("leakage_factor", DEFAULT_LEAKAGE_FACTOR_UA_PER_UF_V),
            spec.get("leakage_floor_ua", DEFAULT_LEAKAGE_FLOOR_UA),
        )
    derating = None
    if "applied_voltage_v" in spec:
        if "rated_voltage_v" not in spec:
            raise ValueError("an applied_voltage_v needs a rated_voltage_v to derate against")
        derating = check_application_voltage(
            spec["applied_voltage_v"],
            spec["rated_voltage_v"],
            spec.get("derating_factor", DEFAULT_DERATING_FACTOR),
        )
        if not derating["within_derating"]:
            findings.append(
                "application voltage %.3f V is above the derated ceiling of %.3f V"
                % (derating["applied_voltage_v"], derating["derated_ceiling_v"])
            )
    advisories = [
        "row '%s' used its accept number in full" % row["group"]
        for row in rows
        if row["marginal"]
    ]
    accepted = not findings
    return {
        "lot_size": lot_size,
        "sample_size": sample_size,
        "accept_number": accept_number,
        "coverage": coverage,
        "rows": rows,
        "leakage_allowance_ua": allowance,
        "derating": derating,
        "rejecting_groups": [row["group"] for row in rows if not row["accepted"]],
        "accepted": accepted,
        "disposition": "accept" if accepted else "hold",
        "findings": findings,
        "advisories": advisories,
    }
