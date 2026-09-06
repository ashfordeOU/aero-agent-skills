---
name: brayton-optimum-pressure-ratio
description: "Use when you must select the pressure ratio of a simple gas-turbine-cycle that maximizes the net specific work at the cycle temperature limits: compute the max-work pressure ratio from x_opt = sqrt(tau) for the ideal cycle and x_opt = sqrt(tau*eta_c*eta_t) with component efficiencies; check the zero-work limiting ratio, exactly the max-work ratio squared; and judge the verdict that the max-efficiency ratio diverges from the max-work ratio. Produces the ideal and lossy max-work pressure ratios, the zero-work limit with the r_zero = r_opt**2 cross-check, the specific work at the optimum, and the efficiency-versus-work verdict in SI units. Trigger: maximum specific work, max-work pressure ratio, gas turbine cycle pressure ratio selection."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: gas-turbine-cycle
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: gas-turbine-cycle
  tags: [brayton-optimum-pressure-ratio, max-specific-work-pressure-ratio, work-optimum-compression-ratio, zero-work-limiting-pressure-ratio, ideal-and-lossy-cycle-selection]
  version: 0.1.0
  author: AeroSkills
---

# Brayton Optimum Pressure Ratio (propulsion/gas-turbine-cycle/brayton-optimum-pressure-ratio)

Use when you must select the pressure ratio of a simple gas-turbine-cycle
that maximizes the net specific work at the cycle temperature limits,
rather than evaluate the cycle at a ratio you already fixed. This leaf
implements the max-work pressure ratio selection in pure Python, stdlib
only, closed form: for the ideal cycle x_opt = sqrt(tau) with tau =
T3/T1 and x = r**((gamma-1)/gamma), and with the compressor and turbine
component efficiencies x_opt = sqrt(tau*eta_c*eta_t). It also returns
the zero-work limiting ratio at which the net specific work returns to
zero (exactly the max-work ratio squared, the algebraic cross-check of
the analysis) and issues the design verdict that the max-efficiency
pressure ratio diverges from the max-work ratio. It pairs with
propulsion/gas-turbine-cycle/gas-turbine-cycle, which evaluates the
cycle at a supplied pressure ratio, and with the other gas-turbine-cycle
pack leaves for the regenerative, intercooled and real-cycle variants.

## Domain quick reference

- Cycle frame: T1 is the compressor inlet temperature, T3 the turbine
  inlet temperature, r the pressure ratio and x = r**KAPPA with KAPPA =
  (gamma - 1)/gamma = 2/7 the pressure exponent; gamma = 1.4, air
  standard, cp = 1005.0 J/(kg K) only for quoting work in J/kg.
- Nondimensional net specific work at tau = T3/T1: ideal w/(cp*T1) =
  tau*(1 - 1/x) - (x - 1); real w/(cp*T1) = tau*eta_t*(1 - 1/x) -
  (x - 1)/eta_c, from w = cp*(w_t - w_c) with w_t =
  cp*eta_t*T3*(1 - 1/x) and w_c = cp*T1*(x - 1)/eta_c.
- Max-work condition d(w)/dx = 0: ideal x_opt = sqrt(tau), so r_opt =
  tau**(gamma/(2*(gamma-1))); real x_opt = sqrt(tau*eta_c*eta_t), so
  r_opt = x_opt**(1/KAPPA). Component losses pull x_opt below sqrt(tau).
- Factored zero-work form: w = cp*T1*(x - 1)*(A - x)/(x*eta_c) with A =
  tau*eta_c*eta_t, whose roots x = 1 (no compression) and x = A bound
  the power-producing band (1, r_zero); hence x_zero = tau*eta_c*eta_t =
  x_opt**2 and, because r = x**(1/KAPPA) is a power, r_zero = r_opt**2
  exactly.
- Efficiency arm of the verdict: ideal eta = 1 - 1/x rises
  monotonically with r (no finite maximizer); real eta_th = w/q_in with
  q_in = cp*(T3 - T2), T2 = T1*(1 + (x - 1)/eta_c), peaks at the
  smaller root of the quadratic b*(b - c + a)*x**2 - 2*a*b*x + a*c = 0
  (a = eta_t*T3, b = T1/eta_c, c = T3 - T1 + b), a ratio strictly above
  r_opt, and returns to zero at r_zero.
