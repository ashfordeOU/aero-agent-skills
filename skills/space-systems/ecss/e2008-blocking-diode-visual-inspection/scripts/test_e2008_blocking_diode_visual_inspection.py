"""Contract tests for the clause 12.6.1 planar blocking diode examination leaf.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused policy, an
undeclared or self-contradictory limit table, a defect type and location
with no limit behind it, the asymmetry of magnification, a lot losing more
diodes than the allowance admits, and a declared diode that carries no
usable disposition.
"""

import unittest

from e2008_blocking_diode_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_INSPECTION_POLICY,
    DEFECT_LIMITS_NOT_ESTABLISHED,
    DEFECT_PAST_REJECT_LIMIT,
    DEFECT_PAST_REVIEW_LIMIT,
    EXAMINATION_INVALID,
    LOT_FAILS_VISUAL_INSPECTION,
    LOT_INSPECTION_INCOMPLETE,
    LOT_MEETS_INSPECTION_LIMITS,
    MAGNIFICATION_BELOW_REQUIREMENT,
    NO_LIMIT_DECLARED,
    REFER_FOR_REVIEW,
    REJECT,
    assess_planar_blocking_diode_inspection,
    defect_extent_fraction,
    diode_disposition,
    lot_dispositions,
    marginal_diode_advisories,
    observation_disposition,
    rejected_fraction,
    unestablished_diodes,
    validate_defect_limit,
    validate_defect_limits,
    validate_diode_record,
    validate_inspection_policy,
    validate_observation,
    worst_diode,
)

DIE_MM = 2.0
SCRATCH = "surface-scratch"
CHIP = "edge-chip"
ACTIVE = "active-area"
PERIPHERY = "periphery"


def _policy(**overrides):
    policy = dict(DEFAULT_INSPECTION_POLICY)
    policy.update(overrides)
    return policy


def _limits():
    return [
        {
            "defect_type": SCRATCH,
            "location": ACTIVE,
            "refer_extent_fraction": 0.05,
            "max_extent_fraction": 0.15,
        },
        {
            "defect_type": SCRATCH,
            "location": PERIPHERY,
            "refer_extent_fraction": 0.20,
            "max_extent_fraction": 0.40,
        },
        {
            "defect_type": CHIP,
            "location": PERIPHERY,
            "refer_extent_fraction": 0.10,
            "max_extent_fraction": 0.25,
        },
    ]


def _table():
    return validate_defect_limits(_limits())


def _diode(identifier, observations=None, **overrides):
    diode = {
        "id": identifier,
        "die_min_dimension_mm": DIE_MM,
        "magnification": 20.0,
        "observations": observations if observations is not None else [],
    }
    diode.update(overrides)
    return diode


