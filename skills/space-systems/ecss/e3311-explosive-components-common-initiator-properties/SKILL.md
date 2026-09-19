---
name: e3311-explosive-components-common-initiator-properties
description: "Determine whether an initiator, cartridge, detonator or packaged charge meets the common explosive-component property requirements of ECSS-E-ST-33-11C clauses 4.11.1 and 4.11.2, table 4-3. Use when the task is confirming the qualified operating and storage temperature ranges contain the mission ranges with margin at both ends reported separately, the seal leak rate sits under its limit, insulation resistance is quoted with the voltage it was measured at, the declared service life covers storage plus mission rather than mission alone, autoignition stands clear of the maximum operating temperature, and function time is graded only against the kinds that carry it. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-component-common-properties, initiator-cartridge-detonator-properties, explosive-component-seal-leak-rate, explosive-component-service-life, explosive-autoignition-margin."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-explosive-components-common-initiator-properties, explosive-component-common-properties, initiator-cartridge-detonator-properties, explosive-component-seal-leak-rate, explosive-component-service-life, explosive-autoignition-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Common Component Properties (space-systems/ecss/e3311-explosive-components-common-initiator-properties)

Use when the task is the common property table of ECSS-E-ST-33-11C
clauses 4.11.1 and 4.11.2 -- the part of the component requirements
that does not care what the device is. An initiator, a cartridge, a
detonator and a packaged charge do different jobs and all four have to
survive the same environment, hold the same seal and last the same
calendar.

## Domain quick reference

- The common set is deliberately kind-agnostic, with one exception.
  Function time belongs to the device that has a firing circuit, so a
  packaged charge inherits the timing of whatever initiates it and
  does not carry the property itself. Declaring it against a charge is
  an error rather than extra evidence.
- A temperature requirement is a containment question, not a
  comparison of two numbers. The qualified range has to extend past
  the mission range by the declared margin at both ends, and the two
  ends are reported separately because a qualification that is
  generous hot and tight cold is the routine outcome of a test
  campaign built around a hot-case worry.
- The margins on operating and storage temperature are separate
  policy numbers. Storage is longer and less controlled, which is why
  it is usually the wider range and the smaller margin.
- Seal leak rate is the one property where larger is worse, so it is
  the one most often graded the wrong way round when a reviewer is
  working quickly down a table.
- Insulation resistance is two numbers. A resistance quoted with no
  test voltage does not demonstrate the requirement, because the same
  specimen reads very differently at fifty volts and five hundred.
- Service life has to cover storage plus mission. An item that will
  sit on a shelf for five years and then fly for seven needs twelve,
  and the life figure that passes against the mission alone is the one
  that expires in the warehouse.
- Autoignition is a separation rather than a limit. The quantity that
  matters is the gap between the autoignition temperature and the
  maximum the component will actually see, which is why both are
  required and neither is useful alone.
- A missing declaration is rejected rather than treated as zero or as
  a pass. An undeclared property means nobody measured it.

## Workflow

1. Take the component kind first and resolve which of the common
   properties apply to it, because the grading set changes and a
   property declared outside that set is an error.
2. Reject a component that omits an applicable property before
   grading anything, so a silent gap cannot read as a pass.
3. Grade the operating envelope: cold margin as required low minus
   qualified low, hot margin as qualified high minus required high,
   each against the operating margin, and report them separately.
4. Repeat for the storage envelope against its own margin.
5. Grade the seal leak rate as an upper limit and the insulation
   resistance as a lower limit paired with its test voltage.
6. Add storage years to mission years and grade the declared life
   against that sum.
7. Subtract the maximum operating temperature from the autoignition
   temperature and grade the separation against its margin.
8. Grade function time where it applies, then roll the per-property
   verdicts into the component verdict and, for a set, into a
   per-component roll-up that keeps the part name on every finding.

## Pitfalls

- Grading a temperature range by asking whether the qualification
  covers the mission. It usually does; the requirement is that it
  covers it with margin, and the answer changes at one end only.
- Reporting one temperature margin. The cold end and the hot end fail
  for different reasons and at different times, and a single combined
  figure hides whichever of them is actually tight.
- Reusing the operating margin on the storage range. They are separate
  policy numbers against separate qualified ranges, and swapping them
  silently moves the bar in both directions.
- Grading seal leak rate as a lower limit. It is the only upper-limit
  property sitting in a table of lower limits, and it reads the same
  as the others at a glance.
- Accepting an insulation resistance with no test voltage. A
  comfortable reading taken at a low voltage is exactly the reading
  that hides a weak insulation path.
- Sizing service life against the mission. Storage is the longer half
  for most flight explosive components, and the life that fails is the
  one nobody added the shelf time to.
- Comparing an autoignition temperature with an ambient. The
  separation is against the maximum the component sees in operation,
  which is a hotter number and often sits well inside the margin.
- Treating a missing property as a zero or as a pass. Unknown is
  neither; it is a rejected declaration.
- Failing a component whose margin lands a hair under its requirement
  in the last bits of a float. The requirement is untouched; the
  comparison absorbs the representation error.

## Behavior contract (gate 3)

The per-kind applicability map, the two-ended temperature containment
checks, the seal, insulation, service-life, autoignition and
function-time gradings, the rejection of missing and inapplicable
declarations, and the component and set verdicts are exercised by the
gate 3 contract test:
scripts/test_e3311_explosive_components_common_initiator_properties.py
against
scripts/e3311_explosive_components_common_initiator_properties_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3311_explosive_components_common_initiator_properties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
