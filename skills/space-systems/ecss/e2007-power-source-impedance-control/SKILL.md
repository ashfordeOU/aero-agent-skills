---
name: e2007-power-source-impedance-control
description: "Use when verify the supply-impedance control demanded by ECSS-E-ST-20-07C clause 5.2.4 across an electromagnetic measurement campaign: confirm every energized supply conductor and its dedicated return carries a line-impedance-stabilization-network, model each network impedance magnitude from its damping-resistance and series-inductance at every swept measurement frequency, compare the measured magnitude against that model inside the declared tolerance band, and re-examine the calibration checkpoints recorded through the campaign so drift from the opening baseline impedance stays inside the permitted fraction. An unstabilized supply conductor, an out-of-band sweep point and a drifted checkpoint are reported as separate findings. Trigger: ecss, e-st-20-electrical-scope, e-st-20-07c-clause-5-2-4, line-impedance-stabilization-network, supply-impedance-envelope, conducted-emission-bench-setup, impedance-drift-checkpoint, stabilization-network-coverage, campaign-impedance-stability."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-power-source-impedance-control, line-impedance-stabilization-network, supply-impedance-envelope, conducted-emission-bench-setup, impedance-drift-checkpoint, stabilization-network-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Supply-Impedance Control (space-systems/ecss/e2007-power-source-impedance-control)

Use when the task is the supply-impedance-control obligation of
ECSS-E-ST-20-07C clause 5.2.4 -- placing a stabilization network on every
energized source conductor feeding the equipment-under-test, holding the
impedance it presents inside a declared band across the measurement
frequency range, and keeping that band demonstrably intact for the whole
duration of the measurement campaign.

## Domain quick reference

- Clause 5.2.4 exists because a conducted-emission or
  conducted-susceptibility reading is only meaningful against a known
  source impedance. The laboratory supply, its cable run and its
  regulation loop present an impedance that varies with frequency, with
  the drawn current and with the day; a line-impedance-stabilization-
  network replaces that unknown with a defined, repeatable impedance and
  simultaneously keeps ambient conducted noise on the facility mains out
  of the measurement.
- Coverage is per conductor, not per bench. Every energized source
  conductor -- the primary-supply feed, any redundant-supply feed, and the
  dedicated supply-return -- carries its own network. A signal return or a
  chassis bond is a referenced conductor rather than a source, so it falls
  outside the stabilization obligation; a de-energized spare feed is
  likewise exempt for that run, and both cases are recorded as exempt
  rather than silently dropped.
- The impedance a network presents is frequency-dependent: flat at its
  damping-resistance near d.c. and rising with the inductive reactance of
  its defining inductance, so the magnitude follows
  sqrt(R^2 + (2*pi*f*L)^2). The verification compares the measured
  magnitude at each swept point against that modelled magnitude and
  accepts it only inside the declared tolerance fraction.
- Campaign stability is a separate question from sweep conformity. A
  network that conformed at the opening calibration can shift through a
  long campaign -- connector wear, thermal soak, a swapped cable -- so the
  clause is satisfied only when the checkpoint readings taken through the
  campaign stay inside a drift fraction of the opening baseline. One
  checkpoint proves nothing: stability needs an opening reading and at
  least one later reading.
- An exact-boundary reading matters here. A deviation assembled from
  measured floats can land a few units in the last place above a limit it
  is physically equal to; the comparison absorbs that representation
  error, and the engineering tolerance itself is never widened to make a
  real exceedance pass.

## Workflow

1. Inventory every conductor entering the equipment-under-test and give
   each one a recognized role (primary-supply, redundant-supply,
   supply-return, signal-return, chassis-bond) with its energized state.
   Reject an unrecognized role or a duplicated conductor identifier before
   anything else runs.
2. Split the inventory: energized source conductors carry the
   stabilization obligation, referenced and de-energized conductors are
   exempt. Raise a coverage finding for each energized source conductor
   with no network declared.
3. Model the declared network across the measurement sweep: at every
   frequency compute the impedance magnitude from the damping-resistance
   and the series-inductance. Require the sweep frequencies to be strictly
   increasing so a duplicated or reordered record is rejected rather than
   averaged.
4. Compare each measured magnitude with its modelled magnitude as a
   fractional deviation and raise a finding for every point outside the
   declared tolerance band.
5. Walk the campaign checkpoints in sequence order, take the opening
   reading as the baseline, and raise a finding for every later checkpoint
   whose drift exceeds the permitted fraction.
6. The campaign satisfies clause 5.2.4 only when coverage, sweep and
   drift each return an empty finding list; report the three lists
   separately so a coverage gap is never masked by a clean sweep.

## Pitfalls

- Stabilizing the supply feed and leaving its dedicated return
  unstabilized -- the loop impedance is what the measurement sees, so a
  bare return leaves the impedance just as undefined as a bare feed.
- Checking the network only at a single frequency, typically near d.c.,
  where the magnitude is simply the damping-resistance and every network
  looks correct; the divergence between a healthy and a degraded network
  appears where the inductive reactance dominates.
- Calibrating once at campaign opening and treating the whole campaign as
  covered -- the clause asks for control throughout, and an undetected
  shift silently re-scales every reading taken after it.
- Reading a de-energized or referenced conductor as a coverage finding,
  which buries the real gaps in noise; the exempt list exists so the
  reviewer can see the judgement rather than guess it.
- Widening the tolerance fraction to clear a boundary point that fails by
  a few units in the last place. The representation error belongs in the
  comparison; the engineering band stays where the setup declared it.

## Behavior contract (gate 3)

The impedance model, tolerance comparison, conductor-coverage,
frequency-sweep and campaign-drift logic is exercised by the gate 3
contract test: scripts/test_e2007_power_source_impedance_control.py
against scripts/e2007_power_source_impedance_control_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_power_source_impedance_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
