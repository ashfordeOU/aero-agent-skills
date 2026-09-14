"""Contract tests for the clause 9.6.10 protection diode contact adherence run.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused adherence policy,
an unstated device configuration, an integral unit with no admissible or no
covering equivalent route, a lot presented with required sites unpulled, and
a device sentenced by the site that let go first.
"""

import unittest

from e2008_diode_contact_adherence_test_logic import (
    ADHERENCE_CONFIGURATION_NOT_STATED,
    CONTACTS_DURABLE,
    CONTACTS_NOT_DURABLE,
    DEFAULT_ADHERENCE_POLICY,
    EQUIVALENT_ROUTE_ACCEPTED,
    EQUIVALENT_ROUTE_NOT_DEMONSTRATED,
    EXTERNAL,
    INTEGRAL,
    REQUIRED_SITES_MISSING,
    adherence_stress_mpa,
    assess_diode_contact_adherence,
    equivalent_coverage_fraction,
    equivalent_coverage_sufficient,
    equivalent_route_admissible,
    missing_sites,
    normalize_configuration,
    site_durable,
    validate_adherence_policy,
    validate_site_reading,
    weakest_site,
)

MIN_STRESS = 2.0


def _policy(**overrides):
    policy = dict(DEFAULT_ADHERENCE_POLICY)
    policy.update(overrides)
    return policy


def _sites(anode_force=9.0, cathode_force=8.4):
    return [
        {
            "site": "anode-terminal",
            "adherence_force_n": anode_force,
            "bonded_area_mm2": 3.0,
        },
        {
            "site": "cathode-terminal",
            "adherence_force_n": cathode_force,
            "bonded_area_mm2": 3.0,
        },
    ]


def _devices():
    return [
        {"id": "pd-01", "sites": _sites()},
        {"id": "pd-02", "sites": _sites(8.7, 9.3)},
    ]


def _case(**overrides):
    case = {"configuration": "external", "devices": _devices()}
    case.update(overrides)
    return case


