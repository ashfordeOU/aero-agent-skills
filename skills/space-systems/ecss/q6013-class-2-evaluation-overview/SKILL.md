---
name: q6013-class-2-evaluation-overview
description: "Use when an evaluation plan or evaluation report decides whether a part may enter a Class 2 design. Evaluate the evaluation activity standing behind a commercial EEE part at the intermediate assurance class of ECSS-Q-ST-60-13C clause 5.2.3.1: take the campaign as one body of evidence, drop the elements the mission profile does not owe out of the denominator, grade each remaining element from its state, downgrade rather than break a heritage claim that only moves assembly site, weight the credit into a coverage fraction, hold the two elements no waiver and no similarity argument may buy, and return the outstanding elements with one campaign verdict. Trigger: ecss, q-st-60-13c-clause-5-2-3-1, class-two-evaluation-campaign, evaluation-element-applicability, class-two-heritage-downgrade, class-two-campaign-coverage-threshold, class-two-evaluation-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-2-evaluation-overview, class-two-evaluation-campaign, evaluation-element-applicability, class-two-heritage-downgrade, class-two-campaign-coverage-threshold, class-two-evaluation-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Evaluation Overview (space-systems/ecss/q6013-class-2-evaluation-overview)

Use when the task is clause 5.2.3.1 of ECSS-Q-ST-60-13C at the intermediate
assurance class: the evaluation that has to stand behind a commercial part
before it is used, taken as one campaign rather than as a stack of individual
tests. This leaf grades the campaign on what it covers, what the mission
profile does not owe, and what it still owes.

## Domain quick reference

- The campaign is a set of elements, and each element supplies a share of the
  assurance. Weighting them is what lets an incomplete campaign be ranked.
- Two elements are load-bearing even here. The manufacturer assessment and
  the constructional analysis each answer a question nothing else in the
  campaign answers, so neither a waiver nor a similarity argument buys them,
  whatever the coverage fraction says.
- Applicability is a property of the mission, not of the part. A radiation
  evaluation is owed only when a radiation requirement exists; an assembly
  compatibility check only when the assembly process departs from the
  qualified one. An element the profile does not owe leaves the denominator
  entirely -- it is neither credit nor a gap. Counting it as covered flatters
  the campaign; counting it as missing punishes it for a question nobody
  asked.
- The state of an element fixes the credit it earns. The intermediate class
  credits a similarity argument more generously than the highest class does,
  because the assurance being bought is lower -- but the credit is still
  partial and still a finding.
- A heritage claim is graded, not merely accepted or refused. A different
  manufacturer, a different part number, a notified process change or
  evidence outside its validity period each break it outright. A different
  assembly site does not: it downgrades the credit and raises a finding,
  because an audit can still recover that one.
- The intermediate class closes on a coverage threshold rather than on total
  coverage. The threshold is what separates this class from the highest one,
  and it never suspends the two unwaivable elements.
- An element nobody mentioned is absent, not excused. The campaign is graded
  against the applicable element set every time, so a silent declaration
  cannot shrink what it is measured against.

## Workflow

1. Name the part type and read the mission profile drivers, rejecting a
   driver the profile does not recognise.
2. Collect what each campaign element declares: its state, and for a heritage
   state the claim behind it.
3. Reject the declaration before grading when an element name or a state is
   unrecognised, when an element is declared twice, or when a heritage state
   carries no claim.
4. Expand the declaration to the full element set, mark each element
   applicable or not from the profile, and grade anything applicable but not
   mentioned as absent.
5. Grade each applicable element to a credit, running every heritage claim
   through the Class 2 rules and keeping the reasons it was downgraded or
   broken.
6. Zero the credit of an unwaivable element carried by a waiver or a
   similarity argument, and record the shortfall separately from the fraction.
7. Take the weighted credit over the applicable weight as the coverage
   fraction, test it against the class threshold, and rank the elements short
   of full credit heaviest first.
8. Name the verdict -- incomplete while the threshold is unmet or an
   unwaivable element is short, open actions when the threshold is met but
   findings remain, complete only when neither is true.

## Pitfalls

- Reusing the highest-class element set unchanged and reporting a campaign as
  short because it never owed the element in the first place.
- Marking a conditional element covered when the mission never raised its
  driver, which inflates the fraction with evidence nobody needed.
- Reading the coverage fraction as a score. It ranks what is outstanding and
  it is tested against a threshold; it never suspends the unwaivable pair.
- Letting a similarity argument carry the constructional analysis because the
  intermediate class is more generous elsewhere. That generosity stops at the
  two elements that cannot be bought.
- Refusing a heritage claim outright for an assembly site difference at this
  class, or accepting one whose part number moved. The two are not the same
  defect and they do not have the same repair.
- Treating an old but otherwise perfect heritage record as good forever. The
  validity period exists because the process behind it drifts.
- Grading only the elements the declaration happened to list, so an element
  nobody thought about never appears as missing.

## Behavior contract (gate 3)

The element weighting, mission-profile applicability, state credit, Class 2
heritage grading and downgrade, unwaivable element rule, coverage fraction,
class threshold, outstanding ranking and campaign verdict are exercised by
the gate 3 contract test:
scripts/test_q6013_class_2_evaluation_overview.py against
scripts/q6013_class_2_evaluation_overview_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_2_evaluation_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
