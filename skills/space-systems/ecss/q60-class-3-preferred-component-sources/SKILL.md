---
name: q60-class-3-preferred-component-sources
description: "Assess which Class 3 source on a shortlist demands the least added qualification under ECSS-Q-ST-60C clause 6.2.2.3: read each candidate's tier, subtract the activities it already holds evidence for, weight what is still owed into an effort index, add the weeks that outstanding programme needs run in sequence on one lot, refuse a part that cannot be tied to a single production lot however much schedule is left, drop a programme that overruns the integration date, then rank what survives and name the recommended source, the runner-up, the margin and the activity that dominates. Use when two Class 3 parts do the same job and one has to be chosen. Trigger: ecss, q-st-60c, q60-c3-least-added-qualification, q60-c3-upscreening-effort-index, q60-c3-source-tier-ranking, q60-c3-single-lot-traceability-bar, q60-c3-qualification-lead-time."
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
  tags: [ecss, q-st-60c, q60-class-3-preferred-component-sources, q60-c3-least-added-qualification, q60-c3-upscreening-effort-index, q60-c3-source-tier-ranking, q60-c3-single-lot-traceability-bar, q60-c3-qualification-lead-time, q60-c3-shortlist-ranking]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Preferred Component Sources (space-systems/ecss/q60-class-3-preferred-component-sources)

Use when the task is the selection direction of ECSS-Q-ST-60C clause
6.2.2.3 -- deciding, between Class 3 parts that do the same electrical
job, which source leaves the least qualification and upscreening work
still owed before the part can fly.

## Domain quick reference

- The preference between two parts that do the same job is not taste
  and not only price. It is the work still owed: the construction
  analysis, the lot traceability, the electrical upscreening, the
  thermal cycling, the burn-in, the destructive physical analysis, the
  radiation characterisation and the qualification testing the source
  has not already done. The preferred source leaves the shortest list.
- Two things decide that list. Where the part sits -- a part qualified
  to a recognised standard owes almost nothing, a manufacturer's space
  catalogue part owes a little, an automotive or industrial part owes a
  good deal, an uncharacterised commercial part owes nearly all of it.
  And what the supplier can already show.
- Evidence removes an activity from the list; it does not shrink one.
  An activity is either done and documented or it is owed in full, and
  a partial report that covers one lot and not the flight lot is not
  evidence for the flight lot.
- Effort and schedule are different currencies and a source can fail on
  either. Upscreening runs in sequence on one lot, so the weeks add up,
  and a cheap programme that lands after the integration date is not
  cheap. Every candidate is graded twice.
- One condition is not tradeable. Upscreening acts on a lot, so a part
  that cannot be tied to a single production lot cannot be upscreened
  at all: every result would describe a different population from the
  one that flies. That source is inadmissible rather than expensive and
  no amount of schedule buys it back.
- The useful output is a ranking with its numbers: the effort index and
  the weeks per candidate, the recommended source, the runner-up, the
  margin between them, and the single activity that dominates what is
  still owed -- because that activity is where a second supplier
  conversation pays for itself.

## Workflow

1. Name the function being sourced and the weeks left before the part
   is needed in the build.
2. For each candidate, read its source tier and the evidence already on
   file, then subtract the evidence from what the tier owes.
3. Weight the outstanding activities into an effort index against a
   wholly uncharacterised source, and add their weeks in sequence.
4. Refuse any candidate that cannot be tied to a single production lot,
   whatever its effort index says.
5. Drop any candidate whose outstanding programme does not fit the
   weeks available. A programme landing exactly on the date still fits.
6. Rank the survivors on effort, then on lead time, then on name so the
   answer is repeatable.
7. Close with the selected source, the runner-up, the effort margin,
   the dominant outstanding activity and one action per activity owed.

## Pitfalls

- Ranking on unit price. The purchase order is the small number; the
  upscreening campaign behind a cheap part is the large one, and it is
  the one this clause is about.
- Counting evidence that describes another lot. Upscreening results
  belong to the lot they were taken on, so a supplier report against a
  different date code removes nothing from the list.
- Choosing the lowest effort and discovering the schedule afterwards.
  Effort and weeks are separate grades; a source can win one and lose
  the other, which is why both are computed before anything is ranked.
- Buying an untraceable part because the effort looks survivable. There
  is no upscreening programme that fixes an unknown lot, so the
  candidate is out before the numbers are compared.
- Leaving a tie unreported. Two sources owing identical work were
  separated by lead time and then by name, and the reader has to know
  that the qualification argument did not decide it.
- Comparing an effort index or a lead time with its limit by bare
  arithmetic. The index is a quotient while the ceiling is a decimal
  literal, so a candidate built to sit exactly on the limit can land a
  few units in the last place over it; the comparison absorbs that
  while the limit stays untouched.

## Behavior contract (gate 3)

The activity table, the per-tier requirement sets, evidence subtraction,
the weighted effort index, the sequential lead time, the single-lot
traceability bar, the schedule drop, the ranking with its tie-breaks,
the selected source with runner-up and margin, the dominant activity
and the action list are exercised by the gate 3 contract test:
scripts/test_q60_class_3_preferred_component_sources.py against
scripts/q60_class_3_preferred_component_sources_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_3_preferred_component_sources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
