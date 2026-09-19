---
name: q7001-particulate-level-selection
description: "Allocate the particulate cleanliness level a hardware item is held to, given its contamination sensitivity band and the obscuration its function can still absorb, per the ECSS-Q-ST-70-01C framework. Use when items have already been banded and each now needs a level written into its requirement, with the fallout of the environment it sits in taken into account: projects the accumulation over the remaining exposure, prices the obscuration each candidate level implies at delivery, applies the margin, and keeps the coarsest candidate inside the budget, the band ceiling and the verification floor. Trigger: ecss, q-st-70-01-cleanliness-contamination-scope, particulate-level-allocation, sensitivity-band-level-ceiling, end-of-exposure-obscuration-budget, fallout-accumulation-projection, verifiable-level-floor, coarsest-compliant-level."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-scope, q7001-particulate-level-selection, particulate-level-allocation, sensitivity-band-level-ceiling, end-of-exposure-obscuration-budget, fallout-accumulation-projection, verifiable-level-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness and Contamination Control — Particulate Level Selection (space-systems/ecss/q7001-particulate-level-selection)

Use when the task is turning an ECSS-Q-ST-70-01C sensitivity band into
the particulate cleanliness level that actually goes into a hardware
requirement — the level the item is delivered to, chosen so that what
the environment adds afterwards still leaves the function inside its
obscuration budget.

## Domain quick reference

- The level is chosen against the end of the exposure, not against
  delivery. What the function has to survive is the obscuration the
  level itself implies plus everything the environment deposits between
  delivery and the moment the performance matters.
- Fallout accumulation is independent of the level delivered. If the
  projected accumulation alone eats the budget, no delivered level can
  recover it: the answer is a shorter exposure, a better environment or
  a cover, and reporting that is more useful than selecting the finest
  level on the ladder.
- The coarsest compliant level is the right answer. A finer level costs
  facility time, handling restriction and verification effort, and
  every one of those is spent for nothing once the budget is already
  met. Selecting the finest available is not conservatism, it is an
  uncosted requirement.
- Two ladder constraints sit outside the arithmetic. The sensitivity
  band sets a ceiling no budget calculation may exceed, and the
  programme's verification capability sets a floor: a level nobody can
  measure cannot be required, however comfortable it looks on paper.
- Which of the three constraints bound the choice is part of the
  answer. A selection bound by the ceiling behaves differently under a
  changed exposure than one bound by the budget, and a reader who is
  not told which one binds cannot see that.
- The obscuration a level implies comes from the incremental population
  in each size band, because counts are cumulative: the band population
  is the difference between adjacent channel allowances, projected
  through the area of a representative particle.

## Workflow

1. Validate the sensitivity band, the obscuration budget, the fallout
   rate, the exposure and the margin factor; a margin below unity
   removes margin instead of adding it and is an input error.
2. Project the fallout accumulation over the exposure that remains, and
   test it against the budget on its own before any level is priced.
3. Build the candidate ladder — the programme's when declared, the
   fall-back otherwise — sorted and free of repeats.
4. Price every candidate: the obscuration the level implies at
   delivery, plus the accumulation, times the margin factor, compared
   with the budget and absorbing an exact equality with a named
   tolerance.
5. Apply the band ceiling and the verification floor to the candidates
   that fit the budget, and refuse a floor declared coarser than the
   ceiling rather than silently emptying the set.
6. Select the coarsest admissible candidate, name the binding
   constraint, and when nothing is admissible say which of the three
   reasons emptied the set.

## Pitfalls

- Selecting against the delivered condition only. A level that meets
  the budget on the day of delivery can be far outside it after weeks
  of storage in the same room.
- Answering a fallout problem with a finer level. Accumulation does not
  care what the item was delivered at, so tightening the level spends
  effort without moving the end-of-exposure number.
- Taking the finest level on the ladder to be safe. That is a cost and
  a verification burden nobody allocated, and it usually forces
  facility upgrades that the budget never needed.
- Requiring a level the programme cannot verify. A requirement with no
  measurement behind it is closed out on assertion, which is worse than
  a coarser level that is actually demonstrated.
- Reporting the selected level without the constraint that bound it.
  Budget-bound and ceiling-bound selections respond differently to a
  changed exposure, and the difference is invisible in the number
  alone.
- Building the implied obscuration from cumulative counts. Every band
  below the size in question would be counted twice; the population of
  a band is a difference between adjacent allowances.

## Behavior contract (gate 3)

The band and ladder validation, ceiling lookup, fallout projection,
per-candidate obscuration pricing with margin, budget comparison at the
bound, ceiling and verification-floor filtering, coarsest-admissible
selection with the binding constraint named and the empty-set findings
are exercised by the gate 3 contract test:
scripts/test_q7001_particulate_level_selection.py against
scripts/q7001_particulate_level_selection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_particulate_level_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
