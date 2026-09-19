---
name: q7050-surface-deposition-monitoring
description: "Evaluate particulate fallout onto a surface from witness-plate data under ECSS-Q-ST-70-50C: convert the counted particles per size band into obscured area, express it as percent area coverage of the plate, subtract an identically handled control plate, divide by the exposure for a deposition rate, then project that rate onto the real hardware exposure and grade it against the allowance. Use when reading a fallout plate result, projecting deposition across an integration campaign, or checking whether a plate was exposed long enough to mean anything. Trigger: ecss, q-st-70-50c, witness-plate-fallout, percent-area-coverage, particle-deposition-rate, fallout-plate-control-subtraction, surface-deposition-projection."
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
  tags: [ecss, q-st-70-50c-particle-contamination-monitoring, q-st-70-50c, q7050-surface-deposition-monitoring, witness-plate-fallout, percent-area-coverage, particle-deposition-rate, fallout-plate-control-subtraction, surface-deposition-projection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle Monitoring — Surface Deposition Monitoring (space-systems/ecss/q7050-surface-deposition-monitoring)

Use when the task is the fallout part of the surface clause of
ECSS-Q-ST-70-50C: a witness plate exposed beside the hardware, counted after
its exposure, and read as the deposition the hardware itself is collecting.

## Domain quick reference

- Fallout is reported as obscured area, not as a particle count. One large
  particle can obscure more area than several hundred small ones, so a count
  without sizes cannot be turned into a coverage figure at all.
- Each particle is treated as a disc of its stated size. That makes coverage
  scale with the square of size, which is why the largest band usually
  dominates a plate even when its count is the smallest number on the sheet.
- Coverage is a ratio to the plate area, so plate area belongs in the record.
  The same particles on half the plate read as twice the coverage, and a
  result quoted without its plate area cannot be compared with another.
- A control plate handled identically but never exposed carries the handling
  and the counting background. Subtracting it is what separates deposition
  from the process of taking the sample, and a missing control leaves that
  background inside the answer.
- Deposition is a rate. The plate's own exposure divides its coverage, and
  only then can the figure be projected onto a hardware exposure that lasted
  a different length of time.
- A projection is only as good as its span. Reading a one-day plate onto a
  six-month exposure assumes the zone and the activity in it stay as they
  were, which is exactly the assumption a long campaign breaks.
- Only an upward-facing plate collects gravitational settling. A vertical or
  downward plate answers a real question about transfer and re-entrainment,
  but the number it returns is not a settling rate.
- A plate can be too small. Below a sensible collecting area the count is
  dominated by whether one large particle happened to land, and the result
  describes luck rather than the zone.

## Workflow

1. Validate the plate: collecting area, exposure duration and orientation.
2. Convert the counted particles in each size band into projected disc area
   and sum them to the obscured area of the plate.
3. Express the obscured area as a percentage of the plate area.
4. Compute the same figure for the control plate and subtract it, refusing a
   control that exceeds the exposed plate rather than returning a negative.
5. Divide the net coverage by the plate exposure to obtain the deposition
   rate, then project that rate across the hardware exposure, carrying any
   coverage the surface already had.
6. Grade the projection against the allowance, absorbing an equality at the
   limit with a tolerance rather than relaxing the allowance.
7. Report the findings the plate raises on its own: an undersized plate, an
   exposure too short to separate from handling, a plate that does not face
   upward, a missing control, and a projection reaching far past the span
   that was actually measured.

## Pitfalls

- Reporting fallout as a particle count. Coverage goes with the square of
  size, so a count with no size distribution behind it cannot be converted
  and cannot be compared with an allowance stated as coverage.
- Dropping the plate area from the record. Coverage is a ratio, and a result
  quoted without the area it was divided by is not a number anyone else can
  use.
- Skipping the control plate. Handling, storage and the counting method all
  deposit, and without a control that contribution is silently reported as
  fallout from the zone.
- Projecting a short plate across a long campaign. The rate was measured over
  the plate's own exposure under the activity of that period; a projection
  far beyond it is an assumption about the future, and should be labelled as
  one.
- Reading a vertical plate as a settling rate. It measures something real,
  but not gravitational fallout, and mixing the two into one trend makes both
  uninterpretable.
- Accepting a small plate to save space. Below a sensible area the result
  turns on whether a single large particle landed, which is variance rather
  than a measurement of the zone.
- Moving the allowance to pass a projection that lands exactly on it. The
  equality is a representation question, handled by the tolerance inside the
  comparison; the allowed coverage stays as specified.

## Behavior contract (gate 3)

The plate validation, the size-band to obscured-area conversion, the percent
area coverage, the control-plate subtraction with its refusal, the deposition
rate, the projection onto the hardware exposure, the reporting bands and the
plate findings are exercised by the gate 3 contract test:
scripts/test_q7050_surface_deposition_monitoring.py against
scripts/q7050_surface_deposition_monitoring_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7050_surface_deposition_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
