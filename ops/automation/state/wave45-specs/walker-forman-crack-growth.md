# Wave-45 leaf spec: walker-forman-crack-growth (structures, damage-tolerance pack)

- Path: skills/structures/damage-tolerance/walker-forman-crack-growth/
- Pack: damage-tolerance (4 leaves present at prep: bird-strike,
  crack-growth, residual-strength, widespread-fatigue-damage;
  walker-forman-crack-growth is a wave-45 addition of the family, wave-45
  GO candidate 2 re-verified GO). Claim fences (quoted from the sibling
  frontmatter and bodies at prep; no sibling computes a stress-ratio-
  corrected da/dN rate, a Walker equivalent range or a K_c-limited rate):
  - crack-growth (this pack) is the R = 0 constant-amplitude Paris arm:
    its description opens "Use when you must calculate fatigue crack growth
    for damage-tolerant structure: estimate the mode I stress intensity
    factor at a crack, apply the Paris law crack growth rate, and project
    the cycles to grow the crack from the initial detectable size to the
    critical size", and its domain quick reference pins the Paris law and
    its unit convention: "The Paris law da/dN = C * (dK)^m relates the
    crack growth rate to the stress intensity range; C and m are material
    constants fitted from da/dN testing", "sigma and dK in MPa /
    MPa*sqrt(m), crack sizes in meters, Paris C in (m/cycle)*
    (MPa*sqrt(m))^-m, da/dN in m/cycle. Anchor: C=1e-11, m=3, dK=20 gives
    da/dN = 8e-8 m/cycle". Its whole workflow (steps 1-5: stress
    intensity, Paris rate, per-cycle extension, cycles to grow) never
    takes a stress ratio R, never corrects the range for mean stress and
    has no K_c-limited rate term anywhere in its text or tags (its tags:
    crack-growth, paris-law, stress-intensity, damage-tolerance,
    fatigue-crack, fracture-mechanics). Its unit convention and Paris
    anchor (C = 1e-11, m = 3) are inherited here so the new leaf's R = 0,
    gamma = 1 limit reproduces the sibling's own worked numbers. crack-
    growth sits in the FAR-25.571 damage tolerance context (its body
    lines 40-41), the same certification frame this leaf inherits.
  - residual-strength (this pack) owns the fracture endpoint at K_c: its
    description opens "Use when you must compute the residual strength of
    a cracked structure for a damage tolerance assessment: derive the
    residual strength from fracture toughness and crack length, find the
    critical crack length at which the applied stress reaches Kc", and its
    body states "Fracture occurs when K reaches the material fracture
    toughness Kc; the crack length at which the applied stress drives K to
    Kc is the critical crack length". K_c enters THIS leaf only as the
    material constant inside the Forman rate denominator; critical crack
    length, residual strength and fracture margins stay with residual-
    strength.
  - widespread-fatigue-damage (this pack) owns the MSD/MED WFD screening
    per FAR 25.571(b)/(c): "classify multiple site damage (MSD) cracks in
    adjacent fastener holes and multiple element damage (MED) in adjacent
    load paths, run the WFD susceptibility screening". No rate content.
  - bird-strike (this pack) owns the certification impact energy vein and
    its residual_strength_fraction is the post-impact knock-down of a
    struck component, not a growing-crack rate.
  - goodman-diagram (fatigue pack, cross-pack fence) is the S-N infinite-
    life mean-stress correction, a different domain: its description opens
    "Use when a fluctuating load case must be checked against a mean-
    stress fatigue limit or a Haigh diagram / fatigue diagram comparison
    is needed", and its quick reference defines "stress ratio R =
    Smin / Smax" and the endurance limit Se as the fully reversed (R = -1)
    infinite-life amplitude. Goodman/Gerber/Soderberg correct the
    allowable stress AMPLITUDE of the stress-life (S-N) domain; Walker and
    Forman correct the da/dN RATE of the crack-growth (LEFM) domain.
    stress-life-curve hands mean-stress corrections to goodman-diagram and
    strain-life-fatigue assumes fully reversed loading; no fatigue leaf
    touches da/dN.
  - Whole-tree greps at prep (real runs): "forman", "walker" and "r-ratio"
    over the skills/ SKILL.md bodies give zero hits in skills/structures;
    the only walker hits in the whole tree are
    space-systems/orbit-mechanics/walker-delta-constellation, an unrelated
    t/p/f constellation geometry leaf (its corpus tasks
    w36-walker-delta-constellation-1/2 carry no crack-growth tokens, so no
    theft in either direction). In eval/hit1-corpus.yaml the tokens
    forman, walker, r-ratio-correction and mean-stress-crack-growth each
    match 0 existing tasks. GENUINE STRUCTURES gap (fresh probe): no leaf
    computes the stress-ratio-affected da/dN rate, the Walker equivalent
    range or the Forman K_c-limited rate; crack-growth is the R = 0 Paris
    arm by claim, residual-strength is the K_c fracture endpoint by claim.
- Standards id: far-25, cs-25 (reference-only, both present in
  standards-map.yaml at repo root, lines 16 and 27, gated false, matching
  the damage-tolerance siblings crack-growth, residual-strength,
  widespread-fatigue-damage and bird-strike; the FAR 25.571 damage
  tolerance basis sets the certification context of the rate and
  extension results, summary paraphrase only, never standard text).
  Ledger Standard: far-25, cs-25.
