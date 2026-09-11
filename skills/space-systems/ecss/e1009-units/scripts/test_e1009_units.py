import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1009_units_logic import (
    check_unit,
    is_compliant,
    get_si_unit,
    get_stated_exceptions,
    validate_parameter_list,
    list_supported_quantities,
    UnitStatus,
)


class TestCheckUnitDistance(unittest.TestCase):
    def test_distance_si_meter(self):
        result = check_unit("distance", "m")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_distance_stated_exception_km(self):
        result = check_unit("distance", "km")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_distance_noncompliant_feet(self):
        result = check_unit("distance", "ft")
        self.assertEqual(result["status"], UnitStatus.NON_COMPLIANT)
        self.assertIn("m", result["expected_si"])

    def test_distance_noncompliant_miles(self):
        result = check_unit("distance", "mi")
        self.assertEqual(result["status"], UnitStatus.NON_COMPLIANT)


class TestCheckUnitAngle(unittest.TestCase):
    def test_angle_si_radians(self):
        result = check_unit("angle", "rad")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_angle_stated_exception_degrees(self):
        result = check_unit("angle", "deg")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_angle_stated_exception_arcsec(self):
        result = check_unit("angle", "arcsec")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_angle_stated_exception_arcmin(self):
        result = check_unit("angle", "arcmin")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_angle_noncompliant_gradians(self):
        result = check_unit("angle", "grad")
        self.assertEqual(result["status"], UnitStatus.NON_COMPLIANT)
        self.assertEqual(result["expected_si"], "rad")
        self.assertIn("deg", result["stated_exceptions"])


class TestCheckUnitTime(unittest.TestCase):
    def test_time_si_seconds(self):
        result = check_unit("time", "s")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_time_stated_exception_jd(self):
        result = check_unit("time", "JD")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_time_stated_exception_mjd(self):
        result = check_unit("time", "MJD")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_time_stated_exception_day(self):
        result = check_unit("time", "day")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_time_stated_exception_hour(self):
        result = check_unit("time", "h")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_time_noncompliant_milliseconds_label(self):
        result = check_unit("time", "ms")
        self.assertEqual(result["status"], UnitStatus.NON_COMPLIANT)


class TestCheckUnitVelocityAndAngularRate(unittest.TestCase):
    def test_velocity_si(self):
        result = check_unit("velocity", "m/s")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_velocity_stated_exception_km_s(self):
        result = check_unit("velocity", "km/s")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_velocity_noncompliant(self):
        result = check_unit("velocity", "mph")
        self.assertEqual(result["status"], UnitStatus.NON_COMPLIANT)

    def test_angular_rate_si(self):
        result = check_unit("angular_rate", "rad/s")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_angular_rate_stated_exception_deg_s(self):
        result = check_unit("angular_rate", "deg/s")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_angular_rate_stated_exception_rpm(self):
        result = check_unit("angular_rate", "rpm")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)


class TestCheckUnitOtherQuantities(unittest.TestCase):
    def test_temperature_si_kelvin(self):
        result = check_unit("temperature", "K")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_temperature_stated_exception_celsius(self):
        result = check_unit("temperature", "degC")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_temperature_noncompliant_fahrenheit(self):
        result = check_unit("temperature", "degF")
        self.assertEqual(result["status"], UnitStatus.NON_COMPLIANT)

    def test_mass_si_kg(self):
        result = check_unit("mass", "kg")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_force_si_newton(self):
        result = check_unit("force", "N")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_force_noncompliant_lbf(self):
        result = check_unit("force", "lbf")
        self.assertEqual(result["status"], UnitStatus.NON_COMPLIANT)

    def test_pressure_si_pa(self):
        result = check_unit("pressure", "Pa")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_pressure_stated_exception_kpa(self):
        result = check_unit("pressure", "kPa")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_frequency_si_hz(self):
        result = check_unit("frequency", "Hz")
        self.assertEqual(result["status"], UnitStatus.SI)

    def test_frequency_stated_exception_ghz(self):
        result = check_unit("frequency", "GHz")
        self.assertEqual(result["status"], UnitStatus.STATED_EXCEPTION)

    def test_acceleration_si(self):
        result = check_unit("acceleration", "m/s2")
        self.assertEqual(result["status"], UnitStatus.SI)


class TestUnknownQuantityType(unittest.TestCase):
    def test_unknown_quantity_type_returns_unknown_status(self):
        result = check_unit("luminosity", "cd")
        self.assertEqual(result["status"], UnitStatus.UNKNOWN_QUANTITY)
        self.assertIsNone(result["expected_si"])

    def test_unknown_quantity_message_contains_type(self):
        result = check_unit("warp_factor", "warp")
        self.assertIn("warp_factor", result["message"])


class TestIsCompliant(unittest.TestCase):
    def test_si_unit_is_compliant(self):
        self.assertTrue(is_compliant("distance", "m"))

    def test_stated_exception_is_compliant(self):
        self.assertTrue(is_compliant("angle", "deg"))

    def test_noncompliant_unit_is_not_compliant(self):
        self.assertFalse(is_compliant("angle", "grad"))

    def test_unknown_quantity_is_not_compliant(self):
        self.assertFalse(is_compliant("warp_factor", "warp"))


