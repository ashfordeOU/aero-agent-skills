---
name: e4008-link-general
description: "Verify the general rules every link in an SMP Level-2 assembly artefact obeys before its kind-specific typing is reached, per ECSS-E-ST-40-08C clause 5.2.7.1: each link name is a valid identifier and unique in the assembly, the declared kind is interface, event or field, both endpoints resolve onto a declared instance by longest-path match with an element left over, no endpoint dangles or reaches outside the assembly scope, the same kind-source-target triple is not declared twice, and an instance is not joined to itself. Use when an assembly fails to connect, a link silently does nothing, or a whole link set needs grading. Trigger: ecss, e-st-40-08c, smp-level-2, assembly-link-set, link-endpoint-resolution, duplicate-link-detection, dangling-link-endpoint, assembly-link-naming."
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
  tags: [ecss, e-st-40-08c-smp-level-2, e4008-link-general, smp-assembly-artefact, assembly-link-set, link-endpoint-resolution, duplicate-assembly-link, assembly-link-scope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SMP L2 — Link General Rules (space-systems/ecss/e4008-link-general)

Use when the task is the part of an SMP Level-2 assembly artefact that every
link shares, per ECSS-E-ST-40-08C clause 5.2.7.1 — naming, kind, endpoint
resolution and duplication — decided before any interface, event or field
typing rule is applied.

## Domain quick reference

- A link is a named element of the assembly, not an anonymous edge. The name is
  what a Link Base entry, a diagnostic and a later amendment all refer to, so a
  name that repeats makes two different connections indistinguishable in every
  downstream report.
- Three link kinds exist: interface, event and field. Each adds its own typing
  rule on top of these general ones. A kind outside the three cannot be graded
  by any of those rules, so it is refused at the general level rather than
  passed on to a loader that will guess.
- An endpoint is a single dotted path that contains both the instance and the
  element on it, and the split between them is not syntactic. It is found by
  matching the longest declared instance path that prefixes the endpoint, which
  is why a nested instance and its parent can both be legitimate endpoints and
  why the deeper one has to win.
- Two failure shapes look alike and are not: an endpoint that resolves to no
  declared instance dangles, and an endpoint that resolves exactly onto an
  instance names no element at all. The first usually means a missing instance;
  the second means a truncated path.
- Scope is the assembly's own instance set. An endpoint reaching a path the
  assembly did not create is out of scope even when that path exists somewhere
  in the simulator, because the assembly cannot guarantee its presence at the
  moment it is applied.

## Workflow

1. Build the instance scope from the declared instance paths, refusing a path
   declared twice before any link is examined.
2. For each link, validate the name as an identifier and record it, flagging a
   repeat against the position that first used it.
3. Categorize the declared kind against the three admitted kinds and stop
   grading a link whose kind is outside them.
4. Resolve each endpoint by longest declared-prefix match, separating the
   dangling case from the names-no-element case in the finding text.
5. Compare the two resolved instances; unless the assembly explicitly permits a
   self-link, a link whose endpoints sit on one instance is refused.
6. Form the (kind, source, target) signature and flag a second link carrying a
   signature already seen, naming the link it duplicates.
7. Report the accepted links, a per-kind tally for the kind-specific gates that
   run next, and every finding.

## Pitfalls

- Splitting an endpoint on the last dot. The element of a link can itself be a
  nested path, so a fixed split puts the wrong boundary between instance and
  element and turns a valid endpoint into a dangling one.
- Matching the first instance prefix rather than the longest. A parent instance
  prefixes every child path, so first-match silently attaches a child's element
  to its parent and the link connects something that was never intended.
- Treating a repeated link as harmless because both copies are identical. The
  duplicate is what makes a later single-sided amendment diverge, and an
  identical pair is the only kind a text diff will not show as a conflict.
- Grading kind-specific typing before the general rules. A field-type mismatch
  reported on a link whose target does not exist sends the reader to the
  datatypes when the real defect is a missing instance.
- Permitting a self-link by default because a model legitimately feeds itself.
  Self-connection is a deliberate assembly decision; making it the default hides
  the common case where a copied link never had its target updated.

## Behavior contract (gate 3)

The identifier rule, instance-scope construction, longest-prefix endpoint
resolution, kind grading, self-link rule and duplicate-signature detection are
exercised by the gate 3 contract test:
scripts/test_e4008_link_general.py against
scripts/e4008_link_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_link_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
