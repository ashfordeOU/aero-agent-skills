"""
Offline deterministic tests for metallic_special_pressurized_equipment_logic.
Run with: python3 test_metallic_special_pressurized_equipment.py
Must print OK.
"""

import sys
import os
import unittest

# Allow running from the scripts/ directory directly
sys.path.insert(0, os.path.dirname(__file__))

from metallic_special_pressurized_equipment_logic import (
    MSPEItem,
    assess_item,
    assess_inventory,
    pressure_margin,
    leak_before_burst_applicable,
    temperature_margin_k,
    PROOF_FACTOR,
    BURST_FACTOR,
    EquipmentType,
    HazardLevel,
)


def _compliant_battery() -> MSPEItem:
    """Return a fully compliant BATTERY item."""
    return MSPEItem(
        equipment_id="BAT-001",
        equipment_type="BATTERY",
        mawp_pa=200_000.0,
        proof_pressure_pa=320_000.0,   # 1.6× MAWP — above 1.5× requirement
        burst_pressure_pa=420_000.0,   # 2.1× MAWP — above 2.0× requirement
        operating_temp_k=293.15,       # 20 °C — within [−40, +60] °C window
        wall_thickness_mm=2.0,
        contains_hazardous=False,
        volume_liters=1.5,
    )


def _compliant_heat_pipe() -> MSPEItem:
    return MSPEItem(
        equipment_id="HP-001",
        equipment_type="HEAT_PIPE",
        mawp_pa=150_000.0,
        proof_pressure_pa=230_000.0,   # 1.53× MAWP
        burst_pressure_pa=310_000.0,   # 2.07× MAWP
        operating_temp_k=350.0,        # within [173.15, 473.15] K
        wall_thickness_mm=1.0,
        contains_hazardous=False,
        volume_liters=0.5,
    )


def _compliant_cryostat() -> MSPEItem:
    return MSPEItem(
        equipment_id="CRYO-001",
        equipment_type="CRYOSTAT",
        mawp_pa=120_000.0,
        proof_pressure_pa=185_000.0,   # 1.54× MAWP
        burst_pressure_pa=245_000.0,   # 2.04× MAWP
        operating_temp_k=77.0,         # liquid-nitrogen temperature, within [4, 120] K
        wall_thickness_mm=3.0,
        contains_hazardous=False,
        volume_liters=10.0,
    )


