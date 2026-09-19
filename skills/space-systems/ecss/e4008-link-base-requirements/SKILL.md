---
name: e4008-link-base-requirements
description: "Verify that an SMP link base artefact resolves against the assembly it wires, under ECSS-E-ST-40-08C clause 5.3 and the five base requirements that clause places on it. Use when a link registry has to be accepted or rejected before the simulator is connected: giving every link an identity that appears once, resolving the source instance and the reference its type declares, resolving the target instance and checking its type provides the required interface directly or through inheritance, counting the links bound to each reference against its multiplicity bounds, and refusing a binding registered twice or bound to its own instance. Trigger: ecss, e-st-40-08-simulation-modelling-scope, e4008-link-base-requirements, smp-link-base-artefact, link-endpoint-resolution, link-interface-satisfaction, link-reference-multiplicity, duplicate-link-binding."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-link-base-requirements, smp-link-base-artefact, link-endpoint-resolution, link-interface-satisfaction, link-reference-multiplicity, duplicate-link-binding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling — Link Base Requirements (space-systems/ecss/e4008-link-base-requirements)

Use when the task is the link base artefact of ECSS-E-ST-40-08C clause
5.3 -- the registry that wires an assembly together by binding each
reference declared on an instance to another instance that provides
the interface that reference requires.

## Domain quick reference

- The assembly says which instances exist; the link base says how
  they are connected. Neither artefact is complete without the other,
  and a link base is only ever graded against a named assembly.
- A link base is a registry and not a script. Nothing about a link's
  meaning depends on where in the file it sits, so a verdict that
  changes when the links are reordered is a defect in the checker,
  not in the artefact.
- A link has three parts and all three have to resolve: the source
  instance, the reference declared on that instance's type, and the
  target instance. Each failure is a different edit, so each gets its
  own finding rather than one blanket unresolved-link.
- Interface satisfaction is closed over inheritance. A type that
  provides a derived interface satisfies a reference written against
  the base interface, so the check is a closure over the inheritance
  chain rather than a string comparison.
- An inheritance cycle in the catalogue is a catalogue defect, not a
  link finding. It makes the closure undefined, so it raises rather
  than producing a verdict that happens to look clean.
- Multiplicity is a property of the reference and a count over the
  links. A reference with a lower bound of one is unsatisfied by an
  empty link base, which is why an empty base is not automatically
  clean.
- Two links that bind the same reference to the same target are not
  redundancy. They are one binding written twice, and they inflate
  the multiplicity count that the next check depends on.
- Binding a reference to its own instance is legal only where the
  reference says so. Left unchecked it produces a model that appears
  wired while nothing external is attached.

## Workflow

1. Validate the assembly view first -- every instance names a
   declared type, every reference carries an interface and sane
   bounds, and no interface inheritance chain loops. A malformed
   model raises rather than producing findings.
2. Walk the links once. Record an unnamed link and a repeated link
   identity as findings, and keep going: identity problems do not
   stop the endpoint checks.
3. Resolve the source endpoint in two steps, the instance then the
   reference on its type, so the finding names which half failed.
4. Resolve the target endpoint and test the required interface
   against the closure of everything the target's type provides.
5. Refuse a self-binding the reference does not permit, then refuse a
   binding already registered, so neither inflates the count.
6. Count the surviving bindings per reference, compare each count
   against the declared bounds, and close with the verdict, the
   resolved links and the finding codes.

## Pitfalls

- Comparing the required interface with the provided list by string
  equality. A target providing the derived interface is then rejected
  even though it satisfies the reference, and the fix applied is
  usually to weaken the reference.
- Counting every link entry toward multiplicity, including the ones
  that failed to resolve. A reference then looks satisfied by two
  links that point nowhere.
- Treating a duplicate binding as harmless. It is invisible at run
  time but it doubles the count, which can push a reference over its
  upper bound or hide that it is under its lower one.
- Grading an empty link base as clean. Every reference with a
  non-zero lower bound is unsatisfied, and an empty base is exactly
  the state a forgotten artefact leaves behind.
- Letting an interface inheritance cycle be absorbed as an
  unsatisfied interface. The closure never terminates in a sane
  sense; the catalogue is what needs fixing.
- Allowing the verdict to depend on link order. The base is a
  registry, and an order-sensitive checker turns an editor's
  reshuffle into an apparent regression.

## Behavior contract (gate 3)

The model validation, interface inheritance closure, link identity
handling, source and target endpoint resolution, self-binding and
duplicate-binding refusal, per-reference multiplicity counting and the
order-independent verdict are exercised by the gate 3 contract test:
scripts/test_e4008_link_base_requirements.py against
scripts/e4008_link_base_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_link_base_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
