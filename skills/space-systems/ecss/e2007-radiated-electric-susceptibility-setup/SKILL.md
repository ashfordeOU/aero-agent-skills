---
name: e2007-radiated-electric-susceptibility-setup
description: "Derive and grade the chamber arrangement for an ECSS-E-ST-20-07C clause 5.4.11.3 radiated electric susceptibility exposure: apply each declared method delta to the baseline geometry, refuse a delta that collapses an allowed band, compute the footprint the antenna projects at the unit plane from its separation and beamwidth, confirm the unit face and the exposed harness both stand inside it, grade separation, boresight height, harness height, probe offset, absorber clearance and bond resistance against their bands, categorize each as conforming, a declared deviation or nonconforming, and return the governing parameter with the verdict. Use when building or reviewing a radiated susceptibility chamber setup. Trigger: ecss, e-st-20-07c, radiated-electric-susceptibility-setup, radiated-susceptibility-chamber-arrangement, uniform-field-footprint-coverage, exposed-harness-illumination, susceptibility-antenna-separation, radiated-field-probe-placement."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-susceptibility-setup, radiated-susceptibility-chamber-arrangement, uniform-field-footprint-coverage, exposed-harness-illumination, susceptibility-antenna-separation, radiated-field-probe-placement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Susceptibility, Chamber Arrangement (space-systems/ecss/e2007-radiated-electric-susceptibility-setup)

Use when the task is the setup clause of ECSS-E-ST-20-07C clause
5.4.11.3 -- standing the unit and the harness that leaves it inside the
field an antenna throws down a shielded chamber, and then showing that
the arrangement actually built is the arrangement that was derived.

## Domain quick reference

- The arrangement is a derivation, not a fresh drawing. Every parameter
  starts at its baseline chamber value and moves only where the method
  declares a delta. A reader can then see which numbers the method chose
  and which it inherited, which is what makes a chamber reviewable.
- A delta moves a bound; it never changes what kind of bound a parameter
  has. A separation with a nominal and a tolerance stays that, a bond
  resistance stays a ceiling and an absorber clearance stays a floor. A
  delta that rewrites the kind, names a parameter the arrangement does
  not carry, or shrinks a tolerance to nothing is refused at derivation
  time rather than found halfway through a sweep.
- The harness is part of the unit under test here, not cabling that
  happens to be attached. Most of the energy that upsets a box arrives
  down its leads, so a run that illuminates the front face and leaves the
  harness in shadow has tested the enclosure and nothing else.
- The illuminated footprint is computed, never assumed. The half-power
  beam subtends a fixed angle at the antenna, so the span it covers at
  the unit plane grows with separation: 2*d*tan(beamwidth/2). A wide unit
  in a short chamber cannot be covered at any drive level, because the
  shortfall is geometric and power does not widen a beam.
- Backing the antenna off widens the footprint and lowers the field, so
  separation trades coverage against the amplifier. That trade is the
  reason separation is usually the governing parameter when a chamber is
  reworked.
- A parameter outside its band is a finding unless a formally accepted
  departure covers it, in which case it is carried as a limitation and
  stays visible in the record. Widening the band to absorb the chamber
  that was actually built is the failure this grading exists to prevent.
- The governing parameter is the one furthest outside its band. It is
  what rework is aimed at, and it is reported even when the arrangement
  conforms, so the margin is known before the exposure starts.

## Workflow

1. Derive the arrangement: copy the baseline chamber, then apply each
   declared delta, refusing an unknown parameter, a kind change, an
   unknown field or a collapsed band.
2. Normalize the realized chamber record, rejecting a parameter given
   twice under two spellings and a record that omits a parameter the
   arrangement carries.
3. Validate the provisions: every one declared, every value a boolean,
   and no invented provision accepted.
4. Compute the illuminated span from the realized separation and the
   beamwidth, and compare it with the span the unit face and the harness
   beside it occupy.
5. For each parameter compute the signed distance outside its allowed
   band, absorbing representation error at a band edge with a named
   tolerance so a value sitting exactly on the edge reads as inside.
6. Categorize each parameter as conforming, a declared deviation or
   nonconforming, and count the categories.
7. Reduce to the governing parameter by the largest absolute deviation,
   breaking an exact tie on the parameter name so the result is
   reproducible.
8. Report the verdict with its findings (nonconforming parameters,
   absent provisions, a footprint that does not reach) and its
   limitations (declared deviations).

## Pitfalls

- Treating the harness as cabling and routing it behind the unit, out of
  the beam. The lead coupling the clause exists to exercise is then never
  exercised, and the run reads clean.
- Assuming the footprint from the chamber drawing instead of computing it
  from the separation actually set. Half a metre of separation lost to a
  cable tray costs span across the whole unit plane.
- Raising the drive to cover a unit wider than the beam. The shortfall is
  geometric; more power raises the level in the middle and leaves the
  edges exactly as dark.
- Letting a delta widen a tolerance so the chamber that was built passes.
  That is a departure buried in the arrangement instead of declared
  against it.
- Parking the field probe where the unit shadows it, so the level logged
  is the level behind the unit rather than the level on it.
- Reading a value sitting exactly on a band edge as outside because the
  subtraction landed a few units in the last place over. That is a
  representation question, handled by the tolerance inside the comparison.

## Behavior contract (gate 3)

The arrangement derivation, delta refusal, chamber-record normalization,
provision validation, illuminated-footprint computation and coverage
reduction, band-deviation computation, parameter categorization and
governing-parameter reduction are exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_susceptibility_setup.py against
scripts/e2007_radiated_electric_susceptibility_setup_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_susceptibility_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