class TestGetSiUnit(unittest.TestCase):
    def test_get_si_unit_mass(self):
        self.assertEqual(get_si_unit("mass"), "kg")

    def test_get_si_unit_force(self):
        self.assertEqual(get_si_unit("force"), "N")

    def test_get_si_unit_unknown_raises(self):
        with self.assertRaises(KeyError):
            get_si_unit("warp_factor")


class TestGetStatedExceptions(unittest.TestCase):
    def test_angle_has_degrees_in_exceptions(self):
        exceptions = get_stated_exceptions("angle")
        self.assertIn("deg", exceptions)
        self.assertIsInstance(exceptions, set)

    def test_force_has_empty_exceptions(self):
        self.assertEqual(get_stated_exceptions("force"), set())

    def test_unknown_quantity_raises(self):
        with self.assertRaises(KeyError):
            get_stated_exceptions("warp_factor")


class TestValidateParameterList(unittest.TestCase):
    def test_all_si_is_compliant(self):
        params = [
            {"quantity_type": "distance", "unit": "m"},
            {"quantity_type": "angle", "unit": "rad"},
            {"quantity_type": "time", "unit": "s"},
        ]
        summary = validate_parameter_list(params)
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["counts"][UnitStatus.SI], 3)

    def test_mixed_si_and_exceptions_is_compliant(self):
        params = [
            {"quantity_type": "distance", "unit": "m"},
            {"quantity_type": "angle", "unit": "deg"},
            {"quantity_type": "time", "unit": "MJD"},
        ]
        summary = validate_parameter_list(params)
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["counts"][UnitStatus.STATED_EXCEPTION], 2)

    def test_one_violation_makes_not_compliant(self):
        params = [
            {"quantity_type": "distance", "unit": "ft"},
            {"quantity_type": "angle", "unit": "rad"},
        ]
        summary = validate_parameter_list(params)
        self.assertFalse(summary["all_compliant"])
        self.assertEqual(summary["counts"][UnitStatus.NON_COMPLIANT], 1)

    def test_unknown_quantity_makes_not_compliant(self):
        params = [
            {"quantity_type": "warp_factor", "unit": "warp"},
        ]
        summary = validate_parameter_list(params)
        self.assertFalse(summary["all_compliant"])
        self.assertEqual(summary["counts"][UnitStatus.UNKNOWN_QUANTITY], 1)

    def test_empty_list_is_compliant(self):
        summary = validate_parameter_list([])
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["total"], 0)

    def test_invalid_entry_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_parameter_list([{"quantity_type": "distance"}])

    def test_non_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_parameter_list("not a list")

    def test_findings_count_matches_total(self):
        params = [
            {"quantity_type": "mass", "unit": "kg"},
            {"quantity_type": "force", "unit": "N"},
            {"quantity_type": "temperature", "unit": "degF"},
        ]
        summary = validate_parameter_list(params)
        self.assertEqual(len(summary["findings"]), summary["total"])


class TestListSupportedQuantities(unittest.TestCase):
    def test_returns_list(self):
        result = list_supported_quantities()
        self.assertIsInstance(result, list)

    def test_contains_expected_types(self):
        result = list_supported_quantities()
        for qt in ("distance", "angle", "time", "velocity", "mass",
                   "force", "pressure", "temperature", "frequency",
                   "acceleration", "angular_rate"):
            self.assertIn(qt, result)

    def test_is_sorted(self):
        result = list_supported_quantities()
        self.assertEqual(result, sorted(result))

    def test_at_least_eleven_types(self):
        self.assertGreaterEqual(len(list_supported_quantities()), 11)


class TestInputValidation(unittest.TestCase):
    def test_empty_quantity_type_raises(self):
        with self.assertRaises(ValueError):
            check_unit("", "m")

    def test_empty_unit_raises(self):
        with self.assertRaises(ValueError):
            check_unit("distance", "")

    def test_none_quantity_type_raises(self):
        with self.assertRaises((ValueError, TypeError)):
            check_unit(None, "m")

    def test_none_unit_raises(self):
        with self.assertRaises((ValueError, TypeError)):
            check_unit("distance", None)


class TestResultStructure(unittest.TestCase):
    def test_verdict_contains_all_keys(self):
        result = check_unit("angle", "deg")
        for key in ("status", "quantity_type", "unit", "expected_si",
                    "stated_exceptions", "message"):
            self.assertIn(key, result)

    def test_stated_exceptions_field_is_sorted_list(self):
        result = check_unit("angle", "rad")
        self.assertIsInstance(result["stated_exceptions"], list)
        self.assertEqual(result["stated_exceptions"],
                         sorted(result["stated_exceptions"]))

    def test_noncompliant_message_contains_expected_si(self):
        result = check_unit("distance", "ft")
        self.assertIn("m", result["message"])


if __name__ == "__main__":
    unittest.main()
