---
name: digital-control-design
description: "Use when you must design a sampled-data digital control loop in the z-domain: discretize a continuous plant with a zero-order hold, emulate a continuous compensator with the Tustin bilinear transform with frequency prewarping, compute discrete PID coefficients in the position and velocity forms, check the sampled poles against the unit circle for stability, and select the sample rate from the closed-loop bandwidth. Produces the discretized plant coefficients, the emulated compensator, the discrete PID gains, the stability verdict and the sample-rate verdict that gate a digital control design. Trigger: z transform, zero order hold, zoh, tustin bilinear emulation, frequency prewarping, discrete pid, unit circle stability, sample rate selection."
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
  tags: [digital-control-design, z-transform, tustin-bilinear-emulation, frequency-prewarping, zero-order-hold, discrete-pid, sample-rate-selection, unit-circle-stability, sampled-data-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# Digital Control Design (gnc-autonomy/control/digital-control-design)

Use when the task is designing a sampled-data control loop in the
z-domain: the plant is continuous and must be discretized with a
zero-order hold, the compensator is continuous and must be emulated in
discrete time, or the loop is implemented as a discrete PID. This leaf
implements the sampled-data control methods in pure Python, stdlib
only, deterministic and offline: ZOH step-invariant discretization with
exact closed-form coefficients, Tustin bilinear emulation with
frequency prewarping, discrete PID coefficient forms, unit-circle
stability and the sample-rate rule. It pairs with the continuous
s-domain design leaves (pid-control-design, lead-lag-compensation) that
produce the continuous controllers this leaf samples, and with
state-space-analysis for the continuous state-space context.

## Domain quick reference

- ZOH first-order plant G(s) = a/(s + a): the step-invariant map gives
  A = exp(-a*T) and B = 1 - A, so A + B == 1.0 exactly and the sampled
  DC gain is the continuous one (1.0). zoh_first_order(a, T).
- ZOH second-order plant G(s) = wn^2/(s^2 + 2*zeta*wn*s + wn^2),
  underdamped (0 < zeta < 1), in phase-variable companion form with
  C = [1, 0]: with sigma = exp(-zeta*wn*T), omega_d =
  wn*sqrt(1 - zeta^2) the discrete state matrix is the exact closed-form
  matrix exponential A11 = sigma*(cos(wd*T) + (zeta*wn/wd)*sin(wd*T)),
  A12 = sigma*sin(wd*T)/wd, A21 = -sigma*wn^2*sin(wd*T)/wd,
  A22 = sigma*(cos(wd*T) - (zeta*wn/wd)*sin(wd*T)), and B = [1 - A11,
  sigma*wn^2*sin(wd*T)/wd]. The step response settles to 1.0 and the
  sampled natural frequency equals the continuous omega_d.
  zoh_second_order(zeta, wn, T). Assumption recorded: the spec hint
  "A11 = sigma*cos(omega_d*T)" describes the scaled companion variant;
  the phase-variable form above is the standard textbook realization
  and satisfies every stated validation identity.
- Tustin (bilinear) emulation substitutes s = (2/T)*(z - 1)/(z + 1),
  or with frequency prewarping at wc the constant c = wc/tan(wc*T/2)
  replaces 2/T; the prewarped map sends s = j*wc exactly to
  z = exp(j*wc*T), so the emulated phase matches the continuous phase
  at wc. A continuous pole s_p maps to z = (c + s_p)/(c - s_p).
  Prewarping requires wc*T < pi (wc below the folding frequency).
  tustin_emulate(cont_coeffs, T, wc = None) -> {num_z, den_z} with a
  monic denominator; tustin_frequency_check(cont_coeffs, z_coeffs, wc,
  T) reports the phase error in degrees at wc.
- Position-form discrete PID: u(k) = Kp*e(k) + Ki*T*sum(e) +
  Kd*(e(k) - e(k-1))/T, so the difference-equation coefficients are
  {kp: Kp, ki: Ki*T, kd: Kd/T}. discrete_pid_position(Kp, Ki, Kd, T).
- Velocity-form discrete PID: delta_u(k) = u(k) - u(k-1) = b0*e(k) +
  b1*e(k-1) + b2*e(k-2) with b0 = Kp + Ki*T + Kd/T, b1 = -Kp -
  2*Kd/T, b2 = Kd/T and a1 = -1 on u(k-1) (the 1 - z^-1 delta
  denominator). Identity b0 + b1 + b2 = Ki*T: a constant error injects
  Ki*T of control per step. discrete_pid_velocity(Kp, Ki, Kd, T).
- Unit-circle stability: a sampled pole is stable only when its modulus
  is strictly below 1; a pole exactly on the unit circle is unstable.
  unit_circle_poles(den_z) -> {poles, stable} with exact closed forms
  for degree 1 and 2 denominators (a 1e-12 boundary epsilon keeps
  numerically unit-modulus poles from being mislabeled stable; higher
  degrees raise ValueError, numeric root finding is out of scope).
- Sample-rate rule (minimum-rate rule, not a band): sample 10-20 times
  per closed-loop cycle, w_s_min = SAMPLING_RULE_LOW*wb with
  SAMPLING_RULE_LOW = 10 and T_max = 2*pi/w_s_min. Sampling at or
  faster than the rule minimum is acceptable: verdict "ok" when
  T <= T_max, "too-slow" when T > T_max. Assumption recorded: the
  spec's model line lists the signature as sample_rate_rule(wb) but the
  verdict and validation list require the candidate sample period, so
  the implemented signature is sample_rate_rule(wb, T) ->
  {w_s_min_rad_s, t_max_s, verdict}.

## Workflow

1. Discretize the plant: zoh_first_order(a, T) for the first-order
   plant a/(s + a), or zoh_second_order(zeta, wn, T) for the
   underdamped second-order plant; the returned (A, B) drive the
   difference equation x(k+1) = A*x(k) + B*u(k).
2. Emulate the continuous compensator with tustin_emulate, passing the
   real num and den coefficient lists in descending powers of s and the
   sample time T; give wc when the emulation must match phase at the
   crossover target (frequency prewarping).
3. Check the emulation: tustin_frequency_check reports the phase error
   in degrees at wc between the continuous and the emulated
   compensator; the spec bound is under 1 deg for a prewarped
   emulation.
4. For a discrete PID, take discrete_pid_position or
   discrete_pid_velocity coefficients and write the difference
   equations from the forms above (velocity form increments u each
   step, so it is the natural form for incremental actuators).
5. Check stability: unit_circle_poles on the sampled denominator
   (plant loop denominator or emulated compensator) returns the
   stability verdict against the unit circle.
6. Select the sample time: sample_rate_rule(wb, T) with the
   closed-loop bandwidth wb returns T_max and the ok / too-slow
   verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_digital_control_design.py.

## Worked example

Lead compensator D(s) = 20*(s + 20)/(s + 200) (DC gain 2) on plant
G(s) = 10/(s + 10), crossover target wc = 10 rad/s, T = 0.01 s. Real
module outputs:

- zoh_first_order(10, 0.01) -> A = 0.9048374180, B = 0.0951625820;
  A is exp(-0.1) and A + B == 1.0 exactly (sampled DC gain 1).
- zoh_second_order(0.5, 10, 0.01) -> A = [[0.9951665847,
  0.0095004083], [-0.9500408335, 0.9001625014]], B = [0.0048334153,
  0.9500408335]; the sampled step response settles to 1.0000000000 and
  the sampled natural frequency is 8.660254 rad/s, matching the
  continuous omega_d = 10*sqrt(0.75) exactly.
- tustin_emulate with prewarp at wc = 10: num_z = [10.9962478112,
  -8.9954139914], den_z = [1.0, 0.0004169099]; the DC gain at z = 1 is
  2.0000000000 and tustin_frequency_check returns 6.36e-15 deg, far
  under the 1 deg bound. Plain Tustin gives den_z = [1.0, 0.0], the
  continuous pole at -200 rad/s mapped to z = 0.
- discrete_pid_position(2.0, 1.0, 0.1, 0.01) -> {kp: 2.0,
  ki: 0.01 (Ki*T), kd: 10.0 (Kd/T)}.
- discrete_pid_velocity(2.0, 1.0, 0.1, 0.01) -> {b0: 12.01, b1: -22.0,
  b2: 10.0, a1: -1.0}; b0 + b1 + b2 = 0.01 = Ki*T.
- unit_circle_poles: pole z = 0.5 -> stable True; z = 1.05 -> stable
  False; z = exp(j*0.3) (unit modulus) -> stable False under the strict
  rule.
- sample_rate_rule(10, 0.01) -> {w_s_min_rad_s: 100.0,
  t_max_s: 0.0628318531, verdict: "ok"}; at T = 0.1 s (slower than
  T_max) the verdict is "too-slow".

## Verification

- zoh_first_order: A + B == 1.0 exactly for any valid (a, T); A equals
  exp(-a*T); ValueError for a <= 0 or T <= 0.
- zoh_second_order: step response settles to 1.0 (DC-gain identity);
  sampled natural frequency within 1% of continuous omega_d; ValueError
  for wn <= 0, zeta outside (0, 1), T <= 0.
- tustin_emulate: monic denominator; DC gain preserved; continuous pole
  mapping z = (c + s_p)/(c - s_p); prewarped phase error under 1 deg at
  wc; ValueError for T <= 0, empty coefficient lists, wc <= 0 when
  given, and wc*T >= pi.
- discrete PID forms: worked-example coefficient identities hold; the
  velocity-form identity b0 + b1 + b2 = Ki*T holds; ValueError for
  T <= 0.
- unit_circle_poles: truth table for z = 0.5 (stable), z = 1.05
  (unstable), z = exp(j*0.3) (boundary, unstable); ValueError for empty
  denominators and for degree 3 and higher.
- sample_rate_rule: verdict "ok" at T = 0.01 s for wb = 10 (T < T_max)
  and exactly at T = T_max; "too-slow" at T = 0.1 s; ValueError for
  wb <= 0 or T <= 0.
- All functions deterministic (no RNG, identical floats run to run);
  the contract test re-runs every function and compares exact results.

## Related leaves

- gnc-autonomy/control/pid-control-design: continuous PID tuning
  sibling; its s-domain gains become the Kp, Ki, Kd sampled here.
- gnc-autonomy/control/lead-lag-compensation: continuous compensator
  sibling; its D(s) is the input to tustin_emulate.
- cross-cutting/numerics/digital-filter-design: signal-filter sibling
  (IIR Butterworth design); distinct scope, it shapes signals, not
  control loops.
- gnc-autonomy/control/state-space-analysis: continuous state-space
  context for the plants discretized by the zero-order hold.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_digital_control_design.py

(35 test methods, deterministic, under a second). It covers the ZOH
first- and second-order discretization against the worked example with
the exact A + B == 1 identity and the settle-to-1 DC-gain identity, the
1% sampled-frequency match, plain and prewarped Tustin emulation with
the closed-form pole mapping and the under-1-deg phase-error bound at
wc, the discrete PID position and velocity coefficient identities
(b0 + b1 + b2 = Ki*T), the unit-circle truth table including the
unit-modulus boundary case, the sample-rate rule verdicts at T = 0.01
and T = 0.1 s, exact dict key sets, ValueError rejection of every
non-physical input, and run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: ARP4754A (development assurance
  of aircraft functions) supplies the assurance context; every equation
  above is standard sampled-data control methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
