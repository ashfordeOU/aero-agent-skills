---
name: initial-flaw-size-assumption
description: "Use when determine initial crack size and shape assumptions for fracture
  mechanics analysis under ECSS-E-ST-32C clause 7.2.6: select the governing NDT
  method from the applicable inspection programme, look up the corresponding minimum
  detectable flaw dimensions (depth and half-surface-length) from the NDT capability
  reference, assign the correct flaw shape (surface semi-elliptical, corner quarter-circle,
  or through-thickness) based on component geometry, confirm the assumed flaw is
  below the material critical flaw size for the applied stress, and record the
  assumption with its NDT-method anchor for the fracture control report.
  Trigger: ecss, e-st-32-structures-scope, fracture-control, initial-flaw-size,
  ndt-capability, crack-shape, fracture-mechanics, semi-elliptical-crack."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, initial-flaw-size, ndt-capability, crack-shape, fracture-mechanics, semi-elliptical-crack]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Initial Flaw Size Assumption (space-systems/ecss/initial-flaw-size-assumption)

Use when the task is to determine the initial crack size and shape to be
assumed in a fracture mechanics life or residual-strength calculation,
following ECSS-E-ST-32C clause 7.2.6. The assumed flaw dimensions are
taken from the detection limits of the NDT method applied to the part,
or from the standard uninspected-part default when no inspection is
performed.

## Domain quick reference

- Clause 7.2.6 ties the initial flaw assumption to the NDT programme:
  the assumed crack cannot be smaller than the largest flaw the NDT method
  might miss at the required confidence level (typically 95 % probability
  of detection at 90 % confidence). Where no inspection is performed, a
  standard default flaw governs — a conservative size representative of a
  flaw that could plausibly escape all manufacturing controls.
- Flaw shape depends on component geometry and loading direction. Surface
  cracks at a free surface are represented as semi-elliptical (depth a,
  half-surface-length c). Edge and fastener-hole cracks are represented as
  quarter-circle corner cracks (radius r = a = c). Through-thickness flaws
  in thin sections are represented as through-cracks (half-length b). The
  shape selection must be documented and justified.
- Aspect ratio a/c defines the flaw eccentricity. A ratio of 1.0 gives a
  semi-circular surface crack (a = c); ratios below 1.0 give a wider,
  shallower crack. NDT capability limits typically define both a and c
  independently; their ratio is an output, not an input.
- Figures 7-1 through 7-3 of ECSS-E-ST-32C §7.2.6 map NDT method to
  minimum detectable flaw size as a function of material thickness and
  inspection frequency. This leaf encodes those relationships as a
  capability table indexed by method name, used for flaw selection.

## Workflow

1. Confirm whether the part is subject to an NDT inspection. If no
   inspection is specified, apply the uninspected-part default flaw size
   (standard a = 1.27 mm, c = 1.905 mm surface semi-elliptical). Record
   "UNINSPECTED" as the governing method.
2. For each applicable NDT method, retrieve the minimum detectable flaw
   dimensions (depth a_min, half-length c_min) from the NDT capability
   table. Reject any method not in the approved table with an explicit
   error — do not guess or interpolate.
3. When more than one method is applied to the same region, select the
   most detection-capable method (smallest a_min) as the governing method.
   Document the selection and the methods that were superseded.
4. Assign the flaw shape based on the component geometry: surface geometry
   maps to a surface semi-elliptical crack; edge or fastener-hole geometry
   maps to a corner quarter-circle crack; thin sections where the flaw
   spans the full thickness map to a through-crack. Reject unrecognized
   geometry designations.
5. Compute the aspect ratio a/c from the selected flaw dimensions. For
   corner cracks (a = c = r), the aspect ratio is 1.0 by definition. For
   through-cracks, the aspect ratio is not applicable.
6. Verify that the assumed flaw depth a is less than the component's
   material-specific critical flaw size a_c for the design stress level.
   Flag the assumption as non-compliant if a >= a_c; this means the part
   may already be critical at initial flaw size and requires redesign or
   tighter inspection.
7. Record the result — method, flaw dimensions, shape, aspect ratio, and
   compliance verdict — as the initial flaw assumption entry in the
   fracture control analysis.

## Pitfalls

- Using the same NDT method's flaw size for a geometry it cannot inspect:
  a volumetric method (RT, UT) does not characterise surface-crack depth
  and half-length the same way a surface method (PT, MT, ET) does.
  Assign the correct shape for the method; a through-crack from RT is not
  interchangeable with a surface semi-elliptical from PT.
- Assuming aspect ratio a/c = 1.0 for all surface cracks: the NDT
  capability table defines a and c independently; forcing a circular shape
  when c > a understates the stress-intensity factor at the deepest point
  and can be unconservative for shallow wide cracks.
- Treating a missing NDT record as equivalent to "uninspected default":
  the uninspected default is a deliberate assumption, not a fallback for
  administrative gaps. A missing inspection record is a non-conformance
  and must be resolved before applying the default.
- Applying the NDT minimum flaw size without accounting for material
  thickness: some NDT methods lose sensitivity in thin sections; the
  governing flaw size may be larger than the table value when thickness
  falls below the method's reliable range.

## Behavior contract (gate 3)

The NDT capability lookup, flaw shape selection, aspect ratio computation,
multi-method ranking, and compliance check logic are exercised by the
gate 3 contract test: scripts/test_initial_flaw_size_assumption.py against
scripts/initial_flaw_size_assumption_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_initial_flaw_size_assumption.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
