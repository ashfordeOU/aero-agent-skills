#!/usr/bin/env python3
"""Contract test for the walker-forman-crack-growth leaf (structures,
damage-tolerance pack).

Covers the SKILL.md workflow end to end, step by step. Step 1 of the
workflow (pin the applied cycle: sigma_max, the stress ratio R and the
initial half-crack a0, then evaluate the mode I stress intensity K_max
and the applied range dK with stress_intensity) is exercised by the
stress-intensity checks; step 2 (the walker-equation equivalent range
dK_bar = dK/(1-R)^(1-gamma) with the material gamma exponent, including
the R = 0 and gamma = 1 recovery limits and the R = -1 square-root
relation) by the equivalent-range checks; step 3 (the R-corrected rate
arms: the walker-equation rate from walker_dadN and the forman-equation
rate with the kc-limited denominator from forman_dadN, plus the
walker-versus-paris and forman-versus-paris ratios against the zero-R
Paris baseline) by the rate and ratio checks; step 4 (the block-extension
march: block_extension projects the crack over the stated cycle block
with forward-Euler substeps that re-evaluate dK from the growing crack,
returning the R-corrected rate table rows and the block extension) by
the block checks; step 5 (the piecewise-R workflow:
piecewise_block_extension applies the ordered (cycles, sigma_max, R)
segments with the identical march, and the split identity reproduces one
constant-R block bit for bit) by the piecewise checks; step 6 (the
kc-limited singularity guard: the forman-equation arm raises ValueError
when the marching crack reaches dK = (1-R)*K_c, the fracture state,
stating the cycle) by the ValueError battery; step 7 (the verification
step: run the gate 3 behavior contract, check the closed-form
identities, the monotone rate-table structure and the determinism sha256
of the canonical dump) closes the file.

Every numeric assertion is tolerance based (math.isclose or
assertAlmostEqual with a delta): no exact float equality is asserted on
any computed aggregate, so the suite holds under both /usr/bin/python3
(3.9.6) and the pyenv 3.13.12 hook interpreter. Exact equality is used
only for the sha256 digest strings, the integer cycle labels of the
rate-table rows and the round-trip structures that are exact by
construction (the bit-for-bit split identity and the recovery limits).
All worked-example anchors are the real outputs of the wave-45 prep
anchor (bitwise identical under both interpreters) and sit inside the
magnitude bounds of the wave-45 spec.
"""

import hashlib
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from walker_forman_crack_growth_logic import (  # noqa: E402
    stress_intensity,
    walker_equivalent_range,
    walker_dadN,
    forman_dadN,
    walker_vs_paris_ratio,
    forman_vs_paris_ratio,
    block_extension,
    piecewise_block_extension,
)

SHA256_ANCHOR = "791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62"


# ---------------------------------------------------------------------------
# Anchor material and load constants (worked-example parameters; the logic
# functions below take every material/load quantity as an argument).
# ---------------------------------------------------------------------------
C_PARIS = 1.0e-11     # Paris/Walker arm constant C, (m/cycle)*(MPa*sqrt(m))^-3
M_EXP = 3.0           # exponent m of both rate arms
GAMMA_WALKER = 0.5    # Walker exponent gamma (Walker's published m = 0.5 for the
                      # 2024-T3 / 7075-T6 aluminum data; dK_bar = dK/sqrt(1-R))
KC_MPA = 100.0        # fracture toughness K_c, MPa*sqrt(m) (2024-T3 sheet scale)
C_FORMAN = 1.0e-9     # Forman arm constant C_F = C_PARIS * KC_MPA numerically,
                      # (m/cycle)*(MPa*sqrt(m))^(1-m); an example fit whose
                      # far-from-critical R = 0 limit reproduces the Paris arm
Y_FACTOR = 1.0        # geometry factor, central through-crack in a wide panel

# Case 1 (corpus query 1): 2024-T3 fuselage panel, R = 0.35, 2000-cycle block
SIGMA_MAX_1 = 100.0   # MPa
R_1 = 0.35
A0_1 = 0.02           # m, half-crack length
N_1 = 2000            # cycles

# Case 2 (corpus query 2): growing crack at R = -0.4 near the K_c-limited band
SIGMA_MAX_2 = 140.0   # MPa
R_2 = -0.4
A0_2 = 0.05           # m
N_2 = 2000


import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def _fmt(x):
    return "%.15g" % x


def dump_case(tag, sigma_max, r, a0, cycles):
    lines = []
    a_crit = (KC_MPA / (Y_FACTOR * sigma_max)) ** 2 / math.pi
    dsigma = sigma_max * (1.0 - r)
    k_max0 = stress_intensity(sigma_max, a0, Y_FACTOR)
    dk0 = stress_intensity(dsigma, a0, Y_FACTOR)
    dk_bar0 = walker_equivalent_range(dk0, r, GAMMA_WALKER)
    rw0 = walker_dadN(dk0, r, GAMMA_WALKER, C_PARIS, M_EXP)
    rf0 = forman_dadN(dk0, r, KC_MPA, C_FORMAN, M_EXP)
    rp0 = C_PARIS * dk0 ** M_EXP
    lines.append("case %s: sigma_max = %s MPa, R = %s, a0 = %s m, "
                 "block N = %d cycles, Y = %s" % (tag, _fmt(sigma_max), _fmt(r),
                                                  _fmt(a0), cycles, _fmt(Y_FACTOR)))
    lines.append("  sigma_min = %s MPa, dsigma = %s MPa, geometric critical "
                 "half-crack (context) a_crit = %s m" %
                 (_fmt(r * sigma_max), _fmt(dsigma), _fmt(a_crit)))
    lines.append("  K_max0 = %s MPa*sqrt(m) (K_max/K_c = %s), dK0 = %s, "
                 "dK_bar0 = %s" % (_fmt(k_max0), _fmt(k_max0 / KC_MPA),
                                   _fmt(dk0), _fmt(dk_bar0)))
    lines.append("  rates at block start: paris baseline %s, walker %s, "
                 "forman %s m/cycle" % (_fmt(rp0), _fmt(rw0), _fmt(rf0)))
    lines.append("  walker/paris = %s, forman/paris = %s" %
                 (_fmt(rw0 / rp0), _fmt(rf0 / rp0)))
    for model in ("walker", "forman"):
        res = block_extension(cycles, sigma_max, r, a0, Y_FACTOR, model,
                              GAMMA_WALKER, KC_MPA, C_PARIS, C_FORMAN, M_EXP)
        lines.append("  %s-model block: a_final = %s m, extension = %s m "
                     "(%.6f mm), rate_start = %s, rate_final = %s m/cycle, "
                     "dK_start = %s, dK_final = %s MPa*sqrt(m)" %
                     (model, _fmt(res["a_final_m"]), _fmt(res["extension_m"]),
                      res["extension_m"] * 1000.0, _fmt(res["rate_start"]),
                      _fmt(res["rate_final"]), _fmt(res["dk_start_mpa"]),
                      _fmt(res["dk_final_mpa"])))
        for row in res["rows"]:
            rp = C_PARIS * row["dk_mpa"] ** M_EXP
            rw = walker_dadN(row["dk_mpa"], r, GAMMA_WALKER, C_PARIS, M_EXP)
            rf = forman_dadN(row["dk_mpa"], r, KC_MPA, C_FORMAN, M_EXP)
            lines.append("    cycle %6.0f: a = %s m, dK = %s, dK_bar = %s, "
                         "walker = %s, forman = %s, forman/paris = %s m/cycle" %
                         (row["cycle"], _fmt(row["a_m"]), _fmt(row["dk_mpa"]),
                          _fmt(row["dk_bar_mpa"]), _fmt(rw), _fmt(rf),
                          _fmt(rf / rp)))
    return lines


