---
name: e3301-maintainability
description: "Evaluate a mechanism design against the maintenance-free intent of ECSS-E-ST-33-01 clause 4.2.4.4 and grade the exceptions the customer has actually approved. Use when a design declares servicing, relubrication, inspection or replacement actions and the programme needs to know which of them are permitted and which are an open non-compliance. Counts how often each declared action falls inside the mission, requires a referenced and dated customer approval plus declared access and tooling for anything done in orbit, and computes the life margin of limited-life items against the duty the mission accumulates. Trigger: ecss, e-st-33-01, mechanism-maintenance-free-design, approved-maintenance-action, mechanism-life-limited-item-margin, mechanism-duty-cycle-accumulation, in-orbit-maintenance-access-provision."
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
  tags: [ecss, e-st-33-mechanisms-scope, e3301-maintainability, mechanism-maintenance-free-design, approved-maintenance-action, mechanism-life-limited-item-margin, mechanism-duty-cycle-accumulation, in-orbit-maintenance-access-provision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Maintainability (space-systems/ecss/e3301-maintainability)

Use when the task is clause 4.2.4.4 of ECSS-E-ST-33-01 — establishing
that a mechanism is designed to need no maintenance, and where it is
not, that every remaining action is one the customer has agreed to and
the design can actually support.

## Domain quick reference

- Maintenance-free is the default, and the exception is an agreement,
  not an engineering opinion. An action that appears in a procedure
  without a referenced, dated customer approval is not a permitted
  action; it is an undeclared requirement on the operator.
- A recurring action has to be counted against the mission. An interval
  longer than the mission means the action never happens and belongs in
  the design description, not the maintenance plan; an interval shorter
  than it is a servicing programme somebody has to resource.
- The phase decides what the action costs. The same relubrication is a
  bench operation before delivery, a schedule risk during storage, and
  something close to impossible once the mechanism is in orbit.
- An approved in-orbit action still needs a route and a tool. Access
  that was never designed in is not access, and an action requiring the
  mechanism to be opened has no flight configuration that supports it
  at all.
- Limited-life items turn into maintenance whether or not anybody wrote
  a procedure. A lubricant or a bearing demonstrated to fewer cycles
  than the mission accumulates, at the required margin, is a
  replacement waiting to be scheduled.
- Life is compared against accumulated duty, not against calendar time.
  Cycles per day times mission days is the number to beat, and the
  margin factor sits on top of it because the demonstration was one
  specimen under one set of conditions.

## Workflow

1. Validate each declared action: identifier, phase from the known set,
   whether it opens the mechanism, its recurrence interval where it has
   one, and the approval and access records attached to it.
2. Count occurrences inside the mission: one for a single action, the
   whole number of intervals for a recurring one, and zero when the
   interval outruns the mission.
3. Grade the approval: absent, pending, or approved. Refuse a record
   claiming approval without a reference or a date, because it cannot
   be produced when asked.
4. Apply the in-orbit rules: an approved orbital action owes a declared
   access route and its tooling, and an action requiring disassembly is
   a finding regardless of approval.
5. Compute each limited-life item's required cycles from its daily duty
   and the mission length, form the margin ratio against the
   demonstrated life, and compare it with the required factor,
   absorbing representation error at the boundary with a named
   tolerance.
6. Return one verdict: maintenance-free when nothing is declared and
   every life margin holds, approved-maintenance when everything
   declared is permitted, and non-compliant otherwise.
7. Report the per-action records, the life margins and every finding,
   so the exceptions can be argued individually rather than as a block.

## Pitfalls

- Recording a maintenance action in a procedure and nowhere else. The
  design then depends on an operation nobody has agreed to perform, and
  the first time anybody costs it is after delivery.
- Accepting an approval with no reference or date. It cannot be
  produced at a review, so it is a malformed record rather than a weak
  one, and a register that scores it asserts something it cannot
  support.
- Treating an interval longer than the mission as maintenance. It
  never occurs, and carrying it as a demand inflates the maintenance
  programme while hiding the actions that do occur.
- Approving an in-orbit action without designing the access. The
  approval says the action is acceptable; it does not create a hatch, a
  clearance or a tool the crew or the arm can reach it with.
- Reading a life-limited item as a life figure rather than as a
  maintenance demand. An item short of the mission duty will be
  replaced, and whether that replacement is called maintenance does not
  change who has to do it.
- Comparing demonstrated life with calendar time. Two mechanisms of the
  same age accumulate very different cycle counts, and the duty is what
  the bearing and the lubricant actually see.
- Relaxing the life factor so a marginal item passes. An equality at
  the factor is a representation question, handled by the tolerance
  inside the comparison; the factor itself stays as specified.

## Behavior contract (gate 3)

The action validation, occurrence counting, approval grading, in-orbit
access and disassembly rules, limited-life duty accumulation and the
three-way verdict are exercised by the gate 3 contract test:
scripts/test_e3301_maintainability.py against
scripts/e3301_maintainability_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e3301_maintainability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
