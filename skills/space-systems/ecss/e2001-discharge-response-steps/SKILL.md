---
name: e2001-discharge-response-steps
description: "Use when plan the response required the moment a discharge or an event appears during a multipactor qualification run, under ECSS-E-ST-20-01C clause 8.5.3: order the immediate actions of drive-removal and onset-state-capture, attribute the excursion to facility-conditioning or to the unit-under-test from the chamber-pressure reading, the outgassing-burst indication and the fixture-fault indication, derive the drive-backoff level the repeat run restarts from, judge the onset-reproducibility across repeat runs against a spread-in-decibels, and issue the disposition -- corrected-and-repeat, nonconformance-raised, or unexplained-event-investigation -- with the onset cap the declaration inherits. Trigger: ecss, e-st-20-electrical-scope, e2001-discharge-response-steps, discharge-response-procedure, event-onset-state-capture, facility-conditioning-attribution, onset-reproducibility-spread, drive-backoff-level, multipactor-nonconformance."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-discharge-response-steps, discharge-response-procedure, event-onset-state-capture, facility-conditioning-attribution, onset-reproducibility-spread, multipactor-nonconformance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Discharge Response Steps (space-systems/ecss/e2001-discharge-response-steps)

Use when the task is the response to a discharge or an event that appears
part-way through a multipactor qualification run, as required by
ECSS-E-ST-20-01C clause 8.5.3 -- what is done at the bench in the seconds
after the excursion, how the excursion is attributed, and what the run may
claim afterwards.

## Domain quick reference

- The response opens with two actions that are never conditional: take the
  drive off the article, and capture the state at onset -- the drive level
  reached, the chamber-pressure reading, the fixture temperature, every
  channel reading, and the timestamp. The capture happens before anything is
  adjusted, because the conditions that produced the excursion disappear the
  moment the bench is touched.
- Attribution splits the excursion two ways. *Facility-conditioning* covers
  everything the bench did to itself: a chamber-pressure reading above the
  vacuum limit, an outgassing-burst as the fixture warms, a fixture-fault at
  a window, feedthrough or connector. *Unit-under-test* covers an excursion
  seen in a clean, stable vacuum with the unit as the only credible source.
  When neither pattern is clean, the attribution stays undetermined.
- A repeat run never restarts at the onset level. It restarts at a
  drive-backoff level below the onset, so the ramp can be re-approached with
  the instrumentation watching, and the reproducibility judged from the onset
  levels the repeats produce.
- Onset-reproducibility is judged on a spread-in-decibels across the repeat
  onsets, not on equality of watt values: bench repeatability is a ratio, so
  the spread is the decibel distance between the highest and lowest onset.
  Within the allowed spread the onset is reproducible and the finding belongs
  to the unit; outside it, the excursion has not been pinned down.
- A reproducible excursion attributed to the unit is a nonconformance, and it
  caps the declarable level below the onset for the rest of the campaign. An
  excursion that never reproduces, in an otherwise nominal bench, is an
  unexplained event that must be investigated -- it is not a pass, and it is
  not deleted from the record.

## Workflow

1. Validate the event record: a non-empty identifier, a positive onset drive
   level, a positive chamber-pressure reading, at least one crossed
   detection-channel, and boolean indications for the outgassing-burst, the
   fixture-fault and the seeding state. Reject a malformed record; do not
   default a missing indication to "clean".
2. Emit the immediate actions in order -- drive removal first, then the
   onset-state capture, then the entry in the run log. These are returned for
   every event, whatever the later attribution turns out to be.
3. Attribute the excursion. A chamber-pressure reading above the vacuum
   limit, an outgassing-burst, or a fixture-fault gives
   facility-conditioning. A clean, stable vacuum with no fixture indication
   gives unit-under-test. Anything else stays undetermined.
4. Derive the drive-backoff level for the repeat run by taking the onset
   level down by the backoff in decibels.
5. Run the repeats and collect their onset levels. Judge the spread between
   the highest and the lowest against the allowed spread-in-decibels; the
   comparison absorbs representation error at the boundary but never widens
   the allowed spread.
6. Issue the disposition. Facility-conditioning: correct the bench condition
   -- extend the pump-down, bake out, repair the fixture -- and repeat from
   the backoff level. Unit-under-test with a reproducible onset: raise a
   nonconformance and cap the declarable level below the lowest onset.
   Anything else: an unexplained event requiring investigation before the
   campaign result is issued.
7. Carry every event into the report with its captured onset state, including
   the ones that were later attributed to the bench.

## Pitfalls

- Ramping back up before the onset state is captured. The pressure and
  channel readings that would have settled the attribution are gone, and the
  event becomes permanently undetermined.
- Restarting the repeat at or just below the onset level. The approach is
  what is being measured; entering at the onset gives no view of the ramp and
  risks stressing the article at an unmonitored level.
- Judging reproducibility on watt equality. Bench repeatability is a ratio;
  two onsets a few percent apart are the same onset, and the spread must be
  read in decibels.
- Attributing to the unit while the chamber-pressure reading sits above the
  vacuum limit. In that condition the bench is the credible source and the
  finding says nothing about the article.
- Dropping a non-reproducible event from the record because the repeats were
  quiet. Clause 8.5.3 leaves it as an event to be investigated, not a pass.
- Leaving the declarable level at the top of the ramp after a confirmed unit
  onset. The cap sits below the lowest onset, not above it.

## Behavior contract (gate 3)

The record validation, immediate-action ordering, attribution,
drive-backoff derivation, onset-reproducibility spread and disposition logic
are exercised by the gate 3 contract test:
scripts/test_e2001_discharge_response_steps.py against
scripts/e2001_discharge_response_steps_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2001_discharge_response_steps.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
