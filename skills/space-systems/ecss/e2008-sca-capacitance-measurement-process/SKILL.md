---
name: e2008-sca-capacitance-measurement-process
description: "Evaluate which single accepted technique, frequency domain or time domain, a solar cell assembly capacitance measurement runs under per ECSS-E-ST-20-08C clause 6.4.3.16.2, and show the nominated one holds: size the reactance at the test frequency against the instrument band, derive the dissipation factor the assembly leakage adds, compute the decay constant or ramp slope and the samples the recorder places inside that window, size the fixture stray against the article, and close an uncertainty budget. Use when an assembly capacitance figure is about to be quoted from a technique nobody nominated. Trigger: ecss, e-st-20-08c-clause-6-4-3-16-2, sca-capacitance-measurement-technique, sca-frequency-domain-capacitance-bridge, sca-time-domain-capacitance-decay, constant-current-ramp-capacitance-slope, sca-fixture-stray-capacitance-fraction, sca-capacitance-uncertainty-budget."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-capacitance-measurement-process, sca-capacitance-measurement-technique, sca-frequency-domain-capacitance-bridge, sca-time-domain-capacitance-decay, constant-current-ramp-capacitance-slope, sca-fixture-stray-capacitance-fraction, sca-capacitance-uncertainty-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Capacitance Measurement Process (space-systems/ecss/e2008-sca-capacitance-measurement-process)

Use when the task is clause 6.4.3.16.2 of ECSS-E-ST-20-08C -- measuring the
capacitance of a solar cell assembly by one accepted technique, taken either
from the frequency domain or from the time domain. The clause asks for a
technique, singular. A campaign that leaves both domains open produces two
numbers with no rule for reconciling them, and this is the figure that gets
extrapolated to panel level, so it has to be defensible rather than merely
available.

## Domain quick reference

- Frequency-domain techniques -- a balanced bridge or a swept impedance
  analyser -- read the reactive part of the impedance at a test frequency.
  The assembly presents 1 / (2 pi f C) ohms there, and that has to land
  inside the band the instrument can actually resolve.
- A solar cell assembly is a small capacitor, so its reactance is large. Pick
  the frequency from habit and the article sits above the instrument ceiling,
  where the reading is the meter's own noise floor rather than the article.
- The assembly's own leakage sits in parallel with that reactance and shows
  up as a dissipation factor, 1 / (2 pi f C R). When the loss stops being
  small the bridge is no longer resolving a capacitance at all.
- Time-domain techniques read a rate. A constant-current charge gives a slope
  of I / C; a resistive discharge gives a decay constant of R C. Both convert
  a fitted rate into a capacitance, so the fit is the measurement.
- The recorder is part of the technique. Whatever the window -- the ramp span
  over the slope, or the decay constant -- enough samples have to land inside
  it for the rate to be fitted. A fast article and a slow recorder produce a
  two-point line and a number with no meaning behind it.
- Fixture stray is the defect that dominates at this scale. Leads, a probe
  card and an unguarded platen can hold as much as the article; the stray has
  to be a small, stated fraction of the reading rather than an afterthought.
- The uncertainty budget closes in root-sum-square, and it closes against the
  requirement, not against whatever the setup happened to achieve. A
  technique that cannot close it is not accepted however convenient it is.

## Workflow

1. Validate the measurement policy first: the instrument reactance band, the
   dissipation ceiling, the minimum samples in the observation window, the
   stray allowance and the uncertainty limit. A band whose ceiling is not
   above its floor is refused rather than used.
2. Group the nominated techniques, rejecting an unrecognised one rather than
   ignoring it. No nomination and more than one nomination are distinct
   outcomes, and neither is a measurement -- report them and stop.
3. Resolve the single nominated technique to its domain, and require the
   settings block that domain needs. A plan that names a bridge and carries
   only recorder settings has not been written yet.
4. For a frequency-domain technique, compute the reactance at the test
   frequency and check it against the instrument band, then derive the
   dissipation factor from the assembly leakage and check the reactive part
   still dominates.
5. For a time-domain technique, derive the observation window -- the ramp
   span over the I / C slope, or the R C decay constant -- and check the
   recorder places enough samples inside it. A count landing exactly on the
   minimum is sufficient; the comparison tolerance absorbs representation
   error and the minimum does not move.
6. Close the two checks both domains share: the fixture stray as a fraction
   of the article, and the combined uncertainty in root-sum-square against
   the requirement.
7. Close on one verdict: technique not nominated, more than one technique
   left open, nominated technique inadequate, or technique accepted --
   reporting every inadequacy found, not only the first.

## Pitfalls

- Carrying both domains into the test plan "for flexibility". The clause asks
  for one accepted technique, and the second one exists only to be quoted
  when the first gives an inconvenient answer.
- Choosing the bridge frequency from another article's procedure. Reactance
  scales as one over the capacitance, and an assembly is orders below the
  string that procedure was written for.
- Reading a capacitance through a dissipation factor nobody checked. A lossy
  article returns a number the bridge is willing to display and the physics
  does not support.
- Fitting a decay the recorder never resolved. Twenty samples in the window
  is a fit; two is a straight line through noise, and the capacitance it
  yields carries no uncertainty anyone can defend.
- Leaving the fixture out of the budget. At this capacitance the leads can be
  a tenth of the reading, and an unstated stray biases every assembly in the
  sample the same way, so the scatter never reveals it.
- Closing the uncertainty budget against the achieved setup rather than the
  requirement. It always passes, and it grades the check's own output.

## Behavior contract (gate 3)

The policy validation, the technique inventory and single nomination, the
domain resolution, the reactance and dissipation factor, the decay constant,
ramp slope, observation window and sample count, the fixture stray fraction,
the root-sum-square uncertainty budget, and the technique verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_sca_capacitance_measurement_process.py against
scripts/e2008_sca_capacitance_measurement_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_capacitance_measurement_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