def _integral_case(**overrides):
    case = {
        "configuration": "integral",
        "equivalent_route": {
            "method": "witness-coupon-pull",
            "covered_sites": ["anode-terminal", "cathode-terminal"],
        },
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_adherence_policy(DEFAULT_ADHERENCE_POLICY),
            DEFAULT_ADHERENCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy("min_adherence_stress_mpa")

    def test_zero_minimum_stress_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(_policy(min_adherence_stress_mpa=0.0))

    def test_empty_required_sites_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(_policy(required_sites=()))

    def test_repeated_required_site_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(
                _policy(required_sites=("anode-terminal", "anode-terminal"))
            )

    def test_coverage_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(_policy(min_equivalent_coverage_fraction=1.4))

    def test_a_site_list_given_as_a_bare_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy(_policy(required_sites="anode-terminal"))


class ConfigurationTests(unittest.TestCase):
    def test_discrete_reads_as_external(self):
        self.assertEqual(normalize_configuration("discrete"), EXTERNAL)

    def test_integrated_reads_as_integral(self):
        self.assertEqual(normalize_configuration("Integrated"), INTEGRAL)

    def test_an_unknown_configuration_rejected(self):
        with self.assertRaises(ValueError):
            normalize_configuration("bonded-somewhere")

    def test_a_blank_configuration_rejected(self):
        with self.assertRaises(ValueError):
            normalize_configuration("   ")


class StressTests(unittest.TestCase):
    def test_stress_divides_force_by_bonded_area(self):
        self.assertAlmostEqual(adherence_stress_mpa(9.0, 3.0), 3.0, places=9)

    def test_a_wider_bond_reports_a_lower_stress_for_the_same_force(self):
        narrow = adherence_stress_mpa(9.0, 3.0)
        wide = adherence_stress_mpa(9.0, 6.0)
        self.assertAlmostEqual(wide, narrow / 2.0, places=9)

    def test_zero_bonded_area_rejected(self):
        with self.assertRaises(ValueError):
            adherence_stress_mpa(9.0, 0.0)

    def test_a_negative_force_rejected(self):
        with self.assertRaises(ValueError):
            adherence_stress_mpa(-9.0, 3.0)

    def test_a_site_exactly_on_the_minimum_is_durable(self):
        self.assertTrue(site_durable(MIN_STRESS))

    def test_a_site_above_the_minimum_is_durable(self):
        self.assertTrue(site_durable(MIN_STRESS * 1.5))

    def test_a_site_below_the_minimum_is_not_durable(self):
        self.assertFalse(site_durable(MIN_STRESS * 0.5))

    def test_a_site_reading_is_read_back_in_full(self):
        name, force, area = validate_site_reading(_sites()[0])
        self.assertEqual(name, "anode-terminal")
        self.assertAlmostEqual(force, 9.0, places=9)
        self.assertAlmostEqual(area, 3.0, places=9)

    def test_a_blank_site_name_rejected(self):
        site = _sites()[0]
        site["site"] = "  "
        with self.assertRaises(ValueError):
            validate_site_reading(site)

    def test_the_weakest_site_sentences_the_device(self):
        records = [
            {"site": "anode-terminal", "adherence_stress_mpa": 3.0},
            {"site": "cathode-terminal", "adherence_stress_mpa": 2.8},
        ]
        self.assertEqual(weakest_site(records)["site"], "cathode-terminal")

    def test_sentencing_an_empty_site_set_rejected(self):
        with self.assertRaises(ValueError):
            weakest_site([])


class CoverageTests(unittest.TestCase):
    def test_a_complete_record_leaves_no_site_missing(self):
        self.assertEqual(
            missing_sites(["anode-terminal", "cathode-terminal"]), ()
        )

    def test_an_unpulled_site_is_named(self):
        self.assertEqual(missing_sites(["anode-terminal"]), ("cathode-terminal",))

    def test_an_admissible_route_is_accepted(self):
        self.assertTrue(equivalent_route_admissible("assembly-level-pull"))

    def test_an_invented_route_is_refused(self):
        self.assertFalse(equivalent_route_admissible("engineering-judgement"))

    def test_full_coverage_reads_as_one(self):
        self.assertAlmostEqual(
            equivalent_coverage_fraction(["anode-terminal", "cathode-terminal"]),
            1.0,
            places=9,
        )

    def test_half_coverage_reads_as_a_half(self):
        self.assertAlmostEqual(
            equivalent_coverage_fraction(["anode-terminal"]), 0.5, places=9
        )

    def test_coverage_exactly_on_the_policy_share_is_sufficient(self):
        self.assertTrue(
            equivalent_coverage_sufficient(
                ["anode-terminal"], _policy(min_equivalent_coverage_fraction=0.5)
            )
        )

    def test_coverage_below_the_policy_share_is_refused(self):
        self.assertFalse(equivalent_coverage_sufficient(["anode-terminal"]))

    def test_an_unrelated_covered_site_does_not_count(self):
        self.assertAlmostEqual(
            equivalent_coverage_fraction(["case-lid"]), 0.0, places=9
        )


class ExternalRunTests(unittest.TestCase):
    def test_a_clean_external_lot_is_durable(self):
        result = assess_diode_contact_adherence(_case())
        self.assertEqual(result["verdict"], CONTACTS_DURABLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["device_records"]), 2)

    def test_each_device_carries_its_weakest_site(self):
        result = assess_diode_contact_adherence(_case())
        first = result["device_records"][0]
        self.assertEqual(first["weakest_site"], "cathode-terminal")
        self.assertAlmostEqual(first["weakest_stress_mpa"], 8.4 / 3.0, places=9)

    def test_the_lot_weakest_stress_is_reported(self):
        result = assess_diode_contact_adherence(_case())
        self.assertAlmostEqual(result["weakest_stress_mpa"], 8.4 / 3.0, places=9)

    def test_a_weak_contact_sentences_the_lot(self):
        devices = _devices()
        devices[1]["sites"][0]["adherence_force_n"] = 1.2
        result = assess_diode_contact_adherence(_case(devices=devices))
        self.assertEqual(result["verdict"], CONTACTS_NOT_DURABLE)
        self.assertTrue(any("pd-02" in note for note in result["findings"]))

    def test_an_unpulled_required_site_stops_the_run(self):
        devices = _devices()
        devices[0]["sites"] = [devices[0]["sites"][0]]
        result = assess_diode_contact_adherence(_case(devices=devices))
        self.assertEqual(result["verdict"], REQUIRED_SITES_MISSING)
        self.assertIn("pd-01/cathode-terminal", result["missing_sites"])

    def test_a_missing_site_is_reported_before_a_weak_one(self):
        devices = _devices()
        devices[0]["sites"] = [devices[0]["sites"][0]]
        devices[1]["sites"][0]["adherence_force_n"] = 1.2
        result = assess_diode_contact_adherence(_case(devices=devices))
        self.assertEqual(result["verdict"], REQUIRED_SITES_MISSING)

    def test_a_duplicate_device_id_rejected(self):
        devices = _devices()
        devices[1]["id"] = "pd-01"
        with self.assertRaises(ValueError):
            assess_diode_contact_adherence(_case(devices=devices))

    def test_a_repeated_site_on_one_device_rejected(self):
        devices = _devices()
        devices[0]["sites"][1]["site"] = "anode-terminal"
        with self.assertRaises(ValueError):
            assess_diode_contact_adherence(_case(devices=devices))

    def test_an_empty_presented_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_adherence(_case(devices=[]))

    def test_a_device_with_no_site_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_adherence(
                _case(devices=[{"id": "pd-01", "sites": []}])
            )

    def test_an_unstated_configuration_stops_the_run(self):
        case = _case()
        del case["configuration"]
        result = assess_diode_contact_adherence(case)
        self.assertEqual(result["verdict"], ADHERENCE_CONFIGURATION_NOT_STATED)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_adherence(["configuration"])


