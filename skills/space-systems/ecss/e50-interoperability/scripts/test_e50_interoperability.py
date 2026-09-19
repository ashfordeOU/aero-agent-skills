"""Contract tests for the clause 5.6.4 interoperability logic."""

import unittest

from e50_interoperability_logic import (
    PARTIAL,
    SUPPORTED,
    UNCONFIRMED,
    UNSUPPORTED,
    assess_interoperability,
    common_options,
    cross_support_fraction,
    mismatched_attributes,
    negotiated_profile,
    options_to_add,
    partner_verdict,
    unconfirmed_attributes,
    validate_option,
    validate_partner_catalogue,
    validate_profile,
)

MISSION = {
    "frequency-band": ["s-band", "x-band"],
    "modulation": ["bpsk", "gmsk"],
    "channel-coding": ["turbo-1-2", "ldpc-7-8"],
    "frame-format": ["tm-transfer-frame", "uslp-frame"],
}

AGENCY_A = {
    "frequency-band": ["x-band"],
    "modulation": ["gmsk"],
    "channel-coding": ["ldpc-7-8"],
    "frame-format": ["uslp-frame"],
}

AGENCY_B = {
    "frequency-band": ["ka-band"],
    "modulation": ["gmsk"],
    "channel-coding": ["ldpc-7-8"],
    "frame-format": ["uslp-frame"],
}


def _partial_partner():
    partner = dict(AGENCY_A)
    partner["ranging-scheme"] = ["pn-regenerative"]
    return partner


class ValidationTests(unittest.TestCase):
    def test_blank_option_rejected(self):
        with self.assertRaises(ValueError):
            validate_option("  ")

    def test_non_string_option_rejected(self):
        with self.assertRaises(ValueError):
            validate_option(5)

    def test_profile_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_profile(["x-band"])

    def test_profile_missing_a_required_attribute_rejected(self):
        partial = {k: v for k, v in MISSION.items() if k != "modulation"}
        with self.assertRaises(ValueError):
            validate_profile(partial)

    def test_attribute_with_no_options_rejected(self):
        broken = dict(MISSION, modulation=[])
        with self.assertRaises(ValueError):
            validate_profile(broken)

    def test_bare_string_options_rejected(self):
        broken = dict(MISSION, modulation="gmsk")
        with self.assertRaises(ValueError):
            validate_profile(broken)

    def test_empty_partner_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            validate_partner_catalogue({})

    def test_catalogue_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_partner_catalogue([AGENCY_A])

    def test_valid_profile_is_normalised_to_sets(self):
        profile = validate_profile(MISSION)
        self.assertEqual(profile["modulation"], frozenset(["bpsk", "gmsk"]))


class MatchTests(unittest.TestCase):
    def test_common_option_is_found(self):
        self.assertEqual(common_options(MISSION, AGENCY_A, "modulation"), ("gmsk",))

    def test_no_common_option_on_a_clashing_attribute(self):
        self.assertEqual(common_options(MISSION, AGENCY_B, "frequency-band"), ())

    def test_attribute_the_mission_never_declared_is_rejected(self):
        with self.assertRaises(ValueError):
            common_options(MISSION, AGENCY_A, "ranging-scheme")

    def test_compatible_partner_has_no_mismatch(self):
        self.assertEqual(mismatched_attributes(MISSION, AGENCY_A), ())

    def test_band_clash_is_named(self):
        self.assertEqual(mismatched_attributes(MISSION, AGENCY_B), ("frequency-band",))

    def test_partner_extra_attribute_is_not_a_mission_gap(self):
        self.assertEqual(unconfirmed_attributes(MISSION, _partial_partner()), ())

    def test_mission_attribute_absent_from_the_partner_is_unconfirmed(self):
        mission = dict(MISSION, ranging_scheme_note=["pn-regenerative"])
        self.assertEqual(
            unconfirmed_attributes(mission, AGENCY_A), ("ranging_scheme_note",)
        )


