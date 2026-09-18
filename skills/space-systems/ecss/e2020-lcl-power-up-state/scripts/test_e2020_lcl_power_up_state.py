"""Contract tests for the clause 5.2.7.2.1 latching limiter power-up logic."""

import unittest

from e2020_lcl_power_up_state_logic import (
    BUS_DEPARTURES_JUSTIFIED,
    BUS_DEPARTURES_UNJUSTIFIED,
    BUS_INRUSH_EXCEEDED,
    BUS_NOT_EVALUATED,
    BUS_RECOMMENDATION_MET,
    CHANNEL_DEPARTURE_JUSTIFIED,
    CHANNEL_DEPARTURE_UNJUSTIFIED,
    CHANNEL_ENABLE_NOT_POSITIVE,
    CHANNEL_RECOMMENDATION_MET,
    CHANNEL_STATE_UNDECLARED,
    CRITICALITY_CATASTROPHIC,
    CRITICALITY_MAJOR,
    CRITICALITY_MINOR,
    DEFAULT_LCL_POWER_UP_POLICY,
    FOLDBACK_LIMITER,
    HIGH_POWER_LIMITER,
    LATCHING_CURRENT_LIMITER,
    OUTPUT_INDETERMINATE,
    OUTPUT_OFF,
    OUTPUT_ON,
    RETRIGGERABLE_LIMITER,
    aggregate_default_on_inrush,
    assess_channel_power_up,
    assess_lcl_power_up,
    categorize_limiter_type,
    criticality_rank,
    departure_is_argued,
    usable_source_inrush_a,
    validate_lcl_power_up_policy,
    worst_standing,
)


def _policy(**overrides):
    policy = dict(DEFAULT_LCL_POWER_UP_POLICY)
    policy.update(overrides)
    return policy


def _off_channel(identifier="lcl-1", **overrides):
    channel = {
        "id": identifier,
        "limiter_type": LATCHING_CURRENT_LIMITER,
        "power_up_state": OUTPUT_OFF,
        "positive_enable_command": True,
        "inrush_peak_a": 4.0,
    }
    channel.update(overrides)
    return channel


def _on_channel(identifier="hpl-1", **overrides):
    channel = {
        "id": identifier,
        "limiter_type": HIGH_POWER_LIMITER,
        "power_up_state": OUTPUT_ON,
        "inrush_peak_a": 6.0,
        "rationale": "survival heater line must carry load before commanding",
        "criticality": CRITICALITY_MAJOR,
        "compensating_provisions": [
            "upstream fuse sized below the harness rating",
            "staggered turn-on delay against the neighbouring line",
        ],
    }
    channel.update(overrides)
    return channel


def _design(channels=None, **overrides):
    design = {
        "channels": channels if channels is not None else [_off_channel()],
        "source_inrush_capability_a": 40.0,
    }
    design.update(overrides)
    return design


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_lcl_power_up_policy(DEFAULT_LCL_POWER_UP_POLICY),
            DEFAULT_LCL_POWER_UP_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_lcl_power_up_policy("off")

    def test_a_margin_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_lcl_power_up_policy(_policy(inrush_margin_fraction=1.0))

    def test_a_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_lcl_power_up_policy(_policy(inrush_margin_fraction=-0.1))

    def test_an_unknown_criticality_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_lcl_power_up_policy(
                _policy(justified_criticality_ceiling="moderate")
            )

    def test_a_non_boolean_enable_switch_rejected(self):
        with self.assertRaises(ValueError):
            validate_lcl_power_up_policy(_policy(require_positive_enable="yes"))


