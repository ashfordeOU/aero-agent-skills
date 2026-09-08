---
name: h-infinity-control
description: "Use when you must run the h-infinity mixed-sensitivity norm analysis of a feedback loop: given the plant transfer function, a candidate controller, the sensitivity weight and the control-effort weight, verify the closed loop is stable and compute the h-infinity norms of the weighted sensitivity functions by gamma iteration over the imaginary-axis frequency response, locating the worst-case peak magnitude of each channel. Produces the weighted-sensitivity norm, the weighted control-sensitivity norm, the achieved gamma of the mixed-sensitivity weighting as the larger of the two norms, and the bound verdict when both weighted norms stay below one so the s-over-ks sensitivity bounds hold at every frequency. Trigger: h infinity norm, gamma iteration, mixed sensitivity weighting, s ks weighted bounds, sensitivity weight, control weight, worst case peak gain, weighted loop analysis."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [h-infinity-control, h-infinity-norm, h-infinity, gamma-iteration, mixed-sensitivity, s-over-ks-weighting, sensitivity-weighting, control-effort-weighting, generalized-plant-weighting, worst-case-peak-gain, imaginary-axis-frequency-response]
  version: 0.1.0
  author: AeroSkills
---

# H-infinity Control (gnc-autonomy/control/h-infinity-control)

Use when the task is the worst-case H-infinity norm review of a SISO
feedback loop under a mixed-sensitivity S/KS weighting: given the plant
transfer function G(s), a candidate controller K(s) and two weighting
functions (the sensitivity weight W1 and the control-effort weight W2),
this leaf assembles the closed-loop channels of L = G K over the
characteristic polynomial, verifies strict stability, and computes the
H-infinity norms of the weighted channels W1 S and W2 KS by gamma
iteration over the imaginary-axis frequency response. The achieved
gamma of the mixed-sensitivity weighting and the bound verdict gamma <
1 certify whether |S(jw)| stays below 1/|W1(jw)| and |KS(jw)| below
1/|W2(jw)| at every frequency of the swept axis. The plant, the
candidate controller and the weight parameters are given inputs; the
controller is never synthesized, tuned, placed or recovered here. Pure
Python, stdlib only, deterministic and offline. It pairs with
frequency-response-design, which evaluates an open loop at isolated
frequencies and reports classical margins, and with pid-control-design,
which designs the controller gains this leaf takes as given.

## Domain quick reference

- Loop model: plant G = g_num/g_den and candidate controller
  K = k_num/k_den, both lists of float coefficients in descending
  powers of s; loop transfer L = G K = (g_num k_num)/(g_den k_den).
  The loop must carry no pole-zero cancellation in L: the channel
  representations below are not reduced, so a cancelled pair evaluates
  0/0 at the cancelled dynamics and is rejected by the caller.
- Channels over the common denominator: the characteristic polynomial
  char = g_den k_den + g_num k_num, with S = 1/(1 + L) =
  (g_den k_den)/char, T = L/(1 + L) = (g_num k_num)/char and
  KS = K/(1 + L) = (k_num g_den)/char. Identity: S + T = 1 exactly as
  polynomials, s_num + t_num = char.
- Stability: the loop is strictly stable exactly when routh_stable(char)
  is True (Routh-Hurwitz first-column test, every first-column element
  strictly positive; marginal cases report not-strictly-stable).
- H-infinity norm of a stable proper channel H = num/den: write
  A(x) = hermitian square of num and B(x) = hermitian square of den,
  where |num(jw)|^2 = A(w^2) and |den(jw)|^2 = B(w^2) are polynomials
  in x = w^2 (for p(s) with ascending coefficients q[m], the
  coefficient of x^m in |p(jw)|^2 is (-1)^m times the alternating sum
  over i + j = 2m of q[i] q[j] (-1)^i; odd-power coefficients vanish).
  The stationary equation of the squared magnitude is
  P(x) = A'(x)B(x) - A(x)B'(x) = 0, and every interior peak of |H(jw)|
  sits at a real root x >= 0 of P. The norm is the square root of the
  largest of the DC value A(0)/B(0), the value at every bracketed
  stationary root on the geometric grid in x = w^2 and the
  high-frequency limit (lead-ratio squared |num[0]/den[0]|^2 when the
  degrees are equal, else 0). This is the gamma-iteration search;
  bisection shrinks each frequency bracket around a worst-case peak.