class TestEquipmentTypeCategorization(unittest.TestCase):
    """Verify that each accepted equipment type is correctly resolved."""

    def test_battery_type_accepted(self):
        result = assess_item(_compliant_battery())
        self.assertEqual(result.equipment_type, "BATTERY")
        self.assertTrue(result.compliant)

    def test_heat_pipe_type_accepted(self):
        result = assess_item(_compliant_heat_pipe())
        self.assertEqual(result.equipment_type, "HEAT_PIPE")
        self.assertTrue(result.compliant)

    def test_lhp_type_accepted(self):
        item = MSPEItem(
            equipment_id="LHP-001", equipment_type="LHP",
            mawp_pa=100_000.0, proof_pressure_pa=160_000.0, burst_pressure_pa=210_000.0,
            operating_temp_k=300.0, wall_thickness_mm=1.0,
            contains_hazardous=False, volume_liters=0.2,
        )
        result = assess_item(item)
        self.assertEqual(result.equipment_type, "LHP")
        self.assertTrue(result.compliant)

    def test_cpl_type_accepted(self):
        item = MSPEItem(
            equipment_id="CPL-001", equipment_type="CPL",
            mawp_pa=100_000.0, proof_pressure_pa=160_000.0, burst_pressure_pa=210_000.0,
            operating_temp_k=300.0, wall_thickness_mm=1.0,
            contains_hazardous=False, volume_liters=0.2,
        )
        result = assess_item(item)
        self.assertEqual(result.equipment_type, "CPL")
        self.assertTrue(result.compliant)

    def test_cryostat_type_accepted(self):
        result = assess_item(_compliant_cryostat())
        self.assertEqual(result.equipment_type, "CRYOSTAT")
        self.assertTrue(result.compliant)

    def test_sealed_container_type_accepted(self):
        item = MSPEItem(
            equipment_id="SC-001", equipment_type="SEALED_CONTAINER",
            mawp_pa=200_000.0, proof_pressure_pa=310_000.0, burst_pressure_pa=410_000.0,
            operating_temp_k=300.0, wall_thickness_mm=2.0,
            contains_hazardous=False, volume_liters=5.0,
        )
        result = assess_item(item)
        self.assertEqual(result.equipment_type, "SEALED_CONTAINER")
        self.assertTrue(result.compliant)

    def test_hazardous_container_type_accepted(self):
        item = MSPEItem(
            equipment_id="HC-001", equipment_type="HAZARDOUS_CONTAINER",
            mawp_pa=200_000.0, proof_pressure_pa=310_000.0, burst_pressure_pa=410_000.0,
            operating_temp_k=300.0, wall_thickness_mm=2.0,
            contains_hazardous=True, volume_liters=1.0,
        )
        result = assess_item(item)
        self.assertEqual(result.equipment_type, "HAZARDOUS_CONTAINER")
        self.assertTrue(result.compliant)

    def test_unknown_type_produces_error(self):
        item = MSPEItem(
            equipment_id="UNK-001", equipment_type="FUEL_CELL",
            mawp_pa=200_000.0, proof_pressure_pa=310_000.0, burst_pressure_pa=410_000.0,
            operating_temp_k=300.0, wall_thickness_mm=2.0,
            contains_hazardous=False, volume_liters=1.0,
        )
        result = assess_item(item)
        self.assertFalse(result.compliant)
        errors = [f for f in result.findings if f.finding_type == "error"]
        self.assertTrue(any("Unknown equipment type" in e.message for e in errors))

    def test_type_lookup_is_case_insensitive(self):
        item = _compliant_battery()
        item.equipment_type = "battery"
        result = assess_item(item)
        self.assertTrue(result.compliant)


class TestPressureFactorChecks(unittest.TestCase):

    def test_proof_below_factor_is_error(self):
        item = _compliant_battery()
        item.proof_pressure_pa = item.mawp_pa * 1.4   # below 1.5× threshold
        result = assess_item(item)
        self.assertFalse(result.compliant)
        errors = [f for f in result.findings if f.finding_type == "error"]
        self.assertTrue(any("Proof pressure" in e.message for e in errors))

    def test_burst_below_factor_is_error(self):
        item = _compliant_battery()
        item.burst_pressure_pa = item.mawp_pa * 1.9   # below 2.0× threshold
        result = assess_item(item)
        self.assertFalse(result.compliant)
        errors = [f for f in result.findings if f.finding_type == "error"]
        self.assertTrue(any("Burst pressure" in e.message for e in errors))

    def test_proof_exactly_at_factor_passes(self):
        item = _compliant_battery()
        item.proof_pressure_pa = PROOF_FACTOR * item.mawp_pa  # exactly 1.5×
        result = assess_item(item)
        proof_errors = [
            f for f in result.findings
            if f.finding_type == "error" and "Proof pressure" in f.message
        ]
        self.assertEqual(len(proof_errors), 0)

    def test_burst_exactly_at_factor_passes(self):
        item = _compliant_battery()
        item.burst_pressure_pa = BURST_FACTOR * item.mawp_pa  # exactly 2.0×
        result = assess_item(item)
        burst_errors = [
            f for f in result.findings
            if f.finding_type == "error" and "Burst pressure" in f.message
        ]
        self.assertEqual(len(burst_errors), 0)

    def test_over_test_warning_issued(self):
        item = _compliant_battery()
        item.proof_pressure_pa = item.mawp_pa * 3.5   # exceeds 3.0× warn threshold
        result = assess_item(item)
        warnings = [f for f in result.findings if f.finding_type == "warning"]
        self.assertTrue(any("over-tested" in w.message for w in warnings))


