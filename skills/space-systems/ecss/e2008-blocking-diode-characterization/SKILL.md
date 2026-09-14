---
name: e2008-blocking-diode-characterization
description: "Assess whether a qualification programme is degrading a blocking diode by reading the electrical characterizations placed between its tests under ECSS-E-ST-20-08C clause 12.6.3: confirm every visit carries the whole parameter set, the declared device count and the baseline reference conditions, convert each reading into a degradation fraction that is positive whichever way the number moved, separate the step one test added from the cumulative the programme has spent, rank the steps by the share of their own limit they used, and name the test that cost the most. Use when a blocking diode degradation trajectory is written or audited. Trigger: ecss, e-st-20-08c-clause-12-6-3, blocking-diode-degradation-trajectory, blocking-diode-inter-test-characterization, blocking-diode-step-versus-cumulative-budget, blocking-diode-reference-condition-match, blocking-diode-degradation-attribution."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-blocking-diode-characterization, blocking-diode-degradation-trajectory, blocking-diode-inter-test-characterization, blocking-diode-step-versus-cumulative-budget, blocking-diode-reference-condition-match, blocking-diode-degradation-attribution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Characterization (space-systems/ecss/e2008-blocking-diode-characterization)

Use when the task is clause 12.6.3 of ECSS-E-ST-20-08C -- the
electrical measurements placed between the tests of a blocking diode
qualification. This clause describes no environment of its own. It
describes the instrument, because a blocking diode almost never fails
a test outright: it comes back working and slightly different, and the
only thing that sees that is the same measurement repeated under the
same conditions, often enough to leave a trajectory rather than a
before and an after.

## Domain quick reference

- Four parameters carry the state of the part and they do not move the
  same way. Forward voltage, reverse leakage and series resistance all
  rise as the diode degrades; the reverse blocking voltage falls. A
  signed difference therefore says nothing on its own, so each reading
  is converted into a degradation fraction that is positive whenever
  the part got worse.
- Two budgets are read off one trajectory and they answer different
  questions. The step is measured against the visit before it and says
  what a single test did to the part it was handed. The cumulative is
  measured against the baseline and says what the programme has spent.
- The two are not the sum of one another. Each step starts from a
  moving value, so a compounding trajectory always leaves the
  cumulative above the sum of its own steps, and a sequence can sit
  inside every step limit and still run out of budget.
- Steps in different parameters cannot be ranked as raw fractions. A
  leakage that grows a quarter and a forward voltage that moves half a
  percent are not comparable numbers, so each step is divided by the
  limit that binds it and the worst share is what names the costly
  test.
- Leakage needs its own limits. A budget tight enough to be meaningful
  for forward voltage refuses every honest leakage trajectory, which
  is why the policy carries per-parameter overrides rather than one
  number.
- The visits are only comparable if they reproduced the baseline
  conditions: junction temperature to an absolute offset, test current
  and reverse bias to a relative one. A leakage read at a different
  bias is a different measurement, not a drifted one.
- The population has to be the same population. A visit that measured
  fewer devices than were declared is not a later point on the same
  trajectory, whatever its numbers say.
- A trajectory that recovers is not good news. A parameter that
  improves beyond measurement noise means the conditions drifted, the
  population changed or the instrument moved, so it is raised before
  any budget is believed.

## Workflow

1. Validate the tracking policy first: visit minimum, step limit,
   cumulative budget, recovery tolerance, condition tolerances and the
   per-parameter overrides. A step limit sitting above the cumulative
   budget can never bind and is refused rather than used.
2. Confirm the sequence is long enough to hold a trajectory and that
   every visit carries the whole parameter set. An incomplete sequence
   is reported as such and nothing downstream is computed from it.
3. Confirm every visit measured the declared device count, so the
   trajectory follows one population.
4. Take the condition offsets of every visit against the baseline and
   decide comparability before any drift is read as degradation.
5. Convert each parameter series into step degradations against the
   preceding visit and one cumulative degradation against the
   baseline, using the sense that makes a worse part read positive.
6. Raise any step that improved beyond the recovery tolerance, since
   that points at the measurement rather than the part.
7. Grade each step against its own limit and each total against its
   own budget, keeping the per-parameter overrides in force.
8. Divide every step by its limit and keep the largest share, then
   attribute it to the test that preceded that visit.
9. Close on one verdict: sequence incomplete, population broken,
   conditions incomparable, trajectory non-monotonic, cumulative
   budget exceeded, step limit exceeded, or degradation within budget
   -- reporting every departure found, not only the first.

## Pitfalls

- Reading degradation as a signed difference. The blocking voltage
  degrades downwards, so a raw subtraction grades it backwards and a
  falling part looks like an improving one.
- Adding the steps to get the cumulative. Each step is read against a
  different starting value, and the sum understates a compounding
  trajectory every time.
- Ranking steps across parameters by their raw fraction. Leakage moves
  in tens of percent where forward voltage moves in tenths, so the
  largest number is almost never the most expensive step.
- Grading leakage against the general budget. One limit for all four
  parameters either refuses honest leakage data or lets a forward
  voltage drift through untouched.
- Comparing visits taken at different bias or current. The reading did
  not drift, it was a different measurement, and the difference
  between them is an artefact rather than degradation.
- Letting the device count move between visits. A shrinking population
  makes an average improve on its own, and the trajectory then reports
  the sampling instead of the hardware.
- Filing a recovery as a good result. A parameter cannot heal in a
  qualification sequence, so an improvement is evidence about the
  measurement and it is raised before the budgets are read.

## Behavior contract (gate 3)

The policy validation and per-parameter overrides, the parameter
senses, the degradation fraction, the parameter series, the step and
cumulative degradations, the reference-condition offsets and
comparability, the worst-step ranking with its attribution, the
population and completeness checks and the degradation verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_characterization.py against
scripts/e2008_blocking_diode_characterization_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_characterization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
