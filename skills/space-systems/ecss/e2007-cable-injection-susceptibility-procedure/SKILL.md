---
name: e2007-cable-injection-susceptibility-procedure
description: "Plan the warm-up and frequency-stepping steps of the bulk cable-injection susceptibility run of ECSS-E-ST-20-07C clause 5.4.8.4. Use when a harness current-injection procedure is written or graded: confirm the unit settled before any current was driven, build the stepped injection frequency list so no sub-band is stepped over, size each dwell from the response time and the monitor sampling, convert the required injection current into the forward power the calibration demands, cap the drive at the amplifier limit and say so when a step never reached that level, categorize each step as immune, on the level or susceptible, and total the run. Trigger: ecss, e-st-20-07c, cable-injection-susceptibility-procedure, bulk-current-injection-step-dwell, cable-injection-frequency-list, cable-injection-forward-power-limit, cable-injection-warm-up-dwell, cable-injection-step-grading."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-cable-injection-susceptibility-procedure, bulk-current-injection-step-dwell, cable-injection-frequency-list, cable-injection-forward-power-limit, cable-injection-warm-up-dwell, cable-injection-step-grading]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Cable-Injection Susceptibility Procedure (space-systems/ecss/e2007-cable-injection-susceptibility-procedure)

Use when the task is the procedure clause of ECSS-E-ST-20-07C clause
5.4.8.4 -- running a bulk current-injection susceptibility test on a
harness: bringing the unit up and leaving it to settle, then stepping the
injection frequency across the declared range while current is driven into
the bundle and the monitored functions are watched.

## Domain quick reference

- Warm-up comes before injection because susceptibility is judged against
  the unit's own steady indications. A unit still drifting as it warms
  produces an indication the operator cannot separate from a response to
  the injected current, and the run then records a disturbance that the
  harness never caused.
- The stepping is geometric, not uniform. Each increment is a permitted
  fraction of the frequency it starts from, so the step grows with
  frequency and the same proportional resolution is held from the bottom
  of the range to the top. A uniform increment sized for the top of the
  range steps clean over whole sub-bands at the bottom.
- The top of the range is always stepped on explicitly. A geometric
  progression overshoots it, and truncating at the last step below the top
  quietly shortens the range the test covers.
- The dwell is set by the unit, not by the operator's patience. It has to
  outlast the slowest response the unit can make and hold enough monitor
  samples for a short upset to be seen at all, and it can never fall below
  any floor the test plan states outright. Three quantities compete and the
  longest wins.
- Drive is requested in current but paid for in power. The calibration
  fixture fixes how much injected current a given forward power produces,
  so the required level becomes a forward power through that calibration,
  and the amplifier either has that power or it does not.
- A step that never reached the required level is not a pass. Nothing was
  seen because nothing strong enough was applied, so the step carries no
  immunity result at all and saying otherwise is the most common way a
  short amplifier is hidden in a report.
- An indication is graded against the required level, never against what
  the amplifier managed. An indication appearing below the required level
  is a susceptibility; one appearing at the level is a pass carried as a
  limitation, because the next build or the next bundle lay will move it.
- Modulation states multiply the run. Every state dwelled on at every step
  is a separate exposure, and a duration budget that counts the steps once
  understates the run by exactly that factor.

## Workflow

1. Validate the range, the step fraction, the required injection current
   and the calibration factor; a non-positive frequency, an inverted range
   or a zero calibration is an input error.
2. Grade the warm-up dwell against the settling time the unit needs, as
   settled, sitting on the bound, or short.
3. Build the stepped frequency list from the bottom of the range upward,
   raising each frequency by the permitted fraction of itself and closing
   on the top of the range exactly.
4. Size the dwell from the response time, the monitor sampling and the
   declared floor, and compare it with the dwell the procedure claims.
5. Convert the required injection current into the forward power the
   calibration demands, compare it with the amplifier limit, and cap the
   delivered current when the limit bites.
6. Categorize every step from what was delivered and what was seen:
   immune, sitting on the required level, susceptible, or carrying no
   result because the level was never reached.
7. Total the run over the steps, the dwell and every modulation state, and
   aggregate findings and limitations. The procedure stands only when no
   finding stands.

## Pitfalls

- Starting the sweep as soon as the unit powers up. The settling dwell is
  what makes a later indication attributable to the injection.
- Stepping with a uniform increment. It is either impractically fine at
  the top of the range or blind to whole sub-bands at the bottom.
- Stopping at the last geometric step below the top of the range, so the
  decade the requirement cares most about is never stepped on.
- Setting the dwell from the monitor rate alone and finding it shorter
  than the unit's own response, so a slow upset arrives after the run has
  already moved to the next frequency.
- Reporting a quiet step as immune when the amplifier never delivered the
  required current. The step has no result, and the limitation belongs in
  the report rather than in the pass column.
- Grading an indication against the delivered current instead of the
  required level, which flatters a run whose drive was short.
- Budgeting the run on the step count alone when two or three modulation
  states are dwelled on at each step.

## Behavior contract (gate 3)

The range and calibration validation, warm-up grading, geometric step-list
construction, dwell sizing, forward-power conversion and amplifier cap,
four-valued step grading and the run duration budget are exercised by the
gate 3 contract test:
scripts/test_e2007_cable_injection_susceptibility_procedure.py against
scripts/e2007_cable_injection_susceptibility_procedure_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_cable_injection_susceptibility_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
