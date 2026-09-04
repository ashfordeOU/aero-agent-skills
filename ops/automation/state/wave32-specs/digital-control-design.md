# Wave-32 leaf spec: digital-control-design (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/digital-control-design/
- Pack: control. Siblings: pid-control-design (continuous),
  lead-lag-compensation (continuous), root-locus-design,
  frequency-response-design, state-space-analysis, gain-scheduling,
  observer-design, adaptive-control, control-allocation,
  python-control-design.
- Standards id: arp4754a (reference-only; pack convention). Ledger
  Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Design sampled-data control systems in the z-domain: discretize a
continuous plant with a zero-order hold using exact closed-form
coefficients, emulate a continuous compensator with the Tustin
bilinear transform with frequency prewarping, compute discrete PID
coefficients in the position and velocity forms, check the sampled
poles against the unit circle for stability, and select a sample rate
from the closed-loop bandwidth. Produces the discretized plant
coefficients, the emulated compensator, the discrete PID gains, the
stability verdict and the sample-rate verdict that gate a digital
control design.

Does NOT do: continuous s-domain controller design (pid-control-design,
lead-lag-compensation, root-locus-design own the continuous design
methods); IIR signal filter design (cross-cutting/numerics/
digital-filter-design owns Butterworth filter coefficients - a signal
filter, not a control loop); state-space analysis of continuous systems
(state-space-analysis); frequency-response evaluation (frequency-
response-design).

## Model (implement exactly)

Module constants:
- PI = math.pi.
- SAMPLING_RULE_LOW = 10.0, SAMPLING_RULE_HIGH = 20.0 (sample-rate
  rule: w_s between 10 and 20 times the closed-loop bandwidth).

Functions (pure stdlib, deterministic):

- zoh_first_order(a, T) -> (A, B) of the ZOH step-invariant
  discretization of G(s) = a/(s+a): A = exp(-a*T), B = 1 - A.
  ValueErrors if a <= 0 or T <= 0.
- zoh_second_order(zeta, wn, T) -> (A 2x2, B 2x1) of the ZOH
  discretization of the standard second-order plant
  G(s) = wn^2/(s^2 + 2*zeta*wn*s + wn^2) in companion form with the
  exact closed-form matrix exponential for the 2x2 case (use the
  standard sampled-data formulas with sigma = exp(-zeta*wn*T),
  omega_d = wn*sqrt(1-zeta^2), A11 = sigma*cos(omega_d*T),
  A12 = sigma*sin(omega_d*T)/... - see the standard textbook result;
  implement exactly and verify by the DC-gain identity: the sampled
  step response settles to 1.0).  ValueErrors if wn <= 0, zeta <= 0
  (underdamped only) or zeta >= 1, T <= 0.
- tustin_emulate(cont_coeffs, T, wc = None) -> discrete coefficients
  {num_z, den_z}: map s = (2/T)*(z-1)/(z+1) (plain Tustin) or with
  prewarp s = (wc/tan(wc*T/2))*(z-1)/(z+1) when wc is given.
  cont_coeffs: {num: [..], den: [..]} descending powers of s.  Return
  the z-domain coefficient lists.  ValueErrors on T <= 0, empty
  coeffs, wc <= 0 when given.
- tustin_frequency_check(cont_coeffs, z_coeffs, wc, T) -> phase error
  in degrees at wc between the continuous compensator and the emulated
  discrete compensator (evaluate G(s) at s = j*wc and G(z) at z =
  exp(j*wc*T) with hand-rolled complex arithmetic - stdlib complex
  numbers are fine for the CHECK function).
- discrete_pid_position(Kp, Ki, Kd, T) -> {kp, ki, kd} of the
  position-form discrete PID: u(k) = Kp*e(k) + Ki*T*sum(e) +
  Kd*(e(k)-e(k-1))/T.  Return the coefficient triple used by the
  difference equation.
- discrete_pid_velocity(Kp, Ki, Kd, T) -> {b0, b1, b2, a1} of the
  velocity-form discrete PID difference equation
  delta_u(k) = Kp*(e(k)-e(k-1)) + Ki*T*e(k) +
  Kd*(e(k)-2*e(k-1)+e(k-2))/T, expressed as delta_u(k) = b0*e(k) +
  b1*e(k-1) + b2*e(k-2) with b0 = Kp + Ki*T + Kd/T, b1 = -Kp -
  2*Kd/T, b2 = Kd/T.
- unit_circle_poles(den_z) -> dict {poles (complex list), stable:
  bool}: stable when every pole has modulus < 1.  ValueErrors on
  empty denominator.
