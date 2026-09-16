---
name: e2008-protection-diode-switching-test
description: "Use when a protection diode switching transient campaign is written or audited. Evaluate whether a protection diode survives the switching transients of ground handling and in-orbit string switching under ECSS-E-ST-20-08C clause 9.6.17: derive the overshoot the stray inductance throws up as the current is interrupted, add it to the standing rail, hold that peak against the derated reverse standoff, take the field energy the switched string dumps into the junction with the clamp power and duration it empties at, step the junction through the transient thermal impedance, and hold each event category to its own pulse count. Trigger: ecss, e-st-20-08c-clause-9-6-17, protection-diode-switching-transient, diode-stray-inductance-overshoot, diode-derated-reverse-standoff, diode-absorbed-pulse-energy, diode-switching-junction-excursion, protection-diode-event-pulse-count."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-protection-diode-switching-test, protection-diode-switching-transient, diode-stray-inductance-overshoot, diode-derated-reverse-standoff, diode-absorbed-pulse-energy, diode-switching-junction-excursion, protection-diode-event-pulse-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Protection Diode Switching Test (space-systems/ecss/e2008-protection-diode-switching-test)

Use when the task is clause 9.6.17 of ECSS-E-ST-20-08C -- whether a
protection diode comes through the transients that switching produces,
first on the ground while connectors are made and broken by hand, then
in orbit while a sequencer switches strings for years. Nothing on an
array switches cleanly, and the part that catches what the switch throws
off is by design the diode.

## Domain quick reference

- The overshoot is the stray inductance times the rate the current is
  interrupted at. It is not a small correction; on a long harness broken
  quickly it can exceed the rail it adds to, and it is the quantity that
  reaches the breakdown voltage first.
- The standoff the design may use is the derated one, not the face
  rating. A rating used at its printed value carries no margin, so the
  peak is held against the rating times the derating factor, and a
  factor looser than the policy allows is itself a finding.
- The margin is reported as a fraction of the derated standoff so parts
  of different ratings can be compared on one scale. A negative fraction
  means the transient has already taken the junction into breakdown.
- Energy and voltage are separate failure paths. The peak decides
  whether the junction breaks down; the field energy of the switched
  string, half the inductance times the square of the current, decides
  how hot it gets doing so. A part can pass one and fail the other.
- The clamp lasts as long as it takes to empty that energy at the peak
  clamp power, which is the peak voltage carried at the switched
  current. Microseconds, typically -- which is why the thermal path is a
  transient impedance rather than a steady-state resistance.
- The excursion is a step on top of the case temperature, so the same
  device passes cold and fails hot. Both the step and where it lands
  carry a limit.
- Ground handling and in-orbit switching are different populations. They
  differ in slew rate, in switched current and in how often they happen,
  so pulses of one category never fill the count of the other.
- Pulses need a recovery interval. Fired faster than the package sheds
  one step, the excursions stack and the test measures an accumulation
  the clause did not ask for.

## Workflow

1. Validate the switching policy first: derating cap, standoff margin
   floor, excursion and junction ceilings, the two pulse counts and the
   recovery interval. A derating cap above one or a margin floor of one
   is refused rather than used.
2. Derive the overshoot from the stray inductance and the current slew
   rate, add the standing rail, and derate the reverse standoff before
   any comparison is made.
3. Take the margin as the unused share of the derated standoff. A margin
   landing exactly on the floor passes; the comparison tolerance absorbs
   representation error and the floor does not move.
4. Derive the absorbed field energy, the peak clamp power, the clamp
   duration that energy empties in, and the junction excursion that
   power produces through the transient thermal impedance. Add the
   excursion to the case temperature.
5. Count the pulses each recognised event category actually declares,
   refusing a category the plan invents, and hold each count against its
   own floor. Report every finding, not the first.
6. Close on one verdict, breakdown outranking the rest because it ends
   the part in one pulse: switching breakdown risk, junction excursion
   excessive, event plan deficient, or switching survival accepted.

## Pitfalls

- Sizing the diode against the rail alone. The rail is the number on the
  drawing; the overshoot is what arrives, and on a long harness
  interrupted quickly it is the larger of the two.
- Taking the reverse rating at face value. An undated margin of zero is
  not a margin, and the derating factor is exactly the quantity a review
  is meant to see applied.
- Treating a positive margin as a pass on its own. Voltage and energy
  fail the part by different routes, and a junction can stand the peak
  while the clamp cooks it.
- Using a steady-state thermal resistance for a microsecond pulse. The
  package has not begun to conduct heat away on that timescale, and the
  steady-state figure understates the step by an order of magnitude.
- Judging the excursion without the case it sits on. The same step is
  harmless on a cold panel and past the ceiling on a hot one, so the
  peak junction temperature is checked as well as the step.
- Letting in-orbit pulses count towards ground handling. Handling
  transients come from an uncontrolled break by hand, in-orbit ones from
  a sequencer at a known current; neither substitutes for the other and
  the counts are kept apart.
- Firing the pulse train faster than the package recovers. The
  excursions then stack, and the campaign reports an accumulation
  failure as a single-pulse failure.
- Comparing a derived margin or excursion against a limit by bare
  arithmetic. These come out of products and divisions that land a few
  units in the last place either side of a limit on different hosts, so
  the comparison absorbs that error while the limit itself is never
  relaxed.

## Behavior contract (gate 3)

The policy validation, inductive overshoot, transient peak, derated
standoff and margin fraction, the absorbed pulse energy, peak clamp
power and clamp duration, the junction excursion and peak junction
temperature, the per-category pulse counts and recovery interval checks,
and the switching verdict are exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_switching_test.py against
scripts/e2008_protection_diode_switching_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_protection_diode_switching_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
