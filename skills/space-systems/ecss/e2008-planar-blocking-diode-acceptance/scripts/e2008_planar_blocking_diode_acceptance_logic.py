#!/usr/bin/env python3
"""Acceptance programme for planar blocking diodes.

Anchor: ECSS-E-ST-20-08C clause 12.4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause hands a planar blocking diode a tabulated list of acceptance
tests. A programme is graded against that table on four things at once,
and three of them survive a programme that carries every test in the
table.

Constructions
    planar-blocking-diode      the part this table covers
    mesa-blocking-diode        a different construction, own programme
    integrated-blocking-diode  accepted through its assembly

The tabulated order below is the order the table is read in, and the
order is load bearing. A final electrical measurement run before the
environmental stress measured a diode nothing had happened to yet, so
the programme carries the test and proves nothing with it.

Tabulated sequence
    initial-visual-inspection, initial-electrical-measurement,
    thermal-shock, high-temperature-reverse-bias,
    intermediate-electrical-measurement, mechanical-shock,
    seal-leak-test, final-electrical-measurement,
    final-visual-inspection

Three of those are stresses -- thermal shock, high temperature reverse
bias and mechanical shock -- and a stress with no electrical readout
after it anywhere in the programme is a stress nobody read.

Each tabulated test also carries a basis. The visual inspections, the
initial and final electrical measurements and the seal leak test reach
every unit; the stresses and the intermediate measurement are drawn on a
sample. Running a tabulated every-unit test on a sample substitutes the
table; running a sampled test on every unit is stricter than the table
and is reported without being held against the programme.

The table, the basis map, the sampling floor and the completeness floor
below are declared project positions transcribed from the tabulated
list, not physical constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONSTRUCTIONS = (
    "planar-blocking-diode",
    "mesa-blocking-diode",
    "integrated-blocking-diode",
)

TABULATED_SEQUENCE = (
    "initial-visual-inspection",
    "initial-electrical-measurement",
    "thermal-shock",
    "high-temperature-reverse-bias",
    "intermediate-electrical-measurement",
    "mechanical-shock",
    "seal-leak-test",
    "final-electrical-measurement",
    "final-visual-inspection",
)

STRESS_TESTS = (
    "thermal-shock",
    "high-temperature-reverse-bias",
    "mechanical-shock",
)

ELECTRICAL_READOUTS = (
    "initial-electrical-measurement",
    "intermediate-electrical-measurement",
    "final-electrical-measurement",
)

BASES = ("every-unit", "sampled")

TABULATED_BASIS = {
    "initial-visual-inspection": "every-unit",
    "initial-electrical-measurement": "every-unit",
    "thermal-shock": "sampled",
    "high-temperature-reverse-bias": "sampled",
    "intermediate-electrical-measurement": "sampled",
    "mechanical-shock": "sampled",
    "seal-leak-test": "every-unit",
    "final-electrical-measurement": "every-unit",
    "final-visual-inspection": "every-unit",
}

AP_OUT_OF_SCOPE = "programme-outside-the-planar-table"
AP_INCOMPLETE = "programme-short-of-the-table"
AP_ACCEPTED = "programme-matches-the-table"

AP_RANK = {
    AP_OUT_OF_SCOPE: 0,
    AP_INCOMPLETE: 1,
    AP_ACCEPTED: 2,
}

DEFAULT_PROGRAMME_POLICY = {
    "tabulated_sequence": TABULATED_SEQUENCE,
    "min_sample_share": 0.1,
    "min_completeness_share": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_share(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError("%s must sit between 0 and 1, got %r" % (name, value))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    The drawn share and the completeness share are quotients of counted
    units and counted tests, so a programme sitting exactly on its floor
    can evaluate a unit in the last place under it. The comparison
    absorbs that; the floor stays as declared.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge a project position over the tabulated default."""
    settings = dict(DEFAULT_PROGRAMME_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    table = tuple(settings["tabulated_sequence"])
    if not table:
        raise ValueError(
            "an empty table leaves the programme with nothing to be graded "
            "against, so every programme would pass"
        )
    seen = []
    for name in table:
        _require_choice("tabulated test", name, TABULATED_SEQUENCE)
        if name in seen:
            raise ValueError("test %r appears twice in the table" % name)
        seen.append(name)
    settings["tabulated_sequence"] = table
    settings["min_sample_share"] = _require_share(
        "min_sample_share", settings["min_sample_share"]
    )
    settings["min_completeness_share"] = _require_share(
        "min_completeness_share", settings["min_completeness_share"]
    )
    return settings


def construction_scope(construction):
    """Decide whether this diode is the one the planar table covers."""
    kind = _require_choice("construction", construction, CONSTRUCTIONS)
    findings = []
    in_scope = kind == "planar-blocking-diode"
    if kind == "mesa-blocking-diode":
        findings.append(
            "a mesa blocking diode is a different construction and carries its "
            "own acceptance list, not this table"
        )
    elif kind == "integrated-blocking-diode":
        findings.append(
            "an integrated blocking diode is accepted through the assembly it "
            "is built into, not as a discrete part against this table"
        )
    return {
        "construction": kind,
        "in_scope": in_scope,
        "findings": findings,
    }


def read_programme(entries):
    """Validate the proposed programme and return it in its run order."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of test records")
    ordered = []
    seen = []
    for entry in entries:
        _require_mapping("entry", entry)
        name = _require_label("test", entry.get("test"))
        if name in seen:
            raise ValueError("test %r is proposed twice in the programme" % name)
        seen.append(name)
        basis = _require_choice("basis", entry.get("basis"), BASES)
        units = _require_count("units", entry.get("units"))
        ordered.append({"test": name, "basis": basis, "units": units})
    return ordered


def programme_coverage(ordered, table):
    """Name the tabulated tests omitted and the tests added to the table."""
    proposed = [row["test"] for row in ordered]
    missing = [name for name in table if name not in proposed]
    untabulated = [name for name in proposed if name not in table]
    present = [name for name in table if name in proposed]
    return {
        "proposed": proposed,
        "present": present,
        "missing": missing,
        "untabulated": untabulated,
        "presence_share": len(present) / len(table),
    }


def sequence_order(ordered, table):
    """Report every pair the programme runs out of tabulated order."""
    positions = [
        (row["test"], table.index(row["test"]))
        for row in ordered
        if row["test"] in table
    ]
    inversions = []
    for first in range(len(positions)):
        for second in range(first + 1, len(positions)):
            if positions[first][1] > positions[second][1]:
                inversions.append((positions[first][0], positions[second][0]))
    return {
        "run_order": [name for name, _ in positions],
        "inversions": inversions,
        "ordered": not inversions,
    }


def post_stress_readout(ordered, table):
    """Find a stress the programme never reads an electrical result after.

    A stress is only evidence once something is measured after it. A
    programme that stresses a sample and never measures it again has
    spent the sample and learned nothing.
    """
    run_order = [row["test"] for row in ordered if row["test"] in table]
    stresses = [name for name in run_order if name in STRESS_TESTS]
    unread = []
    for name in stresses:
        index = run_order.index(name)
        later = run_order[index + 1 :]
        if not any(step in ELECTRICAL_READOUTS for step in later):
            unread.append(name)
    return {
        "stresses": stresses,
        "unread": unread,
        "every_stress_read": not unread,
    }


def basis_and_sample(ordered, lot_size, min_sample_share, table):
    """Grade each tabulated test on the basis and the count it runs at."""
    size = _require_count("lot_size", lot_size)
    if size == 0:
        raise ValueError("lot_size must be at least one diode, got 0")
    floor = _require_share("min_sample_share", min_sample_share)

    substituted = []
    short_units = []
    short_samples = []
    stricter = []
    rows = []
    for row in ordered:
        name = row["test"]
        if name not in table:
            continue
        expected = TABULATED_BASIS[name]
        share = row["units"] / size
        if row["units"] > size:
            raise ValueError(
                "test %r runs on %d units in a lot of %d" % (name, row["units"], size)
            )
        if expected == "every-unit" and row["basis"] == "sampled":
            substituted.append(name)
        if expected == "sampled" and row["basis"] == "every-unit":
            stricter.append(name)
        if row["basis"] == "every-unit" and row["units"] < size:
            short_units.append(name)
        if row["basis"] == "sampled" and not _at_least(share, floor):
            short_samples.append(name)
        rows.append(
            {
                "test": name,
                "tabulated_basis": expected,
                "declared_basis": row["basis"],
                "units": row["units"],
                "drawn_share": share,
            }
        )
    return {
        "rows": rows,
        "lot_size": size,
        "substituted": sorted(substituted),
        "stricter_than_table": sorted(stricter),
        "short_units": sorted(short_units),
        "short_samples": sorted(short_samples),
    }


def programme_completeness(coverage, basis, table):
    """Share of tabulated tests present and not run below their basis."""
    weak = set(basis["substituted"]) | set(basis["short_units"]) | set(
        basis["short_samples"]
    )
    sound = [name for name in coverage["present"] if name not in weak]
    return {
        "table_size": len(table),
        "sound": sorted(sound),
        "short": sorted(name for name in table if name not in sound),
        "completeness_share": len(sound) / len(table),
    }


def assess_planar_blocking_diode_acceptance(case):
    """Full clause 12.4.2 review of one proposed acceptance programme."""
    _require_mapping("case", case)
    programme_id = _require_label("programme_id", case.get("programme_id"))
    settings = resolve_policy(case.get("policy"))
    table = settings["tabulated_sequence"]

    scope = construction_scope(case.get("construction"))
    ordered = read_programme(case.get("entries"))
    coverage = programme_coverage(ordered, table)
    order = sequence_order(ordered, table)
    readout = post_stress_readout(ordered, table)
    basis = basis_and_sample(
        ordered, case.get("lot_size"), settings["min_sample_share"], table
    )
    completeness = programme_completeness(coverage, basis, table)

    findings = ["%s: %s" % (programme_id, f) for f in scope["findings"]]
    for name in coverage["missing"]:
        findings.append(
            "%s: the table lists %s and the programme does not run it"
            % (programme_id, name)
        )
    for name in coverage["untabulated"]:
        findings.append(
            "%s: %s is run and is not in the table, so it is carried on the "
            "project's own authority" % (programme_id, name)
        )
    for first, second in order["inversions"]:
        findings.append(
            "%s: %s runs before %s and the table puts them the other way round"
            % (programme_id, first, second)
        )
    for name in readout["unread"]:
        findings.append(
            "%s: %s is run with no electrical measurement after it, so the "
            "stressed sample was spent without being read"
            % (programme_id, name)
        )
    for name in basis["substituted"]:
        findings.append(
            "%s: %s is tabulated for every unit and is drawn on a sample"
            % (programme_id, name)
        )
    for name in basis["short_units"]:
        findings.append(
            "%s: %s runs on fewer units than the lot holds" % (programme_id, name)
        )
    for name in basis["short_samples"]:
        findings.append(
            "%s: %s draws a sample below the %.4g floor"
            % (programme_id, name, settings["min_sample_share"])
        )
    for name in basis["stricter_than_table"]:
        findings.append(
            "%s: %s is tabulated as a sampled test and runs on every unit, "
            "which is stricter than the table" % (programme_id, name)
        )

    completeness_met = _at_least(
        completeness["completeness_share"], settings["min_completeness_share"]
    )
    if not completeness_met:
        findings.append(
            "%s: %.4g of the tabulated tests are run soundly against a %.4g "
            "floor"
            % (
                programme_id,
                completeness["completeness_share"],
                settings["min_completeness_share"],
            )
        )

    if not scope["in_scope"]:
        verdict = AP_OUT_OF_SCOPE
    elif (
        coverage["missing"]
        or coverage["untabulated"]
        or not order["ordered"]
        or readout["unread"]
        or basis["substituted"]
        or basis["short_units"]
        or basis["short_samples"]
        or not completeness_met
    ):
        verdict = AP_INCOMPLETE
    else:
        verdict = AP_ACCEPTED

    return {
        "programme_id": programme_id,
        "scope": scope,
        "coverage": coverage,
        "order": order,
        "readout": readout,
        "basis": basis,
        "completeness": completeness,
        "completeness_floor_met": completeness_met,
        "verdict": verdict,
        "findings": findings,
    }
