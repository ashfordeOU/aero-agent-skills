---
name: e2008-diode-characterization-acceptance-process
description: "Use when a diode current-voltage recording is being set up or an as-run one judged. Design the dark forward and reverse current-voltage recording a protection diode acceptance characterisation runs under ECSS-E-ST-20-08C clause 9.4.5.2.2: refuse a bench whose stray irradiance leaves the diode still photo-responsive, size the supply compliance limit so it clears the highest forward test current yet stays under what the part survives, build the forward and reverse sweep schedules against their step rules, flag every recorded point the source held at its own limit rather than the diode setting, and confirm the forward curve rises across the swept range. Trigger: ecss, e-st-20-08c-clause-9-4-5-2-2, protection-diode-dark-iv-recording, diode-supply-compliance-limit-sizing, dark-condition-stray-irradiance-floor, supply-limited-point-detection, diode-sweep-schedule-step-rule."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-characterization-acceptance-process, protection-diode-dark-iv-recording, diode-supply-compliance-limit-sizing, dark-condition-stray-irradiance-floor, supply-limited-point-detection, diode-sweep-schedule-step-rule]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Protection Diode Characterisation Process (space-systems/ecss/e2008-diode-characterization-acceptance-process)

Use when the task is to set up, or to judge as run, the dark forward
and reverse current-voltage recording of ECSS-E-ST-20-08C clause
9.4.5.2.2 -- the two bench conditions that decide whether the recording
is a diode measurement at all, the two sweep schedules, and which of
the recorded points are data rather than the source talking about
itself.

## Domain quick reference

- Two bench conditions carry the whole clause. The diode is measured in
  darkness and it is driven from a supply whose current is limited.
  Everything else is arithmetic on the numbers those two conditions let
  the bench produce.
- Darkness is not housekeeping. A protection diode on a photovoltaic
  assembly sits in the plane of the cells and shares their optical
  path, so light on it adds a photocurrent to every reading. That
  photocurrent is largest relative to the signal exactly where the
  signal is smallest -- the reverse branch, whose entire purpose is to
  read a leakage floor.
- The forward branch is an exponential, which is why the supply limit
  exists. A source with no limit walks past the knee within one step
  and the part is gone before the reading settles.
- The compliance limit is therefore sized from two sides at once. It
  has to clear the highest forward test current with headroom, or the
  top of the sweep is the source rather than the diode, and it has to
  stay well under the current the part survives, or it is not a
  protection.
- A reading sitting at the compliance limit is not a diode datum. It
  records where the source stopped. Those points are named, never
  averaged into the curve and never fitted through.
- The two branches take different step rules because they resolve
  different things. The forward branch resolves a knee in tens of
  millivolts; the reverse branch walks a flat leakage floor to the
  working reverse voltage and can step in volts.
- A forward current that falls as the applied voltage rises is not a
  noisy reading, it is a broken one -- a connection, a thermal runaway
  or a swapped lead -- and no averaging repairs it.

## Workflow

1. Validate the recording policy first: dark floor, compliance headroom
   and rating share, the two step rules, and the tolerance that decides
   when a point counts as held at the limit.
2. Check the dark condition before anything else, and stop there when
   it fails. Every downstream number is contaminated by the photocurrent
   the light adds, so a schedule check on a lit bench reports a result
   that means nothing.
3. Size the compliance limit from both sides: safe against the current
   the part survives first, because an unsafe setting can destroy the
   article the rest of the flow is about; then adequate against the top
   of the forward sweep.
4. Build the forward and the reverse schedules from their own start,
   stop and step, always reaching the declared stop value even when the
   span is not a whole number of steps.
5. Measure the widest gap each schedule leaves and hold it against that
   branch's step rule. A gap landing exactly on the rule passes; the
   comparison tolerance absorbs representation error and the rule does
   not move.
6. When an as-run forward curve is supplied, name every point held at
   the supply limit and check the current never falls across the swept
   range, reporting both defects when both are present.
7. Close on one verdict: dark condition not met, supply limit unsafe,
   supply limit insufficient, sweep schedule inadequate, curve recording
   invalid, or curves recorded.

## Pitfalls

- Treating darkness as a tidiness rule. The photocurrent it excludes is
  the same order as the leakage the reverse branch exists to measure,
  so a lit bench does not degrade the reverse result, it replaces it.
- Sizing the compliance limit only against the part rating. A setting
  that is safe but below the top of the forward sweep clips the
  readings that matter most, and the curve then shows a flat top the
  diode never had.
- Sizing it only against the sweep. A limit generous enough to reach
  every planned point and close to the part rating protects nothing,
  which is the failure mode that costs the article.
- Fitting through a point held at the supply limit. It is a fact about
  the source, and a fit that includes it drags the whole knee with it.
- Using one step rule for both branches. The forward knee needs tens of
  millivolts and the reverse floor does not, so a shared step either
  misses the knee or spends the whole session walking a flat line.
- Averaging a falling forward reading away. Current that falls as
  voltage rises names a broken connection, a runaway or a reversed
  lead, and the repair is on the bench, not in the arithmetic.

## Behavior contract (gate 3)

The policy validation, the dark-condition check, both sides of the
compliance sizing, schedule construction to an uneven stop, widest-gap
measurement against each branch's step rule, supply-limited point
detection, the rising-curve check, and the recording verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_diode_characterization_acceptance_process.py against
scripts/e2008_diode_characterization_acceptance_process_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_diode_characterization_acceptance_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
