---
name: e20-harness-mechanical-load-exclusion
description: "Use when verify that a spacecraft harness is routed so the wiring never carries structural or mechanical load under ECSS-E-ST-20C clause 5.8.2: categorize each attachment as a restraint or a load-path misuse, compute the transverse load per metre a bundle sees under quasi-static launch acceleration, derive the span tension and sag from the installed slack, check that tension against the bundle allowable and that sag against the clearance to neighbouring hardware, size the service loop a crossing of a moving or thermally displacing interface needs so the bundle never goes taut, and confirm no connector backshell reacts the weight of an unsupported bundle. Trigger: ecss, e-st-20-electrical-scope, harness-mechanical-load-exclusion, harness-routing-rules, clamp-spacing-rule, bundle-span-tension, service-loop-slack, connector-strain-relief, quasi-static-launch-acceleration, harness-bend-radius."
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
  tags: [ecss, e-st-20-electrical-scope, e20-harness-mechanical-load-exclusion, harness-routing-rules, clamp-spacing-rule, bundle-span-tension, service-loop-slack, connector-strain-relief, harness-bend-radius]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Harness Mechanical Load Exclusion (space-systems/ecss/e20-harness-mechanical-load-exclusion)

Use when the task is the clause 5.8.2 routing rule of ECSS-E-ST-20C --
showing that the structure carries the mechanical loads and the
harness is only carried by it, never the other way round, across every
clamped span, every interface the bundle crosses and every connector
it terminates in.

## Domain quick reference

- Each attachment is categorized once. A restraint holds the bundle to
  structure without letting it react structural load: a P-clamp on a
  standoff, a tie into a cable tray, lacing to a dedicated bracket, a
  saddle clamp on a harness rail, an adhesive tie base on a panel. A
  load-path misuse is a routing arrangement that makes the harness
  structural in its own right: a bundle used as a tie between two
  members, a bundle tensioned between hardpoints, a connector left as
  the only support of the wiring behind it, a bundle bridging a moving
  joint with no slack, a bundle trapped in the faying surface of a
  bolted joint. A misuse is a finding on sight, before any number is
  computed.
- The load a span sees is distributed: bundle mass per metre times the
  quasi-static acceleration times standard gravity, in newtons per
  metre. For a shallow-sag span the axial tension is that load times
  the span squared over eight times the installed sag -- so tension
  falls as the installed slack rises, and a span dressed with no slack
  has no finite tension solution at all. Inverting the same relation
  gives the longest spacing that keeps the tension at or below the
  bundle allowable for a given sag.
- Sag is bounded twice: by the tension it implies and by the clearance
  to whatever sits beneath the bundle. A span that sags onto
  neighbouring hardware starts loading that hardware, which is the
  same defect seen from the other side. A separate workmanship limit
  caps the clamp spacing independently of the computed tension.
- A harness crossing an interface that moves -- a deployment hinge, a
  thermally displacing joint, an assembly shim stack -- needs a
  service loop longer than the summed relative displacement times a
  slack factor, and needs an anchor on each side of the interface so
  the bundle is not the only thing joining the two structures.
- A connector is an electrical termination, not a bracket. The
  unsupported bundle mass behind it times the acceleration is a real
  force into the backshell, and the first support has to sit within a
  short distance of the connector with strain relief in place.

## Workflow

1. Categorize every attachment on the routed harness; raise on a kind
   that is not a recognized harness attachment and record every
   load-path misuse as a finding immediately.
2. For each clamped span compute the transverse load per metre from
   the bundle mass per metre and the quasi-static acceleration.
3. Derive the span tension from the span length and the installed sag,
   and flag a tension above the bundle allowable.
4. Flag an installed sag greater than the clearance beneath the span,
   and a span length greater than the workmanship clamp-spacing limit.
5. Where a bend is recorded, compare the installed radius against the
   minimum bend radius for the bundle diameter and flag a tighter
   bend.
6. For each interface crossing compute the required service-loop
   length from the thermal displacement, the mechanism stroke and the
   assembly tolerance times the slack factor; flag short slack and
   flag a crossing anchored on only one side.
7. For each connector termination compute the reaction the unsupported
   bundle mass drives into the connector and flag an exceedance, a
   first support beyond its distance limit, or absent strain relief.
8. Aggregate the attachment, span, crossing and termination findings;
   the harness excludes mechanical load only when all four lists are
   empty.

## Pitfalls

- Dressing a span tight because it looks neat. Zero slack is the
  worst case, not the best: tension goes to the limit of the relation
  and the bundle becomes the tie clause 5.8.2 forbids.
- Checking tension at one g. The routing rule is written against the
  quasi-static launch environment, and a bundle that is comfortable on
  the bench reacts twenty times that load through the same clamps.
- Sizing a service loop to the mechanism stroke alone and omitting the
  thermal displacement and the assembly tolerance -- the three add,
  and the slack factor applies to the sum, not to the largest term.
- Anchoring a crossing on one side only. One anchor plus one connector
  is a load path through the harness even when both ends look
  supported on the drawing.
- Reading "no tension finding" as compliance while the bundle sags
  onto a radiator or a waveguide beneath it; the clearance check is
  the second half of the same requirement.
- Treating a connector backshell as a support point because it is
  mechanically strong. The allowable is an electrical-termination
  allowable, and the requirement is a support close behind it, not a
  stress calculation that happens to close.

## Behavior contract (gate 3)

The attachment-categorization, distributed-load, span-tension,
sag-clearance, clamp-spacing, bend-radius, service-loop and
connector-reaction logic is exercised by the gate 3 contract test:
scripts/test_e20_harness_mechanical_load_exclusion.py against
scripts/e20_harness_mechanical_load_exclusion_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_harness_mechanical_load_exclusion.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