- Weight functions, closed form from corner parameters: W1(s) =
  (s/ms + wb)/(s + wb as_) with |W1(j0)| = 1/as_ and
  |W1(j inf)| = 1/ms; W2(s) = (s + wbc a2)/(s/mu2 + wbc) with
  |W2(j0)| = a2 and |W2(j inf)| = mu2. All six parameters strictly
  positive.
- Weighted norms: ||W1 S||_inf = hinfinity_norm(w1_num s_num,
  w1_den char) and ||W2 KS||_inf = hinfinity_norm(w2_num ks_num,
  w2_den char). Achieved gamma = max of the two; bound verdict
  gamma < 1. Verdict meaning: |W1(jw) S(jw)| at most gamma at every
  swept frequency, so gamma < 1 certifies the s-over-ks pointwise
  bounds.
- Norm search scope: the imaginary-axis sweep runs w in [1e-4, 1e4]
  rad/s (x = w^2 in [1e-8, 1e8], 801 geometric grid points) plus the
  DC point and the high-frequency limit; peaks beyond 1e4 rad/s are
  outside the declared scope and never claimed.

## Workflow

1. Fix the loop under review: the plant G(s) = g_num/g_den and the
   candidate controller K(s) = k_num/k_den, both given inputs that
   this leaf never synthesizes, tunes or places.
2. Assemble the closed-loop channels of the loop transfer L = G K with
   loop_channels: the characteristic polynomial char_poly and the S, T
   and KS numerators over the common denominator, and confirm the
   S + T = 1 identity coefficient by coefficient.
3. Verify the loop is strictly stable with routh_stable on
   char_poly: the Routh-Hurwitz first-column verdict, checked before
   any weighted-norm claim is made.
4. Build the two standard weight functions from their corner
   parameters with sensitivity_weight (W1 from ms, wb, as_) and
   control_weight (W2 from a2, wbc, mu2).
5. Compute the H-infinity norms of the weighted channels by gamma
   iteration with hinfinity_norm over the imaginary-axis frequency
   response: form A(x) and B(x), find the stationary roots of
   P(x) = A'(x)B(x) - A(x)B'(x) = 0 on the geometric grid, refine
   each bracket by bisection, and take the largest of the DC value,
   the interior peak values and the high-frequency limit.
6. Read the mixed-sensitivity review with mixed_sensitivity_gamma:
   the weighted-sensitivity norm ||W1 S||_inf, the weighted
   control-sensitivity norm ||W2 KS||_inf, the achieved gamma as the
   larger of the two, and the bound verdict gamma < 1.
7. Confirm the worst-case bound semantics: on a coarse sweep of the
   imaginary-axis response no sampled |W1S(jw)| exceeds the computed
   norm, and the low-frequency asymptotes hold (|S| Kv/w tending to 1
   and the flat band |W1S| about wb/Kv).
8. Confirm the deterministic checks with the contract test
   scripts/test_h_infinity_control.py, offline, under both
   interpreters.

## Worked example

Loop under review, all numbers real outputs of the contract module:
plant G(s) = 1/(s(s+1)) (g_num [1.0], g_den [1.0, 1.0, 0.0]),
candidate controller K(s) = 8(s+1)/((s+2)(s+8)) (k_num [8.0, 8.0],
k_den [1.0, 10.0, 16.0], a lead-lag with K(0) = 0.5, strictly proper
so KS rolls off at high frequency). Sensitivity weight W1(s) =
(s/2.5 + 0.3)/(s + 3e-4) (ms = 2.5, wb = 0.3 rad/s, as_ = 1e-3),
control weight W2(s) = (s + 0.2)/(s + 2) (a2 = 0.1, wbc = 2.0 rad/s,
mu2 = 1.0). The S/KS review PASSES with gamma 0.7779822129233023,
dominated by the control channel.