def dump_sweep():
    lines = []
    lines.append("near-critical sweep R = 0.35, sigma_max = 100 MPa "
                 "(peak K approaching K_c = 100):")
    lines.append("  a_m | K_max/K_c | dK | paris | walker | forman | "
                 "forman/paris m/cycle")
    for a in (0.02, 0.15, 0.25, 0.30, 0.31):
        dk = stress_intensity(100.0 * 0.65, a, Y_FACTOR)
        kmax = stress_intensity(100.0, a, Y_FACTOR)
        rp = C_PARIS * dk ** M_EXP
        rw = walker_dadN(dk, 0.35, GAMMA_WALKER, C_PARIS, M_EXP)
        rf = forman_dadN(dk, 0.35, KC_MPA, C_FORMAN, M_EXP)
        lines.append("  %8s %10s %8s %10s %10s %10s %10s" %
                     (_fmt(a), _fmt(kmax / KC_MPA), _fmt(dk), _fmt(rp),
                      _fmt(rw), _fmt(rf), _fmt(rf / rp)))
    return lines


def _canonical_dump():
    out = []
    out.append("wave-45 walker-forman-crack-growth anchor (stdlib math, "
               "deterministic)")
    out.append("constants: C = %s, m = %s, gamma = %s, K_c = %s MPa*sqrt(m), "
               "C_F = %s, Y = %s" % (_fmt(C_PARIS), _fmt(M_EXP), _fmt(GAMMA_WALKER),
                                     _fmt(KC_MPA), _fmt(C_FORMAN), _fmt(Y_FACTOR)))

    # ---- worked example case 1 (corpus query 1): R = 0.35 ----
    out += dump_case("1 (R = 0.35, fuselage panel, query 1)",
                     SIGMA_MAX_1, R_1, A0_1, N_1)

    # ---- worked example case 2 (corpus query 2): R = -0.4, K_c band ----
    out += dump_case("2 (R = -0.4, growing crack, query 2)",
                     SIGMA_MAX_2, R_2, A0_2, N_2)

    # ---- near-critical sweep, R = 0.35 constant ----
    out += dump_sweep()

    # ---- piecewise-R demo and split identity ----
    single = block_extension(N_1, SIGMA_MAX_1, R_1, A0_1, Y_FACTOR, "walker",
                             GAMMA_WALKER, KC_MPA, C_PARIS, C_FORMAN, M_EXP)
    seg_same = [(1000, SIGMA_MAX_1, R_1), (1000, SIGMA_MAX_1, R_1)]
    pw_same = piecewise_block_extension(seg_same, A0_1, Y_FACTOR, "walker",
                                        GAMMA_WALKER, KC_MPA, C_PARIS,
                                        C_FORMAN, M_EXP)
    out.append("piecewise split identity (walker model): two 1000-cycle "
               "segments at R = 0.35 reproduce the single 2000-cycle block "
               "exactly: %s (a_final %s vs %s m)" %
               (pw_same["a_final_m"] == single["a_final_m"],
                _fmt(pw_same["a_final_m"]), _fmt(single["a_final_m"])))
    seg_mixed = [(1000, SIGMA_MAX_1, 0.35), (1000, SIGMA_MAX_1, 0.60)]
    for model in ("walker", "forman"):
        pw = piecewise_block_extension(seg_mixed, A0_1, Y_FACTOR, model,
                                       GAMMA_WALKER, KC_MPA, C_PARIS,
                                       C_FORMAN, M_EXP)
        for s in pw["segments"]:
            out.append("piecewise %s-model segment R = %s (cycles %d): "
                       "a0 = %s, a_final = %s, extension = %s m, rate_start = "
                       "%s, rate_final = %s m/cycle" %
                       (model, _fmt(s["r"]), s["cycles"], _fmt(s["a0_m"]),
                        _fmt(s["a_final_m"]), _fmt(s["extension_m"]),
                        _fmt(s["rate_start"]), _fmt(s["rate_final"])))
        out.append("piecewise %s-model total: a_final = %s m, extension = %s m"
                   % (model, _fmt(pw["a_final_m"]), _fmt(pw["extension_m"])))

    # ---- closed-form identities ----
    out.append("identity checks (all must be near-exact):")
    dk_t = stress_intensity(SIGMA_MAX_1 * (1.0 - R_1), A0_1, Y_FACTOR)
    k_max_t = stress_intensity(SIGMA_MAX_1, A0_1, Y_FACTOR)
    out.append("  I1 R = 0 recovery: dK_bar(dK, 0, 0.5) - dK = %s" %
               _fmt(walker_equivalent_range(dk_t, 0.0, GAMMA_WALKER) - dk_t))
    out.append("  I2 gamma = 1 recovery: dK_bar(dK, 0.35, 1) - dK = %s" %
               _fmt(walker_equivalent_range(dk_t, R_1, 1.0) - dk_t))
    val = walker_equivalent_range(dk_t, R_1, GAMMA_WALKER)
    out.append("  I3 gamma = 0.5: dK_bar^2*(1-R) - dK^2 = %s" %
               _fmt(val * val * (1.0 - R_1) - dk_t * dk_t))
    rat = walker_vs_paris_ratio(dk_t, R_1, GAMMA_WALKER, C_PARIS, M_EXP)
    pred = (1.0 - R_1) ** (M_EXP * (GAMMA_WALKER - 1.0))
    out.append("  I4 walker/paris ratio = %s vs (1-R)^(m*(gamma-1)) = %s, "
               "residual %s" % (_fmt(rat), _fmt(pred), _fmt(rat - pred)))
    rf0 = forman_dadN(dk_t, R_1, KC_MPA, C_FORMAN, M_EXP)
    rp0 = C_PARIS * dk_t ** M_EXP
    predf = (C_FORMAN / C_PARIS) / ((1.0 - R_1) * KC_MPA - dk_t)
    out.append("  I5 forman/paris ratio = %s vs (C_F/C)/((1-R)K_c-dK) = %s, "
               "residual %s" % (_fmt(rf0 / rp0), _fmt(predf),
                                _fmt(rf0 / rp0 - predf)))
    rneg = walker_equivalent_range(dk_t, -1.0, GAMMA_WALKER)
    out.append("  I6 R = -1: dK_bar = dK/sqrt(2), residual %s" %
               _fmt(rneg - dk_t / math.sqrt(2.0)))
    rn04 = walker_equivalent_range(dk_t, -0.4, GAMMA_WALKER)
    r0 = walker_equivalent_range(dk_t, 0.0, GAMMA_WALKER)
    rp35 = walker_equivalent_range(dk_t, 0.35, GAMMA_WALKER)
    out.append("  I7 ordering dK_bar(R=-0.4) < dK_bar(R=0) < dK_bar(R=0.35): "
               "%s < %s < %s" % (_fmt(rn04), _fmt(r0), _fmt(rp35)))
    one = block_extension(1, SIGMA_MAX_1, R_1, A0_1, Y_FACTOR, "walker",
                          GAMMA_WALKER, KC_MPA, C_PARIS, C_FORMAN, M_EXP)
    rw_start = walker_dadN(one["dk_start_mpa"], R_1, GAMMA_WALKER, C_PARIS, M_EXP)
    rel = abs(one["extension_m"] - rw_start) / rw_start
    out.append("  I8 single-cycle block extension vs rate at start: rel "
               "residual %s (extension %s m/cycle, rate %s m/cycle)" %
               (_fmt(rel), _fmt(one["extension_m"]), _fmt(rw_start)))
    out.append("  I9 split-identity piecewise == block (walker): %s; "
               "(forman): %s" %
               (pw_same["a_final_m"] == single["a_final_m"],
                piecewise_block_extension(seg_same, A0_1, Y_FACTOR, "forman",
                                          GAMMA_WALKER, KC_MPA, C_PARIS,
                                          C_FORMAN, M_EXP)["a_final_m"] ==
                block_extension(N_1, SIGMA_MAX_1, R_1, A0_1, Y_FACTOR, "forman",
                                GAMMA_WALKER, KC_MPA, C_PARIS, C_FORMAN,
                                M_EXP)["a_final_m"]))
    dkbar_alt = k_max_t * (1.0 - R_1) ** GAMMA_WALKER
    out.append("  I10 dK_bar = Y*sigma_max*sqrt(pi*a)*(1-R)^gamma residual: "
               "%s (dK_bar %s vs %s)" %
               (_fmt(walker_equivalent_range(dk_t, R_1, GAMMA_WALKER) -
                     dkbar_alt),
                _fmt(walker_equivalent_range(dk_t, R_1, GAMMA_WALKER)),
                _fmt(dkbar_alt)))

    # ---- ValueError battery ----
    errs = [
        ("stress_intensity sigma=0", lambda: stress_intensity(0.0, 0.02, 1.0)),
        ("stress_intensity a<0", lambda: stress_intensity(100.0, -0.001, 1.0)),
        ("stress_intensity y=0", lambda: stress_intensity(100.0, 0.02, 0.0)),
        ("walker_equivalent_range dk=0",
         lambda: walker_equivalent_range(0.0, 0.35, 0.5)),
        ("walker_equivalent_range r=1",
         lambda: walker_equivalent_range(16.0, 1.0, 0.5)),
        ("walker_equivalent_range r<-1",
         lambda: walker_equivalent_range(16.0, -1.01, 0.5)),
        ("walker_equivalent_range gamma=0",
         lambda: walker_equivalent_range(16.0, 0.35, 0.0)),
        ("walker_equivalent_range gamma=1.5",
         lambda: walker_equivalent_range(16.0, 0.35, 1.5)),
        ("walker_dadN c=0", lambda: walker_dadN(16.0, 0.35, 0.5, 0.0, 3.0)),
        ("walker_dadN m=0", lambda: walker_dadN(16.0, 0.35, 0.5, 1e-11, 0.0)),
        ("forman_dadN kc=0", lambda: forman_dadN(16.0, 0.35, 0.0, 1e-9, 3.0)),
        ("forman_dadN c_forman<0",
         lambda: forman_dadN(16.0, 0.35, 100.0, -1e-9, 3.0)),
        ("forman_dadN dk=(1-R)Kc",
         lambda: forman_dadN(65.0, 0.35, 100.0, 1e-9, 3.0)),
        ("forman_dadN dk>(1-R)Kc",
         lambda: forman_dadN(70.0, 0.35, 100.0, 1e-9, 3.0)),
        ("block_extension cycles=0",
         lambda: block_extension(0, 100.0, 0.35, 0.02, 1.0, "walker", 0.5,
                                 100.0, 1e-11, 1e-9, 3.0)),
        ("block_extension model=paris",
         lambda: block_extension(100, 100.0, 0.35, 0.02, 1.0, "paris", 0.5,
                                 100.0, 1e-11, 1e-9, 3.0)),
        ("block_extension starts beyond singularity (forman)",
         lambda: block_extension(2000, 100.0, 0.35, 0.315, 1.0, "forman", 0.5,
                                 100.0, 1e-11, 1e-9, 3.0)),
        ("block_extension reaches singularity mid-block (forman)",
         lambda: block_extension(2000, 100.0, 0.35, 0.310, 1.0, "forman", 0.5,
                                 100.0, 1e-11, 1e-9, 3.0)),
        ("piecewise empty segments",
         lambda: piecewise_block_extension([], 0.02, 1.0, "walker", 0.5,
                                           100.0, 1e-11, 1e-9, 3.0)),
        ("piecewise segment r=1",
         lambda: piecewise_block_extension([(100, 100.0, 1.0)], 0.02, 1.0,
                                           "walker", 0.5, 100.0, 1e-11, 1e-9,
                                           3.0)),
    ]
    ok = 0
    for name, fn in errs:
        try:
            fn()
            out.append("  ERROR %s did NOT raise" % name)
        except ValueError:
            out.append("  ValueError ok: %s" % name)
            ok += 1
    out.append("ValueError battery: %d/%d raised as specified" % (ok, len(errs)))

    # ---- description draft gate ----
    desc = ("Use when you must compute the walker-forman-crack-growth rate of "
            "a mode I crack under a nonzero stress ratio in airframe "
            "structure: apply the walker-equation equivalent range "
            "dK_bar = dK/(1-R)^(1-gamma) with the material gamma exponent "
            "and the forman-equation rate da/dN = C_F*dK^m/((1-R)*K_c - dK) "
            "with the kc-limited denominator, then extend the crack over a "
            "stated cycle block at constant or piecewise stress ratio R. "
            "Produces the R-corrected rate table with the walker-equation "
            "and forman-equation rates at each station, the "
            "equivalent-delta-k correction, the kc-limited amplification of "
            "the rate over the zero-R baseline that grows as the peak "
            "stress-intensity factor approaches fracture toughness K_c, and "
            "the block extension feeding the follow-on life and "
            "inspection-interval assessment.")
    nchars = len(desc)
    nwords = len(desc.split())
    out.append("description draft: %d chars, %d words, em dash present: %s "
               "(limits 1000 chars, 148 words)" %
               (nchars, nwords, "\u2014" in desc))

    return "\n".join(out)


