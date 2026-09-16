---
name: e2008-coating-adherence-test-purpose
description: "Use when scoping or reviewing a coverglass coating adherence campaign. Evaluate whether an adherence test on the conductive coating of a solar cell assembly coverglass serves the purpose ECSS-E-ST-20-08C clause 6.4.3.9.1 gives it, showing the coating stays durable in service: map each declared service stressor onto the durability objective the check demonstrates, accumulate those stressors into one service demand, decide whether the coating and that demand justify a check at all, then confirm the planned check follows the environments that loosen a coating and reads enough subgroup samples to speak for the lot. Trigger: ecss, e-st-20-08c, clause-6-4-3-9-1, coverglass-conductive-coating-adherence, coating-durability-objective, charge-bleed-path-continuity, post-environmental-adherence-check, coating-service-demand-index."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-coating-adherence-test-purpose, coverglass-conductive-coating-adherence, coating-durability-objective, charge-bleed-path-continuity, post-environmental-adherence-check, coating-service-demand-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Coating Adherence Test Purpose (space-systems/ecss/e2008-coating-adherence-test-purpose)

Use when the task is to state and defend why an adherence test is applied to
the conductive coating carried on a coverglass under ECSS-E-ST-20-08C clause
6.4.3.9.1 — what the check is meant to demonstrate, whether the hardware and
its service life justify it, and whether the planned check actually reports the
durability the clause asks about.

## Domain quick reference

- The coating is a function, not a finish. It is the bleed path that keeps the
  front surface of the array from charging differentially, and it is a film a
  few tens of nanometres thick. Losing its adhesion loses the path, so the
  purpose of the check is durability of that path rather than cosmetic
  appearance of the glass.
- The purpose is set by what service does to the film. Thermal cycling shears
  it against a substrate it does not match, solar ultraviolet and atomic oxygen
  attack the interface, handling and cleaning abrade it, launch loads shake it,
  and damp storage creeps under it. Each declared stressor turns into a
  distinct objective the check demonstrates, and every coated coverglass shares
  the retention of the conductive path itself.
- Stressors at different depths are only comparable once scaled. A severity
  expressed as the share of its qualification reference that the mission
  actually spends lets unlike environments be accumulated into one service
  demand the check has to answer.
- Justification is a joint condition. A coverglass with no conductive coating
  has no bleed path to lose however harsh its service life is, and a genuinely
  benign service life does not earn the check however well coated the glass is.
- Order is what makes the check evidence. A check read on pristine as-coated
  glass reports the coating process, not durability; it has to follow the
  environments that work the coating-to-glass interface.
- A subgroup is a sampling device. Too few samples read leaves the result
  unable to speak for the lot even when the check itself is well placed.
- A stated purpose is not a served purpose. A coating that earns the check but
  has none planned is a distinct outcome from one whose planned check is placed
  too early or reads too little, and the two carry different actions.

## Workflow

1. Validate the declared policy first: per-stressor weights, the demand trigger
   and the subgroup sample floor. An unrecognised stressor in the weights is
   refused rather than ignored, so a typo cannot silently drop a demand.
2. Validate the service stressor inventory: recognised names, no duplicates,
   and a severity expressed as a share of its qualification reference.
3. Map each stressor to the durability objective the check demonstrates against
   it, and append the shared conductive-path retention objective when the
   coverglass is coated at all.
4. Accumulate the weighted severities into one service demand on the coating.
5. Decide whether the check is justified: a conductive coating present and a
   demand at or above the trigger. A demand landing exactly on the trigger
   earns the check; the comparison tolerance absorbs representation error and
   the trigger does not move.
6. When it is justified, grade the planned check — does it follow every
   declared environment that loosens a coating, and does it read enough
   subgroup samples — and report each shortfall with the value it owed.
7. Close on one verdict: not required, justified but not planned, planned but
   under scope, or serving its purpose, with the objectives attached to it.

## Pitfalls

- Treating the check as a coating-process test. Adherence measured on
  as-coated glass says the deposition worked; the clause asks whether the film
  is still attached after the service life, and only an ordered check answers
  that.
- Reading only the harshest stressor. A long, mild ground and storage history
  can demand more of an interface than one short severe environment, and the
  accumulation is what the film responds to.
- Adding raw severities across unlike environments. Cycles, ultraviolet dose
  and handling events are not interchangeable until each is scaled against its
  own reference.
- Standing the check down because the glass looks robust. The decision follows
  the declared inventory, so an undeclared coating or an undeclared environment
  silently removes an objective the subgroup was supposed to demonstrate.
- Calling a justified check satisfied because some adherence data exists. Data
  taken before the loosening environments, or from too few samples, leaves the
  purpose unserved, and that is a finding rather than a pass.
- Forgetting the electrostatic objective. The other stressors ask whether the
  film survived; charging asks whether the path it provides is still
  continuous, and that objective survives even a visually perfect coating.

## Behavior contract (gate 3)

The policy validation, stressor inventory checks, objective mapping, service
demand accumulation, justification decision, planned-check grading and the
purpose verdict are exercised by the gate 3 contract test:
scripts/test_e2008_coating_adherence_test_purpose.py against
scripts/e2008_coating_adherence_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coating_adherence_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
