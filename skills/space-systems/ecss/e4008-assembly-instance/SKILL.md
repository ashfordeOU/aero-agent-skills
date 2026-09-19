---
name: e4008-assembly-instance
description: "Validate an assembly Instance against the two normative items of ECSS-E-ST-40-08C clause 4.2.2.3. Use when a composite instance in a simulation assembly is reviewed: walking the containment tree to confirm the assembly actually declares the children it contains, that every child name is a legal identifier used once inside the containment, and that the nesting does not close on itself; then resolving both ends of every declared link onto a child the assembly contains or an interface it explicitly exports. Reports dangling endpoints, containment cycles and children no link reaches. Trigger: ecss, e-st-40-08c, simulation-assembly-instance, assembly-containment-tree, assembly-child-name-uniqueness, assembly-internal-link-resolution, assembly-exported-interface, assembly-containment-cycle."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-assembly-instance, simulation-assembly-instance, assembly-containment-tree, assembly-child-name-uniqueness, assembly-internal-link-resolution, assembly-exported-interface, assembly-containment-cycle]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Assembly Instance (space-systems/ecss/e4008-assembly-instance)

Use when the task is the assembly Instance requirements of
ECSS-E-ST-40-08C clause 4.2.2.3 -- grading a composite, an instance
that contains other instances, against the two items the clause
carries: what it contains, and whether its internal wiring resolves.

## Domain quick reference

- An assembly Instance is judged on containment, not on its own fields.
  The fields, references and path of the composite itself are the
  ordinary instance requirements; this clause adds the two questions a
  composite raises and a leaf instance does not.
- Item one is the containment declaration. The assembly has to say what
  it contains, each child name has to be a legal identifier, each name
  has to be used once inside the containment, and the nesting has to
  terminate. A composite that declares nothing is not an assembly, and
  a definition that appears inside its own containment chain describes
  an infinitely deep tree that no build can finish.
- Item two is link resolution, and it is where composites actually
  fail. A link has two endpoints, each written as an owner and a port.
  A resolvable endpoint names either a child the assembly contains or
  an interface the assembly explicitly exports; anything else is a
  reference into a scope the composite has no access to.
- The export list is what makes a link out of the assembly legitimate.
  Reaching a sibling directly, without an export to carry the signal,
  couples two composites through a path neither of them declares, and
  the coupling then breaks the first time either is reused elsewhere.
- An endpoint that reaches through more than one level is refused
  rather than followed. A composite wires its own children; a link that
  addresses a grandchild bypasses the intermediate assembly's
  interface, which is the one thing the containment was meant to fix.
- A child that no link touches is worth listing but is not a defect.
  Spares, monitors and instances driven only by the schedule are all
  legitimately unwired, so the review reports them and moves on.

## Workflow

1. Walk the containment tree from the assembly down, building the path
   of every contained node. Refuse a duplicate child name inside one
   containment and refuse a definition that reappears in its own
   chain.
2. Take the direct child names -- those are the only owners a link of
   this assembly may address -- and the declared export list, refusing
   a repeated export.
3. Parse each link endpoint into an owner and a port. Refuse an
   endpoint with no port and one that reaches through more than one
   level.
4. Resolve each endpoint: an owner naming a direct child resolves, the
   reserved self owner resolves when its port is a declared export, and
   everything else is a finding naming the end that failed.
5. Grade the two items separately, so a clean containment with broken
   wiring reports exactly that, and roll them into one verdict.
6. List the children no link reaches as information alongside the
   verdict, not as a failure.

## Pitfalls

- Grading a composite with the leaf-instance checks alone. Fields and
  paths say nothing about whether the thing inside is wired, and a
  composite passes every leaf check while delivering no signal at all.
- Following a multi-level endpoint because it happens to resolve. It
  may well address a real grandchild, and it still violates the
  containment: the intermediate assembly's interface is bypassed, and
  the grandchild can then never be replaced without editing a link that
  does not belong to its parent.
- Treating a direct reach into a sibling composite as equivalent to an
  export. The export is the declaration that the signal is part of the
  assembly's interface; without it the coupling is undocumented and
  survives only as long as both composites stay where they are.
- Reporting a containment cycle as a deep tree. The recursion does not
  terminate, so a walk that tries to enumerate it never returns a
  result to report; the cycle has to be detected on the definition
  chain rather than on a depth counter.
- Calling an unwired child a defect. A spare or a schedule-driven
  instance is legitimately unlinked, and failing the assembly for it
  buries the endpoints that genuinely did not resolve.
- Letting two links share a name. The name is how a finding is reported
  and how a later edit addresses the link, so a duplicate makes both
  ambiguous and is rejected outright rather than graded.

## Behavior contract (gate 3)

The identifier rule, path construction, endpoint parsing, containment
walk with its duplicate and cycle refusals, export declaration, link
resolution against children and exports, the two-item grading and the
unlinked-child report are exercised by the gate 3 contract test:
scripts/test_e4008_assembly_instance.py against
scripts/e4008_assembly_instance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e4008_assembly_instance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
