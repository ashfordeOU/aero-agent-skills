"""Lot acceptance testing of incoming passive chips for hybrid assembly.

Anchor: ECSS-Q-ST-60-05C clause 8.2.3 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Size the sample. An incoming batch of passive chips is accepted on a
   sample, not on the whole population, so the first decision is how
   many pieces that sample owes. The sample size comes from the lot
   population in bands: a small lot cannot support the same sample as a
   large one, and a sample larger than the lot it was drawn from is an
   input error rather than a conservative choice.
2. Set the acceptance number. A non-destructive test can tolerate a
   small number of defectives in the sample, and the number it tolerates
   grows with the sample. A destructive test cannot: every piece it
   touches is consumed, so one defective is one failed lot and the
   acceptance number is zero.
3. Grade what the sample found. The observed defective fraction is the
   defectives over the sample size, and it is graded against the
   percent-defective-allowable the chip family carries. Two things then
   have to agree before a lot is accepted: the count is at or under the
   acceptance number, and the fraction is at or under the allowable.
4. Report what the plan actually bought. A sampling plan that accepts on
   zero out of a small sample still passes lots with a real defect rate,
   and the lot tolerance percent defective is the honest statement of
   that. It is derived from the Poisson relation at ninety percent
   confidence for the acceptance number in force.
5. Refuse an unsound resubmission. A lot rejected once and offered again
   is only admissible when it was rescreened and the rescreen was
   approved; otherwise the second presentation is the first result with
   a new date on it.

Stdlib only, offline, deterministic.
"""

import math

PASSIVE_CHIP_FAMILIES = (
    "ceramic-chip-capacitor",
    "tantalum-chip-capacitor",
    "chip-resistor",
    "chip-inductor",
    "chip-ferrite-bead",
)

# Percent-defective-allowable by chip family, as a fraction. A part
# family whose failure mode is a short across the dielectric is held
# tighter than one whose failure mode is a drift out of tolerance.
PERCENT_DEFECTIVE_ALLOWABLE = {
    "ceramic-chip-capacitor": 0.01,
    "tantalum-chip-capacitor": 0.01,
    "chip-resistor": 0.02,
    "chip-inductor": 0.02,
    "chip-ferrite-bead": 0.02,
}

TEST_DESTRUCTIVE = "destructive"
TEST_NON_DESTRUCTIVE = "non-destructive"

# Test kinds and whether the piece survives them. A destructive kind
# consumes its sample, which is what forces the zero acceptance number.
TEST_KIND_CATEGORY = {
    "visual-external-inspection": TEST_NON_DESTRUCTIVE,
    "electrical-parameter-measurement": TEST_NON_DESTRUCTIVE,
    "terminal-solderability": TEST_DESTRUCTIVE,
    "destructive-physical-analysis": TEST_DESTRUCTIVE,
    "termination-adhesion-pull": TEST_DESTRUCTIVE,
}

# Attribute sampling bands: (largest lot in the band, sample size).
SAMPLE_SIZE_BANDS = (
    (50, 8),
    (150, 13),
    (500, 20),
    (1200, 32),
    (3200, 50),
    (10000, 80),
    (35000, 125),
)
LARGE_LOT_SAMPLE_SIZE = 200

# Acceptance number for a non-destructive test, by sample size band.
NON_DESTRUCTIVE_ACCEPTANCE_BANDS = (
    (13, 0),
    (32, 1),
    (80, 2),
    (125, 3),
)
LARGE_SAMPLE_ACCEPTANCE_NUMBER = 5

# Poisson multipliers at ninety percent confidence, indexed by the
# acceptance number in force. Dividing by the sample size gives the lot
# tolerance percent defective the plan actually buys.
POISSON_90_MULTIPLIER = {
    0: 2.302585092994046,
    1: 3.889720169867429,
    2: 5.322320128462059,
    3: 6.680783330976991,
    4: 7.993589498440322,
    5: 9.274674988225775,
}

# A defective fraction is a quotient of two exact integers, so a lot
# sitting exactly on its allowable can land a unit in the last place
# above it. This tolerance absorbs that representation error without
# widening the allowable itself.
FRACTION_TOLERANCE = 1.0e-12

ACCEPT = "lot-accepted"
REJECT = "lot-rejected"


