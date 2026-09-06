# Wave-42 leaf spec: brayton-optimum-pressure-ratio (propulsion,
# gas-turbine-cycle pack)

- Path: skills/propulsion/gas-turbine-cycle/brayton-optimum-pressure-ratio/
- Pack: gas-turbine-cycle (present siblings gas-turbine-cycle,
  regenerative-cycle, intercooled-cycle, real-cycle-effects,
  turbojet-cycle, afterburner-cycle, combustor, propelling-nozzle,
  subsonic-inlet; adjacent fences in propulsion/axial-compressor and
  propulsion/turboprop).
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  the max-net-specific-work pressure ratio selection):
  - gas-turbine-cycle (this pack) evaluates the cycle AT a supplied
    pressure ratio: its description reads "compute the ideal gas
    turbine (Brayton) cycle: estimate the thermal efficiency, the
    compressor exit temperature, the turbine exit temperature, and the
    net specific work from the pressure ratio and the cycle temperature
    limits" and its workflow step 1 is "Fix the pressure ratio and the
    temperature limits T1, T3", with the quick reference "Thermal
    efficiency depends only on the pressure ratio: eta = 1 -
    PR**((1-gamma)/gamma); it rises with pressure ratio". The pressure
    ratio is an INPUT there, never selected; it states that efficiency
    rises with PR and stops, with no maximization.
  - regenerative-cycle (this pack) OWNS the tag optimum-pressure-ratio:
    its description reads "estimate the optimum pressure ratio at which
    turbine exhaust heat recovery stops paying off", its tags list
    contains optimum-pressure-ratio, and its quick reference gives
    PR_opt = (T3/T1)**(gamma/(2*(gamma-1))) as "the crossover, where
    the regenerator temperature difference vanishes". That optimum is
    the exhaust-heat-recovery payoff boundary (where T4 = T2). The new
    leaf selects the max-work pressure ratio and MUST NOT reuse the tag
    optimum-pressure-ratio; the two closed forms coincide only in the
    lossless case, and x_opt = sqrt(tau*eta_c*eta_t) has no
    regenerative analog.
  - intercooled-cycle (this pack) owns the between-stages split at
    FIXED total ratio: its description reads "determine the optimum
    intercooler pressure ratio minimizing total compressor work" and
    its quick reference is "Optimum pressure split: pi_1 = pi_2 =
    sqrt(pi_total) minimizes the total compressor work for a fixed
    total ratio when intercooling returns the air to the ambient
    temperature (equal stage split)". It never chooses the total ratio.
  - real-cycle-effects (this pack) and turbojet-cycle (this pack)
    likewise take the pressure ratio as a given; none of the pack
    leaves selects a ratio for maximum net specific work.
  Whole-tree greps at prep: "maximum specific work" = 0 hits in
  propulsion; "maximize.*specific work" and "r_opt|work-optimum|
  pressure ratio for maximum" hit only intercooled-cycle (split
  context) and regenerative-cycle (regen context). GENUINE propulsion
  gap (fresh probe, GO 2): no leaf owns the max-work pressure ratio,
  the zero-work limiting ratio, or the max-efficiency verdict.
- Standards id: far-33 (reference-only, present in standards-map.yaml).
  Ledger Standard: far-33.
- Family: propulsion

## Claim

