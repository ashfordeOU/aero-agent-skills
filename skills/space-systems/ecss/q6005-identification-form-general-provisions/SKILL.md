---
name: q6005-identification-form-general-provisions
description: "Evaluate a hybrid technology identification form against the preparation and upkeep rules that apply to every supplier case under ECSS-Q-ST-60-05C clause 6.2.1. Use when a form has been issued, amended or is approaching its periodic review and the procurement authority needs to know whether it is still valid, who owes the next action, and what the next issue number is. Assesses the mandatory entries, the preparing and accepting roles, the issue identification, the change-driven reissue trigger and the review window, then returns a validity state, the next review date and an ordered findings list. Trigger: ecss, q-st-60-05, identification-form-general-provisions, hybrid-form-issue-numbering, hybrid-form-reissue-trigger, hybrid-form-periodic-review-window, hybrid-form-preparer-and-approver-roles, hybrid-form-validity-state."
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
  tags: [ecss, q-st-60-hybrid-procurement-scope, q6005-identification-form-general-provisions, hybrid-form-issue-numbering, hybrid-form-reissue-trigger, hybrid-form-periodic-review-window, hybrid-form-preparer-and-approver-roles, hybrid-form-validity-state]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Identification Form General Provisions (space-systems/ecss/q6005-identification-form-general-provisions)

Use when the task is the general-provisions step of ECSS-Q-ST-60-05C
clause 6.2.1 — the rules that hold for every supplier case, whatever
route the supplier is on: what the form must carry, who prepares and
accepts it, how it is identified, and what keeps it current after it has
been accepted once.

## Domain quick reference

- The mandatory entry set is route-independent. Whether a supplier is
  being assessed for the first time or is offering an established line,
  the same entries have to be on the form, because they are what makes
  one form comparable with another and with the same form a year later.
- Preparation and acceptance are separate roles held by separate
  parties. The supplier declares; the customer side accepts. A form
  prepared by the party that accepts it carries no independent
  declaration, so that combination is refused rather than noted.
- Identification is a pair, not a number. The issue tracks the
  declaration; the revision tracks the document. A change that makes the
  declared technology, process, materials, package, site or
  subcontracting different opens a new issue and resets the revision; a
  typographical or contact correction advances the revision and leaves
  the issue alone.
- When several changes are pending at once, the most demanding one sets
  the outcome. One technology change among a handful of editorial
  corrections still opens a new issue.
- Upkeep has two independent clocks. A change-driven reissue can fall
  due at any moment; the periodic review falls due a set interval after
  acceptance. They are graded separately and then combined, with the
  reissue outranking the review, because a form whose declaration is
  already out of date gains nothing from being reviewed on schedule.
- A review that is approaching is not a review that is late. A lead
  window separates due from overdue so that a form inside its notice
  period is actioned, not written up as a nonconformance.
- A form that was never accepted has no review window at all. That is
  its own state, not a review that happens to be overdue, and it beats
  every other condition.

## Workflow

1. Validate the declared entries against the closed entry vocabulary and
   list the mandatory ones the form does not carry.
2. Validate the roles: refuse a form the accepting party prepared, and
   refuse an accepting party that has no standing to accept. A form with
   no accepting role is unaccepted, which is reported, not refused.
3. Check the acceptance record is self-consistent — an acceptance date
   with no accepting role, or an accepting role with no date, is an
   input defect.
4. Parse the issue identification as an issue-and-revision pair and
   reject an issue below one or a missing revision field.
5. Reduce the pending changes to the most demanding kind and compute the
   identification the form moves to.
6. Compute the periodic review date from the acceptance date and the
   project review interval, clamping a month-end acceptance into a
   shorter target month, and grade it against the lead window.
7. Combine into one validity state in precedence order — never accepted,
   reissue owed, review overdue, review due, valid — and return it with
   the next review date, the signed day count and the findings.

## Pitfalls

- Applying a reduced entry set because the supplier looks established.
  The route changes how entries may be answered, not which entries the
  form owes; dropping one here removes the basis for comparing this form
  with the last one.
- Advancing the revision for a process change. The document did change,
  but so did the declaration, and a revision bump hides a technology
  movement inside what reads as an editorial edit.
- Taking the first pending change in the list. Order of arrival says
  nothing about severity; the reissue trigger has to be searched for
  across the whole pending set.
- Reporting a form inside its notice period as overdue. The lead window
  exists so the review can be scheduled; collapsing due into overdue
  turns routine upkeep into a finding and hides the genuinely late ones.
- Adding the review interval by day count. Intervals are calendar
  months, and a month-end acceptance date has to clamp into a shorter
  month rather than spill into the next one.
- Treating a never-accepted form as merely overdue. Nothing has started,
  so there is no interval to be late against, and the action owed is
  acceptance rather than review.

## Behavior contract (gate 3)

The entry validation, role separation, acceptance-record consistency,
issue parsing and advancement, dominant-change reduction, calendar-month
review dating, lead-window grading and the validity-state precedence are
exercised by the gate 3 contract test:
scripts/test_q6005_identification_form_general_provisions.py against
scripts/q6005_identification_form_general_provisions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_identification_form_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
