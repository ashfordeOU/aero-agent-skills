---
name: q7080-surface-condition-control
description: "Evaluate the surface condition of an additively manufactured part against its specification. Use when a roughness record has to be graded surface by surface: refuse an Rz reading compared with an Ra limit, grade every reading rather than the mean, work out what the process actually leaves at each overhang angle and separate a surface that failed from a limit no as-built surface at that angle can meet, count adhering partly fused particles per unit area, confirm every declared surface was measured, then take the worst and name the surfaces that drove it. Trigger: ecss, q-st-70-80-additive-manufacturing, am-as-built-surface-roughness, am-downskin-overhang-roughness, am-ra-versus-rz-parameter, am-adhered-partly-fused-particles, am-surface-sampling-coverage."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-surface-condition-control, am-as-built-surface-roughness, am-downskin-overhang-roughness, am-ra-versus-rz-parameter, am-adhered-partly-fused-particles, am-surface-sampling-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Surface Condition Control (space-systems/ecss/q7080-surface-condition-control)

Use when the quality clause of ECSS-Q-ST-70-80 is the task: deciding
whether the surfaces of an additively manufactured part meet the
condition the specification calls for, and telling a surface that came
out badly from a limit the process cannot reach on that surface at all.

## Domain quick reference

- An additive part does not have one surface. The same parameter set
  leaves one finish on a vertical wall, another on an up-facing skin and
  a much rougher one on a shallow down-skin, so the specification is
  read against the surface it applies to.
- Below a threshold overhang angle the melt pool is unsupported and sags
  into the powder beneath it, and the roughness grows as the angle falls
  towards horizontal. That growth is a property of the process, known
  before the part is built.
- A limit set below what the process leaves at that angle is not a
  failed surface. It is a requirement that needs a finishing operation,
  a support change or a build orientation change declared, and calling
  it a reject sends the part back to be built exactly the same way.
- Ra and Rz are different quantities. Comparing a reading in one with a
  limit in the other passes and fails surfaces for no physical reason,
  and the mistake is invisible once the number is in a table.
- Every reading on a surface is graded, not the mean of them. A mean
  inside the limit is exactly what one shallow patch in the middle of an
  otherwise good face produces.
- Partly fused particles adhering to the surface are a separate
  characteristic from roughness. They shed, so they are a contamination
  source, and they are graded per unit area because the same count on a
  small face and a large one are different results.
- A surface the specification names and nobody measured is unverified,
  which is a finding in its own right and not an implied pass.

## Workflow

1. Check the sampling first: every surface the specification declares
   has at least one reading, and a surface listed with an empty reading
   set counts as unmeasured rather than as measured clean.
2. For each surface, confirm the reading parameter and the limit
   parameter are the same quantity and refuse the comparison outright
   when they are not.
3. Grade every reading against the limit, reporting the count over, the
   worst reading and the mean, so the spread of the face is visible and
   not just the verdict.
4. For an as-built surface, compute what the process leaves at its
   overhang angle from the vertical-wall baseline and the growth below
   the threshold angle, and raise a limit below that expectation for
   review as an unachievable requirement.
5. Skip that expectation for a machined or polished surface: its finish
   comes from the cut, not from the build.
6. Where an adhering particle count is recorded, grade it per unit area
   against its own limit.
7. Take the worst of the surfaces and the sampling coverage as the
   verdict, name the surfaces sitting at that level, and prefix every
   finding with the surface identifier it came from.
8. Grade an on-limit reading or particle density with the tolerant
   comparison so a unit conversion cannot turn an on-limit surface into
   a reject.

## Pitfalls

- Applying one roughness limit to the whole part. The vertical walls
  will pass and the shallow overhangs will fail, and the finding will be
  written against the machine rather than against the orientation.
- Comparing Rz readings with an Ra limit. The two are different
  quantities, and the resulting table looks perfectly ordinary.
- Grading the mean roughness of a face. The mean is a summary; the
  requirement applies to the surface, and one rough patch is what the
  mean is best at hiding.
- Rejecting a down-skin that was never going to meet its limit as built.
  The finding belongs on the requirement or the orientation, and a
  rebuild in the same orientation produces the same surface.
- Applying the as-built expectation to a machined face. Its finish comes
  from the cut, and holding it to the build's baseline hides a genuinely
  bad cut behind a much looser number.
- Counting adhering particles as a bare total. The same count on a large
  duct and on a small boss are different densities, and only the
  per-area figure separates them.
- Treating a declared surface with no reading as acceptable. Nothing was
  measured, so nothing was verified, and the silence reads exactly like
  a pass in the record.

## Behavior contract (gate 3)

The roughness parameter check, per-reading grading, the as-built
overhang roughness expectation, the unachievable-limit review, the
per-area adhering particle density and the sampling coverage are
exercised by the gate 3 contract test:
scripts/test_q7080_surface_condition_control.py against
scripts/q7080_surface_condition_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_surface_condition_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