class IntegralRunTests(unittest.TestCase):
    def test_a_covering_admissible_route_is_accepted(self):
        result = assess_diode_contact_adherence(_integral_case())
        self.assertEqual(result["verdict"], EQUIVALENT_ROUTE_ACCEPTED)
        self.assertEqual(result["equivalent_route"], "witness-coupon-pull")
        self.assertAlmostEqual(
            result["equivalent_coverage_fraction"], 1.0, places=9
        )

    def test_no_declared_route_is_not_a_demonstration(self):
        case = _integral_case()
        del case["equivalent_route"]
        result = assess_diode_contact_adherence(case)
        self.assertEqual(result["verdict"], EQUIVALENT_ROUTE_NOT_DEMONSTRATED)

    def test_a_route_naming_no_sites_is_not_a_demonstration(self):
        result = assess_diode_contact_adherence(
            _integral_case(equivalent_route={"method": "assembly-level-pull"})
        )
        self.assertEqual(result["verdict"], EQUIVALENT_ROUTE_NOT_DEMONSTRATED)

    def test_an_inadmissible_route_is_refused(self):
        result = assess_diode_contact_adherence(
            _integral_case(
                equivalent_route={
                    "method": "engineering-judgement",
                    "covered_sites": ["anode-terminal", "cathode-terminal"],
                }
            )
        )
        self.assertEqual(result["verdict"], EQUIVALENT_ROUTE_NOT_DEMONSTRATED)

    def test_a_route_reaching_one_site_of_two_is_refused(self):
        result = assess_diode_contact_adherence(
            _integral_case(
                equivalent_route={
                    "method": "witness-coupon-pull",
                    "covered_sites": ["anode-terminal"],
                }
            )
        )
        self.assertEqual(result["verdict"], EQUIVALENT_ROUTE_NOT_DEMONSTRATED)
        self.assertAlmostEqual(
            result["equivalent_coverage_fraction"], 0.5, places=9
        )

    def test_an_integral_unit_needs_no_devices_record(self):
        result = assess_diode_contact_adherence(_integral_case())
        self.assertEqual(result["device_records"], [])

    def test_a_blank_route_method_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_contact_adherence(
                _integral_case(
                    equivalent_route={"method": "  ", "covered_sites": ["anode-terminal"]}
                )
            )


if __name__ == "__main__":
    unittest.main()
