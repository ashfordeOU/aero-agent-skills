---
name: e2001-multipactor-verification-plan-content
description: "Use when audit what a multipactor-verification-plan adds to the generic verification-plan data item under ECSS-E-ST-20-01C clause 4.2.2: confirm the plan carries a multipactor-critical-item-list, the route agreed per item, the multipactor-margin policy, the drive level and dwell duration, the vacuum-and-venting conditions, the electron-seeding provision, an independent detection-method-pair, the pass-fail criteria and the non-conformance route; reject an entry that is a placeholder or a bare cross-reference back to the parent data item; and enforce the extra fields each route owes -- seeding and detection for a multipactor-test, susceptibility-model and secondary-electron-yield source for an analysis, reference-equipment and delta-justification for a similarity case. Trigger: ecss, e-st-20-electrical-scope, multipactor-verification-plan-content, verification-plan-data-item, multipactor-critical-item-list, electron-seeding-provision, detection-method-pair, similarity-delta-justification."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-verification-plan-content, multipactor-verification-plan-content, verification-plan-data-item, multipactor-critical-item-list, electron-seeding-provision, detection-method-pair, similarity-delta-justification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Multipactor Verification Plan Content (space-systems/ecss/e2001-multipactor-verification-plan-content)

Use when the task is the *content* of the multipactor-verification-plan
under ECSS-E-ST-20-01C clause 4.2.2 -- the multipactor-specific additions
the plan makes to the generic verification-plan data item. When the plan
was issued and when it has to be revised is a separate clause; this leaf
audits what is inside it.

## Domain quick reference

- The plan is not a free-standing document. It inherits the structure of
  the generic verification-plan data item and adds a defined set of
  multipactor-specific headings; the audit question is always "what does
  this plan add", never "does this plan exist".
- The additions fall into three groups. What is being verified: the
  multipactor-critical-item-list and the route agreed per item. Under
  what conditions: the drive level and dwell duration, the
  vacuum-and-venting conditions, the electron-seeding provision, the
  detection-method-pair. Against what: the multipactor-margin policy,
  the pass-fail criteria, the non-conformance route, and the schedule
  and facility that make the campaign real.
- A heading is not content. An entry left as a placeholder, marked
  to-be-defined, or written as a bare cross-reference back to the parent
  data item adds nothing -- and the cross-reference is the more
  dangerous of the three, because it reads as complete while pointing
  at the very document the clause says to extend.
- Each verification route owes different extra fields. A
  multipactor-test owes a drive level, a dwell, a vacuum pressure, a
  seeding source and a detection pair. An analysis owes the
  susceptibility-model, the secondary-electron-yield source, the gap
  geometry source and the margin it closes at. A similarity case owes
  the reference-equipment, the delta-justification against it, and the
  heritage evidence it rests on.
- Some fields carry an engineering check, not just a presence check. A
  seeding source has to be a recognized one; a detection pair has to be
  two distinct methods, ideally one global and one local; a dwell of
  zero demonstrates nothing; a chamber pressure above the vacuum ceiling
  puts the demonstration in the gas-breakdown regime instead of the
  vacuum multipactor one.
- The additions are not equally weighty. The item list and the route per
  item carry the plan; the facility schedule supports it. A weighted
  completeness keeps a plan that lost its item list from scoring as
  well as one that lost its schedule annex.

## Workflow

1. Resolve every declared heading to a catalogue key, accepting the
   common aliases and rejecting a heading that belongs to no addition.
   A duplicate key stops the audit -- two entries for one addition mean
   two answers to one question.
2. Decide entry by entry whether content was added: detailed adds,
   placeholder and to-be-defined do not, and a parent cross-reference
   does not while looking as though it did.
3. Take the weighted coverage over the catalogue, separating additions
   that are present, present in name only, and absent.
4. Resolve the verification route declared for each
   multipactor-critical item, and look up the extra fields that route
   owes.
5. Audit each item: report a missing field, then apply the engineering
   checks -- recognized seeding source, two distinct detection methods
   with mixed scope, positive dwell, chamber pressure at or below the
   vacuum ceiling, positive analysis margin, non-blank similarity
   justification. A structurally impossible record (no identifier,
   negative dwell, non-numeric level) stops the audit rather than
   becoming a finding.
6. Compare the weighted completeness with the agreed minimum, absorbing
   representation error exactly at the boundary rather than relaxing
   the requirement.
7. Aggregate: the plan's content is compliant only when completeness is
   met, no addition is absent or in name only, and no item carries a
   finding.

## Pitfalls

- Counting headings. A table of contents that names all ten additions
  scores full coverage on a word search and zero on this audit; the
  state of the entry is the measurement, not its title.
- Accepting a cross-reference to the parent data item as the addition.
  The clause exists because the generic plan does not cover multipactor;
  pointing back at it closes the loop on nothing.
- Applying one field list to every item. A similarity case audited
  against the multipactor-test fields reports five missing fields it
  never owed, and an analysis audited that way hides the one field it
  did owe.
- Treating the detection methods as a count. Two entries of the same
  local probe are one method twice, and two local methods still leave
  the global path unwatched.
- Reading a chamber pressure as a formality. Above the vacuum ceiling
  the discharge that appears is a gas breakdown, and the item leaves
  the campaign with evidence about a different physical mechanism.
- Weighting every addition alike. Losing the multipactor-critical-item-list
  is not the same finding as losing the facility annex, and a flat
  completeness makes the two indistinguishable in a review.

## Behavior contract (gate 3)

The content-key resolution, entry-state evaluation, weighted coverage,
route resolution, per-route field lists, seeding and detection
validation, item-level engineering checks, boundary-safe completeness
comparison and the aggregated plan verdict are exercised by the gate 3
contract test: scripts/test_e2001_multipactor_verification_plan_content.py
against scripts/e2001_multipactor_verification_plan_content_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2001_multipactor_verification_plan_content.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
