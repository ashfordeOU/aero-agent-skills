"""Contract test for the storage-condition-requirements leaf (stdlib unittest)."""

import unittest

from q7022_storage_condition_requirements_logic import (
    DESICCATION_LIMIT_PCT,
    FAMILY_DEFAULTS,
    assess_material,
    assess_storage_conditions,
    derive_envelope,
    disposition_for,
    envelope_findings,
    family_default,
    reachable_extremes,
    validate_material,
    validate_store,
)


def material(mid="M-1", family="elastomer", **kw):
    record = {"id": mid, "family": family}
    record.update(kw)
    return record


def store(sid="S-1", **kw):
    record = {
        "id": sid,
        "set_temp_min_c": 15.0,
        "set_temp_max_c": 22.0,
        "temp_control_tolerance_c": 1.0,
        "set_rh_max_pct": 50.0,
        "rh_control_tolerance_pct": 5.0,
        "light_excluded": True,
        "desiccation_available": True,
        "sub_zero_capable": False,
    }
    record.update(kw)
    return record


class TestValidateMaterial(unittest.TestCase):
    def test_defaults_come_from_the_family(self):
        norm = validate_material(material(family="coating"))
        self.assertTrue(norm["light_sensitive"])
        self.assertFalse(norm["sub_zero_required"])

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(family="unobtainium"))

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material("   "))

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_material(["M-1"])

    def test_inverted_declared_band_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(declared_temp_min_c=20.0, declared_temp_max_c=5.0))

    def test_humidity_above_one_hundred_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(declared_rh_max_pct=120.0))

    def test_boolean_temperature_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(declared_temp_max_c=True))

    def test_non_boolean_light_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_material(material(light_sensitive="yes"))


class TestFamilyDefault(unittest.TestCase):
    def test_returned_mapping_is_a_copy(self):
        first = family_default("elastomer")
        first["rh_max_pct"] = 1.0
        self.assertAlmostEqual(FAMILY_DEFAULTS["elastomer"]["rh_max_pct"], 65.0, places=9)

    def test_family_lookup_is_case_insensitive(self):
        self.assertEqual(family_default("Elastomer"), family_default("elastomer"))

    def test_empty_family_raises(self):
        with self.assertRaises(ValueError):
            family_default("")


class TestDeriveEnvelope(unittest.TestCase):
    def test_tighter_declared_limit_governs(self):
        env = derive_envelope(material(declared_temp_max_c=20.0, declared_rh_max_pct=45.0))
        self.assertAlmostEqual(env["temp_max_c"], 20.0, places=9)
        self.assertAlmostEqual(env["rh_max_pct"], 45.0, places=9)
        self.assertEqual(env["governed_by"]["temp_max_c"], "declared")
        self.assertEqual(env["governed_by"]["rh_max_pct"], "declared")

    def test_wider_declared_limit_does_not_relax_the_family_default(self):
        env = derive_envelope(material(declared_temp_max_c=60.0, declared_rh_max_pct=95.0))
        self.assertAlmostEqual(env["temp_max_c"], FAMILY_DEFAULTS["elastomer"]["temp_max_c"],
                               places=9)
        self.assertAlmostEqual(env["rh_max_pct"], 65.0, places=9)
        self.assertEqual(env["governed_by"]["temp_max_c"], "family-default")

    def test_empty_intersection_is_refused(self):
        with self.assertRaises(ValueError):
            derive_envelope(material(family="prepreg", declared_temp_min_c=5.0))

    def test_light_protection_is_the_union_of_both_sources(self):
        env = derive_envelope(material(family="sealant", light_sensitive=True))
        self.assertTrue(env["light_protection"])

    def test_sub_zero_family_keeps_its_flag(self):
        env = derive_envelope(material(family="film-adhesive"))
        self.assertTrue(env["sub_zero"])


class TestReachableExtremes(unittest.TestCase):
    def test_tolerance_widens_the_band_on_both_sides(self):
        reach = reachable_extremes(store())
        self.assertAlmostEqual(reach["coldest_c"], 14.0, places=9)
        self.assertAlmostEqual(reach["hottest_c"], 23.0, places=9)
        self.assertAlmostEqual(reach["wettest_rh_pct"], 55.0, places=9)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            reachable_extremes(store(temp_control_tolerance_c=-0.5))

    def test_inverted_store_band_raises(self):
        with self.assertRaises(ValueError):
            validate_store(store(set_temp_min_c=30.0, set_temp_max_c=10.0))


