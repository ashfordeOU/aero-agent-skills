---
name: e4008-interface-link
description: "Validate the interface links of an SMP Level-2 assembly artefact against ECSS-E-ST-40-08C clause 5.2.7.2: confirm the consumer endpoint names a reference its type declares, the provider endpoint names an interface its type publishes, the published interface is the required type or derives from it, the bindings into each reference stay inside the upper multiplicity, every mandatory reference reaches its lower multiplicity, no provider interface is bound into one reference twice, and no reference is satisfied by its own instance. Use when an assembly leaves a required interface unresolved or a binding is refused at build time. Trigger: ecss, e-st-40-08c, smp-level-2, assembly-interface-link, component-reference-binding, interface-multiplicity-check, interface-derivation-match, unresolved-mandatory-reference."
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
  tags: [ecss, e-st-40-08c-smp-level-2, e4008-interface-link, smp-assembly-artefact, component-reference-binding, interface-link-multiplicity, interface-derivation-compatibility, mandatory-reference-resolution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SMP L2 — Interface Link (space-systems/ecss/e4008-interface-link)

Use when the task is an interface link of an SMP Level-2 assembly artefact per
ECSS-E-ST-40-08C clause 5.2.7.2 — binding a reference that one component
requires to an interface another component publishes, and deciding whether the
binding is admissible before the simulator is built.

## Domain quick reference

- An interface link has two asymmetric ends. The consumer end names a
  *reference*: an interface the component needs in order to work. The provider
  end names an *interface* the other component publishes. Swapping the roles
  produces a link that reads plausibly and resolves to nothing.
- Type agreement is a derivation question, not an equality one. A reference
  requiring a general power-rail interface is satisfied by a regulated or
  switched rail that derives from it, transitively; the reverse never holds,
  because the base does not carry what the derived interface added.
- A reference carries a multiplicity, and both ends of it matter. The upper
  bound caps how many providers may be bound — written as -1 when unbounded —
  and the lower bound makes the reference mandatory, so a reference with a
  lower bound of one and no link at all is a defect of the assembly even though
  no link is wrong.
- The mandatory-reference check is the one that cannot be made by looking at
  the links. It is found by walking every instance's declared references and
  asking which of them no link reached, which is why an assembly can have a
  fully valid link list and still fail to build.
- Binding the same published interface into the same reference twice consumes
  an upper-bound slot for no added connection, and is the usual residue of a
  copied link whose provider was updated but whose reference was not.

## Workflow

1. Resolve each link's consumer instance and the reference it names, reading
   the required interface type and validating its multiplicity pair.
2. Resolve the provider instance and the interface it publishes under the named
   element, reading the published interface type.
3. Walk the interface hierarchy from the published type upwards and accept the
   binding only if the required type is reached; guard the walk against a
   cyclic hierarchy rather than looping.
4. Refuse a binding whose reference and published interface sit on the same
   instance unless the assembly explicitly permits self-binding.
5. Accumulate the providers bound into each reference, rejecting a provider
   already present on that reference.
6. Compare each reference's binding count with its upper bound, then walk every
   declared reference of every instance and report the mandatory ones nothing
   bound.
7. Report the accepted bindings, a per-reference multiplicity verdict, and
   every finding.

## Pitfalls

- Testing interface types for equality. A derived interface is the normal way a
  provider satisfies a general reference, so equality rejects correct assemblies
  and pushes engineers into widening the reference instead.
- Accepting the base interface where a derived one is required. Derivation is
  directional; a check that walks the hierarchy in either direction accepts a
  provider that does not carry the operations the consumer will call.
- Grading only the links that exist. A mandatory reference with no link is
  invisible to any per-link loop, and it is the most common reason a valid-
  looking assembly fails during the building state.
- Reading an unbounded upper multiplicity as zero. The -1 marker is a sentinel,
  not a count, and arithmetic that treats it as a number turns every binding on
  an unbounded reference into an over-binding.
- Counting a repeated binding as a second provider. The duplicate fills an
  upper-bound slot without adding a connection, so an over-bound finding and a
  duplicate finding describe different repairs and must stay separate.

## Behavior contract (gate 3)

The reference and published-interface resolution, hierarchy walk with cycle
guard, self-binding rule, duplicate-provider detection, upper-bound comparison
and mandatory-reference sweep are exercised by the gate 3 contract test:
scripts/test_e4008_interface_link.py against
scripts/e4008_interface_link_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_interface_link.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
