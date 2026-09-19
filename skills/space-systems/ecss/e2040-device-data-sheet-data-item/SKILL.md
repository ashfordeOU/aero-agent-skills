---
name: e2040-device-data-sheet-data-item
description: "Verify a published device data sheet against the required contents of ECSS-E-ST-20-40C Annex H before it goes out to users. Use when the sheet has to carry the device characteristics and the operating ratings in a form a designer can build against: confirm each characteristic orders its minimum, typical and maximum, carries a real unit and names the conditions it was taken under, then place every recommended operating limit inside the absolute maximum rating, compute the derating margin each limit leaves, grade it against the required derating factor, and report the parameters left with no headroom. Trigger: ecss, e-st-20-40-device-scope, e2040-device-data-sheet-data-item, device-characteristic-min-typ-max, absolute-maximum-rating-envelope, recommended-operating-conditions, parameter-derating-margin, data-sheet-drd."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-device-data-sheet-data-item, device-characteristic-min-typ-max, absolute-maximum-rating-envelope, recommended-operating-conditions, parameter-derating-margin, data-sheet-drd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Device Data Sheet Data Item (space-systems/ecss/e2040-device-data-sheet-data-item)

Use when the task is the required contents of the published device data
sheet of ECSS-E-ST-20-40C Annex H -- the sheet a designer builds
against, carrying the characteristics of the device and the ratings
inside which it may be operated.

## Domain quick reference

- A **characteristic** is a triple: minimum, typical and maximum, in one
  declared unit and under named test conditions. Any of the three may
  be absent, but the ones present have to be ordered, and a typical
  outside its own minimum and maximum is a printing error that will be
  designed against for years.
- A characteristic without **test conditions** is not a specification.
  A supply current has a supply voltage and a temperature behind it,
  and a number quoted without them cannot be reproduced or held to.
- The **absolute maximum rating** is a survival limit, not an operating
  point. Nothing is guaranteed at it and the device may be damaged
  beyond it, so the recommended operating limit has to sit strictly
  inside it.
- The **derating margin** of a parameter is the fraction of the
  absolute rating the recommended limit leaves unused, one minus the
  recommended limit over the absolute one. A required derating factor
  states how much of that fraction the project demands, and a limit
  that lands exactly on the requirement meets it -- the comparison
  absorbs representation error rather than moving the requirement.
- Ratings are two-sided where the parameter is. A recommended range has
  to sit inside the absolute range at both ends, and a sheet quoting an
  absolute maximum with no absolute minimum on a bipolar parameter has
  left one of the two edges undefined.

## Workflow

1. Check the sheet's section list against the required contents and
   name each absent section.
2. Validate each characteristic: a non-empty identifier, a unit that is
   a real dimension rather than a placeholder, and minimum, typical and
   maximum values ordered where they are present. Reject an inverted
   triple as an input error rather than sorting it silently.
3. Report as content findings any characteristic whose unit is a
   placeholder, whose test conditions are absent, or which carries no
   value at all.
4. Validate each rating: an absolute maximum, a recommended maximum,
   and, where the parameter is two-sided, the matching minima. Reject a
   non-positive absolute maximum, which makes the derating fraction
   meaningless.
5. Place the recommended range inside the absolute range at both ends
   and report a recommended limit at or beyond an absolute one.
6. Compute the derating margin of each parameter and grade it against
   the required derating factor, treating a margin equal to the
   requirement as met within a named tolerance.
7. Report the worst-margin parameter, every rating without headroom and
   every characteristic content defect as separate findings.

## Pitfalls

- Treating the absolute maximum as a place the device may be run. It is
  the edge of survival; the sheet has to publish a recommended limit
  below it, and a design that sits on the absolute rating has no margin
  for a transient of any kind.
- Comparing a derating margin with a strict inequality. A recommended
  limit at exactly the required fraction of the absolute rating
  produces a margin that lands a few units in the last place off the
  requirement, and a strict comparison then fails a compliant sheet on
  one machine and passes it on another.
- Quoting a typical value with no minimum and maximum. The typical is
  the one number a design must not rely on; the guaranteed edges are
  what the worst case is built from.
- Publishing a number with a placeholder unit. A value carrying a TBD
  dimension reads as specified and cannot be used, and it will survive
  every review that only checks whether the field is filled in.
- Checking only the upper end of a two-sided rating. An undervoltage or
  a negative excursion is as much outside the envelope as an
  overvoltage, and a sheet that defines only the maximum has published
  half a rating.

## Behavior contract (gate 3)

The section check, characteristic ordering and content validation,
rating validation, envelope containment, derating-margin computation
with tolerant comparison, worst-margin selection and the finding
assembly are exercised by the gate 3 contract test:
scripts/test_e2040_device_data_sheet_data_item.py against
scripts/e2040_device_data_sheet_data_item_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_data_sheet_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
