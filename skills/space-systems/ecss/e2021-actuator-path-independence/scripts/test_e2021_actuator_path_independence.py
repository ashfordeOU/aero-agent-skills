"""Contract test for the actuator-path-independence leaf."""

import unittest

from e2021_actuator_path_independence_logic import (
    CAUSE_SHARED_ELEMENT,
    CAUSE_SHARED_RESOURCE,
    FINDING_PATH_INCOMPLETE,
    FINDING_SHARED_ELEMENT,
    FINDING_SHARED_RESOURCE,
    PATH_NOMINAL,
    PATH_REDUNDANT,
    REQUIRED_ELEMENT_KINDS,
    assess_actuator_path_independence,
    common_cause_failures,
    independence_findings,
    missing_element_kinds,
    path_element_ids,
    path_kinds,
    path_resources,
    paths_are_independent,
    paths_surviving_element_loss,
    paths_surviving_resource_loss,
    shared_elements,
    shared_resources,
    validate_element,
    validate_path,
    validate_path_pair,
)


def element(element_id, kind, resources=()):
    return {"id": element_id, "kind": kind, "resources": list(resources)}


def path(name, suffix, bundle):
    return {
        "name": name,
        "elements": [
            element("source-%s" % suffix, "energy-source", ["bus-%s" % suffix]),
            element("arm-%s" % suffix, "arming-switch", ["bus-%s" % suffix]),
            element("fire-%s" % suffix, "firing-switch", ["bus-%s" % suffix]),
            element("harness-%s" % suffix, "harness", [bundle]),
            element("iface-%s" % suffix, "actuator-interface", [bundle]),
        ],
    }


def nominal_path():
    return path(PATH_NOMINAL, "a", "bundle-a")


def redundant_path():
    return path(PATH_REDUNDANT, "b", "bundle-b")


class TestValidateElement(unittest.TestCase):
    def test_resources_default_to_empty(self):
        record = {"id": "fire-a", "kind": "firing-switch"}
        self.assertEqual(validate_element(record)["resources"], ())

    def test_resources_are_sorted(self):
        record = element("fire-a", "firing-switch", ["z-bus", "a-bundle"])
        self.assertEqual(validate_element(record)["resources"], ("a-bundle", "z-bus"))

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_element(["fire-a"])

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_element(element(" ", "firing-switch"))

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_element(element("fire-a", "pyro-charge"))

    def test_non_sequence_resources_raises(self):
        record = element("fire-a", "firing-switch")
        record["resources"] = "bundle-a"
        with self.assertRaises(ValueError):
            validate_element(record)

    def test_repeated_resource_raises(self):
        with self.assertRaises(ValueError):
            validate_element(
                element("fire-a", "firing-switch", ["bundle-a", "bundle-a"])
            )


class TestValidatePath(unittest.TestCase):
    def test_full_path_normalizes(self):
        record = validate_path(nominal_path())
        self.assertEqual(len(record["elements"]), 5)
        self.assertEqual(record["name"], PATH_NOMINAL)

    def test_unknown_path_name_raises(self):
        broken = nominal_path()
        broken["name"] = "third-firing-path"
        with self.assertRaises(ValueError):
            validate_path(broken)

    def test_empty_element_list_raises(self):
        broken = nominal_path()
        broken["elements"] = []
        with self.assertRaises(ValueError):
            validate_path(broken)

    def test_non_sequence_elements_raises(self):
        broken = nominal_path()
        broken["elements"] = "source-a"
        with self.assertRaises(ValueError):
            validate_path(broken)

    def test_repeated_element_in_one_path_raises(self):
        broken = nominal_path()
        broken["elements"].append(element("fire-a", "firing-switch"))
        with self.assertRaises(ValueError):
            validate_path(broken)

    def test_two_paths_with_the_same_name_raise(self):
        with self.assertRaises(ValueError):
            validate_path_pair(nominal_path(), nominal_path())

    def test_pair_is_returned_in_nominal_then_redundant_order(self):
        first, second = validate_path_pair(redundant_path(), nominal_path())
        self.assertEqual((first["name"], second["name"]), (PATH_NOMINAL, PATH_REDUNDANT))


