---
name: e2020-load-converter-startup-current
description: "Verify that the DC/DC converters inside a protected load get themselves started without ever drawing more than the current their protection class allows. Use when an ECSS-E-ST-20-20C clause 5.3.2.2.1 load design has to show the internal converters energise inside the class current: build each converter start-up draw from its input capacitance, soft-start ramp and settled draw, lay the release delays on one timeline, read the true aggregate peak instead of summing peaks, and compare against the class current with the project margin taken out. Reports whether a later release order would repair an exceedance or the converter set itself has to change. Trigger: ecss, e-st-20-20c, load-converter-startup-current, converter-soft-start-ramp, converter-inrush-envelope, staggered-converter-release-order, protection-class-current-allowance, load-startup-current-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-load-converter-startup-current, converter-soft-start-ramp, converter-inrush-envelope, staggered-converter-release-order, protection-class-current-allowance, load-startup-current-margin, unit-input-current-envelope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Load Converter Start-up Current (space-systems/ecss/e2020-load-converter-startup-current)

Use when the task is the load start-up obligation of ECSS-E-ST-20-20C
clause 5.3.2.2.1 — showing that the DC/DC converters inside a unit bring
themselves up without the unit ever pulling more current than the class
of its feeding protection allows.

## Domain quick reference

- A load unit is fed through one protective switch of a declared class,
  and that class fixes a current the unit is not allowed to exceed. The
  obligation is on the LOAD: the converters inside it have to start
  themselves inside that figure, so the switch never has to enter
  limitation to bring the unit up at all.
- A converter draws much more while it is starting than once it is
  regulating. Two contributions add: the constant current that charges
  its input capacitance over the soft-start window, C*V/t, and the share
  of its settled input current it is already delivering during the ramp.
  Taking only the settled figure is the common defect and understates
  the start by an order of magnitude on a small converter.
- The unit figure is a TIMELINE question, not a sum. Converters released
  together add their ramp currents; converters released far enough apart
  that one has settled before the next is let go do not. The envelope
  only steps where a converter is released or settles, so those instants
  are the whole profile and its maximum is the unit peak.
- An exceedance has two very different causes and the repair differs.
  If some release order would fit inside the class current, the unit is
  repaired by spreading the releases further apart. If even a strictly
  one-at-a-time release still peaks too high, no sequencing saves it and
  the converter set, the class or the soft-start windows have to change.
- The settled draw is its own check. A unit whose converters together
  draw more than the class current once they are all regulating never
  leaves limitation, and no start-up sequencing addresses that.
- The current margin, the ramp loading fraction and the headroom
  advisory floor are declared project policy rather than physical
  constants; the defaults in the logic module are a starting point a
  project substitutes its own values into.

## Workflow

1. Validate the converter list: unique names, a positive input
   capacitance, a positive soft-start window, a positive settled draw
   and a release delay that is not negative. A converter with no
   declared soft-start window cannot be assessed and is refused rather
   than assumed instantaneous.
2. Build each converter's start-up draw at the bus voltage: charge the
   input capacitance over the soft-start window and add the loaded share
   of its settled draw.
3. Lay every release delay and settling instant on one timeline and read
   the unit input current at each of them. The largest value is the
   aggregate peak, and the instant it falls on names the converters that
   are overlapping.
4. Take the project margin out of the class current to get the current
   the unit may actually draw, and compare the aggregate peak with it.
5. Check the settled draw against the same allowance, and check each
   converter on its own: a single converter already above the allowance
   is a finding no sequencing can clear.
6. When the peak is too high, search the release orders for the best a
   strictly staggered sequence can reach. Report whether re-staggering
   would repair the unit or whether the converter set itself has to
   change.
7. Raise an advisory, not a finding, when a passing unit is left with
   very little headroom above the allowance.

## Pitfalls

- Summing the per-converter peaks. That reports a finding on a properly
  staggered unit that does not have one, because converters released
  after their predecessors have settled never add their ramp currents.
- Taking the largest single converter peak instead. That is the opposite
  error and hides the real finding on a unit that releases everything
  together, where the ramp currents genuinely do add.
- Assessing the converters on their settled input current. The settled
  figure says nothing about the start; the input capacitance and the
  soft-start window are what decide whether the unit starts inside the
  class current.
- Treating an exceedance as a sequencing problem by reflex. Re-staggering
  only helps when some order actually fits; if a strictly one-at-a-time
  release still peaks too high, the answer is a different converter,
  a longer soft-start or a different class.
- Comparing a peak with the allowance by bare arithmetic. A ramp current
  is built by division and the allowance by multiplication, so a case
  meant to sit exactly on the allowance can land a few units in the last
  place the wrong side of it; the comparison absorbs that representation
  error while the class current and the margin stay as specified.

## Behavior contract (gate 3)

The policy validation, converter validation, ramp current, start-up
envelope, staggered release search, per-converter check and the full
clause assessment are exercised by the gate 3 contract test:
scripts/test_e2020_load_converter_startup_current.py against
scripts/e2020_load_converter_startup_current_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_load_converter_startup_current.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
