---
name: q7031-applicability-and-paint-systems
description: "Scope a declared finish against the paint rules of ECSS-Q-ST-70-31C: decide whether a drawing note's coating is a paint system or a surface treatment outside these rules, assemble the declared layers into an ordered primer, intermediate and topcoat stack, report an inverted or repeated stack and a topcoat on unprimed metal, total the dry-film build with its tolerance band, and close on one in-scope, out-of-scope or incomplete-declaration disposition. Use when a finish schedule or coating drawing note has to be settled before a material is chosen. Trigger: ecss, q-st-70-31c, paint-system-applicability, paint-layer-stack-order, paint-dry-film-build, coating-versus-surface-treatment, paint-scope-disposition."
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
  tags: [ecss, q-st-70-31c-paint-application, q-st-70-31c, q7031-applicability-and-paint-systems, paint-system-applicability, paint-layer-stack-order, paint-dry-film-build, coating-versus-surface-treatment, paint-scope-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paints — Applicability and Paint Systems (space-systems/ecss/q7031-applicability-and-paint-systems)

Use when the task is the framework clause of ECSS-Q-ST-70-31C: which finishes
on space hardware the paint rules govern, and what a declared paint system has
to look like before a single material or process decision is taken. This leaf
reads one finish declaration and says whether it is inside these rules, what
the stack actually is, and what the declaration is still missing.

## Domain quick reference

- A paint system is an organic-binder film applied wet and cured in place. An
  anodised, conversion-coated, plated or vacuum-deposited surface is a surface
  treatment: it may sit under a paint system, but on its own it is governed by
  a different set of rules, and calling it a coating on a drawing does not move
  it into these ones.
- A system is a stack, not a product. The primer answers adhesion and corrosion
  protection at the substrate, the topcoat answers the external environment and
  the thermo-optical role, and an intermediate layer answers whatever the two
  cannot. Naming only the topcoat leaves the adhesion question unanswered.
- Stack order is physical, not clerical. A primer applied over a topcoat is a
  different item from the one the drawing intends, and a second primer in the
  middle of a stack usually means two declarations were merged rather than one
  system being built up twice.
- Bare metal under a topcoat is the classic escape. Metallic substrates need a
  primer or a qualified pretreatment beneath the topcoat; a laminate may not,
  which is why the finding is substrate-dependent rather than universal.
- The build the hardware carries is the sum of the layers at their tolerance
  extremes, not the nominal figure of the thickest one. Mass, thermo-optical
  behaviour and edge coverage all follow the total, so the total is what is
  compared against any declared build limit.
- A declaration that cannot be read is not a scope decision. An unrecognised
  substrate or a stack with no organic layer in it returns incomplete, so the
  gap is closed rather than papered over with an in-scope call.

## Workflow

1. Categorize the declared finish family: paint system, surface treatment, or
   unrecognised. A surface treatment closes out of scope immediately; an
   unrecognised family closes as an incomplete declaration.
2. Normalise every declared layer — role, binder, nominal dry-film thickness
   and tolerance — and refuse a layer whose minus tolerance removes the layer
   entirely or whose role is not a stack role.
3. Order the layers and collect the structural findings: out-of-order stack,
   repeated role, topcoat on unprimed metallic substrate, no organic layer.
4. Total the dry-film build across the stack and return the minimum, nominal
   and maximum of the band.
5. Compare the worst-case build against any declared build limit, absorbing
   representation error at the boundary with a named tolerance instead of
   loosening the limit.
6. Close with one disposition and every finding that produced it, so a reviewer
   can see which declaration gap drove an incomplete call.

## Pitfalls

- Treating anodising or a conversion coating as a paint because the drawing
  note calls it a coating. It is a surface treatment, and pulling it into these
  rules means it is graded against requirements that were never written for it.
- Declaring the topcoat alone. The primer carries adhesion and corrosion
  protection; a single-product declaration on a metallic substrate is a finding
  even when the topcoat itself is perfectly qualified.
- Summing nominal thicknesses only. A stack whose nominal build sits inside a
  limit can exceed it at the tolerance extremes, which is the build the flight
  item actually carries.
- Reading a repeated role as a thicker layer. Two primer entries in a stack are
  a declaration defect until someone confirms otherwise; silently collapsing
  them hides a merged drawing.
- Widening a build limit so an exactly-at-limit stack passes. Equality at the
  limit is a representation question handled by the tolerance inside the
  comparison; the declared limit stays where it was set.

## Behavior contract (gate 3)

The finish categorization, layer normalisation, stack-order and substrate
findings, dry-film band summation, build-limit comparison and the scope
disposition are exercised by the gate 3 contract test:
scripts/test_q7031_applicability_and_paint_systems.py against
scripts/q7031_applicability_and_paint_systems_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7031_applicability_and_paint_systems.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
