---
name: q7045-test-validity-checks
description: "Assess whether a completed mechanical test measured the material or measured the fixture, and dispose of the lot on the valid specimens only. Use when specimens under ECSS-Q-ST-70-45 have been pulled to fracture and the results are about to be accepted: place each fracture along the gauge length, separate a break that owes the displaced-gauge treatment from one that fell outside the gauge length entirely, take the fracture appearance as a named mode and refuse an unnamed one, sweep the run for a slipped extensometer, a machine stop, a rate or soak excursion and a force step before maximum force. Trigger: ecss, q-st-70-45-mechanical-testing, tensile-test-validity-verdict, tensile-fracture-location-acceptance, tensile-fracture-mode-acceptance, tensile-test-anomaly-screening, tensile-lot-repeat-disposition."
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
  tags: [ecss, q-st-70-45-mechanical-testing, q7045-test-validity-checks, tensile-test-validity-verdict, tensile-fracture-location-acceptance, tensile-fracture-mode-acceptance, tensile-test-anomaly-screening, tensile-lot-repeat-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing — Test Validity Checks (space-systems/ecss/q7045-test-validity-checks)

Use when the task is the acceptance step after a mechanical test under
ECSS-Q-ST-70-45: the specimens are broken and the numbers exist, and
the question is which of those numbers are properties of the material
and which are artefacts of where the specimen broke, how it broke, or
what happened to the machine while it was breaking.

## Domain quick reference

- Where the specimen broke decides two different things. Outside the
  gauge length the result is not a result at all; inside it but well off
  centre the strength still stands and only the elongation is affected,
  because the necking region is no longer centred between the gauge
  marks and the measurement owes the displaced-gauge treatment.
- The fracture appearance is evidence about what governed. A cup and
  cone or a slant shear inside the parallel length says the material
  failed; a break in the grips, at the shoulder, at an extensometer
  knife edge or at a gauge mark says the fixture did, and no strength
  reported from it is the material's.
- An unnamed appearance is not a benign one. An observer who cannot
  name the mode has not looked, and defaulting an unrecognised
  description to acceptable is how fixture failures enter a data set.
- A falling force is only an anomaly before maximum force. After it, a
  falling force is the specimen necking and is the expected shape; a
  step down while the force is still rising is a slipping grip or a
  slipping extensometer.
- Rate and temperature excursions invalidate on their own. Both move
  the measured strength of most metals, so a run outside its band has
  measured the right material under the wrong conditions.
- A lot is disposed of on its valid specimens only. Counting an invalid
  specimen towards the required number is the single most common way a
  short data set is made to look complete.

## Workflow

1. Take the fracture offset from mid-gauge as a fraction of the gauge
   length, and split it three ways: central, outer but inside, and
   outside the gauge length altogether.
2. Match the fracture appearance against the named modes and refuse a
   description that is not one of them rather than assuming it benign.
3. Sweep the run record for anomalies: a slipped extensometer, a machine
   stop, an achieved rate outside its percentage band, a soak outside
   its kelvin band, and a force step before maximum force larger than
   the allowance.
4. Combine the three into one verdict per specimen: valid, valid with
   the elongation qualified, or invalid with every reason named.
5. Count only the valid specimens against the number the acceptance
   owes.
6. Accept the lot when the count is met; call a repeat when the
   shortfall is inside the repeats the programme allows and there are
   invalid specimens to repeat; otherwise reject.
7. Report every finding against the specimen it came from, keeping the
   elongation qualifications separate from the invalidating reasons.

## Pitfalls

- Treating any off-centre fracture as invalid. Inside the gauge length
  the strength is still the material's; it is the elongation that owes
  the displaced-gauge treatment, and discarding the whole specimen
  throws away a good strength result.
- Counting an in-grip failure as a low strength result. It is not a low
  result, it is not a result, and averaging it in depresses an
  allowable with no physical basis.
- Accepting a fracture description nobody can name. The unnamed mode is
  where the fixture failures hide.
- Reading necking as a force discontinuity. After maximum force the
  force is meant to fall, and a detector that does not stop at the peak
  invalidates every well-behaved ductile test.
- Filling a short lot with invalid specimens. The required number is a
  number of valid results, and a repeat is what a shortfall buys when
  the programme allows one.

## Behavior contract (gate 3)

The fracture-position split, named-mode matching, rate and temperature
band checks, pre-peak force-discontinuity detection, per-specimen
verdicts and the valid-only lot disposition are exercised by the gate 3
contract test:
scripts/test_q7045_test_validity_checks.py against
scripts/q7045_test_validity_checks_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_test_validity_checks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
