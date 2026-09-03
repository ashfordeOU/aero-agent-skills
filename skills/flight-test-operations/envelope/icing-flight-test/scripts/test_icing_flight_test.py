"""Contract tests for icing_flight_test_logic (offline, stdlib only).

Covers the wave-26 icing-flight-test spec worked examples: continuous
maximum and intermittent maximum envelope verdicts and margins, SLD
exclusion, encounter severity with the duration step, natural icing
search screening, the artificial ice shape matrix check, effectiveness
test point pairing, and ValueError rejection of non-physical inputs.
"""

import math
import unittest

import icing_flight_test_logic as icing


class LwcLimitSegmentTests(unittest.TestCase):
    """Piecewise linear LWC limit segments at the anchor temperatures."""

    def test_cm_limit_at_anchor_n10_exact(self):
        self.assertEqual(icing.cm_lwc_limit(-10.0), 0.44)

    def test_cm_limit_at_0_and_n30_anchors(self):
        self.assertEqual(icing.cm_lwc_limit(0.0), 0.20)
        self.assertEqual(icing.cm_lwc_limit(-30.0), 0.15)

    def test_cm_limit_clamps_outside_temperature_band(self):
        self.assertEqual(icing.cm_lwc_limit(-60.0), 0.15)
        self.assertEqual(icing.cm_lwc_limit(40.0), 0.20)

    def test_cm_limit_linear_segment_interiors(self):
        self.assertAlmostEqual(icing.cm_lwc_limit(-5.0), 0.32, places=6)
        self.assertAlmostEqual(icing.cm_lwc_limit(-20.0), 0.295, places=6)

    def test_im_limit_anchors(self):
        self.assertEqual(icing.im_lwc_limit(-10.0), 1.40)
        self.assertEqual(icing.im_lwc_limit(0.0), 0.65)
        self.assertEqual(icing.im_lwc_limit(-30.0), 0.35)

    def test_im_limit_linear_segment_interiors(self):
        self.assertAlmostEqual(icing.im_lwc_limit(-5.0), 1.025, places=6)
        self.assertAlmostEqual(icing.im_lwc_limit(-20.0), 0.875, places=6)

    def test_lwc_limit_nonfinite_raises(self):
        with self.assertRaises(ValueError):
            icing.cm_lwc_limit(float("nan"))
        with self.assertRaises(ValueError):
            icing.im_lwc_limit(float("inf"))


class EnvelopeVerdictTests(unittest.TestCase):
    """Envelope verdict worked examples from the leaf spec."""

    def test_continuous_max_worked_example(self):
        verdict = icing.envelope_verdict(0.30, 20.0, -10.0)
        self.assertTrue(verdict["in_envelope"])
        self.assertEqual(verdict["regime"], "continuous-max")
        self.assertAlmostEqual(verdict["margin"], 0.14, places=6)

    def test_intermittent_max_worked_example(self):
        verdict = icing.envelope_verdict(1.0, 25.0, -10.0)
        self.assertTrue(verdict["in_envelope"])
        self.assertEqual(verdict["regime"], "intermittent-max")
        self.assertAlmostEqual(verdict["margin"], 0.4, places=6)

    def test_outside_above_both_limits(self):
        verdict = icing.envelope_verdict(1.6, 25.0, -10.0)
        self.assertFalse(verdict["in_envelope"])
        self.assertEqual(verdict["regime"], "outside")
        self.assertAlmostEqual(verdict["margin"], -0.2, places=6)
        self.assertTrue(any("intermittent" in r for r in verdict["reasons"]))

    def test_sld_exclusion_worked_example(self):
        verdict = icing.envelope_verdict(0.30, 60.0, -5.0)
        self.assertFalse(verdict["in_envelope"])
        self.assertEqual(verdict["regime"], "outside")
        self.assertIn(
            "supercooled-large-droplet conditions exceed the appendix C envelope",
            verdict["reasons"],
        )

    def test_mvd_band_and_sld_threshold_boundaries(self):
        self.assertEqual(
            icing.envelope_verdict(0.3, icing.CM_MVD_MAX, -10.0)["regime"],
            "continuous-max",
        )
        self.assertEqual(
            icing.envelope_verdict(0.3, icing.CM_MVD_MAX + 1.0, -10.0)["regime"],
            "intermittent-max",
        )
        self.assertEqual(
            icing.envelope_verdict(0.3, icing.IM_MVD_MIN - 1.0, -10.0)["regime"],
            "outside",
        )
        self.assertEqual(
            icing.envelope_verdict(0.3, icing.SLD_MVD_MIN, -10.0)["regime"],
            "intermittent-max",
        )
        self.assertEqual(
            icing.envelope_verdict(0.3, icing.SLD_MVD_MIN + 0.1, -10.0)["regime"],
            "outside",
        )

    def test_verdict_valueerror_negative_and_nonfinite(self):
        for bad_lwc in (-0.1, float("nan")):
            with self.assertRaises(ValueError):
                icing.envelope_verdict(bad_lwc, 20.0, -10.0)
        with self.assertRaises(ValueError):
            icing.envelope_verdict(0.3, -5.0, -10.0)
        with self.assertRaises(ValueError):
            icing.envelope_verdict(0.3, 20.0, float("inf"))


