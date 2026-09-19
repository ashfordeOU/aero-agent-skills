---
name: q7005-analyst-qualification
description: "Determine whether an analyst may interpret infrared contamination spectra of a given contaminant family under ECSS-Q-ST-70-05C, and who has to check them. Use when a spectrum is waiting and the reader's endorsement, proficiency record and currency have to decide the question rather than seniority: hold qualification per contaminant family, grade a missed detection and a wrongly named species on separate thresholds, refuse a rate that too few rounds stand behind instead of scoring it zero, run currency forward by whole calendar months, and treat a short supervised count or a freshly lapsed currency as provisional work needing an independent check. Trigger: ecss, q-st-70-05-ir-contamination-scope, spectral-interpretation-qualification, contaminant-family-endorsement, analyst-proficiency-round-rate, spectral-misidentification-ceiling, interpretation-currency-window."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-analyst-qualification, spectral-interpretation-qualification, contaminant-family-endorsement, analyst-proficiency-round-rate, spectral-misidentification-ceiling, interpretation-currency-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Analyst Qualification (space-systems/ecss/q7005-analyst-qualification)

Use when the task is the quality-assurance provision on who reads the
spectra in an ECSS-Q-ST-70-05C infrared contamination analysis —
deciding whether a named analyst may interpret a spectrum of a given
contaminant family on a given day, and what supervision the answer
carries with it.

## Domain quick reference

- Qualification is held per contaminant family, not per person. A
  silicone and a fluorinated lubricant are read against different
  expectations and different interferences, and an endorsement in one
  says nothing whatever about the other. A roster that records one
  overall competence cannot answer the question that is actually asked.
- There are two error rates and they are not interchangeable. Failing to
  see contamination leaves a dirty part in the flow; naming the wrong
  species sends a cleaning campaign after the wrong residue and
  discredits the measurement that found it. They are graded on separate
  thresholds so a good detection record cannot hide a naming problem.
- A rate needs rounds behind it. Two rounds out of two is not a
  hundred percent competence, and no rounds at all is not zero
  competence either — it is absent evidence, and absent evidence is
  refused rather than scored.
- Qualification lapses. Currency runs from the last qualifying activity
  in whole calendar months, so a month-end activity expires at a month
  end, and the question is always about the day the spectrum is read.
- Provisional is an outcome, not a polite refusal. An analyst short on
  supervised interpretations, or just past currency, may do the work
  under an independent check by someone fully qualified in that family.
  Losing that middle state either stops competent people working or lets
  unchecked work through.
- A provisional reader with nobody qualified to check them is not a
  provisional arrangement at all. The work waits, and the record says
  why, rather than quietly proceeding unchecked.

## Workflow

1. Resolve the policy: the supervised-interpretation floor, the minimum
   round count, the correct-reading threshold, the misidentification
   ceiling, the currency window and the grace window — refusing an
   unknown key rather than ignoring it.
2. Validate the analyst record: a name, a non-empty endorsement list
   with no duplicates, a whole supervised count and a proficiency list.
3. Refuse the request outright when there is no training record, or when
   the family sits outside the endorsement.
4. Take the proficiency rounds for that family alone and compute the
   correct-reading rate and the misidentification rate over them.
5. Block when the rounds are too few to support a rate, when the
   correct-reading rate falls below its threshold, or when the
   misidentification rate rises above its ceiling — comparing with a
   tolerance so a rate landing exactly on a threshold is not lost to
   representation error.
6. Run currency forward by whole calendar months, clamping to the month
   end, and take the days left on the day of the reading. Inside the
   grace window a lapse is provisional; beyond it, blocking.
7. Mark a short supervised count provisional.
8. Verdict: not qualified on any blocking finding, provisional on any
   provisional finding, qualified otherwise. Then assign a reader from a
   roster, preferring a fully qualified one, and refuse the work when
   only a provisional reader is available with nobody to check them.

## Pitfalls

- Recording one overall competence per analyst. The question is always
  about a family, and a single grade answers it wrongly in both
  directions.
- Folding a missed detection and a wrong name into one score. They fail
  differently downstream and they need different remedies.
- Scoring an empty proficiency record as zero, or a two-round record as
  a perfect one. Both turn absent evidence into a number.
- Counting currency in years of 365 days. A month-end qualifying
  activity then expires a day early or a day late, every cycle.
- Collapsing provisional into pass or into fail. Into pass, unchecked
  work ships; into fail, the lab stops for a condition that has a
  defined remedy.
- Assigning a provisional reader with no qualified checker on the
  roster. The independent check is the whole basis of the provisional
  state; without it the state does not exist.

## Behavior contract (gate 3)

The policy merge, the per-family proficiency rates, the separate
misidentification ceiling, the too-few-rounds refusal, the
calendar-month currency and grace windows, the qualified, provisional
and refused verdicts and the roster assignment are exercised by the gate
3 contract test: scripts/test_q7005_analyst_qualification.py against
scripts/q7005_analyst_qualification_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7005_analyst_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
