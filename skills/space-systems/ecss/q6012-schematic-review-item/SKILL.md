---
name: q6012-schematic-review-item
description: "Assess the schematic item tabled at an ECSS-Q-ST-60-12C clause 7.3.3 die-form MMIC design review: confirm the drawn diagram is connectively complete, that every active device sits inside the foundry scalable-model window for unit gate width, finger count and total gate periphery, and that the bias arrangement as drawn puts each device at a quiescent point the derating policy and the process both allow. Use when a schematic package reaches a MMIC design review and its device sizing, bias feed drop and decoupling have to become named findings instead of impressions. Trigger: ecss, q-st-60-12c-clause-7-3-3, mmic-schematic-review-item, gate-periphery-model-window, mmic-drain-current-density, bias-feed-voltage-drop, mmic-bias-decoupling, floating-net-finding, mmic-dissipation-density."
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
  tags: [ecss, q-st-60-12-die-mmic-scope, q6012-schematic-review-item, mmic-schematic-review-item, gate-periphery-model-window, mmic-drain-current-density, bias-feed-voltage-drop, mmic-bias-decoupling, mmic-dissipation-density]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die-Form MMIC -- Schematic Review Item (space-systems/ecss/q6012-schematic-review-item)

Use when the task is the schematic item of the design review of
ECSS-Q-ST-60-12C clause 7.3.3 -- the checkpoint at which the circuit
diagram, the sizing of the drawn devices and the bias arrangement behind
them are examined together, before the design is allowed to move on.

## Domain quick reference

- The reviewable size of an active MMIC device is not its drawing
  reference but its total gate periphery: a unit gate width repeated
  over a finger count, W = unit_gate_width_um * finger_count / 1000 in
  mm. Two devices with the same periphery but different finger splits
  behave differently thermally, so the review grades all three numbers,
  not the product alone.
- The foundry scalable model is only valid over a declared window in
  unit gate width, finger count and total periphery. A device outside
  that window is not merely unusual: the simulated performance shown at
  the same review rests on an extrapolated model, so the sizing finding
  and the simulation evidence fall together.
- The quiescent point comes from the bias feed as drawn, not from the
  intended supply. A resistive feed drops the rail by Id * R_feed, so
  the drain sits at Vdd - Id * R_feed. Reviewing against the rail value
  hides both a low-voltage compression risk and, when the feed is
  small, an over-voltage against the derated rating.
- Three bias quantities are graded, and they move independently: drain
  voltage against the rated maximum after the derating factor, drain
  current density Id / W against the process window for the intended
  operating class, and dissipation density Vds * Id / W against the
  thermal limit. A device can sit comfortably inside the current window
  and still exceed the thermal limit, because dissipation carries the
  dropped drain voltage with it.
- The diagram itself is review evidence. A terminal that appears on no
  net, a net that reaches a single connection, and a bias net with no
  decoupling element are all defects of the drawn schematic, independent
  of whether the numbers behind it are acceptable.

## Workflow

1. Validate the package: device list, net list, the foundry model window
   and the bias policy. A missing bias policy is an input error, not a
   device that passes by default.
2. For each device, form the total gate periphery from the unit gate
   width and the finger count, then grade width, finger count and
   periphery against the model window with inclusive bounds; a value
   meant to land on a bound is inside it.
3. Derive the quiescent point from the drawn feed: compute the feed drop
   and the resulting drain voltage. A feed that collapses the drain node
   is an input error and stops the grading for that device.
4. Grade the operating point three ways -- derated drain voltage,
   current density window, dissipation density limit -- and emit a named
   finding for each breach rather than a single pass or fail flag.
5. Grade the diagram: every declared device terminal on a net, every net
   with at least two connections, every bias net decoupled. Duplicate
   net names and duplicate device references are input errors.
6. Collect the sizing, bias and connectivity findings into one item
   verdict and report the worst dissipation density, which is the number
   the thermal item of the same review inherits.

## Pitfalls

- Grading the periphery alone. A 16-finger and a 4-finger device of the
  same total periphery sit at different points of the model window and
  spread heat differently; the finger count is graded in its own right.
- Reading the drain voltage off the supply rail. The drawn feed
  resistance sets the actual drain voltage, and reviewing the rail
  instead is how an over-derated device passes a schematic review.
- Treating a comfortable current density as covering the thermal case.
  Dissipation density carries the drain voltage as well as the current,
  so it can breach while the current density is mid-window.
- Letting a device outside the model window pass because its simulated
  numbers looked fine. Those numbers came from the extrapolated model;
  the sizing finding invalidates them rather than being offset by them.
- Waving through an undecoupled bias net because the schematic is
  "only a block diagram at this stage". The decoupling element is what
  the stability item at the same review depends on being present.
- Relaxing a foundry bound so a value that lands exactly on it passes.
  An exact landing is a representation question, absorbed by the
  comparison tolerance; the bound itself stays where the foundry put it.

## Behavior contract (gate 3)

The periphery conversion, the model-window grading, the bias-feed
operating point, the derating, current-density and dissipation-density
comparisons, the connectivity grading and the assembled item verdict are
exercised by the gate 3 contract test:
scripts/test_q6012_schematic_review_item.py against
scripts/q6012_schematic_review_item_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_schematic_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
