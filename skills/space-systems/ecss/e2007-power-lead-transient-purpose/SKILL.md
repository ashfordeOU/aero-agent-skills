---
name: e2007-power-lead-transient-purpose
description: "Verify that the aim of ECSS-E-ST-20-07C clause 5.4.9.1 is actually demonstrated: that a unit keeps performing while the brief transients its supply carries are applied to its power leads. Use when injected supply-transient records are judged: validate each pulse, take its signed peak and its half-amplitude width by interpolating the crossings, integrate the volt-second area it delivers, compare the applied stress with the level the interface specifies and refuse an under-driven pulse as proof of anything, categorize the observed behaviour against the allowed performance category, reduce every lead to its worst event and name the governing one, and report the polarity and repeat coverage. Trigger: ecss, e-st-20-07c, power-lead-transient-purpose, supply-transient-immunity, transient-half-amplitude-width, transient-volt-second-area, transient-applied-stress-margin, transient-performance-category, transient-polarity-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-power-lead-transient-purpose, supply-transient-immunity, transient-half-amplitude-width, transient-volt-second-area, transient-applied-stress-margin, transient-performance-category, transient-polarity-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Power-Lead Transient Purpose (space-systems/ecss/e2007-power-lead-transient-purpose)

Use when the task is the aim of ECSS-E-ST-20-07C clause 5.4.9.1 -- deciding
whether a set of injected transient records actually shows that a unit goes
on performing as specified while the brief voltage excursions its supply
carries, from switching elsewhere on the bus and from the harness itself,
are applied to its power leads.

## Domain quick reference

- The event is short and the demonstration is about survival, not about the
  steady bus. What the unit has to ride out is an excursion lasting
  microseconds to a few milliseconds, and the interface specifies it by an
  amplitude, a width and a repetition, never by an average.
- Applying less than the specified transient demonstrates nothing. The unit
  survived something smaller, and no argument carries from a smaller pulse
  to a larger one, so an under-driven pulse is a finding against the run
  rather than a pass with a small shortfall.
- Amplitude and area answer different questions. The peak decides whether
  an input stage is taken past its rating; the volt-second area the pulse
  delivers decides whether the input filter and the converter hold the rail
  up through it. A short tall spike and a long modest one can share a peak
  and stress the unit quite differently.
- The width is taken at half amplitude and the crossings are interpolated.
  Counting samples above half amplitude biases the width by up to a sample
  interval at each end, which on a microsecond edge is most of the answer.
- Both polarities are separate events. A positive excursion is caught by
  one set of protection and a negative one frequently reaches further into
  the unit through a return path, so a campaign that applied one polarity
  has covered half the aim.
- The outcome is a category, not a pass mark. No effect, recovery without
  intervention, recovery needing an operator, and damage that stays are
  four different results, and the interface says which of them the unit is
  allowed to reach. Reaching exactly the allowed category is a pass with
  nothing in hand and belongs in the report as such.
- Every lead is judged on its own and the campaign is reduced to its worst
  lead, never to an average across leads. A return lead and a primary lead
  do not see the same event once the decoupling is in the picture.

## Workflow

1. Validate each transient record: at least two samples, times strictly
   advancing, amplitudes finite.
2. Take the signed peak from the record and the polarity from it; refuse a
   record that never leaves zero, and refuse a declared polarity that
   disagrees with the trace.
3. Measure the half-amplitude width by interpolating the first and last
   crossings, and refuse a capture window that does not hold the whole
   pulse.
4. Integrate the volt-second area the pulse delivers on its magnitude.
5. Compare the applied peak with the specified level: comfortably past it,
   sitting on it, or short of it, absorbing representation error at the
   level with a named tolerance rather than by lowering the level.
6. Categorize the observed behaviour against the allowed performance
   category, and compare the achieved width with the specified width when
   one is stated.
7. Count what was applied on each lead in each polarity against the
   required repeats, reduce every lead to its worst event, name the
   governing lead and aggregate findings and limitations. The aim stands
   only when no finding stands.

## Pitfalls

- Accepting a pulse the generator could not quite reach. The result proves
  immunity at the level applied and nothing at the level specified.
- Grading the peak alone and never integrating the pulse, so a long modest
  transient that sags the internal rail passes on amplitude.
- Measuring the width by counting samples above half amplitude instead of
  interpolating the two crossings.
- Applying one polarity because the generator was already set that way,
  and finding the other polarity reaches the unit by a different path on a
  later build.
- Reading a self-recovering upset as no effect because the unit was working
  again by the time anyone looked. The category is what the interface
  allows against, and the two are not the same result.
- Averaging across leads, which hides the one lead that governs.
- Reporting a single repeat as coverage when the interface asks for the
  transient to be applied repeatedly, since a latch-up frequently needs
  more than one attempt to appear.

## Behavior contract (gate 3)

The pulse validation, signed peak and polarity extraction, interpolated
half-amplitude width, volt-second area, applied-stress ratio and margin,
three-valued stress grading, performance-category comparison, per-lead
worst-case reduction and polarity and repeat coverage are exercised by the
gate 3 contract test:
scripts/test_e2007_power_lead_transient_purpose.py against
scripts/e2007_power_lead_transient_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_power_lead_transient_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
