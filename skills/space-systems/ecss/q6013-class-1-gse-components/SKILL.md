---
name: q6013-class-1-gse-components
description: "Use when a GSE parts list, umbilical interface or bench protection scheme is reviewed. Assess commercial components fitted inside ground support equipment that connects to flight hardware under clause 4.1.5 of ECSS-Q-ST-60-13C: trace each part to the interface it sits behind, form the worst-case power it can drive into the flight side from its own supply voltage and current limit, credit a protection barrier only when the barrier is itself qualified, compare what survives with the susceptibility limit declared for that interface, and return the control category each part earns instead of exempting a whole rack because it stays on the ground. Report the governing part and ranked findings. Trigger: ecss, q-st-60-13c, gse-commercial-component-control, gse-to-flight-interface-margin, gse-protection-barrier-credit, gse-worst-case-injection-power, gse-part-control-category."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q-st-60-13c, q6013-class-1-gse-components, gse-commercial-component-control, gse-to-flight-interface-margin, gse-protection-barrier-credit, gse-worst-case-injection-power, gse-part-control-category]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Ground Support Equipment Components (space-systems/ecss/q6013-class-1-gse-components)

Use when the task is clause 4.1.5 of ECSS-Q-ST-60-13C: commercial components
used inside ground support equipment that connects to flight hardware. This
leaf decides, part by part, which of those components sit in a path that can
reach the flight side, and what control each one therefore earns.

## Domain quick reference

- Ground support equipment is not flight hardware, and the temptation is to
  read that as an exemption for everything in the rack. The boundary that
  matters is not flight-or-ground, it is whether a fault inside the part can
  propagate across the umbilical. A commercial regulator wired straight to a
  harness under test is inside that boundary; the same regulator powering the
  rack's own fan is not.
- The quantity to compare is the fault case, not the operating point. A supply
  running at 40 mA through a part rated to fold back at 2 A can deliver the
  2 A when the part shorts, so the injection is formed from the supply voltage
  and the current limit that actually bounds it.
- A protection barrier is worth its attenuation only when the barrier itself
  has been demonstrated. An opto-isolator on a drawing and an opto-isolator
  with a qualified isolation rating are the same picture and different
  evidence, and crediting the first is how a bench passes a review and then
  destroys a unit.
- The susceptibility limit belongs to the interface, not to the rack. The same
  part that clears a power umbilical by two orders of magnitude can be the
  dominant threat on a telemetry line, because the limit moved by two orders
  of magnitude while the injection did not move at all.
- Three control levels are distinguishable and worth keeping distinct: an
  ordinary ground part, a part declared with credited protection, and a part
  that has to be controlled as though it were flight hardware because nothing
  stands between it and the spacecraft.
- One exposed part governs the bench. Averaging margins across a parts list
  hides the single line that can reach the flight side, which is the only line
  the clause is about.

## Workflow

1. Validate each part and the interface identifier it is declared against;
   refuse an interface with no declared susceptibility limit rather than
   assuming a generous one.
2. Separate the parts that connect to flight hardware from the ones that do
   not, and stop evaluating the latter -- they carry ordinary ground control.
3. Form the worst-case injection from the supply voltage and the current limit
   that bounds the part under fault.
4. Look up the barrier attenuation, credit it only when the barrier is
   qualified, and record a note whenever a declared barrier earns nothing.
5. Divide the injection by the credited attenuation and form the margin
   against the interface susceptibility limit.
6. Categorize each connected part on that margin, treating an exactly-met
   margin as met through a named tolerance rather than by moving the
   requirement.
7. Retain the lowest-margin connected part as the governing case, breaking an
   exact tie on the part identifier so the result is reproducible.
8. Return the category counts, the governing part, ranked findings and one
   accept-or-escalate verdict.

## Pitfalls

- Exempting the rack because it is ground equipment. The clause exists for the
  subset of ground parts that are electrically upstream of flight hardware,
  and that subset is identified by tracing the interface, not by reading the
  label on the box.
- Sizing the injection on the nominal current. The fault current is what
  arrives at the umbilical when the commercial part fails short, and it is
  usually set by a limit somewhere else in the supply.
- Crediting an undemonstrated barrier. An unqualified isolator is worth unity;
  giving it three orders of magnitude on the strength of a datasheet is the
  single change that turns an escalation into a pass.
- Using one susceptibility limit for the whole bench. Power and telemetry
  interfaces differ by orders of magnitude, so a part must be graded against
  the interface it actually touches.
- Averaging margins over the parts list. The bench is governed by its worst
  connected part; a mean dilutes exactly the part the review is looking for.
- Nudging the required margin to clear an exact equality. The equality is a
  representation question handled inside the comparison; the required margin
  stays where the project set it.

## Behavior contract (gate 3)

The interface tracing, worst-case injection, barrier crediting, margin
formation, control categorization, governing-part selection and bench verdict
are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_gse_components.py against
scripts/q6013_class_1_gse_components_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_1_gse_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
