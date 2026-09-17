---
name: q60-pure-tin-whisker-risk-analysis
description: "Assess whether a submitted pure tin whisker risk analysis carries the content ECSS-Q-ST-60C clause 9.2 expects of it. Use when a whisker risk assessment arrives for review and someone has to say whether it is acceptable as submitted or a document with holes: confirm every declared pure tin item is addressed, grade each required section by whether it is absent, merely asserted or substantiated with cited evidence, demote a substantiated claim that cites nothing, fail a missing mandatory section however high the weighted total climbs, and judge both content floors at the boundary under a named tolerance. Trigger: ecss, q-st-60c-clause-9-2, pure-tin-whisker-risk-analysis-content, whisker-analysis-section-substantiation, declared-pure-tin-item-coverage, whisker-mitigation-justification-review, residual-whisker-risk-acceptance-statement."
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
  tags: [ecss, q-st-60c-eee-component-scope, q60-pure-tin-whisker-risk-analysis, q-st-60c-clause-9-2, pure-tin-whisker-risk-analysis-content, whisker-analysis-section-substantiation, declared-pure-tin-item-coverage, whisker-mitigation-justification-review, residual-whisker-risk-acceptance-statement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Pure Tin Whisker Risk Analysis Content (space-systems/ecss/q60-pure-tin-whisker-risk-analysis)

Use when the task is the whisker risk analysis of ECSS-Q-ST-60C clause 9.2 —
not computing the risk a pure tin finish carries, but reviewing the document
that reports it and deciding whether a reader has been given enough to
believe its conclusion.

## Domain quick reference

- The deliverable is the subject here. Somebody else bounds the whisker
  length; this review asks whether the analysis that reports it shows its
  working, and the two jobs fail in different ways.
- Coverage comes before quality. An analysis that reasons beautifully about
  nine of eleven declared pure tin items has not covered the hardware, and no
  amount of depth on the nine repairs the two.
- Presence is not content. A section that states a conclusion earns partial
  credit; one that substantiates it against cited evidence earns full credit;
  the difference between the two is the whole point of the review.
- A substantiation that cites nothing is an assertion with a confident
  heading. The declaration belongs to the author and the credit belongs to
  the reviewer, so the demotion is made in the review, not negotiated.
- Mandatory sections are not weights. Identification, composition evidence,
  the mission basis, the length bound, the bridging assessment, the
  mitigation justification and the residual risk statement fail the analysis
  by their absence, whatever the weighted total reaches without them.
- The optional sections — growth drivers, circuit consequence, surveillance —
  are what separate a defensible analysis from a sufficient one, which is why
  they carry weight rather than a veto.
- Two floors, not one. Above the upper floor the analysis stands; between the
  floors it stands with actions written against it; below the lower floor it
  goes back. Both floors are judged under a named tolerance so a document
  sitting exactly on one is not failed by float representation.

## Workflow

1. Validate the submission: the document identifier, the declared pure tin
   item count, how many of those items the analysis addresses, and the
   sections it contains.
2. Normalize every submitted section against the required content list,
   rejecting an unknown heading and a section submitted twice, and marking
   anything unsubmitted as absent.
3. Credit each section from its state, demoting a substantiated section that
   cites no evidence to asserted before any credit is taken.
4. Compute the item coverage fraction and the weighted content score across
   every required section.
5. List the mandatory sections that are absent; any entry on that list, or
   any shortfall in item coverage, blocks acceptance on its own.
6. Grade the score against the two content floors at the boundary under the
   named tolerance and return the verdict with the findings and the actions
   that close them.

## Pitfalls

- Reviewing the risk instead of the analysis. Agreeing with a conclusion is
  not the same as finding it supported, and a reviewer who re-derives the
  number has stopped reading the document.
- Counting headings. A table of contents matching the required list says
  nothing about whether any section carries an argument.
- Taking "substantiated" from the author's own summary table. A claim with no
  reference behind it is an assertion, and crediting it as more hides exactly
  the gap the review exists to find.
- Letting a strong total absorb a missing mandatory section. The weighted
  score and the mandatory list are separate tests and both have to pass.
- Scoring the sections and forgetting the hardware. Item coverage is checked
  against the declared list, not against the sections, so a complete document
  about half the parts is still incomplete.
- Returning a score with no actions. A verdict that does not say what would
  close it puts the next revision back in the reviewer's lap.

## Behavior contract (gate 3)

The section catalogue, state credit and evidence demotion, duplicate and
unknown section rejection, absent-section defaulting, item coverage, the
weighted content score, the mandatory shortfall list, the two boundary
tolerant content floors and the finding and action lists are exercised by the
gate 3 contract test:
scripts/test_q60_pure_tin_whisker_risk_analysis.py against
scripts/q60_pure_tin_whisker_risk_analysis_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q60_pure_tin_whisker_risk_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
