---
name: e2040-tailoring-by-device-criticality
description: "Determine which baseline requirements a device actually carries once its type and criticality category are known, under ECSS-E-ST-20-40C clause 5.1.2: fold the category and device type spellings onto ordered sets, keep each requirement whose type reach covers the device and whose criticality floor its category meets, confirm the baseline is monotonic so raising a category never drops a requirement, then overlay the project delta and report each unjustified removal, each removal of a non-removable requirement and each addition nothing defines. Use when a device requirement set is being tailored or audited. Trigger: ecss, e-st-20-40c, device-criticality-tailoring, device-type-requirement-scope, criticality-category-floor, non-removable-baseline-requirement, tailoring-delta-justification, criticality-monotonic-requirement-set."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-tailoring-by-device-criticality, device-criticality-tailoring, device-type-requirement-scope, criticality-category-floor, non-removable-baseline-requirement, tailoring-delta-justification, criticality-monotonic-requirement-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Tailoring by Device Criticality (space-systems/ecss/e2040-tailoring-by-device-criticality)

Use when the task is the tailoring rule of ECSS-E-ST-20-40C clause
5.1.2 -- cutting the full requirement set down to the requirements a
particular device has to answer, using the two properties that decide
it: what kind of device it is, and how severe the consequence of its
failure is.

## Domain quick reference

- Two independent axes decide applicability. The device type says
  whether a requirement is even about this kind of hardware, and the
  criticality category says how much of the applicable set is
  demanded. Collapsing them into one severity number loses the type
  axis and pulls in requirements written for other hardware.
- A requirement carries a criticality floor, not a criticality. It
  applies at that category and at every more severe one, which is what
  makes the set grow monotonically as consequence grows.
- Monotonicity is the property that makes the category mean something.
  If moving a device up a category ever removes a requirement, the
  category is no longer a measure of how much rigour is demanded, and
  a supplier can reduce its obligations by declaring a worse failure
  consequence.
- Some requirements have no floor to speak of: they apply to every
  device at every category because they are how the device is
  specified at all. Those are also the ones a project most often tries
  to tailor away, which is why the baseline marks them non-removable
  rather than relying on judgement.
- Project tailoring is a delta against the tailored baseline, not a
  fresh selection. What the review needs to see is what the project
  added, what it removed, and why -- and a removal that travels with
  no reason recorded is indistinguishable afterwards from an omission.
- An addition that is not in the baseline is not wrong, but nothing
  then defines it. It has to arrive with its own statement or the set
  holds an identifier that no document explains.

## Workflow

1. Fold every criticality and device type spelling onto the canonical
   ordered sets. Refuse an unrecognised spelling: a silently defaulted
   category produces a plausible set for the wrong device.
2. Read the baseline and refuse a repeated requirement identifier, an
   empty type scope and a free-text scope that is not the all-types
   token, since each one quietly changes who the requirement reaches.
3. Derive the tailored set: keep a requirement when its type reach
   covers this device and the device's category is at or above its
   criticality floor.
4. Run the monotonicity check across all four categories for this
   device type and report any requirement that a more severe category
   drops.
5. Overlay the project delta. Refuse a removal of something the set
   does not hold and an addition of something it already holds, since
   both mean the delta was written against a different baseline.
6. Report each removal with no justification, each removal of a
   requirement the baseline marks non-removable, and each addition
   that is not in the baseline.
7. Report the tailored set, the final set and the reduction the delta
   represents, so the review sees the before, the after and the
   difference rather than only the result.

## Pitfalls

- Tailoring on criticality alone. The type axis is what keeps
  requirements written for one kind of hardware out of another's set,
  and dropping it produces a set that looks thorough and is wrong.
- Storing a criticality rather than a floor. A requirement recorded as
  applying at exactly one category disappears at every other, and the
  set stops growing with consequence.
- Skipping the monotonicity check because the baseline looks sensible.
  Non-monotonicity comes from a single mis-entered floor and is
  invisible at the category the device happens to sit at.
- Applying a delta without checking it against the set it was written
  for. A removal of something the tailored set never held means the
  delta predates a baseline change, and applying the rest of it is
  then unsafe.
- Letting an unjustified removal through because the reason is obvious
  today. The next project inherits the reduced set and the obvious
  reason is gone.
- Reading a non-removable requirement as advisory. It is marked that
  way because it is how the device gets specified at all, and removing
  it leaves the rest of the set with nothing to attach to.

## Behavior contract (gate 3)

The category and device type folding, baseline validation, type and
floor applicability rule, tailored set derivation, monotonicity check
across the categories, and project delta overlay with its justification
and non-removable findings are exercised by the gate 3 contract test:
scripts/test_e2040_tailoring_by_device_criticality.py against
scripts/e2040_tailoring_by_device_criticality_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_tailoring_by_device_criticality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
