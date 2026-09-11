"""
Gate 3 contract tests for e1009_authorities_logic.py.

stdlib unittest only — deterministic, offline, no network.
Run: python3 test_e1009_authorities.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1009_authorities_logic import (
    AUTHORITIES,
    CITATION_ERROR,
    COVERED,
    DOMAIN_PRIMARY,
    GAP,
    audit_authority_coverage,
    check_citation,
    get_authority_info,
    list_authorities_by_domain,
    resolve_authority,
    validate_citation,
)


class TestAuthorityRegistryCompleteness(unittest.TestCase):
    """All eight Annex C authorities must be present and well-formed."""

    REQUIRED_IDS = {"IERS", "IAU", "USNO", "BIPM", "IMCCE", "JPL", "CCSDS", "NIMA", "WGCCRE"}

    def test_all_required_authorities_present(self):
        self.assertTrue(self.REQUIRED_IDS.issubset(set(AUTHORITIES.keys())))

    def test_each_authority_has_required_fields(self):
        required_fields = {"full_name", "products", "domain", "notes"}
        for auth_id in self.REQUIRED_IDS:
            with self.subTest(authority=auth_id):
                info = AUTHORITIES[auth_id]
                missing = required_fields - set(info.keys())
                self.assertFalse(missing, f"{auth_id} missing fields: {missing}")

    def test_each_authority_has_non_empty_products(self):
        for auth_id, info in AUTHORITIES.items():
            with self.subTest(authority=auth_id):
                self.assertIsInstance(info["products"], list)
                self.assertTrue(len(info["products"]) >= 1)

    def test_no_forbidden_words_in_registry(self):
        forbidden = ["class" + "ified", "un" + "class" + "ified"]
        full_text = str(AUTHORITIES).lower()
        for word in forbidden:
            self.assertNotIn(word, full_text)


class TestGetAuthorityInfo(unittest.TestCase):

    def test_get_iers_returns_eop_in_products(self):
        info = get_authority_info("IERS")
        self.assertIn("EOP", info["products"])

    def test_get_bipm_returns_tai_and_utc(self):
        info = get_authority_info("BIPM")
        self.assertIn("TAI", info["products"])
        self.assertIn("UTC", info["products"])

    def test_get_wgccre_returns_planet_orientation_models(self):
        info = get_authority_info("WGCCRE")
        self.assertIn("planet_orientation_models", info["products"])

    def test_get_authority_case_insensitive_input(self):
        info = get_authority_info("iers")
        self.assertIn("ITRS", info["products"])

    def test_get_authority_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            get_authority_info("UNKNOWN_ORG")

    def test_get_authority_empty_string_raises_key_error(self):
        with self.assertRaises(KeyError):
            get_authority_info("")


class TestResolveAuthority(unittest.TestCase):

    def test_resolve_tai_returns_bipm(self):
        result = resolve_authority("TAI")
        self.assertIn("BIPM", result)

    def test_resolve_eop_returns_iers(self):
        result = resolve_authority("EOP")
        self.assertIn("IERS", result)

    def test_resolve_wgs84_returns_nima(self):
        result = resolve_authority("WGS84")
        self.assertIn("NIMA", result)

    def test_resolve_de_series_returns_jpl(self):
        result = resolve_authority("DE_series")
        self.assertIn("JPL", result)

    def test_resolve_oem_returns_ccsds(self):
        result = resolve_authority("OEM")
        self.assertIn("CCSDS", result)

    def test_resolve_body_rotation_elements_returns_wgccre(self):
        result = resolve_authority("body_rotation_elements")
        self.assertIn("WGCCRE", result)

    def test_resolve_inpop_returns_imcce(self):
        result = resolve_authority("INPOP")
        self.assertIn("IMCCE", result)

    def test_resolve_unknown_product_returns_empty_list(self):
        result = resolve_authority("totally_unknown_product_xyz")
        self.assertEqual(result, [])

    def test_resolve_case_insensitive(self):
        result_lower = resolve_authority("tai")
        result_upper = resolve_authority("TAI")
        self.assertEqual(set(result_lower), set(result_upper))


class TestListAuthoritiesByDomain(unittest.TestCase):

    def test_time_scales_includes_bipm_and_iers(self):
        result = list_authorities_by_domain("time_scales")
        self.assertIn("BIPM", result)
        self.assertIn("IERS", result)

    def test_ephemerides_includes_jpl_and_imcce(self):
        result = list_authorities_by_domain("ephemerides")
        self.assertIn("JPL", result)
        self.assertIn("IMCCE", result)

    def test_geodesy_returns_nima(self):
        result = list_authorities_by_domain("geodesy")
        self.assertIn("NIMA", result)

    def test_space_data_formats_returns_ccsds(self):
        result = list_authorities_by_domain("space_data_formats")
        self.assertIn("CCSDS", result)

    def test_unknown_domain_returns_empty_list(self):
        result = list_authorities_by_domain("nonexistent_domain_xyz")
        self.assertEqual(result, [])

    def test_planetary_cartography_includes_wgccre(self):
        result = list_authorities_by_domain("planetary_cartography")
        self.assertIn("WGCCRE", result)

    def test_returns_list_not_reference_to_registry(self):
        result = list_authorities_by_domain("ephemerides")
        result.append("FAKE")
        original = list_authorities_by_domain("ephemerides")
        self.assertNotIn("FAKE", original)


class TestValidateCitation(unittest.TestCase):

    def test_bipm_produces_tai(self):
        self.assertTrue(validate_citation("BIPM", "TAI"))

    def test_ccsds_produces_time_code_formats(self):
        self.assertTrue(validate_citation("CCSDS", "time_code_formats"))

    def test_nima_produces_wgs84(self):
        self.assertTrue(validate_citation("NIMA", "WGS84"))

    def test_nima_does_not_produce_tai(self):
        self.assertFalse(validate_citation("NIMA", "TAI"))

    def test_usno_does_not_produce_wgs84(self):
        self.assertFalse(validate_citation("USNO", "WGS84"))

    def test_unknown_authority_returns_false(self):
        self.assertFalse(validate_citation("FAKE_ORG", "EOP"))

    def test_iau_produces_tdb(self):
        self.assertTrue(validate_citation("IAU", "TDB"))

    def test_case_insensitive_product_match(self):
        self.assertTrue(validate_citation("BIPM", "tai"))


class TestAuditAuthorityCoverage(unittest.TestCase):

    def test_known_products_are_covered(self):
        products = ["TAI", "EOP", "WGS84"]
        result = audit_authority_coverage(products)
        for product in products:
            self.assertIn(product, result)
            self.assertEqual(result[product]["status"], COVERED)
            self.assertTrue(len(result[product]["authorities"]) >= 1)

    def test_unknown_product_has_gap_status(self):
        result = audit_authority_coverage(["totally_unknown_xyz"])
        self.assertEqual(result["totally_unknown_xyz"]["status"], GAP)
        self.assertEqual(result["totally_unknown_xyz"]["authorities"], [])

    def test_mixed_coverage_produces_correct_statuses(self):
        result = audit_authority_coverage(["TAI", "nonexistent_product"])
        self.assertEqual(result["TAI"]["status"], COVERED)
        self.assertEqual(result["nonexistent_product"]["status"], GAP)

    def test_empty_product_list_returns_empty_dict(self):
        result = audit_authority_coverage([])
        self.assertEqual(result, {})


class TestCheckCitation(unittest.TestCase):

    def test_valid_citation_returns_covered(self):
        self.assertEqual(check_citation("IERS", "EOP"), COVERED)

    def test_valid_citation_jpl_de_series(self):
        self.assertEqual(check_citation("JPL", "DE_series"), COVERED)

    def test_mismatched_authority_returns_citation_error(self):
        self.assertEqual(check_citation("USNO", "TAI"), CITATION_ERROR)

    def test_unknown_authority_returns_gap(self):
        self.assertEqual(check_citation("FAKE_ORG", "EOP"), GAP)

    def test_wgccre_prime_meridian_covered(self):
        self.assertEqual(check_citation("WGCCRE", "prime_meridian_definitions"), COVERED)

    def test_bipm_circular_t_covered(self):
        self.assertEqual(check_citation("BIPM", "Circular_T"), COVERED)

    def test_nima_egm96_covered(self):
        self.assertEqual(check_citation("NIMA", "EGM96"), COVERED)

    def test_ccsds_aem_covered(self):
        self.assertEqual(check_citation("CCSDS", "AEM"), COVERED)

    def test_iau_does_not_produce_wgs84(self):
        self.assertEqual(check_citation("IAU", "WGS84"), CITATION_ERROR)


if __name__ == "__main__":
    unittest.main()