class EncounterSeverityTests(unittest.TestCase):
    """Severity index and label with the duration step."""

    def test_ratio_half_is_light(self):
        index, label = icing.encounter_severity(0.22, -10.0, 30.0)
        self.assertEqual((index, label), (1, "light"))

    def test_duration_step_45_minutes_to_moderate(self):
        index, label = icing.encounter_severity(0.22, -10.0, 45.0)
        self.assertEqual((index, label), (2, "moderate"))

    def test_trace_and_trace_duration_step(self):
        self.assertEqual(
            icing.encounter_severity(0.20, -10.0, 20.0), (0, "trace")
        )
        self.assertEqual(
            icing.encounter_severity(0.20, -10.0, 45.0), (1, "light")
        )

    def test_moderate_and_boundary_severe(self):
        self.assertEqual(
            icing.encounter_severity(0.55, -10.0, 20.0), (2, "moderate")
        )
        self.assertEqual(
            icing.encounter_severity(0.66, -10.0, 20.0), (3, "severe")
        )

    def test_severe_capped_through_duration_step(self):
        self.assertEqual(
            icing.encounter_severity(0.70, -10.0, 90.0), (3, "severe")
        )

    def test_duration_boundary_30_does_not_step(self):
        self.assertEqual(
            icing.encounter_severity(0.22, -10.0, 30.0), (1, "light")
        )
        self.assertEqual(
            icing.encounter_severity(0.22, -10.0, 30.1), (2, "moderate")
        )

    def test_severity_valueerror(self):
        with self.assertRaises(ValueError):
            icing.encounter_severity(-0.2, -10.0, 30.0)
        with self.assertRaises(ValueError):
            icing.encounter_severity(0.3, -10.0, -5.0)
        with self.assertRaises(ValueError):
            icing.encounter_severity(float("nan"), -10.0, 30.0)


class NaturalIcingSearchTests(unittest.TestCase):
    """Natural icing search go/no-go screening."""

    def test_false_when_freezing_level_below_cloud_base(self):
        ok, reasons = icing.natural_icing_search_ok(-8.0, 3000.0, 2000.0, 0.1)
        self.assertFalse(ok)
        self.assertTrue(any("freezing level" in r for r in reasons))

    def test_true_when_freezing_level_above_cloud_base(self):
        ok, reasons = icing.natural_icing_search_ok(-8.0, 3000.0, 4000.0, 0.1)
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_false_when_forecast_lwc_below_fraction(self):
        ok, reasons = icing.natural_icing_search_ok(-8.0, 3000.0, 4000.0, 0.02)
        self.assertFalse(ok)
        self.assertTrue(any("liquid water content" in r for r in reasons))

    def test_false_when_temperature_outside_band(self):
        ok, reasons = icing.natural_icing_search_ok(5.0, 3000.0, 4000.0, 0.1)
        self.assertFalse(ok)
        self.assertTrue(any("above 0 C" in r for r in reasons))
        ok, reasons = icing.natural_icing_search_ok(-40.0, 3000.0, 4000.0, 0.1)
        self.assertFalse(ok)
        self.assertTrue(any("below -30 C" in r for r in reasons))

    def test_search_valueerror(self):
        with self.assertRaises(ValueError):
            icing.natural_icing_search_ok(float("nan"), 3000.0, 4000.0, 0.1)
        with self.assertRaises(ValueError):
            icing.natural_icing_search_ok(-8.0, 3000.0, 4000.0, -0.1)
        with self.assertRaises(ValueError):
            icing.natural_icing_search_ok(-8.0, -1.0, 4000.0, 0.1)


def _shape(surface, coverage=0.9, roughness=True, shape_type="glaze"):
    return {
        "surface": surface,
        "type": shape_type,
        "coverage_frac": coverage,
        "roughness_ok": roughness,
    }


