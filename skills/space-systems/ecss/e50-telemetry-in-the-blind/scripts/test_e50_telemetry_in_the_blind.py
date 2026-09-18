"""Contract tests for the clause 5.5.4 telemetry-in-the-blind logic."""

import math
import unittest

from e50_telemetry_in_the_blind_logic import (
    BOLTZMANN_DBW_PER_K_HZ,
    MARGIN_TOLERANCE_DB,
    arming_findings,
    assess_telemetry_in_the_blind,
    blind_link_margin_db,
    command_dependency_findings,
    default_configuration_findings,
    free_space_loss_db,
    rate_term_db,
    supportable_rate_bps,
    validate_blind_configuration,
)

ACQUIRABLE = {
    "modulation": ["bpsk-residual-carrier", "bpsk-suppressed-carrier"],
    "coding": ["convolutional-r12-k7", "concatenated-rs-convolutional"],
    "bit_rate_bps": [16.0, 64.0, 256.0],
}


def _config(**overrides):
    config = {
        "frequency_mhz": 2250.0,
        "bit_rate_bps": 16.0,
        "modulation": "bpsk-residual-carrier",
        "coding": "convolutional-r12-k7",
        "uplink_loss_timeout_s": 43200.0,
        "command_dependent_parameters": [],
    }
    config.update(overrides)
    return config


def _budget(**overrides):
    budget = {
        "eirp_dbw": 5.0,
        "range_km": 40000.0,
        "frequency_mhz": 2250.0,
        "bit_rate_bps": 16.0,
        "station_g_over_t_dbk": 37.0,
        "required_ebn0_db": 2.5,
        "atmospheric_loss_db": 0.5,
        "polarisation_loss_db": 0.5,
        "implementation_loss_db": 1.0,
    }
    budget.update(overrides)
    return budget


class ValidateConfigurationTests(unittest.TestCase):
    def test_returns_normalised_record(self):
        record = validate_blind_configuration(_config())
        self.assertAlmostEqual(record["frequency_mhz"], 2250.0)
        self.assertEqual(record["modulation"], "bpsk-residual-carrier")

    def test_command_dependent_list_defaults_to_empty(self):
        config = _config()
        del config["command_dependent_parameters"]
        self.assertEqual(validate_blind_configuration(config)["command_dependent_parameters"], [])

    def test_missing_key_rejected(self):
        config = _config()
        del config["coding"]
        with self.assertRaises(ValueError):
            validate_blind_configuration(config)

    def test_zero_bit_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_blind_configuration(_config(bit_rate_bps=0.0))

    def test_negative_timeout_rejected(self):
        with self.assertRaises(ValueError):
            validate_blind_configuration(_config(uplink_loss_timeout_s=-1.0))

    def test_empty_modulation_rejected(self):
        with self.assertRaises(ValueError):
            validate_blind_configuration(_config(modulation="  "))

    def test_non_finite_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_blind_configuration(_config(frequency_mhz=float("inf")))

    def test_string_command_dependency_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_blind_configuration(_config(command_dependent_parameters="coding"))

    def test_non_mapping_configuration_rejected(self):
        with self.assertRaises(ValueError):
            validate_blind_configuration(["frequency_mhz"])


class PathLossTests(unittest.TestCase):
    def test_unit_range_and_frequency_gives_the_constant(self):
        self.assertAlmostEqual(free_space_loss_db(1.0, 1.0), 32.44, places=9)

    def test_doubling_range_costs_six_db(self):
        near = free_space_loss_db(20000.0, 2250.0)
        far = free_space_loss_db(40000.0, 2250.0)
        self.assertAlmostEqual(far - near, 20.0 * math.log10(2.0), places=9)

    def test_doubling_frequency_costs_six_db(self):
        low = free_space_loss_db(40000.0, 2250.0)
        high = free_space_loss_db(40000.0, 4500.0)
        self.assertAlmostEqual(high - low, 20.0 * math.log10(2.0), places=9)

    def test_zero_range_rejected(self):
        with self.assertRaises(ValueError):
            free_space_loss_db(0.0, 2250.0)

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            free_space_loss_db(40000.0, -2250.0)

    def test_rate_term_of_a_kilobit(self):
        self.assertAlmostEqual(rate_term_db(1000.0), 30.0, places=9)

    def test_rate_term_doubles_by_three_db(self):
        self.assertAlmostEqual(
            rate_term_db(32.0) - rate_term_db(16.0), 10.0 * math.log10(2.0), places=9
        )

    def test_rate_term_rejects_zero(self):
        with self.assertRaises(ValueError):
            rate_term_db(0.0)


