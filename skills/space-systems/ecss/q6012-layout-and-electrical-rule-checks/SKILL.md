---
name: q6012-layout-and-electrical-rule-checks
description: "Validate a drawn MMIC mask layout against the foundry rule deck under ECSS-Q-ST-60-12C clause 7.2.11: run minimum drawn width, same-layer spacing between differing nets and inner-to-outer enclosure over every rectangle, then the electrical checks that each declared net is drawn, each drawn net is declared, no node is left floating and the narrowest metal carries the net current. Use when a layout database is handed over and the run has to say clean, waived or failed. Refuses a duplicate shape id and a shape on a layer the deck never defines. Trigger: ecss, q-st-60-12c, mmic-layout-rule-check, foundry-rule-deck, minimum-metal-spacing, via-enclosure-margin, mmic-netlist-connectivity, metal-current-capacity, drc-waiver."
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
  tags: [ecss, q-st-60-12-mmic-die-scope, q6012-layout-and-electrical-rule-checks, mmic-layout-rule-check, foundry-rule-deck, minimum-metal-spacing, via-enclosure-margin, mmic-netlist-connectivity, metal-current-capacity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Die -- Layout and Electrical Rule Checks (space-systems/ecss/q6012-layout-and-electrical-rule-checks)

Use when the task is the rule-check step of ECSS-Q-ST-60-12C clause 7.2.11: a
drawn MMIC layout is handed over with a foundry rule deck and a netlist, and the
run has to report whether the geometry obeys the deck, whether the drawn
connectivity is the intended one, and what remains open after waivers.

## Domain quick reference

- Geometry and connectivity are two different questions. A layout can obey every
  width and spacing rule and still be wired wrongly, and it can be wired
  correctly on metal too narrow to survive, so both passes have to run before a
  verdict is given.
- Spacing is a rule between nets, not between shapes. Two runs of the same net
  may touch by design, and flagging that contact as a spacing violation buries
  the real ones under noise the reviewer learns to skip.
- The narrow axis of a rectangle governs its width check, and the narrowest
  metal on a net governs that net's current capability. A wide bus with one
  neck is as good as the neck, on both counts.
- A waiver is a reporting outcome, not a deletion. A waived finding stays in the
  report with its reference attached; what changes is that it no longer blocks
  the run. A finding removed from the output cannot be reviewed at the next
  design iteration.
- The shapes that decide whether a checker is trustworthy are the ones drawn
  exactly on a rule. A run that rejects metal sitting precisely on the minimum
  spacing is not conservative, it is wrong, and it trains the designer to
  ignore the tool.

## Workflow

1. Validate the deck and the drawn shapes: every layer carries a minimum width
   and a minimum spacing, an enclosure rule names two different layers, and a
   shape id drawn twice is an input error rather than a duplicate check.
2. Run the geometry pass. Take the narrow axis of each rectangle against its
   layer's minimum width, the edge-to-edge separation of each same-layer pair on
   differing nets against the minimum spacing, and the tightest of the four
   margins of each inner shape against the enclosure rule.
3. Absorb floating-point representation error at every limit with a named
   tolerance, so a shape drawn exactly on a rule passes it, and report a shape
   on an undefined layer as its own finding rather than skipping it silently.
4. Run the electrical pass. A declared net with nothing drawn on it, a drawn net
   the netlist never declared and a net reaching fewer than two connection
   points are each reported; then take each net's declared current against the
   capability of its narrowest rated metal.
5. Move findings covered by a documented waiver into the waived group with their
   reference, keep them in the report, and return the counts grouped by severity
   and by rule with the open findings in a stable order.

## Pitfalls

- Writing the limit comparisons strictly. Metal drawn precisely on the minimum
  spacing is compliant, and a strict comparison turns the last representable
  bit of a coordinate into a violation the designer cannot resolve.
- Flagging same-net contact as a spacing error. Deliberate same-net metal
  overlap is how a connection is drawn, and reporting it floods the run with
  findings that train reviewers to skim past the real violations.
- Checking the drawn width on the long axis. A two hundred micron run three
  microns across passes any check that looks at the larger dimension, and the
  narrow axis is the one the foundry rule is written about.
- Rating a net on its widest metal. The current a net can carry is set at its
  narrowest neck, and averaging or taking the widest segment produces a pass
  for a track that will open in service.
- Deleting waived findings from the report. A waiver records a decision that has
  to be revisited when the layout changes; a finding deleted instead of waived
  takes that decision out of the next review entirely.

## Behavior contract (gate 3)

The deck and shape validation, the width, spacing and enclosure geometry checks,
the connectivity and current-capacity electrical checks, the waiver step and the
grouped verdict are exercised by the gate 3 contract test:
scripts/test_q6012_layout_and_electrical_rule_checks.py against
scripts/q6012_layout_and_electrical_rule_checks_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_layout_and_electrical_rule_checks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
