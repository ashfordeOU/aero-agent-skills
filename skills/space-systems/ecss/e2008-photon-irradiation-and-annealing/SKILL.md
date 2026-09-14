---
name: e2008-photon-irradiation-and-annealing
description: "Use when a photon irradiation and annealing qualification run has to be sentenced. Evaluate a combined ultraviolet exposure and thermal anneal sequence run on bare solar cells under ECSS-E-ST-20-08C clause 7.5.15: stop a run whose accumulated equivalent sun hours, cell temperature, chamber pressure or soak fell short of the declared profile, stop one whose soak was recorded before the exposure it is meant to recover, split the ultraviolet loss into the share the soak gave back and the residual the mission carries, and read a post-soak reading above the pre-exposure baseline as instrument drift rather than a gain. Trigger: ecss, e-st-20-08c-clause-7-5-15, bare-cell-ultraviolet-photon-irradiation, bare-cell-thermal-anneal-recovery, ultraviolet-equivalent-sun-hours-dose, bare-cell-residual-ultraviolet-degradation, ultraviolet-exposure-anneal-sequence-order."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-photon-irradiation-and-annealing, e-st-20-08c-clause-7-5-15, bare-cell-ultraviolet-photon-irradiation, bare-cell-thermal-anneal-recovery, ultraviolet-equivalent-sun-hours-dose, bare-cell-residual-ultraviolet-degradation, ultraviolet-exposure-anneal-sequence-order]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Photon Irradiation and Annealing (space-systems/ecss/e2008-photon-irradiation-and-annealing)

Use when the task is clause 7.5.15 of ECSS-E-ST-20-08C: bare cells taken
through an ultraviolet exposure and then a thermal soak, in that order,
so that the part of the ultraviolet loss which anneals out can be
separated from the part the mission carries for the rest of its life.

## Domain quick reference

- The exposure is a profile, not a switch. Accumulated equivalent sun
  hours, the cell temperature the exposure ran at, and the chamber
  pressure it ran under are all part of the stress, and a run short on
  any one of them exercised a milder cell than the one that flies.
- Pressure belongs with the other two because it changes the spectrum.
  An ultraviolet source operated against a poor vacuum delivers a
  filtered beam, so the dose counter keeps running while the stress the
  cell actually receives is no longer the declared one.
- Order carries as much weight as the numbers. A soak recorded before
  the exposure it is supposed to recover annealed nothing, and the
  post-soak reading is then a second baseline rather than a result.
- Three measurements are needed and each sits where it can mean
  something: one before the exposure, one between exposure and soak, one
  after the soak. Drop the middle one and the split between recovered
  and residual loss cannot be made at all.
- Only the residual is a degradation budget entry. The recovered share
  describes the test, and quoting it as flight performance credits the
  array with a soak that will never be repeated in orbit.
- A cell that lost nothing to the exposure has no recovery share. The
  quotient has a zero denominator, and reporting it as a full recovery
  reads as evidence where there was none.
- A post-soak reading above the pre-exposure baseline is a measurement
  statement, not a physical one. Ultraviolet does not improve a cell, so
  a reading above the baseline by more than declared repeatability says
  the two readings sat at different reference conditions.
- The dose, the two temperature windows, the pressure ceiling, the soak
  duration, the residual allowance and the specimen floor are declared
  project policy rather than physical constants, so they are stated with
  the result.

## Workflow

1. Take the run: one record per specimen, each with its step order, the
   exposure record, the soak record and the three power measurements.
2. Read the step order first and stop a specimen whose soak precedes its
   exposure or which is missing one of the five steps, because neither
   case carries evidence a sentence could rest on.
3. Read the exposure against the declared dose, temperature window and
   pressure ceiling, and the soak against its own temperature window and
   minimum duration.
4. Reduce the readings twice: the loss the exposure caused, against the
   pre-exposure baseline, and the loss still present after the soak.
5. Turn the two into the share the soak gave back, leaving that share
   undefined where the exposure took nothing away.
6. Hold a post-soak reading above the baseline as an overshoot and leave
   the specimen unsentenced, because the comparison itself is in doubt.
7. Sentence each specimen on the residual alone, then roll the lot up:
   specimen count against its floor, rejected share against its
   allowance, and any unsentenced specimen named on its own.

## Pitfalls

- Counting equivalent sun hours and calling the profile met. The dose
  counter says nothing about the temperature the cell sat at or the
  vacuum the beam crossed, and both change what was delivered.
- Quoting the recovered share as flight performance. The soak is a
  laboratory step; the array in orbit keeps the residual and never sees
  the recovery.
- Reading a soak that gave nothing back as a failed anneal. It is a
  statement about the damage, which was not the reversible kind, and the
  finding belongs against the residual rather than against the oven.
- Accepting a post-soak reading above the baseline as an improvement.
  It is the signature of two measurements taken at different reference
  conditions, and it invalidates the whole comparison rather than
  flattering it.
- Computing a recovery share for a cell the exposure did not damage.
  There is no loss for the share to be a share of, and the quotient
  invents a result.
- Sentencing a specimen whose steps ran out of order because the numbers
  still look reasonable. The reading that would have carried the
  sentence was taken at the wrong moment.
- Comparing a residual loss, a recovered share or a rejected share
  against its limit by bare arithmetic. All three are quotients of
  measured quantities, so a specimen cut exactly to an allowance can
  evaluate a unit in the last place over it and read as a reject on one
  platform and as compliant on another.

## Behavior contract (gate 3)

The step-order check with its missing-step and out-of-order cases, the
exposure dose, temperature and pressure reads, the soak temperature and
duration reads, the exposure and residual losses, the recovered share
with its undefined case, the four recovery groupings and the overshoot,
the specimen verdict and the lot population, reject share and
unsentenced roll-up are exercised by the gate 3 contract test:
scripts/test_e2008_photon_irradiation_and_annealing.py against
scripts/e2008_photon_irradiation_and_annealing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_photon_irradiation_and_annealing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