class LinkMarginTests(unittest.TestCase):
    def test_margin_is_finite_for_a_representative_budget(self):
        self.assertTrue(math.isfinite(blind_link_margin_db(_budget())))

    def test_halving_the_rate_buys_three_db(self):
        fast = blind_link_margin_db(_budget(bit_rate_bps=32.0))
        slow = blind_link_margin_db(_budget(bit_rate_bps=16.0))
        self.assertAlmostEqual(slow - fast, 10.0 * math.log10(2.0), places=9)

    def test_extra_implementation_loss_reduces_the_margin_one_for_one(self):
        base = blind_link_margin_db(_budget(implementation_loss_db=1.0))
        worse = blind_link_margin_db(_budget(implementation_loss_db=3.0))
        self.assertAlmostEqual(base - worse, 2.0, places=9)

    def test_station_figure_of_merit_adds_to_the_margin(self):
        poor = blind_link_margin_db(_budget(station_g_over_t_dbk=30.0))
        good = blind_link_margin_db(_budget(station_g_over_t_dbk=37.0))
        self.assertAlmostEqual(good - poor, 7.0, places=9)

    def test_noise_constant_is_the_standard_value(self):
        self.assertAlmostEqual(BOLTZMANN_DBW_PER_K_HZ, -228.6, places=9)

    def test_negative_loss_rejected(self):
        with self.assertRaises(ValueError):
            blind_link_margin_db(_budget(atmospheric_loss_db=-1.0))

    def test_missing_budget_key_rejected(self):
        budget = _budget()
        del budget["required_ebn0_db"]
        with self.assertRaises(ValueError):
            blind_link_margin_db(budget)

    def test_non_mapping_budget_rejected(self):
        with self.assertRaises(ValueError):
            blind_link_margin_db(["eirp_dbw"])

    def test_zero_margin_budget_supports_exactly_the_flown_rate(self):
        base = _budget()
        margin = blind_link_margin_db(base)
        tight = _budget(required_ebn0_db=base["required_ebn0_db"] + margin)
        self.assertAlmostEqual(blind_link_margin_db(tight), 0.0, places=9)
        self.assertAlmostEqual(
            supportable_rate_bps(tight), tight["bit_rate_bps"], places=6
        )

    def test_positive_margin_supports_a_higher_rate(self):
        base = _budget()
        headroom = blind_link_margin_db(base)
        self.assertAlmostEqual(
            supportable_rate_bps(base),
            base["bit_rate_bps"] * math.pow(10.0, headroom / 10.0),
            places=6,
        )


