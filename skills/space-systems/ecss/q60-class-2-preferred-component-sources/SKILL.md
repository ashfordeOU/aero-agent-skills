---
name: q60-class-2-preferred-component-sources
description: "Assess which Class 2 source costs the project the least added work under ECSS-Q-ST-60C clause 5.2.2.3: scope the qualification and screening steps a candidate's package style can physically be run through, subtract the evidence the source already holds, price what is left in effort units, campaign weeks and sample devices consumed, rank every candidate by the burden it leaves, then set the chosen part against the cheapest one and grade any step away against the reasons the project accepts. Use when a Class 2 parts list has to show it favoured the source needing the least upscreening. Trigger: ecss, q-st-60c-class-2-selection-scope, class-2-least-additional-qualification, residual-qualification-effort-index, class-2-upscreening-burden-ranking, upscreening-step-gap-list, lower-burden-equivalent-passed-over, class-2-source-effort-preference."
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
  tags: [ecss, q-st-60c-class-2-selection-scope, q60-class-2-preferred-component-sources, class-2-least-additional-qualification, residual-qualification-effort-index, class-2-upscreening-burden-ranking, upscreening-step-gap-list, lower-burden-equivalent-passed-over, class-2-source-effort-preference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Preferred Component Sources (space-systems/ecss/q60-class-2-preferred-component-sources)

Use when the task is the selection direction of ECSS-Q-ST-60C clause
5.2.2.3 -- deciding, for a Class 2 design, which candidate source
arrives closest to the assurance the class already asks for, and what
the step away from it costs when a different one is taken.

## Domain quick reference

- The direction is not "buy the best part". It is "buy the part that
  arrives closest to the assurance the class already asks for", because
  every step the source has not evidenced has to be paid for afterwards
  in a campaign the project runs itself.
- That makes preference arithmetic rather than a tier lookup. The
  question is how much of the applicable qualification and screening
  work each candidate leaves open, not which list its maker appears on.
- Applicability is settled before cost. A seal test on a plastic
  package is not a gap the source failed to close, it is a step that
  cannot be run on that package at all, and counting it as missing
  penalises exactly the sources the clause is steering toward.
- Evidence claimed for a step the package style cannot be run through
  is ignored rather than credited. Crediting it flatters a source that
  has, in fact, closed nothing.
- The burden is priced in three currencies because they do not trade.
  Effort units add up. Sample devices add up and are destroyed. Campaign
  weeks do not add up: separate steps run in parallel on separate
  samples, so the campaign is as long as its longest missing step.
- A source that leaves more than the project's ceiling of the
  applicable effort open is not an upscreening run with a long list, it
  is a qualification campaign, and it is planned and funded as one.
- Each package style is scored against its own applicable total, so a
  hermetic and a plastic candidate are comparable even though the step
  sets differ.
- A step away from the cheapest candidate is allowed, but it is bought
  with a recorded reason. The useful output is the ranking, the effort
  penalty the departure costs, and the weeks it adds.

## Workflow

1. Declare every candidate for the slot with its package style and the
   qualification and screening steps its source already evidences.
   Reject a claim against a step the catalogue does not contain.
2. Scope the applicable steps from the package style, then subtract the
   evidence held. Set aside any evidence that falls outside the scope,
   and say so rather than crediting it.
3. Price what is left: sum the effort, sum the sample devices, and take
   the longest lead rather than the total.
4. Turn the residual effort into an index against the applicable total,
   and give each candidate a disposition: arrives qualified, needs an
   upscreening run, or needs a full campaign.
5. Rank the candidates by residual effort, breaking ties by campaign
   weeks, then samples, then reference, so the order is deterministic.
6. Set the chosen part against the cheapest one. Report the least
   effort route taken, a departure recorded against an accepted reason,
   or a departure with no accepted reason -- with the effort and week
   penalties either way.

## Pitfalls

- Reading the clause as a quality ranking. The cheapest candidate here
  is the one that arrives with the most evidence already in hand, which
  is usually the better part and never automatically the dearer one.
- Counting a step that cannot be run on the package as a gap. That
  scores a plastic part against a hermetic step set and buries the
  source the clause is steering toward.
- Crediting evidence for an out-of-scope step. A source that submits a
  seal report for a plastic package has closed nothing, and the report
  is a sign the wrong step set was worked to.
- Summing campaign weeks across missing steps. They run in parallel on
  separate samples, so the sum overstates the schedule and can turn a
  cheap candidate into an apparently impossible one.
- Ignoring the sample count. Samples are consumed, so two candidates
  with equal effort are not equal when one destroys eleven devices from
  a small lot.
- Taking a dearer source with no recorded reason. The departure itself
  is allowed; leaving it unrecorded is what makes the parts list
  undefendable later.
- Comparing a residual index with a ceiling by bare arithmetic. The
  index is a ratio of two sums, so one built to sit exactly on the
  ceiling can land a few units in the last place above it; the
  comparison absorbs that representation error while the ceiling stays
  untouched.

## Behavior contract (gate 3)

The catalogue validation, package-style step scoping, residual burden
pricing, out-of-scope evidence handling, candidate disposition,
deterministic ranking and departure grading are exercised by the gate 3
contract test:
scripts/test_q60_class_2_preferred_component_sources.py against
scripts/q60_class_2_preferred_component_sources_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_2_preferred_component_sources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