- sample_rate_rule(wb) -> dict {w_s_min_rad_s, t_max_s, verdict}:
  the rule is a MINIMUM sample-rate rule (sample 10-20 times per
  closed-loop cycle): w_s_min = SAMPLING_RULE_LOW * wb, T_max =
  2*pi/w_s_min.  verdict "ok" when T <= T_max (sampling at or faster
  than the rule minimum is acceptable), "too-slow" when T > T_max.
  ValueErrors if wb <= 0.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

Lead compensator D(s) = K*(s+20)/(s+200) with K = 20 (so the DC gain
is 2), crossover target wc = 10 rad/s, sample time T = 0.01 s, plant
G(s) = 10/(s+10).

Run your module and take the real outputs as assert targets, then check
the magnitude bounds:
- zoh_first_order(10, 0.01): A about 0.90484, B about 0.09516
  (A = exp(-0.1)).
- DC-gain identity: the ZOH discretized first-order plant step settles
  to 1.0 (A + B = 1.0 exactly).
- Tustin emulation with prewarp at wc = 10 rad/s reproduces the
  continuous compensator's phase at wc to within 1 degree
  (tustin_frequency_check error < 1 deg).
- unit_circle_poles of a stable discrete pole z = 0.5 -> stable True;
  z = 1.05 -> stable False.
- sample_rate_rule(10): T_max = 2*pi/(10*10) = 0.0628 s; T = 0.01 s
  <= T_max -> "ok" (faster than the 10-20x minimum-rate rule is
  acceptable; the rule is a lower bound on the sample rate).
- discrete_pid_position(2.0, 1.0, 0.1, 0.01) coefficient triple
  (position form, Ki*T = 0.01, Kd/T = 10).
- discrete_pid_velocity(2.0, 1.0, 0.1, 0.01): b0 = 2 + 0.01 + 10 =
  12.01, b1 = -2 - 20 = -22, b2 = 10.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: a <= 0, wn <= 0, zeta outside (0,1), T <= 0, empty
  coeffs, wb <= 0, wc <= 0.
- zoh_first_order A+B == 1.0 exactly; A = exp(-a*T).
- Second-order ZOH: step response settles to 1.0 (DC gain identity);
  the sampled natural frequency matches the continuous omega_d within
  1%.
- Tustin phase check < 1 deg at the prewarp frequency.
- unit_circle_poles truth table for known stable/unstable z values
  (0.5 stable, 1.05 unstable, exp(j*0.3) stable on the boundary -
  |z| == 1 -> unstable by the strict < 1 rule).
- discrete PID coefficient identities from the worked example.
- sample_rate_rule: "ok" at T = 0.01 s for wb = 10; "too-slow" at
  T = 0.1 s (0.1 > 0.0628).
- Determinism: no RNG, identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-digital-control-design.yaml)

Query 1 (copy verbatim):
  "discretize a continuous plant with a zero order hold and emulate a lead compensator with the Tustin bilinear transform with frequency prewarping for a sampled data control loop"
  intent: "gnc-autonomy; ZOH plant discretization and Tustin compensator emulation"
  expected_skill: "gnc-autonomy/control/digital-control-design"
Query 2 (copy verbatim):
  "compute the discrete PID coefficients in the position and velocity forms and check the sampled poles against the unit circle for digital control stability"
  intent: "gnc-autonomy; discrete PID coefficients and unit circle stability"
  expected_skill: "gnc-autonomy/control/digital-control-design"
Task ids: w32-digital-control-design-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design a sampled-data digital
control loop in the z-domain:" and include the outputs in the Claim.
First tag: digital-control-design. Additional tags ONLY: z-transform,
tustin-bilinear-emulation, frequency-prewarping, zero-order-hold,
discrete-pid, sample-rate-selection, unit-circle-stability,
sampled-data-control. NEVER single generic words (digital, control,
design, filter, discrete, pid). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): Butterworth, IIR, lowpass,
highpass, cutoff frequency, filter coefficients (cross-cutting/
numerics/digital-filter-design); Ziegler-Nichols, continuous PID
tuning, s-domain root locus (pid-control-design and the continuous
control leaves); state transition matrix continuous (state-space-
analysis).  "Bilinear transform" alone belongs to the CC filter leaf;
always pair it with "compensator" or "control" here.

Tags: [digital-control-design, z-transform,
tustin-bilinear-emulation, frequency-prewarping, zero-order-hold,
discrete-pid, sample-rate-selection, unit-circle-stability,
sampled-data-control]

Sibling-citation lines for Related leaves:
gnc-autonomy/control/pid-control-design (continuous tuning sibling),
gnc-autonomy/control/lead-lag-compensation (continuous compensator
sibling), cross-cutting/numerics/digital-filter-design (signal-filter
sibling; distinct scope), gnc-autonomy/control/state-space-analysis.

Ledger Standard: arp4754a.
