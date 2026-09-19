---
name: q7005-method-selection
description: "Determine which infrared contamination method a given piece of hardware can actually be measured by. Use when the ECSS-Q-ST-70-05C method choice has to survive the hardware rather than the wish list: gate every candidate on physical access to the surface, on whether the substrate tolerates a solvent or a touch, and on whether the chosen solvent takes the contaminant type up at a usable recovery, then rank only the survivors by the margin their detection limit leaves on the required cleanliness level and flag a retained method that clears it too narrowly. Trigger: ecss, q-st-70-05-ir-contamination-scope, ir-contamination-method-selection, surface-access-feasibility-gate, contaminant-solvent-compatibility, ir-detection-limit-margin, non-destructive-surface-sampling."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-method-selection, ir-contamination-method-selection, surface-access-feasibility-gate, contaminant-solvent-compatibility, ir-detection-limit-margin, non-destructive-surface-sampling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Method Selection (space-systems/ecss/q7005-method-selection)

Use when the task is choosing one infrared contamination method of
ECSS-Q-ST-70-05C for a real piece of hardware — after applicability has
said the technique fits, and before anything is wiped, rinsed or probed.
Applicability asks what could work; selection asks what this
configuration, this substrate and this contaminant leave standing.

## Domain quick reference

- Selection is a gate and then a ranking, in that order. Gates are hard
  and each carries its reason; the ranking only ever runs on survivors. A
  sensitivity argument never brings back a candidate the hardware cannot
  physically be measured by.
- The access gate is about how the surface can be reached, not whether it
  can be seen. A standoff reflection read needs a sight line; a contact
  probe and a wipe need a hand on the surface; a rinse needs the surface
  open enough to flood and drain, or enclosed in a way that lets the
  solvent be recovered. An enclosed volume with no drain path leaves very
  few candidates and that is a real finding, not a procedural problem.
- The substrate gate is two separate questions that are often collapsed
  into one. A substrate may tolerate solvent but not contact, or contact
  but not solvent, and the two rule out different method sets. The
  standoff read is the one that survives both restrictions.
- The solvent gate is a data lookup, not a judgement. A silicone residue
  and an alcohol are a poor pairing whatever the procedure says; a
  recovery below the declared floor blocks the method. A contaminant type
  or a solvent with no tabulated recovery is refused rather than assigned
  a plausible number, because an invented recovery propagates straight
  into the quantitative result.
- The ranking runs on the margin between the required level and the
  method's detection limit, not on the limit alone. A method whose limit
  sits exactly on the requirement is admissible and fragile at once: it
  is kept if nothing better survives, ranked last, and flagged, because a
  small loss of recovery or a dirtier blank then puts the result under.
- A wet method's recovery fraction is part of the answer it produces. The
  extracted mass is not the surface mass, and the selection carries that
  correction forward as a duty rather than leaving it to the analyst.

## Workflow

1. Validate the selection policy: a recovery floor in the unit interval
   and a fragile threshold at or above the admissibility floor.
2. For every method the case declares a detection limit for, run the
   access, substrate and solvent gates and collect every gate that
   blocked it, not only the first.
3. Take the sensitivity margin as the required level over the detection
   limit, less one, so a limit on the requirement reads as zero.
4. Admit a candidate only when no gate blocked it and its margin clears
   the floor, absorbing representation error at the boundary rather than
   relaxing the floor.
5. Order the admissible candidates by falling margin, breaking ties on
   the method name so the selection is reproducible, and order the
   rejected list by name for the same reason.
6. Retain the first admissible candidate, flag it if it is fragile, and
   report every rejection with the gate that produced it and the duties
   the retained method brings.

## Pitfalls

- Choosing the most sensitive method first and checking access later. The
  gates are cheap and the sensitivity work is not; running them the other
  way round produces a plan the hardware cannot execute.
- Collapsing "tolerates solvent" and "may be touched" into one flag. They
  exclude different methods, and a surface that permits neither still has
  a standoff read available.
- Assigning a plausible recovery to an untabulated solvent and contaminant
  pairing. That number goes straight into the reported surface level, so
  a guess there is a fabricated measurement, not a conservative one.
- Excluding a method whose limit equals the requirement. It is admissible;
  the right response is to rank it last and flag it, so the decision to
  accept a zero-margin measurement is taken knowingly.
- Comparing a margin or a recovery against its floor with a bare strict
  inequality. A value built from a division can land a few units in the
  last place either side of a floor it should meet exactly; the gate
  absorbs that while the floor itself stays untouched.
- Reporting only the method kept. A configuration change can reopen a
  gate, and without the recorded reason the whole selection is re-run from
  nothing.

## Behavior contract (gate 3)

The policy validation, the access, substrate and solvent gates with their
reasons, the sensitivity margin, candidate admissibility and the fragile
flag, the ranking order and the retained selection are exercised by the
gate 3 contract test: scripts/test_q7005_method_selection.py against
scripts/q7005_method_selection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7005_method_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
