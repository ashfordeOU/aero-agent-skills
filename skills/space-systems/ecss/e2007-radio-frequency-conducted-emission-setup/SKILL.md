---
name: e2007-radio-frequency-conducted-emission-setup
description: "Use when derive the bench arrangement for an ECSS-E-ST-20-07C clause 5.4.3.3 conducted-emission run from the general equipment configuration: apply each declared method delta to the baseline geometry, refuse an unknown delta or one that collapses an allowed band, compare the realized lead length, lead height above the ground-plane, probe-to-connector distance, harness separation and bond resistance against their bands, categorize every parameter as conforming, a declared deviation or nonconforming, confirm the bond and routing provisions, and return the governing parameter with the setup verdict. Trigger: ecss, e-st-20-07c, rf-conducted-emission-setup, derived-bench-arrangement, power-lead-routing-geometry, current-probe-placement-distance, ground-plane-bond-resistance, setup-deviation-categorization."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radio-frequency-conducted-emission-setup, rf-conducted-emission-setup, derived-bench-arrangement, power-lead-routing-geometry, current-probe-placement-distance, ground-plane-bond-resistance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radio-Frequency Conducted Emission, Bench Arrangement (space-systems/ecss/e2007-radio-frequency-conducted-emission-setup)

Use when the task is the setup clause of ECSS-E-ST-20-07C clause
5.4.3.3 -- building the bench for a higher-band conducted-emission run.
The clause does not describe a bench from nothing: it starts from the
general equipment arrangement the discipline uses everywhere and states
what this method changes about it, so the arrangement is derived, then
the realized bench is graded against what was derived.

## Domain quick reference

- The arrangement is a derivation, not a fresh drawing. Every
  parameter starts at its general-configuration value and moves only
  where the method declares a delta. That distinction is what makes a
  bench reviewable: a reader can see which numbers the method chose
  and which it inherited.
- A delta moves a bound; it never changes what kind of bound a
  parameter has. A length with a nominal and a tolerance stays a
  nominal-and-tolerance parameter, and a bond resistance stays a
  ceiling. A delta that rewrites the kind, names a parameter the
  arrangement does not have, or shrinks a tolerance to nothing is
  refused at derivation time rather than found mid-run.
- Geometry is the measurement. Lead length sets the resonances that
  land inside the band, height above the ground-plane sets the
  lead-to-plane capacitance, and the probe's distance from the
  connector decides how much of the lead is between the source and
  the clamp. These are not housekeeping numbers; moving any of them
  moves the recorded level.
- Separating the power leads from the signal harness is a provision,
  not a tolerance. Either the routing keeps them apart or the reading
  carries coupled harness current that no correction recovers.
- A parameter out of its band is a finding unless a formally accepted
  departure covers it, in which case it is carried as a limitation
  and stays visible in the record. Silently widening the band to
  absorb the bench that was actually built is the failure this
  grading exists to prevent.
- The governing parameter is the one furthest outside its band. It is
  what the bench rework is aimed at, and it is reported even when the
  setup conforms so that the margin is known.

## Workflow

1. Derive the arrangement: copy the general configuration, then apply
   each declared delta, refusing an unknown parameter, a kind change,
   an unknown field or a collapsed band.
2. Normalize the realized bench record, rejecting a parameter given
   twice under two spellings and a record that omits a parameter the
   arrangement carries.
3. Validate the provisions: every one declared, every value a
   boolean, and no invented provision accepted.
4. For each parameter compute the signed distance outside its allowed
   band, absorbing representation error at a band edge with a named
   tolerance so a value sitting exactly on the edge reads as inside.
5. Categorize each parameter as conforming, a declared deviation or
   nonconforming, and count the categories.
6. Reduce to the governing parameter by the largest absolute
   deviation, breaking an exact tie on the parameter name so the
   result is reproducible.
7. Report the verdict with its findings (nonconforming parameters,
   absent provisions) and its limitations (declared deviations). The
   setup conforms only when no finding stands.

## Pitfalls

- Writing the bench down as an absolute specification. Doing that
  hides which numbers the method actually changed, and the next
  reviewer cannot tell a deliberate delta from a transcription slip.
- Letting a delta widen a tolerance so the bench that was built
  passes. That is the departure being buried in the arrangement
  instead of declared against it.
- Clamping the probe around the pair of leads rather than one lead.
  The currents then partly cancel and the reading understates the
  emission by an amount nothing in the record reveals.
- Treating lead height as cosmetic. The lead-to-plane capacitance
  moves with it, which moves the resonances the method is looking
  for.
- Reading a value sitting exactly on a band edge as outside because
  the subtraction landed a few units in the last place over. That is
  a representation question, handled by the tolerance inside the
  comparison.

## Behavior contract (gate 3)

The arrangement derivation, delta refusal, bench-record
normalization, provision validation, band-deviation computation,
parameter categorization and governing-parameter reduction are
exercised by the gate 3 contract test:
scripts/test_e2007_radio_frequency_conducted_emission_setup.py
against
scripts/e2007_radio_frequency_conducted_emission_setup_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radio_frequency_conducted_emission_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
