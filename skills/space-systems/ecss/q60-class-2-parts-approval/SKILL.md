---
name: q60-class-2-parts-approval
description: "Assess whether every part proposed for Class 2 flight use carries the justification, documents and gate clearance of ECSS-Q-ST-60C clause 5.2.4: hold each submission to the justification record and to the separate approval document set, read the gate that governs the part from how it is procured and treat an approval granted after it as late however complete it is, refuse an approval outside its validity window, release nothing on a conditional approval until every condition carries a closure record, and name each proposed part nobody ever submitted. Use when a proposed parts list has to become a released flight list. Trigger: ecss, q-st-60c-clause-5-2-4, class-2-part-approval-justification, class-2-approval-document-set, class-2-approval-gate-timing, class-2-conditional-approval-closure, class-2-flight-release-status."
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
  tags: [ecss, q-st-60c-class-2-eee-scope, q-st-60c, q60-class-2-parts-approval, q-st-60c-clause-5-2-4, class-2-part-approval-justification, class-2-approval-document-set, class-2-approval-gate-timing, class-2-conditional-approval-closure, class-2-flight-release-status]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Parts Approval (space-systems/ecss/q60-class-2-parts-approval)

Use when the task is clause 5.2.4 of ECSS-Q-ST-60C: the justification record,
the approval documents and the project gates that every electrical, electronic
and electromechanical part proposed for Class 2 flight use has to clear before
it may be built into flight hardware.

## Domain quick reference

- Approval is per part, not per supplier and not per programme. A supplier
  approved on another part number carries nothing here, so the first question
  is always whether this part was ever submitted at all.
- The justification record is what the approval is granted against. It says
  what the part does, why this assurance class is adequate for that use, what
  evaluation or qualification stands behind it, what derating and worst-case
  work covers it, and what is actually being bought. Each absent field is a
  separate gap with a separate repair.
- The approval documents are a second, independent set. A complete
  justification carried on an incomplete document set is an approval nobody
  can audit afterwards, and the two are therefore never merged into one score.
- Approval is a deadline, not only a decision. Which gate governs comes from
  how the part is procured: a long-lead item has to be approved before the
  design is frozen around it, a catalogue item by the design review, a late
  substitution later still. An approval granted after its governing gate is
  late even when it is otherwise perfect, because the decisions it was meant
  to inform were already taken.
- An approval outside its validity window is not an approval. The window
  exists because the part, the source and the design around it all drift.
- A conditional approval releases nothing. Until every condition carries a
  closure record the part is conditionally approved, which is a state, not a
  slower kind of release.
- The category declared on the list has to be the category being released. A
  part carried at another class on the components list is not released by this
  check, whatever its paperwork says.
- One blocked part blocks the list. A flight parts list is released as a set,
  so the part-by-part result and the list-level result are both reported.

## Workflow

1. Take the proposed parts list and read each entry: part number, how it is
   procured, and the assurance category it is declared at.
2. Look for an approval record at all. A proposed part with none is not
   approved, and it is named rather than counted as merely incomplete.
3. Check the justification record field by field, collecting every absent
   field instead of stopping at the first.
4. Check the approval document set separately, the same way.
5. Read the governing gate from the procurement role and compare it with the
   gate the approval was granted at; later is late.
6. Check the approval against its validity window, absorbing an age that lands
   exactly on the edge with a named tolerance rather than by moving the edge.
7. For a conditional approval, walk its conditions and require a closure
   record on each one.
8. Return a status per part and a single list-level verdict, with every
   finding attached to the part number it belongs to.

## Pitfalls

- Counting a supplier approval as a part approval. The unit the verdict
  attaches to is the part number, and the list is checked entry by entry.
- Treating an incomplete submission as a submission with nothing wrong with
  it. A review that could not be performed is not a review that passed.
- Merging the justification record and the document set into one completeness
  figure. They fail independently and they are repaired independently.
- Accepting an approval that arrived after its governing gate because it
  arrived eventually. The design decisions it was supposed to inform were
  taken without it.
- Applying one deadline to every part. A long-lead item and a late
  substitution are not governed by the same gate.
- Reading a conditional approval as an approval with paperwork still to
  follow. Until the closure records exist the part is not released.
- Keeping an approval whose validity window has closed because nothing about
  the part changed. Its source and the design around it may have.
- Releasing a part carried on the components list at another assurance
  category, on the strength of an approval that looked complete.
- Reporting the first blocking reason only. A late approval that is also
  outside its window and also missing a document needs all three named.

## Behavior contract (gate 3)

The submission check, justification and document completeness sets, governing
gate derivation and timeliness comparison, validity window, conditional
closure rule, category check and list-level verdict are exercised by the gate
3 contract test: scripts/test_q60_class_2_parts_approval.py against
scripts/q60_class_2_parts_approval_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_2_parts_approval.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
