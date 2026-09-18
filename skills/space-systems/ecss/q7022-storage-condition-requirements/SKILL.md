---
name: q7022-storage-condition-requirements
description: "Define the storage envelope a limited-shelf-life material owes under ECSS-Q-ST-70-22: intersect the house family default with the manufacturer declared temperature band, humidity ceiling and light sensitivity so the tighter side always governs, refuse a pair whose intersection is empty, widen a candidate store's set band by its own control tolerance before comparing, and close with a suitable, suitable-with-added-controls or not-suitable disposition naming every breached axis. Use when a new material enters the store, a store is requalified, or a datasheet limit disagrees with the house default. Trigger: ecss, q-st-70-22, shelf-life-storage-envelope, shelf-life-temperature-band-intersection, shelf-life-humidity-ceiling, shelf-life-light-protection, shelf-life-store-suitability-disposition."
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
  tags: [ecss, q-st-70-22-limited-shelf-life-materials, q-st-70-22, q7022-storage-condition-requirements, shelf-life-storage-envelope, shelf-life-temperature-band-intersection, shelf-life-humidity-ceiling, shelf-life-light-protection, shelf-life-store-suitability-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Storage Condition Requirements (space-systems/ecss/q7022-storage-condition-requirements)

Use when the task is the storage clause of ECSS-Q-ST-70-22: deciding what
temperature, relative humidity and light regime a limited-shelf-life material
has to be held at, and whether the store it is about to go into actually
delivers that regime.

## Domain quick reference

- The required envelope has two sources, not one. The house default for the
  material family and the manufacturer's declared limits are both binding, and
  the envelope is their intersection: the tighter side governs on every axis.
  A datasheet that permits 60 C does not licence 60 C for an elastomer whose
  family default stops at 27 C.
- An empty intersection is a real outcome and a refusal. A prepreg family
  default that stops below freezing and a declared minimum above freezing
  cannot both be honoured; the answer is to resolve the conflict with the
  supplier, not to pick whichever bound is convenient.
- A store is not its setpoint. The band a material sees is the setpoint band
  widened by the store's own control tolerance, so a chamber set to the top of
  the allowed band and holding to plus or minus one degree is already outside
  it. Compare the reachable extreme, never the nameplate.
- Light is an axis in its own right, and so is sub-zero capability. They are
  not temperature by another name: a material can sit comfortably inside a
  room-temperature band and still be degrading under uncontrolled daylight.
- Breaches are not equal. Some close with an added control the store can carry
  anyway — an opaque overwrap for light, a desiccated overbag for a small
  humidity overshoot. Temperature band and sub-zero capability do not: they
  need a different store. Grading them alike either over-rejects usable stores
  or quietly accepts unusable ones.

## Workflow

1. Validate each material record: family against the known set, declared bands
   for inversion, humidity ceiling inside its physical range. An unknown family
   is an input error, not a reason to fall back to the mildest default.
2. Derive the envelope by intersecting the family default with the declared
   limits, recording which source governs each axis so the reviewer can see why
   a bound is where it is.
3. Refuse a material whose intersection is empty, naming both bounds.
4. Validate the store and form its reachable extremes: setpoint minimum minus
   the temperature tolerance, setpoint maximum plus it, humidity ceiling plus
   its own tolerance.
5. Raise one finding per breached axis, each marked mitigable or not: light and
   a small desiccatable humidity overshoot are mitigable when the store can
   carry the control; temperature and sub-zero capability are not.
6. Reduce the findings to one disposition per material, then roll the material
   dispositions up to the store, with the worst case governing.
7. Report the derived envelope, the governing source per axis, every finding,
   the added controls implied, and the disposition.

## Pitfalls

- Letting a wider datasheet limit replace the house family default. The
  envelope is an intersection, so a declared bound only moves a limit when it
  is the tighter of the two.
- Comparing the material against the store's setpoint band. The control
  tolerance is part of what the material experiences; ignoring it passes stores
  that spend part of every cycle outside the envelope.
- Treating an empty intersection as a degenerate case to be clamped. Clamping
  invents a band nobody approved; the contradiction has to be resolved upstream.
- Folding light protection into the temperature question. A material can be in
  band on every thermal axis and still be exposed on the one that governs it.
- Calling every breach fatal, or every breach fixable. A desiccated overbag can
  carry a few points of humidity overshoot; nothing packed around the material
  makes a warm store cold.
- Allowing a single store report without per-material detail. The store is only
  as suitable as its worst material, and that material has to be named.

## Behavior contract (gate 3)

The material and store validation, envelope intersection, empty-intersection
refusal, reachable-extreme comparison, per-axis mitigability and the
disposition roll-up are exercised by the gate 3 contract test:
scripts/test_q7022_storage_condition_requirements.py against
scripts/q7022_storage_condition_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7022_storage_condition_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
