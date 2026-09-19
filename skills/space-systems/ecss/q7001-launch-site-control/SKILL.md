---
name: q7001-launch-site-control
description: "Plan the cleanliness controls that carry a spacecraft through a launch campaign without spending the budget it arrived with. Use when arrival, unpacking, integration, propellant loading, encapsulation, transfer and pad stay each have a duration, an environment and a protection state, and the fairing has to be verified before it closes. Accumulates particulate and molecular pickup stage by stage, credits a container, cover or purge only for what it blocks, refuses a loading stage run without vapour protection, refuses a purge credit with no purge connected, and reports the budget left at lift-off with the stage that consumed most of it. Trigger: ecss, q-st-70-01, launch-campaign-cleanliness, fairing-cleanliness-verification, propellant-loading-vapour-protection, launch-site-purge-credit, transport-container-protection, pad-stay-contamination-budget."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-control, q7001-launch-site-control, launch-campaign-cleanliness, fairing-cleanliness-verification, propellant-loading-vapour-protection, launch-site-purge-credit, transport-container-protection, pad-stay-contamination-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Contamination Control — Launch Site (space-systems/ecss/q7001-launch-site-control)

Use when the task is preserving cleanliness at the launch site under
ECSS-Q-ST-70-01 — from the container arriving at the processing hall to the
vehicle standing on the pad. This leaf covers the ground campaign; the in-orbit
leaf takes over after separation.

## Domain quick reference

- The launch campaign is where the cleanliness budget is most often spent and
  least often measured. The article is at its most exposed, the environments
  are the worst it has seen since manufacture, and the stages are long.
- Encapsulation is a one-way door. Once the fairing closes, nothing inside can
  be inspected, sampled or re-cleaned, so a verification before it closes is
  the last opportunity that exists; closing on an unverified article is not a
  risk to be tracked, it is a finding.
- Propellant loading is a molecular source, not just a hazardous operation. The
  vapour reaches surfaces the liquid never touches, and a deposit laid down at
  the pad is not removable there, so the article is protected against vapour or
  the operation is re-planned.
- A purge credit belongs to a connected purge. An encapsulated volume with the
  purge line off is a closed box slowly equalising with the hall, and claiming
  the purged transmission for it understates the pickup by nearly an order of
  magnitude.
- Protection states rank, and the ranking is the plan. A transport container
  beats a bag, a purged fairing beats an unpurged one, and a pad stay is
  survivable only because the fairing is closed and flowing.
- The article's arrival state is the campaign's opening balance. A budget that
  starts at zero at the gate credits the campaign with cleanliness the shipping
  already spent.

## Workflow

1. Validate each stage: a known activity, a known environment, a non-negative
   duration and a known protection state.
2. Validate the sequence: no activity twice, and no activity ahead of one that
   physically precedes it — an encapsulation before integration is an input
   error, not an aggressive schedule.
3. Compute the particulate pickup of each stage from the environment rate, the
   duration and the protection transmission.
4. Compute the molecular pickup the same way, adding the propellant vapour
   source during loading and reducing it where vapour protection is declared.
5. Apply the campaign rules: verified fairing before encapsulation, vapour
   protection during loading, a connected purge behind any purge credit.
6. Accumulate both totals from the arrival balance, and compare them with the
   budgets through a named tolerance so an exactly-consumed budget still
   closes.
7. Report the totals, margins, the dominant stage and every blocking finding.

## Pitfalls

- Verifying the fairing after encapsulation. The measurement has to happen
  while the surface is still reachable; afterwards the only options are opening
  it again or launching on an assumption.
- Treating propellant loading as a safety operation with no contamination
  content. The vapour deposits on everything with a view of the volume, and the
  article is usually at its most exposed at that point in the flow.
- Claiming the purged-fairing transmission for a fairing whose purge is not
  connected. The credit is the largest in the table, and it is the easiest to
  take by habit.
- Budgeting the pad stay as though the fairing were open, or the transfer as
  though it were closed. The protection state, not the environment, is what
  makes a long pad stay affordable.
- Starting the campaign budget at zero. Transport is a stage like any other,
  and the article that arrives has already spent part of the allocation.
- Reading an exactly-consumed budget as a breach. The comparison carries a
  named tolerance, because a sum of stage contributions can land on the budget
  a bit either side of it.

## Behavior contract (gate 3)

The environment and protection tables, stage and sequence validation, the
per-stage particulate and molecular contributions, the propellant-vapour
source, the fairing-verification, vapour-protection and purge-credit rules, the
campaign accumulation and the lift-off margins are exercised by the gate 3
contract test: scripts/test_q7001_launch_site_control.py against
scripts/q7001_launch_site_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7001_launch_site_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