class TestPathContent(unittest.TestCase):
    def test_element_ids_are_in_declaration_order(self):
        self.assertEqual(path_element_ids(nominal_path())[0], "source-a")
        self.assertEqual(path_element_ids(nominal_path())[-1], "iface-a")

    def test_kinds_are_reported_sorted(self):
        self.assertEqual(path_kinds(nominal_path()), tuple(sorted(path_kinds(nominal_path()))))

    def test_complete_path_misses_no_required_kind(self):
        self.assertEqual(missing_element_kinds(nominal_path()), ())

    def test_path_without_a_firing_switch_is_incomplete(self):
        broken = nominal_path()
        broken["elements"] = [e for e in broken["elements"] if e["kind"] != "firing-switch"]
        self.assertEqual(missing_element_kinds(broken), ("firing-switch",))

    def test_resources_are_collected_across_elements(self):
        self.assertEqual(path_resources(nominal_path()), ("bundle-a", "bus-a"))


class TestSharing(unittest.TestCase):
    def test_separated_paths_share_nothing(self):
        self.assertEqual(shared_elements(nominal_path(), redundant_path()), ())
        self.assertEqual(shared_resources(nominal_path(), redundant_path()), {})

    def test_a_common_switch_is_a_shared_element(self):
        redundant = redundant_path()
        redundant["elements"][2] = element("fire-a", "firing-switch", ["bus-b"])
        self.assertEqual(shared_elements(nominal_path(), redundant), ("fire-a",))

    def test_a_common_bundle_is_a_shared_resource(self):
        redundant = path(PATH_REDUNDANT, "b", "bundle-a")
        shared = shared_resources(nominal_path(), redundant)
        self.assertEqual(sorted(shared), ["bundle-a"])
        self.assertEqual(shared["bundle-a"][PATH_NOMINAL], ("harness-a", "iface-a"))
        self.assertEqual(shared["bundle-a"][PATH_REDUNDANT], ("harness-b", "iface-b"))

    def test_a_common_bus_is_a_shared_resource_even_with_separate_boxes(self):
        redundant = redundant_path()
        for record in redundant["elements"]:
            if record["resources"] == ["bus-b"]:
                record["resources"] = ["bus-a"]
        self.assertEqual(sorted(shared_resources(nominal_path(), redundant)), ["bus-a"])
        self.assertEqual(shared_elements(nominal_path(), redundant), ())


class TestCommonCause(unittest.TestCase):
    def test_separated_paths_are_independent(self):
        self.assertTrue(paths_are_independent(nominal_path(), redundant_path()))
        self.assertEqual(common_cause_failures(nominal_path(), redundant_path()), [])

    def test_shared_element_is_a_common_cause(self):
        redundant = redundant_path()
        redundant["elements"][0] = element("source-a", "energy-source", ["bus-b"])
        causes = common_cause_failures(nominal_path(), redundant)
        self.assertEqual(causes[0]["cause"], CAUSE_SHARED_ELEMENT)
        self.assertEqual(causes[0]["subject"], "source-a")
        self.assertFalse(paths_are_independent(nominal_path(), redundant))

    def test_shared_resource_is_a_common_cause(self):
        redundant = path(PATH_REDUNDANT, "b", "bundle-a")
        causes = common_cause_failures(nominal_path(), redundant)
        self.assertEqual([c["cause"] for c in causes], [CAUSE_SHARED_RESOURCE])
        self.assertFalse(paths_are_independent(nominal_path(), redundant))

    def test_causes_are_sorted_by_cause_then_subject(self):
        redundant = path(PATH_REDUNDANT, "b", "bundle-a")
        redundant["elements"][0] = element("source-a", "energy-source", ["bus-b"])
        keys = [(c["cause"], c["subject"]) for c in common_cause_failures(nominal_path(), redundant)]
        self.assertEqual(keys, sorted(keys))


