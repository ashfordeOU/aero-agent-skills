---
name: q7026-wire-and-terminal-control
description: "Validate a wire and terminal pairing against the qualified combination list of ECSS-Q-ST-70-26C and derive the strip length window it must be cut to. Use when a build sheet names a contact for a conductor and the bare length between insulation and barrel has to be controlled. Checks conductor cross-section against the qualified barrel range, separates an unlisted terminal from an out-of-range conductor, derives the window from barrel length and insulation stand-off, categorizes a measured strip as short, in-window or long, and counts strands left outside the barrel. Trigger: ecss, q-st-70-26, wire-terminal-qualified-combination, crimp-strip-length-window, crimp-barrel-conductor-range, crimp-exposed-conductor-limit, crimp-conductor-brush."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-wire-and-terminal-control, wire-terminal-qualified-combination, crimp-strip-length-window, crimp-barrel-conductor-range, crimp-exposed-conductor-limit, crimp-conductor-brush]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Wire and Terminal Control (space-systems/ecss/q7026-wire-and-terminal-control)

Use when the task is the materials step of ECSS-Q-ST-70-26C — binding a
conductor to a terminal the combination was qualified with, and fixing
the length the insulation is cut back to before anyone reaches for a
tool.

## Domain quick reference

- A terminal and a conductor are a combination, not two independent
  choices. The qualified list is keyed on the terminal part number and
  carries the conductor cross-section range that terminal was qualified
  with. Nothing outside that pairing is qualified, however sensible the
  gauge looks.
- An unlisted terminal and an out-of-range conductor are different
  findings. One says nobody qualified this hardware; the other says
  somebody qualified it for a different wire. They go to different
  people and they are fixed differently.
- Strip length is derived, never remembered. It is the barrel length
  plus the gap the insulation has to stand off the barrel mouth, held
  inside a tolerance. Cutting to a number from the last job applies one
  terminal's window to another terminal's barrel.
- Short and long fail differently. A short strip leaves part of the
  barrel empty, so the crimp closes on insulation instead of metal. A
  long strip leaves bare conductor outside the barrel, which is a
  clearance and short-circuit problem, not a grip problem.
- Exposed conductor is measured from the barrel, not from the window. A
  strip inside its tolerance can still leave more bare metal than the
  installation allows when the barrel is short.
- Every strand goes in the barrel. A strand combed outside is not a
  slightly worse crimp; it is a loose conductor beside a terminal, and
  the strand count is the only way to see it after the die has closed.

## Workflow

1. Build the qualified list, folding part-number case and refusing a
   terminal listed twice or a range written backwards.
2. Validate the build-sheet item: identifier, terminal part number,
   conductor cross-section, measured strip, strand count and strands
   seated in the barrel.
3. Look the terminal up. Absent from the list, the item stops here with
   that finding and no strip verdict, because there is no barrel
   dimension to derive a window from.
4. Compare the conductor cross-section with the qualified range,
   inclusive of both bounds.
5. Derive the strip window from barrel length plus insulation stand-off
   and its tolerance.
6. Categorize the measured strip as short, in-window or long against
   that window, inclusive of both bounds.
7. Compute exposed conductor from the barrel mouth and compare it with
   the installation limit independently of the strip verdict.
8. Compare strands seated against strands present, and report the item
   with every finding tagged to its identifier; roll the lot up into
   accepted and rejected.

## Pitfalls

- Treating the terminal and the wire as separate approvals. Neither is
  qualified alone.
- Folding an unlisted terminal and an out-of-range conductor into one
  generic rejection, which sends both to whoever handles the other one.
- Carrying a strip length between terminal types. The window belongs to
  the barrel, not to the operator's memory.
- Checking the strip window and calling exposed conductor covered. A
  short barrel can be in window and still leave too much bare metal.
- Ignoring the strand count because the crimp looks sound. The brush is
  invisible once the die has closed.
- Losing the item identifier in the lot roll-up, which turns a specific
  rework into a lot-wide argument.

## Behavior contract (gate 3)

Qualified-list construction, combination verdicts, strip window
derivation, strip categorization at both bounds, exposed-conductor
computation, strand containment, per-item assessment and the lot
roll-up are exercised by the gate 3 contract test:
scripts/test_q7026_wire_and_terminal_control.py against
scripts/q7026_wire_and_terminal_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7026_wire_and_terminal_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
