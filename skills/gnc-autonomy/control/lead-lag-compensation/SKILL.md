---
name: lead-lag-compensation
description: "Design phase lead and phase lag compensators for aerospace flight control and GNC loops: compute the plant phase margin at gain crossover from the open loop transfer function, size the phase boost the lead network must add to meet the phase margin specification, derive the lead ratio alpha from the boost, place the lead zero and pole at the new crossover frequency, and size the lag network pole zero pair below crossover to lift the steady state error constant. Produces the compensator transfer function, its zero and pole, the crossover frequency, and the compensated loop phase margin that gate the control law design. Use when the task is lead lag compensation, phase margin improvement, steady state error reduction, or compensator design for a flight control loop. Trigger: phase lead compensator, phase lag compensator, lead lag network, phase margin, gain crossover, steady state error, error constant."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [lead-lag-compensation, phase-lead-compensator, phase-lag-compensator, lead-network, lag-network, phase-margin-boost, gain-crossover-frequency, steady-state-error, error-constant, compensator-zero-pole]
  version: 0.1.0
  author: Aero Agent Skills
---

# Lead Lag Compensation (gnc-autonomy/control/lead-lag-compensation)

Use when the task is classical compensator design for a flight control
or GNC loop: synthesizing a phase lead network to raise the phase
margin toward a specification, or a phase lag network to improve the
steady state error constant without disturbing the crossover much.

## Domain quick reference

- Transfer function representation: the plant is G(s) = num(s) /
  den(s) with coefficient lists in descending powers of s, so
  G(s) = 1/(s(s + 1)) is num = [1], den = [1, 1, 0]. The compensator
  D(s) sits in series ahead of the plant, giving the open loop
  L(s) = D(s) * G(s).
- Gain crossover frequency: omega_wc is the frequency where
  |G(j*omega_wc)| = 1 (0 dB); it is found by bisection over the
  monotone magnitude response of a proper plant.
- Phase margin: PM = 180 + phase(G(j*omega_wc)) in degrees. A
  positive phase margin means the closed loop is stable; transport
  design practice targets 45 degrees minimum, 60 degrees for comfort.
- Lead compensator form: D(s) = (1 + sT)/(1 + alpha * sT) with
  0 < alpha < 1. The zero 1/T lies below the pole 1/(alpha*T), so the
  network adds positive phase and lifts the magnitude between them.
- Maximum phase boost: phi_m = asin((1 - alpha)/(1 + alpha)); solving
  for the ratio gives alpha = (1 - sin(phi_m))/(1 + sin(phi_m)). The
  peak phase occurs at omega_m = 1/(T * sqrt(alpha)).
- Gain rise at the peak: |D(j*omega_m)| = 1/sqrt(alpha), which is
  -10*log10(alpha) dB above the low frequency gain. The design places
  omega_m at the new crossover, where the plant magnitude is short by
  exactly that amount (|G(j*omega_m)| = sqrt(alpha)).
- Lead design recipe: boost = PM_desired - PM_plant + margin (5 to 12
  degrees of margin for the crossover shift), alpha from the boost,
  omega_m where |G| = sqrt(alpha), then T = 1/(omega_m*sqrt(alpha)),
  zero = 1/T and pole = 1/(alpha*T).
- Lag compensator form: D(s) = Kc * (1 + s/zero)/(1 + s/pole) with
  pole = zero/beta and beta > 1. The zero sits one decade below
  crossover so the phase lag at crossover stays near -5 degrees.
- Steady state error constants: position constant Kp = G(0) for a
  type-0 loop, velocity constant Kv = lim(s*G(s)) as s goes to 0 for
  a type-1 loop. Step error is 1/(1 + Kp), ramp error is 1/Kv.
- Lag effect on the error constant: with dc gain Kc = beta the
  velocity error constant is multiplied by beta, cutting the ramp
  error by the same factor while the crossover moves little.
- Certification context: control law design and the margins that
  verify it are developed and validated under ARP4754A development
  assurance; the compensator math here is the classical control
  methodology behind those checks.

## Workflow

1. Write the plant as coefficient lists num and den; confirm it is
   proper so the magnitude falls off at high frequency.
2. Measure the plant phase margin with phase_margin_degrees; the
   crossover comes from gain_crossover_frequency.
3. For a phase margin specification, compute the required boost with
   design_lead_compensator: alpha from lead_alpha_from_phase_boost,
   the new crossover where the plant sits at sqrt(alpha), and the
   zero/pole from lead_zero_pole. Verify the boost is feasible
   (lead_max_phase_deg and lead_gain_boost_db bound it).
4. Assemble the lead network with lead_transfer_function and check
   the compensated loop with compensated_phase_margin; iterate the
   boost margin until the spec is met.
5. For steady state error, read the error constants with
   velocity_error_constant and position_error_constant, then size a
   lag network with design_lag_compensator (beta from the required Kv
   improvement). Confirm the loop stays stable with
   phase_margin_degrees of the series product.
6. Record the compensator transfer function, its zero and pole, the
   new crossover frequency, and the compensated phase margin; sanity
   check the phase at crossover with lead_phase_deg or lag_phase_deg.

## Pitfalls

- Forgetting the boost margin: the lead peak is placed at the NEW
  crossover, but raising the crossover changes the plant phase; a 5
  to 12 degree margin prevents the compensated loop from missing the
  specification.
- Asking for more boost than alpha can give: phi_m approaches 90
  degrees only as alpha goes to 0; a boost near 60 degrees needs a
  very small alpha and a large gain rise, which stresses the loop.
- Placing the lead peak below the plant crossover: the compensator
  then boosts magnitude where the plant is already above 0 dB and the
  crossover lands well above omega_m, wrecking the phase margin.
- Putting the lag zero above crossover: the lag pole zero pair then
  adds several degrees of phase lag at crossover and erodes the
  margin instead of leaving it alone; keep the zero one decade below.
- Treating the lag as free gain: with dc gain beta the lag lifts Kv
  by beta, but the pair also moves the crossover slightly and adds
  phase lag; verify the compensated phase margin stays positive.
- Confusing lead and lag ratios: lead uses alpha in (0, 1) and a
  zero below the pole; lag uses beta > 1 and a pole below the zero.
  Swapping the forms produces a network with the wrong sign of phase.
- Using a single error constant for every loop type: the step error
  formula needs Kp from a type-0 loop; a type-1 loop has infinite Kp
  and zero step error, and the ramp error 1/Kv is the meaningful
  check.
- Checking the margins of G instead of the loop: the phase margin
  that matters is the one of the compensated open loop L = D * G,
  not the raw plant.

## Behavior contract (gate 3)

The compensator design math is exercised by the gate 3 contract test:
scripts/test_lead_lag_compensation.py against
scripts/lead_lag_compensation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_lead_lag_compensation.py

## Compliance

- Standards referenced, not reproduced: ARP4754A frames the
  development assurance and verification of flight control law design
  that this compensator math supports; the lead lag formulas above are
  common classical control methodology, summary-only per
  standards-map.yaml. ARP4754A is proprietary (SAE), name and
  paraphrase only.
- compliance: STANDARDS-REF, gated: false.
