"""Screening assessment for one purchased date-code lot of a commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 5.3.3 (screening tests at the intermediate
assurance class, whose job is to remove the weak units from a lot before the
lot is offered for assembly). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Screening is a removal operation applied to every unit of the lot, not a
   sample plan. A lot whose screened count is short of its size has not been
   screened, so that is an input error rather than a partial result.
2. The screen set is fixed by the package family: a cavity package carries
   seal and particle screens a solid-encapsulated package cannot carry, and a
   solid-encapsulated package carries a moisture precondition a cavity package
   does not need. A screen absent from the performed sequence is named.
3. The sequence has an order. Burn-in end points read the units after burn-in,
   the final electrical test closes the sequence and the external visual is the
   last thing done to the lot, so an out-of-order sequence is reported even
   when every screen is present.
4. The units the screens removed accumulate into a percent defective for the
   lot, judged against the allowable; burn-in carries its own subtotal because
   an infant-mortality population is the failure the burn-in screen exists to
   expose and must not be diluted by the visual screens.
5. Passing the allowance rejects the whole lot, not only the removed units --
   the removals are evidence about the population left behind. Units may not be
   made up from another date code, and a lot accepted close to its allowance is
   reported with an advisory rather than as a bare pass.
"""

import math

__all__ = [
    "SCREENING_TOLERANCE",
    "MARGINAL_FRACTION",
    "PACKAGE_SCREENS",
    "BURN_IN_SCREENS",
    "package_screens",
    "missing_screens",
    "sequence_order_findings",
    "screen_removals",
    "cumulative_percent_defective",
    "assess_screening",
]

# Percent-defective comparisons are a ratio of small integers scaled by 100; an
# exact equality with the allowance can land a few ULPs on the wrong side.
# Absorb the representation error here, never by relaxing the allowance.
SCREENING_TOLERANCE = 1e-9

# A lot accepted having used this share of its allowance is reported as
# marginal: it passes, but the next date code of the same build has no room.
MARGINAL_FRACTION = 0.8

# Ordered screen set per package family. The order IS the requirement: the
# sequence is checked against this tuple, not merely its membership.
PACKAGE_SCREENS = {
    "hermetic-cavity": (
        "internal-visual",
        "stabilization-bake",
        "temperature-cycling",
        "constant-acceleration",
        "burn-in",
        "burn-in-electrical-end-points",
        "seal-fine-leak",
        "seal-gross-leak",
        "particle-impact-noise-detection",
        "final-electrical",
        "external-visual",
    ),
    "solid-encapsulated": (
        "incoming-external-visual",
        "moisture-preconditioning",
        "temperature-cycling",
        "burn-in",
        "burn-in-electrical-end-points",
        "final-electrical",
        "external-visual",
    ),
    "hermetic-hybrid": (
        "internal-visual",
        "stabilization-bake",
        "temperature-cycling",
        "burn-in",
        "burn-in-electrical-end-points",
        "seal-fine-leak",
        "seal-gross-leak",
        "final-electrical",
        "external-visual",
    ),
}

