"""Contract test for the propulsion/axial-compressor/polytropic-efficiency leaf.

Exercises the numbered SKILL.md Workflow: fixing the operating point with
the air-standard gamma of 1.4 and the physical pressure-ratio and
efficiency bounds (step 1), converting a quoted isentropic efficiency to
the stage-count-independent polytropic efficiency at the overall pressure
ratio for the compressor and the turbine (step 2), restating that
polytropic efficiency at the per-stage pressure ratio to expose the
isentropic efficiency's dependence on the quoted ratio (step 3), resolving
the polytropic efficiency from the inlet and exit total states and
checking the result against the conversion value (step 4), sweeping the
isentropic efficiency over the pressure-ratio ladder at fixed eta_p to
show the compressor fall and the turbine rise (step 5), running the
reheat-factor log-sum cross-check of the per-stage pressure ratios
against the overall pressure ratio (step 6), and confirming the
deterministic contract test run (step 7).  Every expectation is a real
module output from a local run, cross-checked against the spec anchors
and the closed-form identities of the leaf.
"""

import unittest

import polytropic_efficiency_logic as pel


class TestModuleConstants(unittest.TestCase):
    """Step 1 of the SKILL.md workflow, the air-standard operating point."""

    def test_module_constants_air_standard_gamma(self):
        """Step 1 fixes gamma at 1.4 and KAPPA at (gamma - 1)/gamma = 2/7."""
        self.assertEqual(pel.GAMMA, 1.4)
        self.assertAlmostEqual(pel.KAPPA, 2.0 / 7.0, places=15)
        self.assertAlmostEqual(pel.KAPPA, 0.2857142857142857, places=15)

    def test_module_outputs_deterministic(self):
        """Step 7's contract relies on deterministic closed-form outputs."""
        first = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        second = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        self.assertEqual(first, second)
        third = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        fourth = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        self.assertEqual(third, fourth)


