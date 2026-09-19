---
name: q7001-contamination-nonconformance
description: "Determine the disposition a contamination nonconformance needs under ECSS-Q-ST-70-01C. Use when a measured molecular or particulate level has overrun the limit for a surface, when the performance the deposit costs has to be sized before a board sits, or when a re-clean is being proposed as the remedy: compute the exceedance against the limit, turn it into an optical or thermal performance penalty through the declared surface sensitivity, decide between use-as-is under concession, re-cleaning with re-verification, and escalation, count the re-clean cycles the item has already spent, and name the re-verification method the disposition owes. Trigger: ecss, q-st-70-01c-cleanliness-scope, contamination-nonconformance-disposition, cleanliness-limit-exceedance, recleaning-cycle-budget, contamination-performance-penalty, cleanliness-re-verification-method, contamination-escalation-threshold."
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
  tags: [ecss, q-st-70-01c-cleanliness-scope, q7001-contamination-nonconformance, contamination-nonconformance-disposition, cleanliness-limit-exceedance, recleaning-cycle-budget, contamination-performance-penalty, cleanliness-re-verification-method, contamination-escalation-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Contamination Nonconformance Disposition (space-systems/ecss/q7001-contamination-nonconformance)

Use when the task is the contamination nonconformance route of
ECSS-Q-ST-70-01C — a surface has been measured over its cleanliness
limit, and the programme has to say what that costs, what is done
about it, and how the remedy is shown to have worked.

## Domain quick reference

- An exceedance is an input, not a verdict. The number that decides
  the case is what the deposit costs the function: a transmittance
  loss on an optical path, an absorptance rise on a radiator, a
  contact resistance on a mating surface.
- The bridge from level to penalty is a declared surface sensitivity.
  Without it the board is comparing an areal mass against a
  requirement written in performance, which is not a comparison at
  all.
- Re-cleaning is not free and not unlimited. Every cycle works the
  surface, and coatings, seals and optical finishes carry a cycle
  budget; an item at the end of that budget has no re-clean option
  left however clean the process could get it.
- Some cases cannot be re-cleaned out of. If the penalty computed at
  the limit itself already exceeds what the function can absorb, then
  cleaning back to the limit still leaves the item unacceptable, and
  the case is a requirement or a design matter rather than a cleaning
  one.
- A re-clean that is not re-verified is not a disposition. The
  measurement after the clean is the only statement of what level the
  item actually reached, and the method has to suit the contaminant
  and the criticality.
- Molecular and particulate need different re-verification. A rinse
  and gravimetric residue reading says nothing about particle
  obscuration, and a tape lift says nothing about a molecular film.
- Use-as-is is legitimate but narrow. It holds while the exceedance is
  small and the penalty still fits inside the performance allowance,
  and it always leaves a concession and an as-built record behind it.

## Workflow

1. Take the item, the contaminant ledger, the measured level, the
   limit, the surface sensitivity and the performance allowance, and
   reject a case that cannot name them rather than defaulting them.
2. Compute the exceedance: the absolute overrun and the ratio to the
   limit, treating a level exactly on the limit as compliant rather
   than as a marginal failure.
3. Convert the measured level into a performance penalty through the
   declared sensitivity, and compute the same penalty at the limit so
   the recoverable part of the loss is visible.
4. Categorize the severity from the exceedance ratio and whether the
   penalty fits inside the allowance.
5. Check the re-clean budget: cycles already spent against the cycles
   the substrate and finish permit.
6. Choose the disposition in order -- no action where there is no
   exceedance and no penalty; escalation where cleaning to the limit
   cannot recover the function; use-as-is under concession where the
   exceedance is small and the penalty fits; re-clean with
   re-verification while cycles remain; escalation otherwise.
7. Name the re-verification method the contaminant and the criticality
   demand, and list the records the route owes.

## Pitfalls

- Disposing on the exceedance ratio alone. A small overrun on a
  sensitive optical surface can cost more than a large one on
  structure, because the sensitivity, not the ratio, sets the penalty.
- Proposing a re-clean without checking the cycle budget. The cleaning
  that removes the deposit can also remove the coating, and the budget
  exists because the surface only tolerates so much.
- Re-cleaning a case whose penalty at the limit already exceeds the
  allowance. The best achievable outcome is still unacceptable, so the
  cycle is spent for nothing and the real decision is deferred.
- Re-verifying with a method that cannot see the contaminant. A
  particle count after a molecular rinse gives a clean answer to a
  question nobody asked.
- Closing a use-as-is without a concession and an as-built record. The
  item now differs from its cleanliness requirement, and the only
  place that difference will ever be recorded is the concession.
- Comparing a measured level against its limit by bare arithmetic. A
  reading landing exactly on the limit can miss it by a few units in
  the last place, so the comparison absorbs that representation error
  rather than raising a nonconformance that does not exist.

## Behavior contract (gate 3)

Exceedance arithmetic, the sensitivity-to-penalty conversion, severity
categorization, the re-clean cycle budget, disposition selection and
the re-verification method set are exercised by the gate 3 contract
test: scripts/test_q7001_contamination_nonconformance.py against
scripts/q7001_contamination_nonconformance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_contamination_nonconformance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