- Units SI throughout: K, J/kg, dimensionless pressure ratios.
- FAR 33 frames the powerplant certification context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the cycle temperature limits T1, T3 and the component
   efficiencies eta_c, eta_t; every function rejects non-physical
   inputs with ValueError (T1 <= 0, T3 <= T1, eta outside (0, 1], ratio
   at or below 1).
2. Select the ideal max-work pressure ratio with
   ideal_optimum_pressure_ratio(t1, t3), the d(w)/dx = 0 closed form
   x_opt = sqrt(tau) at unit component efficiencies.
3. Select the lossy max-work pressure ratio with
   optimum_pressure_ratio(t1, t3, eta_c, eta_t), the sqrt(tau*eta_c*
   eta_t) closed form that degenerates exactly to the ideal selection
   at eta_c = eta_t = 1.0.
4. Cross-check the zero-work limiting ratio with
   zero_work_pressure_ratio(t1, t3, eta_c, eta_t): the factored form
   makes r_zero = r_opt**2 exact, and the ratio band (1, r_zero) spans
   r_zero/r_opt = r_opt, one decade above the optimum.
5. Evaluate the net specific work at the optimum with
   net_specific_work(t1, t3, r_opt, eta_c, eta_t) and confirm the peak
   against the log-symmetric neighbours of the ratio (factor sqrt(2)
   for the lossy cycle, factor 4 for the ideal cycle).
6. Verify the maximum by the derivative sign change: the closed-form
   d(w)/dx = (cp*T1/eta_c)*(A/x**2 - 1) is positive just below x_opt,
   zero at x_opt and negative just above it.
7. Issue the efficiency-versus-work verdict with
   design_verdict(t1, t3, eta_c, eta_t): the ideal efficiency rises
   monotonically with the ratio while the lossy-cycle efficiency peaks
   at the quadratic root r_eta_max above r_opt and returns to zero at
   the zero-work ratio, so only the specific-work criterion selects
   r_opt.
8. Confirm with the deterministic contract test:
   python3 scripts/test_brayton_optimum_pressure_ratio.py.

## Worked example

T1 = 288.15 K, T3 = 1500 K (tau = 5.205622), eta_c = eta_t = 0.87 for
the lossy cycle; all values are the real outputs of the module.

- Ideal cycle (eta_c = eta_t = 1): r_opt_ideal = 17.940 with w =
  475639.9 J/kg (475.6 kJ/kg), above the log-symmetric neighbours
  w(r_opt_ideal/4) = w(4*r_opt_ideal) = 370621.4 J/kg; the zero-work
  ratio r_zero_ideal = 321.851 equals r_opt_ideal**2 (relative
  difference 7.06e-16) with w vanishing at scaled residual below 1e-9.
- Ideal efficiency arm: 0.002839 at r = 1.01, 0.561708 at the ideal
  max-work ratio, 0.640453 at 2*r_opt_ideal and 0.980693 at r = 1e6,
  still rising: no finite efficiency maximizer in the lossless cycle.
- Lossy cycle: x_opt = 1.984977, r_opt = 11.019 (down from 17.940),
  with w(r_opt) = 322937.1 J/kg above both neighbours w(r_opt/sqrt(2))
  = w(r_opt*sqrt(2)) = 316453.3 J/kg.
- Zero-work cross-check: x_zero = 3.940135 = x_opt**2 exactly and
  r_zero = 121.420 = r_opt**2 (relative difference 2.34e-16); w at
  r_zero is 1.143e-10 J/kg (scaled residual 3.945e-16) and the band
  (1, 121.420) spans r_zero/r_opt = 11.019059 = r_opt.
- Derivative check: d(w)/dx = +66.583 at x_opt*(1 - 1e-4), 0 at x_opt
  and -66.563 at x_opt*(1 + 1e-4): the sign change confirms the
  maximum.
- Verdict: the real thermal efficiency at the max-work ratio is
  0.362832; the closed-form efficiency optimum sits at x_eta_max =
  2.564089, r_eta_max = 26.994 with eta_th = 0.400699, strictly above
  r_opt = 11.019, and the efficiency returns to 0 at r_zero = 121.420
  where the net work is zero. The ideal-cycle efficiency at the lossy
  optimum (r = 11.019) is 0.496216, below the 0.561708 at the ideal
  optimum.
- Read-off: the engine maximizes net specific work near PR 11; PR 27
  maximizes thermal efficiency (about 3.8 points higher) but at lower
  work per unit airflow; past PR 121 the compressor work exceeds the
  turbine output.

## Verification

