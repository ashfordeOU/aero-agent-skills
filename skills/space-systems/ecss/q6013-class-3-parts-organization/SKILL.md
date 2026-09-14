---
name: q6013-class-3-parts-organization
description: "Allocate organizational responsibility for commercial EEE part control at the lowest assurance class under ECSS-Q-ST-60-13C clause 6.1.2.1: refuse an organization the project plan records nowhere, accept combined duties because this class lets one role hold several, require at least one holder for part-selection approval, take coverage as the share of duties carried by at least one role and judge it against a floor below unity under a named tolerance, name every duty nobody carries, flag a role past the concentration ceiling with no deputy named, total the declared effort against its floor, and require a stated location for the parts decision record. Use when a thin parts function has to become a responsibility verdict. Trigger: ecss, q-st-60-13c-clause-6-1-2-1, class-three-commercial-eee-parts-responsibility, combined-parts-duty-assignment, parts-role-deputy-continuity, parts-responsibility-coverage-floor, declared-parts-effort-fte-floor, parts-decision-record-location."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-parts-organization, q-st-60-13c-clause-6-1-2-1, class-three-commercial-eee-parts-responsibility, combined-parts-duty-assignment, parts-role-deputy-continuity, parts-responsibility-coverage-floor, declared-parts-effort-fte-floor, parts-decision-record-location]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Parts Organization (space-systems/ecss/q6013-class-3-parts-organization)

Use when the task is the clause 6.1.2.1 organization question of
ECSS-Q-ST-60-13C at the lowest assurance class: a project intends to fly
commercial EEE parts with a small team, and what has to exist is a recorded
assignment of who carries which part-control duty.

## Domain quick reference

- The clause still asks the organization question, but it asks it of a much
  smaller team. Reading the highest class's answer onto this one produces a
  finding on every real project instead of a useful one, so three things are
  deliberately relaxed and one is not.
- Duties may be combined. One role holding part selection, procurement source
  control and the parts list is ordinary here rather than a split
  accountability, so a duty counts as covered when at least one role carries
  it — the opposite of the highest class, which counts a duty only when
  exactly one unit holds it.
- Coverage is judged against a floor below unity. The class accepts that a
  duty or so is carried by the project's general quality function rather than
  by a named parts role. That gap is reported, and it is survivable, provided
  the function carrying it knows it owns it.
- The exception is part-selection approval. A project with nobody able to say
  yes to a commercial part entering the design has no parts control at this
  class or any other, so a missing anchor closes the assessment whatever the
  coverage arithmetic says.
- Independence stops being the test. A parts role sitting inside the design
  authority is normal at this class and is carried as an advisory, not a
  finding. What replaces it is continuity: the real failure mode of a small
  team is one person holding everything and then leaving, so a role past the
  concentration ceiling with no deputy named is the finding this class needs.
- Effort is the same argument in numbers. Responsibility assigned at a
  fraction of a person that could never exercise it is assignment on paper,
  which is why the declared effort is totalled and compared with a floor
  rather than assumed from the role titles.
- The decision has to land somewhere findable. There is no parts control board
  minute to fall back on here, so the location of the parts decision record is
  part of the organization rather than an afterthought — and it matters most
  exactly where the parts role sits inside the design authority.

## Workflow

1. Validate the responsibility policy: the coverage floor, the effort floor,
   the concentration ceiling and whether a decision record location is
   required. A coverage floor above one, an effort floor beyond the duty set,
   or a ceiling covering every duty is refused rather than used.
2. Validate every declared role: a non-blank identifier, no duplicate
   identifier, duties drawn only from the recognised names, an effort between
   zero and one whole person, and the deputy, project-plan and design-authority
   flags.
3. Establish responsibility exists at all. An absent role set, or a set no
   part of which the project plan records, closes the assessment on
   responsibility not assigned; a single unrecorded role among recorded ones
   is an advisory.
4. Check the anchor duty has at least one holder, and close on responsibility
   not assigned when it has none.
5. Build the duty assignment, take coverage as the share of duties carried by
   at least one role, name every duty nobody carries, and compare the coverage
   against the below-unity floor with a tolerance that absorbs representation
   error.
6. Check concentration: name every role carrying more duties than the ceiling
   with no deputy named, then total the declared effort and compare it with
   its floor under the same tolerance.
7. Check the parts decision record location is stated, and report the anchor
   holders, the coverage, the gaps, the concentration, the effort and one
   verdict: responsibility not assigned, coverage below the class floor,
   continuity not assured, effort below the floor, decision record not
   located, or organization meets class three.

## Pitfalls

- Applying the highest class's singularity test here. Two roles sharing a
  duty is combination, not a split, and reporting it as a finding buries the
  gaps that actually matter.
- Reading the below-unity floor as permission to leave any duty unassigned.
  The anchor is exempt from the floor, and an uncovered duty is still named
  so the general quality function can pick it up knowingly.
- Treating a parts role inside the design authority as a finding. It is
  ordinary at this class; what it changes is how much the decision record
  location is worth, not whether the organization stands.
- Counting a named deputy as spare capacity. The deputy clears the continuity
  question, not the effort one, and a project can satisfy both names and
  neither hour.
- Assuming effort from a role title. A parts engineer at five per cent of a
  person is a title; the total is what the class compares against its floor.
- Leaving the parts decision record wherever it happened to be written. With
  no board minute behind it, an unlocated decision is a decision nobody can
  reconstruct at the next review.
- Accepting an organization that exists only in a conversation. A role the
  project plan records nowhere works today and is invisible to whoever
  inherits the project.

## Behavior contract (gate 3)

The policy validation, role validation, project-plan and anchor checks, the
duty assignment with its combined-duty coverage, the gap naming, the
concentration and deputy check, the declared effort against its floor, the
decision record location and the responsibility verdict are exercised by the
gate 3 contract test:
scripts/test_q6013_class_3_parts_organization.py against
scripts/q6013_class_3_parts_organization_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_parts_organization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
