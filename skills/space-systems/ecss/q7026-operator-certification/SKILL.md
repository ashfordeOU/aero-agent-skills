---
name: q7026-operator-certification
description: "Assess whether a crimping operator holds a live certification for the flight termination in front of them under the personnel clause of ECSS-Q-ST-70-26C. Use when an operator picks up a tool and the training record, the qualification sample set and the currency of practice all have to agree: check the required modules are complete, grade the samples per tool and contact combination rather than in total, honour the vision-check validity, expire the certification on its own interval, and suspend rather than requalify an operator who simply has not crimped lately. Trigger: ecss, q-st-70-26, crimp-operator-certification, crimp-qualification-sample-set, crimp-operator-training-record, crimp-operator-vision-check, crimp-practice-currency-lapse."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-operator-certification, crimp-qualification-sample-set, crimp-operator-training-record, crimp-operator-vision-check, crimp-practice-currency-lapse]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Operator Certification (space-systems/ecss/q7026-operator-certification)

Use when the task is the personnel step of ECSS-Q-ST-70-26C — deciding
whether the person about to crimp flight hardware is certified for it
today, and if not, whether that is a requalification, a suspension or
an unfinished qualification.

## Domain quick reference

- Certification rests on two separate legs. Training says the operator
  was taught the process and can recognise the defects; the
  qualification sample set says the operator's own hands produced
  conforming terminations on real tooling. Neither leg stands in for
  the other, and a shop that trains without sampling has certified
  nobody.
- Samples are counted per tool and contact combination, not in total.
  Thirty good samples on one contact family say nothing about the
  family the operator is about to crimp, so an uncovered combination
  is a gap rather than a rounding error against a healthy total.
- Every sample in the required set passes both the pull test and the
  visual. A pass rate is not the criterion here; one failed sample
  means the set was not demonstrated, and the operator makes another
  set rather than averaging the one they have.
- A strong pull result does not rescue a failed visual. The visual
  catches the barrel geometry and strand condition that the pull test
  happens not to load, which is exactly why both are required.
- Standing decays on three independent clocks. The certification
  expires on its interval, the vision check expires on its own shorter
  one, and practice lapses when too long has passed since the last
  crimp. The earliest clock to run out governs.
- A practice lapse is a suspension pending refresher samples, not a
  lost qualification. It routes to a different queue than an expiry
  and than an unfinished sample set, and collapsing them sends people
  through weeks of work they did not need.
- A clock landing exactly on its interval has not exceeded it. Days
  are whole numbers here so the boundary is settled by the calendar
  rather than by a fraction that rounds differently on two machines.

## Workflow

1. Validate the scheme: required training modules, samples per
   combination, a declared pull-off minimum for every combination with
   none listed twice, the vision-check validity, the recertification
   interval and a notice period shorter than it, and the practice
   currency period.
2. Validate the operator record: identifier, training modules, each
   sample with a combination, a measured force and a boolean visual
   result, the certification and vision-check dates, and the last
   crimp date, which may be genuinely absent.
3. List the outstanding training modules, comparing case-insensitively
   so a record typed differently is not read as a gap.
4. Grade each sample against the declared minimum for its own
   combination, refusing a combination nobody declared a minimum for,
   and treat an exact landing on the minimum as a pass.
5. Count the passing samples per combination, mark a combination
   sufficient only when it has enough of them and none failed, and
   collect the gaps.
6. Compute the three clocks in whole days, refusing a reference date
   in the future, and treat an absent last crimp as not current rather
   than as current.
7. Decide in order: unfinished qualification, then expiry, then vision
   check, then practice lapse, then certified — and attach a due-soon
   finding when the notice period has started.

## Pitfalls

- Totalling the qualification samples across combinations. The total
  looks healthy while the combination in front of the operator has
  never been demonstrated.
- Passing a sample set on a pass rate. The set is the demonstration,
  so a failed member means it was not made.
- Reading a strong pull result as covering a failed visual. They
  examine different failure modes on the same barrel.
- Treating a practice lapse as an expiry. The operator needs refresher
  samples, not a full requalification, and the wrong route costs weeks
  of unavailable bench time.
- Forgetting the vision check because the certification is in date.
  It is a shorter clock on purpose and it runs out first.
- Reading an absent last-crimp date as recent. Nothing was recorded,
  so nothing is known, and an operator with no logged practice is not
  current.

## Behavior contract (gate 3)

Scheme and operator validation, training completeness, per-combination
sample grading with the exact-minimum boundary and the visual override,
per-combination coverage, the three independent clocks with their
exact-interval boundaries, the disposition precedence and the bench
roll-up are exercised by the gate 3 contract test:
scripts/test_q7026_operator_certification.py against
scripts/q7026_operator_certification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7026_operator_certification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