- Family: structures

## Claim

Compute the stress-ratio-affected (mean-stress and toughness-limited)
fatigue crack growth rate of a mode I through-thickness crack under
constant-amplitude cyclic loading: evaluate the Walker equivalent stress
intensity range dK_bar = dK/(1 - R)^(1 - gamma) from the applied range
dK = Y*dsigma*sqrt(pi*a) with dsigma = sigma_max*(1 - R), the material
Walker exponent gamma (0.5 for the 2024-T3 / 7075-T6 aluminum anchor
data), and the Walker rate da/dN = C*dK_bar^m; evaluate the Forman rate
da/dN = C_F*dK^m/((1 - R)*K_c - dK) whose denominator shrinks as the peak
stress intensity approaches the fracture toughness K_c, producing the
terminal acceleration the Paris arm cannot show; project the crack
extension over a stated cycle block (2000 cycles in the worked examples)
at a constant or piecewise stress ratio R by a per-cycle Euler march that
re-evaluates dK from the growing crack at every substep, and report the
R-corrected rate table (cycle, a, dK, dK_bar, rate per model), the
walker-versus-Paris and forman-versus-Paris rate ratios (the R = 0,
gamma = 1 Paris baseline C*dK^m of crack-growth, used here only as the
comparison denominator, never as a growth projection), and the block
extension that feeds the follow-on damage tolerance life and inspection-
interval assessment in the FAR-25.571 context. Produces dK_bar, the
walker_dadN and forman_dadN rates, the two model-vs-baseline ratios, the
station rate table, the block extension (walker and forman models) and
the piecewise-R block extension, with the Forman arm raising a
deterministic guard when the marching crack reaches the K_c singularity
(dK = (1 - R)*K_c, the fracture state). Does NOT do: the Paris constant-
amplitude stress intensity / da/dN / cycles-to-critical projection itself
or any result that treats R as zero (crack-growth, which also owns the
Y*sigma*sqrt(pi*a) evaluation as a delivered product; this leaf reuses
the form as an input to the range correction only); residual strength,
critical crack length, fracture margins or K_c failure checks
(residual-strength); WFD/MSD/MED screening and supplemental inspection
flags (widespread-fatigue-damage); bird impact energy and post-impact
residual strength fraction (bird-strike); S-N infinite-life mean-stress
allowable amplitudes, Goodman/Gerber/Soderberg lines or the Haigh diagram
(goodman-diagram, fatigue pack, stress-life domain); da/dN threshold and
crack-closure (Elber) corrections, spectrum cycle counting, variable-
amplitude load sequences beyond piecewise-constant R segments, or da/dN
test-data curve fitting. Scope: mode I through-thickness crack in a wide
panel (geometry factor Y constant), single half-crack length a growing
from a0, far-field tension with constant amplitude and constant R within
a segment, R in [-1, 1), gamma in (0, 1], linear-elastic small-scale-
yielding conditions, material constants C, m, C_F, gamma and K_c given
(no fitting). Units (single convention, inherited from the crack-growth
sibling): sigma in MPa, a in meters, K, dK and K_c in MPa*sqrt(m),
C in (m/cycle)*(MPa*sqrt(m))^-m, C_F in (m/cycle)*(MPa*sqrt(m))^(1 - m),
da/dN in m/cycle. Deterministic, pure stdlib.

## Model (implement exactly)

Pure stdlib, math only. All functions take plain floats; the R-corrected
model needs no module-level material constants (every constant is an
argument), mirroring the sibling logic module style. The stress ratio
R = sigma_min/sigma_max = K_min/K_max is passed directly; the applied
cycle is pinned by sigma_max and R with sigma_min = R*sigma_max and
dsigma = sigma_max*(1 - R). Negative R is handled by the pinned formulas
as written, with no R = 0 clamping (an R = 0 lower clamp is a stated
extension, not this contract); the Walker and Forman arms both stay
defined down to R = -1 and the equivalent range falls below dK under
compressive mean stress.

Defining relations (pin these exactly; every function derives from them):
- Mode I stress intensity: K = Y*sigma*sqrt(pi*a) in MPa*sqrt(m) with
  sigma in MPa and a in meters (crack-growth's form, reused as the range
  input only). K_max = Y*sigma_max*sqrt(pi*a) and
  dK(a) = Y*dsigma*sqrt(pi*a) = K_max*(1 - R).
- Walker equivalent range (Walker 1970, ASTM STP 462):
  dK_bar = dK/(1 - R)^(1 - gamma). Equivalent closed form
  dK_bar = Y*sigma_max*sqrt(pi*a)*(1 - R)^gamma holds to roundoff
  (anchor residual -3.5527136788005e-15). Recovery limits: R = 0 gives
  dK_bar = dK for any gamma; gamma = 1 gives dK_bar = dK for any R (no
  correction, pure Paris); at R = -1, dK_bar = dK/2^(1 - gamma)
  (dK/sqrt(2) at gamma = 0.5, exact).
