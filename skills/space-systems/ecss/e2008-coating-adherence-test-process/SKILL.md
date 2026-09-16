---
name: e2008-coating-adherence-test-process
description: "Use when running or auditing a coverglass coating adherence check. Execute the adherence check over the full coverglass face of every solar cell assembly subgroup sample under ECSS-E-ST-20-08C clause 6.4.3.9.2: validate the declared face and the applied zones, refuse a zone that runs off it, compute the exact union area the zones cover so overlapping applications are not counted twice, report the untested remainder against the full-face allowance, reduce each sample to the coating area that came away, and sentence the subgroup only when every sample is both fully covered and inside its removal limit. Trigger: ecss, e-st-20-08c, clause-6-4-3-9-2, coverglass-face-adherence-coverage, subgroup-sample-adherence-check, coating-removal-area-fraction, tested-zone-union-area, full-face-coverage-allowance."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-coating-adherence-test-process, coverglass-face-adherence-coverage, subgroup-sample-adherence-check, coating-removal-area-fraction, tested-zone-union-area, full-face-coverage-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Coating Adherence Test Process (space-systems/ecss/e2008-coating-adherence-test-process)

Use when the task is to run or audit the adherence check of ECSS-E-ST-20-08C
clause 6.4.3.9.2 — applying the check over the whole coverglass face of the
samples of a subgroup, and deciding from the applied zones and what came away
under them whether each sample, and the subgroup, can be sentenced.

## Domain quick reference

- Full face is the requirement, not a sampling convenience. A conductive
  coating fails where deposition, handling or an edge seal was weakest, and
  those places are not in the middle of the glass, so an unread corner is the
  most likely place for the defect the check exists to find.
- Coverage is a geometry problem, not a count of applications. Zones overlap
  when an operator repeats one, so the area the check actually reached is the
  union of the zones, and adding their areas instead reads coverage above one
  while leaving real gaps unseen.
- The union is computed exactly rather than sampled. Compressing the zone edges
  into a grid and adding the cells a zone contains gives the covered area with
  no grid resolution to choose and no Monte Carlo noise to defend at a review.
- A zone that runs off the face is an input error, not a wider check. It means
  the coordinates were mis-measured or the check touched the mount rather than
  the glass, and silently clipping it hides both.
- Two different numbers come out of the same run. How much face was read is a
  statement about the check; how much coating came away is a statement about
  the hardware. A sample that lost nothing over a face read only in part has
  demonstrated nothing about the part that was not read, so coverage is
  sentenced before removal.
- Removal is expressed against the whole face, not against the zones. A
  fraction quoted against the tested area flatters a check that only read a
  quarter of the glass.
- The floor edges are part of the floor. A face read exactly to the full-face
  floor, or a removal landing exactly on its limit, passes; the comparison
  absorbs representation error rather than moving the limit.
- A subgroup is a sampling device. Too few samples read leaves the result
  unable to speak for the lot, which is a different outcome from a subgroup
  whose samples were read and found wanting.

## Workflow

1. Validate the coverglass face: a positive width and height in millimetres.
2. Validate every applied zone against that face — positive dimensions, an
   origin on the glass, an extent that stays on it, and a removed area that
   cannot exceed the zone it was measured in.
3. Compress the zone edges into a grid and add the cells a zone contains, so
   the covered area counts an overlapped patch once.
4. Divide by the face area for the coverage, report the untested remainder in
   square millimetres as well, and compare with the full-face floor the
   untested allowance sets.
5. Sum the removed areas, express them against the whole face, and compare with
   the removal limit.
6. Sentence each sample: not covered outranks coating removed, because a
   removal figure from a partly read face is not yet evidence.
7. Close on one subgroup verdict — undersized, rejected, or accepted — with the
   worst coverage, the worst removal and every per-sample finding attached.

## Pitfalls

- Adding the zone areas for coverage. Two applications over the same patch then
  read as twice the glass, and a check that missed an edge reports itself
  complete.
- Quoting removal against the tested area. It rises as the check reads less of
  the face, which is exactly backwards.
- Clipping a zone that overruns the face instead of refusing it. The overrun is
  the finding; clipping converts a measurement error into a plausible number.
- Accepting a sample on its removal figure while its coverage fell short. The
  unread part of the face is where the weak coating usually is, so the order of
  the two sentences matters.
- Choosing a grid resolution to approximate the covered area. The zone edges
  already are the resolution; anything coarser argues with itself at a review.
- Treating a face read exactly to the floor, or a removal landing exactly on
  the limit, as a failure. The boundary belongs to the passing side and the
  tolerance belongs inside the comparison.
- Sentencing an undersized subgroup on the samples it happened to carry. The
  sampling floor is a separate condition with its own verdict.

## Behavior contract (gate 3)

The face and zone validation, the exact union area of the applied zones, the
coverage and removal fractions, the per-sample sentence order and the subgroup
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_coating_adherence_test_process.py against
scripts/e2008_coating_adherence_test_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coating_adherence_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
