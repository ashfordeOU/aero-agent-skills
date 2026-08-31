---
name: goodman-diagram
description: "Determine the allowable stress amplitude for infinite life under mean stress: compute the modified Goodman, Gerber, and Soderberg allowable amplitudes from the endurance limit, ultimate strength, and yield strength, plot the Haigh diagram with the design point, and give the infinite-life verdict when the applied amplitude exceeds the allowable. Use when a fluctuating load case must be checked against a mean-stress fatigue limit or a Haigh diagram / fatigue diagram comparison is needed for a structure. Trigger: goodman, gerber, soderberg, haigh diagram, fatigue diagram, mean stress, endurance limit, allowable amplitude, infinite life, stress ratio."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fatigue
  tags: [fatigue, mean-stress, goodman, gerber, soderberg, haigh-diagram, endurance-limit, infinite-life]
  version: 0.1.0
  author: AeroSkills
---

# Mean-Stress Fatigue Corrections (structures/fatigue/goodman-diagram)

Use when a fluctuating stress cycle is superimposed on a steady mean
stress and the infinite-life margin must be quantified: compute the
allowable stress amplitude per modified Goodman, Gerber, and Soderberg,
place the design point on the Haigh diagram, and decide whether the
applied amplitude is acceptable.

## Domain quick reference

- Mean stress Sm is the steady component of the cycle,
  Sm = (Smax + Smin) / 2; stress amplitude Sa is the oscillating
  component, Sa = (Smax - Smin) / 2; stress ratio R = Smin / Smax.
- The endurance limit Se is the fully reversed (R = -1) stress
  amplitude the material survives for infinite life.
- Modified Goodman line: allowable amplitude
  Sa = Se * (1 - Sm / Sut), a straight line from (0, Se) to (Sut, 0).
- Gerber parabola: Sa = Se * (1 - (Sm / Sut)^2), above the Goodman
  line, less conservative.
- Soderberg line: Sa = Se * (1 - Sm / Sy), below the Goodman line,
  most conservative, safe against yield at the mean stress.
- The Haigh diagram plots allowable amplitude against mean stress for
  each criterion; a design point (Sm, Sa) above the line fails the
  infinite-life check for that criterion.
- Infinite-life check: the applied amplitude must not exceed the
  allowable amplitude, Sa <= Sa_allowable.
- FAR-25 and CS-25 set the certification context for fatigue
  substantiation of transport airplane structure; the mean-stress
  correction itself is standard mechanical engineering methodology.

## Workflow

1. Gather material allowables: endurance limit Se, ultimate strength
   Sut, yield strength Sy, all in the same stress unit.
2. Resolve the load case into mean stress Sm and applied amplitude Sa
   (from Smax and Smin if the cycle extrema are given; R = Smin / Smax
   confirms the cycle type).
3. Compute the allowable amplitude for each criterion:
   Goodman Se * (1 - Sm / Sut), Gerber Se * (1 - (Sm / Sut)^2),
   Soderberg Se * (1 - Sm / Sy).
4. Compare the applied amplitude against each allowable; any
   exceedance fails the infinite-life check under that criterion.
5. Plot the design point and the three lines on the Haigh diagram to
   show which criterion governs and the margin.
6. Report the verdict and the governing criterion.

## Pitfalls

- Mixing stress units (MPa vs ksi) between Se, Sut, Sy, Sm, Sa.
- Using a mean stress above the ultimate strength: the Goodman
  allowable goes non-positive and no positive amplitude is acceptable.
- Forgetting that the endurance limit assumes fully reversed loading;
  any nonzero mean stress reduces the allowable amplitude.
- Treating Soderberg as an alternative to yield checks: it bounds
  amplitude, it does not replace a static yield check at the peak
  stress Sm + Sa.
- Applying these corrections to compressive mean stress regimes
  without noting the conservative assumption; the formulas here target
  tensile mean stress.
- Reporting the Gerber or Goodman verdict without stating which
  criterion it came from; the three lines disagree by design.

## Behavior contract (gate 3)

The mean-stress correction logic is exercised by the gate 3 contract
test: scripts/test_goodman.py against scripts/goodman_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_goodman.py

## Compliance

- FAR-25 and CS-25 are cited as reference-only certification context
  (compliance: STANDARDS-REF, gated: false); no text is quoted from
  either regulation.
