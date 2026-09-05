"""Contract test for variables_acceptance_sampling_logic (wave-38, as9100 pack).

Runs offline with stdlib unittest only:
    python3 scripts/test_variables_acceptance_sampling.py

Covers the spec validation list: the code letter boundary truth table
(91-150 E through 3201-10000 K, spec boundaries 281 -> G, 501 -> H,
1201 -> J), the plan_lookup table values for the embedded codes and AQLs
(sample sizes 15-40, k set 1.75/1.62/1.47/1.28/1.09, M rows E, H and K),
the Q forms and accept verdict at the worked example (Q 1.9167 accept,
Q 4.75 lower-limit accept), the reject case (xbar 50.1, USL 50.2, Q 0.833
reject), p_hat = 2.76 percent at Q 1.9167 within 0.05 percent, the AQL
margin identity (accept at a looser AQL, reject at a tighter AQL for the
same stats), normal-survival consistency, determinism, exact dict keys,
and ValueError rejection of non-physical inputs (s <= 0, lot_size <= 0,
out-of-band lot sizes, unknown code letter, unknown AQL, unknown level,
invalid tail).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from variables_acceptance_sampling_logic import (
    AQLS,
    CODE_LETTER_BANDS,
    INSPECTION_LEVELS,
    K_BY_AQL,
    M_BY_CODE_AQL,
    N_BY_CODE,
    accept_verdict,
    code_letter,
    estimated_pct_nonconforming,
    form_q_lower,
    form_q_upper,
    normal_cdf,
    normal_survival,
    plan_lookup,
    variables_sampling_decision,
)


class VariablesAcceptanceSamplingContract(unittest.TestCase):
    """Deterministic offline contract for the variables sampling model."""

    # --- code letter truth table -------------------------------------------

    def test_code_letter_band_edges_all_codes(self):
        edges = [(91, "E"), (150, "E"), (151, "F"), (280, "F"), (281, "G"),
                 (500, "G"), (501, "H"), (1200, "H"), (1201, "J"),
                 (3200, "J"), (3201, "K"), (10000, "K")]
        for lot, expected in edges:
            self.assertEqual(code_letter(lot), expected, "lot %d" % lot)

    def test_code_letter_lot_800_anchor_code_h(self):
        self.assertEqual(code_letter(800), "H")
        self.assertEqual(code_letter(800, "II"), "H")

    def test_code_letter_spec_boundaries_281_501_1201(self):
        self.assertEqual(code_letter(281), "G")
        self.assertEqual(code_letter(501), "H")
        self.assertEqual(code_letter(1201), "J")

    def test_code_letter_nonpositive_and_out_of_band_raise(self):
        for bad in (0, -5, 90, 10001):
            with self.assertRaises(ValueError, msg="lot %r" % bad):
                code_letter(bad)

    def test_code_letter_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            code_letter(800, "IV")
        # Levels I and III have no embedded rows in the reduced table.
        with self.assertRaises(ValueError):
            code_letter(800, "I")
        with self.assertRaises(ValueError):
            code_letter(800, "III")

    # --- plan lookup table values ------------------------------------------

    def test_plan_lookup_anchor_row_h_aql_1_0(self):
        plan = plan_lookup("H", 1.0)
        self.assertEqual(plan, {"n": 30, "k": 1.62, "M": 3.37})

    def test_plan_lookup_sample_sizes_all_codes(self):
        for code, n in (("E", 15), ("F", 20), ("G", 25), ("H", 30),
                        ("J", 35), ("K", 40)):
            self.assertEqual(plan_lookup(code, 1.0)["n"], n)

    def test_plan_lookup_k_values_all_aqls(self):
        expected = {0.65: 1.75, 1.0: 1.62, 1.5: 1.47, 2.5: 1.28, 4.0: 1.09}
        for aql, k in expected.items():
            self.assertEqual(plan_lookup("H", aql)["k"], k, "AQL %r" % aql)
        # k falls as the AQL loosens.
        ks = [plan_lookup("H", aql)["k"] for aql in AQLS]
        self.assertEqual(ks, sorted(ks, reverse=True))

    def test_plan_lookup_m_values_code_e(self):
        expected = {0.65: 4.17, 1.0: 3.61, 1.5: 2.98, 2.5: 2.28, 4.0: 1.66}
        for aql, M in expected.items():
            self.assertEqual(plan_lookup("E", aql)["M"], M, "AQL %r" % aql)

    def test_plan_lookup_m_values_code_h(self):
        expected = {0.65: 3.90, 1.0: 3.37, 1.5: 2.78, 2.5: 2.13, 4.0: 1.55}
        for aql, M in expected.items():
            self.assertEqual(plan_lookup("H", aql)["M"], M, "AQL %r" % aql)

    def test_plan_lookup_m_values_code_k(self):
        expected = {0.65: 3.80, 1.0: 3.29, 1.5: 2.72, 2.5: 2.08, 4.0: 1.52}
        for aql, M in expected.items():
            self.assertEqual(plan_lookup("K", aql)["M"], M, "AQL %r" % aql)

    def test_plan_lookup_unknown_code_raises(self):
        for bad in ("L", "Z", "A", "II"):
            with self.assertRaises(ValueError, msg="code %r" % bad):
                plan_lookup(bad, 1.0)

    def test_plan_lookup_unknown_aql_raises(self):
        for bad in (0.8, 2.0, 0.1, 6.5):
            with self.assertRaises(ValueError, msg="AQL %r" % bad):
                plan_lookup("H", bad)

    def test_plan_lookup_int_aql_float_equivalence(self):
        self.assertEqual(plan_lookup("H", 1), plan_lookup("H", 1.0))

    # --- Q statistics -------------------------------------------------------

    def test_form_q_upper_anchor_value(self):
        Q = form_q_upper(50.2, 49.97, 0.12)
        self.assertAlmostEqual(Q, 1.9167, delta=0.001)

    def test_form_q_lower_anchor_value(self):
        Q = form_q_lower(49.4, 49.97, 0.12)
        self.assertAlmostEqual(Q, 4.75, delta=0.001)

    def test_form_q_reject_geometry_mean_near_limit(self):
        # xbar 50.1 against USL 50.2: Q = 0.8333, below k = 1.62.
        Q = form_q_upper(50.2, 50.1, 0.12)
        self.assertAlmostEqual(Q, 0.8333, delta=0.001)
        self.assertLess(Q, 1.62)

    def test_form_q_negative_when_mean_past_limit(self):
        self.assertLess(form_q_upper(50.2, 50.3, 0.12), 0.0)
        self.assertLess(form_q_lower(49.4, 49.3, 0.12), 0.0)

    def test_form_q_nonpositive_s_raises(self):
        for s in (0.0, -0.1):
            with self.assertRaises(ValueError, msg="s %r" % s):
                form_q_upper(50.2, 49.97, s)
            with self.assertRaises(ValueError, msg="s %r" % s):
                form_q_lower(49.4, 49.97, s)

    # --- normal tail and estimated percent nonconforming -------------------

    def test_normal_survival_reference_points(self):
        self.assertAlmostEqual(normal_survival(0.0), 0.5, places=12)
        self.assertAlmostEqual(normal_survival(1.96), 0.025, delta=1e-3)

    def test_normal_survival_cdf_complement_identity(self):
        for z in (0.5, 1.5, 2.0, -1.0):
            self.assertAlmostEqual(normal_survival(z) + normal_cdf(z), 1.0,
                                   delta=1e-6)

    def test_estimated_pct_upper_anchor_2_76_percent(self):
        p_hat = estimated_pct_nonconforming(1.9167, "upper")
        self.assertAlmostEqual(p_hat, 2.76, delta=0.05)
        # The Q values and p_hat stay consistent through the survival fn.
        d = variables_sampling_decision(800, 1.0, 50.2, 49.97, 0.12)
        self.assertAlmostEqual(d["p_hat"],
                               estimated_pct_nonconforming(d["Q"], "upper"),
                               places=6)

    def test_estimated_pct_lower_upper_symmetry(self):
        for Q in (1.9167, 4.75, 0.8333):
            self.assertAlmostEqual(
                estimated_pct_nonconforming(Q, "lower"),
                estimated_pct_nonconforming(Q, "upper"),
                places=10)

    def test_estimated_pct_far_inside_limit_tiny_and_m_ok(self):
        p_hat = estimated_pct_nonconforming(4.75, "upper")
        self.assertLess(p_hat, 0.001)   # percent
        self.assertLess(p_hat, 3.37)    # M for code H at AQL 1.0

    def test_estimated_pct_invalid_tail_raises(self):
        for tail in ("both", "UPPER", "", None):
            with self.assertRaises(ValueError, msg="tail %r" % tail):
                estimated_pct_nonconforming(1.9167, tail)

    # --- accept verdict -----------------------------------------------------

    def test_accept_verdict_truth_table(self):
        self.assertTrue(accept_verdict(1.9167, 1.62))
        self.assertFalse(accept_verdict(0.8333, 1.62))
        self.assertTrue(accept_verdict(1.62, 1.62))   # boundary accepts
        self.assertFalse(accept_verdict(1.61, 1.62))
        self.assertTrue(accept_verdict(4.75, 1.62))

    # --- end-to-end decision -------------------------------------------------

    def test_decision_worked_example_upper(self):
        d = variables_sampling_decision(800, 1.0, 50.2, 49.97, 0.12)
        self.assertEqual(d["code"], "H")
        self.assertEqual(d["n"], 30)
        self.assertEqual(d["k"], 1.62)
        self.assertEqual(d["M"], 3.37)
        self.assertAlmostEqual(d["Q"], 1.9167, delta=0.001)
        self.assertTrue(d["accept"])
        self.assertAlmostEqual(d["p_hat"], 2.76, delta=0.05)

    def test_decision_worked_example_lower(self):
        d = variables_sampling_decision(800, 1.0, 49.4, 49.97, 0.12)
        self.assertEqual(d["code"], "H")
        self.assertAlmostEqual(d["Q"], 4.75, delta=0.001)
        self.assertTrue(d["accept"])

    def test_decision_reject_case(self):
        d = variables_sampling_decision(800, 1.0, 50.2, 50.1, 0.12)
        self.assertAlmostEqual(d["Q"], 0.8333, delta=0.001)
        self.assertFalse(d["accept"])

    def test_decision_aql_margin_identity(self):
        # Same stats, Q = 1.50: accept at AQL 1.5 (k 1.47), reject at the
        # tighter AQLs 1.0 (k 1.62) and 0.65 (k 1.75).
        loose = variables_sampling_decision(800, 1.5, 50.2, 50.02, 0.12)
        tight = variables_sampling_decision(800, 1.0, 50.2, 50.02, 0.12)
        tightest = variables_sampling_decision(800, 0.65, 50.2, 50.02, 0.12)
        self.assertTrue(loose["accept"])
        self.assertFalse(tight["accept"])
        self.assertFalse(tightest["accept"])
        self.assertEqual(loose["n"], tight["n"])
        self.assertAlmostEqual(loose["Q"], tight["Q"], places=12)

    def test_decision_m_method_agreement_anchor(self):
        d = variables_sampling_decision(800, 1.0, 50.2, 49.97, 0.12)
        self.assertTrue(d["accept"])
        self.assertLessEqual(d["p_hat"], d["M"])

    def test_decision_dict_keys_and_determinism(self):
        d = variables_sampling_decision(800, 1.0, 50.2, 49.97, 0.12)
        self.assertEqual(set(d.keys()),
                         {"code", "n", "k", "M", "Q", "p_hat", "accept"})
        for _ in range(3):
            self.assertEqual(variables_sampling_decision(
                800, 1.0, 50.2, 49.97, 0.12), d)

    def test_decision_valueerror_propagation(self):
        with self.assertRaises(ValueError):
            variables_sampling_decision(50, 1.0, 50.2, 49.97, 0.12)
        with self.assertRaises(ValueError):
            variables_sampling_decision(800, 2.0, 50.2, 49.97, 0.12)
        with self.assertRaises(ValueError):
            variables_sampling_decision(800, 1.0, 50.2, 49.97, 0.0)


if __name__ == "__main__":
    unittest.main()
