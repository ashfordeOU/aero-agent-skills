"""Contract test for the crimped-connection scope leaf (stdlib unittest)."""

import unittest

from q7026_applicability_and_connections_logic import (
    ACCEPTABLE_FILL,
    COAX_FERRULE,
    FILL_MAX,
    FILL_MIN,
    LUG,
    MACHINED_CONTACT,
    OUT_OF_SCOPE,
    OVERFILLED,
    SPLICE,
    STAMPED_CONTACT,
    UNDERFILLED,
    assess_connection,
    assess_harness,
    barrel_fill_ratio,
    categorize_connection,
    conductor_limit,
    fill_verdict,
    in_scope,
    mixed_construction,
    normalize_method,
    normalize_termination,
    validate_conductor,
    validate_connection,
)


def conductor(**kw):
    c = {"conductor_csa_mm2": 0.5, "construction": "stranded"}
    c.update(kw)
    return c


def connection(**kw):
    c = {
        "connection_id": "W12-P3-7",
        "joining_method": "crimp",
        "termination_type": "machined-contact",
        "conductors": [conductor()],
        "barrel_bore_csa_mm2": 1.0,
    }
    c.update(kw)
    return c


class TestMethodNormalization(unittest.TestCase):
    def test_a_crimp_is_a_crimp(self):
        self.assertEqual(normalize_method("Crimp"), "crimp")

    def test_a_past_tense_method_folds_to_its_token(self):
        self.assertEqual(normalize_method("soldered"), "solder")

    def test_spacing_and_underscores_fold(self):
        self.assertEqual(normalize_method("wire_wrap"), "wire-wrap")

    def test_an_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            normalize_method("glued")

    def test_a_blank_method_raises(self):
        with self.assertRaises(ValueError):
            normalize_method("   ")

    def test_an_unknown_termination_raises(self):
        with self.assertRaises(ValueError):
            normalize_termination("push-fit")

    def test_a_known_termination_folds(self):
        self.assertEqual(normalize_termination("In-Line Splice"), "in-line-splice")


class TestScope(unittest.TestCase):
    def test_a_crimped_contact_is_in_scope(self):
        self.assertTrue(in_scope(connection())["in_scope"])

    def test_a_soldered_joint_is_out_of_scope(self):
        result = in_scope(connection(joining_method="solder"))
        self.assertFalse(result["in_scope"])
        self.assertEqual(result["verdict"], OUT_OF_SCOPE)

    def test_an_insulation_displacement_joint_is_out_of_scope(self):
        self.assertFalse(
            in_scope(connection(joining_method="insulation-displacement"))["in_scope"]
        )

    def test_a_welded_joint_names_its_method_in_the_reason(self):
        result = in_scope(connection(joining_method="welded"))
        self.assertEqual(result["reason"], "joining-method-is-weld")

    def test_an_out_of_scope_joint_has_no_crimp_category(self):
        with self.assertRaises(ValueError):
            categorize_connection(connection(joining_method="wire-wrap"))


class TestCategories(unittest.TestCase):
    def test_a_machined_contact_categorizes(self):
        self.assertEqual(categorize_connection(connection()), MACHINED_CONTACT)

    def test_a_stamped_contact_categorizes(self):
        self.assertEqual(
            categorize_connection(connection(termination_type="stamped-contact")),
            STAMPED_CONTACT,
        )

    def test_a_splice_categorizes(self):
        self.assertEqual(
            categorize_connection(connection(termination_type="in-line-splice")),
            SPLICE,
        )

    def test_a_coaxial_ferrule_categorizes(self):
        self.assertEqual(
            categorize_connection(connection(termination_type="coaxial-ferrule")),
            COAX_FERRULE,
        )

    def test_a_contact_barrel_takes_one_conductor(self):
        self.assertEqual(conductor_limit(MACHINED_CONTACT), 1)

    def test_a_splice_barrel_takes_more_than_a_contact(self):
        self.assertGreater(conductor_limit(SPLICE), conductor_limit(MACHINED_CONTACT))

    def test_a_lug_takes_a_pair(self):
        self.assertEqual(conductor_limit(LUG), 2)

    def test_an_unknown_category_has_no_limit(self):
        with self.assertRaises(ValueError):
            conductor_limit("banana-crimp")