class TestTemperatureRangeChecks(unittest.TestCase):

    def test_battery_too_cold_is_error(self):
        item = _compliant_battery()
        item.operating_temp_k = 220.0   # below 233.15 K (−40 °C)
        result = assess_item(item)
        self.assertFalse(result.compliant)
        errors = [f for f in result.findings if f.finding_type == "error"]
        self.assertTrue(any("temperature" in e.message.lower() for e in errors))

    def test_battery_too_hot_is_error(self):
        item = _compliant_battery()
        item.operating_temp_k = 340.0   # above 333.15 K (+60 °C)
        result = assess_item(item)
        self.assertFalse(result.compliant)

    def test_cryostat_within_range_passes(self):
        result = assess_item(_compliant_cryostat())
        temp_errors = [
            f for f in result.findings
            if f.finding_type == "error" and "temperature" in f.message.lower()
        ]
        self.assertEqual(len(temp_errors), 0)

    def test_cryostat_above_max_is_error(self):
        item = _compliant_cryostat()
        item.operating_temp_k = 130.0   # above 120 K limit
        result = assess_item(item)
        self.assertFalse(result.compliant)


class TestWallThicknessCheck(unittest.TestCase):

    def test_wall_below_minimum_is_error(self):
        item = _compliant_battery()
        item.wall_thickness_mm = 0.3    # below 0.5 mm minimum
        result = assess_item(item)
        self.assertFalse(result.compliant)
        errors = [f for f in result.findings if f.finding_type == "error"]
        self.assertTrue(any("Wall thickness" in e.message for e in errors))

    def test_wall_at_minimum_passes(self):
        item = _compliant_battery()
        item.wall_thickness_mm = 0.5
        result = assess_item(item)
        wall_errors = [
            f for f in result.findings
            if f.finding_type == "error" and "Wall thickness" in f.message
        ]
        self.assertEqual(len(wall_errors), 0)


class TestHazardLevelDerivation(unittest.TestCase):

    def test_hazardous_high_pressure_is_critical(self):
        item = MSPEItem(
            equipment_id="HC-CRIT", equipment_type="HAZARDOUS_CONTAINER",
            mawp_pa=600_000.0,          # > 500 kPa (5 bar)
            proof_pressure_pa=950_000.0,
            burst_pressure_pa=1_250_000.0,
            operating_temp_k=300.0, wall_thickness_mm=4.0,
            contains_hazardous=True, volume_liters=2.0,
        )
        result = assess_item(item)
        self.assertEqual(result.hazard_level, HazardLevel.CRITICAL.value)

    def test_hazardous_low_pressure_is_high(self):
        item = MSPEItem(
            equipment_id="HC-HIGH", equipment_type="HAZARDOUS_CONTAINER",
            mawp_pa=200_000.0,          # ≤ 500 kPa
            proof_pressure_pa=320_000.0,
            burst_pressure_pa=420_000.0,
            operating_temp_k=300.0, wall_thickness_mm=2.0,
            contains_hazardous=True, volume_liters=1.0,
        )
        result = assess_item(item)
        self.assertEqual(result.hazard_level, HazardLevel.HIGH.value)

    def test_cryostat_is_high(self):
        result = assess_item(_compliant_cryostat())
        self.assertEqual(result.hazard_level, HazardLevel.HIGH.value)

    def test_battery_non_hazardous_is_medium(self):
        result = assess_item(_compliant_battery())
        self.assertEqual(result.hazard_level, HazardLevel.MEDIUM.value)

    def test_low_pressure_non_hazardous_sealed_is_low(self):
        item = MSPEItem(
            equipment_id="SC-LOW", equipment_type="SEALED_CONTAINER",
            mawp_pa=100_000.0,          # ≤ 300 kPa
            proof_pressure_pa=160_000.0,
            burst_pressure_pa=210_000.0,
            operating_temp_k=300.0, wall_thickness_mm=1.0,
            contains_hazardous=False, volume_liters=0.5,
        )
        result = assess_item(item)
        self.assertEqual(result.hazard_level, HazardLevel.LOW.value)