- loop_channels(G, K): char_poly [1.0, 11.0, 26.0, 24.0, 8.0]
  (s^4 + 11 s^3 + 26 s^2 + 24 s + 8), routh_stable True. The velocity
  constant of the loop is Kv = lim s L = K(0) = k z/(p1 p2) =
  8/(2*8) = 0.5 s^-1.
- Weight functions as built: sensitivity_weight(2.5, 0.3, 1e-3)
  returns ([0.4, 0.3], [1.0, 0.0003]); control_weight(0.1, 2.0, 1.0)
  returns ([1.0, 0.2], [1.0, 2.0]).
- Weight closed forms: |W1(j0)| = 1000.0 (1/as_), |W1(j inf)| = 0.4
  (1/ms), |W2(j0)| = 0.1 (a2), |W2(j inf)| = 1.0 (mu2). The corner
  magnitude |W1(j wb)| = sqrt(1 + 1/ms^2)/sqrt(1 + as_^2) =
  1.077032422910824 (the formula divides by sqrt(1 + as_^2); a
  printed 1.0770329614269009 equals sqrt(1 + 1/ms^2) alone).
- Weighted sensitivity norm: ||W1 S||_inf = 0.6210716713301313. The
  flat band |W1S| about wb/Kv = 0.6 carries the pass: |W1S(jw)| =
  0.5997464724424371 at w = 0.01, 0.6003939878705405 at w = 0.05,
  0.601583811863733 at w = 0.1, and the worst-case peak sits just
  above the band where the low-frequency asymptote bends over.
- Weighted control norm: ||W2 KS||_inf = 0.7779822129233023, the
  control-sensitivity peak where the strictly proper controller rolls
  off against the rising control weight.
- Achieved gamma = max(0.6210716713301313, 0.7779822129233023) =
  0.7779822129233023 with verdict True (pass): the loop satisfies
  |S(jw)| < 1/|W1(jw)| and |KS(jw)| < 1/|W2(jw)| at every frequency
  of the swept imaginary axis.
- Unweighted channels for context: ||S||_inf = 1.2187761291690518
  (the classical sensitivity peak above 1 near the crossover region)
  and ||T||_inf = 1.0 (the type-1 tracking identity |T(j0)| = 1);
  the S + T = 1 identity holds exactly at the polynomial level and
  pointwise at the sampled frequencies.
- Low-frequency asymptote check: |S(jw)| Kv/w = 0.9999993828127061
  at w = 1e-3, confirming S about jw/Kv with Kv = 0.5.
- Fail sibling (the verdict False path): the same loop with the
  demanding sensitivity weight W1(s) = (s/2.5 + 1)/(s + 1e-3) (wb
  raised from 0.3 to 1.0 rad/s) drives the flat band to wb/Kv = 2.0:
  ||W1 S||_inf = 1.9979285867334802, ||W2 KS||_inf =
  0.7779822129233023 (unchanged), gamma = 1.9979285867334802,
  verdict False: the tracking requirement wb = 1 rad/s exceeds the
  loop's velocity constant Kv = 0.5 s^-1, so the weighted sensitivity
  violates the unit bound. The reviewer reports the achieved gamma and
  the verdict; the controller itself is not altered.
- Determinism: mixed_sensitivity_gamma on the worked loop returns
  identical dicts run to run (gamma and both norms bit-identical).

## Verification

- Confirm the channel assembly anchors: char_poly of the worked loop,
  the S + T = 1 identity at the polynomial and pointwise levels, and
  the |S| and |T| norms.
- Confirm the weight closed forms at DC, at the corner and at the
  high-frequency limit, and the Routh verdicts on the anchor
  polynomials.
- Confirm the norm machinery against closed-form cases: the DC carry
  of 1/(s+1), the zero-at-origin carry of (s+2)/(s+1), and the
  resonant peak 1/(2 zeta sqrt(1 - zeta^2)) = 5.025189076296056 of
  1/(s^2 + 0.2 s + 1).
- Confirm the worked pass and fail sibling norms, achieved gamma and
  bound verdict within 1e-6 relative of the Worked example values,
  and the worst-case bound semantics: the computed norm never
  underestimates the imaginary-axis response sampled on a coarse
  sweep.