Select the pressure ratio of the simple air-standard gas-turbine-cycle
that maximizes the net specific work at the cycle temperature limits:
for the ideal cycle, x_opt = sqrt(tau) with x = r**((GAMMA-1)/GAMMA)
and tau = T3/T1, giving r_opt = (T3/T1)**(GAMMA/(2*(GAMMA-1))); with
the compressor and turbine component efficiencies, x_opt =
sqrt(tau*eta_c*eta_t), giving r_opt = x_opt**(1/KAPPA). Determine the
zero-net-work limiting ratio from the factored form w = cp*T1*(x-1)*
(A - x)/(x*eta_c) with A = tau*eta_c*eta_t, whose two roots x = 1 and
x = A bound the power-producing band, so x_zero = tau*eta_c*eta_t =
x_opt**2 exactly and r_zero = r_opt**2, the algebraic cross-check of
the whole analysis. Issue the design verdict that the maximum-
efficiency pressure ratio diverges from the maximum-work ratio: in the
ideal cycle the efficiency eta = 1 - 1/x rises monotonically with r, so
the efficiency maximizer is unbounded (r tending to infinity, eta
tending to 1) while the work maximizer is finite at r_opt; in the lossy
cycle the real thermal efficiency peaks at a finite r_eta_max strictly
above r_opt (closed-form quadratic root) and returns to zero at r_zero,
so only the specific-work criterion selects r_opt. Produces the ideal
and lossy max-work pressure ratios, the zero-work limiting ratio with
its r_zero = r_opt**2 identity, the net specific work at the optimum,
and the efficiency-versus-work verdict with the efficiency values at
both optima and at the zero-work limit. Does NOT do: cycle efficiency,
station temperatures or specific work evaluated at a user-supplied
pressure ratio (gas-turbine-cycle, the given-PR cycle); regenerator
effectiveness, exhaust heat recovery or the tag optimum-pressure-ratio
(regenerative-cycle, where the optimum is the recovery payoff
boundary); the intercooler split of a fixed total ratio into stages
(intercooled-cycle); actual station temperatures with pressure losses
or other loss accounting beyond the constant component efficiencies
(real-cycle-effects); thrust, nozzle or augmentation quantities
(turbojet-cycle, propelling-nozzle, afterburner-cycle). Air-standard
gamma = 1.4 only; the temperature dependence of specific heat is out of
scope.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants: GAMMA = 1.4
(air), KAPPA = (GAMMA - 1) / GAMMA (= 2/7, about 0.285714), CP =
1005.0 J/(kg K). CP appears only to quote w in J/kg; every optimum is a
pure ratio and CP-independent.

Defining relations (pin these exactly; every function below derives
from them):
- Nondimensional net specific work at temperature ratio tau = T3/T1
  and pressure variable x = r**KAPPA: ideal cycle w/(cp*T1) =
  tau*(1 - 1/x) - (x - 1); real cycle w/(cp*T1) = tau*eta_t*(1 - 1/x)
  - (x - 1)/eta_c, from w = cp*(w_t - w_c) with w_t =
  cp*eta_t*T3*(1 - 1/x) and w_c = cp*T1*(x - 1)/eta_c.
- Max-work condition d(w)/dx = 0: ideal cycle x_opt = sqrt(tau), so
  r_opt = tau**(GAMMA/(2*(GAMMA-1))) = tau**(1/(2*KAPPA)); real cycle
  x_opt = sqrt(tau*eta_c*eta_t), so r_opt = (tau*eta_c*eta_t)**
  (1/(2*KAPPA)). Component losses pull x_opt below sqrt(tau).
- Factored zero-work form: w = cp*T1*(x - 1)*(A - x)/(x*eta_c) with
  A = tau*eta_c*eta_t, so the roots of w = 0 are x = 1 (no
  compression) and x = A. Hence x_zero = tau*eta_c*eta_t = x_opt**2
  and, because r = x**(1/KAPPA) is a power, r_zero = r_opt**2 exactly.
  The power-producing band of pressure ratios is (1, r_zero); at the
  lossy anchor r_zero/r_opt = r_opt, one decade above the optimum.
- Efficiency side of the verdict: ideal eta = 1 - 1/x, strictly
  increasing in r (no finite maximizer). Real thermal efficiency
  eta_th = w/q_in with q_in = cp*(T3 - T2), T2 = T1*(1 + (x - 1)/
  eta_c), rearranged to eta_th(x) = (x - 1)*(a - b*x)/(x*(c - b*x))
  with a = eta_t*T3, b = T1/eta_c, c = T3 - T1 + b. Setting
  d(eta_th)/dx = 0 gives the quadratic b*(b - c + a)*x**2 - 2*a*b*x +
  a*c = 0; its smaller root x_eta_max sits between x_opt and x_zero
  (the larger root is unphysical, beyond the q_in = 0 pole at
  x = c/b), and eta_th returns to 0 at x_zero where w = 0.

Functions:
- ideal_optimum_pressure_ratio(t1, t3) -> float
  (t3/t1)**(GAMMA/(2*(GAMMA-1))), the closed form sharing the
  regenerative-cycle crossover shape but derived here from d(w)/dx = 0
  for the lossless cycle. ValueError if t1 <= 0 or t3 <= t1.
- optimum_pressure_ratio(t1, t3, eta_c, eta_t) -> float
  x_opt = math.sqrt(tau*eta_c*eta_t), return x_opt**(1/KAPPA).
  Degenerates to ideal_optimum_pressure_ratio at eta_c = eta_t = 1.0.
  ValueError if t1 <= 0, t3 <= t1, or eta_c or eta_t outside (0, 1].
