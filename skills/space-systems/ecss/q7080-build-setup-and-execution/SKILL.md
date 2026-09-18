---
name: q7080-build-setup-and-execution
description: "Execute a powder-bed build under control, from platform preparation to the last layer. Use when a job is about to start, or has finished and needs a disposition: grade every start-up check against its declared limit, block the start when one is out of limit or simply never recorded, then walk the monitored channels layer by layer, separate a single layer outside a band from a run of consecutive layers that means the process left control, measure how much of the build was monitored at all, count the recoater interruptions against their allowance, and return blocked, aborted, complete with concession or complete. Trigger: ecss, q-st-70-80-additive-manufacturing, am-build-startup-checks, am-build-platform-preparation, am-in-process-build-monitoring, am-layer-excursion-run, am-build-disposition."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-build-setup-and-execution, am-build-startup-checks, am-build-platform-preparation, am-in-process-build-monitoring, am-layer-excursion-run, am-build-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Build Set-up and Execution (space-systems/ecss/q7080-build-setup-and-execution)

Use when the task is the process clause of ECSS-Q-ST-70-80 that governs
running a build: preparing the platform, passing the start-up checks that
gate the first layer, monitoring the job while it runs, and giving the
finished build a disposition.

## Domain quick reference

- The start-up checks are a gate, not a log. Platform flatness, preheat,
  chamber atmosphere and feedstock condition are the conditions the
  qualified process assumes, so the first layer is the last moment they
  can be fixed cheaply.
- An unrecorded check and an out-of-limit check block the start for the
  same reason. Neither shows the machine was ready, and a blank field
  read as nominal is the cheapest way to lose a build.
- A build that should not have started is dispositioned on that. Grading
  its monitoring data afterwards answers a different question and can
  make a blocked start look like an acceptable run.
- Excursion duration carries the information, not excursion count. One
  layer outside the oxygen band is a local event in a build of
  thousands; the same excursion sustained over consecutive layers is a
  region of material built under a process nobody qualified.
- Unmonitored layers are unevidenced layers. A channel sampled on a
  tenth of the build cannot support a statement about the build, which
  is why coverage is graded separately from the values.
- Discrete events count differently from continuous channels. Recoater
  interruptions and restarts are graded against an allowance for the
  job, because each one is a disturbance to the powder bed rather than a
  reading outside a band.
- Monitored values arrive through sensor scaling and logger rounding, so
  a reading exactly on a limit can land a few units in the last place
  outside it. The comparison absorbs that; the limit is never moved.

## Workflow

1. Validate every declared limit before grading anything against it. An
   inverted limit pair or a limit set with neither bound is an input
   error, not a permissive check.
2. Grade the start-up checklist: each required check either carries a
   recorded value inside its limits, or it blocks. Refuse a recorded
   check the requirements never declared.
3. Stop there when the start is blocked. Return the blocking list and no
   monitoring assessment at all.
4. For each monitored channel, grade every layer sample against the
   channel limits, refusing duplicate or non-positive layer indices.
5. Measure the longest run of consecutive layers in excursion, and abort
   the build when that run reaches the declared threshold.
6. Measure monitoring coverage against the declared layer count, and
   raise a finding when a channel sampled less of the build than
   required. A sample above the declared build height is an input error.
7. Grade the discrete event counts against their allowances.
8. Give the disposition: start blocked, aborted on a sustained
   excursion, complete with concession when isolated excursions, sparse
   monitoring or an event allowance was exceeded, complete otherwise.

## Pitfalls

- Filling a missed start-up check from the previous build's record. The
  platform was reworked between them, which is the reason the check is
  repeated every time.
- Counting excursions instead of measuring their runs. Ten isolated
  layers scattered through a build and ten consecutive ones are
  different material conditions and different dispositions.
- Accepting a channel that monitored the first hundred layers and
  stopped. The coverage number is what exposes it; the values within the
  monitored region all look fine.
- Dispositioning a build on its monitoring when the start-up gate was
  already broken. The evidence being graded is downstream of a condition
  that was never met.
- Reading a recoater interruption as an equipment note rather than a
  process event. Each one disturbs the bed the next layer is spread on,
  which is why it has an allowance.

## Behavior contract (gate 3)

The limit validation, start-up gating, layer-excursion grading with its
consecutive-run measure, monitoring coverage, discrete event allowances
and the final disposition are exercised by the gate 3 contract test:
scripts/test_q7080_build_setup_and_execution.py against
scripts/q7080_build_setup_and_execution_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_build_setup_and_execution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
