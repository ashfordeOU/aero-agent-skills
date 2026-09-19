---
name: q2007-specimen-hstp
description: "Plan and check how a test centre handles, stores, transports and preserves a customer specimen inside its own walls, under ECSS-Q-ST-20-07C clause 5.7.4.4, which carries the provisions of ECSS-Q-ST-20-08 into the centre: score the storage log against the temperature, humidity and cleanliness limits the item was accepted under, total the time spent outside them, compare the preservation expiry with the planned use day, check the transport shock and tilt monitors against what the item may take, and confirm the handling constraints the mass and sensitivity of the item impose. Use when specimen storage, internal moves or preservation are being planned or audited. Trigger: ecss, q-st-20-07c-clause-5-7-4-4, specimen-handling-storage-transport-preservation, specimen-storage-environment-excursion, specimen-preservation-shelf-life, internal-transport-shock-monitor."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-specimen-hstp, specimen-handling-storage-transport-preservation, specimen-storage-environment-excursion, specimen-preservation-shelf-life, internal-transport-shock-monitor, specimen-handling-constraint]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Specimen Handling, Storage, Transport and Preservation (space-systems/ecss/q2007-specimen-hstp)

Use when the task is the handling-and-storage clause of
ECSS-Q-ST-20-07C clause 5.7.4.4 -- what happens to a customer's item
between the moment the centre accepts it and the moment it goes on the
rig, applying the handling, storage, transportation and preservation
provisions of ECSS-Q-ST-20-08 inside the centre's own perimeter.

## Domain quick reference

- The clause covers the time nobody is testing. Most of a specimen's
  stay at a centre is spent in a store or on a trolley, and that is
  where an item is quietly altered by an environment nobody logged.
- An environment limit is a two-sided band and a duration. A single
  sample over the humidity limit is a different event from four hours
  over it; the record needs both the excursion and the time spent
  outside, because the customer's disposition depends on exposure, not
  on the count of readings.
- Preservation has a clock. A purge, a desiccant, a protective coating
  or a sealed bag is valid for a stated period from the day it was
  applied, so a specimen preserved on receipt and used months later is
  outside its preservation even though nothing visibly changed.
- Internal transport is transport. A move between two buildings on the
  same site can apply more shock than the delivery lorry did, so the
  shock and tilt monitors travel with the item on internal moves and
  are read at every destination.
- Handling constraints come from the item, not the crew. Mass above the
  two-person limit needs lifting equipment with a current certificate;
  an item with declared lift points has to be lifted by them; a
  sensitive item needs the protection its sensitivity implies, and
  none of these is a judgement the crew makes on the day.
- Cleanliness is a graded requirement like the others. A store one
  class dirtier than the item was accepted under is an excursion to be
  recorded, not a detail, because contamination is rarely reversible.

## Workflow

1. Validate the limits: a temperature band whose upper bound exceeds
   its lower, a humidity ceiling inside a sensible percentage, a
   positive cleanliness class number, a positive shock limit, a
   non-negative tilt limit and a positive shelf life.
2. Validate the storage log: samples in time order with finite
   temperature, humidity and cleanliness readings.
3. Score each sample against the limits, absorbing float representation
   error at a bound with a named tolerance so a reading exactly on the
   limit is compliant.
4. Total the time spent outside the limits from the sample spacing, so
   a brief excursion and a sustained one are distinguishable.
5. Compute the preservation expiry day from the day it was applied and
   compare it with the planned use day.
6. Read the transport monitors: peak shock against the item's limit,
   tilt against its allowance, and the seal and protection state on
   arrival.
7. Check the handling constraints the item's mass, lift points and
   sensitivity impose, then aggregate into findings, limitations and a
   compliant-or-deficient verdict.

## Pitfalls

- Counting excursions instead of timing them. Sample density decides
  the count; only the duration says how much exposure the item had.
- Treating an internal move as not transport. The monitors and the
  handling plan apply inside the site, and the short moves are the ones
  that get done without them.
- Letting preservation run from the day the item was received rather
  than the day it was applied. Those differ whenever the customer
  preserved the item before shipping, and the earlier date is the one
  that governs.
- Reading a shock monitor once, at the end. A monitor read only at the
  final destination cannot say which leg applied the peak, so nobody
  can stop the leg that is doing the damage.
- Rounding a limit outward so a reading passes. A reading exactly on a
  bound is compliant by the tolerance inside the comparison; the bound
  itself is what the item was accepted under and does not move.

## Behavior contract (gate 3)

The limit validation, storage-log validation, per-sample excursion
scoring, time-outside-limits total, preservation expiry and use-day
comparison, transport monitor checks, handling-constraint checks and the
compliant-or-deficient verdict are exercised by the gate 3 contract
test: scripts/test_q2007_specimen_hstp.py against
scripts/q2007_specimen_hstp_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_specimen_hstp.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