- zero_work_pressure_ratio(t1, t3, eta_c, eta_t) -> float
  x_zero = tau*eta_c*eta_t, return x_zero**(1/KAPPA). Identical
  ValueError set. The caller-facing cross-check r_zero == r_opt**2
  holds to float noise.
- net_specific_work(t1, t3, r, eta_c, eta_t, cp = CP) -> float
  cp*(eta_t*t3*(1 - 1/x) - t1*(x - 1)/eta_c) with x = r**KAPPA, the
  real-cycle work in J/kg (use eta_c = eta_t = 1.0 for the ideal
  value). ValueError if r <= 1 (pressure ratios of 1 or below raise,
  sibling convention), t1 <= 0, t3 <= t1, or an eta outside (0, 1].
- ideal_cycle_efficiency(r) -> float
  1 - 1/(r**KAPPA), used only for the monotonicity arm of the verdict.
  ValueError if r <= 1.
- cycle_efficiency(t1, t3, r, eta_c, eta_t, cp = CP) -> float
  w/q_in with q_in = cp*(t3 - t2) and t2 = t1*(1 + (x - 1)/eta_c);
  equals 0 at r_zero and at r = 1, peaks at r_eta_max. ValueError set
  as net_specific_work.
- design_verdict(t1, t3, eta_c, eta_t) -> dict
  the max-efficiency versus max-work comparison, all closed form:
  returns eta_ideal_at_r_opt_ideal, eta_ideal_low and eta_ideal_high_r
  (monotone rise, so no finite ideal efficiency maximizer), and for the
  lossy cycle eta_real_at_r_opt, x_eta_max_real, r_eta_max_real
  (smaller quadratic root), eta_real_at_eta_max and eta_real_at_r_zero
  (0 at the zero-work ratio). ValueError set as optimum_pressure_ratio.

Identities to test (closed form, exact):
- Degeneracy: optimum_pressure_ratio(t1, t3, 1.0, 1.0) ==
  ideal_optimum_pressure_ratio(t1, t3) exactly (both tau**(1/(2*KAPPA)))
  and zero_work_pressure_ratio(t1, t3, 1.0, 1.0) == tau**(1/KAPPA) ==
  r_opt_ideal**2.
- x_zero == x_opt**2 exactly (A = x_opt**2 by construction) and
  r_zero == r_opt**2 within float noise (real anchor relative
  difference 2.34e-16).
- Zero-work roots: net specific work vanishes at both roots of the
  factored form, w(x = 1) = 0 and w(x = x_zero) = 0, scaled by cp*T1
  to within 1e-9 (real anchor residual 3.945e-16 at r_zero); the
  factored form reproduces net_specific_work everywhere.
- Peak property: w(r_opt) > 0 and above both log-symmetric neighbours
  (lossy: w(r_opt/sqrt(2)) = w(r_opt*sqrt(2)) < w(r_opt); ideal:
  w(r_opt/4) = w(4*r_opt) < w(r_opt)).
- Derivative sign change: d(w)/dx > 0 below x_opt, zero at x_opt
  within 1e-6, < 0 above x_opt.
- Lossy ordering: component losses pull the optimum down, r_opt falls
  from 17.940 (ideal) to 11.019 (0.87/0.87) and r_zero from 321.851 to
  121.420; x_opt = sqrt(tau*eta_c*eta_t) < sqrt(tau).
- Ideal efficiency monotone: eta(1.01) < eta(r_opt_ideal) <
  eta(2*r_opt_ideal) < eta(1e6), never a finite maximizer.
- Lossy efficiency verdict: eta_th(r_opt) < eta_th(r_eta_max),
  r_eta_max > r_opt, and eta_th(r_zero) = 0 within 1e-9.
- ValueErrors across the module: t1 <= 0; t3 <= t1; eta_c or eta_t at
  0, 1.5 and 1.01; r at 1.0 and 0.5 for net_specific_work,
  ideal_cycle_efficiency and cycle_efficiency.
- Determinism; no imports beyond math; gamma fixed at 1.4.

## Worked example

