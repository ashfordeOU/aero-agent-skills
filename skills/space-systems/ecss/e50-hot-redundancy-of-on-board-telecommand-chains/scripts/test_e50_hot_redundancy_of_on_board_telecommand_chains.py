"""Contract tests for the clause 5.4.9 telecommand hot-redundancy logic."""

import unittest

from e50_hot_redundancy_of_on_board_telecommand_chains_logic import (
    ACTIVATION_ALWAYS_ON,
    ACTIVATION_COMMANDED,
    MINIMUM_HOT_CHAINS,
    REQUIRED_ROLES,
    assess_hot_redundancy,
    chain_is_hot,
    common_elements,
    severing_depth,
    validate_chain,
    validate_element,
)


def chain(name, identifiers, **overrides):
    record = {
        "name": name,
        "elements": [
            {"role": role, "id": identifier}
            for role, identifier in zip(REQUIRED_ROLES, identifiers)
        ],
        "powered": True,
        "enabled": True,
        "activation": ACTIVATION_ALWAYS_ON,
    }
    record.update(overrides)
    return record


CHAIN_A = chain("A", ["ANT1", "RX1", "DEM1", "DEC1"])
CHAIN_B = chain("B", ["ANT2", "RX2", "DEM2", "DEC2"])


class ElementTests(unittest.TestCase):
    def test_element_is_canonicalised(self):
        self.assertEqual(validate_element({"role": " Antenna ", "id": " ANT1 "}, 0, "A"), ("antenna", "ANT1"))

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_element({"role": "diplexer", "id": "DX1"}, 0, "A")

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_element({"role": "antenna", "id": "  "}, 0, "A")

    def test_element_missing_a_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_element({"role": "antenna"}, 0, "A")

    def test_required_roles_cover_antenna_to_decoder(self):
        self.assertEqual(REQUIRED_ROLES[0], "antenna")
        self.assertEqual(REQUIRED_ROLES[-1], "decoder")


class ChainValidationTests(unittest.TestCase):
    def test_complete_chain_reports_no_missing_roles(self):
        record = validate_chain(CHAIN_A)
        self.assertTrue(record["complete"])
        self.assertEqual(record["missing_roles"], [])

    def test_short_chain_names_the_missing_roles(self):
        short = {
            "name": "C",
            "elements": [{"role": "antenna", "id": "ANT3"}, {"role": "receiver", "id": "RX3"}],
            "powered": True,
            "enabled": True,
            "activation": ACTIVATION_ALWAYS_ON,
        }
        record = validate_chain(short)
        self.assertFalse(record["complete"])
        self.assertEqual(record["missing_roles"], ["demodulator", "decoder"])

    def test_two_elements_in_one_role_rejected(self):
        doubled = {
            "name": "D",
            "elements": [{"role": "antenna", "id": "ANT4"}, {"role": "antenna", "id": "ANT5"}],
            "powered": True,
            "enabled": True,
            "activation": ACTIVATION_ALWAYS_ON,
        }
        with self.assertRaises(ValueError):
            validate_chain(doubled)

    def test_non_boolean_powered_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain(chain("A", ["ANT1", "RX1", "DEM1", "DEC1"], powered=1))

    def test_unknown_activation_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain(chain("A", ["ANT1", "RX1", "DEM1", "DEC1"], activation="warm"))

    def test_empty_element_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain(chain("A", []))


class HotnessTests(unittest.TestCase):
    def test_powered_enabled_complete_always_on_chain_is_hot(self):
        self.assertTrue(chain_is_hot(validate_chain(CHAIN_A)))

    def test_unpowered_chain_is_not_hot(self):
        self.assertFalse(chain_is_hot(validate_chain(chain("A", ["ANT1", "RX1", "DEM1", "DEC1"], powered=False))))

    def test_disabled_chain_is_not_hot(self):
        self.assertFalse(chain_is_hot(validate_chain(chain("A", ["ANT1", "RX1", "DEM1", "DEC1"], enabled=False))))

    def test_command_activated_chain_is_not_hot(self):
        cold = chain("A", ["ANT1", "RX1", "DEM1", "DEC1"], activation=ACTIVATION_COMMANDED)
        self.assertFalse(chain_is_hot(validate_chain(cold)))

    def test_non_record_rejected(self):
        with self.assertRaises(ValueError):
            chain_is_hot({"name": "A"})


