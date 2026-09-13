---
name: e2001-pulsed-test-application
description: "Use when determine whether a pulsed drive may stand in for continuous-wave multipaction verification of equipment that operates continuously, under ECSS-E-ST-20-01C clause 6.4.4: convert the pulse-width into electron-gap-crossings at the operating frequency and resonant-order, confirm the pulse holds the avalanche-growth transits a discharge needs, check the duty-cycle and accumulated on-time give the detection-chain enough integration, verify the pulse peak reaches the operational level plus verification-margin, and require a compensating measure because a low-duty-cycle run never reproduces the continuous-wave thermal state that sets the secondary-emission condition. Trigger: ecss, e-st-20-01c, multipaction, pulsed-drive-substitution, continuous-wave-equivalence, electron-gap-crossings, duty-cycle-adequacy, detection-integration-time, thermal-representativeness."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e2001-pulsed-test-application, multipaction, pulsed-drive-substitution, continuous-wave-equivalence, electron-gap-crossings, thermal-representativeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Pulsed-Drive Substitution (space-systems/ecss/e2001-pulsed-test-application)

Use when the task is the substitution allowed by ECSS-E-ST-20-01C
clause 6.4.4 -- deciding whether equipment that operates in
continuous-wave service may be multipaction-verified with a pulsed
drive instead, and proving the pulse is long enough, repeated enough,
high enough and thermally honest enough to mean anything.

## Domain quick reference

- A pulsed drive is attractive because the bench only delivers the peak
  for a fraction of the time, so a peak that a continuous-wave source
  could never sustain becomes reachable. The clause exists because that
  convenience is only valid under conditions the pulse itself has to
  satisfy.
- A multipaction discharge is not instantaneous. A seed electron
  crosses the gap, liberates secondaries, and the population doubles
  again on each subsequent transit; roughly twenty transits are needed
  before the discharge is observable. Transit time at resonant order n
  and frequency f is `n / (2f)`, so the pulse has to contain
  `pulse_width / transit_time >= 20` transits. A shorter pulse
  extinguishes the avalanche before it grows and the article passes a
  run that never stressed it.
- Higher resonant orders lengthen the transit, so the same pulse holds
  proportionally fewer transits: the shortest admissible pulse scales
  directly with the order being screened.
- The detection chain integrates over accumulated on-time, not over
  wall-clock duration. Whole pulses in the observation window times the
  pulse width gives that on-time; a very low duty cycle starves the
  detector even when every individual pulse is long enough.
- Average dissipation is the peak scaled by the duty cycle, so a
  low-duty run sits far below the steady-state temperature of
  continuous-wave service. Surface temperature drives outgassing and
  the secondary-emission condition that sets the multipaction
  threshold, so the thermal gap has to be closed explicitly -- a
  baseplate preheat, an auxiliary continuous-wave soak, or a separate
  thermal-vacuum run -- and not assumed away.
- The substitution is a stand-in for continuous-wave operation. If the
  equipment already operates pulsed in flight, a pulsed run is simply
  representative service and this clause does not govern it.

## Workflow

1. Confirm the equipment's flight operating mode is continuous-wave;
   pulsed flight operation puts the campaign outside this clause.
2. Validate the pulse profile: a finite positive pulse width and
   repetition frequency, with the width strictly inside the repetition
   period. Derive the period and the duty cycle from them.
3. Convert the pulse width into gap transits at the operating frequency
   and the resonant order being screened, and compare against the
   avalanche-growth minimum. Absorb representation error at an exact
   boundary with a named relative tolerance -- a width derived as
   twenty transit times divides back to twenty only to within a few
   units in the last place -- but never lower the transit minimum.
4. Raise the operational level by the verification margin and confirm
   the pulse peak reaches it; a peak set from average power instead of
   the margined operational level under-drives the whole campaign.
5. Count whole pulses in the observation window, multiply by the pulse
   width for accumulated on-time, and compare against whatever the
   detection method needs to integrate.
6. Compare the duty cycle against the threshold above which the run can
   be treated as thermally representative. Below it, require a
   compensating measure on record.
7. Categorize the outcome: acceptable, acceptable with the compensating
   measure it depends on, out of scope for pulsed flight operation, or
   not acceptable when any condition is unmet.

## Pitfalls

- Sizing the pulse from the RF period alone. The governing interval is
  the electron transit, which is the RF half-period only at first
  order; a pulse sized for first order can be several times too short
  for the higher order actually being screened.
- Reading a high peak as sufficient. Peak amplitude, pulse duration and
  accumulated on-time are three independent conditions; a tall, short,
  rare pulse satisfies none of the other two.
- Treating a pulsed pass as thermal evidence. The run deposits only the
  duty-scaled average, so nothing about the continuous-wave
  steady-state temperature -- or the outgassing and secondary-emission
  condition riding on it -- is verified by it.
- Counting wall-clock duration as detector integration. What the
  detection chain sees is the accumulated on-time; a long window at a
  tiny duty cycle can carry less on-time than a short window at a high
  one.
- Lowering the transit minimum to clear a boundary comparison. When a
  pulse derived as exactly twenty transit times evaluates a few units
  in the last place short, the shortfall is arithmetic; absorb it in
  the comparison and leave the growth criterion where the physics put
  it.

## Behavior contract (gate 3)

The operating-mode check, pulse-profile validation, transit-count,
peak-level, accumulated-on-time and thermal-representativeness logic is
exercised by the gate 3 contract test:
scripts/test_e2001_pulsed_test_application.py against
scripts/e2001_pulsed_test_application_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_pulsed_test_application.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