- Walker rate: da/dN = C*dK_bar^m in m/cycle.
- Forman rate (Forman, Kearney, Engle 1967, ASME Journal of Basic
  Engineering): da/dN = C_F*dK^m/((1 - R)*K_c - dK). The denominator
  vanishes at dK = (1 - R)*K_c, equivalent to K_max = K_c (dK =
  K_max*(1 - R)), the fracture state owned by residual-strength; the arm
  is undefined at and beyond that point and raises ValueError. The
  terminal acceleration is the growth of the rate as the denominator
  approaches zero; the forman-versus-paris ratio
  (C_F/C)/((1 - R)*K_c - dK) diverges like
  (1/(1 - R))/(1 - K_max/K_c) as K_max/K_c approaches 1.
- Paris baseline (comparison denominator only, never a projection
  deliverable): C*dK^m, the R = 0, K_c-infinite limit of both arms.
- Material constants: C and m are the crack-growth Paris arm constants of
  the sibling unit convention (anchor C = 1e-11, m = 3, which reproduces
  the sibling's own 8e-8 m/cycle at dK = 20). C_F is the Forman arm's own
  fitted constant (m/cycle)*(MPa*sqrt(m))^(1 - m); the worked-example
  value C_F = 1e-9 equals C*K_c numerically with K_c = 100 MPa*sqrt(m),
  an example fit whose R = 0 low-range limit collapses onto the Paris arm
  (equal as dK/K_c approaches 0, amplified by the factor
  (1 - dK/K_c)^(-1) otherwise).
- Block march (constant R): da/dN at a growing crack is an ODE in a;
  integrate over the stated block with forward-Euler substeps. Substep is
  exactly 1.0 cycle when cycles <= 5000, else 5000 equal substeps. At
  every substep: dK = Y*dsigma*sqrt(pi*a) from the current a, rate from
  the selected model, then a += rate*step. dK is never held constant
  while the crack grows. Table rows are recorded at cycles 0, N/4, N/2,
  3N/4, N. Piecewise R: segments (cycles, sigma_max, R) applied in order,
  each segment run by the identical march starting from the previous
  segment's final crack length; a two-segment split of one constant-R
  block reproduces the single block bit for bit (anchor: True for both
  models).

Functions:
- stress_intensity(sigma_mpa, a_m, y) -> float: K = y*sigma*sqrt(pi*a)
  in MPa*sqrt(m). ValueError: sigma <= 0, a <= 0, y <= 0.
- walker_equivalent_range(dk_mpa, r, gamma) -> float: dK_bar =
  dk/(1 - r)^(1 - gamma) in MPa*sqrt(m). ValueError: dk <= 0; r >= 1
  or r < -1; gamma <= 0 or gamma > 1.
- walker_dadN(dk_mpa, r, gamma, c, m) -> float: da/dN = C*dK_bar^m in
  m/cycle. ValueErrors of the range function plus c <= 0, m <= 0.
- forman_dadN(dk_mpa, r, kc_mpa, c_forman, m) -> float:
  da/dN = C_F*dK^m/((1 - R)*K_c - dK) in m/cycle. ValueError: dk <= 0;
  r >= 1 or r < -1; kc <= 0; c_forman <= 0; m <= 0; dk >= (1 - r)*kc
  (peak K at or beyond K_c: fracture state, out of the growth-rate
  domain).
- walker_vs_paris_ratio(dk_mpa, r, gamma, c, m) -> float: walker rate
  over the Paris baseline C*dK^m, equal to (1 - R)^(m*(gamma - 1)) to
  roundoff (anchor residual -2.22044604925031e-16). ValueErrors
  propagate.
- forman_vs_paris_ratio(dk_mpa, r, kc_mpa, c_forman, c, m) -> float:
  forman rate over the Paris baseline, equal to
  (C_F/C)/((1 - R)*K_c - dK) to roundoff (anchor residual 0.0).
  ValueErrors propagate.
- block_extension(cycles, sigma_max_mpa, r, a0_m, y, model, gamma,
  kc_mpa, c, c_forman, m) -> dict with keys "a0_m", "a_final_m",
  "extension_m" (m), "rate_start", "rate_final" (m/cycle),
  "dk_start_mpa", "dk_final_mpa", "dk_bar_start_mpa" (MPa*sqrt(m)) and
  "rows", a list of station dicts with keys "cycle", "a_m", "dk_mpa",
  "dk_bar_mpa", "rate" at cycles 0, N/4, N/2, 3N/4, N. model must be the
  string "walker" or "forman" (anything else raises ValueError).
  ValueErrors: cycles < 1; sigma_max <= 0; a0 <= 0; y <= 0; r >= 1 or
  r < -1; gamma out of (0, 1]; for model "forman": an initial crack with
  dK >= (1 - r)*kc (fracture state), and a crack that reaches the
  singularity during the march (the error states the cycle at which peak
  K reaches K_c).
- piecewise_block_extension(segments, a0_m, y, model, gamma, kc_mpa, c,
  c_forman, m) -> dict with keys "a0_m", "a_final_m", "extension_m" and
  "segments", a list of per-segment dicts with keys "cycles", "r",
  "sigma_max_mpa", "a0_m", "a_final_m", "extension_m", "rate_start",
  "rate_final"; segments is a list of (cycles, sigma_max_mpa, r) tuples
  applied in order with the identical march. ValueErrors as
  block_extension plus an empty segments list.
  All block functions require integer cycles >= 1 (a ValueError for
  non-positive or non-integer cycles).

Identities to test (closed form, deterministic; verifiable without the
builder's module):
- R = 0 recovery: dK_bar(dK, 0, gamma) - dK = 0 exactly for gamma = 0.5
  (anchor residual 0.0); the R = 0, gamma = 1 double limit gives the
  crack-growth Paris value C*dK^m, so walker_dadN(20.0, 0.0, 1.0, 1e-11,
  3.0) = 8e-8 m/cycle, the sibling's own anchor.
- gamma = 1 recovery: dK_bar(dK, 0.35, 1.0) - dK = 0 exactly (anchor
  residual 0.0).
- gamma = 0.5 square identity: dK_bar^2*(1 - R) - dK^2 = 0 (anchor
  residual -5.6843418860808e-14).
- Equivalent closed form: dK_bar = Y*sigma_max*sqrt(pi*a)*(1 - R)^gamma
  (anchor residual -3.5527136788005e-15).
- Ratio identities: walker_vs_paris_ratio = (1 - R)^(m*(gamma - 1))
  (anchor residual -2.22044604925031e-16 at R = 0.35, m = 3,
  gamma = 0.5, ratio 1.90822668598782); forman_vs_paris_ratio =
  (C_F/C)/((1 - R)*K_c - dK) (anchor residual 0.0, ratio
  2.05309651628924).
- Fully reversed: at R = -1, dK_bar = dK/sqrt(2) at gamma = 0.5 (anchor
  residual 0.0).
- Direction bounds (magnitude, physics): at fixed dK and gamma,
  dK_bar(R = -0.4) < dK_bar(R = 0) < dK_bar(R = 0.35) (anchor
  13.7701690836267 < 16.2930837851015 < 20.209083229248), so a tensile
  mean accelerates and a compressive mean retards the Walker rate against
  the Paris baseline at the same range; the Forman arm is monotone
  increasing in dK over (0, (1 - R)*K_c) and unbounded as dK approaches
  (1 - R)*K_c.
- March consistency: a one-cycle block extends the crack by exactly the
  rate at the start up to floating-point subtraction rounding (anchor
  relative residual 7.06360499154575e-12); a constant-R block split into
  two equal segments reproduces the single block bit for bit (anchor:
  True, walker and forman).
- Determinism: two identical runs produce identical bits (anchor sha256
  791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62
  under both /usr/bin/python3 3.9.6 and
  ~/.pyenv/versions/3.13.12/bin/python3); no imports beyond math and
  hashlib; no RNG.

## Worked example

2024-T3 aluminium fuselage panel, central through-crack (Y = 1.0),
material constants C = 1e-11 (m/cycle)*(MPa*sqrt(m))^-3, m = 3.0,
gamma = 0.5, K_c = 100 MPa*sqrt(m), C_F = 1e-9
(m/cycle)*(MPa*sqrt(m))^(1 - m) (= C*K_c numerically for m = 3, the
example fit). All values below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_walker_forman_crack_growth.py (stdlib math, exit 0,
run from ~/AeroSkills under python3 3.9.6 and under
~/.pyenv/versions/3.13.12/bin/python3; identical bits, sha256
791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62).

Case 1 (corpus query 1): sigma_max = 100 MPa, R = 0.35 (sigma_min = 35
MPa, dsigma = 65 MPa), initial half-crack a0 = 0.02 m, block of 2000
cycles:
- Starting stress intensities: K_max0 = Y*sigma_max*sqrt(pi*a0) =
  25.06628274631 MPa*sqrt(m) (K_max/K_c = 0.2506628274631), dK0 =
  dsigma*sqrt(pi*a0) = 16.2930837851015 MPa*sqrt(m), Walker equivalent
  dK_bar0 = dK0/(1 - R)^(1 - gamma) = dK0/sqrt(0.65) =
  20.209083229248 MPa*sqrt(m).
- Rates at block start: Paris baseline C*dK0^m = 4.32523663134402e-08
  m/cycle, Walker 8.25353196314273e-08 m/cycle, Forman
  8.88012825993901e-08 m/cycle. The mean-stress corrections at R = 0.35:
  walker/paris = 1.90822668598782 (= 0.65^(-1.5)) and forman/paris =
  2.05309651628924 (= 100/(65 - dK0)); both arms nearly double the
  R = 0 Paris rate at this range.
- Walker-model 2000-cycle block: a_final = 0.0201660975842774 m,
  extension 1.66097584277439e-04 m (0.166098 mm), rate grows from
  8.25353196314273e-08 to 8.3565620180878e-08 m/cycle as dK grows from
  16.2930837851015 to 16.3605999429847 MPa*sqrt(m). Station rows (real
  anchor rows; dK and dK_bar in MPa*sqrt(m), rates in m/cycle, forman
  rate and ratio evaluated at the station state):
  cycle      0: a = 2.000000e-02 m, dK = 1.629308e+01, dK_bar =
    2.020908e+01, walker = 8.253532e-08, forman = 8.880128e-08,
    forman/paris = 2.053097e+00
  cycle    500: a = 2.004133e-02 m, dK = 1.630991e+01, dK_bar =
    2.022995e+01, walker = 8.279130e-08, forman = 8.910748e-08,
    forman/paris = 2.053806e+00
  cycle   1000: a = 2.008279e-02 m, dK = 1.632677e+01, dK_bar =
    2.025087e+01, walker = 8.304834e-08, forman = 8.941509e-08,
    forman/paris = 2.054518e+00
  cycle   1500: a = 2.012438e-02 m, dK = 1.634367e+01, dK_bar =
    2.027183e+01, walker = 8.330644e-08, forman = 8.972413e-08,
    forman/paris = 2.055231e+00
  cycle   2000: a = 2.016610e-02 m, dK = 1.636060e+01, dK_bar =
    2.029283e+01, walker = 8.356562e-08, forman = 9.003461e-08,
    forman/paris = 2.055946e+00
- Forman-model 2000-cycle block: a_final = 0.0201789260510205 m,
  extension 1.7892605102051e-04 m (0.178926 mm), rate 8.88012825993901e-08
  to 9.01301724331156e-08 m/cycle, dK_final = 16.365802933883. Far from
  K_c (K_max/K_c = 0.25) the two models differ by only the R-ratio
  correction shape; the K_c term is not yet felt.
- Near-critical sweep at the same sigma_max = 100 MPa, R = 0.35 (real
  anchor rows; a in m, rates in m/cycle): as a grows and K_max/K_c
  climbs, the Forman arm accelerates away from the Paris and Walker arms
  (the forman/paris ratio equals 100/((1 - R)*K_c - dK) =
  (1/0.65)/(1 - K_max/K_c)):
  a = 0.02:  K_max/K_c = 0.2506628274631,   dK = 16.2930837851015,
    paris = 4.32523663134402e-08, walker = 8.25353196314273e-08,
    forman = 8.88012825993901e-08, forman/paris = 2.05309651628924
  a = 0.15:  K_max/K_c = 0.686468424647827,  dK = 44.6204476021087,
    paris = 8.88386126075541e-07, walker = 1.69524211323869e-06,
    forman = 4.35920332660233e-06, forman/paris = 4.90687911331886
  a = 0.25:  K_max/K_c = 0.886226925452758,  dK = 57.6047501544293,
    paris = 1.91150259516238e-06, walker = 3.64758026242384e-06,
    forman = 2.58477081245233e-05, forman/paris = 13.5221935821267
  a = 0.30:  K_max/K_c = 0.97081295627785,   dK = 63.1028421580602,
    paris = 2.51273541624025e-06, walker = 4.79486877609636e-06,
    forman = 1.32447356814078e-04, forman/paris = 52.7104270342384
  a = 0.31:  K_max/K_c = 0.986860538583257,  dK = 64.1459350079117,
    paris = 2.63941341514295e-06, walker = 5.03659911413004e-06,
    forman = 3.09041283695431e-04, forman/paris = 117.087108037864
  At K_max/K_c = 0.987 the Forman arm runs 117 times the Paris baseline
  while the Walker arm (no K_c term) is still only 1.9 times it: the
  terminal acceleration of the kc-limited denominator is the whole
  difference. The singularity sits at dK = (1 - R)*K_c = 65 MPa*sqrt(m),
  i.e. K_max = K_c, beyond which block_extension raises.
Case 2 (corpus query 2): sigma_max = 140 MPa, R = -0.4 (sigma_min = -56
MPa, dsigma = 196 MPa), initial half-crack a0 = 0.05 m, block of 2000
cycles, the kc-limited band:
- Starting stress intensities: K_max0 = 55.4865821664841 MPa*sqrt(m)
  (K_max/K_c = 0.554865821664841), dK0 = 77.6812150330778, Walker
  equivalent dK_bar0 = dK0/(1.4)^(0.5) = 65.6526093976865 MPa*sqrt(m),
  BELOW dK0: the compressive mean (negative R) pulls the equivalent
  range down against the R = 0 baseline, the reverse of case 1.
- Rates at block start: Paris baseline 4.6875728436968e-06, Walker
  2.82980152371443e-06, Forman 7.52192592680504e-06 m/cycle.
  walker/paris = 0.603681610520369 (= 1.4^(-1.5), below 1: mean
  compression retards the R-corrected rate) while forman/paris =
  1.60465259476863 (above 1: at K_max/K_c = 0.555 the K_c term already
  amplifies against the baseline even at negative R). The two models
  disagree by a factor 2.66 at the block start: Walker carries only the
  mean-stress correction, Forman also counts the K_c proximity.
- Walker-model 2000-cycle block: a_final = 0.0561787832844155 m,
  extension 6.17878328441552e-03 m (6.178783 mm), rate 2.82980152371443e-06
  to 3.37022940273813e-06 m/cycle, dK_final = 82.3411962703766.
- Forman-model 2000-cycle block: a_final = 0.0727588016051557 m,
  extension 2.27588016051557e-02 m (22.758802 mm), rate
  7.52192592680504e-06 to 1.77749967229633e-05 m/cycle (a 2.36x
  acceleration across the block), dK_final = 93.7073758781297
  MPa*sqrt(m). The kc-limited model grows the same block 3.68 times
  farther than the Walker model (22.76 mm vs 6.18 mm) because the crack
  ends at K_max/K_c = 0.669 with the denominator (1 - R)*K_c - dK down
  from 62.32 to 46.29 MPa*sqrt(m); the difference IS the damage
  tolerance life driver. Station rows of the forman-model run (real
  anchor rows; a in m, dK and dK_bar in MPa*sqrt(m), rates in m/cycle):
  cycle      0: a = 5.000000e-02 m, dK = 7.768122e+01, dK_bar =
    6.565261e+01, walker = 2.829802e-06, forman = 7.521926e-06,
    forman/paris = 1.604653e+00
  cycle    500: a = 5.409043e-02 m, dK = 8.079625e+01, dK_bar =
    6.828530e+01, walker = 3.184062e-06, forman = 8.908907e-06,
    forman/paris = 1.689082e+00
  cycle   1000: a = 5.899044e-02 m, dK = 8.437656e+01, dK_bar =
    7.131121e+01, walker = 3.626381e-06, forman = 1.079960e-05,
    forman/paris = 1.797803e+00
  cycle   1500: a = 6.502449e-02 m, dK = 8.858690e+01, dK_bar =
    7.486959e+01, walker = 4.196782e-06, forman = 1.352181e-05,
    forman/paris = 1.945030e+00
  cycle   2000: a = 7.275880e-02 m, dK = 9.370738e+01, dK_bar =
    7.919719e+01, walker = 4.967402e-06, forman = 1.777500e-05,
    forman/paris = 2.160171e+00
  The forman/paris ratio climbs 1.60 to 2.16 across the block while the
  walker/paris ratio stays pinned at 0.6037: the mean-stress correction
  is a constant factor of the range while the kc-limited correction
  grows with the crack.
- Piecewise-R block (sigma_max = 100 MPa throughout): 1000 cycles at
  R = 0.35 then 1000 cycles at R = 0.6, a0 = 0.02 m. Walker model:
  segment 1 extends 8.2791219901783e-05 m (8.25353196314273e-08 to
  8.30483396217601e-08 m/cycle), segment 2 extends
  4.01514165165699e-05 m (4.00913708215703e-08 to
  4.02116625894209e-08 m/cycle), total a_final = 0.0201229426364184 m.
  Raising R at fixed sigma_max cuts dsigma = sigma_max*(1 - R) from 65
  to 40 MPa, and the equivalent range dK_bar =
  Y*sigma_max*sqrt(pi*a)*(1 - R)^gamma drops by sqrt(0.4/0.65) =
  0.7845, so the rate in the second segment falls despite the higher
  mean stress: the block story is the R-corrected rate per regime, not
  a monotone response to R alone. Forman model piecewise total:
  a_final = 0.0201230576354857 m, extension 1.23057635485715e-04 m.
  Split identity: two 1000-cycle segments at R = 0.35 reproduce the
  single 2000-cycle block bit for bit under both models (a_final
  0.0201660975842774 m, anchor True).
- Identity residuals (real anchor runs): R = 0 recovery 0.0; gamma = 1
  recovery 0.0; dK_bar^2*(1 - R) - dK^2 = -5.6843418860808e-14;
  walker/paris ratio residual -2.22044604925031e-16; forman/paris ratio
  residual 0.0; R = -1 square-root relation residual 0.0; ordering
  13.7701690836267 < 16.2930837851015 < 20.209083229248; single-cycle
  extension relative residual 7.06360499154575e-12; equivalent closed
  form residual -3.5527136788005e-15. ValueError battery: 20/20 raised
  as specified. Determinism: sha256
  791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62 on
  both runs under both interpreters.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w45spec/anchor_walker_forman_crack_growth.py
(stdlib math, exit 0).

## Validation list (contract test must include)

- stress_intensity(65.0, 0.02, 1.0) = 16.2930837851015 within 1e-9
  relative; equals y*sigma*sqrt(pi*a) by construction;
  stress_intensity(100.0, 0.02, 1.0) = 25.06628274631 and
  dK = K_max*(1 - R) reproduces the range at R = 0.35.
- walker_equivalent_range(16.2930837851015, 0.35, 0.5) =
  20.209083229248 within 1e-9 relative;
  walker_equivalent_range(dk, 0.0, 0.5) - dk == 0.0 exactly;
  walker_equivalent_range(dk, 0.35, 1.0) == dk exactly;
  walker_equivalent_range(dk, -1.0, 0.5) == dk/sqrt(2) within 1e-12
  relative; the gamma = 0.5 square identity
  dK_bar^2*(1 - r) == dK^2 within 1e-9 relative.
- walker_dadN(16.2930837851015, 0.35, 0.5, 1e-11, 3.0) =
  8.25353196314273e-08 within 1e-6 relative; at r = 0 the same call
  equals the Paris baseline 4.32523663134402e-08 within 1e-6 relative;
  at r = -0.4 the same dK gives 1e-11*13.7701690836267^3, below the
  baseline by the factor 0.603681610520369 (no R clamp, pinned
  formulas).
- walker_vs_paris_ratio(16.2930837851015, 0.35, 0.5, 1e-11, 3.0) =
  1.90822668598782 within 1e-9 relative and equals
  (1 - r)^(m*(gamma - 1)) = 0.65^(-1.5).
- forman_dadN(16.2930837851015, 0.35, 100.0, 1e-9, 3.0) =
  8.88012825993901e-08 within 1e-6 relative; forman_dadN is strictly
  increasing in dk over (0, (1 - r)*kc) and the R = 0 far-limit value
  at dk = 16.2930837851015 equals the Paris baseline times
  (1 - dk/kc)^(-1) = 1.194655... within 1e-6 relative; a doubling of
  C_F doubles the rate (linearity in C_F).
- forman_vs_paris_ratio(16.2930837851015, 0.35, 100.0, 1e-9, 1e-11,
  3.0) = 2.05309651628924 within 1e-9 relative and equals
  (c_forman/c)/((1 - r)*kc - dk) = 100/48.7069162148985.
- block_extension(2000, 100.0, 0.35, 0.02, 1.0, "walker", 0.5, 100.0,
  1e-11, 1e-9, 3.0): a_final 0.0201660975842774 within 1e-6 relative;
  extension 1.66097584277439e-04; rate_final 8.3565620180878e-08;
  dk_final 16.3605999429847; dk_bar_start 20.209083229248.
- block_extension(2000, 100.0, 0.35, 0.02, 1.0, "forman", 0.5, 100.0,
  1e-11, 1e-9, 3.0): a_final 0.0201789260510205 within 1e-6 relative;
  extension 1.7892605102051e-04; rate_final 9.01301724331156e-08;
  dk_final 16.365802933883.
- block_extension(2000, 140.0, -0.4, 0.05, 1.0, "walker", 0.5, 100.0,
  1e-11, 1e-9, 3.0): a_final 0.0561787832844155 within 1e-6 relative;
  block_extension(2000, 140.0, -0.4, 0.05, 1.0, "forman", ...): a_final
  0.0727588016051557 within 1e-6 relative; extension
  2.27588016051557e-02; rate_final 1.77749967229633e-05; dk_final
  93.7073758781297.
- The station rows of the worked example reproduce within 1e-5 relative
  for both cases, e.g. the case 1 cycle-1000 row a = 0.0200827912199018,
  dk 16.3267720644985, dk_bar 20.2508683971858, walker
  8.30483396217601e-08, forman 8.94150945394409e-08 and the case 2
  cycle-1000 row a = 0.0589904442124411, dk 84.376564969541, forman
  1.07996011796121e-05; the block rows are monotone in a and rate.
- Near-critical sweep: at a = 0.31, sigma_max = 100, R = 0.35:
  forman_dadN(64.1459350079117, 0.35, 100.0, 1e-9, 3.0) =
  3.09041283695431e-04 within 1e-6 relative and
  forman_vs_paris_ratio = 117.087108037864 = (1/0.65)/(1 -
  K_max/K_c) with K_max/K_c = 0.986860538583257; the sweep rows
  2.05309651628924 / 4.90687911331886 / 13.5221935821267 /
  52.7104270342384 / 117.087108037864 are monotone increasing.
- piecewise_block_extension([(1000, 100.0, 0.35), (1000, 100.0, 0.35)],
  0.02, 1.0, model, 0.5, 100.0, 1e-11, 1e-9, 3.0) returns a_final
  identical (bit for bit) to the single 2000-cycle block under BOTH
  models; the mixed-R piecewise walker result a_final =
  0.0201229426364184 within 1e-6 relative with segment extensions
  8.2791219901783e-05 and 4.01514165165699e-05, and the forman result
  a_final = 0.0201230576354857 with total extension
  1.23057635485715e-04.
- block_extension(1, 100.0, 0.35, 0.02, 1.0, "walker", 0.5, 100.0,
  1e-11, 1e-9, 3.0): extension 8.25353196308443e-08 within 1e-9
  relative of the rate at the start 8.25353196314273e-08 (single
  substep Euler); doubling the cycles more than doubles the extension
  (the range grows with a) for both models.
- ValueErrors across the module: stress_intensity sigma = 0, a < 0,
  y = 0; walker_equivalent_range dk = 0, r = 1, r < -1, gamma = 0,
  gamma > 1; walker_dadN c = 0, m = 0; forman_dadN kc = 0,
  c_forman < 0, m = 0, dk = (1 - r)*kc (65.0 at r = 0.35, kc = 100),
  dk > (1 - r)*kc (70.0); block_extension cycles = 0, model = "paris",
  forman block starting at or beyond the singularity
  (a0 = 0.315, sigma_max = 100, R = 0.35) and forman block reaching
  the singularity mid-block (a0 = 0.31, sigma_max = 100, R = 0.35,
  N = 2000, raises with the cycle at which peak K reaches K_c);
  piecewise_block_extension empty segments and a segment with r = 1
  (20 anchor cases, each raises ValueError).
- Determinism: two identical runs return identical bits (anchor sha256
  791d233f3a5c74e9030d56c2359d50b920605b5bba3777f12a7ba401175dab62
  on both runs); no imports beyond math; no RNG. Contract test file
  named test_walker_forman_crack_growth.py (underscores), unittest,
  offline in under 20 seconds. Test passes under BOTH interpreters
  (/usr/bin/python3 3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3).
  No exact-float equality on computed sums; use
  assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (eval/hit1-wave45-walker-forman-crack-growth.yaml)

Query 1 (copy verbatim):
  "estimate the walker-forman-crack-growth rate of the 2024-T3 fuselage
  panel at stress ratio R = 0.35: apply the walker-equation equivalent
  delta-k with the gamma exponent and the forman-equation rate with the
  kc-limited denominator, then the crack extension over the 2000-cycle
  block"
  intent: "structures; stress-ratio-corrected crack growth rate:
  Walker equivalent stress intensity range dK_bar = dK/(1-R)^(1-gamma)
  with the gamma exponent, the Forman rate with the K_c-limited
  denominator, the walker-versus-paris and forman-versus-paris ratios,
  and the crack extension over a 2000-cycle block at R = 0.35"
  expected_skill: "structures/damage-tolerance/walker-forman-crack-growth"
Query 2 (copy verbatim):
  "compute the walker-equation equivalent delta-k and the forman-equation
  rate for the growing crack at stress ratio R = -0.4 with the
  r-ratio-correction gamma exponent, and report the walker-forman crack
  extension over the block so the kc-limited acceleration near fracture
  toughness is captured"
  intent: "structures; walker-equation equivalent delta-k and
  forman-equation rate at negative stress ratio R = -0.4 with the gamma
  exponent, the R-corrected rate table and the block extension showing
  the kc-limited terminal acceleration as peak K approaches K_c"
  expected_skill: "structures/damage-tolerance/walker-forman-crack-growth"
Task ids: w45-walker-forman-crack-growth-1 and -2. Prep grep and probe:
the distinctive tokens walker-equation, forman-equation, r-ratio-
correction, equivalent-delta-k, kc-limited-growth and
stress-ratio-crack-growth each match 0 existing eval/hit1-corpus.yaml
tasks (real greps); the only walker corpus matches belong to the wave-36
walker-delta-constellation tasks (space-systems orbit mechanics, a t/p/f
constellation geometry token space with no crack-growth content), and the
existing cg1/cg2 tasks of crack-growth (paris law, crack-growth,
stress-intensity range, damage-tolerance tokens) and the goodman-diagram
tasks keep routing to their owners because both queries above lead with
walker/forman/r-ratio tokens and never use the paris-law, damage-
tolerance, goodman or gerber token strings. Build-time fence note (wave
precedent): add one routing line to crack-growth pointing R-ratio and
K_c-limited rate questions at this leaf.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the walker-forman-crack-
growth rate of a mode I crack under a nonzero stress ratio in airframe
structure:" and include the outputs in the Claim order. First tag:
walker-forman-crack-growth. Additional tags ONLY: walker-equation,
forman-equation, r-ratio-correction, equivalent-delta-k,
kc-limited-growth, stress-ratio-crack-growth. NEVER single generic words
(walker, forman, crack, growth, rate, fatigue, stress, ratio, mean
stress, aluminum, panel, toughness, Kc, delta-k, life, analysis) and
NEVER the sibling tag strings or steering tokens: crack-growth,
paris-law, stress-intensity, damage-tolerance, fatigue-crack,
fracture-mechanics (crack-growth, which owns the R = 0 Paris arm and its
Y*sigma*sqrt(pi*a) product), residual-strength, critical-crack-length,
fracture-toughness, limit-load, crack-length (residual-strength, which
owns the K_c fracture endpoint and critical crack length),
widespread-fatigue-damage, msd, med, multiple-site-damage,
multiple-element-damage, supplemental-inspection (widespread-fatigue-
damage), bird-strike, impact-energy, soft-body-impact (bird-strike),
goodman, gerber, soderberg, haigh-diagram, endurance-limit, infinite-
life, mean-stress (goodman-diagram, the fatigue-pack S-N mean-stress
owner), nor walker-delta, walker-delta-constellation (space-systems
orbit mechanics). The description must not contain the strings "paris
law", "damage tolerance" or "fatigue crack". 50-150 words, <=1000 chars,
no em dash, no content-policy sweep term, action verb present.
Recommended wording (anchor-checked, 794 chars, 112 words): "Use when
you must compute the walker-forman-crack-growth rate of a mode I crack
under a nonzero stress ratio in airframe structure: apply the
walker-equation equivalent range dK_bar = dK/(1-R)^(1-gamma) with the
material gamma exponent and the forman-equation rate da/dN =
C_F*dK^m/((1-R)*K_c - dK) with the kc-limited denominator, then extend
the crack over a stated cycle block at constant or piecewise stress
ratio R. Produces the R-corrected rate table with the walker-equation
and forman-equation rates at each station, the equivalent-delta-k
correction, the kc-limited amplification of the rate over the zero-R
baseline that grows as the peak stress-intensity factor approaches
fracture toughness K_c, and the block extension feeding the follow-on
life and inspection-interval assessment. Trigger: walker equation,
forman equation, stress ratio R, equivalent delta-k, kc-limited growth,
R-ratio correction." The sibling triggers "paris law", "stress
intensity factor", "damage tolerance", "residual strength", "critical
crack length", "goodman" and "gerber" must not appear as this leaf's
trigger list.
