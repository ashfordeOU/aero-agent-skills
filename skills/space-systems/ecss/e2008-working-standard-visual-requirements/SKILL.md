---
name: e2008-working-standard-visual-requirements
description: "Evaluate a secondary working standard against the visible defect rules written for solar cells and cell assemblies under ECSS-E-ST-20-08C clause 10.2.2.3.1: resolve the construction of the device, derive which cell-level and assembly-level rule families actually reach it, disposition each observed defect against an allowance derived from the device's own active area rather than a typed-in figure, refer an observation no applicable family governs instead of passing it silently, accumulate obscured active area into the short-circuit-current bias every transfer made with the device inherits, and name any applicable family left uninspected. Use when a working standard needs a fitness-for-transfer visual disposition. Trigger: ecss, e-st-20-08c, clause-10-2-2-3-1, working-standard-visual-defect-rules, secondary-working-standard-fitness, working-standard-active-area-obscuration, working-standard-inspection-coverage-gap."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-working-standard-visual-requirements, e-st-20-08c, clause-10-2-2-3-1, working-standard-visual-defect-rules, secondary-working-standard-fitness, working-standard-active-area-obscuration, working-standard-inspection-coverage-gap, photovoltaic-working-standard-visual-screen]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Working Standard Visual Requirements (space-systems/ecss/e2008-working-standard-visual-requirements)

Use when the task is clause 10.2.2.3.1 of ECSS-E-ST-20-08C: a secondary
working standard is held to the visible defect rules already written for
solar cells and for cell assemblies. This leaf reads one device and the
marks observed on it, and returns a disposition per observation plus the
fitness call that decides whether the device may still carry a
calibration value.

## Domain quick reference

- The clause writes no defect catalogue of its own. It points the
  existing cell and assembly rules at the working standard, so the first
  question is which of those rule families reaches a device built like
  this one, not how big the mark is.
- Construction fixes the applicable set. A bare cell standard is reached
  by the cell surface and edge rules alone. Adding a coverglass adds the
  coverglass and adhesive rules. Interconnecting it adds the joint rules.
  Mounting it on a carrier adds the wiring rules on top of all of those.
- A family that does not reach the build must not quietly dispose of the
  observation. A coverglass finding on a bare device is a real thing
  somebody saw; these rules simply are not the ones that judge it, so it
  is referred rather than accepted or rejected.
- The consequence of a defect is what separates a working standard from
  the cell it is built from. A cell that loses a sliver of collecting
  area loses a sliver of its own output. A working standard that loses
  the same sliver biases the current it reports, and every measurement
  later transferred through it inherits that bias.
- The rollup therefore converts accumulated obscured area into the
  fractional current bias it implies. That number, not the defect count,
  decides fitness, because short-circuit current tracks collecting area
  under a fixed irradiance.
- Not every finding obscures. A weld defect or a wiring mark can be
  serious for handling and survivability and still remove no collecting
  area, so it is dispositioned but never added into the bias.
- Allowances are derived from the device's own active area and its own
  shortest edge, so a physically smaller standard tightens its own limits
  without anyone editing a table.
- A crack is graded on the edge it runs across, not on the area it takes.
  A hairline crack occupies almost nothing and still propagates under
  thermal cycling until the device stops holding one value.
- Coverage is a finding in its own right. An applicable family that was
  never run leaves a hole that a clean report from the families that were
  run does not fill.

## Workflow

1. Resolve the device: identifier, construction and outline, and derive
   the active area and the shortest edge the allowances come from. Reject
   an inactive border that leaves no active area.
2. Derive the applicable rule families from the construction, and take
   the families actually inspected as a separate input.
3. For each observation, map its category to a rule family. If that
   family does not reach this construction, refer it and record it as
   ungoverned; do not grade its size.
4. Disposition a governed observation on area against the share of the
   active area allowed, with its own review band above the accept band.
5. Grade a crack additionally on its run across the shortest edge, and
   any observation on its clearance from a contact.
6. Add the obscuring findings up, convert the total into the implied
   current bias, and refer or reject the device on that figure.
7. Count findings per family, name every applicable family left
   uninspected, and take the worst disposition as the fitness verdict.

## Pitfalls

- Grading the device against every defect rule in the standard. Rules
  written for a coverglassed assembly do not reach a bare cell standard,
  and applying them manufactures failures that do not exist.
- Accepting an observation because no applicable family covers it. That
  is the one disposition it must not get; it is referred so somebody
  decides what judges it.
- Judging a mark against an absolute area figure. The figure that matters
  is a share of the active area this device actually has.
- Screening defects one at a time and never adding them up. Several
  individually acceptable marks can still shade enough of the face to put
  a bias on every transfer made through the device.
- Adding a weld or wiring finding into the obscuration total. It is a
  real finding that removes no collecting area, and counting it inflates
  a bias figure that is supposed to be physical.
- Grading a crack on area. A crack takes almost no area and is graded on
  how far it runs across the edge, because that is what decides whether
  it propagates.
- Reporting a clean device when a whole rule family was never run. The
  uninspected family is the finding.
- Comparing a measurement with a derived allowance by bare arithmetic.
  Every allowance here is a product of a criteria share and a measured
  quantity, so a measurement exactly on it can evaluate a few units in
  the last place above it; the comparison absorbs that representation
  error while the allowance stays untouched.

## Behavior contract (gate 3)

The geometry resolution, the construction-to-rule-family mapping, the
category-to-family lookup, the ungoverned-observation referral, the
derived area band with its review limit, the crack run band, the contact
clearance screen, the obscuration accumulation, the implied current bias
conversion, the per-family count rollup, the uninspected-family finding
and the device verdict are exercised by the gate 3 contract test:
scripts/test_e2008_working_standard_visual_requirements.py against
scripts/e2008_working_standard_visual_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_working_standard_visual_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
