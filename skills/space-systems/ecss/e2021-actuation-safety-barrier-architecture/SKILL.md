---
name: e2021-actuation-safety-barrier-architecture
description: "Verify the three-barrier safety architecture of an actuation chain against ECSS-E-ST-20-21C clause 5.2.1. Use when the task is proving that arm, select and fire each sit behind a separate inhibit that has to be deliberately removed before a deployment device can activate: categorize every barrier by function, by the element whose release removes it and by the command domain that can order that release, detect a relay or a domain shared between two barriers, count the independent elements an inadvertent activation must defeat, and report the depth that survives one credible failure. Trigger: ecss, e-st-20-21-actuation-scope, actuation-safety-barrier-architecture, arm-select-fire-barriers, barrier-release-independence, inadvertent-activation-depth, energy-isolating-barrier, deployment-device-inhibit."
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
  tags: [ecss, e-st-20-21-actuation-scope, e2021-actuation-safety-barrier-architecture, arm-select-fire-barriers, barrier-release-independence, inadvertent-activation-depth, energy-isolating-barrier, deployment-device-inhibit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuation Electronics — Actuation Safety Barrier Architecture (space-systems/ecss/e2021-actuation-safety-barrier-architecture)

Use when the task is the barrier architecture of ECSS-E-ST-20-21C
clause 5.2.1 -- establishing that three independent barriers, arm,
select and fire, all stand between the spacecraft and a deployment
device, and that every one of them has to be deliberately released
before the device can activate.

## Domain quick reference

- The clause asks for three barriers, but the engineering content is
  independence, not arithmetic. Three inhibits that all fall to one
  relay, one command domain or one power feed are one barrier wearing
  three names, and a design review that counts the names passes an
  architecture that a single failure opens.
- The three functions are distinct jobs. Arm makes the firing energy
  available, select routes it to one device out of the set, and fire
  releases it for the pulse. An architecture that covers a function
  twice and another not at all has no real depth, which is why a
  duplicate function is rejected rather than counted.
- Independence has two axes and both are checked. The release element
  is the hardware whose state change removes the barrier; the command
  domain is the authority that can order that change. Two barriers
  released by one element fall to one hardware failure, and two
  barriers ordered from one domain fall to one erroneous command
  sequence, even when the hardware is separate.
- Activation depth is the count of distinct elements an inadvertent
  activation would have to defeat, so a barrier that sits released in
  its default state contributes nothing to it. Depth is what the
  requirement is really about, and it is never larger than the barrier
  count and often smaller.
- Not every barrier is worth the same. A barrier that breaks the firing
  energy path -- a series power switch, a relay contact, a safe and arm
  device, a connector shunt -- survives a software fault that a logic
  enable does not, so an architecture whose three barriers are all
  command-side is reported even when its depth reaches three.
- The useful output is not the verdict alone but the worst single
  element: the one whose loss removes the most holding barriers. That
  is the element the failure analysis, the inspection and the ground
  procedure all have to be built around.

## Workflow

1. Declare every barrier with its function, its release element, its
   command domain, its isolation kind and its default state. Reject an
   unknown function, an unknown isolation kind, a duplicate identifier
   and a function declared twice, because each of those silently
   inflates the depth the architecture appears to carry.
2. Categorize the set: which of arm, select and fire are covered and
   which are absent. An absent function is a gap in the architecture,
   not merely a missing record.
3. Group the barriers by release element and by command domain, and
   raise a finding for every element or domain that appears more than
   once. Name the barriers involved so the reviewer can see which pair
   collapsed.
4. Count the activation depth over the barriers that are inhibited by
   default, then remove the worst single element and report the depth
   that remains. Report the element itself.
5. Check that at least one barrier isolates the firing energy rather
   than only withholding a command word, and raise a finding when none
   does.
6. Close with a verdict: compliant only when all three functions are
   covered, no independence finding stands, the depth reaches the
   required three and the energy path is broken somewhere.

## Pitfalls

- Counting barriers instead of elements. Three declared inhibits driven
  from one relay board give an activation depth of one, and the report
  that quotes the barrier count reads as compliant while the design is
  a single-failure activation away from a deployment.
- Treating separate hardware as sufficient independence. Two relays on
  two boards are still one barrier if one command domain can order both
  of them released; the command axis has to be checked alongside the
  hardware axis, never instead of it.
- Letting a barrier sit released in its default state and still counting
  it. A barrier only holds while it is inhibited, so a released one adds
  a name to the architecture and nothing to the depth.
- Accepting an architecture built entirely from logic enables. Depth
  three against a command fault is depth zero against a processor that
  writes the enable word by accident, which is exactly why one barrier
  has to break the energy path.
- Reporting the verdict without the worst single element. The verdict
  tells a reviewer that something is wrong; the element tells the
  failure analysis, the inspection plan and the ground procedure where
  to go.

## Behavior contract (gate 3)

Barrier categorization, function coverage, shared release element and
shared command domain detection, activation depth, depth after one
failure, energy isolation and the compliance verdict are exercised by
the gate 3 contract test:
scripts/test_e2021_actuation_safety_barrier_architecture.py against
scripts/e2021_actuation_safety_barrier_architecture_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_actuation_safety_barrier_architecture.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
