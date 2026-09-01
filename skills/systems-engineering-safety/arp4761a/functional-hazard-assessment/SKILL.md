---
name: functional-hazard-assessment
description: "Identify and rate the failure conditions of a functional hazard assessment (FHA) per ARP4761A: derive the A-FHA and S-FHA failure conditions from each aircraft or system function, rate severity into the categories catastrophic, hazardous, major, minor, and no safety effect, map each severity to its quantitative probability target (extremely improbable below 1e-9/flight-hour, extremely remote below 1e-7, remote below 1e-5, probable below 1e-3), and populate the FHA worksheet rows with phase, effects, and the safety objective that feeds the PSSA and SSA. Use when the safety assessment starts with functional hazard assessment or an FHA worksheet must be produced. Trigger: functional hazard assessment, failure condition, severity category, probability target, FHA worksheet, A-FHA, S-FHA."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [functional-hazard-assessment, failure-condition, severity-classification, probability-targets, fha-worksheet]
  version: 0.1.0
  author: AeroSkills
---

# ARP4761A Functional Hazard Assessment (systems-engineering-safety/arp4761a/functional-hazard-assessment)

Use when the task is the functional hazard assessment (FHA) per
ARP4761A: identifying failure conditions, rating their severity,
mapping probability targets, and populating the FHA worksheet that
opens the safety assessment process.

## Domain quick reference

The FHA is the first step of the safety assessment process. It is
performed for the aircraft (A-FHA) and then for each system (S-FHA)
that contributes to the aircraft functions. A failure
condition is an effect on the aircraft and its occupants, direct or
consequential, caused by one or more failures or errors.

Severity categories with the commonly applied quantitative probability
targets per flight hour (worked numbers, verified by running
scripts/test_functional_hazard_assessment.py):

| Severity | Assurance | Probability target per flight hour | Band |
|---|---|---|---|
| Catastrophic | A | p < 1e-9 | extremely improbable |
| Hazardous | B | p < 1e-7 | extremely remote |
| Major | C | p < 1e-5 | remote |
| Minor | D | p < 1e-3 | probable |
| No safety effect | E | none | no quantitative target |

Severity drives development assurance (A = Catastrophic
through E = No safety effect); the full assurance chain is covered by
the safety-assessment sub-skill. The targets here are the common-practice
bands consistent with AC 25.1309-1A terminology; confirm the approved
program targets for the certification basis.

Worked anchor examples (all verified by the contract test):

- Failure condition "Loss of all thrust on takeoff": the effect text
  matches the keyword "loss of all", so it is rated Catastrophic; the
  probability target is p < 1e-9 per flight hour. An assessed
  probability of 5e-10 meets the target (5e-10 < 1e-9).
- Failure condition "Loss of electrical power" rated Hazardous carries
  the target p < 1e-7 per flight hour; an assessed 2e-8 meets it.
- Reverse lookup: an assessed probability of 1e-6 sits in the "remote"
  band, and the highest severity target it meets is Major
  (1e-6 < 1e-5, but 1e-6 is not < 1e-7).
- The target comparison is strict: 1e-3 does not meet the Minor target
  (p < 1e-3, not p <= 1e-3).

FHA worksheet columns: function, failure condition, flight phase,
effect on aircraft and occupants, effect on crew, severity,
probability target, assessed probability, meets target, safety
objective, remarks. A sample row built by the logic module:

| function | failure condition | flight phase | severity | target | assessed p | meets | safety objective |
|---|---|---|---|---|---|---|---|
| Autopilot | Loss of all pitch authority | Climb | Catastrophic | p < 1e-9/FH | 5e-10 | yes | P(failure condition) < 1e-9 per flight hour |

## Workflow

1. Scope the FHA: run the A-FHA for the aircraft first, then the
   S-FHA for each system; record the scope in each worksheet.
2. Enumerate the functions from the system description, including
   normal, degraded, and loss states of each function.
3. Identify the failure conditions per function: loss of function,
   malfunction, erroneous output, and combinations of failures; state
   each as an effect on the aircraft and occupants.
4. Rate each failure condition severity from its effects using the
   five categories, and record the flight phase the effect applies to.
5. Map the probability target from the severity, and record the
   assessed probability when one is available.
6. Populate the worksheet rows; flag any row where the assessed
   probability misses the target for follow-up.
7. Hand the completed worksheet to the PSSA once the architecture is
   proposed, and later to the SSA for closure.

## Pitfalls

- Confusing the FHA with the whole safety assessment process: the FHA
  identifies, rates, and targets failure conditions; it does not run
  the PSSA/SSA or build the fault trees. Those belong to the
  safety-assessment sub-skill.
- Confusing the FHA with common-cause analysis: CCA looks for a single
  event that defeats independence across functions and zones; the FHA
  rows are per-function failure conditions. Do not merge common-mode
  checks into FHA worksheet rows.
- Confusing the FHA with zonal safety analysis: the ZSA assesses
  physical zone contents, separation, and containment; the FHA assesses
  functional effects regardless of installation. Do not rate zonal
  hazards as failure conditions.
- Rating severity from failure rate instead of from effects: a very
  rare failure can still be catastrophic. Severity comes from the
  effect on the aircraft and occupants, never from how often the
  failure is expected.
- Missing flight-phase dependence: the same failure condition can rate
  differently in different flight phases; record the phase on every
  row.
- Reversing the direction of the mapping: the probability target is
  derived from the severity, not the severity from the target. Rate
  severity first, then look up the target.
- Dropping "no safety effect" rows: they still get worksheet entries;
  they simply carry no quantitative probability target.
- Treating the target as met at the boundary: every quantitative
  target is strict (p < 1e-9, not p <= 1e-9).

## Behavior contract (gate 3)

The severity ordering, probability target lookup, strict target
comparison, reverse lookups, and worksheet row builder are exercised
by the gate 3 contract test: scripts/test_functional_hazard_assessment.py
against scripts/functional_hazard_assessment_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_functional_hazard_assessment.py

## Compliance

- Standards referenced, not reproduced: ARP4761A / ARP4754A text is
  proprietary (SAE); summary-only per standards-map.yaml and brief 06.
- Revision note: ARP4754B (2023) supersedes ARP4754A; this skill keys
  to ARP4754A as the certification-baseline revision (FAA AC 20-174
  cites A); see standards-map.yaml arp4754a.revision_decision.
- compliance: STANDARDS-REF, gated: false.