class TestCompressorConversions(unittest.TestCase):
    """Steps 2, 3 and 5 of the SKILL.md workflow on the compressor side."""

    def test_polytropic_from_isentropic_anchor_overall_ratio(self):
        """Step 2 converts eta_s 0.85 quoted at overall pressure ratio 20
        to eta_p 0.898525, the stage-count-independent value."""
        eta_p = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        self.assertAlmostEqual(eta_p, 0.898525, places=6)
        self.assertGreater(eta_p, 0.85)

    def test_round_trip_at_overall_ratio(self):
        """Step 2 and its step 3 reverse: converting 0.898525 back at the
        same overall pressure ratio recovers the input eta_s exactly."""
        eta_p = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        eta_s = pel.compressor_isentropic_from_polytropic(eta_p, 20.0)
        self.assertAlmostEqual(eta_s, 0.85, places=12)

    def test_round_trip_holds_across_ratios(self):
        """Step 2's conversion and step 3's reverse are exact inverses at
        any fixed overall pressure ratio within float noise."""
        for eta_s, pr in ((0.85, 20.0), (0.9, 3.0), (0.75, 12.0),
                          (0.99, 2.0), (0.6, 30.0)):
            eta_p = pel.compressor_polytropic_from_isentropic(eta_s, pr)
            self.assertAlmostEqual(
                pel.compressor_isentropic_from_polytropic(eta_p, pr),
                eta_s, places=12)

    def test_per_stage_restatement_anchor(self):
        """Step 3 restates eta_p 0.898525 at the per-stage pressure ratio
        1.2, giving the per-stage isentropic efficiency 0.895862."""
        eta_p = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        eta_s_stage = pel.compressor_isentropic_from_polytropic(eta_p, 1.2)
        self.assertAlmostEqual(eta_s_stage, 0.895862, places=6)

    def test_per_stage_efficiency_above_overall_value(self):
        """Step 3: the per-stage isentropic efficiency 0.895862 exceeds the
        overall-ratio value 0.85, so eta_s depends on the quoted ratio
        while eta_p is stage-count independent."""
        eta_p = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        eta_s_stage = pel.compressor_isentropic_from_polytropic(eta_p, 1.2)
        eta_s_overall = pel.compressor_isentropic_from_polytropic(eta_p, 20.0)
        self.assertGreater(eta_s_stage, eta_s_overall)
        self.assertAlmostEqual(eta_s_overall, 0.85, places=12)

    def test_isentropic_efficiency_falls_with_pressure_ratio(self):
        """Step 5 sweeps eta_s over the pressure-ratio ladder at fixed
        eta_p 0.898525: 0.862070 at PR 10 and 0.837497 at PR 40, the
        headline sizing fall as the overall pressure ratio grows."""
        eta_p = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        self.assertAlmostEqual(
            pel.compressor_isentropic_from_polytropic(eta_p, 10.0),
            0.862070, places=6)
        self.assertAlmostEqual(
            pel.compressor_isentropic_from_polytropic(eta_p, 40.0),
            0.837497, places=6)
        ratios = (1.2, 2.0, 5.0, 10.0, 20.0, 40.0)
        ladder = [pel.compressor_isentropic_from_polytropic(eta_p, pr)
                  for pr in ratios]
        for low, high in zip(ladder, ladder[1:]):
            self.assertGreater(low, high)

    def test_isentropic_efficiency_stays_in_unit_interval(self):
        """Step 5: the swept eta_s never leaves (0, 1) and always sits
        below the fixed polytropic value for the compressor."""
        eta_p = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        for pr in (1.2, 2.0, 5.0, 10.0, 20.0, 40.0):
            eta_s = pel.compressor_isentropic_from_polytropic(eta_p, pr)
            self.assertGreater(eta_s, 0.0)
            self.assertLess(eta_s, 1.0)
            self.assertLess(eta_s, eta_p)

    def test_unity_efficiency_boundary_compressor(self):
        """Step 1 bounds: eta of exactly 1 is physical and converts to 1."""
        self.assertAlmostEqual(
            pel.compressor_polytropic_from_isentropic(1.0, 20.0), 1.0,
            places=12)
        self.assertAlmostEqual(
            pel.compressor_isentropic_from_polytropic(1.0, 20.0), 1.0,
            places=12)

    def test_eta_s_meets_eta_p_as_pr_approaches_one(self):
        """Step 5 ordering identity: both efficiencies coincide with eta_p
        as the overall pressure ratio approaches 1 from above."""
        eta_p = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        near = 1.0001
        eta_s = pel.compressor_isentropic_from_polytropic(eta_p, near)
        self.assertAlmostEqual(eta_s, eta_p, places=4)
        self.assertLess(eta_s, eta_p)