class VerdictTests(unittest.TestCase):
    def test_compatible_partner_is_supported(self):
        self.assertEqual(partner_verdict(MISSION, AGENCY_A), SUPPORTED)

    def test_clashing_partner_is_unsupported(self):
        self.assertEqual(partner_verdict(MISSION, AGENCY_B), UNSUPPORTED)

    def test_undeclared_attribute_is_unconfirmed_not_unsupported(self):
        mission = dict(MISSION, ranging_scheme_note=["pn-regenerative"])
        self.assertEqual(partner_verdict(mission, AGENCY_A), UNCONFIRMED)

    def test_negotiated_profile_is_deterministic(self):
        agreed = negotiated_profile(MISSION, AGENCY_A)
        self.assertEqual(agreed["frequency-band"], "x-band")
        self.assertEqual(agreed, negotiated_profile(MISSION, AGENCY_A))

    def test_no_negotiated_profile_for_an_unsupported_partner(self):
        with self.assertRaises(ValueError):
            negotiated_profile(MISSION, AGENCY_B)

    def test_remedy_names_the_option_the_mission_lacks(self):
        self.assertEqual(options_to_add(MISSION, AGENCY_B), {"frequency-band": ("ka-band",)})

    def test_supported_partner_needs_no_remedy(self):
        self.assertEqual(options_to_add(MISSION, AGENCY_A), {})

    def test_added_option_actually_restores_support(self):
        remedy = options_to_add(MISSION, AGENCY_B)
        widened = dict(MISSION)
        for attribute, options in remedy.items():
            widened[attribute] = list(widened[attribute]) + list(options)
        self.assertEqual(partner_verdict(widened, AGENCY_B), SUPPORTED)


class CoverageTests(unittest.TestCase):
    def test_all_partners_supported_is_a_full_fraction(self):
        self.assertAlmostEqual(
            cross_support_fraction(MISSION, {"a": AGENCY_A}), 1.0, places=9
        )

    def test_one_of_two_partners_supported(self):
        self.assertAlmostEqual(
            cross_support_fraction(MISSION, {"a": AGENCY_A, "b": AGENCY_B}),
            0.5,
            places=9,
        )


class AssessTests(unittest.TestCase):
    def test_required_partner_supported_is_interoperable(self):
        result = assess_interoperability(MISSION, {"a": AGENCY_A}, ["a"])
        self.assertEqual(result["verdict"], SUPPORTED)
        self.assertTrue(result["interoperable"])

    def test_required_partner_unsupported_is_not_interoperable(self):
        result = assess_interoperability(MISSION, {"b": AGENCY_B}, ["b"])
        self.assertEqual(result["verdict"], UNSUPPORTED)
        self.assertFalse(result["interoperable"])

    def test_mixed_required_set_is_partial(self):
        result = assess_interoperability(
            MISSION, {"a": AGENCY_A, "b": AGENCY_B}, ["a", "b"]
        )
        self.assertEqual(result["verdict"], PARTIAL)

    def test_optional_partner_does_not_change_the_verdict(self):
        result = assess_interoperability(
            MISSION, {"a": AGENCY_A, "b": AGENCY_B}, ["a"]
        )
        self.assertEqual(result["verdict"], SUPPORTED)

    def test_unsupported_partner_is_still_reported(self):
        result = assess_interoperability(MISSION, {"a": AGENCY_A, "b": AGENCY_B}, ["a"])
        self.assertTrue(any("shares no option" in f for f in result["findings"]))

    def test_findings_carry_the_remedy(self):
        result = assess_interoperability(MISSION, {"b": AGENCY_B}, ["b"])
        self.assertTrue(any("ka-band" in f for f in result["findings"]))

    def test_supported_only_set_reports_nothing(self):
        result = assess_interoperability(MISSION, {"a": AGENCY_A}, ["a"])
        self.assertEqual(result["findings"], ())

    def test_repeated_required_partner_is_counted_once(self):
        result = assess_interoperability(MISSION, {"a": AGENCY_A}, ["a", "a"])
        self.assertEqual(result["required_partners"], ("a",))

    def test_unstated_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_interoperability(MISSION, {"a": AGENCY_A}, [])

    def test_required_partner_without_a_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_interoperability(MISSION, {"a": AGENCY_A}, ["c"])

    def test_required_partners_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_interoperability(MISSION, {"a": AGENCY_A}, "a")

    def test_cross_support_fraction_is_carried(self):
        result = assess_interoperability(MISSION, {"a": AGENCY_A, "b": AGENCY_B}, ["a"])
        self.assertAlmostEqual(result["cross_support_fraction"], 0.5, places=9)


if __name__ == "__main__":
    unittest.main()
