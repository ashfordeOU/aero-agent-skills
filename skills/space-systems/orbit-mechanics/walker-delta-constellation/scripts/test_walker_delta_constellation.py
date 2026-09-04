"""Contract test for walker_delta_constellation_logic (offline, stdlib only).

Covers the Walker-Delta t/p/f parameterization contract: ValueError
rejection of non-physical triples, the 24/3/1 worked example within
1e-9, the f=2 and 27/3/1 phase checks, the slot grid enumeration,
uniqueness of the (raan, ma) pairs, the documented identities, dict
key exactness and determinism. Run: python3 test_walker_delta_constellation.py
"""

import unittest

from walker_delta_constellation_logic import (
    validate_walker,
    walker_parameters,
    walker_slots,
    unique_slot_count,
)


class WalkerValidationTest(unittest.TestCase):
    def test_valid_triple_returns_none(self):
        self.assertIsNone(validate_walker(24, 3, 1))


    def test_t_not_divisible_raises(self):
        with self.assertRaises(ValueError):
            validate_walker(24, 5, 1)

    def test_f_equal_p_raises(self):
        with self.assertRaises(ValueError):
            validate_walker(24, 3, 3)

    def test_f_negative_raises(self):
        with self.assertRaises(ValueError):
            validate_walker(24, 3, -1)

    def test_zero_t_raises(self):
        with self.assertRaises(ValueError):
            validate_walker(0, 3, 1)

    def test_negative_t_raises(self):
        with self.assertRaises(ValueError):
            validate_walker(-24, 3, 1)

    def test_zero_p_raises(self):
        with self.assertRaises(ValueError):
            validate_walker(24, 0, 0)

    def test_negative_p_raises(self):
        with self.assertRaises(ValueError):
            validate_walker(24, -3, 0)

    def test_float_inputs_raise(self):
        with self.assertRaises(ValueError):
            validate_walker(24.0, 3, 1)
        with self.assertRaises(ValueError):
            validate_walker(24, 3.0, 1)
        with self.assertRaises(ValueError):
            validate_walker(24, 3, 1.0)


class WalkerParametersTest(unittest.TestCase):
    def test_24_3_1_exact_values(self):
        p = walker_parameters(24, 3, 1)
        self.assertEqual(p["satellites_per_plane"], 8)
        self.assertAlmostEqual(p["raan_spacing_deg"], 120.0, places=9)
        self.assertAlmostEqual(p["mean_anomaly_spacing_deg"], 45.0, places=9)
        self.assertAlmostEqual(p["inter_plane_phase_deg"], 15.0, places=9)

    def test_dict_keys_exact(self):
        self.assertEqual(
            set(walker_parameters(24, 3, 1).keys()),
            {"satellites_per_plane", "raan_spacing_deg",
             "mean_anomaly_spacing_deg", "inter_plane_phase_deg"},
        )

    def test_f2_phase_30(self):
        self.assertAlmostEqual(
            walker_parameters(24, 3, 2)["inter_plane_phase_deg"], 30.0, places=9
        )

    def test_27_3_1_phase_13_333(self):
        self.assertAlmostEqual(
            walker_parameters(27, 3, 1)["inter_plane_phase_deg"],
            13.333, places=3,
        )


    def test_single_plane_f0(self):
        p = walker_parameters(5, 1, 0)
        self.assertEqual(p["satellites_per_plane"], 5)
        self.assertAlmostEqual(p["raan_spacing_deg"], 360.0, places=9)
        self.assertAlmostEqual(p["mean_anomaly_spacing_deg"], 72.0, places=9)
        self.assertAlmostEqual(p["inter_plane_phase_deg"], 0.0, places=9)

    def test_satellites_per_plane_times_p_identity(self):
        for t, p, f in [(24, 3, 1), (27, 3, 2), (12, 4, 3), (50, 5, 0)]:
            par = walker_parameters(t, p, f)
            self.assertEqual(par["satellites_per_plane"] * p, t)

    def test_raan_spacing_times_p_identity(self):
        for t, p, f in [(24, 3, 1), (12, 4, 3), (50, 5, 0)]:
            par = walker_parameters(t, p, f)
            self.assertAlmostEqual(par["raan_spacing_deg"] * p, 360.0, places=9)

    def test_ma_spacing_times_s_identity(self):
        for t, p, f in [(24, 3, 1), (27, 3, 2), (50, 5, 0)]:
            par = walker_parameters(t, p, f)
            s = par["satellites_per_plane"]
            self.assertAlmostEqual(
                par["mean_anomaly_spacing_deg"] * s, 360.0, places=9
            )

    def test_phase_equals_f_360_over_t(self):
        for t, p, f in [(24, 3, 1), (27, 3, 2), (12, 4, 3)]:
            par = walker_parameters(t, p, f)
            self.assertAlmostEqual(
                par["inter_plane_phase_deg"], f * 360.0 / t, places=9
            )

    def test_invalid_triple_raises(self):
        for bad in [(24, 5, 1), (24, 3, 3), (0, 3, 1), (24, 3, -1)]:
            with self.assertRaises(ValueError):
                walker_parameters(*bad)


