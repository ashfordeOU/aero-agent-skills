"""
Gate 3 contract test — e1009-time (ECSS E-ST-10C §5.4.4).
stdlib unittest only; deterministic, offline. Run: python3 test_e1009_time.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1009_time_logic import (
    validate_time_scale,
    validate_epoch,
    validate_frame,
    check_frame_time_scale,
    select_time_scale_for_frame,
    get_epoch_jd,
    get_epoch_time_scale,
    jd_to_mjd,
    mjd_to_jd,
    days_from_j2000,
    centuries_from_j2000,
    tai_to_tt,
    tt_to_tai,
    tai_to_gps,
    gps_to_tai,
    tai_to_utc,
    utc_to_tai,
    describe_time_scale,
    TimeScaleError,
    EpochError,
    FrameTimeScaleError,
    MJD_OFFSET,
    VALID_TIME_SCALES,
    FRAME_RECOMMENDED_SCALES,
    STANDARD_EPOCHS,
)


class TestValidateTimeScale(unittest.TestCase):

    def test_all_valid_scales_accepted(self):
        for s in ("TAI", "UTC", "UT1", "TT", "TDB", "TCB", "TCG", "GPS"):
            with self.subTest(scale=s):
                self.assertEqual(validate_time_scale(s), s)

    def test_lowercase_input_normalized(self):
        self.assertEqual(validate_time_scale("tai"), "TAI")
        self.assertEqual(validate_time_scale("utc"), "UTC")
        self.assertEqual(validate_time_scale("tt"), "TT")

    def test_mixed_case_normalized(self):
        self.assertEqual(validate_time_scale("TdB"), "TDB")

    def test_whitespace_stripped(self):
        self.assertEqual(validate_time_scale("  GPS  "), "GPS")

    def test_unknown_scale_raises_time_scale_error(self):
        with self.assertRaises(TimeScaleError):
            validate_time_scale("XYZ")

    def test_empty_string_raises_time_scale_error(self):
        with self.assertRaises(TimeScaleError):
            validate_time_scale("")

    def test_numeric_string_raises_time_scale_error(self):
        with self.assertRaises(TimeScaleError):
            validate_time_scale("1234")


class TestValidateEpoch(unittest.TestCase):

    def test_j2000_recognized_and_jd_correct(self):
        ep = validate_epoch("J2000.0")
        self.assertAlmostEqual(ep.jd, 2451545.0, places=3)

    def test_j2000_defined_in_tt(self):
        ep = validate_epoch("J2000.0")
        self.assertEqual(ep.time_scale, "TT")

    def test_j1950_recognized(self):
        ep = validate_epoch("J1950.0")
        self.assertAlmostEqual(ep.jd, 2433282.5, places=3)

    def test_b1950_recognized(self):
        ep = validate_epoch("B1950.0")
        self.assertGreater(ep.jd, 2433280.0)

    def test_mjd0_epoch_recognized(self):
        ep = validate_epoch("MJD0")
        self.assertAlmostEqual(ep.jd, MJD_OFFSET, places=3)

    def test_unknown_epoch_raises_epoch_error(self):
        with self.assertRaises(EpochError):
            validate_epoch("J3000.0")

    def test_empty_epoch_raises_epoch_error(self):
        with self.assertRaises(EpochError):
            validate_epoch("")


class TestJdMjdConversion(unittest.TestCase):

    def test_jd_to_mjd_j2000(self):
        # J2000.0 is JD 2451545.0; MJD = JD − 2400000.5 = 51544.5
        self.assertAlmostEqual(jd_to_mjd(2451545.0), 51544.5, places=6)

    def test_mjd_to_jd_j2000(self):
        self.assertAlmostEqual(mjd_to_jd(51544.5), 2451545.0, places=6)

    def test_jd_mjd_roundtrip(self):
        jd = 2459000.0
        self.assertAlmostEqual(mjd_to_jd(jd_to_mjd(jd)), jd, places=9)

    def test_mjd_offset_value(self):
        self.assertAlmostEqual(MJD_OFFSET, 2400000.5, places=6)


class TestJ2000Offsets(unittest.TestCase):

    def test_days_at_j2000_epoch_is_zero(self):
        self.assertAlmostEqual(days_from_j2000(2451545.0), 0.0, places=9)

    def test_days_one_julian_year_after_j2000(self):
        self.assertAlmostEqual(days_from_j2000(2451545.0 + 365.25), 365.25, places=9)

    def test_days_before_j2000_is_negative(self):
        self.assertLess(days_from_j2000(2451544.0), 0.0)

    def test_centuries_one_century_after_j2000(self):
        jd = 2451545.0 + 36525.0
        self.assertAlmostEqual(centuries_from_j2000(jd), 1.0, places=9)

    def test_centuries_at_j2000_is_zero(self):
        self.assertAlmostEqual(centuries_from_j2000(2451545.0), 0.0, places=9)


class TestTAITTConversion(unittest.TestCase):

    def test_tai_to_tt_adds_32184_ms(self):
        self.assertAlmostEqual(tai_to_tt(0.0), 32.184, places=9)

    def test_tai_to_tt_known_value(self):
        self.assertAlmostEqual(tai_to_tt(1000.0), 1032.184, places=9)

    def test_tt_to_tai_subtracts_offset(self):
        self.assertAlmostEqual(tt_to_tai(32.184), 0.0, places=9)

    def test_tai_tt_roundtrip(self):
        tai = 123456789.0
        self.assertAlmostEqual(tt_to_tai(tai_to_tt(tai)), tai, places=9)


class TestGPSConversion(unittest.TestCase):

    def test_tai_to_gps_offset_is_19_seconds(self):
        # GPS = TAI − 19 s
        self.assertAlmostEqual(tai_to_gps(19.0), 0.0, places=9)

    def test_tai_to_gps_known_value(self):
        self.assertAlmostEqual(tai_to_gps(1000.0), 981.0, places=9)

    def test_gps_to_tai_known_value(self):
        self.assertAlmostEqual(gps_to_tai(0.0), 19.0, places=9)

    def test_gps_tai_roundtrip(self):
        gps = 987654.321
        self.assertAlmostEqual(gps_to_tai(tai_to_gps(gps)), gps, places=9)


class TestTAIUTCConversion(unittest.TestCase):

    def test_tai_to_utc_37_leap_seconds(self):
        # TAI − 37 = UTC when 37 leap seconds have been introduced
        utc = tai_to_utc(1000037.0, 37)
        self.assertAlmostEqual(utc, 1000000.0, places=9)

    def test_utc_to_tai_37_leap_seconds(self):
        tai = utc_to_tai(1000000.0, 37)
        self.assertAlmostEqual(tai, 1000037.0, places=9)

    def test_tai_utc_roundtrip(self):
        utc = 500000.0
        leaps = 37
        self.assertAlmostEqual(tai_to_utc(utc_to_tai(utc, leaps), leaps), utc, places=9)

    def test_zero_leap_seconds_identity(self):
        self.assertAlmostEqual(tai_to_utc(1000.0, 0), 1000.0, places=9)

    def test_negative_leap_seconds_raises(self):
        with self.assertRaises(ValueError):
            tai_to_utc(1000.0, -1)

    def test_float_leap_seconds_raises(self):
        with self.assertRaises(ValueError):
            tai_to_utc(1000.0, 37.0)

    def test_bool_leap_seconds_raises(self):
        # bool is a subclass of int in Python; we explicitly reject it
        with self.assertRaises(ValueError):
            tai_to_utc(1000.0, True)


class TestFrameTimeScaleCompatibility(unittest.TestCase):

    def test_eci_with_tt_is_compatible(self):
        self.assertTrue(check_frame_time_scale("ECI", "TT"))

    def test_eci_with_tai_is_compatible(self):
        self.assertTrue(check_frame_time_scale("ECI", "TAI"))

    def test_eci_with_utc_raises_frame_time_scale_error(self):
        with self.assertRaises(FrameTimeScaleError):
            check_frame_time_scale("ECI", "UTC")

    def test_ecef_with_utc_is_compatible(self):
        self.assertTrue(check_frame_time_scale("ECEF", "UTC"))

    def test_ecef_with_ut1_is_compatible(self):
        self.assertTrue(check_frame_time_scale("ECEF", "UT1"))

    def test_ecef_with_tdb_raises_frame_time_scale_error(self):
        with self.assertRaises(FrameTimeScaleError):
            check_frame_time_scale("ECEF", "TDB")

    def test_bcrs_with_tdb_is_compatible(self):
        self.assertTrue(check_frame_time_scale("BCRS", "TDB"))

    def test_bcrs_with_tcb_is_compatible(self):
        self.assertTrue(check_frame_time_scale("BCRS", "TCB"))

    def test_bcrs_with_tai_raises_frame_time_scale_error(self):
        with self.assertRaises(FrameTimeScaleError):
            check_frame_time_scale("BCRS", "TAI")

    def test_gcrs_with_tcg_is_compatible(self):
        self.assertTrue(check_frame_time_scale("GCRS", "TCG"))

    def test_unknown_frame_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_frame_time_scale("UNKNOWN_FRAME", "TAI")

    def test_case_insensitive_frame_and_scale(self):
        self.assertTrue(check_frame_time_scale("eci", "tt"))
        self.assertTrue(check_frame_time_scale("bcrs", "tdb"))


class TestSelectTimeScaleForFrame(unittest.TestCase):

    def test_eci_returns_tai_and_tt(self):
        scales = select_time_scale_for_frame("ECI")
        self.assertIn("TAI", scales)
        self.assertIn("TT", scales)

    def test_bcrs_returns_tdb_and_tcb(self):
        scales = select_time_scale_for_frame("BCRS")
        self.assertIn("TDB", scales)
        self.assertIn("TCB", scales)

    def test_ecef_returns_utc_and_ut1(self):
        scales = select_time_scale_for_frame("ECEF")
        self.assertIn("UTC", scales)
        self.assertIn("UT1", scales)

    def test_result_is_sorted(self):
        scales = select_time_scale_for_frame("RTN")
        self.assertEqual(scales, sorted(scales))

    def test_unknown_frame_raises(self):
        with self.assertRaises(ValueError):
            select_time_scale_for_frame("NOPE")


class TestGetEpochHelpers(unittest.TestCase):

    def test_get_epoch_jd_j2000(self):
        self.assertAlmostEqual(get_epoch_jd("J2000.0"), 2451545.0, places=3)

    def test_get_epoch_time_scale_j2000(self):
        self.assertEqual(get_epoch_time_scale("J2000.0"), "TT")

    def test_get_epoch_jd_invalid_raises(self):
        with self.assertRaises(EpochError):
            get_epoch_jd("J9999.0")

    def test_j1900_jd_less_than_j1950_jd(self):
        self.assertLess(get_epoch_jd("J1900.0"), get_epoch_jd("J1950.0"))

    def test_j1950_jd_less_than_j2000_jd(self):
        self.assertLess(get_epoch_jd("J1950.0"), get_epoch_jd("J2000.0"))


class TestDescribeTimeScale(unittest.TestCase):

    def test_tai_description_is_non_empty(self):
        desc = describe_time_scale("TAI")
        self.assertGreater(len(desc), 20)

    def test_utc_description_is_non_empty(self):
        desc = describe_time_scale("UTC")
        self.assertGreater(len(desc), 20)

    def test_all_valid_scales_have_descriptions(self):
        for s in VALID_TIME_SCALES:
            with self.subTest(scale=s):
                desc = describe_time_scale(s)
                self.assertIsInstance(desc, str)
                self.assertGreater(len(desc), 10)

    def test_invalid_scale_raises_time_scale_error(self):
        with self.assertRaises(TimeScaleError):
            describe_time_scale("UNKNOWN")


class TestRegistryCompleteness(unittest.TestCase):

    def test_all_frames_have_at_least_one_scale(self):
        for frame, scales in FRAME_RECOMMENDED_SCALES.items():
            with self.subTest(frame=frame):
                self.assertGreater(len(scales), 0)

    def test_all_recommended_scales_are_in_valid_set(self):
        for frame, scales in FRAME_RECOMMENDED_SCALES.items():
            for s in scales:
                with self.subTest(frame=frame, scale=s):
                    self.assertIn(s, VALID_TIME_SCALES)

    def test_standard_epochs_have_positive_jd(self):
        for name, epoch in STANDARD_EPOCHS.items():
            with self.subTest(epoch=name):
                self.assertGreater(epoch.jd, 0.0)

    def test_standard_epochs_time_scales_are_valid(self):
        for name, epoch in STANDARD_EPOCHS.items():
            with self.subTest(epoch=name):
                self.assertIn(epoch.time_scale, VALID_TIME_SCALES)


if __name__ == "__main__":
    unittest.main()
