---
name: e2008-welding-visual-inspection
description: "Use when a welded assembly has been examined and the drawing is the authority the record has to answer to. Verify the welds at solar-array string terminations and terminals against the assembly control drawing under ECSS-E-ST-20-08C clause 5.5.3.2.14: match every inspected location to its drawing entry, compare the welds present with the count the drawing calls for, resolve each weld's offset from its drawn position and its nugget diameter against the drawing band, grade cracked, expelled and discoloured nuggets, count the sound welds a location has left, and return accept, rework or reject with undeclared locations refused and unrecorded ones named. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-14, solar-array-termination-weld-inspection, weld-against-assembly-control-drawing, weld-nugget-diameter-band, weld-position-tolerance-check, undeclared-weld-location."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-welding-visual-inspection, solar-array-termination-weld-inspection, weld-against-assembly-control-drawing, weld-nugget-diameter-band, weld-position-tolerance-check, undeclared-weld-location]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Welding Visual Inspection (space-systems/ecss/e2008-welding-visual-inspection)

Use when the task is the weld inspection of ECSS-E-ST-20-08C clause
5.5.3.2.14 -- the welds at a solar-array string's terminations and at its
terminals, examined against the assembly control drawing rather than
against a general impression of good workmanship.

## Domain quick reference

- The drawing is the authority. It says which locations carry welds, how
  many welds each one carries, where each weld sits and how wide its
  nugget has to be. Every question this inspection asks is a comparison
  with that drawing, and the revision the inspection cites has to be the
  revision in hand.
- A weld found where the drawing declares no location is not a spare. It
  has no drawn position and no nugget band to be graded against, so it
  is refused and raised as a configuration question rather than screened
  and passed.
- Placement is a two-axis measurement collapsed to one number. The
  offset from the drawn position is the root-sum-square of its
  components, and it is that resultant, not either component, that the
  drawing tolerance applies to.
- Nugget diameter is not symmetric about the band. Under the band the
  joint carries less current than it was drawn to and there is no
  reworking that back; over the band the heat went somewhere, which is a
  process question and a rework call.
- A cracked nugget is not a graded defect. It has already stopped being
  a joint, so it comes out of the sound-weld count and takes the
  location with it.
- Redundancy is what the sound-weld count measures. A termination drawn
  with four welds and left with one is inside most fraction allowances
  and out of margin, so a reserve of sound welds sits underneath the
  fractions.
- Locations without a record leave the assembly open. An allowance taken
  over the locations that happened to be inspected is taken over the
  wrong population and reads better than the assembly is.

## Workflow

1. Validate the control drawing and index it by location, refusing a
   drawing with no identifier, no revision, a duplicated location, an
   inverted nugget band or a non-positive position tolerance.
2. Check the revision the inspection cites against the drawing in hand
   before any weld is read.
3. For each inspected location, find its drawing entry. Refuse a
   location the drawing does not declare, and refuse a weld population
   larger than the count the drawing calls for.
4. Per weld, form the resultant position offset and compare it with the
   drawing tolerance and the rework margin; compare the nugget diameter
   with the drawing band; read the cracked, expelled and discoloured
   conditions.
5. Per location, count the welds present against those called for, count
   the sound welds left, take the condition fractions over the required
   population and apply the sound-weld reserve.
6. Roll the assembly up: how many locations carry a finding, how much of
   the assembly allowance is left, and which drawing locations still
   have no record.
7. Report the worst disposition, the locations not accepted, the
   remaining allowance and the completeness flag.

## Pitfalls

- Grading a weld on its own merits without opening the drawing. A
  well-formed nugget in the wrong place is still a weld the assembly was
  not drawn with.
- Taking the position tolerance against one axis at a time. Two offsets
  each inside the tolerance can put the resultant outside it.
- Treating an undersized and an oversized nugget as the same finding.
  One of them is a current path that was never built; the other is a
  process excursion on a joint that exists.
- Reporting a defect fraction with no sound-weld count beside it. One
  cracked weld of four and one of eight are the same fraction and a
  different amount of redundancy left.
- Counting a cracked nugget as a sound weld because the location still
  passes its fractions. It stopped carrying current the moment it
  cracked.
- Applying the assembly allowance to the locations that were inspected
  rather than to the locations the drawing declares. The short set moves
  the denominator and flatters the assembly.
- Comparing a counted number of welds or locations with a derived
  allowance by bare arithmetic, or an offset with a tolerance it lands
  exactly on. The allowance is a product of a declared fraction and a
  counted population and the offset is a root-sum-square, so either can
  evaluate a few units in the last place past its limit; the comparison
  absorbs that representation error while the limit stays untouched.

## Behavior contract (gate 3)

The drawing validation and indexing, the revision check, the resultant
offset and nugget band comparisons, the per-weld dispositions, the
location population and sound-weld reserve, the condition fractions and
the assembly allowance with its remaining budget and completeness rollup
are exercised by the gate 3 contract test:
scripts/test_e2008_welding_visual_inspection.py against
scripts/e2008_welding_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_welding_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
