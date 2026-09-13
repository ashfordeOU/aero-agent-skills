---
name: e2001-multicarrier-analysis-margins
description: "Use when determine the nominal multipactor-analysis-margins of ECSS-E-ST-20-01C clause 4.7.2.2 for a multicarrier radio-frequency unit: build the multicarrier peak-envelope-power from the individual carrier-powers, categorize the unit against the recognized equipment-type list, resolve its design-heritage level, look up the nominal analysis-margin that pair owes, accumulate the declared margin-contributions (geometry-tolerance, secondary-emission-yield-uncertainty, field-solver-uncertainty, carrier-phasing-uncertainty) into one applied analysis-margin, then verify that it covers the required value and report the per-contribution shortfall where it does not. Trigger: ecss, e-st-20-electrical-scope, multicarrier-analysis-margin, multipactor-margin-contribution, peak-envelope-power, design-heritage-margin, equipment-type-categorisation, secondary-emission-yield-uncertainty."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multicarrier-analysis-margins, multicarrier-analysis-margin, multipactor-margin-contribution, peak-envelope-power, design-heritage-margin, equipment-type-categorisation, secondary-emission-yield-uncertainty]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Multicarrier Analysis Margins (space-systems/ecss/e2001-multicarrier-analysis-margins)

Use when the task is the nominal analysis margin of ECSS-E-ST-20-01C
clause 4.7.2.2 -- how much margin a multicarrier multipactor analysis
has to carry above the operating condition, resolved contribution by
contribution, against the equipment type being assessed and the design
heritage behind it.

## Domain quick reference

- Multicarrier operation changes the operating condition the margin is
  taken against. Several carriers sharing one gap drift in and out of
  phase; at the instant they align, their voltages add, so the envelope
  power reaches the square of the sum of the carrier root-powers. For
  equal carriers that is the carrier count squared times one carrier --
  eight equal carriers peak at eighteen decibel above one of them, not
  at nine. The margin is applied to that peak envelope, never to the
  summed average.
- The nominal analysis margin is not one number for the whole unit. It
  is resolved from two indices. The first is the equipment type: a
  high-power transmit chain or an output multiplexer, where the field
  is largest and the consequence of a discharge is a lost channel,
  owes more than a waveguide or coaxial passive component, which in
  turn owes more than a low-power receive chain.
- The second index is design heritage. A recurring item already flown
  in a comparable configuration owes the base margin; a modified design
  owes an increment because the modification invalidates part of the
  flight evidence; a wholly new design owes the largest increment
  because nothing has been demonstrated on orbit at all.
- The applied margin is itself a sum of contributions, each one a named
  uncertainty rather than an unexplained allowance: manufacturing
  geometry-tolerance on the critical gap, secondary-emission-yield
  spread of the electrode surface, field-solver uncertainty on the
  computed field, carrier-phasing uncertainty on the envelope
  statistics, plus optional thermal-drift, power-measurement and
  surface-treatment terms. A multicarrier analysis that declares no
  carrier-phasing contribution has not addressed the multicarrier
  question at all.
- Each contribution carries a credibility floor -- the smallest value
  that can still be defended for that physical effect -- and a ceiling
  above which the number is a modelling error rather than a margin.
  Both bounds are findings about the declaration, separate from whether
  the total covers the requirement.

## Workflow

1. Collect the carrier set for the case and build the peak envelope
   power by in-phase voltage addition. Refuse a set with fewer than two
   carriers: that is the single-carrier clause, not this one.
2. Categorize the unit against the recognized equipment-type list and
   resolve its design-heritage level. An unrecognized equipment type or
   heritage level stops the case -- there is no default margin to fall
   back on.
3. Add the heritage increment to the equipment-type base to obtain the
   required nominal analysis margin in decibel.
4. Normalize every declared margin contribution: recognized category,
   real non-negative value, below the single-contribution ceiling, no
   category declared twice. Sum them into the applied margin.
5. Raise a finding for each mandatory contribution that was never
   declared and for each contribution sitting below its credibility
   floor. A contribution landing exactly on its floor is compliant --
   the comparison absorbs representation error rather than moving the
   floor.
6. Compare applied against required. A margin landing exactly on the
   requirement passes, again absorbing floating-point error; otherwise
   report the shortfall in decibel.
7. Derive the power level the analysis must actually cover: the peak
   envelope raised by the required margin. That is the number the field
   analysis and the threshold comparison are run at.
8. Aggregate. The unit clears clause 4.7.2.2 only when every case both
   covers its requirement and carries no declaration finding.

## Pitfalls

- Applying the margin to the summed average power of the carriers.
  Multipactor responds to the instantaneous field, so the operating
  condition is the in-phase envelope peak; averaging understates it by
  ten log of the carrier count and quietly consumes the whole margin.
- Reading a covered total as a clean result while a mandatory
  contribution is missing. A large geometry-tolerance term can make the
  sum look healthy with no carrier-phasing term declared at all -- the
  total passes and the multicarrier physics was never addressed.
- Carrying one unit-wide margin number. The clause resolves the margin
  per equipment type and per heritage; a single project-wide value
  over-margins the receive chain and under-margins the transmit chain
  at the same time.
- Treating a modified design as recurring because most of it is
  unchanged. The increment exists precisely because the modification
  invalidates part of the flight evidence, and the gap geometry is
  usually what the modification touched.
- Inflating a single contribution to absorb an unexplained difference.
  Above the single-contribution ceiling the number stops describing an
  uncertainty and starts hiding a modelling error, so it is refused
  rather than summed.
- Letting a total that lands one bit below its requirement read as a
  failure. When the applied margin is a sum of decimal contributions
  the binary sum can fall a few units in the last place short; the
  logic absorbs that, and the engineering limit stays where the
  standard put it.

## Behavior contract (gate 3)

The peak-envelope-power construction, equipment-type and
design-heritage resolution, contribution normalization and
accumulation, credibility-floor and ceiling findings, applied-versus-
required comparison, analysis power-level derivation and unit-level
verdict are exercised by the gate 3 contract test:
scripts/test_e2001_multicarrier_analysis_margins.py against
scripts/e2001_multicarrier_analysis_margins_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_multicarrier_analysis_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
