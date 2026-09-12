---
name: e1012-see-hardness
description: "Use when run SEE hardness assurance for a space electronic device under ECSS-E-ST-10-12C §9.5: determine the device's susceptibility to ion-induced and proton/neutron-induced single-event effects, predict the on-orbit SEE rate using device cross-section parameters and the mission particle spectrum, compare the predicted rate against the allowed-error-rate requirement, and assign the hardness assurance category that sets acceptance testing and lot-screening obligations. Trigger: ecss, e-st-10-system-scope, see, single-event-effect, seu, sel, seb, see-rate, hardness-assurance, ion-environment, proton-neutron."
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
  tags: [ecss, e-st-10-system-scope, see, single-event-effect, seu, sel, seb, hardness-assurance, ion-see-rate, proton-see-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — SEE Hardness Assurance (space-systems/ecss/e1012-see-hardness)

Use when the task is the §9.5 single-event effects hardness assurance
procedure of ECSS-E-ST-10-12C — determining each electronic device's
susceptibility to ion-induced and proton/neutron-induced SEE, predicting
the on-orbit rate, comparing it against the system error-rate requirement,
and assigning the hardness assurance category that governs acceptance
testing and lot-screening obligations.

## Domain quick reference

- §9.5 organises the SEE hardness assurance work around three particle
  environments and two effect families. Ion-induced effects are driven by
  the heavy-ion LET spectrum; proton/neutron-induced effects are driven by
  the energy spectrum of trapped and solar protons plus secondary neutrons.
  The two rate contributions are summed for comparison against the
  system-level error-rate requirement.
- Effect types split into destructive (SEL — single-event latchup; SEB —
  single-event burnout; SEGR — single-event gate rupture) and
  non-destructive (SEU — single-event upset; SEFI — single-event functional
  interrupt; SETR — single-event transient; SEHE — single-event hard error).
  Destructive effects require the most stringent hardness assurance controls
  regardless of whether the predicted rate meets the numerical requirement.
- Device susceptibility is determined by the LET threshold (ions) and the
  proton energy threshold. A device whose ion LET threshold is at or above
  the ion immunity level (37 MeV·cm²/mg) needs no ion hardness assurance
  measures. A device whose proton threshold is at or above the proton
  immunity level (200 MeV) needs no proton/neutron measures.
- The SEE rate is estimated from the Weibull cross-section model: the device
  cross-section as a function of LET (or energy) is integrated against the
  mission particle spectrum, yielding a predicted rate in events per device
  per day. The Weibull model requires four parameters: saturation cross-
  section (σ_sat), onset threshold (LET₀ or E₀), width (W), and shape (s).
- Three hardness assurance categories govern acceptance obligations.
  HA1 applies to any device susceptible to a destructive SEE effect: lot
  screening plus acceptance test every lot. HA2 applies to a device with a
  non-destructive SEE effect whose predicted rate exceeds the requirement:
  representative sample test. HA3 applies to a device whose predicted rate
  is within the requirement: compliant by analysis, with the analysis
  documented and reviewed when the environment estimate is updated.

## Workflow

1. Identify every electronic device in the design and enumerate the SEE
   effect types relevant to each device (SEU, SEL, SEB, SEFI, SETR, SEHE,
   SEGR). Reject an unrecognized effect type before it enters the rate
   calculation.
2. For each device-effect pair, obtain the device cross-section parameters
   (σ_sat, LET threshold or energy threshold, Weibull width W, shape s)
   from the device test data or manufacturer data sheet. If data is
   unavailable, apply a conservative bounding assumption and document it.
3. Check ion immunity: if the LET threshold is at or above
   37 MeV·cm²/mg, record the device as ion-immune for this effect and skip
   the ion rate step.
4. If not ion-immune, integrate the Weibull ion cross-section against the
   mission heavy-ion LET spectrum to obtain the ion-induced SEE rate
   (events/device/day): rate_ion = Σ σ_Weibull(LET_i) × flux_i over all
   LET bins.
5. Check proton immunity: if the proton energy threshold is at or above
   200 MeV, record the device as proton-immune for this effect and skip
   the proton/neutron rate step.
6. If not proton-immune, integrate the Weibull proton cross-section against
   the mission proton/neutron energy spectrum to obtain the proton/neutron-
   induced SEE rate: rate_pn = Σ σ_Weibull(E_i) × flux_i over all energy
   bins.
7. Sum the ion and proton/neutron rates to obtain the total predicted rate:
   rate_total = rate_ion + rate_pn.
8. Compare rate_total against the system error-rate requirement for the
   device-effect pair. Flag a violation when rate_total exceeds the
   requirement.
9. Assign the hardness assurance category: HA1 if the effect is
   destructive; HA2 if non-destructive and the rate violates the
   requirement; HA3 if non-destructive and the rate is within the
   requirement.
10. Aggregate per-device findings. A device has no outstanding findings only
    when all effect assessments are free of rate violations (HA1 devices
    still receive HA1 regardless of their numerical rate).

## Pitfalls

- Treating a destructive-effect device as compliant when its predicted rate
  numerically meets the requirement — HA1 is mandatory for destructive
  effects regardless of the numerical comparison; lot screening cannot be
  waived by rate analysis alone.
- Summing ion and proton rates from mismatched environments — the ion LET
  spectrum and the proton/neutron energy spectrum must both derive from the
  same mission orbit and duration, and both must use the same shielding
  depth applied to the device location.
- Ignoring the immunity thresholds — applying the Weibull integration to a
  device that sits above the ion immunity LET threshold overstates risk and
  may trigger unnecessary HA1 or HA2 obligations; conversely, failing to
  check immunity and skipping the integration for a sensitive device
  understates risk.
- Using a manufacturer's nominal Weibull fit without applying a margin to
  the parameters — test data scatter and lot-to-lot variability mean that
  the nominal fit understates the cross-section at the worst-case end; the
  assessment should reflect whether a margin factor has been applied.
- Closing the review without updating the rate assessment when the mission
  orbit or shielding design changes — the §9.5 procedure is iterated every
  time an environment input or shielding assumption is revised.

## Behavior contract (gate 3)

The SEE-type categorization, Weibull cross-section evaluation, ion and
proton/neutron rate integration, hardness assurance category assignment, and
full device review logic are exercised by the gate 3 contract test:
scripts/test_e1012_see_hardness.py against
scripts/e1012_see_hardness_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_see_hardness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