- Confirm the low-frequency asymptote |S| Kv/w tending to 1 and the
  flat band |W1S| about wb/Kv on the worked loop.
- Confirm ValueError rejection of an improper transfer function, an
  unstable denominator, a denominator zero at the evaluation point,
  and non-positive weight corner parameters (each naming the
  parameter), with the real messages quoted in the Worked example.
- Run the contract test offline: python3 scripts/test_h_infinity_control.py
  (deterministic, no imports beyond math, no exact-float equality on
  computed sums).

## Related leaves

- gnc-autonomy/control/pid-control-design: designs and tunes the
  controller gains this leaf takes as given inputs; this leaf never
  tunes, places or margin-checks a controller.
- gnc-autonomy/control/frequency-response-design: evaluates an open
  loop at isolated frequencies and reports gain and phase margins;
  this leaf searches a weighted closed-loop channel for its
  worst-case peak and never reports classical margins.
- gnc-autonomy/optimal-control/lqr-design and
  gnc-autonomy/optimal-control/lqg-design: solve the algebraic Riccati
  equations of optimal regulation and estimation; this leaf computes
  no Riccati solution and no state-feedback or compensator gain.
- gnc-autonomy/optimal-control/loop-transfer-recovery: reshapes a
  recovered LQG loop toward a full-state target; this leaf compares
  weighted channel peaks, not one complex transfer against another.
- gnc-autonomy/control/state-space-analysis: the state-space toolbox
  of the pack; this leaf works with rational transfer functions only.

## Pitfalls

- Reading this leaf as an H-infinity controller synthesis: no
  controller is ever synthesized, tuned, placed or recovered here, and
  no algebraic Riccati equation solver lives in the leaf; the plant,
  the candidate controller and the weight parameters are all given
  inputs, and the review verdict only rates the supplied pair.
- Expecting norm coverage beyond the declared sweep: the gamma-
  iteration search covers w in [1e-4, 1e4] rad/s plus the DC point and
  the high-frequency limit; a worst-case peak beyond 1e4 rad/s is
  outside the declared scope and never claimed.
- Feeding a loop with pole-zero cancellation in L: the S, T and KS
  channel representations are not reduced, so a cancelled pair
  evaluates 0/0 at the cancelled dynamics; the user must supply a
  plant-controller pair without cancellation.
- Confusing the weighted bound with a classical margin: the verdict
  gamma < 1 certifies the s-over-ks pointwise bounds of the given
  weighting only; it is not a gain margin or phase margin number
  (those belong to frequency-response-design).
- Reading the |W1(j wb)| corner as sqrt(1 + 1/ms^2) alone: the closed
  form divides by sqrt(1 + as_^2), a difference of about 5.4e-7
  relative at as_ = 1e-3.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_h_infinity_control.py

The test covers the pinned module constants of the gamma-iteration
search (workflow step 5), the Routh-Hurwitz stability verdict on the
characteristic polynomial (step 3), the closed-loop channel assembly
with the S + T = 1 identity (step 2), the weight functions built from
their corner parameters and their closed-form magnitudes (step 4), the
H-infinity norm machinery on the identity cases (step 5), the worked
pass and fail sibling norms with the achieved gamma and the bound
verdict of the mixed-sensitivity weighting (step 6), the worst-case
bound semantics, the velocity asymptote and the flat band (step 7),
determinism across repeated runs, and ValueError rejection of every
non-physical input enumerated in the Worked example.

## Compliance

- Standards referenced, not reproduced: ARP4754A is a proprietary SAE
  standard (name plus paraphrase only, per standards-map.yaml); the
  mixed-sensitivity formulation and the gamma-iteration norm search
  above are standard control engineering methodology, summary-only,
  from Skogestad and Postlethwaite, Multivariable Feedback Control
  (Wiley, 2005, chapter 9) and the Doyle, Glover, Khargonekar and
  Francis state-space H-infinity paper (IEEE Transactions on Automatic
  Control 34(8), 1989) as synthesis context.
- compliance: STANDARDS-REF, gated: false.
