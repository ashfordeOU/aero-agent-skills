---
name: e2008-sca-humidity-shelf-life-purpose
description: "Use when scoping or reviewing an accelerated shelf-life humidity exposure on a solar cell assembly. Evaluate whether an accelerated shelf-life humidity exposure on a solar cell assembly is earned, represents the required storage life and actually watches the conductive coverglass coating, under ECSS-E-ST-20-08C clause 6.4.3.8.1: compute the factor by which the planned damp-air conditions accelerate the declared storage environment, convert the run into the storage months it is worth, refuse a factor beyond the model's fitted range, confirm the coating measurements are in the monitoring set, then decide whether the exposure represents the shelf life or falls short. Trigger: ecss, e-st-20-08c-clause-6-4-3-8-1, sca-accelerated-shelf-life-exposure, conductive-coverglass-coating-monitoring, damp-air-acceleration-factor, sca-storage-life-equivalence, coating-sheet-resistance-stability."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-humidity-shelf-life-purpose, sca-accelerated-shelf-life-exposure, conductive-coverglass-coating-monitoring, damp-air-acceleration-factor, sca-storage-life-equivalence, coating-sheet-resistance-stability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Humidity Shelf-Life Test Purpose (space-systems/ecss/e2008-sca-humidity-shelf-life-purpose)

Use when the task is to state and defend why an accelerated humidity exposure
is applied to a solar cell assembly under ECSS-E-ST-20-08C clause 6.4.3.8.1 --
what the damp-air run is meant to reveal about the conductive coverglass
coating, whether the assembly and its required storage life justify the run at
all, and whether the planned conditions really stand in for the shelf life
they compress.

## Domain quick reference

- The exposure is aimed at a specific part. The conductive coating on the
  coverglass exists to bleed charge off an insulating surface, and it is the
  feature of the assembly that minds damp storage most: it can lose sheet
  conductivity, lose continuity to the assembly ground, or cloud enough to cost
  transmittance. An assembly whose coverglass carries no conductive coating has
  nothing for this exposure to watch.
- Shelf life is the environment being represented, not orbit. The assembly can
  sit in stores for years before it is laid down on a panel, and the run
  compresses those years into a short spell in warm damp air so the coating's
  behaviour is seen before the assembly is committed.
- Acceleration is a declared model. Humidity raised to an exponent against the
  storage ratio and a doubling per temperature interval turn a planned run into
  a number of storage months. Two projects with different models get different
  answers from the same chamber settings, so the model travels with the result.
- More acceleration is not more evidence. Past the range the model was fitted
  over, the chamber starts driving mechanisms that storage never produces, so a
  factor beyond the declared ceiling is refused rather than credited.
- An exposure that never measures the coating serves no purpose. A run with
  only an output-power check afterwards shows the assembly survived damp air
  and says nothing about sheet resistance, grounding continuity or
  transmittance, which are the three things the clause is aimed at.
- A stated purpose is not a served purpose. An assembly that justifies the
  exposure but has no run planned yet is a distinct outcome from one whose
  planned run is too short, too fierce, or blind to the coating, and the four
  carry different actions.

## Workflow

1. Validate the acceleration policy first: humidity exponent, doubling
   interval, hours per month, shelf-life trigger, acceleration ceiling and
   coverage factor. A coverage factor below unity would let the run fall short
   by construction and is refused.
2. Group the declaration: the coverglass coating, rejecting an unrecognised one
   rather than assuming it is bare, and the required shelf life in months.
3. Decide whether the exposure is earned: a conductive coating present and a
   required shelf life at or above the trigger. A shelf life landing exactly on
   the trigger earns the exposure; the comparison tolerance absorbs
   representation error and the trigger does not move.
4. When it is earned, compute the acceleration factor the planned damp-air
   conditions give over the declared storage environment, and convert the run
   duration into the storage months it is worth.
5. Check the monitoring set names every coating measurement, and report each
   one it leaves out by name rather than as a count.
6. Close on one verdict: not required, justified but not planned, accelerated
   beyond the model, planned but not watching the coating, planned but under
   the shelf life, or representing the shelf life -- with the coating
   objectives the run serves attached to it.

## Pitfalls

- Quoting chamber hours as shelf life. A thousand hours means nothing until the
  storage environment it is accelerated against is stated; the same run is
  worth years against a damp warehouse and months against a dry conditioned
  store.
- Pushing the temperature to shorten the run. The doubling term makes that
  tempting, but past the fitted range the coating sees mechanisms its storage
  life would never produce, and the result no longer stands in for anything.
- Judging the coating by output power alone. Sheet resistance can drift far
  enough to stop the coating doing its charge-bleed job while the assembly
  still makes its current, so the electrical output check passes and the
  purpose goes unserved.
- Treating an uncoated coverglass as a pass. It is not a pass, it is an
  assembly outside the reason for the exposure, and recording it as a pass
  quietly credits the build with evidence it never produced.
- Summing chamber hours across runs at different settings. Hours at eighty-five
  percent and forty-five degrees are not the hours at sixty percent and
  thirty degrees, and adding them undercounts what the coating actually saw.

## Behavior contract (gate 3)

The policy validation, damp-air acceleration factor, storage-life equivalence,
coating declaration, monitoring gap and purpose verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_sca_humidity_shelf_life_purpose.py against
scripts/e2008_sca_humidity_shelf_life_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_humidity_shelf_life_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