class TestWalkerFormanCrackGrowth(unittest.TestCase):
    """Worked-example anchors, identities and rejection battery of the
    walker-forman-crack-growth leaf (spec validation list)."""

    C = 1.0e-11
    M = 3.0
    G = 0.5
    KC = 100.0
    CF = 1.0e-9
    Y = 1.0

    def _assert_rel(self, actual, expected, tol, label=""):
        self.assertTrue(
            math.isclose(actual, expected, rel_tol=tol, abs_tol=0.0),
            "%s: actual %r vs expected %r (rel tol %g)" % (label, actual,
                                                           expected, tol))

    # ------------------------------------------------------------------
    # Step 1 checks: applied cycle and stress intensity (stress_intensity)
    # ------------------------------------------------------------------
    def test_stress_intensity_anchors(self):
        """Step 1 of the SKILL.md workflow, the stress_intensity evaluation
        of the applied range and peak stress intensity: the case 1 anchors
        dK = 65*sqrt(pi*0.02) and K_max = 100*sqrt(pi*0.02) and the case 2
        anchors at a0 = 0.05 m."""
        self._assert_rel(stress_intensity(65.0, 0.02, 1.0),
                         16.2930837851015, 1e-9, "dK0 case 1")
        self._assert_rel(stress_intensity(100.0, 0.02, 1.0),
                         25.06628274631, 1e-9, "K_max0 case 1")
        self._assert_rel(stress_intensity(196.0, 0.05, 1.0),
                         77.6812150330778, 1e-9, "dK0 case 2")
        self._assert_rel(stress_intensity(140.0, 0.05, 1.0),
                         55.4865821664841, 1e-9, "K_max0 case 2")
        self._assert_rel(stress_intensity(140.0, 0.05, 1.0) / self.KC,
                         0.554865821664841, 1e-9, "K_max/K_c case 2 start")

    def test_stress_intensity_construction_and_range_split(self):
        """Step 1 of the SKILL.md workflow: K = y*sigma*sqrt(pi*a) by
        construction, and dK = K_max*(1 - R) reproduces the applied range
        at R = 0.35 (dsigma = sigma_max*(1 - R) pins the cycle)."""
        for (sig, a, y) in ((65.0, 0.02, 1.0), (100.0, 0.02, 1.12),
                            (196.0, 0.05, 1.0), (140.0, 0.05, 1.0)):
            self._assert_rel(
                stress_intensity(sig, a, y),
                y * sig * math.sqrt(math.pi * a), 1e-15,
                "construction y*sigma*sqrt(pi*a)")
        kmax = stress_intensity(100.0, 0.02, 1.0)
        self._assert_rel(kmax * (1.0 - 0.35),
                         stress_intensity(65.0, 0.02, 1.0), 1e-12,
                         "dK = K_max*(1-R)")
        self._assert_rel(stress_intensity(100.0, 0.02, 1.0) / self.KC,
                         0.2506628274631, 1e-9, "K_max/K_c case 1 start")

    # ------------------------------------------------------------------
    # Step 2 checks: walker-equation equivalent range
    # ------------------------------------------------------------------
    def test_walker_equivalent_range_anchor_and_ordering(self):
        """Step 2 of the SKILL.md workflow, the walker-equation equivalent
        range dK_bar = dK/(1-R)^(1-gamma): the case 1 anchor value and the
        direction bound dK_bar(R=-0.4) < dK_bar(R=0) < dK_bar(R=0.35) at
        one fixed range (tensile mean accelerates, compressive mean
        retards the equivalent range against the zero-R baseline)."""
        dk = 16.2930837851015
        self._assert_rel(walker_equivalent_range(dk, 0.35, 0.5),
                         20.209083229248, 1e-9, "dK_bar0 case 1")
        rn = walker_equivalent_range(dk, -0.4, 0.5)
        r0 = walker_equivalent_range(dk, 0.0, 0.5)
        rp = walker_equivalent_range(dk, 0.35, 0.5)
        self._assert_rel(rn, 13.7701690836267, 1e-9, "dK_bar R=-0.4")
        self._assert_rel(r0, 16.2930837851015, 1e-9, "dK_bar R=0")
        self.assertLess(rn, r0)
        self.assertLess(r0, rp)

    def test_walker_range_recovery_limits_exact(self):
        """Step 2 of the SKILL.md workflow, the recovery limits: R = 0
        gives dK_bar = dK for any gamma and gamma = 1 gives dK_bar = dK
        for any R (no correction, the pure zero-R baseline). Both are
        exact by construction (1.0 powers), asserted with assertEqual."""
        dk = 16.2930837851015
        self.assertEqual(walker_equivalent_range(dk, 0.0, 0.5), dk)
        self.assertEqual(walker_equivalent_range(dk, 0.0, 1.0), dk)
        self.assertEqual(walker_equivalent_range(dk, 0.35, 1.0), dk)
        self.assertEqual(walker_equivalent_range(dk, -0.4, 1.0), dk)

    def test_walker_range_negative_r_sqrt2(self):
        """Step 2 of the SKILL.md workflow at fully reversed loading:
        R = -1 with gamma = 0.5 gives dK_bar = dK/2^(1-gamma) = dK/sqrt(2)
        exactly to roundoff."""
        dk = 16.2930837851015
        self._assert_rel(walker_equivalent_range(dk, -1.0, 0.5),
                         dk / math.sqrt(2.0), 1e-12, "R=-1 sqrt(2)")

    def test_walker_range_square_identity(self):
        """Step 2 of the SKILL.md workflow plus the step 7 identity check:
        the gamma = 0.5 square identity dK_bar^2*(1 - R) = dK^2 holds to
        roundoff at R = 0.35."""
        dk = 16.2930837851015
        dbar = walker_equivalent_range(dk, 0.35, 0.5)
        self._assert_rel(dbar * dbar * (1.0 - 0.35), dk * dk, 1e-9,
                         "square identity dK_bar^2*(1-R) = dK^2")

    def test_walker_range_equivalent_closed_form(self):
        """Step 2 of the SKILL.md workflow: the equivalent closed form
        dK_bar = Y*sigma_max*sqrt(pi*a)*(1-R)^gamma reproduces the range
        function to roundoff at the case 1 state."""
        dk = 16.2930837851015
        closed = stress_intensity(100.0, 0.02, 1.0) * (1.0 - 0.35) ** 0.5
        self._assert_rel(walker_equivalent_range(dk, 0.35, 0.5),
                         closed, 1e-12, "equivalent closed form")

    # ------------------------------------------------------------------
    # Step 3 checks: walker-equation and forman-equation rates and ratios
    # ------------------------------------------------------------------
    def test_walker_dadN_anchor_and_zero_r_paris_limit(self):
        """Step 3 of the SKILL.md workflow, the walker-equation rate
        da/dN = C*dK_bar^m: the case 1 anchor 8.25353196314273e-08 m/cycle
        at R = 0.35, and the R = 0 limit that collapses onto the zero-R
        Paris baseline C*dK^m = 4.32523663134402e-08 m/cycle."""
        dk = 16.2930837851015
        self._assert_rel(walker_dadN(dk, 0.35, 0.5, self.C, self.M),
                         8.25353196314273e-08, 1e-9, "walker rate R=0.35")
        r0 = walker_dadN(dk, 0.0, 0.5, self.C, self.M)
        self._assert_rel(r0, 4.32523663134402e-08, 1e-9, "walker rate R=0")
        self._assert_rel(r0, self.C * dk ** self.M, 1e-15,
                         "R=0 walker equals Paris baseline")

    def test_walker_dadN_negative_r_no_clamp(self):
        """Step 3 of the SKILL.md workflow at R = -0.4: the pinned
        formulas (no R = 0 clamp) give dK_bar = 13.7701690836267 and a
        walker rate below the zero-R baseline by the factor
        0.603681610520369 = 1.4^(-1.5) (compressive mean retards)."""
        dk = 16.2930837851015
        dbar = walker_equivalent_range(dk, -0.4, 0.5)
        self._assert_rel(dbar, 13.7701690836267, 1e-9, "dK_bar R=-0.4")
        rate = walker_dadN(dk, -0.4, 0.5, self.C, self.M)
        self._assert_rel(rate, self.C * 13.7701690836267 ** 3, 1e-9,
                         "walker rate at R=-0.4")
        baseline = self.C * dk ** self.M
        self._assert_rel(rate / baseline, 0.603681610520369, 1e-9,
                         "walker/paris at R=-0.4")
        self.assertLess(rate, baseline)

    def test_walker_vs_paris_ratio_identity(self):
        """Step 3 of the SKILL.md workflow, the walker-versus-paris ratio
        of the walker-equation arm over the zero-R baseline: the case 1
        anchor 1.90822668598782, equal to (1-R)^(m*(gamma-1)) =
        0.65^(-1.5) to roundoff and to the rate ratio by construction."""
        dk = 16.2930837851015
        rat = walker_vs_paris_ratio(dk, 0.35, 0.5, self.C, self.M)
        self._assert_rel(rat, 1.90822668598782, 1e-9, "walker/paris anchor")
        self._assert_rel(rat, (1.0 - 0.35) ** (self.M * (0.5 - 1.0)), 1e-12,
                         "(1-R)^(m*(gamma-1))")
        baseline = self.C * dk ** self.M
        self._assert_rel(rat,
                         walker_dadN(dk, 0.35, 0.5, self.C, self.M) /
                         baseline, 1e-15, "rate ratio")

    def test_forman_dadN_anchor(self):
        """Step 3 of the SKILL.md workflow, the forman-equation rate with
        the kc-limited denominator: the case 1 anchor
        8.88012825993901e-08 m/cycle at R = 0.35, above the walker rate
        because the K_c term is already felt at K_max/K_c = 0.25."""
        dk = 16.2930837851015
        self._assert_rel(forman_dadN(dk, 0.35, self.KC, self.CF, self.M),
                         8.88012825993901e-08, 1e-9, "forman rate R=0.35")
        wrate = walker_dadN(dk, 0.35, 0.5, self.C, self.M)
        self.assertGreater(forman_dadN(dk, 0.35, self.KC, self.CF, self.M),
                           wrate)

    def test_forman_dadN_zero_r_far_limit(self):
        """Step 3 of the SKILL.md workflow at R = 0: the far-limit value
        equals the zero-R Paris baseline times (1 - dK/K_c)^(-1) =
        1.194655... within 1e-6 relative (the example fit C_F = C*K_c
        collapses onto the Paris arm as dK/K_c approaches 0)."""
        dk = 16.2930837851015
        paris = self.C * dk ** self.M
        far = forman_dadN(dk, 0.0, self.KC, self.CF, self.M)
        self._assert_rel(far, paris / (1.0 - dk / self.KC), 1e-6,
                         "R=0 far limit (1-dK/Kc)^-1 scaling")

    def test_forman_dadN_linearity_and_monotonicity(self):
        """Step 3 of the SKILL.md workflow: the forman-equation arm is
        linear in C_F (doubling C_F doubles the rate) and strictly
        increasing in dK over (0, (1-R)*K_c) toward the singularity."""
        dk = 16.2930837851015
        base = forman_dadN(dk, 0.35, self.KC, self.CF, self.M)
        self._assert_rel(forman_dadN(dk, 0.35, self.KC, 2.0 * self.CF,
                                     self.M), 2.0 * base, 1e-12,
                         "linearity in C_F")
        rates = [forman_dadN(x, 0.35, self.KC, self.CF, self.M)
                 for x in (5.0, 15.0, 25.0, 35.0, 45.0, 55.0, 60.0)]
        for a, b in zip(rates, rates[1:]):
            self.assertLess(a, b)

    def test_forman_dadN_kc_proximity_growth(self):
        """Steps 3 and 6 of the SKILL.md workflow: near the kc-limited
        singularity the forman-equation rate runs far above the
        walker-equation arm, the terminal acceleration of the
        (1-R)*K_c - dK denominator (the fracture-state approach)."""
        dk = 64.1459350079117  # a = 0.31 m state, K_max/K_c = 0.98686
        self._assert_rel(forman_dadN(dk, 0.35, self.KC, self.CF, self.M),
                         3.09041283695431e-04, 1e-6, "forman near K_c")
        low = forman_dadN(10.0, 0.35, self.KC, self.CF, self.M)
        high = forman_dadN(dk, 0.35, self.KC, self.CF, self.M)
        self.assertGreater(high / low, 100.0)

    def test_forman_vs_paris_ratio_identity(self):
        """Step 3 of the SKILL.md workflow, the forman-versus-paris ratio:
        the case 1 anchor 2.05309651628924 = 100/48.7069162148985 =
        (C_F/C)/((1-R)*K_c - dK) to roundoff."""
        dk = 16.2930837851015
        rat = forman_vs_paris_ratio(dk, 0.35, self.KC, self.CF,
                                     self.C, self.M)
        self._assert_rel(rat, 2.05309651628924, 1e-9, "forman/paris anchor")
        pred = (self.CF / self.C) / ((1.0 - 0.35) * self.KC - dk)
        self._assert_rel(rat, pred, 1e-12, "(C_F/C)/((1-R)Kc-dK)")
        baseline = self.C * dk ** self.M
        self._assert_rel(rat, forman_dadN(dk, 0.35, self.KC, self.CF,
                                          self.M) / baseline, 1e-15,
                         "rate ratio")

    def test_near_critical_sweep_ratios_monotone(self):
        """Step 3 of the SKILL.md workflow plus the step 6 kc-limited
        sweep: the forman-versus-paris ratio at a = 0.02/0.15/0.25/0.30/
        0.31 m (R = 0.35, sigma_max = 100) reads 2.05309651628924 /
        4.90687911331886 / 13.5221935821267 / 52.7104270342384 /
        117.087108037864, monotone increasing, and equals
        (1/0.65)/(1 - K_max/K_c) at the last station."""
        dk = [stress_intensity(65.0, a, 1.0) for a in
              (0.02, 0.15, 0.25, 0.30, 0.31)]
        expected = [2.05309651628924, 4.90687911331886, 13.5221935821267,
                    52.7104270342384, 117.087108037864]
        ratios = []
        for x, e in zip(dk, expected):
            rat = forman_vs_paris_ratio(x, 0.35, self.KC, self.CF,
                                         self.C, self.M)
            self._assert_rel(rat, e, 1e-6, "sweep ratio")
            ratios.append(rat)
        for a, b in zip(ratios, ratios[1:]):
            self.assertLess(a, b)
        kmax_kc = stress_intensity(100.0, 0.31, 1.0) / self.KC
        self._assert_rel(kmax_kc, 0.986860538583257, 1e-9, "K_max/K_c 0.31")
        self._assert_rel(ratios[-1], (1.0 / 0.65) / (1.0 - kmax_kc), 1e-9,
                         "ratio = (1/(1-R))/(1-Kmax/Kc)")

    # ------------------------------------------------------------------
    # Step 4 checks: block-extension march and the R-corrected rate table
    # ------------------------------------------------------------------
    def test_block_walker_case1_outputs(self):
        """Step 4 of the SKILL.md workflow, the walker-equation block
        march over the 2000-cycle case 1 block: a_final =
        0.0201660975842774 m, extension 1.66097584277439e-04 m, rates
        8.25353196314273e-08 to 8.3565620180878e-08 m/cycle as dK grows
        from 16.2930837851015 to 16.3605999429847 MPa*sqrt(m)."""
        res = block_extension(2000, 100.0, 0.35, 0.02, 1.0, "walker", 0.5,
                              100.0, 1e-11, 1e-9, 3.0)
        self.assertEqual(res["a0_m"], 0.02)
        self._assert_rel(res["a_final_m"], 0.0201660975842774, 1e-9,
                         "walker a_final case 1")
        self._assert_rel(res["extension_m"], 1.66097584277439e-04, 1e-9,
                         "walker extension case 1")
        self._assert_rel(res["rate_start"], 8.25353196314273e-08, 1e-9,
                         "walker rate_start")
        self._assert_rel(res["rate_final"], 8.3565620180878e-08, 1e-9,
                         "walker rate_final")
        self._assert_rel(res["dk_start_mpa"], 16.2930837851015, 1e-9,
                         "dk_start")
        self._assert_rel(res["dk_final_mpa"], 16.3605999429847, 1e-9,
                         "dk_final")
        self._assert_rel(res["dk_bar_start_mpa"], 20.209083229248, 1e-9,
                         "dk_bar_start")

    def test_block_forman_case1_outputs(self):
        """Step 4 of the SKILL.md workflow, the forman-equation block
        march over the same 2000-cycle case 1 block: a_final =
        0.0201789260510205 m, extension 1.7892605102051e-04 m, rate
        8.88012825993901e-08 to 9.01301724331156e-08 m/cycle. Far from
        K_c (K_max/K_c = 0.25) the two arms differ only by the R-ratio
        correction shape."""
        res = block_extension(2000, 100.0, 0.35, 0.02, 1.0, "forman", 0.5,
                              100.0, 1e-11, 1e-9, 3.0)
        self._assert_rel(res["a_final_m"], 0.0201789260510205, 1e-9,
                         "forman a_final case 1")
        self._assert_rel(res["extension_m"], 1.7892605102051e-04, 1e-9,
                         "forman extension case 1")
        self._assert_rel(res["rate_start"], 8.88012825993901e-08, 1e-9,
                         "forman rate_start")
        self._assert_rel(res["rate_final"], 9.01301724331156e-08, 1e-9,
                         "forman rate_final")
        self._assert_rel(res["dk_final_mpa"], 16.365802933883, 1e-9,
                         "dk_final case 1 forman")
        walker_ext = 1.66097584277439e-04
        self.assertGreater(res["extension_m"], walker_ext)

    def test_block_rows_case1(self):
        """Step 4 of the SKILL.md workflow, the R-corrected rate table of
        the case 1 walker block: five rows at cycles 0, N/4, N/2, 3N/4, N
        that are monotone in a and rate, with the cycle-1000 row a =
        0.0200827912199018 m, dK = 16.3267720644985, dK_bar =
        20.2508683971858, walker rate 8.30483396217601e-08 m/cycle and
        the forman rate 8.94150945394409e-08 evaluated at the station."""
        res = block_extension(2000, 100.0, 0.35, 0.02, 1.0, "walker", 0.5,
                              100.0, 1e-11, 1e-9, 3.0)
        rows = res["rows"]
        self.assertEqual(len(rows), 5)
        self.assertEqual([r["cycle"] for r in rows],
                         [0.0, 500.0, 1000.0, 1500.0, 2000.0])
        row1000 = rows[2]
        self._assert_rel(row1000["a_m"], 0.0200827912199018, 1e-9,
                         "row cycle-1000 a")
        self._assert_rel(row1000["dk_mpa"], 16.3267720644985, 1e-9,
                         "row cycle-1000 dK")
        self._assert_rel(row1000["dk_bar_mpa"], 20.2508683971858, 1e-9,
                         "row cycle-1000 dK_bar")
        self._assert_rel(row1000["rate"], 8.30483396217601e-08, 1e-9,
                         "row cycle-1000 walker rate")
        self._assert_rel(forman_dadN(row1000["dk_mpa"], 0.35, self.KC,
                                     self.CF, self.M),
                         8.94150945394409e-08, 1e-9, "station forman rate")
        for r0, r1 in zip(rows, rows[1:]):
            self.assertLess(r0["a_m"], r1["a_m"])
            self.assertLess(r0["rate"], r1["rate"])

    def test_block_walker_case2_outputs(self):
        """Step 4 of the SKILL.md workflow, the walker-equation block
        march over the 2000-cycle case 2 block at R = -0.4: a_final =
        0.0561787832844155 m, extension 6.17878328441552e-03 m, rate
        2.82980152371443e-06 to 3.37022940273813e-06 m/cycle with the
        equivalent range dK_bar0 = 65.6526093976865 below dK0 (the
        compressive mean pulls the equivalent range down)."""
        res = block_extension(2000, 140.0, -0.4, 0.05, 1.0, "walker", 0.5,
                              100.0, 1e-11, 1e-9, 3.0)
        self._assert_rel(res["a_final_m"], 0.0561787832844155, 1e-9,
                         "walker a_final case 2")
        self._assert_rel(res["extension_m"], 6.17878328441552e-03, 1e-9,
                         "walker extension case 2")
        self._assert_rel(res["rate_start"], 2.82980152371443e-06, 1e-9,
                         "walker rate_start case 2")
        self._assert_rel(res["rate_final"], 3.37022940273813e-06, 1e-9,
                         "walker rate_final case 2")
        self._assert_rel(res["dk_final_mpa"], 82.3411962703766, 1e-9,
                         "dk_final case 2 walker")
        self._assert_rel(res["dk_bar_start_mpa"], 65.6526093976865, 1e-9,
                         "dk_bar_start case 2")
        self.assertLess(res["dk_bar_start_mpa"], res["dk_start_mpa"])

    def test_block_case2_start_rates(self):
        """Step 3 of the SKILL.md workflow at the case 2 block start:
        Paris baseline 4.6875728436968e-06, walker 2.82980152371443e-06
        (below the baseline, ratio 0.603681610520369 = 1.4^(-1.5)) and
        forman 7.52192592680504e-06 m/cycle (above the baseline, ratio
        1.60465259476863: the K_c term amplifies even at negative R)."""
        dk = 77.6812150330778
        baseline = self.C * dk ** self.M
        self._assert_rel(baseline, 4.6875728436968e-06, 1e-9, "paris")
        self._assert_rel(walker_dadN(dk, -0.4, 0.5, self.C, self.M),
                         2.82980152371443e-06, 1e-9, "walker case 2")
        self._assert_rel(forman_dadN(dk, -0.4, self.KC, self.CF, self.M),
                         7.52192592680504e-06, 1e-9, "forman case 2")
        self._assert_rel(walker_dadN(dk, -0.4, 0.5, self.C, self.M) /
                         baseline, 0.603681610520369, 1e-9,
                         "walker/paris case 2")
        self._assert_rel(forman_dadN(dk, -0.4, self.KC, self.CF, self.M) /
                         baseline, 1.60465259476863, 1e-9,
                         "forman/paris case 2")

    def test_block_forman_case2_outputs(self):
        """Step 4 of the SKILL.md workflow, the forman-equation block
        march over the case 2 block: a_final = 0.0727588016051557 m,
        extension 2.27588016051557e-02 m, rate 7.52192592680504e-06 to
        1.77749967229633e-05 m/cycle (a 2.36x acceleration across the
        block); the kc-limited model grows the block 3.68 times farther
        than the walker model, the damage tolerance life driver."""
        res = block_extension(2000, 140.0, -0.4, 0.05, 1.0, "forman", 0.5,
                              100.0, 1e-11, 1e-9, 3.0)
        self._assert_rel(res["a_final_m"], 0.0727588016051557, 1e-9,
                         "forman a_final case 2")
        self._assert_rel(res["extension_m"], 2.27588016051557e-02, 1e-9,
                         "forman extension case 2")
        self._assert_rel(res["rate_start"], 7.52192592680504e-06, 1e-9,
                         "forman rate_start case 2")
        self._assert_rel(res["rate_final"], 1.77749967229633e-05, 1e-9,
                         "forman rate_final case 2")
        self._assert_rel(res["dk_final_mpa"], 93.7073758781297, 1e-9,
                         "dk_final case 2 forman")
        self.assertGreater(res["extension_m"], 3.6 * 6.17878328441552e-03)

    def test_block_rows_case2_forman(self):
        """Step 4 of the SKILL.md workflow, the R-corrected rate table of
        the case 2 forman block: the cycle-1000 row a = 0.0589904442124411
        m, dK = 84.376564969541, forman rate 1.07996011796121e-05 m/cycle;
        the forman-versus-paris ratio climbs 1.60 to 2.16 across the rows
        while the walker-versus-paris ratio stays pinned at 0.6036816
        (the mean-stress correction is a constant factor of the range,
        the kc-limited correction grows with the crack)."""
        res = block_extension(2000, 140.0, -0.4, 0.05, 1.0, "forman", 0.5,
                              100.0, 1e-11, 1e-9, 3.0)
        rows = res["rows"]
        self.assertEqual(len(rows), 5)
        row1000 = rows[2]
        self._assert_rel(row1000["a_m"], 0.0589904442124411, 1e-9,
                         "row cycle-1000 a case 2")
        self._assert_rel(row1000["dk_mpa"], 84.376564969541, 1e-9,
                         "row cycle-1000 dK case 2")
        self._assert_rel(row1000["rate"], 1.07996011796121e-05, 1e-9,
                         "row cycle-1000 forman rate case 2")
        fpr = []
        wpr = []
        for row in rows:
            dk = row["dk_mpa"]
            baseline = self.C * dk ** self.M
            fpr.append(forman_dadN(dk, -0.4, self.KC, self.CF, self.M) /
                       baseline)
            wpr.append(walker_dadN(dk, -0.4, 0.5, self.C, self.M) /
                       baseline)
        for a, b in zip(fpr, fpr[1:]):
            self.assertLess(a, b)
        self._assert_rel(fpr[0], 1.60465259476863, 1e-9, "fpr row 0")
        self._assert_rel(fpr[-1], 2.160171e+00, 1e-4, "fpr final row")
        for p in wpr:
            self._assert_rel(p, 0.603681610520369, 1e-12,
                             "walker/paris pinned")
        for r0, r1 in zip(rows, rows[1:]):
            self.assertLess(r0["a_m"], r1["a_m"])

    def test_block_single_cycle_march_consistency(self):
        """Step 4 of the SKILL.md workflow plus the step 7 identity: a
        one-cycle block extends the crack by exactly the rate at the
        start up to floating-point subtraction rounding (relative
        residual 7.06e-12), the forward-Euler single substep."""
        res = block_extension(1, 100.0, 0.35, 0.02, 1.0, "walker", 0.5,
                              100.0, 1e-11, 1e-9, 3.0)
        rate_start = walker_dadN(res["dk_start_mpa"], 0.35, 0.5, self.C,
                                 self.M)
        self._assert_rel(res["extension_m"], 8.25353196308443e-08, 1e-9,
                         "single-cycle extension")
        self._assert_rel(res["extension_m"], rate_start, 1e-9,
                         "extension vs rate at start")

    def test_block_doubling_cycles_superlinear(self):
        """Step 4 of the SKILL.md workflow: doubling the cycles more than
        doubles the extension for both models because dK is re-evaluated
        from the growing crack at every substep (the march is never run
        at a constant range)."""
        for model in ("walker", "forman"):
            e1000 = block_extension(1000, 100.0, 0.35, 0.02, 1.0, model,
                                    0.5, 100.0, 1e-11, 1e-9, 3.0)
            e2000 = block_extension(2000, 100.0, 0.35, 0.02, 1.0, model,
                                    0.5, 100.0, 1e-11, 1e-9, 3.0)
            self.assertGreater(e2000["extension_m"],
                               2.0 * e1000["extension_m"])
        e1000w = block_extension(1000, 100.0, 0.35, 0.02, 1.0, "walker",
                                 0.5, 100.0, 1e-11, 1e-9, 3.0)
        self._assert_rel(e1000w["extension_m"], 8.2791219901783e-05, 1e-9,
                         "walker 1000-cycle extension")

    # ------------------------------------------------------------------
    # Step 5 checks: piecewise-R block extension
    # ------------------------------------------------------------------
    def test_piecewise_split_identity_bit_for_bit(self):
        """Step 5 of the SKILL.md workflow, the split identity: two equal
        1000-cycle segments at R = 0.35 reproduce the single 2000-cycle
        block bit for bit under both models (round-trip exact by
        construction, asserted with assertEqual)."""
        for model in ("walker", "forman"):
            single = block_extension(2000, 100.0, 0.35, 0.02, 1.0, model,
                                     0.5, 100.0, 1e-11, 1e-9, 3.0)
            pw = piecewise_block_extension([(1000, 100.0, 0.35),
                                            (1000, 100.0, 0.35)],
                                           0.02, 1.0, model, 0.5, 100.0,
                                           1e-11, 1e-9, 3.0)
            self.assertEqual(pw["a_final_m"], single["a_final_m"])
            self.assertEqual(pw["extension_m"], single["extension_m"])
            self.assertEqual(pw["a0_m"], 0.02)
            self.assertEqual(len(pw["segments"]), 2)
            seg1, seg2 = pw["segments"]
            self.assertEqual(seg1["a_final_m"], seg2["a0_m"])
            self.assertEqual(seg1["cycles"], 1000)
            self.assertEqual(seg2["cycles"], 1000)
            for key in ("r", "sigma_max_mpa", "a0_m", "a_final_m",
                        "extension_m", "rate_start", "rate_final"):
                self.assertIn(key, seg1)

    def test_piecewise_mixed_r_walker(self):
        """Step 5 of the SKILL.md workflow, the piecewise-R walker block:
        1000 cycles at R = 0.35 then 1000 cycles at R = 0.6 at fixed
        sigma_max = 100 MPa gives a_final = 0.0201229426364184 m with
        segment extensions 8.2791219901783e-05 and 4.01514165165699e-05
        m; raising R cuts dsigma and the second-segment rate falls below
        the first (the block story is the R-corrected rate per regime)."""
        pw = piecewise_block_extension([(1000, 100.0, 0.35),
                                        (1000, 100.0, 0.6)],
                                       0.02, 1.0, "walker", 0.5, 100.0,
                                       1e-11, 1e-9, 3.0)
        self._assert_rel(pw["a_final_m"], 0.0201229426364184, 1e-9,
                         "piecewise walker a_final")
        seg1, seg2 = pw["segments"]
        self._assert_rel(seg1["extension_m"], 8.2791219901783e-05, 1e-9,
                         "segment 1 extension")
        self._assert_rel(seg2["extension_m"], 4.01514165165699e-05, 1e-9,
                         "segment 2 extension")
        self._assert_rel(seg1["rate_start"], 8.25353196314273e-08, 1e-9,
                         "segment 1 rate_start")
        self._assert_rel(seg2["rate_start"], 4.00913708215703e-08, 1e-9,
                         "segment 2 rate_start")
        self.assertLess(seg2["rate_start"], seg1["rate_start"])

    def test_piecewise_mixed_r_forman(self):
        """Step 5 of the SKILL.md workflow, the piecewise-R forman block:
        the same two-segment block gives a_final = 0.0201230576354857 m
        with total extension 1.23057635485715e-04 m."""
        pw = piecewise_block_extension([(1000, 100.0, 0.35),
                                        (1000, 100.0, 0.6)],
                                       0.02, 1.0, "forman", 0.5, 100.0,
                                       1e-11, 1e-9, 3.0)
        self._assert_rel(pw["a_final_m"], 0.0201230576354857, 1e-9,
                         "piecewise forman a_final")
        self._assert_rel(pw["extension_m"], 1.23057635485715e-04, 1e-9,
                         "piecewise forman total extension")
        self._assert_rel(pw["a_final_m"] - 0.02, pw["extension_m"], 1e-15,
                         "extension consistency")

    # ------------------------------------------------------------------
    # Step 6 checks: the kc-limited singularity guard and rejections
    # ------------------------------------------------------------------
    def test_valueerror_function_domains(self):
        """Step 6 of the SKILL.md workflow plus the domain checks of
        steps 1 to 3: every non-physical input class raises ValueError
        (stress_intensity sigma/a/y, walker_equivalent_range dk/r/gamma,
        walker_dadN c/m, forman_dadN kc/c_forman/m and dK at or beyond
        the (1-R)*K_c singularity)."""
        cases = [
            lambda: stress_intensity(0.0, 0.02, 1.0),
            lambda: stress_intensity(100.0, -0.001, 1.0),
            lambda: stress_intensity(100.0, 0.02, 0.0),
            lambda: walker_equivalent_range(0.0, 0.35, 0.5),
            lambda: walker_equivalent_range(16.0, 1.0, 0.5),
            lambda: walker_equivalent_range(16.0, -1.01, 0.5),
            lambda: walker_equivalent_range(16.0, 0.35, 0.0),
            lambda: walker_equivalent_range(16.0, 0.35, 1.5),
            lambda: walker_dadN(16.0, 0.35, 0.5, 0.0, 3.0),
            lambda: walker_dadN(16.0, 0.35, 0.5, 1e-11, 0.0),
            lambda: forman_dadN(16.0, 0.35, 0.0, 1e-9, 3.0),
            lambda: forman_dadN(16.0, 0.35, 100.0, -1e-9, 3.0),
            lambda: forman_dadN(16.0, 0.35, 100.0, 1e-9, 0.0),
            lambda: forman_dadN(65.0, 0.35, 100.0, 1e-9, 3.0),
            lambda: forman_dadN(70.0, 0.35, 100.0, 1e-9, 3.0),
        ]
        for fn in cases:
            with self.assertRaises(ValueError):
                fn()

    def test_valueerror_block_and_piecewise(self):
        """Step 6 of the SKILL.md workflow, the kc-limited singularity
        guard of the block march: a forman block starting at or beyond
        the singularity, a forman block reaching the singularity
        mid-block (the error states the cycle at which peak K reaches
        K_c), an invalid model name, non-positive or non-integer cycle
        counts, and the piecewise guards (empty segments, a segment at
        r = 1)."""
        with self.assertRaises(ValueError):
            block_extension(2000, 100.0, 0.35, 0.315, 1.0, "forman", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            block_extension(2000, 100.0, 0.35, 0.32, 1.0, "forman", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaisesRegex(ValueError, "cycle"):
            block_extension(2000, 100.0, 0.35, 0.31, 1.0, "forman", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            block_extension(0, 100.0, 0.35, 0.02, 1.0, "walker", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            block_extension(2000.5, 100.0, 0.35, 0.02, 1.0, "walker", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            block_extension(100, 100.0, 0.35, 0.02, 1.0, "paris", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            block_extension(100, 0.0, 0.35, 0.02, 1.0, "walker", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            block_extension(100, 100.0, 0.35, 0.0, 1.0, "walker", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            block_extension(100, 100.0, 1.0, 0.02, 1.0, "walker", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            block_extension(100, 100.0, 0.35, 0.02, 0.0, "walker", 0.5,
                            100.0, 1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            piecewise_block_extension([], 0.02, 1.0, "walker", 0.5, 100.0,
                                      1e-11, 1e-9, 3.0)
        with self.assertRaises(ValueError):
            piecewise_block_extension([(100, 100.0, 1.0)], 0.02, 1.0,
                                      "walker", 0.5, 100.0, 1e-11, 1e-9,
                                      3.0)

    def test_walker_model_marches_past_kc_region(self):
        """Step 6 fence of the SKILL.md workflow: the walker-equation arm
        carries no K_c term, so a walker block starting beyond the forman
        singularity region (a0 = 0.32 m, where dK0 > (1-R)*K_c) still
        marches to a result; only the forman-equation arm raises."""
        res = block_extension(200, 100.0, 0.35, 0.32, 1.0, "walker", 0.5,
                              100.0, 1e-11, 1e-9, 3.0)
        self.assertGreater(res["a_final_m"], 0.32)

    # ------------------------------------------------------------------
    # Step 7 checks: verification, determinism and purity
    # ------------------------------------------------------------------
    def test_determinism_sha256_canonical_dump(self):
        """Step 7 of the SKILL.md workflow, the verification step: two
        identical full runs produce identical bits, and the sha256 of the
        canonical dump equals the wave-45 spec anchor digest
        791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62
        (bitwise identical under both /usr/bin/python3 3.9.6 and the
        pyenv 3.13.12 hook interpreter)."""
        dump1 = _canonical_dump()
        dump2 = _canonical_dump()
        self.assertEqual(dump1, dump2)
        digest = hashlib.sha256(dump1.encode("utf-8")).hexdigest()
        self.assertEqual(digest, SHA256_ANCHOR)
        self.assertIn("ValueError battery: 20/20 raised as specified",
                      dump1)
        self.assertIn("description draft: 794 chars, 112 words, "
                      "em dash present: False", dump1)

    def test_logic_module_purity(self):
        """Step 7 of the SKILL.md workflow: the logic module imports only
        math (no numpy, no random, no network), so the R-corrected model
        stays deterministic and offline."""
        here = os.path.dirname(os.path.abspath(__file__))
        logic_path = os.path.join(here, "walker_forman_crack_growth_logic.py")
        imports = []
        with open(logic_path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")):
                    imports.append(stripped)
        self.assertEqual(imports, ["import math"])


if __name__ == "__main__":
    unittest.main()
