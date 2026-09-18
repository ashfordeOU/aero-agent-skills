---
name: q7004-temperature-limit-derivation
description: "Derive the temperature limits a thermal test runs to from the hardware's environmental data and the declared margins. Use when the ECSS-Q-ST-70-04C limits have to be built up rather than quoted: take an uncertainty increment from the data basis, whether measured hardware, a correlated model or an uncorrelated one, add the acceptance band and, for a qualification run, the qualification band, cap the total at the programme ceiling, check the derived limits against what the hardware can survive, and report the widening a measurement would take back. Trigger: ecss, q-st-70-04-thermal-testing-scope, test-temperature-limit-derivation, thermal-uncertainty-margin-build-up, qualification-temperature-margin, hardware-capability-limit-check, predicted-versus-measured-thermal-data."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-temperature-limit-derivation, test-temperature-limit-derivation, thermal-uncertainty-margin-build-up, qualification-temperature-margin, hardware-capability-limit-check, predicted-versus-measured-thermal-data]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Temperature Limit Derivation (space-systems/ecss/q7004-temperature-limit-derivation)

Use when the task is the temperature limit derivation of ECSS-Q-ST-70-04C —
turning a predicted thermal environment into the limits a chamber actually
runs to, through a build-up of declared increments that can be read back
afterwards.

## Domain quick reference

- A test limit is never the predicted temperature. It is the prediction
  widened outward by increments, each answering a different question, and the
  increments are what makes the limit defensible.
- The first increment is the uncertainty of the prediction itself, and it
  follows the data basis. Measured flight hardware owes nothing. A model
  correlated against test data owes a moderate increment. An uncorrelated
  model owes the most, because nothing has yet shown that it predicts this
  hardware rather than a plausible one.
- The second increment is the acceptance band, the workmanship margin a
  delivered item is verified over. The third is the qualification band, which
  a qualification run adds and an acceptance run does not.
- The ladder runs outward in order: prediction to design limits, design to
  acceptance limits, acceptance to qualification limits. Reporting only the
  endpoint loses which step widened the envelope and by how much.
- Two ceilings bound the build-up. The programme caps the total widening, so
  a weak data basis on a qualification run can hit the cap and the limits are
  then narrower than the increments call for, which has to be said. The
  hardware's own capability caps it again, and a derived limit beyond what
  the material or part survives damages the item rather than demonstrating
  anything about the mission.
- The build-up is also the business case for measurement. The difference
  between the current uncertainty increment and the measured-hardware one is
  what an instrumented flight-configuration measurement takes back off each
  end of the envelope.

## Workflow

1. Declare the predicted cold and hot extremes, the data basis behind them,
   the objective and the hardware capability envelope. Reject an
   uncategorized data basis rather than defaulting it.
2. Build up the increments: uncertainty from the basis, the acceptance band,
   and the qualification band when the objective calls for it. Keep the raw
   total and the capped total separately.
3. Build the ladder step by step so design, acceptance and qualification
   limits are all visible, and check that the cold end never crosses absolute
   zero under a large increment.
4. Derive the test limits by widening the prediction by the capped total, and
   record whether the cap was reached.
5. Check both derived limits against the hardware capability and report the
   remaining margin on the tighter end, not an average of the two.
6. Close with the widening a measurement would take back, and with the duty
   to quote the build-up alongside the limits.

## Pitfalls

- Quoting a test limit without its build-up. The number then cannot be traced
  to a prediction, a data basis or a policy, and the next programme inherits
  it as a constant.
- Taking an uncorrelated model at the correlated increment because the model
  looks careful. Correlation is a comparison against test data, not a
  property of the mesh, and the increment follows what was compared.
- Applying the qualification band to an acceptance run. The delivered item is
  then verified over a band it was never designed to be verified over, and
  acceptance failures start appearing that are really qualification findings.
- Reporting the capped total as if it were the build-up. A capped total means
  the increments exceeded the programme ceiling, and that shortfall is a
  finding rather than a quiet narrowing of the test.
- Widening past the hardware capability and running it anyway. The item is
  damaged by the test, and the failure is then indistinguishable from one the
  mission environment would have caused.
- Comparing a derived limit against a capability by bare arithmetic. A limit
  built from a chain of added increments can land a few units in the last
  place either side of the capability; the comparison absorbs that
  representation error while the capability itself stays untouched.

## Behavior contract (gate 3)

The uncertainty increment selection, margin build-up with its programme cap,
the design-acceptance-qualification ladder, the widening arithmetic, the
hardware capability check and the measurement reduction are exercised by the
gate 3 contract test:
scripts/test_q7004_temperature_limit_derivation.py against
scripts/q7004_temperature_limit_derivation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7004_temperature_limit_derivation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