class LimiterTypeTests(unittest.TestCase):
    def test_a_latching_limiter_is_governed(self):
        self.assertEqual(
            categorize_limiter_type(LATCHING_CURRENT_LIMITER),
            LATCHING_CURRENT_LIMITER,
        )

    def test_a_high_power_limiter_is_governed(self):
        self.assertEqual(
            categorize_limiter_type("  high-power-limiter "), HIGH_POWER_LIMITER
        )

    def test_a_retriggerable_limiter_is_refused_as_out_of_scope(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(RETRIGGERABLE_LIMITER)

    def test_a_foldback_limiter_is_refused_as_out_of_scope(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(FOLDBACK_LIMITER)

    def test_an_unrecognised_limiter_type_rejected(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type("thermostat")

    def test_criticality_bands_are_ordered(self):
        self.assertLess(
            criticality_rank(CRITICALITY_MINOR),
            criticality_rank(CRITICALITY_CATASTROPHIC),
        )

    def test_an_unknown_criticality_band_rejected(self):
        with self.assertRaises(ValueError):
            criticality_rank("nuisance")


class DepartureArgumentTests(unittest.TestCase):
    def test_a_complete_argument_is_argued(self):
        argument = departure_is_argued(_on_channel())
        self.assertTrue(argument["argued"])
        self.assertEqual(argument["gaps"], [])

    def test_a_missing_rationale_is_a_gap(self):
        argument = departure_is_argued(_on_channel(rationale="tbd"))
        self.assertFalse(argument["argued"])

    def test_an_unassessed_criticality_is_a_gap(self):
        argument = departure_is_argued(_on_channel(criticality=None))
        self.assertFalse(argument["argued"])

    def test_a_criticality_above_the_ceiling_is_a_gap(self):
        argument = departure_is_argued(
            _on_channel(criticality=CRITICALITY_CATASTROPHIC)
        )
        self.assertFalse(argument["argued"])

    def test_too_few_compensating_provisions_is_a_gap(self):
        argument = departure_is_argued(
            _on_channel(compensating_provisions=["upstream fuse"])
        )
        self.assertFalse(argument["argued"])

    def test_a_provision_named_twice_rejected(self):
        with self.assertRaises(ValueError):
            departure_is_argued(
                _on_channel(compensating_provisions=["fuse", "fuse"])
            )

    def test_a_non_sequence_provision_set_rejected(self):
        with self.assertRaises(ValueError):
            departure_is_argued(_on_channel(compensating_provisions="fuse"))

    def test_an_empty_provision_string_rejected(self):
        with self.assertRaises(ValueError):
            departure_is_argued(
                _on_channel(compensating_provisions=["upstream fuse", "  "])
            )


class ChannelAssessmentTests(unittest.TestCase):
    def test_an_off_channel_with_a_positive_enable_meets_the_recommendation(self):
        record = assess_channel_power_up(_off_channel())
        self.assertEqual(record["standing"], CHANNEL_RECOMMENDATION_MET)
        self.assertFalse(record["defaults_on"])

    def test_an_off_channel_with_no_positive_enable_is_reported(self):
        record = assess_channel_power_up(
            _off_channel(positive_enable_command=False)
        )
        self.assertEqual(record["standing"], CHANNEL_ENABLE_NOT_POSITIVE)

    def test_the_enable_check_can_be_switched_off_by_policy(self):
        record = assess_channel_power_up(
            _off_channel(positive_enable_command=False),
            _policy(require_positive_enable=False),
        )
        self.assertEqual(record["standing"], CHANNEL_RECOMMENDATION_MET)

    def test_an_argued_on_channel_is_a_justified_departure(self):
        record = assess_channel_power_up(_on_channel())
        self.assertEqual(record["standing"], CHANNEL_DEPARTURE_JUSTIFIED)
        self.assertTrue(record["defaults_on"])

    def test_a_bare_on_channel_is_an_unjustified_departure(self):
        record = assess_channel_power_up(
            _on_channel(
                rationale=None, criticality=None, compensating_provisions=[]
            )
        )
        self.assertEqual(record["standing"], CHANNEL_DEPARTURE_UNJUSTIFIED)
        self.assertEqual(len(record["gaps"]), 3)

    def test_an_indeterminate_state_is_undeclared(self):
        record = assess_channel_power_up(
            _off_channel(power_up_state=OUTPUT_INDETERMINATE)
        )
        self.assertEqual(record["standing"], CHANNEL_STATE_UNDECLARED)

    def test_an_unrecognised_state_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel_power_up(_off_channel(power_up_state="output-warm"))

    def test_a_channel_with_no_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel_power_up(_off_channel(id="  "))

    def test_a_negative_inrush_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel_power_up(_off_channel(inrush_peak_a=-1.0))


class InrushTests(unittest.TestCase):
    def test_only_the_defaulting_channels_charge_the_source(self):
        records = [
            assess_channel_power_up(_off_channel("lcl-1", inrush_peak_a=9.0)),
            assess_channel_power_up(_on_channel("hpl-1", inrush_peak_a=6.0)),
        ]
        self.assertAlmostEqual(aggregate_default_on_inrush(records), 6.0, places=9)

    def test_usable_capability_holds_the_margin_back(self):
        self.assertAlmostEqual(usable_source_inrush_a(40.0, 0.2), 32.0, places=9)

    def test_a_zero_margin_leaves_the_capability_whole(self):
        self.assertAlmostEqual(usable_source_inrush_a(40.0, 0.0), 40.0, places=9)

    def test_a_zero_capability_rejected(self):
        with self.assertRaises(ValueError):
            usable_source_inrush_a(0.0, 0.2)

    def test_a_non_sequence_record_set_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_default_on_inrush("records")


class DesignAssessmentTests(unittest.TestCase):
    def test_an_all_off_design_meets_the_recommendation(self):
        result = assess_lcl_power_up(
            _design([_off_channel("lcl-1"), _off_channel("lcl-2")])
        )
        self.assertEqual(result["verdict"], BUS_RECOMMENDATION_MET)
        self.assertEqual(result["findings"], [])

    def test_an_argued_departure_is_reported_as_justified(self):
        result = assess_lcl_power_up(
            _design([_off_channel("lcl-1"), _on_channel("hpl-1")])
        )
        self.assertEqual(result["verdict"], BUS_DEPARTURES_JUSTIFIED)

    def test_a_bare_departure_is_reported_as_unjustified(self):
        result = assess_lcl_power_up(
            _design(
                [
                    _on_channel(
                        "hpl-1",
                        rationale=None,
                        criticality=None,
                        compensating_provisions=[],
                    )
                ]
            )
        )
        self.assertEqual(result["verdict"], BUS_DEPARTURES_UNJUSTIFIED)

    def test_an_undeclared_state_outranks_every_other_finding(self):
        result = assess_lcl_power_up(
            _design(
                [
                    _off_channel("lcl-1", power_up_state=OUTPUT_INDETERMINATE),
                    _on_channel("hpl-1", rationale=None),
                ]
            )
        )
        self.assertEqual(result["verdict"], BUS_NOT_EVALUATED)

    def test_an_inrush_overrun_outranks_a_well_argued_departure(self):
        result = assess_lcl_power_up(
            _design(
                [_on_channel("hpl-1", inrush_peak_a=30.0)],
                source_inrush_capability_a=20.0,
            )
        )
        self.assertEqual(result["verdict"], BUS_INRUSH_EXCEEDED)

    def test_an_inrush_exactly_on_the_usable_capability_still_fits(self):
        result = assess_lcl_power_up(
            _design(
                [_on_channel("hpl-1", inrush_peak_a=32.0)],
                source_inrush_capability_a=40.0,
            )
        )
        self.assertAlmostEqual(result["usable_source_inrush_a"], 32.0, places=9)
        self.assertTrue(result["inrush_fits"])
        self.assertEqual(result["verdict"], BUS_DEPARTURES_JUSTIFIED)

    def test_a_duplicate_channel_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_lcl_power_up(
                _design([_off_channel("lcl-1"), _off_channel("lcl-1")])
            )

    def test_a_design_with_no_channels_rejected(self):
        with self.assertRaises(ValueError):
            assess_lcl_power_up(_design([]))

    def test_a_missing_source_capability_rejected(self):
        design = _design()
        del design["source_inrush_capability_a"]
        with self.assertRaises(ValueError):
            assess_lcl_power_up(design)

    def test_findings_name_the_channel_that_produced_them(self):
        result = assess_lcl_power_up(
            _design([_on_channel("hpl-7", rationale=None)])
        )
        self.assertTrue(result["findings"])
        self.assertTrue(result["findings"][0].startswith("hpl-7:"))

    def test_the_worst_standing_is_the_one_reported(self):
        records = [
            assess_channel_power_up(_off_channel("lcl-1")),
            assess_channel_power_up(_on_channel("hpl-1")),
            assess_channel_power_up(
                _off_channel("lcl-2", power_up_state=OUTPUT_INDETERMINATE)
            ),
        ]
        self.assertEqual(worst_standing(records), CHANNEL_STATE_UNDECLARED)

    def test_worst_standing_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_standing([])


if __name__ == "__main__":
    unittest.main()
