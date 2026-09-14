---
name: q6013-class-1-selection-overview
description: "Assess the selection duties a Class 1 commercial EEE component choice carries under ECSS-Q-ST-60-13C clause 4.2.1. Use when a project must show, per candidate part and once per programme, that the usage justification, franchised procurement route, radiation suitability, lifetime assessment, evaluation plan, obsolescence continuity and customer agreement are each owed to a named role and evidenced rather than assumed. Keeps a duty with no record apart from one open or rejected, stops a programme duty being re-owed by every part, and returns a selection-readiness verdict with the duty-coverage share against the declared minimum. Trigger: ecss, q-st-60-13c, class-1-commercial-component-selection, commercial-eee-usage-justification, franchised-procurement-route, component-radiation-suitability, component-evaluation-plan, customer-agreement-record, selection-duty-coverage."
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
  tags: [ecss, q-st-60-commercial-eee-scope, q6013-class-1-selection-overview, class-1-commercial-component-selection, commercial-eee-usage-justification, franchised-procurement-route, component-evaluation-plan, selection-duty-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Selection Duty Framing (space-systems/ecss/q6013-class-1-selection-overview)

Use when the task is the framing step of ECSS-Q-ST-60-13C clause 4.2.1 —
fixing what a Class 1 commercial component selection owes and who owes
it, before any single rule is applied to any single part. Class 1 is the
highest assurance category a project can put a commercial part into, so
the framing is the thing that decides which later checks are even
in scope.

## Domain quick reference

- The duties divide by scope, not by importance. The usage
  justification, the franchised procurement route, the radiation
  suitability assessment, the reliability-and-lifetime assessment and
  the component evaluation plan are owed once per candidate part; the
  customer agreement record and the obsolescence continuity plan are
  owed once per programme. A tool that re-owes a programme duty on every
  part reports one outstanding decision as a hundred open duties, and
  the project reading that list cannot find the one that mattered.
- Each duty has a named owner role — design authority, procurement
  authority, product assurance, or the customer. A duty reported without
  its owner cannot be chased, so the owner travels with the finding.
- Three record states are kept apart from absence because different
  people disposition them through different paperwork: held, open
  (an owner is working it), rejected (an owner has answered and the
  answer was no), and no record at all. Absence is the worst, because
  nobody can say whether the duty was skipped, lost or never scheduled.
- The assurance category selects the duty set. Class 1 owes the whole
  set; a lower category owes a declared subset, and the duties it drops
  are exactly what the lower category buys its relief with. Grading a
  lower-category part against the Class 1 set invents findings.
- The coverage share is a quotient of two duty counts, so a selection
  holding exactly the declared minimum can land a unit in the last place
  below it. That is absorbed inside the comparison; the declared minimum
  is never relaxed to make a boundary case pass.

## Workflow

1. Validate each component entry: a non-empty identifier, a known
   assurance category, and duty records naming only duties in the
   declared set with only declared record states. Reject a component
   listed twice in one selection rather than merging its records.
2. Resolve the duty set the category owes, split by scope, and grade
   each part against the per-component duties only.
3. Flag a programme duty filed against a part. It is not a pass and not
   a failure; it is a record filed at the wrong scope, and it is
   reported so it can be moved.
4. Grade the programme duties once, against the programme record set,
   using the highest assurance category present in the selection.
5. Roll each part to a verdict by worst state: absence outranks
   rejection, rejection outranks open, open outranks held.
6. Compute the duty-coverage share over every owed duty instance — the
   per-part duties across all parts plus the programme duties once — and
   compare it with the declared minimum, absorbing representation error
   at the boundary with a named tolerance.
7. Report the selection verdict, the weakest part, the parts grouped by
   verdict, the coverage share, and every finding with its owner role.

## Pitfalls

- Re-owing the customer agreement and the obsolescence continuity plan
  on every part. One outstanding programme decision then reads as a
  hundred open duties, the coverage share is dragged down by the same
  record counted many times, and the real per-part gaps disappear.
- Collapsing "no record" into "failed". A rejected duty has an owner and
  an answer; an absent duty has neither, and merging them hides the only
  state nobody is working.
- Grading a Class 2 or Class 3 part against the Class 1 duty set. The
  dropped duties are the declared relief of the lower category, so the
  extra findings are invented, not found.
- Reporting a missing duty without its owner role. Product assurance,
  procurement and the customer clear different paperwork, and an
  unattributed finding sits in the list until somebody guesses.
- Relaxing the declared coverage minimum to clear a selection that sits
  exactly on it. An equality at the limit is a representation question,
  handled by the tolerance inside the comparison; the declared value
  stays as specified.

## Behavior contract (gate 3)

The component record validation, the scope split, the owner attribution,
the four record states, the misfiled programme duty, the coverage share
against the declared minimum and the selection roll-up are exercised by
the gate 3 contract test:
scripts/test_q6013_class_1_selection_overview.py against
scripts/q6013_class_1_selection_overview_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_selection_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
