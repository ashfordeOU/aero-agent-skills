---
name: q6013-class-3-procurement-specification
description: "Use when a thin purchase specification must be judged fit to order against. Evaluate whether the documentation a lowest assurance commercial order rests on carries the content ECSS-Q-ST-60-13C clause 6.3.2 still asks for: accept a purchase specification, a cited manufacturer data sheet or the order text as the carrier of each required item, refuse a data-sheet citation naming no issue, keep the ordered temperature range, the acceptance route and the traceability requirement off the data sheet alone, require an identified and approved specification before it may carry anything, and take content completeness against the declared floor. Trigger: ecss, q-st-60-13c-clause-6-3-2, class-three-purchase-specification-content, order-content-carrier-assignment, data-sheet-citation-issue-lock, specification-header-required, procurement-content-completeness-floor."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-procurement-specification, q-st-60-13c-clause-6-3-2, class-three-purchase-specification-content, order-content-carrier-assignment, data-sheet-citation-issue-lock, specification-header-required, procurement-content-completeness-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 3 Procurement Specification (space-systems/ecss/q6013-class-3-procurement-specification)

Use when the task is clause 6.3.2 of ECSS-Q-ST-60-13C at the lowest assurance
class: a purchase specification has been drafted for commercial electrical,
electronic and electromechanical parts, and the question is whether the
documentation behind the order holds enough for the order to be placed and the
delivery to be dispositioned.

## Domain quick reference

- The specification is allowed to be thin here, and that is the point of the
  class. What it is not allowed to be is incomplete: the required content may
  move to another carrier, but it may not disappear. The question is therefore
  where each required item sits, not how long the specification runs.
- Three carriers are permitted at this class: the purchase specification, the
  manufacturer's published data sheet, and the order text itself. Each
  required item names the carriers the class permits for it, and an item
  placed outside that set is misplaced rather than merely undocumented.
- Three items may never rest on the data sheet alone. The ordered operating
  temperature range, the acceptance route for the delivery and the marking and
  lot traceability requirement are what the project is buying, not what the
  manufacturer happens to publish, and a reissued data sheet would rewrite
  them without anybody being told.
- A data-sheet carrier counts only where the citation names the document and
  its issue. A citation with no issue points at whatever the manufacturer says
  today, which is a moving target rather than an ordered condition.
- The specification may carry content only once it is identifiable: an
  identifier, an issue and an approving authority. A draft with no issue
  cannot be invoked on an order, because nobody can later say which text the
  delivery was bought under, and every item resting on it inherits that.
- An item also needs a location inside its carrier. "It is in the data sheet"
  is not a content declaration; the section or table is what a receiving
  inspector reads to disposition the delivery.
- Completeness counts the items actually traceable to a permitted, identified
  carrier at a cited location. The share of that content resting on the data
  sheet is reported rather than judged: an order leaning entirely on published
  data is permitted here and is a different risk posture from one that fixes
  its own content, and the reviewer needs to see which one they hold.
- A figure landing exactly on the floor is admissible, the tolerance absorbing
  representation error rather than widening the floor.

## Workflow

1. Validate the completeness policy: the floor the content completeness has to
   reach. A floor of nothing is refused rather than used.
2. Validate the specification header where one is declared -- identifier,
   issue, approving authority -- and record which of the three are missing.
3. Validate every content declaration: the item, a recognized carrier, the
   location inside that carrier and, for a data-sheet carrier, the citation
   document and issue. Reject an item declared twice.
4. Grade each required item against the carriers the class permits for it,
   marking a misplaced item before anything else is asked of it.
5. Refuse a data-sheet carrier whose citation names no document and issue, a
   specification carrier with no identified specification behind it, and a
   declaration citing no location.
6. Record any declaration naming an item the class does not require as its own
   finding.
7. Take the content completeness and the data-sheet share, compare
   completeness with the floor under a named tolerance, and close on one
   verdict -- documentation not declared, content carried where the class does
   not permit it, content absent, content not traceable to an identified
   carrier, completeness below the floor, or documentation meets class 3
   expectations -- carrying every finding, not the first.

## Pitfalls

- Reading a short specification as an incomplete one. Brevity is the class
  working as intended; the defect is content that sits in no carrier at all.
- Letting the acceptance route rest on the data sheet. The manufacturer never
  agreed to it, so the delivery arrives with nothing to be dispositioned
  against and the argument starts at goods inwards.
- Citing a data sheet with no issue. The deferral is permitted at this class,
  but the issue is what turns a pointer into an ordered condition.
- Ordering against an unissued specification. Whichever revision the supplier
  happens to hold silently becomes the acceptance basis.
- Declaring a carrier with no location. The item reads as covered on the
  register while nobody can find the sentence it was covered by.
- Judging the data-sheet share instead of reporting it. Published data is a
  legitimate carrier here; the share is risk posture, not a defect.
- Widening the floor to pass an exact-equality case. An equality at the floor
  is a representation question handled by the tolerance in the comparison.
- Stopping at the first finding. The specification owner needs the whole list
  to close it in one revision rather than one revision per finding.

## Behavior contract (gate 3)

The completeness-policy validation, specification-header validation, the
permitted-carrier register, declaration and citation validation, the
data-sheet issue lock, the location requirement, per-item grading, the
extraneous-declaration finding, the completeness and data-sheet share, the
floor comparison and the overall verdict are exercised by the gate 3 contract
test: scripts/test_q6013_class_3_procurement_specification.py against
scripts/q6013_class_3_procurement_specification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_procurement_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