class WalkerSlotsTest(unittest.TestCase):
    def test_slot_list_length_equals_t(self):
        self.assertEqual(len(walker_slots(24, 3, 1)), 24)
        self.assertEqual(len(walker_slots(27, 3, 2)), 27)
        self.assertEqual(len(walker_slots(50, 5, 0)), 50)

    def test_entries_per_plane_equals_s(self):
        slots = walker_slots(24, 3, 1)
        per_plane = {}
        for s in slots:
            per_plane[s["plane"]] = per_plane.get(s["plane"], 0) + 1
        self.assertEqual(per_plane, {0: 8, 1: 8, 2: 8})

    def test_plane0_slot0_ma_zero(self):
        self.assertEqual(walker_slots(24, 3, 1)[0]["mean_anomaly_deg"], 0.0)

    def test_plane1_slot0_ma_15(self):
        slot = walker_slots(24, 3, 1)[8]
        self.assertEqual(slot["plane"], 1)
        self.assertEqual(slot["slot"], 0)
        self.assertAlmostEqual(slot["mean_anomaly_deg"], 15.0, places=9)

    def test_plane2_slot0_ma_30(self):
        slot = walker_slots(24, 3, 1)[16]
        self.assertEqual(slot["plane"], 2)
        self.assertAlmostEqual(slot["mean_anomaly_deg"], 30.0, places=9)

    def test_raan_values_follow_plane_index(self):
        slots = walker_slots(24, 3, 1)
        for j in range(3):
            first = next(s for s in slots if s["plane"] == j and s["slot"] == 0)
            self.assertAlmostEqual(first["raan_deg"], j * 120.0, places=9)

    def test_within_plane_ma_spacing(self):
        slots = walker_slots(24, 3, 1)
        plane0 = sorted((s for s in slots if s["plane"] == 0),
                        key=lambda s: s["slot"])
        for k in range(1, len(plane0)):
            delta = plane0[k]["mean_anomaly_deg"] - plane0[k - 1]["mean_anomaly_deg"]
            self.assertAlmostEqual(delta, 45.0, places=9)

    def test_ma_stays_in_0_360_band(self):
        for s in walker_slots(27, 3, 2):
            self.assertGreaterEqual(s["mean_anomaly_deg"], 0.0)
            self.assertLess(s["mean_anomaly_deg"], 360.0)

    def test_slot_dict_keys_exact(self):
        keys = set(walker_slots(24, 3, 1)[0].keys())
        self.assertEqual(keys, {"plane", "slot", "raan_deg", "mean_anomaly_deg"})

    def test_ordering_plane_major(self):
        slots = walker_slots(24, 3, 1)
        for idx, s in enumerate(slots):
            self.assertEqual(s["plane"], idx // 8)
            self.assertEqual(s["slot"], idx % 8)

    def test_determinism_two_calls_identical(self):
        self.assertEqual(walker_slots(24, 3, 1), walker_slots(24, 3, 1))

    def test_single_satellite_slot(self):
        slots = walker_slots(1, 1, 0)
        self.assertEqual(len(slots), 1)
        self.assertAlmostEqual(slots[0]["raan_deg"], 0.0, places=9)
        self.assertAlmostEqual(slots[0]["mean_anomaly_deg"], 0.0, places=9)

    def test_invalid_triple_raises(self):
        for bad in [(24, 5, 1), (24, 3, 3), (0, 3, 1), (24, 3, -1)]:
            with self.assertRaises(ValueError):
                walker_slots(*bad)


class WalkerUniquenessTest(unittest.TestCase):

    def test_unique_count_equals_t_across_configs(self):
        for t, p, f in [(27, 3, 1), (27, 3, 2), (12, 4, 3), (50, 5, 0),
                        (24, 3, 0), (1, 1, 0)]:
            self.assertEqual(unique_slot_count(t, p, f), t)


    def test_invalid_triple_raises(self):
        for bad in [(24, 5, 1), (24, 3, 3), (0, 3, 1)]:
            with self.assertRaises(ValueError):
                unique_slot_count(*bad)


class WalkerClosedFormTest(unittest.TestCase):
    def test_first_slot_ma_carries_phase(self):
        for f in range(3):
            t, p = 24, 3
            slots = walker_slots(t, p, f)
            for j in range(p):
                first = next(s for s in slots if s["plane"] == j and s["slot"] == 0)
                self.assertAlmostEqual(
                    first["mean_anomaly_deg"], j * f * 360.0 / t, places=9
                )


if __name__ == "__main__":
    unittest.main()