class TestLossCases(unittest.TestCase):
    def test_losing_a_nominal_element_leaves_the_redundant_path(self):
        self.assertEqual(
            paths_surviving_element_loss(nominal_path(), redundant_path(), "fire-a"),
            (PATH_REDUNDANT,),
        )

    def test_losing_a_shared_element_leaves_nothing(self):
        redundant = redundant_path()
        redundant["elements"][2] = element("fire-a", "firing-switch", ["bus-b"])
        self.assertEqual(
            paths_surviving_element_loss(nominal_path(), redundant, "fire-a"), ()
        )

    def test_losing_a_shared_bundle_leaves_nothing(self):
        redundant = path(PATH_REDUNDANT, "b", "bundle-a")
        self.assertEqual(
            paths_surviving_resource_loss(nominal_path(), redundant, "bundle-a"), ()
        )

    def test_losing_one_bundle_leaves_the_other_path(self):
        self.assertEqual(
            paths_surviving_resource_loss(nominal_path(), redundant_path(), "bundle-a"),
            (PATH_REDUNDANT,),
        )

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            paths_surviving_element_loss(nominal_path(), redundant_path(), "fire-c")

    def test_unknown_resource_raises(self):
        with self.assertRaises(ValueError):
            paths_surviving_resource_loss(nominal_path(), redundant_path(), "bundle-c")


class TestFindings(unittest.TestCase):
    def test_separated_paths_have_no_findings(self):
        self.assertEqual(independence_findings(nominal_path(), redundant_path()), [])

    def test_shared_element_raises_its_code(self):
        redundant = redundant_path()
        redundant["elements"][2] = element("fire-a", "firing-switch", ["bus-b"])
        codes = [f["code"] for f in independence_findings(nominal_path(), redundant)]
        self.assertIn(FINDING_SHARED_ELEMENT, codes)

    def test_shared_resource_raises_its_code(self):
        redundant = path(PATH_REDUNDANT, "b", "bundle-a")
        codes = [f["code"] for f in independence_findings(nominal_path(), redundant)]
        self.assertIn(FINDING_SHARED_RESOURCE, codes)

    def test_incomplete_path_raises_its_code(self):
        broken = nominal_path()
        broken["elements"] = [e for e in broken["elements"] if e["kind"] != "harness"]
        codes = [f["code"] for f in independence_findings(broken, redundant_path())]
        self.assertIn(FINDING_PATH_INCOMPLETE, codes)

    def test_findings_are_sorted_by_code_then_subject(self):
        redundant = path(PATH_REDUNDANT, "b", "bundle-a")
        redundant["elements"][0] = element("source-a", "energy-source", ["bus-b"])
        keys = [(f["code"], f["subject"]) for f in independence_findings(nominal_path(), redundant)]
        self.assertEqual(keys, sorted(keys))


class TestAssessment(unittest.TestCase):
    def test_separated_pair_is_compliant(self):
        report = assess_actuator_path_independence(nominal_path(), redundant_path())
        self.assertTrue(report["compliant"])
        self.assertTrue(report["independent"])
        self.assertEqual(report["common_cause_count"], 0)
        self.assertEqual(report["element_counts"][PATH_NOMINAL], 5)

    def test_shared_bundle_pair_is_not_compliant(self):
        redundant = path(PATH_REDUNDANT, "b", "bundle-a")
        report = assess_actuator_path_independence(nominal_path(), redundant)
        self.assertFalse(report["compliant"])
        self.assertFalse(report["independent"])
        self.assertEqual(report["shared_elements"], ())
        self.assertEqual(sorted(report["shared_resources"]), ["bundle-a"])

    def test_report_names_both_paths_in_order(self):
        report = assess_actuator_path_independence(redundant_path(), nominal_path())
        self.assertEqual(report["path_names"], (PATH_NOMINAL, PATH_REDUNDANT))

    def test_incomplete_path_is_reported_per_kind(self):
        broken = nominal_path()
        broken["elements"] = [e for e in broken["elements"] if e["kind"] != "energy-source"]
        report = assess_actuator_path_independence(broken, redundant_path())
        self.assertEqual(report["missing_element_kinds"][PATH_NOMINAL], ("energy-source",))
        self.assertEqual(report["missing_element_kinds"][PATH_REDUNDANT], ())
        self.assertFalse(report["compliant"])

    def test_required_kinds_are_the_four_a_path_needs(self):
        self.assertEqual(len(REQUIRED_ELEMENT_KINDS), 4)


if __name__ == "__main__":
    unittest.main()
