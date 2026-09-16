---
name: e2008-angular-performance-test-purpose
description: "Use when a slewing or sun-offset mission needs array power at an incidence angle nobody has measured. Determine what an angular performance test on a photovoltaic assembly must deliver under ECSS-E-ST-20-08C clause 6.4.3.19.1: project the normal-incidence output onto the sun incidence angle an off-pointing mission actually flies, separate the free cosine term from the angular response factor coverglass reflection erodes, derive the worst-case off-pointing power and its margin, and hold the planned angle envelope against the attitude the declared drivers impose. Trigger: ecss, e-st-20-08c-clause-6-4-3-19-1, solar-array-angular-performance-purpose, sun-incidence-angle-response, off-pointing-array-power-margin, assembly-cosine-departure-factor, angular-test-envelope-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-angular-performance-test-purpose, solar-array-angular-performance-purpose, sun-incidence-angle-response, off-pointing-array-power-margin, assembly-cosine-departure-factor, angular-test-envelope-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Angular Performance Test Purpose (space-systems/ecss/e2008-angular-performance-test-purpose)

Use when the task is to state and defend why the output of a
photovoltaic assembly is measured against sun incidence angle under
ECSS-E-ST-20-08C clause 6.4.3.19.1 -- which off-pointing attitudes make
the number necessary, what the assembly is expected to deliver at the
worst of them, and whether the planned sweep reaches that attitude at
all.

## Domain quick reference

- Every other electrical test on the assembly is taken at normal
  incidence, because that is the condition the datasheet and the
  acceptance test share. A mission that slews across a target, holds a
  sun offset for thermal control, drifts through a seasonal beta spread
  or tumbles in safe mode never sees that condition at the moment power
  matters most.
- Two effects are stacked in the angular number and only one is free.
  The cosine projection is geometry, known before any hardware exists.
  The angular response factor -- what the coverglass reflection, the
  cell stack and the cell edge shadowing leave of the projected value
  -- is the term that has to be measured, and it is the whole reason
  the clause exists.
- An assembly that followed the cosine exactly would need no test. The
  departure from it is small near the normal and grows as the incidence
  angle opens, which is why the worst-case attitude, not the nominal
  one, sets what the test has to reach.
- The worst-case off-pointing power is the product of three terms:
  normal-incidence output, the cosine of the worst-case angle, and the
  response factor there. A power budget that drops any one of them is
  quoting a different assembly.
- A response factor above unity is not a good assembly, it is a
  measurement error or a mislabelled reference output, because the
  projection is already the ceiling the geometry allows.
- Beyond about eighty-five degrees the illuminated area, the fixture
  shadowing and the reference cell all become the dominant error terms,
  so a sweep planned past that ceiling produces numbers nobody can
  defend rather than extra coverage.
- A declared driver with no sweep planned is a distinct outcome from a
  sweep that stops short of the attitude that driver imposes, and both
  differ from an adequate sweep that simply shows a shortfall.

## Workflow

1. Validate the characterisation policy first: off-pointing trigger,
   credible-angle ceiling, response-factor floor and margin floor. A
   ceiling at or below the trigger is refused rather than used.
2. Group the declared off-pointing drivers, rejecting an unrecognised
   one rather than ignoring it, and map each to the quantity the
   angular characterisation feeds it. Append the shared objective
   whenever any driver is present.
3. Take the worst-case incidence angle from the declared attitudes, not
   from the nominal pointing, because that is the angle the power
   budget is written at.
4. Derive the cosine projection at that angle, the expected output once
   the response factor is applied, and the margin against the required
   power. These are reported whatever the verdict, because they are
   what the number was wanted for.
5. Decide whether the characterisation is required at all: a declared
   driver present and a worst-case angle at or above the trigger. An
   angle landing exactly on the trigger earns the sweep; the comparison
   tolerance absorbs representation error and the trigger does not move.
6. When it is required and a sweep is planned, check the sweep reaches
   the worst-case angle, stays inside the credible-angle ceiling, and
   that the declared response factor sits in a band the cosine
   projection allows.
7. Close on one verdict: characterisation not required, measurement not
   planned, measurement inadequate, off-pointing power shortfall, or
   angular performance characterised -- reporting every inadequacy
   found, not only the first.

## Pitfalls

- Quoting the cosine alone as the angular performance. It is the term
  that needs no test; the response factor is the one the clause asks
  for, and at a wide angle it is where the power goes.
- Planning the sweep around the nominal attitude. The budget is written
  at the worst case, and a sweep that stops at the nominal leaves that
  point to an extrapolation of a curve that is not a cosine.
- Sweeping to ninety degrees for completeness. The assembly is edge on
  there, the fixture shadows the article and the reference cell reads
  its own error, so the extra points are noise carrying a decimal
  point.
- Accepting a response factor above one. The cosine projection is the
  geometric ceiling; a factor over unity means the normal-incidence
  reference, not the assembly, is what moved.
- Reporting an adequate sweep as a pass. Coverage and sufficiency are
  separate outcomes: a sweep can reach every angle it should and still
  show the assembly under the requirement at the worst-case attitude.
- Treating a declared driver as sufficient reason to sweep. A mission
  whose worst-case incidence stays under the trigger buys nothing from
  the angular test that the normal-incidence measurement did not
  already give.

## Behavior contract (gate 3)

The policy validation, cosine projection, angular response factor and
departure fraction, output at incidence, worst-case angle selection,
power margin, envelope coverage, response-factor physicality, the
driver inventory and objective mapping, and the purpose verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_angular_performance_test_purpose.py against
scripts/e2008_angular_performance_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_angular_performance_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