def _diodes():
    return [
        _diode("bd-01"),
        _diode(
            "bd-02",
            [{"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.04}],
        ),
        _diode(
            "bd-03",
            [{"defect_type": CHIP, "location": PERIPHERY, "extent_mm": 0.10}],
        ),
    ]


def _case(**overrides):
    case = {"defect_limits": _limits(), "diodes": _diodes()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        checked = validate_inspection_policy(DEFAULT_INSPECTION_POLICY)
        self.assertAlmostEqual(checked["required_magnification"], 10.0, places=12)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_policy("required_magnification")

    def test_a_zero_required_magnification_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_policy(_policy(required_magnification=0.0))

    def test_a_reject_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_policy(_policy(max_rejected_fraction=1.3))

    def test_a_marginal_headroom_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_policy(_policy(marginal_headroom_fraction=1.2))

    def test_a_zero_reject_allowance_is_a_legitimate_policy(self):
        checked = validate_inspection_policy(_policy(max_rejected_fraction=0.0))
        self.assertAlmostEqual(checked["max_rejected_fraction"], 0.0, places=12)


class LimitTableTests(unittest.TestCase):
    def test_a_declared_limit_validates(self):
        checked = validate_defect_limit(_limits()[0])
        self.assertEqual(checked["defect_type"], SCRATCH)
        self.assertAlmostEqual(checked["max_extent_fraction"], 0.15, places=12)

    def test_a_review_threshold_above_the_reject_threshold_rejected(self):
        limit = _limits()[0]
        limit["refer_extent_fraction"] = 0.30
        with self.assertRaises(ValueError):
            validate_defect_limit(limit)

    def test_equal_thresholds_are_admitted(self):
        limit = _limits()[0]
        limit["refer_extent_fraction"] = limit["max_extent_fraction"]
        checked = validate_defect_limit(limit)
        self.assertAlmostEqual(
            checked["refer_extent_fraction"],
            checked["max_extent_fraction"],
            places=12,
        )

    def test_a_reject_threshold_longer_than_the_die_rejected(self):
        limit = _limits()[0]
        limit["max_extent_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_defect_limit(limit)

    def test_a_blank_location_rejected(self):
        limit = _limits()[0]
        limit["location"] = "  "
        with self.assertRaises(ValueError):
            validate_defect_limit(limit)

    def test_the_same_type_and_place_declared_twice_rejected(self):
        limits = _limits()
        limits.append(dict(limits[0]))
        with self.assertRaises(ValueError):
            validate_defect_limits(limits)

    def test_the_same_type_at_two_places_is_two_entries(self):
        self.assertEqual(len(_table()), 3)


class RecordTests(unittest.TestCase):
    def test_a_diode_record_is_read_back(self):
        record = validate_diode_record(_diodes()[1])
        self.assertEqual(record["id"], "bd-02")
        self.assertEqual(len(record["observations"]), 1)

    def test_a_blank_diode_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_record(_diode(" "))

    def test_a_zero_die_dimension_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_record(_diode("bd-09", die_min_dimension_mm=0.0))

    def test_a_negative_defect_extent_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(
                {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": -0.1}
            )

    def test_a_defect_with_no_location_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation({"defect_type": SCRATCH, "extent_mm": 0.1})


class ExtentTests(unittest.TestCase):
    def test_an_extent_is_referred_to_the_smallest_die_dimension(self):
        self.assertAlmostEqual(defect_extent_fraction(0.1, DIE_MM), 0.05, places=12)

    def test_the_same_defect_is_worse_on_a_smaller_die(self):
        self.assertGreater(
            defect_extent_fraction(0.1, 1.0), defect_extent_fraction(0.1, 4.0)
        )

    def test_a_zero_die_dimension_rejected_rather_than_divided_by(self):
        with self.assertRaises(ValueError):
            defect_extent_fraction(0.1, 0.0)


class ObservationDispositionTests(unittest.TestCase):
    def test_a_small_defect_is_accepted(self):
        result = observation_disposition(
            {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.04},
            DIE_MM,
            _table(),
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_defect_exactly_on_the_review_threshold_is_accepted(self):
        result = observation_disposition(
            {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.10},
            DIE_MM,
            _table(),
        )
        self.assertAlmostEqual(result["extent_fraction"], 0.05, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_defect_past_the_review_threshold_is_referred(self):
        result = observation_disposition(
            {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.20},
            DIE_MM,
            _table(),
        )
        self.assertEqual(result["disposition"], REFER_FOR_REVIEW)
        self.assertEqual(result["reason"], DEFECT_PAST_REVIEW_LIMIT)

    def test_a_defect_exactly_on_the_reject_threshold_is_referred_not_rejected(self):
        result = observation_disposition(
            {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.30},
            DIE_MM,
            _table(),
        )
        self.assertAlmostEqual(result["extent_fraction"], 0.15, places=9)
        self.assertEqual(result["disposition"], REFER_FOR_REVIEW)

    def test_a_defect_past_the_reject_threshold_is_rejected(self):
        result = observation_disposition(
            {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.50},
            DIE_MM,
            _table(),
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["reason"], DEFECT_PAST_REJECT_LIMIT)

    def test_the_same_defect_is_judged_by_where_it_sits(self):
        active = observation_disposition(
            {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.20},
            DIE_MM,
            _table(),
        )
        periphery = observation_disposition(
            {"defect_type": SCRATCH, "location": PERIPHERY, "extent_mm": 0.20},
            DIE_MM,
            _table(),
        )
        self.assertEqual(active["disposition"], REFER_FOR_REVIEW)
        self.assertEqual(periphery["disposition"], ACCEPT)

    def test_a_defect_with_no_declared_limit_is_referred_not_accepted(self):
        result = observation_disposition(
            {"defect_type": "metallisation-smear", "location": ACTIVE, "extent_mm": 0.01},
            DIE_MM,
            _table(),
        )
        self.assertEqual(result["disposition"], REFER_FOR_REVIEW)
        self.assertEqual(result["reason"], NO_LIMIT_DECLARED)


class MagnificationTests(unittest.TestCase):
    def test_a_clean_look_at_adequate_magnification_accepts(self):
        result = diode_disposition(_diode("bd-10"), _table())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["magnification_adequate"])

    def test_a_clean_look_below_the_requirement_accepts_nothing(self):
        result = diode_disposition(_diode("bd-11", magnification=4.0), _table())
        self.assertEqual(result["disposition"], EXAMINATION_INVALID)
        self.assertIn(MAGNIFICATION_BELOW_REQUIREMENT, result["reasons"])

    def test_an_examination_exactly_at_the_requirement_is_adequate(self):
        result = diode_disposition(_diode("bd-12", magnification=10.0), _table())
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_defect_seen_below_the_requirement_still_rejects(self):
        result = diode_disposition(
            _diode(
                "bd-13",
                [{"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.50}],
                magnification=4.0,
            ),
            _table(),
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_a_defect_seen_below_the_requirement_still_refers(self):
        result = diode_disposition(
            _diode(
                "bd-14",
                [{"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.20}],
                magnification=4.0,
            ),
            _table(),
        )
        self.assertEqual(result["disposition"], REFER_FOR_REVIEW)


class DiodeDispositionTests(unittest.TestCase):
    def test_the_worst_defect_decides_the_diode(self):
        result = diode_disposition(
            _diode(
                "bd-15",
                [
                    {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.02},
                    {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.50},
                ],
            ),
            _table(),
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertAlmostEqual(result["worst_extent_fraction"], 0.25, places=9)

    def test_a_reject_outranks_a_referral_on_the_same_diode(self):
        result = diode_disposition(
            _diode(
                "bd-16",
                [
                    {"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.20},
                    {"defect_type": CHIP, "location": PERIPHERY, "extent_mm": 0.90},
                ],
            ),
            _table(),
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_a_duplicate_diode_id_rejected(self):
        diodes = _diodes()
        diodes[2]["id"] = "bd-01"
        with self.assertRaises(ValueError):
            lot_dispositions(diodes, _table())

    def test_an_empty_examined_population_rejected(self):
        with self.assertRaises(ValueError):
            lot_dispositions([], _table())


class LotTests(unittest.TestCase):
    def test_a_clean_lot_rejects_nothing(self):
        dispositions = lot_dispositions(_diodes(), _table())
        self.assertAlmostEqual(rejected_fraction(dispositions), 0.0, places=12)

    def test_one_reject_in_four_is_a_quarter(self):
        diodes = _diodes()
        diodes.append(
            _diode(
                "bd-04",
                [{"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.50}],
            )
        )
        dispositions = lot_dispositions(diodes, _table())
        self.assertAlmostEqual(rejected_fraction(dispositions), 0.25, places=12)

    def test_a_declared_diode_never_presented_is_unestablished(self):
        dispositions = lot_dispositions(_diodes(), _table())
        self.assertEqual(
            unestablished_diodes(["bd-01", "bd-02", "bd-03", "bd-99"], dispositions),
            ("bd-99",),
        )

    def test_an_invalid_examination_sits_with_the_never_presented(self):
        diodes = _diodes()
        diodes.append(_diode("bd-05", magnification=4.0))
        dispositions = lot_dispositions(diodes, _table())
        self.assertIn("bd-05", unestablished_diodes([], dispositions))

    def test_the_worst_diode_carries_the_largest_relative_defect(self):
        dispositions = lot_dispositions(_diodes(), _table())
        self.assertEqual(worst_diode(dispositions)["id"], "bd-03")

    def test_an_empty_disposition_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_diode([])

    def test_a_diode_just_under_the_review_threshold_raises_an_advisory(self):
        dispositions = lot_dispositions(
            [
                _diode(
                    "bd-06",
                    [
                        {
                            "defect_type": SCRATCH,
                            "location": ACTIVE,
                            "extent_mm": 0.098,
                        }
                    ],
                )
            ],
            _table(),
        )
        advisories = marginal_diode_advisories(dispositions)
        self.assertEqual(len(advisories), 1)
        self.assertIn("bd-06", advisories[0])

    def test_a_comfortable_lot_raises_no_advisory(self):
        dispositions = lot_dispositions([_diodes()[1]], _table())
        self.assertEqual(marginal_diode_advisories(dispositions), ())


class AssessmentTests(unittest.TestCase):
    def test_a_clean_lot_meets_the_limits(self):
        result = assess_planar_blocking_diode_inspection(_case())
        self.assertEqual(result["verdict"], LOT_MEETS_INSPECTION_LIMITS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["accepted_diodes"]), 3)

    def test_a_missing_limit_table_closes_the_assessment(self):
        case = _case()
        del case["defect_limits"]
        result = assess_planar_blocking_diode_inspection(case)
        self.assertEqual(result["verdict"], DEFECT_LIMITS_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_an_empty_limit_table_closes_the_assessment(self):
        result = assess_planar_blocking_diode_inspection(_case(defect_limits=[]))
        self.assertEqual(result["verdict"], DEFECT_LIMITS_NOT_ESTABLISHED)

    def test_too_many_rejects_fail_the_lot(self):
        diodes = _diodes()
        diodes[0] = _diode(
            "bd-01",
            [{"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.50}],
        )
        result = assess_planar_blocking_diode_inspection(_case(diodes=diodes))
        self.assertEqual(result["verdict"], LOT_FAILS_VISUAL_INSPECTION)
        self.assertIn("bd-01", result["rejected_diodes"])

    def test_a_referral_holds_the_lot_open(self):
        diodes = _diodes()
        diodes[1] = _diode(
            "bd-02",
            [{"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.20}],
        )
        result = assess_planar_blocking_diode_inspection(_case(diodes=diodes))
        self.assertEqual(result["verdict"], LOT_INSPECTION_INCOMPLETE)
        self.assertIn("bd-02", result["referred_diodes"])

    def test_a_declared_diode_with_no_record_holds_the_lot_open(self):
        result = assess_planar_blocking_diode_inspection(
            _case(declared_diode_ids=["bd-01", "bd-02", "bd-03", "bd-77"])
        )
        self.assertEqual(result["verdict"], LOT_INSPECTION_INCOMPLETE)
        self.assertIn("bd-77", result["unestablished_diodes"])

    def test_every_bad_diode_is_reported_not_only_the_first(self):
        diodes = _diodes()
        diodes[0] = _diode(
            "bd-01",
            [{"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.50}],
        )
        diodes[1] = _diode(
            "bd-02",
            [{"defect_type": CHIP, "location": PERIPHERY, "extent_mm": 0.90}],
        )
        result = assess_planar_blocking_diode_inspection(_case(diodes=diodes))
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_the_worst_diode_travels_with_the_verdict(self):
        result = assess_planar_blocking_diode_inspection(_case())
        self.assertEqual(result["worst_diode_id"], "bd-03")
        self.assertAlmostEqual(result["worst_extent_fraction"], 0.05, places=9)

    def test_advisories_do_not_move_the_verdict(self):
        diodes = [
            _diode(
                "bd-08",
                [{"defect_type": SCRATCH, "location": ACTIVE, "extent_mm": 0.098}],
            )
        ]
        result = assess_planar_blocking_diode_inspection(_case(diodes=diodes))
        self.assertEqual(result["verdict"], LOT_MEETS_INSPECTION_LIMITS)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_rejected_share_is_reported(self):
        result = assess_planar_blocking_diode_inspection(_case())
        self.assertAlmostEqual(result["rejected_fraction"], 0.0, places=12)

    def test_a_missing_diode_population_rejected(self):
        case = _case()
        del case["diodes"]
        with self.assertRaises(ValueError):
            assess_planar_blocking_diode_inspection(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_planar_blocking_diode_inspection(["defect_limits"])


if __name__ == "__main__":
    unittest.main()