T1 = 288.15 K, T3 = 1500 K, so tau = 5.205622, and eta_c = eta_t =
0.87. All values below are REAL outputs of the prep anchor
/tmp/w42spec/anchor_brayton_optimum_pressure_ratio.py (stdlib math,
closed form).
- Ideal cycle (eta_c = eta_t = 1):
  - x_opt_ideal = sqrt(tau) = 2.281583; r_opt_ideal = tau**(GAMMA/
    (2*(GAMMA-1))) = 17.940.
  - w(r_opt_ideal) = 475639.9 J/kg (475.6 kJ/kg), positive and above
    the log-symmetric neighbours w(r_opt_ideal/4) = w(4*r_opt_ideal) =
    370621.4 J/kg.
  - Zero-work root: x_zero_ideal = tau = 5.205622, r_zero_ideal =
    321.851, and r_zero_ideal = r_opt_ideal**2 (relative difference
    7.06e-16). w at r_zero_ideal = 2.285e-10 J/kg, scaled residual
    7.891e-16 (< 1e-9).
  - Ideal efficiency at the ideal max-work ratio: eta = 0.561708,
    still rising: 0.640453 at 2*r_opt_ideal and 0.980693 at r = 1e6,
    versus 0.002839 at r = 1.01, the monotone arm of the verdict.
- Lossy cycle (eta_c = eta_t = 0.87):
  - x_opt = sqrt(tau*eta_c*eta_t) = sqrt(3.940135) = 1.984977;
    r_opt = 11.019 (down from 17.940).
  - w(r_opt) = 322937.1 J/kg (322.9 kJ/kg), above both neighbours
    w(r_opt/sqrt(2)) = w(r_opt*sqrt(2)) = 316453.3 J/kg.
  - Zero-work root: x_zero = tau*eta_c*eta_t = 3.940135 = x_opt**2
    exactly; r_zero = 121.420 = r_opt**2 (relative difference
    2.34e-16). w at r_zero = 1.143e-10 J/kg, scaled residual 3.945e-16
    (< 1e-9); w at r = 1 = 0.000e+00 (the x = 1 root). The feasible
    power band (1, 121.420) spans r_zero/r_opt = 11.019059 = r_opt.
  - Derivative check: d(w)/dx = +66.583 at x_opt*(1 - 1e-4), 5.7e-11
    at x_opt (zero to 1e-6), -66.563 at x_opt*(1 + 1e-4): sign change
    confirms the maximum.
  - Verdict numbers: real eta_th at r_opt = 0.362832; the closed-form
    efficiency optimum sits at x_eta_max = 2.564089, r_eta_max =
    26.994 with eta_th = 0.400699, strictly above r_opt = 11.019; eta
    returns to 0.000000 at r_zero = 121.420 where the net work is
    zero. The ideal cycle efficiency at the LOSSY optimum (r = 11.019)
    is 0.496216, below the 0.561708 at the ideal optimum, the gain
    available from a higher ratio.
- Read-off: the engine maximizes net specific work near PR 11; PR 27
  maximizes thermal efficiency (about 3.8 points higher) but at lower
  work per unit airflow; past PR 121 the compressor work exceeds the
  turbine output.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w42spec/
anchor_brayton_optimum_pressure_ratio.py (stdlib math, closed form,
exit 0).

## Validation list (contract test must include)

- ideal_optimum_pressure_ratio(288.15, 1500.0) = 17.940 within 1e-3;
  equals optimum_pressure_ratio(288.15, 1500.0, 1.0, 1.0) exactly.
- optimum_pressure_ratio(288.15, 1500.0, 0.87, 0.87) = 11.019 within
  1e-3; zero_work_pressure_ratio(288.15, 1500.0, 0.87, 0.87) =
  121.420 within 1e-3; r_zero == r_opt**2 within 1e-9 relative.
- net_specific_work(288.15, 1500.0, r_opt, 0.87, 0.87) = 322937.1
  J/kg within 1e-2 (assert with the module r_opt, not the rounded
  11.019); ideal value at r_opt_ideal = 475639.9 J/kg.
- Zero-work: w(r_zero) scaled residual below 1e-9 (anchor 3.945e-16);
  w(r = 1) = 0; neighbours w(r_opt/sqrt(2)) and w(r_opt*sqrt(2)) equal
  each other (316453.3 J/kg) and sit below w(r_opt).
- d(w)/dx sign change around x_opt: positive just below, |value| <
  1e-6 at x_opt, negative just above.
- Design verdict: eta_real_at_r_opt = 0.362832 within 1e-6,
  r_eta_max_real = 26.994 within 0.02, eta_real_at_eta_max = 0.400699
  within 1e-6, eta_real_at_r_zero = 0 within 1e-9, and r_eta_max_real
  > r_opt; ideal efficiency monotone with eta_ideal_at_r_opt_ideal =
  0.561708 within 1e-6.