class TestCompressorFromStates(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, resolving eta_p from total states."""

    def test_from_states_anchor_overall_machine(self):
        """Step 4 with t01 = 288.15 K and the whole-drop exit 747.002 K at
        overall pressure ratio 20 resolves eta_p 0.898525."""
        eta_p = pel.compressor_polytropic_from_states(288.15, 747.002, 20.0)
        self.assertAlmostEqual(eta_p, 0.898525, delta=1e-6)

    def test_from_states_matches_conversion_value(self):
        """Step 4: the eta_p resolved from states built with the whole-drop
        ratio 1 + (pr**KAPPA - 1)/eta_s equals the conversion value from
        step 2 exactly."""
        t01 = 288.15
        t02 = t01 * (1.0 + (20.0 ** pel.KAPPA - 1.0) / 0.85)
        from_states = pel.compressor_polytropic_from_states(t01, t02, 20.0)
        from_eta_s = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        self.assertAlmostEqual(from_states, from_eta_s, places=12)
        self.assertAlmostEqual(t02, 747.0023969474354, places=6)

    def test_stage_count_independence_from_states(self):
        """Step 4 and step 3 together: eta_p resolved at one stage's states
        (t01, t01 * 1.2**(KAPPA/eta_p), pr 1.2) equals eta_p resolved at
        the overall machine's states to 1e-12, the stage-count
        independence verdict on the log scale."""
        eta_p = pel.compressor_polytropic_from_isentropic(0.85, 20.0)
        t01 = 288.15
        stage_ratio = 1.2 ** (pel.KAPPA / eta_p)
        self.assertAlmostEqual(stage_ratio, 1.059688, places=6)
        stage_states = pel.compressor_polytropic_from_states(
            t01, t01 * stage_ratio, 1.2)
        overall_states = pel.compressor_polytropic_from_states(
            t01, t01 * (1.0 + (20.0 ** pel.KAPPA - 1.0) / 0.85), 20.0)
        self.assertAlmostEqual(stage_states, overall_states, places=12)
        self.assertAlmostEqual(stage_states, eta_p, places=12)

    def test_state_rejections_compressor(self):
        """Step 4 guards: no compression (t02 equal to or below t01) and
        non-positive total temperatures raise ValueError."""
        with self.assertRaises(ValueError):
            pel.compressor_polytropic_from_states(288.15, 288.15, 20.0)
        with self.assertRaises(ValueError):
            pel.compressor_polytropic_from_states(288.15, 250.0, 20.0)
        with self.assertRaises(ValueError):
            pel.compressor_polytropic_from_states(0.0, 500.0, 20.0)
        with self.assertRaises(ValueError):
            pel.compressor_polytropic_from_states(288.15, -1.0, 20.0)


class TestTurbineConversions(unittest.TestCase):
    """Steps 2, 3 and 5 of the SKILL.md workflow on the turbine side."""

    def test_polytropic_from_isentropic_anchor_expansion_ratio(self):
        """Step 2 mirror: converting the turbine eta_s 0.88 at expansion
        ratio 3 gives eta_p 0.862061, below the isentropic value."""
        eta_p = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        self.assertAlmostEqual(eta_p, 0.862061, places=6)
        self.assertLess(eta_p, 0.88)

    def test_round_trip_at_expansion_ratio(self):
        """Step 2 and its step 3 reverse on the turbine side recover the
        input eta_s 0.88 exactly at the same expansion ratio."""
        eta_p = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        eta_s = pel.turbine_isentropic_from_polytropic(eta_p, 3.0)
        self.assertAlmostEqual(eta_s, 0.88, places=12)

    def test_round_trip_holds_across_expansion_ratios(self):
        """Step 2's turbine conversion and step 3's reverse are exact
        inverses at any fixed expansion ratio within float noise."""
        for eta_s, pr in ((0.88, 3.0), (0.92, 6.0), (0.80, 1.5),
                          (0.95, 15.0), (0.75, 8.0)):
            eta_p = pel.turbine_polytropic_from_isentropic(eta_s, pr)
            self.assertAlmostEqual(
                pel.turbine_isentropic_from_polytropic(eta_p, pr),
                eta_s, places=12)

    def test_isentropic_from_polytropic_at_ratio_ten(self):
        """Step 5 mirror: at the same eta_p 0.862061 the turbine isentropic
        efficiency rises to 0.897934 as the expansion ratio grows to 10."""
        eta_p = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        eta_s_10 = pel.turbine_isentropic_from_polytropic(eta_p, 10.0)
        self.assertAlmostEqual(eta_s_10, 0.897934, places=6)
        self.assertGreater(eta_s_10, 0.88)

    def test_turbine_ordering_reversed_from_compressor(self):
        """Step 3 ordering: for the turbine the isentropic efficiency 0.88
        sits ABOVE its polytropic 0.862061 at expansion ratio 3, the
        reverse of the compressor ordering at pressure ratio above 1."""
        eta_p = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        eta_s = pel.turbine_isentropic_from_polytropic(eta_p, 3.0)
        self.assertGreater(eta_s, eta_p)
        self.assertAlmostEqual(eta_s, 0.88, places=12)

    def test_turbine_eta_s_rises_with_expansion_ratio(self):
        """Step 5: the turbine eta_s rises toward 1 as the expansion ratio
        grows at fixed eta_p, never leaving (0, 1)."""
        eta_p = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        ladder = [pel.turbine_isentropic_from_polytropic(eta_p, pr)
                  for pr in (1.5, 3.0, 6.0, 10.0, 15.0)]
        for low, high in zip(ladder, ladder[1:]):
            self.assertLess(low, high)
        for value in ladder:
            self.assertGreater(value, 0.0)
            self.assertLess(value, 1.0)

    def test_unity_efficiency_boundary_turbine(self):
        """Step 1 bounds: eta of exactly 1 converts to 1 on the turbine
        side as well."""
        self.assertAlmostEqual(
            pel.turbine_polytropic_from_isentropic(1.0, 3.0), 1.0,
            places=12)
        self.assertAlmostEqual(
            pel.turbine_isentropic_from_polytropic(1.0, 3.0), 1.0,
            places=12)


class TestTurbineFromStates(unittest.TestCase):
    """Step 4 of the SKILL.md workflow on the turbine side."""

    def test_from_states_anchor_turbine(self):
        """Step 4 with t03 = 1500 K, the whole-drop exit 1144.392 K and
        expansion ratio 3 resolves eta_p 0.862061."""
        eta_p = pel.turbine_polytropic_from_states(1500.0, 1144.392, 3.0)
        self.assertAlmostEqual(eta_p, 0.862061, places=6)

    def test_from_states_matches_conversion_value_turbine(self):
        """Step 4: the eta_p resolved from the whole-drop exit
        t04 = t03 * (1 - eta_s*(1 - pr**(-KAPPA))) equals the
        from-isentropic conversion value exactly."""
        t03 = 1500.0
        t04 = t03 * (1.0 - 0.88 * (1.0 - 3.0 ** (-pel.KAPPA)))
        from_states = pel.turbine_polytropic_from_states(t03, t04, 3.0)
        from_eta_s = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        self.assertAlmostEqual(from_states, from_eta_s, places=12)
        self.assertAlmostEqual(t04, 1144.3919414490722, places=6)

    def test_exponent_form_matches_whole_drop_form(self):
        """Step 4: the polytropic exponent form t04/t03 = pr**(-KAPPA*eta_p)
        agrees with the whole-drop form 1 - eta_s*(1 - pr**(-KAPPA))."""
        t03 = 1500.0
        whole_drop = 1.0 - 0.88 * (1.0 - 3.0 ** (-pel.KAPPA))
        eta_p = pel.turbine_polytropic_from_isentropic(0.88, 3.0)
        exponent_form = 3.0 ** (-pel.KAPPA * eta_p)
        self.assertAlmostEqual(whole_drop, 0.762928, places=6)
        self.assertAlmostEqual(exponent_form, whole_drop, places=12)

    def test_state_rejections_turbine(self):
        """Step 4 guards: no expansion (t04 equal to or above t03) and
        non-positive total temperatures raise ValueError."""
        with self.assertRaises(ValueError):
            pel.turbine_polytropic_from_states(1500.0, 1500.0, 3.0)
        with self.assertRaises(ValueError):
            pel.turbine_polytropic_from_states(1500.0, 1600.0, 3.0)
        with self.assertRaises(ValueError):
            pel.turbine_polytropic_from_states(0.0, 800.0, 3.0)
        with self.assertRaises(ValueError):
            pel.turbine_polytropic_from_states(1500.0, -5.0, 3.0)


class TestReheatFactorCheck(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the reheat-factor log-sum
    cross-check of the per-stage pressure ratios against the overall
    pressure ratio."""

    def test_equal_stage_identity(self):
        """Step 6: 16 stages at 1.2 against their own product 1.2**16 give
        R = 1 to 1e-12, the equal-stage identity of the log sum."""
        r = pel.reheat_factor_check([1.2] * 16, 1.2 ** 16)
        self.assertAlmostEqual(r, 1.0, places=12)
        self.assertAlmostEqual(1.2 ** 16, 18.49, places=2)

    def test_underreported_stages_flag_inconsistency(self):
        """Step 6: 16 stages at 1.2 claimed against overall pressure ratio
        20 give R = 0.973767, flagging stage data below the quoted
        overall ratio."""
        r = pel.reheat_factor_check([1.2] * 16, 20.0)
        self.assertAlmostEqual(r, 0.973767, places=6)
        self.assertLess(r, 1.0)

    def test_overreported_stages_flag_inconsistency(self):
        """Step 6: 17 stages at 1.2 claimed against overall pressure ratio
        20 give R = 1.034627, flagging stage data above the quoted
        overall ratio."""
        r = pel.reheat_factor_check([1.2] * 17, 20.0)
        self.assertAlmostEqual(r, 1.034627, places=6)
        self.assertGreater(r, 1.0)

    def test_mixed_stage_list_product_identity(self):
        """Step 6: any stage list whose product equals the overall ratio
        returns R = 1, here [1.2, 1.3, 1.5] against its own product."""
        stages = [1.2, 1.3, 1.5]
        overall = 1.2 * 1.3 * 1.5
        r = pel.reheat_factor_check(stages, overall)
        self.assertAlmostEqual(r, 1.0, places=12)

    def test_mismatched_stage_list_deviates_from_one(self):
        """Step 6: swapping one stage ratio against a foreign overall ratio
        pushes R away from the equal-stage identity of 1."""
        r = pel.reheat_factor_check([1.2, 1.5], 1.2 * 1.3)
        self.assertNotAlmostEqual(r, 1.0, places=6)

    def test_invalid_stage_data_rejected(self):
        """Step 6 guards: an empty stage list, a stage ratio of 1.0, and a
        non-physical overall pressure ratio all raise ValueError."""
        with self.assertRaises(ValueError):
            pel.reheat_factor_check([], 20.0)
        with self.assertRaises(ValueError):
            pel.reheat_factor_check([1.2, 1.0], 20.0)
        with self.assertRaises(ValueError):
            pel.reheat_factor_check([1.2] * 16, 1.0)
        with self.assertRaises(ValueError):
            pel.reheat_factor_check([1.2] * 16, 0.5)


class TestInputValidation(unittest.TestCase):
    """Step 1 of the SKILL.md workflow, the physical bounds on every
    argument: eta in (0, 1] and pr above 1 for both machines."""

    def test_compressor_eta_arguments_reject_nonphysical(self):
        """Step 1: eta at 0, 1.5 and 1.01 raises ValueError for both
        compressor conversion directions."""
        for bad in (0.0, 1.5, 1.01):
            with self.assertRaises(ValueError):
                pel.compressor_polytropic_from_isentropic(bad, 20.0)
            with self.assertRaises(ValueError):
                pel.compressor_isentropic_from_polytropic(bad, 20.0)

    def test_turbine_eta_arguments_reject_nonphysical(self):
        """Step 1: eta at 0, 1.5 and 1.01 raises ValueError for both
        turbine conversion directions."""
        for bad in (0.0, 1.5, 1.01):
            with self.assertRaises(ValueError):
                pel.turbine_polytropic_from_isentropic(bad, 3.0)
            with self.assertRaises(ValueError):
                pel.turbine_isentropic_from_polytropic(bad, 3.0)

    def test_pr_arguments_reject_nonphysical(self):
        """Step 1: an overall pressure ratio of 1.0 or below raises
        ValueError across every conversion, compressor and turbine."""
        for bad in (1.0, 0.5, 1.0 / 3.0):
            with self.assertRaises(ValueError):
                pel.compressor_polytropic_from_isentropic(0.85, bad)
            with self.assertRaises(ValueError):
                pel.compressor_isentropic_from_polytropic(0.898525, bad)
            with self.assertRaises(ValueError):
                pel.turbine_polytropic_from_isentropic(0.88, bad)
            with self.assertRaises(ValueError):
                pel.turbine_isentropic_from_polytropic(0.862061, bad)


if __name__ == "__main__":
    unittest.main()
