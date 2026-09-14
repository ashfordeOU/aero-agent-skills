---
name: e2008-coverglass-electro-optical-properties
description: "Use when a coated coverglass has been probed and its electro-optical resistivity must be reduced and dispositioned. Derive the bulk and surface resistivity behaviour of a coated coverglass per ECSS-E-ST-20-08C clause 8.7.3: reduce bulk volume resistivity from guarded-electrode resistance, electrode area and specimen thickness, reduce surface resistivity from the concentric-ring or rectangular-bar geometry factor, confirm both properties are present before a component counts as characterized, judge a conductive coating against its surface resistivity ceiling and the bulk figure against its declared band, and report the spread across the measured articles. Trigger: ecss, e-st-20-08c, clause-8-7-3, coverglass-bulk-volume-resistivity, coverglass-surface-resistivity-ceiling, coverglass-guarded-electrode-reduction, coverglass-coating-electro-optical-characterization, coverglass-resistivity-declared-band."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-electro-optical-properties, coverglass-bulk-volume-resistivity, coverglass-surface-resistivity-ceiling, coverglass-guarded-electrode-reduction, coverglass-coating-electro-optical-characterization, coverglass-resistivity-declared-band, solar-cell-assembly-charge-bleed]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Electro-Optical Properties (space-systems/ecss/e2008-coverglass-electro-optical-properties)

Use when the task is the electro-optical property characterization of
ECSS-E-ST-20-08C clause 8.7.3 -- reducing the bulk and the surface
resistivity of a coated coverglass component from the raw measurement and
judging both against what the drawing fixes.

## Domain quick reference

- Behaviour here means two numbers, not one. Bulk volume resistivity
  describes the path straight through the glass from the outer face to the
  cell; surface resistivity describes the path sideways along the outer
  face. A component is characterized only when both are present, and one
  figure with a promise about the other closes the assessment as
  incomplete rather than passing on the half that was measured.
- Bulk resistivity comes out of a guarded-electrode reading as the
  measured resistance times the electrode area divided by the specimen
  thickness. The guard ring is what keeps the surface path out of the
  result; without it the reading is a parallel combination of the two
  properties this clause wants separated.
- Surface resistivity comes out as the measured resistance times a
  geometry factor set by the electrode arrangement: two pi over the
  natural log of the radius ratio for concentric rings, electrode width
  over electrode gap for parallel bars. The same resistance on two
  different fixtures is two different sheet resistivities.
- The two properties have opposite senses, and that is the trap. Bulk
  resistivity is wanted inside a declared band -- too low is a leakage
  path to the junction, and a value far above the band is usually the
  instrument's range limit reported as a measurement. Surface resistivity
  on a coated part is wanted at or below a ceiling, because the coating
  exists to bleed deposited charge sideways to the frame instead of
  letting it build to an arc.
- The ceiling belongs to the coating, not to the glass. An uncoated
  coverglass carries no charge-bleed duty, so its surface figure is
  characterization only; applying the coated ceiling to it fails a part
  that was never required to pass.
- Spread across the measured articles is a separate reading from the
  verdict. Articles that differ by orders of magnitude are a real finding
  about process control even when every one of them sits inside its band,
  so the spread is reported in decades as an advisory beside the verdict.

## Workflow

1. Take the drawing-fixed band and ceiling. With no drawing reference
   behind them there is nothing to judge against, and the assessment
   closes there rather than passing.
2. Reduce each article. Accept an already-reduced resistivity when one is
   supplied, otherwise compute it from the raw geometry: resistance, area
   and thickness for bulk; resistance and the arrangement's geometry
   factor for surface.
3. Name any article missing either property and stop on an incomplete
   property set before judging anything against a band.
4. Confirm a surface ceiling exists whenever a coated article is present.
   A coated part with no declared ceiling cannot be judged on the duty its
   coating was applied for.
5. Judge each bulk figure inside the band and each coated surface figure
   at or below the ceiling. Report an uncoated article's surface figure as
   characterization only.
6. Compute the bulk and surface spread across the articles in decades and
   advise when either runs beyond the expectation.
7. Roll up: outside-band identifiers, the incomplete identifiers, the two
   spread figures and the verdict.

## Pitfalls

- Reporting one property and calling the component characterized. The
  clause asks for the pair, and the pair is what a charging analysis
  needs.
- Measuring bulk resistivity without a guard. The unguarded reading mixes
  the surface path into the volume result and flatters neither.
- Reusing a geometry factor across fixtures. The ring factor depends on
  the radius ratio and the bar factor on the width-to-gap ratio; a fixture
  change moves the sheet resistivity without the resistance moving.
- Inverting the sense of the surface limit. High sheet resistivity is the
  failure mode for a charge-bleed coating, not the goal.
- Holding an uncoated coverglass to the coated ceiling, or holding a
  coated one to nothing because no ceiling was declared.
- Accepting a bulk value sitting far above the band as a good result. That
  is usually the instrument saturating, and it deserves the same finding
  as a value below the band.
- Reading a tight subgroup as good process because every article passed.
  The spread in decades is the figure that sees a drifting coating line.
- Comparing a reduced resistivity with a band edge by bare arithmetic. The
  figure is a product and a quotient of measured quantities and, on the
  ring fixture, a natural log as well, so a value that should sit exactly
  on an edge can evaluate a few units in the last place outside it; the
  comparison absorbs that representation error while the edge stays
  untouched.

## Behavior contract (gate 3)

The guarded-electrode bulk reduction, both surface geometry factors, the
both-properties-present rule, the band and ceiling judgements, the
uncoated-article exemption and the decade spread advisories are exercised
by the gate 3 contract test:
scripts/test_e2008_coverglass_electro_optical_properties.py against
scripts/e2008_coverglass_electro_optical_properties_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_electro_optical_properties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