- ValueErrors: t1 at 0 and -1; t3 <= t1 (t3 = 288.15); eta_c and eta_t
  at 0, 1.5 and 1.01 on every eta argument; r at 1.0 and 0.5 on
  net_specific_work, ideal_cycle_efficiency and cycle_efficiency.
- Determinism; no imports beyond math; gamma fixed at 1.4.

## Corpus fragment (eval/hit1-wave42-brayton-optimum-pressure-ratio.yaml)

Query 1 (copy verbatim):
  "select the brayton-optimum-pressure-ratio that maximizes the net
  specific work of the simple gas-turbine-cycle at a given
  turbine-inlet temperature ratio and check the zero-work limiting
  ratio"
  intent: "propulsion; simple gas-turbine-cycle pressure ratio
  selection for maximum net specific work at the cycle temperature
  limits with the zero-work limiting ratio cross-check"
  expected_skill: "propulsion/gas-turbine-cycle/
  brayton-optimum-pressure-ratio"
Query 2 (copy verbatim):
  "find the maximum-work compression ratio of the ideal and lossy
  brayton cycle from the cycle temperature limits and component
  efficiencies"
  intent: "propulsion; ideal and component-efficiency closed forms for
  the maximum-work pressure ratio of the brayton simple cycle"
  expected_skill: "propulsion/gas-turbine-cycle/
  brayton-optimum-pressure-ratio"
Task ids: w42-brayton-optimum-pressure-ratio-1 and -2. Prep grep:
"maximum specific work" appears in NO existing hit1-corpus.yaml task
and no propulsion leaf; the gas-turbine-cycle tasks route on efficiency
and exit temperatures at a GIVEN pressure ratio, the regenerative-cycle
tasks route on regenerator effectiveness and the recovery payoff
boundary, and the intercooled-cycle tasks route on the inter-stage
split, so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must select the pressure ratio of a
simple gas-turbine-cycle that maximizes the net specific work at the
cycle temperature limits:" and include the outputs in the Claim. First
tag: brayton-optimum-pressure-ratio. Additional tags ONLY:
max-specific-work-pressure-ratio, work-optimum-compression-ratio,
zero-work-limiting-pressure-ratio, ideal-and-lossy-cycle-selection.
NEVER single generic words (pressure, ratio, optimum, brayton, cycle,
efficiency, specific, work, turbine, compressor, temperature) and NEVER
optimum-pressure-ratio, which regenerative-cycle owns (its payoff
boundary is a different optimum, and the probe fence forbids reuse).
50-150 words, <=1000 chars, no em dash, no content-policy sweep term
(the banned word from the builder kit), action verb present.
Recommended wording (outputs and verdict in Claim order): "Use when
you must select the pressure ratio of a simple gas-turbine-cycle that
maximizes the net specific work at the cycle temperature limits:
compute the max-work pressure ratio from x_opt = sqrt(tau) for the
ideal cycle and x_opt = sqrt(tau*eta_c*eta_t) with component
efficiencies, where x = r**((gamma-1)/gamma) and tau = T3/T1; check
the zero-work limiting ratio at which the net specific work returns to
zero, exactly the max-work ratio squared; and judge the design verdict
that the max-efficiency pressure ratio diverges from the max-work
ratio, since the ideal-cycle efficiency keeps rising past the work
optimum. Produces the ideal and lossy optimum pressure ratios, the
zero-work limit with its r_zero = r_opt**2 cross-check, the specific
work at the optimum, and the efficiency-versus-work verdict, in SI
units, that gate the engine cycle assessment. Trigger: maximum
specific work, max-work pressure ratio, pressure ratio for maximum
work, gas turbine cycle pressure ratio selection." The tag
optimum-pressure-ratio and the regenerative trigger "optimum pressure
ratio" must not appear.

FORBIDDEN TOKENS (belong to siblings): compressor-exit-temperature,
turbine-exit-temperature, cycle-thermal-efficiency at a user-supplied
pressure ratio, given-pressure-ratio cycle evaluation (gas-turbine-
cycle); regenerator-effectiveness, recuperator, exhaust-heat-recovery,
regenerator-payoff, efficiency-gain-percentage-points, the tag
optimum-pressure-ratio (regenerative-cycle); intercooler-effectiveness,
two-stage-compression, inter-stage-split, compression-work-split,
equal-stage-split (intercooled-cycle); actual-station-temperature,
combustor-pressure-loss, component-losses beyond the constant
efficiency assumption, off-design (real-cycle-effects); thrust,
specific-thrust, propelling-nozzle, afterburner, augmentation
(turbojet-cycle, propelling-nozzle, afterburner-cycle).