class TestInventoryAssessment(unittest.TestCase):

    def test_all_compliant_inventory_passes(self):
        items = [_compliant_battery(), _compliant_heat_pipe(), _compliant_cryostat()]
        results, overall = assess_inventory(items)
        self.assertTrue(overall)
        self.assertEqual(len(results), 3)

    def test_one_non_compliant_item_fails_overall(self):
        bad = _compliant_battery()
        bad.proof_pressure_pa = 100.0   # clearly fails proof check
        items = [_compliant_heat_pipe(), bad]
        results, overall = assess_inventory(items)
        self.assertFalse(overall)

    def test_empty_inventory_passes(self):
        results, overall = assess_inventory([])
        self.assertTrue(overall)
        self.assertEqual(results, [])


class TestPressureMarginHelper(unittest.TestCase):

    def test_positive_margin_within_limit(self):
        margin = pressure_margin(mawp_pa=200_000.0, applied_pa=150_000.0)
        self.assertAlmostEqual(margin, 200_000 / 150_000 - 1.0)
        self.assertGreater(margin, 0)

    def test_zero_margin_at_limit(self):
        margin = pressure_margin(mawp_pa=200_000.0, applied_pa=200_000.0)
        self.assertAlmostEqual(margin, 0.0)

    def test_negative_margin_exceeds_limit(self):
        margin = pressure_margin(mawp_pa=200_000.0, applied_pa=250_000.0)
        self.assertLess(margin, 0)

    def test_invalid_applied_pressure_raises(self):
        with self.assertRaises(ValueError):
            pressure_margin(200_000.0, 0.0)
        with self.assertRaises(ValueError):
            pressure_margin(200_000.0, -1.0)


class TestLeakBeforeBurstHelper(unittest.TestCase):

    def test_thick_wall_tough_material_lbb_applicable(self):
        # High toughness relative to yield → crack scale large → LBB not applicable
        # Low toughness relative to yield → crack scale small → LBB applicable
        result = leak_before_burst_applicable(
            wall_thickness_mm=5.0,
            fracture_toughness_mpa_sqrt_m=30.0,  # MPa√m
            yield_strength_mpa=400.0,
        )
        # (30/400)^2 = 0.005625; threshold = 5.0/10 = 0.5 → 0.005625 < 0.5 → True
        self.assertTrue(result)

    def test_low_toughness_thick_wall_lbb_not_applicable(self):
        # Very high toughness/yield ratio makes crack scale exceed threshold
        result = leak_before_burst_applicable(
            wall_thickness_mm=2.0,
            fracture_toughness_mpa_sqrt_m=150.0,
            yield_strength_mpa=200.0,
        )
        # (150/200)^2 = 0.5625; threshold = 2.0/10 = 0.2 → 0.5625 > 0.2 → False
        self.assertFalse(result)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            leak_before_burst_applicable(0.0, 30.0, 400.0)
        with self.assertRaises(ValueError):
            leak_before_burst_applicable(5.0, 0.0, 400.0)
        with self.assertRaises(ValueError):
            leak_before_burst_applicable(5.0, 30.0, 0.0)


class TestTemperatureMarginHelper(unittest.TestCase):

    def test_within_limit_positive_margin(self):
        margin = temperature_margin_k(operating_k=300.0, limit_k=333.15)
        self.assertAlmostEqual(margin, 33.15)

    def test_at_limit_zero_margin(self):
        margin = temperature_margin_k(operating_k=333.15, limit_k=333.15)
        self.assertAlmostEqual(margin, 0.0)

    def test_beyond_limit_negative_margin(self):
        margin = temperature_margin_k(operating_k=340.0, limit_k=333.15)
        self.assertLess(margin, 0.0)


if __name__ == "__main__":
    unittest.main()
