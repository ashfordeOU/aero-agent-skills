---
name: q7080-machine-qualification
description: "Determine the qualification status of a metallic powder bed fusion machine under ECSS-Q-ST-70-80C: grade every calibrated item against its own interval and count the days overdue, compare the chamber environment — residual oxygen, dew point and leak rate — against its control limits, compute witness-build capability from the specimen mean, sample spread and a capability index, and close with a verdict tied to the machine, material, layer-thickness and parameter-set envelope it was earned on. Use when a machine enters service, returns from maintenance, or is proposed for work outside its envelope. Trigger: ecss, q-st-70-80c, pbf-machine-qualification, pbf-calibration-interval-status, pbf-chamber-environment-limits, pbf-witness-build-capability-index, pbf-qualification-envelope."
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
  tags: [ecss, q-st-70-80c-powder-bed-fusion, q-st-70-80c, q7080-machine-qualification, pbf-machine-qualification, pbf-calibration-interval-status, pbf-chamber-environment-limits, pbf-witness-build-capability-index, pbf-qualification-envelope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Powder Bed Fusion — Machine Qualification (space-systems/ecss/q7080-machine-qualification)

Use when the task is the machine qualification clause of ECSS-Q-ST-70-80C:
whether a machine may build flight hardware, what its qualification actually
covers, and what a proposed change to material, layer thickness or parameter
set costs.

## Domain quick reference

- A machine is never qualified on its own. It is qualified for a combination —
  this machine, this material, this layer thickness, this parameter set — and
  a verdict quoted without that combination attached cannot be checked by
  anyone reading it later.
- Three things stand behind the verdict and all three have to hold at once:
  every measuring and energy-delivery item behind the process is in
  calibration, the chamber environment is inside its control limits, and a
  witness build demonstrates capability against the property the design relies
  on.
- Calibration has three states, not two. An item past its interval is overdue
  and blocks the qualification outright. An item inside its warning window is
  due: it does not invalidate today's build, but it limits the verdict and
  puts a date on it.
- The chamber environment is what separates a sound melt from an oxidised one.
  Residual oxygen, dew point and the chamber leak rate are graded together,
  because a leak that is small enough to pass on its own will still pull the
  oxygen up over a long build.
- Capability is a distribution, not a pass mark. A witness build whose mean
  sits comfortably above the specification but scatters widely is not capable,
  and only an index built from both the mean margin and the sample spread says
  so. A one-sided property such as density uses the nearer bound only.
- The index carries two thresholds. Below the required index the machine is
  not qualified. Between the required and the preferred index it is qualified
  with a limitation, which is the honest state for a machine that passes but
  has no room.
- A change to the envelope is priced, not argued. A different machine or
  material restarts the qualification; a layer thickness move outside its
  tolerance restarts it too, because the melt pool and the fusion depth both
  scale with it; a parameter set change inside the same material and thickness
  is a delta qualification.

## Workflow

1. Write the envelope first: machine, material, layer thickness, parameter
   set. Everything that follows is a statement about that combination.
2. Grade the calibration schedule item by item, keeping the days remaining and
   the days overdue, and separate the overdue items from those inside their
   warning window.
3. Grade the chamber environment against every control limit at once, and name
   each parameter that fell outside.
4. Compute the witness build statistics — count, mean, sample spread, extremes
   — and reject a specimen set that is too small to support them.
5. Compute the capability index against the specification actually imposed,
   one-sided or two-sided, and compare it with the required and preferred
   thresholds.
6. Close with the verdict: blocked by an overdue calibration, a chamber breach
   or a shortfall in capability; limited by a calibration falling due or an
   index with no room; clean otherwise. Attach the envelope to the verdict.
7. Where a change is proposed, price it against the baseline envelope before
   anything is built.

## Pitfalls

- Quoting a machine as qualified without its envelope. The next job runs a
  different material or a coarser layer, the qualification is silently assumed
  to carry, and the evidence behind it never covered that combination.
- Reading a comfortable mean as capability. A density mean well above the
  minimum with a wide scatter puts individual specimens under it, and the
  index is the only statistic that notices.
- Comparing a capability index with its requirement by bare arithmetic. The
  index is a quotient of a difference by a standard deviation, so a build that
  lands exactly on the requirement can fall a few units in the last place
  below it; the comparison absorbs that representation error while the
  requirement stays untouched.
- Treating an item inside its warning window as an item out of calibration.
  It blocks nothing today, and downgrading the verdict to not-qualified for it
  burns a machine that is fit to run.
- Grading residual oxygen without the leak rate. A chamber that meets the
  oxygen limit at the start of a long build and leaks steadily will not meet
  it at the end, and a single reading taken at the start cannot show that.
- Letting a parameter set change ride on the existing qualification because
  the material and the machine are the same. The parameter set is what puts
  the energy in; it earns a delta qualification, never a silent carry-over.

## Behavior contract (gate 3)

The calibration grading, chamber environment limits, witness build statistics,
capability index, qualification envelope, envelope change pricing and the
final verdict are exercised by the gate 3 contract test:
scripts/test_q7080_machine_qualification.py against
scripts/q7080_machine_qualification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7080_machine_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
