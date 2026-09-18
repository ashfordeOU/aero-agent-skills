---
name: e2020-onboard-failure-removal-response
description: "Assess how a distribution unit behaves when onboard software answers a dissipatively failed limiter switch by reducing the load or commanding that switch off, under clause 5.2.14.2.1 of ECSS-E-ST-20-20C. Use when the survival argument for the surrounding parts rests on software rather than on hardware removing the fault. Raise each part through the detection and reaction latency on a first order thermal response, test the temperature reached against its derated rating, test what the action leaves running against the same rating, and report an off command the failed switch cannot answer. Trigger: ecss, e-st-20-20c, onboard-software-failure-removal, dissipative-failure-load-reduction, dissipative-failure-switch-off-command, onboard-response-latency-heating, failed-switch-off-command-effectiveness."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-onboard-failure-removal-response, onboard-software-failure-removal, dissipative-failure-load-reduction, dissipative-failure-switch-off-command, onboard-response-latency-heating, failed-switch-off-command-effectiveness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Onboard Failure Removal Response (space-systems/ecss/e2020-onboard-failure-removal-response)

Use when the task is clause 5.2.14.2.1 of ECSS-E-ST-20-20C: onboard software
answers a dissipatively failed current limiter switch, either by reducing the
load that switch carries or by commanding it off, and the behaviour that
follows has to be established. This leaf grades both halves of that argument
— what happens while the software is still deciding, and what it leaves
running afterwards.

## Domain quick reference

- Software is a slow protection and the clause is about the delay. Detection,
  confirmation, voting and command take seconds to minutes, and the failed
  switch holds its full dissipation for every one of them, so the number that
  matters is the temperature a part has reached when the command finally
  lands.
- A latency figure means nothing on its own. It is only assessable against
  the time the earliest part would have reached its own limit, so that time
  is computed per part and the smallest of them is the budget the software
  has to fit inside.
- The rise is first order, not instantaneous. The coupling sets where a part
  ends up and the product of that coupling with its heat capacity sets how
  fast it gets there, which is why a well coupled part with little mass can
  be the casualty while a hotter-running one with a long time constant is
  never in danger.
- Reducing the load is not removing the failure. The switch is still in
  limitation, still dropping the bus and still dissipating at the reduced
  current, for the rest of the mission; that residual steady state has to
  clear the same derated limits as the peak.
- Commanding the switch off assumes the switch answers. A device that has
  failed dissipatively is a device behaving incorrectly, and an off command
  it cannot execute turns the whole declared response back into no response.
  That degeneration is reported by name rather than assumed away.
- The bound is the derated limit for both halves. The transient and the
  residual are compared against the rated maximum less the margin the parts
  programme withholds, so a peak that clears the catalogue number is not yet
  an argument.
- A part can pass one half and fail the other. A fast response with a shallow
  reduction survives the latency and cooks afterwards; a deep reduction
  applied too late loses the part before it arrives. Both lists are reported
  separately.

## Workflow

1. Validate the case: a named switch, a positive drop and failed current, a
   physically possible reference temperature, an action from the declared
   vocabulary, and parts carrying a coupling, a heat capacity and a rating.
2. Enforce the fields the action implies: a reduced current that actually
   reduces for a load reduction, an effectiveness flag for an off command, a
   latency for either, and none of them when no action is declared.
3. Compute the dissipation the switch holds before the response.
4. Derive the effective action: an off command the switch cannot answer, or
   no declared action at all, both leave the failure running untouched.
5. For each part, raise it on its own time constant to the moment the command
   lands and compare against its derated limit; compute the time at which it
   would have reached that limit and keep the earliest as the latency budget.
6. For each part, settle it on the dissipation the action leaves running and
   compare against the same limit.
7. Return both casualty lists, both margins per part, the latency budget and
   the verdict; the response is adequate only when an effective action exists
   and every part clears both halves.

## Pitfalls

- Grading only the end state. A response that leaves nothing running still
  fails the clause when the part it was protecting was already over its limit
  before the command arrived.
- Grading only the peak. A load reduction ends in a steady state that lasts
  the rest of the mission, and the peak says nothing about whether that state
  is survivable.
- Taking the off command for granted. The switch under discussion has failed
  in a mode nobody designed; whether it still answers its own command is an
  input to the assessment, not a background assumption.
- Quoting a detection latency with no budget beside it. Fifteen seconds is
  fast against a part with a five minute time constant and far too slow
  against one that reaches its limit in eight.
- Using one time constant for the whole assembly. The coupling and the mass
  belong to individual parts, and the casualty is usually the one with the
  worst product of the two rather than the one running hottest.
- Comparing against the rated maximum. The derated limit is what the review
  will hold, on the transient and on the residual alike.
- Reading a load reduction as equivalent to an off command. They leave
  different dissipations behind and the report keeps them apart.

## Behavior contract (gate 3)

The case validation, action-dependent field rules, dissipation arithmetic,
thermal time constant, first order transient, time-to-limit inversion,
residual current derivation, off-command degeneration, per-part transient and
residual grading, latency budget and verdict are exercised by the gate 3
contract test: scripts/test_e2020_onboard_failure_removal_response.py against
scripts/e2020_onboard_failure_removal_response_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_onboard_failure_removal_response.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
