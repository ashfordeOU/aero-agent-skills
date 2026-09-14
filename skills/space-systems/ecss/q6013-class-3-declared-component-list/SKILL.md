---
name: q6013-class-3-declared-component-list
description: "Evaluate whether a declared component list was issued in time and has been kept true at the lowest assurance class under ECSS-Q-ST-60-13C clause 6.1.4: refuse a list carrying no reference, issue label or first issue milestone, compare that milestone with the review the list was meant to inform, age the document against its re-issue interval, separate a superseded line still carrying installed quantity from a line nobody re-confirmed and from a part under an open alert, and weight currency by installed quantity rather than by line count. Use when a parts baseline has to become an upkeep verdict. Trigger: ecss, q-st-60-13c-clause-6-1-4, class-three-declared-component-list, dcl-first-issue-milestone, dcl-reissue-interval-age, quantity-weighted-line-currency, retired-line-still-installed, dcl-open-alert-disposition."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-declared-component-list, class-three-declared-component-list, dcl-first-issue-milestone, dcl-reissue-interval-age, quantity-weighted-line-currency, retired-line-still-installed, dcl-open-alert-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Declared Component List (space-systems/ecss/q6013-class-3-declared-component-list)

Use when the task is the clause 6.1.4 issue and upkeep question of
ECSS-Q-ST-60-13C at the lowest assurance class: a declared component
list exists for commercial EEE parts, and the question is whether it was
raised early enough to govern anything and whether it still describes
the build.

## Domain quick reference

- The list is still required at this class. The two things asked of it
  are the two a light project drops: issue it early enough to inform a
  decision, and keep it true afterwards.
- Issue is a milestone question, not a date question. A list first
  issued after the design review it was meant to inform records parts
  already chosen, and no later re-issue recovers the review that had
  nothing to read. The first issue milestone is therefore compared with
  the required one, and a list raised earlier is fine.
- The document ages as well as its lines. Past the re-issue interval the
  list is a snapshot of a build standard that has moved, whatever state
  the individual lines are in, so the issue age is checked before any
  line is looked at.
- Upkeep is a quantity question, not a line-count question. A stale line
  on a resistor fitted four hundred times and a stale line on a spare
  fitted once are not the same debt, so currency is weighted by
  installed quantity across the active lines.
- Three upkeep defects are kept apart because they are repaired
  differently. A line nobody re-confirmed inside the confirmation
  interval is stale and needs a review. A superseded or withdrawn line
  still carrying an installed quantity is worse: the list and the build
  disagree about what is fitted, and that is caught before any currency
  arithmetic because the arithmetic would otherwise average it away. A
  line under an open alert is neither -- it is a live question about a
  part already installed, and it is dispositioned rather than re-dated.
- A line sitting exactly on the confirmation interval is current. The
  interval is the last admissible age, not the first inadmissible one,
  and the comparison tolerance absorbs representation error rather than
  widening the interval.
- The margin is worth as much as the verdict. A list re-issued just
  inside its interval, and a line confirmed just inside the confirmation
  window, both pass today and both fall due before anyone looks again.

## Workflow

1. Validate the upkeep policy first: the milestone the list must be
   issued by, the re-issue interval, the line confirmation interval, the
   quantity-weighted currency floor, the marginal band inside which an
   ageing issue or line is still advised on, and the open-alert flag. An
   unrecognised milestone, an interval of zero, or a band wider than the
   confirmation interval is refused rather than used.
2. Validate the list identity: a non-blank reference, a non-blank issue
   label, a recognised first issue milestone and a whole last-issue day.
   An absent list, or one missing any of those, closes the assessment on
   list not issued.
3. Validate every line: a non-blank part reference, no duplicate part, a
   recognised line status, a whole confirmation day not later than the
   assessment day, a whole installed quantity and a boolean alert flag.
   An empty line sequence is refused.
4. Take the issue age, then compare the first issue milestone with the
   required one. A first issue later than the milestone it was meant to
   inform closes on issue milestone missed.
5. Age the document against the re-issue interval and close on issue
   stale before looking at any line.
6. Name every superseded or withdrawn line that still carries an
   installed quantity and close on retired line still installed. This
   runs before the currency share so a disagreement between list and
   build cannot be averaged away.
7. Take the quantity-weighted currency share across the active lines,
   counting a line at or inside the confirmation interval as current,
   and compare it with the floor under a tolerance that absorbs
   representation error. Name every stale line, not the first.
8. Check the open alerts last, then report the reference, the issue, the
   first issue milestone, the issue age, the currency share, the stale
   lines, the retained retired lines, the open alerts and an advisory
   for the issue or any line falling due inside the marginal band. Close
   on one verdict: list not issued, issue milestone missed, issue stale,
   retired line still installed, line upkeep short, alert open, or list
   maintained.

## Pitfalls

- Counting stale lines rather than weighting them. Ten stale spares and
  one stale connector fitted across the whole harness read the same on a
  line count and nothing like the same on the build.
- Averaging a retired line into the currency share. A withdrawn part
  still fitted is a disagreement between the list and the hardware, not
  a percentage, and it is reported as its own verdict.
- Re-dating a line under an open alert. Confirming the line moves its
  date and answers nothing; the alert is dispositioned or the part comes
  out.
- Reading a re-issue as a fix for a missed first issue. The milestone
  that had no parts baseline to read stays without one, and only the
  next review benefits.
- Treating a line exactly on the confirmation interval as stale. The
  interval is the last admissible age, and the advisory rather than the
  verdict is what flags a line about to fall due.
- Reporting a bare pass. The currency share, the issue age and the stale
  line list are what the next issue is compared against, and the verdict
  word carries none of them.

## Behavior contract (gate 3)

The policy validation, list identity validation, line validation, the
issue and line ages, the first-issue milestone comparison, the retired
line check, the quantity-weighted currency share, the stale line list,
the open alert check, the marginal advisories and the list verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_3_declared_component_list.py against
scripts/q6013_class_3_declared_component_list_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_declared_component_list.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
