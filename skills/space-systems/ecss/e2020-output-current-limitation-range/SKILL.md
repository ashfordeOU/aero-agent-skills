---
name: e2020-output-current-limitation-range
description: "Verify that a current limiter holds its output inside the defined minimum and maximum protection thresholds. Use when ECSS-E-ST-20-20C clause 5.2.3.1.1 asks a limiter design to prove the limitation current never leaves that window: stack the setpoint contributors — initial setting, temperature, reference drift, ageing, total dose, sense offset — arithmetically or by root-sum-square, build the worst-case limitation range around the nominal setpoint, compare both edges with the thresholds, confirm the lower edge clears the healthy load current and the upper edge stays under the protected harness rating, and report the setpoint that recentres the band. Refuses a negative tolerance, a relative contributor at or beyond unity and an inverted threshold window. Trigger: ecss, e-st-20-20c, limiter-output-current-limitation-range, protection-threshold-window, limitation-setpoint-tolerance-stack, root-sum-square-tolerance-stack, nuisance-limitation-headroom, recentred-limitation-setpoint."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-output-current-limitation-range, protection-threshold-window, limitation-setpoint-tolerance-stack, root-sum-square-tolerance-stack, nuisance-limitation-headroom, recentred-limitation-setpoint]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Output Current Limitation Range (space-systems/ecss/e2020-output-current-limitation-range)

Use when the task is the output-current-limitation check of
ECSS-E-ST-20-20C clause 5.2.3.1.1 — showing that the current a limiter
actually holds, across every contributor that moves it, stays between
the minimum and the maximum protection threshold the design declared.

## Domain quick reference

- A limiter does not hold one current. The limitation current moves with
  temperature, with the initial setting tolerance of the sense element,
  with reference drift, with ageing and with total dose, and it differs
  unit to unit. The object of this clause is therefore a RANGE, and a
  single nominal figure quoted against the thresholds answers nothing.
- The two thresholds fail in opposite directions. Below the minimum, the
  protection is too eager: a healthy load can provoke limitation and be
  denied current it was designed to draw. Above the maximum, the
  protection is too slack: the fault current the harness and the load
  carry exceeds what the design assumed.
- Contributors come in two shapes. A relative contributor scales with
  the setpoint, so moving the setpoint moves its contribution; an
  absolute one such as a sense-amplifier offset does not. Mixing them
  correctly is what makes the stack setpoint-dependent.
- Arithmetic stacking puts every contributor at its own worst case at
  the same instant and is the bounding answer. Root-sum-square assumes
  the contributors are independent and always returns a narrower band,
  so it buys margin only against an independence argument, and the
  method travels with the result.
- Two separations are not implied by the thresholds and have to be
  checked on their own. The lower edge has to clear the highest healthy
  load current, or a good load is limited; the upper edge has to stay
  under the rating of the harness being protected, or the protection
  does not protect.
- When the stacked band is wider than the threshold window, no setpoint
  satisfies the clause. That is a contributor problem — a tighter
  reference, a narrower temperature range, a trimmed initial setting —
  and moving the setpoint only chooses which threshold is broken.
- When the band does fit but sits off centre, the setpoint that puts
  equal slack on both sides is the one worth reporting: it is the
  cheapest change that buys margin at both thresholds at once.

## Workflow

1. Validate the contributor set: unique names, a known kind, tolerances
   that are not negative, relative tolerances below unity, and no
   two-sided zero entry masquerading as a contributor.
2. Express every contributor in amperes at the nominal setpoint,
   keeping the two sides separate — an asymmetric contributor such as
   ageing or dose is the usual reason the range is not centred.
3. Stack the two sides by the declared method and record which method
   was used. Refuse a downward stack that consumes the setpoint
   entirely rather than reporting a non-positive lower edge.
4. Build the range as setpoint minus the downward stack to setpoint
   plus the upward stack, and take its width.
5. Compare the lower edge with the minimum threshold and the upper edge
   with the maximum threshold, reporting both margins in amperes and the
   share of the window the stack consumes.
6. Check the two separations: the lower edge strictly above the highest
   healthy load current, and the upper edge under the harness rating.
7. Compute the setpoint that recentres the band. Return no setpoint when
   the band is wider than the window, and say so as a finding naming the
   stack and the window rather than a bare refusal.
8. Close with a verdict and, where everything passes but the stack eats
   most of the window, an advisory that the design has little room for a
   later contributor.

## Pitfalls

- Checking the nominal limitation current against the thresholds. The
  nominal is the one value guaranteed not to be the worst case; the
  clause is satisfied by the edges of the range or not at all.
- Scaling an absolute contributor with the setpoint. A sense offset in
  amperes is the same at every setpoint, and treating it as a percentage
  understates it badly at low setpoints and overstates it at high ones.
- Reaching for root-sum-square to make a failing stack pass. It is a
  claim of independence between contributors; initial setting and
  reference drift on a shared part are not independent, and the narrower
  band it reports is then not a bound at all.
- Assuming the range is symmetric. Ageing and total dose usually push
  harder one way, so the downward and upward stacks differ and the
  margin at one threshold is not the margin at the other.
- Treating the threshold check as covering the healthy load. A range
  can sit inside the window and still overlap the load current, which is
  nuisance limitation in flight, not a protection failure on paper.
- Moving the setpoint when the band is wider than the window. Every
  setpoint then breaks one threshold or the other; the fix is to tighten
  a contributor, and reporting a recentred setpoint in that case hides
  the real defect.
- Comparing an edge with a threshold by bare arithmetic. An edge is
  built from sums, products and a square root, so a case meant to sit
  exactly on a threshold can land a few units in the last place outside
  it; the comparison absorbs that representation error while the
  thresholds stay as declared.

## Behavior contract (gate 3)

The contributor validation, per-contributor ampere conversion,
arithmetic and root-sum-square stacking, range construction, threshold
comparison, healthy-load and harness separations, recentred setpoint and
overall verdict are exercised by the gate 3 contract test:
scripts/test_e2020_output_current_limitation_range.py against
scripts/e2020_output_current_limitation_range_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_output_current_limitation_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
