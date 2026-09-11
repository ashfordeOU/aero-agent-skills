---
name: e1011-mannequin
description: "Use when verify fit, reach, and visibility of crewed spacecraft workstations and habitable volumes using electronic mannequins and digital human models, per ECSS-E-ST-10-11C §4.5.2. Select the bounding anthropometric population percentiles (5th-female for minimum reach, 95th-male for maximum envelope), position the mannequin at each defined workstation, evaluate clearance against the required fit margin, check whether each control target lies within the functional reach envelope, and confirm each critical display falls within the accepted visibility cone without obstruction. Flag any station where fit margin, reach shortfall, or obstruction check fails. Trigger: ecss, e-st-10-11c, e-st-10-system-scope, mannequin, digital-human-model, fit-verification, reach-envelope, visibility-check, anthropometry, crewed-spacecraft."
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
  tags: [ecss, e-st-10-11c, e-st-10-system-scope, mannequin, digital-human-model, fit-verification, reach-envelope, visibility-check, anthropometry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Electronic Mannequin Verification (space-systems/ecss/e1011-mannequin)

Use when the task is the fit, reach, and visibility verification of crewed
spacecraft workstations using electronic mannequins and digital human models
(DHMs) per ECSS-E-ST-10-11C §4.5.2 — establishing which bounding
anthropometric population cases to run, positioning the mannequin at each
workstation, and checking each check type (fit clearance, functional reach,
visibility cone) against its acceptance criterion.

## Domain quick reference

- §4.5.2 requires fit, reach, and visibility to be verified against a
  representative anthropometric population range. The two bounding cases
  that bracket the design space are the 95th-percentile male (largest body
  — worst case for fit/clearance) and the 5th-percentile female (smallest
  body — worst case for reach and visibility from a low-eye-point).
  Both cases must pass before a workstation is accepted; using only the
  50th-percentile male is a common but non-compliant shortcut.
- Fit check: the available linear clearance dimension must exceed the
  mannequin stature by at least the required margin (typically 50 mm
  minimum). Clearance is measured along the constrained axis — usually
  vertical for seated overhead panels, lateral for corridor pass-through.
- Reach check: the distance from the mannequin's shoulder reference point
  to each target control or connector must not exceed the mannequin's
  functional reach. Functional reach is shorter than arm length because it
  accounts for torso stability constraints in microgravity; use the
  population-specific functional reach, not the full arm length.
- Visibility check: each critical display or indicator must lie within the
  mannequin's visibility cone (typically ±55 degrees from the forward eye
  axis for comfortable eye rotation without head movement) and must have an
  unobstructed sightline. A structurally clear angle that is still blocked
  by an intermediate panel, harness, or equipment box is a visibility
  failure regardless of the angular value.

## Workflow

1. Identify every workstation or habitable volume to be verified and list
   the check types required for each (fit, reach, visibility, or all three).
   Reject any check-type string that is not one of those three before
   proceeding.
2. For each workstation, determine the bounding anthropometric cases: fit
   checks require the 95th-percentile male; reach checks require the
   5th-percentile female; visibility checks require both because the eye
   point height and cone origin differ between the two bounds.
3. Retrieve the anthropometric parameters (stature and functional reach)
   for each bounding case from the approved population table. Reject any
   (sex, percentile) combination not in that table rather than interpolating.
4. Run the fit check: compute the clearance margin (available clearance minus
   mannequin stature). The workstation passes fit if the margin meets or
   exceeds the required minimum margin. Record the margin value whether it
   passes or fails.
5. Run the reach check: compute the shortfall (target distance minus
   functional reach). The workstation passes reach if the shortfall is zero
   or negative. Record the shortfall value whether it passes or fails.
6. Run the visibility check: confirm the sightline angle to each critical
   display is within the accepted cone limit AND that no obstruction blocks
   the sightline. A display fails visibility if either condition is violated;
   both must be true for a pass.
7. Aggregate the three check results for the workstation. The workstation
   is verified only when fit, reach, and visibility all pass for all
   required bounding cases. Produce a per-workstation summary listing each
   check result and the measured value.

## Pitfalls

- Running only one anthropometric bound for a check type that requires both
  — visibility checks must use both 95th-male and 5th-female eye points
  because head clearance differs and can change which displays are obstructed.
- Using full arm length instead of functional reach for the reach check —
  in microgravity the occupant cannot brace against a fixed surface, so
  functional reach is the correct limiting parameter and is consistently
  shorter than geometric arm length.
- Passing the clearance margin as zero or unset and reading "no violation"
  as compliant — an unset margin means the required fit budget was never
  captured, which is itself a finding.
- Treating an angular check that passes as automatically free of obstruction
  — the obstruction check is independent of the cone angle check; both must
  pass separately for visibility to be accepted.
- Applying the 50th-percentile male as the sole population case — this is
  the most frequently cited non-compliance in DHM reviews and fails §4.5.2
  because it covers neither the fit-bounding nor the reach-bounding extreme.

## Behavior contract (gate 3)

The anthropometric lookup, fit-clearance, reach-shortfall, visibility-cone,
and full-workstation-verification logic is exercised by the gate 3 contract
test: scripts/test_e1011_mannequin.py against
scripts/e1011_mannequin_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_mannequin.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
