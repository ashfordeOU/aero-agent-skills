---
name: q7028-repair-limits
description: "Determine whether a printed circuit board assembly stays inside the repair ceilings of ECSS-Q-ST-70-28C once a further repair is added. Read the count and density allowance the assurance level carries, combine the repairs already on the board with the ones proposed, refuse a reused site identity, measure the in-plane separation of every pair against the minimum that pair takes — longer on one face, shorter across the laminate — count repairs per conductor, and return the disposition with the closest pair, the governing limit and whether the proposal is what broke it. Use when authorising another repair or auditing a heavily reworked board. Trigger: ecss, q-st-70-28c, repairs-per-board-allowance, board-repair-proximity-rule, board-repair-density-limit, repairs-per-conductor-limit, repair-site-separation."
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
  tags: [ecss, q-st-70-28c-pcb-repair-and-modification, q-st-70-28c, q7028-repair-limits, repairs-per-board-allowance, board-repair-proximity-rule, board-repair-density-limit, repairs-per-conductor-limit, repair-site-separation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PCB Repair — Repair Limits (space-systems/ecss/q7028-repair-limits)

Use when the task is the limits clause of ECSS-Q-ST-70-28C: how much repair
one printed circuit board assembly is allowed to carry, how densely the sites
may sit, how many repairs one conductor may take, and how close two repair
sites may be before the material between them stops being undisturbed.

## Domain quick reference

- The limits are on the board, not on the individual repair. Every repair can
  be perfectly executed and the board still be refused, because what the
  ceiling protects is the amount of the assembly whose qualification now rests
  on rework rather than on the original process.
- A count and a density are different limits and both are needed. The count
  stops a board accumulating repairs indefinitely; the density stops a small
  board carrying the population a large one was allowed.
- Proximity is a thermal and mechanical rule. Two repairs close together mean
  the second reflow ran through material the first had already cycled, and the
  laminate between them has seen both. The separation is what keeps each
  repair sitting in undisturbed material.
- The minimum separation depends on which faces the sites are on. Two sites on
  one face interact across the surface and take the longer minimum; two on
  opposite faces interact only through the thickness and may sit closer in
  plan. Applying one figure to both is either needlessly strict or unsafe.
- A conductor takes one repair. A second repair on the same run leaves a
  conductor that is mostly joint, and the electrical and mechanical behaviour
  of the run is no longer the behaviour that was qualified.
- A proposal is assessed against the board as it will be, not as it is. The
  useful answer names whether the proposal is what pushes the board over, so
  the alternative — relocating the jumper, routing on the other face — can be
  evaluated instead of the repair being refused outright.
- Two proposals that each pass alone can fail together. Pairwise separation is
  checked across the whole combined population, existing and proposed, rather
  than proposal against existing only.

## Workflow

1. Read the count and density allowances for the board's assurance level.
2. Normalise the existing and proposed sites, validating the side and the
   coordinates, and refuse a proposal that reuses an existing site identity.
3. Count the whole combined population against the per-board allowance.
4. Compute the density over the board area and compare it against the
   per-area allowance.
5. Group the sites by conductor and report any conductor over its allowance.
6. Measure the separation of every pair and compare it with the minimum that
   pair takes, treating a pair exactly on the minimum as acceptable.
7. Report the closest pair and the governing limit as the highest utilisation
   across the count and density allowances.
8. Say whether the proposal is implicated in any breach, and return the
   disposition with every finding.

## Pitfalls

- Checking the count and calling the board clear. A small board at four
  repairs can be well past its density while comfortably inside its count.
- Applying one separation figure to every pair. Sites on opposite faces are
  refused for a surface interaction they do not have, and the crowding that
  matters goes unexamined when the figure is set from the cross-laminate case.
- Checking each proposal only against the existing sites. Two proposals four
  millimetres apart both clear the old population and crowd each other.
- Counting repairs per board and not per conductor. One run can absorb the
  whole allowance without the board count looking remarkable.
- Reporting a refusal without saying which limit governed or how close the
  nearest pair was. Moving a jumper five millimetres is often the whole fix,
  and the disposition has to make that visible.
- Reusing a site identity when a repair is reworked. The population then
  counts one site where there were two, and the history of the first is lost.

## Behavior contract (gate 3)

The count and density allowances by assurance level, site normalisation and
duplicate-identity refusal, pairwise separation against the same-face and
cross-laminate minima, per-conductor counting, closest-pair reporting,
governing-limit selection and the proposal-implicated flag are exercised by
the gate 3 contract test: scripts/test_q7028_repair_limits.py against
scripts/q7028_repair_limits_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7028_repair_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