class TestEnvelopeFindings(unittest.TestCase):
    def test_conforming_store_raises_no_finding(self):
        env = derive_envelope(material(family="sealant", light_sensitive=False))
        self.assertEqual(envelope_findings(env, store()), [])

    def test_band_edge_equality_is_not_a_breach(self):
        env = derive_envelope(material(family="sealant", light_sensitive=False,
                                       declared_temp_max_c=23.0))
        self.assertAlmostEqual(env["temp_max_c"], 23.0, places=9)
        self.assertEqual(envelope_findings(env, store()), [])

    def test_hot_store_is_a_non_mitigable_finding(self):
        env = derive_envelope(material(family="adhesive-paste"))
        found = [f for f in envelope_findings(env, store(set_temp_max_c=30.0)) if
                 f["axis"] == "temperature-high"]
        self.assertEqual(len(found), 1)
        self.assertFalse(found[0]["mitigable"])

    def test_small_humidity_overshoot_with_desiccation_is_mitigable(self):
        env = derive_envelope(material(family="prepreg", declared_rh_max_pct=50.0))
        found = [f for f in envelope_findings(env, store(sub_zero_capable=True))
                 if f["axis"] == "humidity"]
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["overshoot_pct"], 5.0, places=9)
        self.assertTrue(found[0]["mitigable"])

    def test_large_humidity_overshoot_is_not_mitigable(self):
        env = derive_envelope(material(family="prepreg", declared_rh_max_pct=30.0))
        found = [f for f in envelope_findings(env, store(sub_zero_capable=True))
                 if f["axis"] == "humidity"]
        self.assertGreater(found[0]["overshoot_pct"], DESICCATION_LIMIT_PCT)
        self.assertFalse(found[0]["mitigable"])

    def test_humidity_overshoot_without_desiccation_is_not_mitigable(self):
        env = derive_envelope(material(family="prepreg", declared_rh_max_pct=50.0))
        found = [f for f in envelope_findings(env, store(sub_zero_capable=True,
                                                         desiccation_available=False))
                 if f["axis"] == "humidity"]
        self.assertFalse(found[0]["mitigable"])

    def test_missing_light_exclusion_is_mitigable(self):
        env = derive_envelope(material(family="coating"))
        found = [f for f in envelope_findings(env, store(set_temp_max_c=22.0,
                                                         light_excluded=False))
                 if f["axis"] == "light"]
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["mitigable"])

    def test_missing_sub_zero_capability_is_not_mitigable(self):
        env = derive_envelope(material(family="film-adhesive"))
        found = [f for f in envelope_findings(env, store()) if f["axis"] == "sub-zero"]
        self.assertEqual(len(found), 1)
        self.assertFalse(found[0]["mitigable"])

    def test_bad_envelope_raises(self):
        with self.assertRaises(ValueError):
            envelope_findings({"nope": 1}, store())


class TestDisposition(unittest.TestCase):
    def test_no_findings_is_suitable(self):
        self.assertEqual(disposition_for([]), "suitable")

    def test_all_mitigable_is_conditioned(self):
        self.assertEqual(disposition_for([{"axis": "light", "mitigable": True}]),
                         "suitable-with-added-controls")

    def test_one_hard_finding_dominates(self):
        self.assertEqual(
            disposition_for([{"axis": "light", "mitigable": True},
                             {"axis": "sub-zero", "mitigable": False}]),
            "not-suitable",
        )

    def test_finding_without_mitigable_key_raises(self):
        with self.assertRaises(ValueError):
            disposition_for([{"axis": "light"}])


class TestAssessStorageConditions(unittest.TestCase):
    def test_single_conforming_material_is_suitable(self):
        report = assess_storage_conditions(
            [material("M-1", family="sealant", light_sensitive=False)], store())
        self.assertEqual(report["overall_disposition"], "suitable")
        self.assertEqual(report["not_suitable_ids"], [])

    def test_conditioned_material_names_its_added_controls(self):
        report = assess_storage_conditions(
            [material("M-2", family="coating")], store(light_excluded=False))
        self.assertEqual(report["overall_disposition"], "suitable-with-added-controls")
        self.assertEqual(report["materials"][0]["added_controls"], ["light"])

    def test_one_blocked_material_blocks_the_store(self):
        report = assess_storage_conditions(
            [material("M-1", family="sealant", light_sensitive=False),
             material("M-3", family="prepreg")], store())
        self.assertEqual(report["overall_disposition"], "not-suitable")
        self.assertEqual(report["not_suitable_ids"], ["M-3"])

    def test_duplicate_material_id_raises(self):
        with self.assertRaises(ValueError):
            assess_storage_conditions([material("M-1"), material("M-1")], store())

    def test_empty_material_list_raises(self):
        with self.assertRaises(ValueError):
            assess_storage_conditions([], store())

    def test_non_sequence_materials_raises(self):
        with self.assertRaises(ValueError):
            assess_storage_conditions(material(), store())

    def test_assess_material_reports_the_derived_envelope(self):
        result = assess_material(material("M-9", family="elastomer",
                                          declared_temp_max_c=24.0), store())
        self.assertAlmostEqual(result["envelope"]["temp_max_c"], 24.0, places=9)
        self.assertEqual(result["id"], "M-9")


if __name__ == "__main__":
    unittest.main()