class TestBarrelFill(unittest.TestCase):
    def test_the_ratio_is_total_conductor_over_bore(self):
        self.assertAlmostEqual(
            barrel_fill_ratio([conductor(conductor_csa_mm2=0.6)], 1.2), 0.5, places=9
        )

    def test_several_conductors_sum(self):
        pair = [conductor(conductor_csa_mm2=0.3), conductor(conductor_csa_mm2=0.3)]
        self.assertAlmostEqual(barrel_fill_ratio(pair, 1.2), 0.5, places=9)

    def test_a_zero_bore_raises(self):
        with self.assertRaises(ValueError):
            barrel_fill_ratio([conductor()], 0.0)

    def test_an_empty_conductor_set_raises(self):
        with self.assertRaises(ValueError):
            barrel_fill_ratio([], 1.0)

    def test_a_fill_inside_the_window_is_acceptable(self):
        self.assertEqual(fill_verdict(0.6), ACCEPTABLE_FILL)

    def test_a_fill_exactly_on_the_floor_is_acceptable(self):
        self.assertEqual(fill_verdict(FILL_MIN), ACCEPTABLE_FILL)

    def test_a_fill_exactly_on_the_ceiling_is_acceptable(self):
        self.assertEqual(fill_verdict(FILL_MAX), ACCEPTABLE_FILL)

    def test_a_thin_conductor_underfills(self):
        self.assertEqual(fill_verdict(FILL_MIN - 0.1), UNDERFILLED)

    def test_a_fat_conductor_overfills(self):
        self.assertEqual(fill_verdict(FILL_MAX + 0.1), OVERFILLED)

    def test_a_negative_ratio_raises(self):
        with self.assertRaises(ValueError):
            fill_verdict(-0.2)


class TestConstruction(unittest.TestCase):
    def test_one_construction_is_not_mixed(self):
        self.assertFalse(mixed_construction([conductor(), conductor()]))

    def test_solid_with_stranded_is_mixed(self):
        self.assertTrue(
            mixed_construction([conductor(), conductor(construction="solid")])
        )

    def test_an_unknown_construction_raises(self):
        with self.assertRaises(ValueError):
            validate_conductor(conductor(construction="litz-ish"))

    def test_a_zero_cross_section_raises(self):
        with self.assertRaises(ValueError):
            validate_conductor(conductor(conductor_csa_mm2=0.0))


class TestAssessment(unittest.TestCase):
    def test_a_sound_contact_is_acceptable(self):
        result = assess_connection(connection())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["fill_verdict"], ACCEPTABLE_FILL)

    def test_two_conductors_in_a_contact_barrel_are_refused(self):
        result = assess_connection(
            connection(
                conductors=[
                    conductor(conductor_csa_mm2=0.3),
                    conductor(conductor_csa_mm2=0.3),
                ]
            )
        )
        self.assertFalse(result["acceptable"])
        self.assertIn(
            "conductor-count-2-over-the-limit-1-for-%s" % MACHINED_CONTACT,
            result["findings"],
        )

    def test_the_same_pair_in_a_splice_barrel_is_accepted(self):
        result = assess_connection(
            connection(
                termination_type="in-line-splice",
                conductors=[
                    conductor(conductor_csa_mm2=0.3),
                    conductor(conductor_csa_mm2=0.3),
                ],
            )
        )
        self.assertTrue(result["acceptable"])

    def test_a_mixed_barrel_is_refused_even_at_a_good_fill(self):
        result = assess_connection(
            connection(
                termination_type="in-line-splice",
                conductors=[
                    conductor(conductor_csa_mm2=0.3),
                    conductor(conductor_csa_mm2=0.3, construction="solid"),
                ],
            )
        )
        self.assertIn("solid-and-stranded-conductors-in-one-barrel", result["findings"])

    def test_an_overfilled_barrel_is_refused(self):
        result = assess_connection(
            connection(conductors=[conductor(conductor_csa_mm2=0.95)])
        )
        self.assertIn(OVERFILLED, result["findings"])

    def test_an_out_of_scope_joint_carries_no_category(self):
        result = assess_connection(connection(joining_method="solder"))
        self.assertIsNone(result["category"])
        self.assertFalse(result["in_scope"])

    def test_a_non_mapping_connection_raises(self):
        with self.assertRaises(ValueError):
            validate_connection("W12-P3-7")

    def test_a_blank_connection_id_raises(self):
        with self.assertRaises(ValueError):
            validate_connection(connection(connection_id="  "))


class TestHarness(unittest.TestCase):
    def test_a_clean_harness_reports_clean(self):
        report = assess_harness([connection(), connection(connection_id="W12-P3-8")])
        self.assertTrue(report["clean"])
        self.assertEqual(report["in_scope_count"], 2)

    def test_the_roll_up_counts_by_category(self):
        report = assess_harness(
            [
                connection(),
                connection(connection_id="S1", termination_type="in-line-splice"),
            ]
        )
        self.assertEqual(report["counts_by_category"][MACHINED_CONTACT], 1)
        self.assertEqual(report["counts_by_category"][SPLICE], 1)

    def test_an_out_of_scope_joint_is_counted_apart(self):
        report = assess_harness(
            [connection(), connection(connection_id="S2", joining_method="solder")]
        )
        self.assertEqual(report["counts_by_category"][OUT_OF_SCOPE], 1)
        self.assertEqual(report["in_scope_count"], 1)

    def test_findings_name_the_connection(self):
        report = assess_harness(
            [connection(connection_id="BAD1", conductors=[conductor(conductor_csa_mm2=0.95)])]
        )
        self.assertTrue(any(f.startswith("BAD1: ") for f in report["findings"]))

    def test_an_empty_harness_raises(self):
        with self.assertRaises(ValueError):
            assess_harness([])

    def test_a_non_list_harness_raises(self):
        with self.assertRaises(ValueError):
            assess_harness(connection())


if __name__ == "__main__":
    unittest.main()
