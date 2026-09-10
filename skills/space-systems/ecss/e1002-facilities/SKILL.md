---
name: e1002-facilities
description: "Use when qualifying an integration and test facility or a test
  tool before it is used on a flight article under ECSS-E-ST-10-02C clause
  5.2.6.6: map the planned test method to the facility type it requires,
  verify the facility's operating envelope covers the test's required range,
  confirm the facility's quality accreditation is a live Q-ST-20-07
  test-centre accreditation, confirm calibration currency for the facility
  and for any measurement instrument, confirm a test tool's interfaces fit
  the article, check a qualification-plan record for missing fields, and
  roll many facility/tool qualification results up into a single AIT
  readiness gate. Trigger: ecss, e-st-10-02c, facilities, test tools,
  facility qualification, q-st-20-07, test-centre quality, calibration,
  capability envelope, ait readiness."
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
  tags: [ecss, e-st-10-02c, facilities, test-tools, q-st-20-07, calibration, ait-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Integration and Test Facility Qualification (space-systems/ecss/e1002-facilities)

Use when the task is qualifying an integration and test facility or a test
tool per ECSS-E-ST-10-02C clause 5.2.6.6 -- confirming a facility or tool
is fit to host a specific test on a flight article before that test is
run, with the facility's quality standing tied to the ECSS-Q-ST-20-07
test-centre quality framework.

## Domain quick reference

- A test method (thermal-vacuum, thermal-balance, sine/random vibration,
  acoustic, EMC emissions/susceptibility, mass-properties, alignment,
  cleanliness inspection) has exactly one facility type that can host it.
  A method with no mapped facility type is not recognized and must be
  rejected before qualification proceeds -- it is not defaulted to the
  nearest-looking facility.
- A facility is qualified only when three independent checks all pass:
  its operating envelope covers the test's required range end to end
  (partial overlap is a fail, not a partial pass), its quality
  accreditation is currently "accredited" and specifically against
  Q-ST-20-07 (a live accreditation against a different quality standard,
  e.g. a generic lab-competence standard, does not satisfy this clause),
  and its calibration is current at the day the test is run. All three
  findings are collected, not short-circuited on the first failure, so a
  facility with multiple defects reports all of them at once.
- A test tool (mechanical/electrical/software GSE, measurement
  instrument, handling equipment) is qualified when its interfaces are a
  superset of what the article requires -- a tool missing even one
  required interface is incompatible, not "mostly compatible." Only a
  measurement-instrument tool additionally carries a calibration-currency
  requirement; other tool types are interface-checked only.
- Calibration currency is a day-count comparison: an asset stays current
  through the exact day its interval elapses (day count equal to the
  interval is still current) and expires the day after. A calibration
  record whose "current day" precedes its own last-calibration day is
  invalid input, not an edge case to silently accept.
- A qualification-plan record is complete only when it carries every one
  of: facility_id, requirement_ref, capability_check, calibration_check,
  accreditation_check, qualification_date. A record missing any of these
  cannot support a qualification decision, regardless of what the
  present fields say.
- AIT readiness is a roll-up across every facility and tool qualification
  result feeding a test campaign: the gate opens only when every result
  is "qualified." One blocking (not-qualified) result holds the whole
  gate, and the roll-up reports how many results are blocking so the
  campaign owner knows the size of the punch list.

## Workflow

1. For each planned test, map its test method to the required facility
   type. Reject a test method that has no mapping rather than guessing a
   facility type for it.
2. For the candidate facility, check its capability envelope against the
   test's required range, its accreditation status and standard against
   the "accredited" + Q-ST-20-07 requirement, and its calibration
   currency against the day the test is scheduled. Collect every finding
   the facility produces; do not stop at the first one.
3. For each test tool associated with the test, check its interfaces
   against the article's required interface set, and -- if the tool is a
   measurement instrument -- its calibration currency for the same
   scheduled day.
4. Before relying on a qualification-plan record, verify it carries all
   six required fields; treat a record with any field missing as
   insufficient to support a go decision.
5. Roll every facility and tool qualification result for the campaign up
   into a single AIT readiness verdict. Do not declare readiness while
   any individual result remains not-qualified.
6. Re-run the qualification checks whenever a facility's accreditation,
   calibration, or capability envelope changes, or whenever a tool's
   interface set or calibration changes -- qualification is a
   point-in-time result, not a permanent attribute of the asset.

## Pitfalls

- Treating a facility whose envelope only partially overlaps the
  required range as usable "for most of the test" -- clause 5.2.6.6
  qualification requires the envelope to cover the full required range,
  not merely intersect it.
- Accepting a facility's accreditation against a different quality
  standard as satisfying the Q-ST-20-07 test-centre requirement --
  accreditation is standard-specific, and a lab-competence certificate
  against an unrelated standard does not substitute for it.
- Stopping the facility check at the first failing item -- a facility can
  simultaneously fail envelope, accreditation, and calibration, and
  reporting only the first hides the rest of the punch list from whoever
  has to fix it.
- Skipping the calibration check for a test tool that is not a
  measurement instrument -- correct, but only for that tool type; a
  measurement instrument still needs the same currency check the
  facility gets, and skipping it there is a miss, not a shortcut.
- Declaring AIT readiness from a partial set of qualification results
  (e.g. only the facilities, not the tools) -- the roll-up is only
  meaningful over the complete set of assets feeding the campaign.

## Behavior contract (gate 3)

The method-to-facility mapping, capability-envelope, calibration-currency,
accreditation, tool-interface, plan-completeness, and readiness roll-up
logic is exercised by the gate 3 contract test:
scripts/test_e1002_facilities.py against scripts/e1002_facilities_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1002_facilities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
