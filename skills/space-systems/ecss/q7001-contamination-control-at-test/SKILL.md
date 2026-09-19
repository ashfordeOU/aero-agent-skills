---
name: q7001-contamination-control-at-test
description: "Maintain the cleanliness a test article arrived with across an environmental campaign, phase by phase. Use when thermal-vacuum, vibration, acoustic, handling and storage phases each expose the hardware for known hours in a known environment and the contamination budget has to hold to the end. Accumulates particulate fallout from the cleanroom class and the exposure hours, adds molecular deposition driven by chamber loading and the shroud temperature difference, credits a covered, bagged or purged phase only for the protection it really gives, compares each phase against its own allocation and the campaign against its total, and names the first phase where a re-clean is owed. Trigger: ecss, q-st-70-01, test-campaign-contamination-budget, cleanroom-particle-fallout-rate, thermal-vacuum-molecular-deposition, purge-protection-credit, test-phase-cleanliness-allocation, campaign-reclean-point."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-control, q7001-contamination-control-at-test, test-campaign-contamination-budget, cleanroom-particle-fallout-rate, thermal-vacuum-molecular-deposition, purge-protection-credit, test-phase-cleanliness-allocation, campaign-reclean-point]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Contamination Control — Cleanliness During Test (space-systems/ecss/q7001-contamination-control-at-test)

Use when the task is holding a cleanliness level through an environmental test
campaign under ECSS-Q-ST-70-01 — the article is clean when it arrives at the
first test and has to still be clean when it leaves the last. This leaf budgets
the campaign; the launch-site leaf picks the article up afterwards.

## Domain quick reference

- Contamination at test is bought by the hour, not by the event. A short
  vibration run in a poor environment costs less than a long soak in a good
  one, so the budget is driven by exposure time multiplied by the fallout rate
  of the environment the article is standing in.
- Protection is a transmission factor, never a seal. A cover, a bag or a purged
  enclosure cuts what reaches the hardware by a known fraction, and treating
  any of them as zero pickup is how a long bagged storage phase disappears from
  a budget it actually dominated.
- Thermal vacuum is the phase that deposits molecules. The chamber and its
  fixtures outgas, and the article collects what the shroud-to-article
  temperature difference drives onto it; a shroud at article temperature drives
  nothing. Vibration and acoustic phases add particles, not films, so a single
  combined number hides which control would have helped.
- The two budgets are independent. Particulate obscuration and molecular
  loading answer to different sensitivities, and holding one while breaking the
  other is not a pass.
- An allocation exists per phase as well as for the campaign. A phase that eats
  its own allocation is the point at which re-cleaning is cheaper than carrying
  the contamination forward, whether or not the campaign total still closes.
- An article rarely arrives pristine. The state it came in with is the starting
  balance of the campaign, and a budget computed from zero overstates the
  margin available by exactly that amount.

## Workflow

1. Validate each phase: a known kind, a known cleanroom class, non-negative
   exposure hours, a known protection state, and — only for a vacuum phase —
   the shroud temperature difference and chamber loading.
2. Compute the particulate addition of each phase from the fallout rate, the
   hours and the protection transmission.
3. Compute the molecular addition of the vacuum phases from the deposition
   driver, the hours, the chamber loading, the shroud difference and the same
   protection transmission; every other kind adds zero.
4. Accumulate both quantities in phase order, refusing a duplicated phase name
   so the same exposure cannot be counted twice.
5. Add the article's arrival state as the starting balance of each running
   total.
6. Compare each phase against its own allocation and the campaign totals
   against theirs, testing the boundary through a named tolerance instead of a
   bare inequality.
7. Report the totals, the remaining margins, the dominant phase and the first
   phase at which a re-clean is owed.

## Pitfalls

- Counting a bagged phase as free. The bag transmits a small fraction, and over
  three hundred hours a small fraction of a poor environment is a real number.
- Adding molecular deposition to a vibration phase because the article was
  exposed. Films come from a vacuum environment with a driving temperature
  difference; in ambient air the phase adds particles.
- Budgeting the campaign only at the end. The campaign total can close while a
  single phase has already put the article below its level, and the re-clean
  point is that phase, not the last one.
- Starting the budget at zero for an article that arrived with a history. The
  arrival state is a balance, and ignoring it inflates every margin downstream.
- Merging the two budgets into one figure of merit. An optic cares about the
  film and a mechanism cares about the particles; a combined number cannot fail
  the right one.
- Comparing a float sum to an allocation with a strict inequality. A phase
  landing exactly on its allocation has not breached it, and the tolerance says
  so explicitly.

## Behavior contract (gate 3)

The environment and protection tables, phase validation, per-phase particulate
and molecular contributions, campaign accumulation, the starting balance, the
allocation comparisons and the re-clean point are exercised by the gate 3
contract test: scripts/test_q7001_contamination_control_at_test.py against
scripts/q7001_contamination_control_at_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_contamination_control_at_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
