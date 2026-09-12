---
name: e20-reliable-insulation-underlying-assumptions
description: "Use when validate the background assumptions a reliable-insulation argument rests on under ECSS-E-ST-20C clause 4.2.1.2.1, the provision formerly termed double insulation: categorize each declared layer as basic, supplementary, reinforced or merely functional, confirm the layer set is admissible (two independent layers, or one reinforced layer), test the pair for the shared part, material or process that would defeat independence, check that the surviving layer alone withstands the full applied stress with margin, and screen the applied environment against the qualification envelope including the low-pressure corona band. Trigger: ecss, e-st-20-electrical-scope, reliable-insulation, double-insulation, insulation-layer-independence, common-cause-exclusion, dielectric-withstand-margin, corona-onset-pressure."
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
  tags: [ecss, e-st-20-electrical-scope, e20-reliable-insulation-underlying-assumptions, reliable-insulation, double-insulation, insulation-layer-independence, common-cause-exclusion, dielectric-withstand-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design — Reliable Insulation, Underlying Assumptions (space-systems/ecss/e20-reliable-insulation-underlying-assumptions)

Use when the task is the admissibility of a reliable-insulation
argument under ECSS-E-ST-20C clause 4.2.1.2.1 -- the concept
previously called double insulation, whose protective intent is that
no single insulation defect can expose a hazardous net. The argument
is only as good as the assumptions underneath it, and this leaf tests
those assumptions rather than the insulation hardware.

## Domain quick reference

- Reliable insulation is a layer-set property, not a material
  property. The set is admissible in exactly two shapes: one basic
  layer plus one supplementary layer that are mutually independent,
  or a single reinforced layer qualified to the whole stress on its
  own. Functional insulation -- present for circuit operation, not
  for protection -- never counts toward the set, however good it is.
- The protective intent is single-defect tolerance: after one layer
  is assumed defective, the remaining layer alone still separates the
  hazardous net from the exposed part. Everything the argument claims
  follows from five assumptions, and each is checkable: the layers
  are independent items, no common-cause mechanism links them, the
  surviving layer withstands the full applied stress with margin, the
  applied environment stays inside the qualification envelope, and no
  conductive path bypasses the insulation entirely.
- Independence fails in three concrete ways, all of them recorded in
  the build data rather than in the schematic: the two "layers" are
  the same physical part (a single sleeve counted twice), they share
  the same material (so one ageing or radiation mechanism attacks
  both), or they share the same process step (so one workmanship
  escape produces both defects). Distinct material or distinct
  process is the minimum discriminator; a shared part identifier is
  fatal regardless.
- The environment screen is not only voltage and temperature. In the
  low-pressure band between roughly 1e-1 Pa and 1e4 Pa -- traversed
  during ascent and re-entered by any vented volume -- corona onset
  drops sharply, so a layer qualified only at ambient or only at hard
  vacuum has no evidence covering the band it will actually fly
  through. A withstand margin measured at sea level does not transfer
  into it.

## Workflow

1. Categorize every declared layer: basic, supplementary, reinforced
   or functional. Reject an unrecognised layer type before it enters
   the argument.
2. Test the layer set for admissibility: one qualified reinforced
   layer, or one basic plus one supplementary layer. Anything else --
   a single basic layer, two functional layers, a reinforced layer
   without its own qualification -- fails here and the remaining
   checks are moot.
3. For a two-layer set, test independence: distinct part identifiers,
   and a difference in material or in process. Record a shared part,
   a shared material or a shared process as a common-cause finding.
4. Compute the withstand margin of the surviving layer alone against
   the full applied stress and compare it with the required factor;
   the margin is taken per layer, never summed across layers.
5. Screen the applied environment against the qualification envelope:
   voltage ceiling, temperature range, and low-pressure corona band
   coverage. Each exceedance is its own finding.
6. Record any conductive bypass -- an unsleeved fastener, a bonding
   strap, a moisture path in ground operations -- as a bypass
   finding. The assumption set holds only when every finding list is
   empty.

## Pitfalls

- Counting one physical sleeve as two layers because it is drawn
  twice, or counting functional insulation as the supplementary
  layer. Both produce an admissible-looking set with one real layer.
- Summing the withstand of both layers into a single number. The
  clause presumes one layer is already defective, so the margin that
  matters is the survivor's alone.
- Treating identical material in both layers as conservative. A
  shared material is a shared ageing, radiation and outgassing
  mechanism -- it is the definition of the common cause the second
  layer exists to exclude.
- Qualifying only at ambient pressure or only at hard vacuum and
  reading the gap as covered. The low-pressure band in between is
  where corona onset is lowest and where the hardware spends ascent.
- Declaring the assumptions satisfied while a bonding strap, a
  fastener or a test-connector shell provides a path around both
  layers. A bypass makes the layer count irrelevant.

## Behavior contract (gate 3)

The layer categorization, set-admissibility, independence,
withstand-margin and environment-envelope logic is exercised by the
gate 3 contract test:
scripts/test_e20_reliable_insulation_underlying_assumptions.py against
scripts/e20_reliable_insulation_underlying_assumptions_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_reliable_insulation_underlying_assumptions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
