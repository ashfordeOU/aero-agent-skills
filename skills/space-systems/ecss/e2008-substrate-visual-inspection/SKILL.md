---
name: e2008-substrate-visual-inspection
description: "Evaluate a solar-array substrate for damage left by assembly, handling or test operations under ECSS-E-ST-20-08C clause 5.5.3.2.5: categorize each indication as a facesheet scratch, dent or puncture, honeycomb core crush, facesheet-core disbond, insulation-layer tear, edge close-out damage or insert damage, measure its depth against the facesheet thickness and its damaged area, tighten every limit where the damage sits under the cell bonding footprint or an insert, disposition it accept, repair or reject, roll the damaged-area fraction up into a panel verdict, and attribute the indications to the operation that produced them. Use when a panel substrate has been examined and the record needs a defensible disposition. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-5, solar-array-substrate-damage-inspection, facesheet-damage-disposition, honeycomb-core-crush-assessment, substrate-handling-damage-attribution, cell-bonding-footprint-severity, panel-damaged-area-fraction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-substrate-visual-inspection, solar-array-substrate-damage-inspection, facesheet-damage-disposition, honeycomb-core-crush-assessment, substrate-handling-damage-attribution, cell-bonding-footprint-severity, panel-damaged-area-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Substrate Visual Inspection (space-systems/ecss/e2008-substrate-visual-inspection)

Use when the task is the substrate examination of ECSS-E-ST-20-08C
clause 5.5.3.2.5 -- looking at the panel itself, not the cells on it,
for damage that the assembly, handling or test operations put there,
and turning each indication into a disposition that a repair or a
scrap decision can rest on.

## Domain quick reference

- The subject of this examination is the substrate: a honeycomb panel
  with thin facesheets, a dielectric layer under the cell field, an
  edge close-out and bonded inserts. Damage to it is induced, not
  manufactured in, so the survey is run after the operations that can
  cause it rather than once at incoming inspection.
- Eight indication kinds cover what those operations actually do:
  facesheet scratch, facesheet dent, facesheet puncture, honeycomb
  core crush, facesheet-core disbond, insulation-layer tear, edge
  close-out damage and insert damage. Grouping the indication first is
  what makes a limit applicable at all; an uncategorized indication
  must never inherit a neighbouring kind's limit.
- Two measurements govern each indication and the worse of the two
  wins: depth expressed as a fraction of the facesheet thickness, and
  damaged area. Depth decides whether the load path through the
  facesheet is still intact; area decides how much of the panel has to
  be reworked, and a shallow but broad indication can be the worse of
  the pair.
- Where the damage sits changes the limit. Under the cell bonding
  footprint the facesheet also carries the bond line and the
  dielectric, so the limits tighten; around an insert the damage sits
  in a load introduction point and tightens likewise. Open facesheet
  and the edge close-out carry the full limit.
- Damage that passes through the facesheet under the cell field is a
  different failure from the same hole in an open area: a surface
  repair cannot restore the bond line or the dielectric underneath it,
  so that case rejects on location rather than on size.
- The panel carries a limit of its own. Indications that each pass on
  their own still add up, so the damaged-area fraction of the whole
  panel is compared against a repair fraction and a reject fraction.
- Every indication is attributed to assembly, handling or test. The
  disposition fixes the panel; the attribution is what stops the next
  panel arriving with the same damage, so an unattributed indication
  is rejected rather than recorded.

## Workflow

1. Open the record against a substrate identifier, the panel area and
   the facesheet thickness. A survey with no traceable identifier or
   no thickness cannot be dispositioned, because every depth limit is
   expressed against that thickness.
2. Categorize every indication by kind and zone, and attribute it to
   the operation that produced it. Reject an unrecognized kind, zone
   or operation rather than defaulting it.
3. Measure each indication twice: depth into the facesheet and
   damaged area. Reject an indication that carries neither, since
   there is nothing to compare against a limit.
4. Scale the accept and repair limits by the zone severity factor,
   then disposition the indication on the worse of its depth call and
   its area call.
5. Apply the through-facesheet rule under the cell field: a hole that
   reaches the bond line and the dielectric there rejects whatever its
   area.
6. Sum the damaged area, take the fraction of the panel area, and
   escalate the panel verdict when the fraction crosses the repair or
   the reject fraction even though no single indication did.
7. Close with the panel verdict, the re-inspection duty a repair
   creates, and the operation that produced most of the indications so
   the corrective action lands on the process rather than the part.

## Pitfalls

- Dispositioning on area alone. A narrow deep gouge removes load path
  through the facesheet while covering almost no area, and an
  area-only screen accepts it.
- Applying the open-facesheet limit under the cell field. The same
  scratch there sits on the bond line and the dielectric, and the
  limit that governs it is the tightened one.
- Treating a puncture under the cells as a repairable hole. The
  surface repair restores the facesheet and leaves the bond line and
  the dielectric it passed through unrepaired.
- Accepting a panel because every indication passed individually. The
  damaged-area fraction is a separate limit, and a scatter of small
  accepted indications is exactly the case it exists to catch.
- Recording damage without attributing it to assembly, handling or
  test. The panel gets repaired and the operation that caused the
  damage keeps producing it on the next panel.
- Comparing a measurement with a scaled limit by bare arithmetic. The
  limit is a product of a criteria value and a zone factor, so a
  measurement exactly on the limit can evaluate a few units in the
  last place above it; the comparison absorbs that representation
  error while the limit stays untouched.

## Behavior contract (gate 3)

The kind and zone categorization, depth-fraction and area
dispositioning, through-facesheet rule, panel damaged-area rollup and
operation attribution are exercised by the gate 3 contract test:
scripts/test_e2008_substrate_visual_inspection.py against
scripts/e2008_substrate_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_substrate_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