class CommonElementTests(unittest.TestCase):
    def test_independent_chains_share_nothing(self):
        records = [validate_chain(CHAIN_A), validate_chain(CHAIN_B)]
        self.assertEqual(common_elements(records), [])

    def test_a_shared_antenna_is_reported(self):
        shared = chain("B", ["ANT1", "RX2", "DEM2", "DEC2"])
        records = [validate_chain(CHAIN_A), validate_chain(shared)]
        self.assertEqual(common_elements(records), ["ANT1"])

    def test_all_shared_elements_are_reported_in_order(self):
        twin = chain("B", ["ANT1", "RX1", "DEM2", "DEC2"])
        records = [validate_chain(CHAIN_A), validate_chain(twin)]
        self.assertEqual(common_elements(records), ["ANT1", "RX1"])

    def test_empty_record_set_shares_nothing(self):
        self.assertEqual(common_elements([]), [])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            common_elements([{"name": "A"}])


class SeveringDepthTests(unittest.TestCase):
    def test_two_independent_hot_chains_need_two_failures(self):
        records = [validate_chain(CHAIN_A), validate_chain(CHAIN_B)]
        self.assertEqual(severing_depth(records), 2)

    def test_a_shared_element_collapses_the_depth_to_one(self):
        shared = chain("B", ["ANT1", "RX2", "DEM2", "DEC2"])
        records = [validate_chain(CHAIN_A), validate_chain(shared)]
        self.assertEqual(severing_depth(records), 1)

    def test_cold_spare_does_not_add_depth(self):
        cold = chain("B", ["ANT2", "RX2", "DEM2", "DEC2"], activation=ACTIVATION_COMMANDED)
        records = [validate_chain(CHAIN_A), validate_chain(cold)]
        self.assertEqual(severing_depth(records), 1)

    def test_no_hot_chain_gives_zero_depth(self):
        cold = chain("A", ["ANT1", "RX1", "DEM1", "DEC1"], powered=False)
        self.assertEqual(severing_depth([validate_chain(cold)]), 0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"chains": [CHAIN_A, CHAIN_B]}
        spec.update(overrides)
        return spec

    def test_two_independent_hot_chains_are_compliant(self):
        result = assess_hot_redundancy(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["hot_count"], 2)

    def test_default_minimum_is_two(self):
        self.assertEqual(MINIMUM_HOT_CHAINS, 2)

    def test_single_chain_fails_the_minimum(self):
        result = assess_hot_redundancy(self._spec(chains=[CHAIN_A]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("are hot" in f for f in result["findings"]))

    def test_cold_spare_is_named_with_its_reason(self):
        cold = chain("B", ["ANT2", "RX2", "DEM2", "DEC2"], activation=ACTIVATION_COMMANDED)
        result = assess_hot_redundancy(self._spec(chains=[CHAIN_A, cold]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("needs a command" in f for f in result["findings"]))

    def test_shared_element_fails_despite_two_hot_chains(self):
        shared = chain("B", ["ANT1", "RX2", "DEM2", "DEC2"])
        result = assess_hot_redundancy(self._spec(chains=[CHAIN_A, shared]))
        self.assertEqual(result["hot_count"], 2)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["common_elements"], ["ANT1"])

    def test_incomplete_chain_is_named_with_its_missing_roles(self):
        short = {
            "name": "B",
            "elements": [{"role": "antenna", "id": "ANT2"}],
            "powered": True,
            "enabled": True,
            "activation": ACTIVATION_ALWAYS_ON,
        }
        result = assess_hot_redundancy(self._spec(chains=[CHAIN_A, short]))
        self.assertTrue(any("missing receiver" in f for f in result["findings"]))

    def test_three_chain_minimum_can_be_demanded(self):
        result = assess_hot_redundancy(self._spec(minimum_hot_chains=3))
        self.assertFalse(result["compliant"])

    def test_duplicate_chain_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_hot_redundancy(self._spec(chains=[CHAIN_A, dict(CHAIN_A)]))

    def test_empty_chain_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_hot_redundancy(self._spec(chains=[]))

    def test_zero_minimum_rejected(self):
        with self.assertRaises(ValueError):
            assess_hot_redundancy(self._spec(minimum_hot_chains=0))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_hot_redundancy(["chains"])


if __name__ == "__main__":
    unittest.main()
