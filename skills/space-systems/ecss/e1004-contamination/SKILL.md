---
name: e1004-contamination
description: "Use when assessing on-orbit contamination of a spacecraft external surface under ECSS-E-ST-10-04C clause 11.2: classify each contamination source as molecular (outgassing, venting, propulsion effluent, leak) or particulate (debris, MLI fragment, handling residue, paint flake), determine the molecular transport path (direct line-of-sight vs. LEO ram/wake return flux), compute the deposited molecular mass and compare it against the surface's allowable budget, and verify every particulate-generating surface carries a cleanliness level per the ECSS-Q-ST-70-01 contamination control linkage. Trigger: ecss, e-st-10-04c, contamination, molecular contamination, particulate contamination, outgassing, deposition, cleanliness level, q-st-70-01, on-orbit contamination assessment."
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
  tags: [ecss, e-st-10-04c, contamination, molecular-contamination, particulate-contamination, deposition, q-st-70-01]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — On-Orbit Contamination (space-systems/ecss/e1004-contamination)

Use when the task is the on-orbit contamination assessment of
ECSS-E-ST-10-04C clause 11.2 -- classifying molecular and particulate
contamination sources, tracing their transport path to a sensitive
surface, and checking deposition against the contamination-control
requirements linked to ECSS-Q-ST-70-01.

## Domain quick reference

- Clause 11.2 splits contamination into two families: molecular
  (outgassing, venting, propulsion effluent, leaks -- deposits as a
  thin film) and particulate (debris, MLI fragments, handling residue,
  paint flakes -- deposits as discrete particles). Each source is
  categorized into exactly one family before its transport is traced.
- Molecular transport follows one of two paths to a given surface:
  direct line-of-sight (the source has an unobstructed view factor to
  the surface) or return flux (no direct view, but the source's
  effluent is scattered back by the ambient atmosphere in the LEO
  ram/wake region and arrives indirectly, at reduced efficiency).
  A source with neither a line-of-sight view nor exposure to a
  return-flux region has no transport path to that surface.
  Particulate transport is mechanical (launch vibration/shock
  redistributing debris) or venting-driven redistribution. This leaf's
  transport check is scoped to the molecular path -- the particulate
  side is controlled procedurally via cleanliness level, not a
  computed transport model.
- Deposition is the accumulated mass per unit area on a surface over
  an exposure duration; each sensitive surface (optics, thermal
  control, solar cells) carries an allowable molecular deposition
  budget set by the payload/subsystem contamination requirement, which
  is itself derived from the cleanliness and contamination control
  policy of ECSS-Q-ST-70-01. A surface with particulate-generating
  sources in view must also carry a Q-ST-70-01-linked cleanliness
  level (e.g. a visibly-clean class); the E-ST-10-04C environment
  assessment does not set that level itself, it flags when the linkage
  is missing.

## Workflow

1. Inventory every candidate contamination source (outgassing item,
   vent, thruster, leak path, debris generator, MLI edge, handling
   step, paint) and classify each one as molecular or particulate.
   Reject an unrecognized source type before it enters the assessment.
2. For each molecular source and each sensitive surface it can reach,
   determine the transport path: direct line-of-sight if the source
   has an unobstructed view factor to the surface, return flux if it
   sits in the LEO ram/wake region without a direct view, otherwise no
   transport path (drop the pair from the deposition calculation).
3. Compute the deposited mass per surface: source rate x transport
   efficiency (1.0 direct line-of-sight, reduced for return flux) x
   exposure duration, summed over every molecular source reaching that
   surface.
4. Compare the summed deposition against the surface's allowable
   molecular budget (from the Q-ST-70-01-linked contamination
   requirement); flag an exceedance, and separately flag a sensitive
   surface with molecular sources but no budget on record.
5. For each surface with particulate-generating sources in view,
   confirm a cleanliness level is on record; flag a surface with
   particulate sources but no linked cleanliness level.
6. Aggregate the molecular and particulate findings per surface; the
   surface is not contamination-compliant until both lists are empty.

## Pitfalls

- Skipping the transport-path step and applying the source rate
  directly as deposition -- a source with no view factor and outside
  the return-flux region contributes nothing and must be dropped, not
  treated as a worst case.
- Treating return-flux transport as equivalent to direct line-of-sight
  -- the ambient-scattered path deposits at markedly lower efficiency
  than an unobstructed view, and collapsing the two overstates risk on
  every return-flux pair and understates it if the direction is
  reversed.
- Leaving a sensitive surface's molecular budget unset and reading
  "no violation" as compliant -- an unset budget means the
  Q-ST-70-01-linked requirement was never captured, which is itself a
  finding, not a pass.
- Treating particulate control as satisfied because no numeric
  deposition was computed -- clause 11.2 controls particulates via a
  cleanliness-level requirement, not a mass budget; the check is
  presence of that linkage, not a number.

## Behavior contract (gate 3)

The source-classification, transport-path, molecular-deposition, and
particulate-cleanliness-linkage logic is exercised by the gate 3
contract test: scripts/test_e1004_contamination.py against
scripts/e1004_contamination_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_contamination.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