# The screens whose removals are counted into the separate burn-in subtotal.
BURN_IN_SCREENS = ("burn-in", "burn-in-electrical-end-points")


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _screen_name(label, value):
    """Return a screen name normalised to its lowercase hyphenated form."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty screen name, got %r" % (label, value))
    return "-".join(value.strip().lower().replace("_", "-").split())


def package_screens(package_family):
    """Return the ordered screen set the package family demands."""
    if not isinstance(package_family, str) or not package_family.strip():
        raise ValueError("package_family must be a non-empty string, got %r" % (package_family,))
    key = _screen_name("package_family", package_family)
    if key not in PACKAGE_SCREENS:
        raise ValueError(
            "unknown package_family %r; known families are %s"
            % (package_family, ", ".join(sorted(PACKAGE_SCREENS)))
        )
    return PACKAGE_SCREENS[key]


def missing_screens(package_family, performed):
    """Return the screens the family demands that the sequence does not carry."""
    required = package_screens(package_family)
    if not isinstance(performed, (list, tuple)):
        raise ValueError("performed must be a sequence of screen names")
    seen = [_screen_name("performed[%d]" % i, s) for i, s in enumerate(performed)]
    if len(seen) != len(set(seen)):
        raise ValueError("performed lists the same screen twice; a screen runs once per lot")
    return [screen for screen in required if screen not in seen]


def sequence_order_findings(package_family, performed):
    """Return the order findings for a performed screening sequence.

    Membership is checked elsewhere. This looks only at relative position: the
    screens present must appear in the order the family's set declares, and the
    external visual must close the sequence.
    """
    required = package_screens(package_family)
    seen = [_screen_name("performed[%d]" % i, s) for i, s in enumerate(performed)]
    known = [screen for screen in seen if screen in required]
    findings = []
    for index in range(1, len(known)):
        earlier, later = known[index - 1], known[index]
        if required.index(earlier) > required.index(later):
            findings.append(
                "screen '%s' was run before '%s'; the sequence inverts the required order"
                % (later, earlier)
            )
    if known and known[-1] != required[-1] and required[-1] in known:
        findings.append(
            "screen '%s' does not close the sequence; it is the last thing done to the lot"
            % required[-1]
        )
    return findings


def screen_removals(lot_size, removals):
    """Return the validated per-screen removal records for one lot.

    removals: a sequence of mappings with keys 'screen' and 'rejects'.
    """
    lot = _count("lot_size", lot_size)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    if not isinstance(removals, (list, tuple)):
        raise ValueError("removals must be a sequence of per-screen mappings")
    records = []
    running = 0
    for index, item in enumerate(removals):
        if not isinstance(item, dict):
            raise ValueError("removals[%d] must be a mapping" % index)
        for key in ("screen", "rejects"):
            if key not in item:
                raise ValueError("removals[%d] missing required key '%s'" % (index, key))
        screen = _screen_name("removals[%d] screen" % index, item["screen"])
        rejects = _count("removals[%d] rejects" % index, item["rejects"])
        running += rejects
        if running > lot:
            raise ValueError(
                "removals total %d exceeds the lot of %d units; a unit is removed once"
                % (running, lot)
            )
        records.append(
            {
                "screen": screen,
                "rejects": rejects,
                "percent_of_lot": 100.0 * rejects / lot,
                "burn_in": screen in BURN_IN_SCREENS,
            }
        )
    return records


def cumulative_percent_defective(lot_size, records):
    """Return the total and burn-in percent defective from removal records."""
    lot = _count("lot_size", lot_size)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of removal records")
    total = sum(record["rejects"] for record in records)
    burn_in = sum(record["rejects"] for record in records if record["burn_in"])
    return {
        "removed": total,
        "burn_in_removed": burn_in,
        "survivors": lot - total,
        "percent_defective": 100.0 * total / lot,
        "burn_in_percent_defective": 100.0 * burn_in / lot,
    }


def _within(observed, allowance):
    """Return True when observed sits at or under allowance, ULPs absorbed."""
    return observed < allowance or math.isclose(
        observed, allowance, rel_tol=0.0, abs_tol=SCREENING_TOLERANCE
    )


def assess_screening(spec):
    """Run the full clause 5.3.3 screening assessment for one date-code lot.

    spec keys: lot_size, package_family, performed_screens, removals,
    allowable_percent, optional units_screened (defaults to the whole lot),
    optional burn_in_allowable_percent and optional replacement_units.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "package_family", "performed_screens", "removals", "allowable_percent"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot = _count("lot_size", spec["lot_size"])
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    screened = _count("units_screened", spec.get("units_screened", lot))
    if screened > lot:
        raise ValueError("units_screened %d exceeds the lot of %d units" % (screened, lot))
    if screened < lot:
        raise ValueError(
            "units_screened %d is short of lot_size %d; screening removes weak units from "
            "every unit of the lot and is not a sample plan" % (screened, lot)
        )
    family = _screen_name("package_family", spec["package_family"])
    required = package_screens(family)
    absent = missing_screens(family, spec["performed_screens"])
    order = sequence_order_findings(family, spec["performed_screens"])
    records = screen_removals(lot, spec["removals"])
    for record in records:
        if record["screen"] not in required:
            raise ValueError(
                "removals name screen '%s', which the %s screen set does not carry"
                % (record["screen"], family)
            )
    totals = cumulative_percent_defective(lot, records)
    allowance = _real("allowable_percent", spec["allowable_percent"])
    if allowance < 0.0 or allowance > 100.0:
        raise ValueError("allowable_percent must lie in 0..100, got %g" % allowance)
    burn_in_allowance = _real(
        "burn_in_allowable_percent", spec.get("burn_in_allowable_percent", allowance)
    )
    if burn_in_allowance < 0.0 or burn_in_allowance > 100.0:
        raise ValueError(
            "burn_in_allowable_percent must lie in 0..100, got %g" % burn_in_allowance
        )
    replacements = _count("replacement_units", spec.get("replacement_units", 0))

    within_allowance = _within(totals["percent_defective"], allowance)
    within_burn_in = _within(totals["burn_in_percent_defective"], burn_in_allowance)

    findings = []
    for screen in absent:
        findings.append("required screen '%s' was not run on the lot" % screen)
    findings.extend(order)
    if not within_allowance:
        findings.append(
            "screening removed %.3f%% of the lot against an allowable %.3f%%; the lot is "
            "rejected, not only its removed units"
            % (totals["percent_defective"], allowance)
        )
    if not within_burn_in:
        findings.append(
            "burn-in alone removed %.3f%% against an allowable %.3f%%"
            % (totals["burn_in_percent_defective"], burn_in_allowance)
        )
    if replacements:
        findings.append(
            "%d unit(s) were added to make the lot up to size; a screened lot is one date "
            "code and is not topped up" % replacements
        )
    accepted = (
        not absent
        and not order
        and within_allowance
        and within_burn_in
        and replacements == 0
    )
    marginal = (
        accepted
        and allowance > 0.0
        and totals["percent_defective"] >= MARGINAL_FRACTION * allowance
    )
    if marginal:
        findings.append(
            "lot accepted at %.3f%% of an allowable %.3f%%; little screening margin left"
            % (totals["percent_defective"], allowance)
        )
    return {
        "package_family": family,
        "lot_size": lot,
        "units_screened": screened,
        "required_screens": list(required),
        "missing_screens": absent,
        "order_findings": order,
        "removals": records,
        "removed": totals["removed"],
        "survivors": totals["survivors"],
        "percent_defective": totals["percent_defective"],
        "burn_in_percent_defective": totals["burn_in_percent_defective"],
        "allowable_percent": allowance,
        "burn_in_allowable_percent": burn_in_allowance,
        "within_allowance": within_allowance,
        "within_burn_in_allowance": within_burn_in,
        "accepted": accepted,
        "marginal": marginal,
        "disposition": "release-screened-lot" if accepted else "reject-lot",
        "findings": findings,
    }