class ArmingTests(unittest.TestCase):
    def test_early_arming_is_clean(self):
        self.assertEqual(arming_findings(3600.0, 43200.0), [])

    def test_late_arming_is_flagged(self):
        findings = arming_findings(86400.0, 43200.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("later than", findings[0])

    def test_arming_exactly_at_the_limit_is_accepted(self):
        self.assertEqual(arming_findings(43200.0, 43200.0), [])

    def test_zero_timeout_rejected(self):
        with self.assertRaises(ValueError):
            arming_findings(0.0, 43200.0)


class DefaultConfigurationTests(unittest.TestCase):
    def test_default_configuration_is_clean(self):
        self.assertEqual(default_configuration_findings(_config(), ACQUIRABLE), [])

    def test_unknown_modulation_is_flagged(self):
        findings = default_configuration_findings(
            _config(modulation="gmsk-blind-only"), ACQUIRABLE
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("modulation", findings[0])

    def test_unknown_coding_is_flagged(self):
        findings = default_configuration_findings(
            _config(coding="ldpc-r78-blocklength-16384"), ACQUIRABLE
        )
        self.assertIn("coding", findings[0])

    def test_off_plan_rate_is_flagged(self):
        findings = default_configuration_findings(_config(bit_rate_bps=20.0), ACQUIRABLE)
        self.assertTrue(any("bit rate" in f for f in findings))

    def test_acquirable_map_missing_a_key_rejected(self):
        partial = dict(ACQUIRABLE)
        del partial["coding"]
        with self.assertRaises(ValueError):
            default_configuration_findings(_config(), partial)

    def test_empty_rate_list_rejected(self):
        broken = dict(ACQUIRABLE, bit_rate_bps=[])
        with self.assertRaises(ValueError):
            default_configuration_findings(_config(), broken)

    def test_command_dependent_parameter_is_flagged(self):
        findings = command_dependency_findings(
            _config(command_dependent_parameters=["bit_rate_bps"])
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("telecommand", findings[0])

    def test_no_command_dependency_is_clean(self):
        self.assertEqual(command_dependency_findings(_config()), [])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "configuration": _config(),
            "required_max_timeout_s": 43200.0,
            "acquirable": ACQUIRABLE,
            "budget": _budget(),
        }
        spec.update(overrides)
        return spec

    def test_clean_design_is_compliant(self):
        result = assess_telemetry_in_the_blind(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["link_closes"])

    def test_budget_inherits_the_configuration_rate(self):
        budget = _budget()
        del budget["bit_rate_bps"]
        del budget["frequency_mhz"]
        result = assess_telemetry_in_the_blind(
            self._spec(configuration=_config(bit_rate_bps=64.0), budget=budget)
        )
        self.assertAlmostEqual(
            result["supportable_rate_bps"],
            64.0 * math.pow(10.0, result["margin_db"] / 10.0),
            places=6,
        )

    def test_late_arming_is_reported(self):
        result = assess_telemetry_in_the_blind(
            self._spec(configuration=_config(uplink_loss_timeout_s=90000.0))
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("arms" in f for f in result["findings"]))

    def test_non_default_coding_is_reported(self):
        result = assess_telemetry_in_the_blind(
            self._spec(configuration=_config(coding="ldpc-r78-blocklength-16384"))
        )
        self.assertFalse(result["compliant"])

    def test_link_that_does_not_close_is_reported(self):
        result = assess_telemetry_in_the_blind(
            self._spec(budget=_budget(range_km=400000.0, bit_rate_bps=2048000.0))
        )
        self.assertFalse(result["link_closes"])
        self.assertTrue(any("does not close" in f for f in result["findings"]))

    def test_exact_zero_margin_still_closes(self):
        base = _budget()
        margin = blind_link_margin_db(base)
        tight = _budget(required_ebn0_db=base["required_ebn0_db"] + margin)
        result = assess_telemetry_in_the_blind(self._spec(budget=tight))
        self.assertTrue(result["link_closes"])
        self.assertAlmostEqual(result["margin_db"], 0.0, places=9)

    def test_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE_DB, 1e-6)

    def test_path_loss_is_reported(self):
        result = assess_telemetry_in_the_blind(self._spec())
        self.assertAlmostEqual(
            result["free_space_loss_db"], free_space_loss_db(40000.0, 2250.0), places=9
        )

    def test_findings_accumulate_across_defect_kinds(self):
        result = assess_telemetry_in_the_blind(
            self._spec(
                configuration=_config(
                    uplink_loss_timeout_s=90000.0,
                    modulation="gmsk-blind-only",
                    command_dependent_parameters=["coding"],
                ),
                budget=_budget(range_km=400000.0, bit_rate_bps=2048000.0),
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["acquirable"]
        with self.assertRaises(ValueError):
            assess_telemetry_in_the_blind(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_telemetry_in_the_blind(["configuration"])


if __name__ == "__main__":
    unittest.main()