class ArtificialShapeCheckTests(unittest.TestCase):
    """Artificial ice shape matrix coverage checks."""

    def test_missing_critical_surface_issue(self):
        shapes = [
            _shape("wing"),
            _shape("horizontal-tail", shape_type="rime"),
        ]
        result = icing.artificial_shape_check(shapes)
        self.assertEqual(result["verdict"], "fail")
        issues = "\n".join(result["issues"])
        self.assertIn("vertical-tail", issues)
        self.assertIn("windshield", issues)
        self.assertIn("probe", issues)

    def test_pass_when_all_critical_surfaces_covered(self):
        shapes = [
            _shape(surface, shape_type="runback")
            for surface in icing.CRITICAL_SURFACES
        ]
        result = icing.artificial_shape_check(shapes)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["issues"], [])

    def test_low_coverage_issue(self):
        shapes = [_shape(surface) for surface in icing.CRITICAL_SURFACES]
        shapes[0] = _shape("wing", coverage=0.79)
        result = icing.artificial_shape_check(shapes)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("coverage below 0.8 on wing" in i for i in result["issues"]))

    def test_roughness_issue(self):
        shapes = [_shape(surface) for surface in icing.CRITICAL_SURFACES]
        shapes[1] = _shape("horizontal-tail", roughness=False)
        result = icing.artificial_shape_check(shapes)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(
            any("roughness not representative on horizontal-tail" in i for i in result["issues"])
        )

    def test_valueerror_on_bad_shape_fields(self):
        for bad_coverage in (-0.1, 1.2, float("nan")):
            with self.assertRaises(ValueError):
                icing.artificial_shape_check([_shape("wing", coverage=bad_coverage)])
        with self.assertRaises(ValueError):
            icing.artificial_shape_check([_shape("spinner")])
        with self.assertRaises(ValueError):
            icing.artificial_shape_check([_shape("wing", shape_type="frost")])
        with self.assertRaises(ValueError):
            icing.artificial_shape_check(
                [
                    {
                        "surface": "wing",
                        "type": "glaze",
                        "coverage_frac": 0.9,
                        "roughness_ok": "yes",
                    }
                ]
            )


class EffectivenessAndSummaryTests(unittest.TestCase):
    """Effectiveness test point pairing, standard rows, summary."""

    def _configs(self):
        return [
            {"name": "anti-ice-off", "anti_ice": "off", "de_ice_cycle": "standard"},
            {"name": "anti-ice-on", "anti_ice": "on", "de_ice_cycle": "none"},
        ]

    def test_effectiveness_test_points_pairing(self):
        rows = icing.effectiveness_test_points(self._configs(), icing.standard_envelope_rows())
        self.assertEqual(len(rows), 2 * len(icing.standard_envelope_rows()))
        self.assertEqual(rows[0]["config"], "anti-ice-off")
        self.assertEqual(rows[0]["condition"], "continuous-maximum-peak-lwc")
        self.assertEqual(rows[0]["expected_regime"], "continuous-max")
        for row in rows:
            self.assertIn(row["config"], ("anti-ice-off", "anti-ice-on"))
            self.assertIn(row["condition"], {r["condition"] for r in icing.standard_envelope_rows()})

    def test_effectiveness_config_validation(self):
        with self.assertRaises(ValueError):
            icing.effectiveness_test_points([{"anti_ice": "on", "de_ice_cycle": "none"}], [])
        with self.assertRaises(ValueError):
            icing.effectiveness_test_points(
                [{"name": "x", "anti_ice": "auto", "de_ice_cycle": "none"}], []
            )
        with self.assertRaises(ValueError):
            icing.effectiveness_test_points([{"name": "x", "anti_ice": "on"}], [])

    def test_standard_rows_consistent_with_verdict(self):
        for row in icing.standard_envelope_rows():
            verdict = icing.envelope_verdict(row["lwc"], row["mvd"], row["tat"])
            self.assertTrue(verdict["in_envelope"])
            self.assertEqual(verdict["regime"], row["regime"])

    def test_summarize_worked_example_report(self):
        report = icing.summarize(0.30, 20.0, -10.0, 45.0)
        self.assertTrue(report["in_envelope"])
        self.assertEqual(report["regime"], "continuous-max")
        self.assertAlmostEqual(report["margin"], 0.14, places=6)
        self.assertEqual(report["severity_index"], 2)
        self.assertEqual(report["severity_label"], "moderate")

    def test_module_constants_present(self):
        self.assertEqual(icing.SLD_MVD_MIN, 50.0)
        self.assertEqual(icing.SEARCH_LWC_FRACTION, 0.1)
        self.assertEqual(icing.COVERAGE_MIN, 0.8)
        self.assertEqual(icing.SEVERE_DURATION_MIN, 30.0)
        self.assertEqual(
            icing.CRITICAL_SURFACES,
            ["wing", "horizontal-tail", "vertical-tail", "windshield", "probe"],
        )
        self.assertEqual(icing.LWC_CM_MAX, 0.44)
        self.assertEqual(icing.LWC_IM_MAX, 1.4)


if __name__ == "__main__":
    unittest.main()
