---
name: q2030-comp-general
description: "Determine which requirement governs a harness topic under ECSS-Q-ST-20-30C sections 7.1 and 7.2. Use when the task is reconciling an IPC/WHMA-A-620 acceptance criterion with the space addendum row that modifies it and the complementary requirement that sits above both: filtering each requirement by the harness type and assurance level it applies to, ranking the surviving sources so a complementary requirement outranks an addendum row and an addendum row outranks the external basis, demoting a project deviation carrying no approved waiver, and listing the topics left on the external basis alone. Trigger: ecss, q-st-20-30c, ecss-ipc-precedence, complementary-requirement-resolution, harness-requirement-applicability, harness-deviation-waiver, ipc-whma-a-620-addendum."
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
  tags: [ecss, q-st-20-30-harness-scope, q2030-comp-general, ecss-ipc-precedence, complementary-requirement-resolution, harness-requirement-applicability, harness-deviation-waiver, ipc-whma-a-620-addendum]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Complementary Requirements, General (space-systems/ecss/q2030-comp-general)

Use when the task is the general provision of ECSS-Q-ST-20-30C
sections 7.1 and 7.2 — what the complementary requirements of section 7
are for, which harness builds they bear on, and how they sit against
the external acceptance basis and its space addendum when both speak to
the same topic.

## Domain quick reference

- The harness standard does not restate its acceptance basis. It adopts
  an external criteria set, modifies part of it through a space
  addendum, and then adds complementary requirements of its own. Any
  given topic can therefore be addressed from three directions at once,
  and the question a reviewer actually asks is which of them governs.
- The ladder runs one way. A complementary requirement governs over the
  addendum row it complements, and an addendum row governs over the
  base external criterion it modifies. Reading the external criterion
  first and treating the complementary one as commentary inverts the
  ladder and is the common mistake.
- Applicability is decided before precedence, not after. A requirement
  scoped to a harness type or an assurance level that this build is not
  simply does not enter the contest for that topic. Calling it
  overridden misreports what happened, and a topic where nothing
  applies is a gap in the requirement set rather than a free pass.
- A project deviation sits above the ladder only once it is approved. A
  deviation carrying no waiver reference is an unapproved relaxation,
  so it is demoted out of the contest and reported; letting it govern
  turns an open action into a silent tailoring.
- Two sources at the same rank that say different things are not
  resolvable by rank. That is a defect in the requirement set, and it
  has to be surfaced rather than settled by whichever record was read
  first.
- Topics left governed by the external basis alone are legitimate and
  worth listing. They are where the standard adds nothing, which is
  exactly where a reviewer checks that nothing was meant to be added.

## Workflow

1. Validate the harness the set is resolved against — identifier, type
   and assurance level — and validate each requirement record: topic,
   source, criterion, applicable types and levels, and waiver
   reference. An unknown source, a bare string where a scope sequence
   belongs, or a waiver on something that is not a deviation is an
   input error, not a case to normalize away.
2. Group the requirement set by topic, preserving the order topics were
   first seen so the report is reproducible.
3. For each topic, drop the requirements that do not apply to this
   harness type and assurance level.
4. Compute the effective rank of each survivor, demoting a deviation
   with no approved waiver to no rank at all and recording that
   finding.
5. Take the highest surviving rank; when more than one source sits
   there with different criteria, raise the conflict finding rather
   than picking silently, then settle on a deterministic choice so the
   report is stable.
6. Report a topic with no applicable requirement as unresolved, and a
   topic governed by the external basis alone as such.
7. Aggregate: how many topics each source governs, the share governed
   by the standard itself, the unresolved list, and which findings
   block the set as it stands.

## Pitfalls

- Resolving precedence before applicability. A requirement scoped to
  another harness type never competed, and reporting it as overridden
  hides the real question of whether this build has a requirement at
  all.
- Letting an unapproved deviation govern because it is the most
  specific record on the topic. Specificity is not authority; the
  waiver is.
- Settling a same-rank disagreement by picking the first record. The
  disagreement is the finding, and a deterministic pick is only there
  to keep the report stable, not to close it.
- Treating a topic governed by the external basis alone as a defect. It
  is a legitimate outcome and should be listed, not blocked.
- Assuming the addendum replaces the base criterion wholesale. It
  modifies specified rows; where it is silent, the base criterion is
  still the governing one.

## Behavior contract (gate 3)

The harness and requirement validation, applicability filtering,
precedence ranking with the unwaived-deviation demotion, per-topic
resolution with the same-rank conflict and no-applicable-requirement
findings, topic grouping and the set-level aggregation are exercised by
the gate 3 contract test: scripts/test_q2030_comp_general.py against
scripts/q2030_comp_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2030_comp_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