- Confirm ideal_optimum_pressure_ratio(288.15, 1500.0) returns 17.940
  and optimum_pressure_ratio(288.15, 1500.0, 1.0, 1.0) equals it
  exactly (both tau**(1/(2*KAPPA))).
- Confirm optimum_pressure_ratio(288.15, 1500.0, 0.87, 0.87) returns
  11.019, zero_work_pressure_ratio returns 121.420, and r_zero equals
  r_opt**2 within 1e-9 relative.
- Confirm net_specific_work at the module optimum ratio returns
  322937.1 J/kg (475639.9 J/kg ideal), the log-symmetric neighbours
  are equal and below the peak, and w vanishes at both roots of the
  factored form to within 1e-9 scaled residual.
- Confirm the derivative sign change of d(w)/dx across x_opt and the
  verdict numbers (0.362832 at r_opt, r_eta_max 26.994, 0.400699 at
  the efficiency optimum, 0 at r_zero).
- Confirm every non-physical input raises ValueError: t1 at 0 and -1,
  t3 <= t1, eta_c and eta_t at 0, 1.5 and 1.01, and ratios at 1.0 and
  0.5 on the work and efficiency evaluators.
- Run the contract test offline: python3
  scripts/test_brayton_optimum_pressure_ratio.py (35 tests,
  deterministic, all numeric asserts order-safe tolerances).

## Related leaves

- propulsion/gas-turbine-cycle/gas-turbine-cycle: the given-ratio
  cycle evaluation this leaf complements (efficiency, exit
  temperatures and specific work at a supplied pressure ratio).
- propulsion/gas-turbine-cycle/regenerative-cycle: the exhaust heat
  recovery variant whose recovery payoff boundary is a different
  optimum; it owns the regenerative trigger wording.
- propulsion/gas-turbine-cycle/intercooled-cycle: the inter-stage
  split of a fixed total ratio into compressor stages.
- propulsion/gas-turbine-cycle/real-cycle-effects: loss accounting
  beyond the constant component efficiencies used here.
- propulsion/gas-turbine-cycle/turbojet-cycle: the thrust-oriented
  variant; thrust and nozzle quantities are out of scope here.

## Pitfalls

- Confusing the two optima of this pack: the max-work selection here
  (x_opt = sqrt(tau*eta_c*eta_t), r_opt finite) is not the
  regenerative-cycle recovery optimum, and the two closed forms
  coincide only in the lossless case; never reuse the regenerative
  trigger wording for the recovery payoff boundary.
- Using the ideal closed form for a lossy engine: with eta_c and eta_t
  below 1 the max-work ratio falls (17.940 to 11.019 at 0.87/0.87),
  so sizing on the ideal value overstates the ratio and the work.
- Taking the wrong quadratic root: the efficiency stationarity
  quadratic has a larger unphysical root beyond the q_in = 0 pole at
  x = c/b; always take the smaller root x_eta_max.
- Equating max efficiency with max work: the efficiency optimum
  r_eta_max (26.994) sits above the max-work ratio (11.019) and the
  efficiency there is about 3.8 points higher at lower work per unit
  airflow; only the specific-work criterion selects r_opt.
- Calling design_verdict at unit efficiencies: at eta_c = eta_t = 1.0
  the zero-work ratio coincides with the q_in = 0 pole, so
  eta_real_at_r_zero is not defined there; the verdict is for the
  lossy cycle.
- Extending beyond the model: air-standard gamma = 1.4 only, constant
  specific heats, and component losses limited to the constant
  efficiencies; station temperatures with pressure losses, thrust and
  augmentation quantities belong to the sibling leaves.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_brayton_optimum_pressure_ratio.py

The test covers the worked-example anchors (ideal and lossy max-work
pressure ratios 17.940 and 11.019, zero-work limiting ratio 121.420,
net specific work 475639.9 and 322937.1 J/kg), the degeneracy of the
lossy selection to the ideal closed form at unit efficiencies, the
r_zero = r_opt**2 identity of the factored form with the scaled
zero-work residuals, the log-symmetric neighbour peak property, the
derivative sign change of d(w)/dx across x_opt, the ideal-efficiency
monotone arm, the lossy efficiency quadratic-root optimum with the
efficiency-versus-work verdict numbers, ValueError rejection of every
non-physical input, and the determinism and stdlib-only checks.

## Compliance

- Standards referenced, not reproduced: FAR 33 (14 CFR Part 33) frames
  the aircraft powerplant certification context; the max-work pressure
  ratio relations above are standard gas-turbine-cycle engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
