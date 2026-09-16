---
name: e2008-bare-cell-contact-area-general
description: "Use when a bare-cell mark list has to become a contact area verdict. Evaluate the general condition of the contact areas of a bare solar cell under ECSS-E-ST-20-08C clause 7.5.1.5.1, which wants them clear of digs, scratches and probe marks where the metallisation is absent: place every mark against the contact geometry so an inside, straddling or outside call is made before any disposition, count only the straddling part that overlaps, reject a mark that bares the semiconductor, send metal thinned past its working fraction to review, and track probe witnesses and the disturbed footprint. Trigger: ecss, e-st-20-08c-clause-7-5-1-5-1, bare-cell-contact-area-condition, contact-metallisation-absence, cell-probe-mark-witness-count, contact-area-dig-and-scratch-placement, weldable-surface-disturbed-fraction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-contact-area-general, bare-cell-contact-area-condition, contact-metallisation-absence, cell-probe-mark-witness-count, contact-area-dig-and-scratch-placement, weldable-surface-disturbed-fraction, solar-cell-contact-geometry-containment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bare Cell Contact Area General Condition (space-systems/ecss/e2008-bare-cell-contact-area-general)

Use when the task is the contact-area screen of ECSS-E-ST-20-08C clause
7.5.1.5.1 -- digs, scratches and probe marks have been recorded on a bare
cell and each of them has to be placed against the contact geometry and
dispositioned on the state of the metallisation underneath it.

## Domain quick reference

- Two qualifiers carry the requirement and both go missing in practice. It
  is about contact areas, not the cell face at large, and it is about the
  places where the metallisation is absent, not about marks as such.
- Location comes first and it is a containment test, not a judgement. A mark
  sits inside a contact area, straddles its edge or misses it, and only a
  mark with some overlap is this clause's business at all.
- A straddling mark contributes the overlapping part and nothing else.
  Charging its whole footprint to the contact area inflates every area
  figure that follows it.
- A mark that touches the boundary without crossing it has no overlap, so it
  is outside. The edge itself is not contact area.
- The metallisation state decides the disposition and the mark's own size
  does not. A dig that displaced metal and left a continuous conductor has
  exposed nothing; the same dig that went through has bared semiconductor on
  the surface a weld is about to be made on.
- Thinned metal is the middle case that gets waved through. It is not bare
  and it is not sound, and a contact thinned past a working fraction of its
  deposit is one probe landing or one weld pulse from being bare, so it goes
  to review rather than being accepted because nothing shows through yet.
- A mark that lands nowhere near a contact is a real finding under other
  clauses of the cell inspection and is not a rejection here. It is carried
  as an advisory so it reaches the clause that does own it.
- Two effects survive an area in which every individual mark was admissible.
  Probe witnesses accumulate because the fixture lands on the same sites, so
  they are counted per contact area. And the disturbed footprint accumulates
  too, so an area can be fully metallised and still have had most of its
  weldable surface worked over.
- Overlapping marks are summed rather than unioned for the disturbed
  figure. A site worked twice has taken twice the working, which is the
  quantity the allowance is about.

## Workflow

1. Normalise each contact area into a footprint in the cell coordinate
   frame, rejecting a duplicate identifier on the same cell.
2. Place every recorded mark against every contact area and set aside the
   ones that overlap nothing; carry those as advisories rather than losing
   them.
3. Disposition each mark that overlaps: absent metallisation rejects,
   thinned metal is compared against the working fraction, intact metal is
   accepted with the mark recorded.
4. Total the exposed footprint, the disturbed footprint and the probe
   witnesses for each contact area.
5. Apply the area-level allowances -- the disturbed fraction and the witness
   count -- which can send a contact area to review on marks that each
   passed on their own.
6. Roll up by severity rather than record order: the governing verdict per
   contact area, then the cell verdict, the contact areas not accepted, the
   total exposed footprint and the marks that belong to another clause.

## Pitfalls

- Dispositioning a mark before placing it. A scratch across an active
  region is somebody else's clause and rejecting the cell on it here is a
  scrapped part for the wrong reason.
- Charging a straddling mark's full footprint to the contact area.
- Treating a boundary touch as contained.
- Grading on the mark's size. The size drives the area totals; the
  metallisation state drives the disposition.
- Accepting thinned metal because nothing is showing through. The next
  probe landing is what the working fraction is protecting against.
- Losing an off-contact mark entirely because this clause does not reject
  on it.
- Accepting a contact area because every mark passed. The disturbed
  fraction and the witness count exist for exactly that case.
- Unioning overlapping marks in the disturbed figure and so hiding a site
  that has been worked repeatedly.
- Comparing a fraction with its allowance by bare arithmetic. The fraction
  is a quotient of summed footprints, so a value that should sit exactly on
  the allowance can evaluate a few units in the last place above it; the
  comparison absorbs that representation error while the allowance stays
  untouched.

## Behavior contract (gate 3)

The containment test, the straddling overlap, the metallisation-state
dispositioning, the working-fraction review rule, the exposed and disturbed
footprints, the probe witness count, the area-level allowances and the
severity rollup are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_contact_area_general.py against
scripts/e2008_bare_cell_contact_area_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_contact_area_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