def _positive_integer(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _non_negative_integer(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def sample_size_for_lot(lot_size):
    """Attribute sample size owed by a lot of this population."""
    _positive_integer("lot_size", lot_size)
    for ceiling, size in SAMPLE_SIZE_BANDS:
        if lot_size <= ceiling:
            return min(size, lot_size)
    return min(LARGE_LOT_SAMPLE_SIZE, lot_size)


def test_category(test_kind):
    """Return whether a test kind consumes the pieces it touches."""
    if test_kind not in TEST_KIND_CATEGORY:
        raise ValueError(
            "unknown test_kind %r (expected one of %s)"
            % (test_kind, ", ".join(sorted(TEST_KIND_CATEGORY)))
        )
    return TEST_KIND_CATEGORY[test_kind]


def acceptance_number(sample_size, test_kind):
    """Defectives a sample may carry and still accept the lot."""
    _positive_integer("sample_size", sample_size)
    if test_category(test_kind) == TEST_DESTRUCTIVE:
        return 0
    for ceiling, number in NON_DESTRUCTIVE_ACCEPTANCE_BANDS:
        if sample_size <= ceiling:
            return number
    return LARGE_SAMPLE_ACCEPTANCE_NUMBER


def defective_fraction(defectives, sample_size):
    """Observed defective fraction of a drawn sample."""
    _non_negative_integer("defectives", defectives)
    _positive_integer("sample_size", sample_size)
    if defectives > sample_size:
        raise ValueError(
            "defectives (%d) cannot exceed sample_size (%d)"
            % (defectives, sample_size)
        )
    return defectives / sample_size


def lot_tolerance_percent_defective(sample_size, accept_number):
    """Defect fraction the plan still passes at ninety percent confidence."""
    _positive_integer("sample_size", sample_size)
    _non_negative_integer("accept_number", accept_number)
    if accept_number not in POISSON_90_MULTIPLIER:
        raise ValueError(
            "no tabulated multiplier for acceptance number %d" % accept_number
        )
    return POISSON_90_MULTIPLIER[accept_number] / sample_size


def allowable_fraction(chip_family):
    """Percent-defective-allowable carried by a passive chip family."""
    if chip_family not in PERCENT_DEFECTIVE_ALLOWABLE:
        raise ValueError(
            "unknown chip_family %r (expected one of %s)"
            % (chip_family, ", ".join(PASSIVE_CHIP_FAMILIES))
        )
    return PERCENT_DEFECTIVE_ALLOWABLE[chip_family]


def validate_lot(lot):
    """Validate one incoming lot record and return a normalized copy."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    lot_id = lot.get("id")
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot needs a non-empty string id")
    family = lot.get("chip_family")
    if family not in PERCENT_DEFECTIVE_ALLOWABLE:
        raise ValueError(
            "lot %s has unknown chip_family %r (expected one of %s)"
            % (lot_id, family, ", ".join(PASSIVE_CHIP_FAMILIES))
        )
    test_kind = lot.get("test_kind")
    test_category(test_kind)
    lot_size = _positive_integer("lot %s lot_size" % lot_id, lot.get("lot_size"))
    drawn = lot.get("sample_drawn")
    if drawn is None:
        drawn = sample_size_for_lot(lot_size)
    drawn = _positive_integer("lot %s sample_drawn" % lot_id, drawn)
    defectives = _non_negative_integer(
        "lot %s defectives_found" % lot_id, lot.get("defectives_found", 0)
    )
    if defectives > drawn:
        raise ValueError(
            "lot %s reports %d defectives in a sample of %d"
            % (lot_id, defectives, drawn)
        )
    return {
        "id": lot_id,
        "chip_family": family,
        "test_kind": test_kind,
        "lot_size": lot_size,
        "sample_drawn": drawn,
        "defectives_found": defectives,
        "previously_rejected": _boolean(
            "lot %s previously_rejected" % lot_id,
            lot.get("previously_rejected", False),
        ),
        "rescreened": _boolean(
            "lot %s rescreened" % lot_id, lot.get("rescreened", False)
        ),
        "rescreen_approved": _boolean(
            "lot %s rescreen_approved" % lot_id,
            lot.get("rescreen_approved", False),
        ),
    }


def check_sampling(lot):
    """Findings about how the sample for one lot was drawn."""
    norm = validate_lot(lot)
    owed = sample_size_for_lot(norm["lot_size"])
    findings = []
    if norm["sample_drawn"] < owed:
        findings.append("sample-smaller-than-the-plan-requires")
    if norm["sample_drawn"] > norm["lot_size"]:
        findings.append("sample-larger-than-the-lot-it-was-drawn-from")
    if (
        test_category(norm["test_kind"]) == TEST_DESTRUCTIVE
        and norm["sample_drawn"] >= norm["lot_size"]
    ):
        findings.append("destructive-sample-consumes-the-whole-lot")
    return findings


def check_resubmission(lot):
    """Findings about a lot offered again after an earlier rejection."""
    norm = validate_lot(lot)
    if not norm["previously_rejected"]:
        return []
    if not norm["rescreened"]:
        return ["rejected-lot-resubmitted-without-a-rescreen"]
    if not norm["rescreen_approved"]:
        return ["rescreen-performed-without-an-approval-on-record"]
    return []


def check_defectives(lot):
    """Findings about the count and fraction the sample returned."""
    norm = validate_lot(lot)
    accept_number = acceptance_number(norm["sample_drawn"], norm["test_kind"])
    fraction = defective_fraction(norm["defectives_found"], norm["sample_drawn"])
    allowable = allowable_fraction(norm["chip_family"])
    findings = []
    if norm["defectives_found"] > accept_number:
        findings.append("defectives-above-the-acceptance-number")
    if fraction > allowable + FRACTION_TOLERANCE:
        findings.append("defective-fraction-above-the-family-allowable")
    return findings


def assess_lot(lot):
    """Assess one incoming passive chip lot against clause 8.2.3."""
    norm = validate_lot(lot)
    accept_number = acceptance_number(norm["sample_drawn"], norm["test_kind"])
    fraction = defective_fraction(norm["defectives_found"], norm["sample_drawn"])
    findings = list(check_sampling(norm))
    findings.extend(check_resubmission(norm))
    findings.extend(check_defectives(norm))
    return {
        "id": norm["id"],
        "chip_family": norm["chip_family"],
        "test_kind": norm["test_kind"],
        "test_category": test_category(norm["test_kind"]),
        "lot_size": norm["lot_size"],
        "sample_owed": sample_size_for_lot(norm["lot_size"]),
        "sample_drawn": norm["sample_drawn"],
        "acceptance_number": accept_number,
        "defectives_found": norm["defectives_found"],
        "defective_fraction": fraction,
        "allowable_fraction": allowable_fraction(norm["chip_family"]),
        "lot_tolerance_fraction": lot_tolerance_percent_defective(
            norm["sample_drawn"], accept_number
        ),
        "findings": findings,
        "disposition": REJECT if findings else ACCEPT,
    }


def assess_incoming_batch(lots):
    """Run the clause 8.2.3 assessment over a delivery of several lots."""
    if not isinstance(lots, list) or not lots:
        raise ValueError("lots must be a non-empty list")
    results = []
    seen = set()
    for lot in lots:
        result = assess_lot(lot)
        if result["id"] in seen:
            raise ValueError("duplicate lot id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    rejected = [r["id"] for r in results if r["disposition"] == REJECT]
    pieces = sum(r["sample_drawn"] for r in results)
    consumed = sum(
        r["sample_drawn"]
        for r in results
        if r["test_category"] == TEST_DESTRUCTIVE
    )
    return {
        "lots": results,
        "accepted_ids": [r["id"] for r in results if r["disposition"] == ACCEPT],
        "rejected_ids": rejected,
        "pieces_sampled": pieces,
        "pieces_consumed": consumed,
        "batch_accepted": not rejected,
    }


def worst_lot_tolerance(lots):
    """Largest lot tolerance across a delivery, with the lot that carries it."""
    report = assess_incoming_batch(lots)
    worst = max(report["lots"], key=lambda r: (r["lot_tolerance_fraction"], r["id"]))
    return worst["id"], worst["lot_tolerance_fraction"]


def sample_size_is_saturated(lot_size):
    """True when the plan has hit its ceiling and the sample stops growing."""
    _positive_integer("lot_size", lot_size)
    return sample_size_for_lot(lot_size) == LARGE_LOT_SAMPLE_SIZE and (
        lot_size > SAMPLE_SIZE_BANDS[-1][0]
    )


def pieces_to_reserve(lot_size, test_kinds):
    """Pieces a lot must reserve to cover every test kind it owes."""
    _positive_integer("lot_size", lot_size)
    if not isinstance(test_kinds, (list, tuple)) or not test_kinds:
        raise ValueError("test_kinds must be a non-empty sequence")
    total = 0
    for kind in test_kinds:
        if test_category(kind) == TEST_DESTRUCTIVE:
            total += sample_size_for_lot(lot_size)
    if total > lot_size:
        raise ValueError(
            "destructive tests would consume %d pieces of a lot of %d"
            % (total, lot_size)
        )
    return total


def confidence_multiplier_span():
    """Span of tabulated Poisson multipliers, for reporting the plan basis."""
    values = sorted(POISSON_90_MULTIPLIER)
    return values[0], values[-1], math.fsum(
        POISSON_90_MULTIPLIER[v] for v in values
    )
