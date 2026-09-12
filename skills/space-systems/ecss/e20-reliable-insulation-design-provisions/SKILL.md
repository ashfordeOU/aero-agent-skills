---
name: e20-reliable-insulation-design-provisions
description: "Use when determine the dedicated insulation provisions an electrical line needs where it is exposed to meteoroid and debris impact or a comparable hazardous space environment under ECSS-E-ST-20C clause 4.2.1.2.3: categorize each exposure hazard acting on the line, derive the provision set that hazard demands and flag any provision not implemented, verify the line carries enough independent insulation barriers for a single-barrier failure to remain non-hazardous, evaluate the dielectric withstand margin of the insulation against the applied working voltage, size the impact protection areal density against the meteoroid screening requirement, and confirm the routing standoff from exposed external surfaces. Trigger: ecss, e-st-20-electrical-scope, reliable-insulation, meteoroid-damage-protection, redundant-insulation-barrier, atomic-oxygen-resistant-jacket, harness-routing-standoff, dielectric-withstand-margin, insulation-provision-review."
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
  tags: [ecss, e-st-20-electrical-scope, e20-reliable-insulation-design-provisions, reliable-insulation, meteoroid-damage-protection, redundant-insulation-barrier, harness-routing-standoff, dielectric-withstand-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Reliable Insulation Design Provisions (space-systems/ecss/e20-reliable-insulation-design-provisions)

Use when the task is the reliable-insulation design provision review of
ECSS-E-ST-20C clause 4.2.1.2.3 -- deciding what dedicated insulation,
shielding and routing provisions a line must carry because it is
exposed to meteoroid or debris impact, or to another hazardous feature
of the space environment that can breach insulation in service.

## Domain quick reference

- Clause 4.2.1.2.3 is a *provision* clause, not a performance clause.
  It does not ask whether the insulation passed a bench measurement;
  it asks whether the design carries the specific provisions that the
  line's exposure demands. A line routed inside a closed, shielded
  equipment bay and an identical line routed across an exposed
  external boom attract different provisions from the same wire type.
- Exposure hazards fall into four families, and the family sets the
  provision style. Impact hazards (meteoroid, orbital debris) are
  countered by mass -- a shield areal density, or routing behind
  primary structure. Material-degradation hazards (atomic oxygen, UV,
  charged-particle dose) are countered by the jacket material itself.
  Electrical-stress hazards (plasma charging, corona, arc tracking)
  are countered by a grounded overshield and by voltage derating.
  Mechanical-wear hazards (chafing, thermal-cycle fatigue of the
  jacket) are countered by chafe protection, stress relief and a
  temperature-rated insulation choice.
- "Reliable insulation" is a redundancy statement about barriers. Where
  the loss of one insulation barrier would itself be hazardous -- a
  high-voltage line, a line adjacent to a pyrotechnic circuit, a line
  whose short would defeat a failure-containment boundary -- the design
  needs two independent barriers, so that a single breach is detectable
  and non-hazardous rather than immediately damaging. Where a single
  barrier failure is not hazardous, one qualified barrier is enough.
- Impact protection is sized against a screening areal density derived
  from the design particle: its diameter, density and impact velocity.
  The screening relation used here is a deliberately simple monotonic
  sizing rule with a project-set coefficient; it ranks and screens
  candidate shields and flags an under-sized one. It is not a
  ballistic-limit qualification and does not replace a hypervelocity
  impact campaign or a dedicated debris-environment model.
- Routing standoff is the separate, cheap provision: distance between
  the line and the exposed external surface. A line that meets its
  standoff requirement is shadowed by structure and needs less
  dedicated shield mass than one run against the outer skin.

## Workflow

1. Inventory every exposure hazard acting on the line (meteoroid,
   orbital debris, atomic oxygen, solar UV, charged-particle dose,
   plasma charging, corona, arc tracking, chafing, thermal cycling)
   and categorize each into its family. Reject an unrecognized hazard
   name before it enters the review rather than silently dropping it.
2. Derive the union of provisions the categorized hazards demand, and
   subtract the provisions the design actually implements. Whatever
   remains is a missing-provision finding, one per provision.
3. Count the line's independent insulation barriers and decide whether
   a single-barrier failure is hazardous on this line. Require two
   independent barriers when it is, one when it is not.
4. Evaluate the dielectric withstand margin: the insulation's rated
   voltage against the applied working voltage, expressed as a
   fraction of the applied voltage. Compare it against the derating
   floor (default: rated at least twice applied).
5. Where an impact hazard is present, compute the required shield
   areal density from the design particle diameter, density and impact
   velocity, and compare the provided areal density against it.
6. Where the line runs near an exposed external surface, compare the
   routing standoff against the minimum standoff requirement.
7. Aggregate every finding onto the line. The line is not
   provision-compliant until the finding list is empty; report the
   findings rather than a single pass/fail bit, because each one names
   a different design action.

## Pitfalls

- Reading a qualified wire specification as satisfying the clause --
  the wire's own qualification says nothing about the provisions its
  installation needs. Two lines of identical part number, one internal
  and one on an exposed boom, attract different provision sets.
- Counting a shield and the insulation under it as two independent
  barriers when the shield is grounded and conductive -- a conductive
  overshield is impact and plasma protection, not a second dielectric
  barrier. Independence means a single breach cannot take out both.
- Treating a missing dielectric margin as acceptable because the line
  has never arced in ground test -- the derating floor exists because
  insulation withstand degrades with dose, thermal cycling and
  contamination over the mission, and a ground measurement samples
  the beginning-of-life condition only.
- Sizing the shield against the average particle rather than the
  design particle, or omitting impact velocity from the sizing -- the
  velocity term dominates the required areal density, so a shield
  sized at a low assumed velocity is under-sized by a wide factor.
- Accepting an unset shield areal density or an unset routing standoff
  as "no violation" -- an unset value means the provision was never
  captured, which is a finding in its own right, not a pass.

## Behavior contract (gate 3)

The hazard-categorization, provision-derivation, barrier-redundancy,
dielectric-margin, impact-sizing and routing-standoff logic is
exercised by the gate 3 contract test:
scripts/test_e20_reliable_insulation_design_provisions.py against
scripts/e20_reliable_insulation_design_provisions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_reliable_insulation_design_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
