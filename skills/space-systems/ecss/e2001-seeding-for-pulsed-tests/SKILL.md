---
name: e2001-seeding-for-pulsed-tests
description: "Use when evaluate the electron-seeding arrangement of a multipactor run driven with pulsed radio-frequency under ECSS-E-ST-20-01C clause 6.5.3: derive the drive duty-cycle and the whole-pulse count held at each step, resolve whether a free-running emitter or a pulse-synchronized burst-source supplies the electrons, count the seed electrons present inside one radio-frequency on-time, accumulate the initiation-probability over the pulse-train against the stated seeding-confidence, check the gate-advance of a synchronized burst against the electron-transit-time and the available off-time, and confirm every pulse spans enough carrier-cycles for the avalanche to reach a detectable population. Trigger: ecss, e-st-20-electrical-scope, e2001-seeding-for-pulsed-tests, pulsed-drive-seeding, duty-cycle-derating, pulse-synchronized-seed-burst, gate-advance-timing, avalanche-build-up-cycles."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-seeding-for-pulsed-tests, pulsed-drive-seeding, duty-cycle-derating, pulse-synchronized-seed-burst, gate-advance-timing, avalanche-build-up-cycles]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Seeding Under Pulsed Drive (space-systems/ecss/e2001-seeding-for-pulsed-tests)

Use when the task is the seeding arrangement of ECSS-E-ST-20-01C clause
6.5.3 -- showing that, with the carrier applied in pulses, a seed electron
is present inside the radio-frequency on-time often enough, and early
enough within it, for a discharge to start and grow far enough to be seen.

## Domain quick reference

- Pulsed drive changes the seeding question that clause 6.5.2 answers for
  an uninterrupted carrier. The field exists only during the on-time, so a
  seed electron arriving in the off-time contributes nothing: it is swept
  out or lost before the next pulse rises. Seeding is therefore counted
  per pulse, not per second of dwell.
- A free-running emitter is derated by geometry alone: over one pulse it
  contributes its delivered rate multiplied by the on-time, so a narrow
  pulse collects proportionally fewer seed electrons even though the
  source output never changed. A burst source gated to the pulse train
  instead injects a declared population ahead of each pulse, and its
  per-pulse delivery is independent of how narrow the on-time is.
- A gated burst has a timing window. It must be launched at least one
  electron-transit-time before the field rises, or its electrons arrive
  after the leading edge and the early part of the pulse runs unseeded;
  and it must not be launched earlier than the off-time is long, or the
  burst falls inside the preceding pulse.
- Initiation over a train of pulses is cumulative. Treating each pulse as
  an independent trial, the probability of at least one start over the
  train is one minus the exponential of the per-pulse electron count times
  the pulse count, and the pulse count required for a stated
  seeding-confidence follows by inversion and rounding up to a whole pulse.
- A pulse must also be long enough in carrier-cycles. The avalanche starts
  from a single electron and grows by a per-cycle multiplication factor;
  the cycles needed to reach a detectable population are the logarithm of
  that population over the logarithm of the growth factor. A pulse
  narrower than that budget can host a genuine discharge that never rises
  above the detection floor -- a false pass.
- Independence between pulses is not free: the off-time has to be long
  enough to clear residual charge, and the duty has to stay inside the
  pulsed regime. A duty that climbs toward unity is a continuous-wave run
  in disguise and belongs under the continuous-wave seeding clause.

## Workflow

1. For each drive step, take the on-time, the pulse period, the dwell and
   the carrier frequency. Derive the duty-cycle, reject an on-time wider
   than its period, and count the whole pulses in the dwell. A dwell
   shorter than one period is an input error.
2. Resolve the seed source: free-running (declares a delivered rate into
   the gap) or pulse-synchronized (declares a burst population, a gate
   advance and an electron transit time). Reject a mode that omits the
   fields its own arithmetic needs.
3. Count the seed electrons available inside one on-time -- delivered rate
   times on-time for a free-running emitter, the burst population for a
   gated source.
4. For a gated source, check the gate advance against the
   electron-transit-time and against the off-time. Absorb float
   representation error at both comparisons rather than loosening either
   timing requirement.
5. Accumulate the initiation-probability over the pulse train, compute the
   pulse count the stated seeding-confidence requires, and flag a step
   whose train is shorter than that.
6. Compare the carrier-cycles in the on-time against the cycles the
   avalanche needs to reach the detectable population; flag a pulse too
   narrow to build up. Flag an off-time shorter than the residual-clearing
   time, and a duty that has left the pulsed regime.
7. Aggregate per step across the run, each finding tagged with its step
   identifier. The arrangement is acceptable only when the finding list is
   empty.

## Pitfalls

- Carrying a continuous-wave seeding argument straight into a pulsed run
  -- at a duty of one percent, ninety-nine percent of a free-running
  source's output arrives while there is no field to act on, and the
  seeding is a hundredfold weaker than the dwell-based figure suggests.
- Launching a synchronized burst on the pulse edge -- electrons need their
  transit time to cross into the gap, so a zero-advance burst leaves the
  leading portion of every pulse unseeded, which is exactly where the
  lowest-threshold discharge would have started.
- Advancing a burst so far that it lands in the preceding pulse -- the
  electrons are consumed by the wrong pulse and the intended one is again
  unseeded.
- Sizing a pulse from the seeding statistics alone -- a pulse can carry
  ample seed electrons and still be too short in carrier-cycles for the
  avalanche to reach the detection floor, so the run reports quiet while a
  discharge was in fact starting.
- Counting a fractional trailing pulse toward the train -- only whole
  pulses deliver a full on-time, and rounding the count up borrows
  confidence that was never delivered.
- Letting the duty drift upward to improve seeding -- past the pulsed
  regime the run is a continuous-wave run, and the thermal and
  multipaction behaviour it exercises is no longer the pulsed case the
  article was declared against.

## Behavior contract (gate 3)

The duty-cycle, pulse-count, per-pulse-electron, gate-timing,
cumulative-probability and avalanche-build-up logic is exercised by the
gate 3 contract test: scripts/test_e2001_seeding_for_pulsed_tests.py
against scripts/e2001_seeding_for_pulsed_tests_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_seeding_for_pulsed_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
