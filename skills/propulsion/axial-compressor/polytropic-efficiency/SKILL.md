---
name: polytropic-efficiency
description: 'Use when you must convert between the isentropic and the polytropic efficiency of a compressor or a turbine for performance sizing: recover the polytropic efficiency from the isentropic efficiency at the overall pressure ratio and the reverse, resolve either from inlet and exit total states, restate the stage-count-independent polytropic efficiency at the per-stage pressure ratio, and run the reheat-factor log-sum cross-check of per-stage ratios against the overall ratio. Produces the converted efficiency pair, the state-resolved efficiency and the stage-consistency verdict in air-standard gamma 1.4 closed forms. Trigger: polytropic efficiency, isentropic efficiency, stage-count-independent efficiency, per-stage pressure ratio, reheat-factor cross-check, efficiency conversion, compressor sizing, turbine sizing.'
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: far-33
  reference-only: true
gated: false
domain: propulsion
pack: axial-compressor
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: propulsion
  subdomain: axial-compressor
  tags:
  - polytropic-efficiency
  - isentropic-to-polytropic-conversion
  - polytropic-to-isentropic-conversion
  - stage-count-independent-efficiency
  - reheat-factor-cross-check
  version: 0.1.0
  author: AeroSkills
---

# Polytropic Efficiency (propulsion/axial-compressor/polytropic-efficiency)

Use when you must convert between the isentropic and the polytropic
efficiency of a compressor or a turbine for performance sizing. The
polytropic (small-stage) efficiency eta_p is stage-count independent:
the exponent form t02/t01 = pr**(KAPPA/eta_p) is the exact integral of
the small-stage relation dT/T = (KAPPA/eta_p)*dp/p, so the same eta_p
describes one stage and the whole machine, while the isentropic
efficiency quoted at the overall pressure ratio depends on the ratio it
is quoted at. This leaf implements the exact algebra between the two
senses, the resolution of either from measured total states, and the
log-sum stage consistency check, all in pure Python stdlib closed form.
It pairs with the propulsion/axial-compressor pack leaves: the work
split and stage arithmetic live in multi-stage-compressor, and the
single-stage machine analysis lives in axial-compressor-stage, while
this leaf owns only the efficiency sense conversion.

## Domain quick reference

- Air-standard gamma = 1.4, KAPPA = (GAMMA - 1)/GAMMA = 2/7 (about
  0.285714). Module constants GAMMA and KAPPA fix every relation.
- Compressor polytropic relation: t02/t01 = pr**(KAPPA/eta_p). The
  polytropic efficiency sits in the DENOMINATOR of the exponent because
  the actual temperature rise exceeds the isentropic rise at every small
  stage, so on the log scale ln(t02/t01) = (KAPPA/eta_p)*ln(pr).
- Turbine polytropic relation (mirror, temperature ratio inverted):
  t04/t03 = pr**(-KAPPA*eta_p), so ln(t03/t04) = eta_p*KAPPA*ln(pr).
  The efficiency MULTIPLIES the exponent on the turbine side because the
  actual temperature drop falls short of the isentropic drop.
- Isentropic whole-drop parametrization of the same exit states:
  compressor t02/t01 = 1 + (pr**KAPPA - 1)/eta_s;
  turbine t04/t03 = 1 - eta_s*(1 - pr**(-KAPPA)). The two
  parametrizations describe the SAME actual exit temperature, and the
  conversions below are the exact algebra between them.
- Conversion compressor (pr > 1): eta_p = KAPPA*ln(pr)/ln(1 +
  (pr**KAPPA - 1)/eta_s) and its inverse eta_s = (pr**KAPPA - 1)/(
  pr**(KAPPA/eta_p) - 1). eta_s falls as the overall pressure ratio
  grows at fixed eta_p, toward 0.
- Conversion turbine (expansion ratio pr > 1): eta_p = ln(1 - eta_s*(1 -
  pr**(-KAPPA)))/(-KAPPA*ln(pr)) and its inverse eta_s = (1 -
  pr**(-KAPPA*eta_p))/(1 - pr**(-KAPPA)). eta_s rises toward 1 as the
  expansion ratio grows at fixed eta_p.
- From states: compressor eta_p = KAPPA*ln(pr)/ln(t02/t01) requires
  t02 > t01; turbine eta_p = ln(t03/t04)/(KAPPA*ln(pr)) requires
  t04 < t03; pr is p02/p01 or p03/p04 and must exceed 1.
- Reheat-factor log-sum check: R = sum(ln(pr_i) for stage ratios
  pr_i)/ln(pr_overall). R = 1 exactly when the stage product matches the
  overall ratio (equal-stage identity); R below or above 1 flags stage
  data inconsistent with the quoted overall ratio. This R is a
  pressure-ratio-side consistency ratio, not the work-based reheat
  factor of the multi-stage-compressor leaf.
- FAR-33 frames the propulsion systems context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: choose the machine (compressor or turbine),
   the overall pressure ratio pr (above 1) and the efficiency you hold:
   the isentropic efficiency quoted at the overall ratio, or the
   polytropic efficiency.
2. Convert a quoted isentropic efficiency to the stage-count-independent
   polytropic efficiency at the overall ratio with
   compressor_polytropic_from_isentropic (compressor) or
   turbine_polytropic_from_isentropic (turbine).
3. Restate the polytropic efficiency at the per-stage pressure ratio:
   compressor_isentropic_from_polytropic or
   turbine_isentropic_from_polytropic at the stage ratio gives the
   per-stage isentropic efficiency, which differs from the overall-ratio
   value while eta_p itself is unchanged. This contrast is the
   stage-count independence statement.
4. Resolve the polytropic efficiency from the inlet and exit total
   states with compressor_polytropic_from_states (t01, t02, pr) or
   turbine_polytropic_from_states (t03, t04, pr), and compare with the
   step 2 conversion value at the same ratio; they must agree.
5. Sweep the isentropic efficiency over the pressure-ratio ladder at
   fixed eta_p (1.2, 2, 5, 10, 20, 40) with
   compressor_isentropic_from_polytropic or
   turbine_isentropic_from_polytropic to confirm the headline sizing
   behavior: eta_s falls as the overall ratio grows for the compressor,
   rises toward 1 for the turbine.
6. Cross-check the per-stage pressure ratio list against the overall
   pressure ratio with reheat_factor_check, the log-sum identity
   R = sum(ln pr_i)/ln(pr_overall): 1 for consistent equal-stage data,
   off 1 otherwise.
7. Confirm the deterministic checks with the contract test
   scripts/test_polytropic_efficiency.py.

## Worked example

Multistage compressor: overall pressure ratio 20, design stage pressure
ratio 1.2, isentropic efficiency 0.85 quoted at the overall ratio.
Real module outputs from a local run of polytropic_efficiency_logic.py:

- compressor_polytropic_from_isentropic(0.85, 20) = 0.898525, the
  stage-count-independent polytropic efficiency behind the isentropic
  0.85 at overall PR 20; the ratio ln(20)/ln(1.2) = 16.431 places the
  machine between 16 and 17 equal stages.
- compressor_isentropic_from_polytropic(0.898525, 1.2) = 0.895862, the
  per-stage isentropic efficiency, ABOVE the overall 0.85 because the
  overall machine re-compresses every stage's reheat loss.
- Round trip at the overall ratio:
  compressor_isentropic_from_polytropic(0.898525, 20) = 0.850000.
- From states with t01 = 288.15 K: the whole-drop ratio t02/t01 =
  1 + (20**KAPPA - 1)/0.85 = 2.592408 gives t02 = 747.002 K, and
  compressor_polytropic_from_states(288.15, 747.002, 20) = 0.898525,
  identical to the from-isentropic result.
- Per stage the ratio is 1.2**(KAPPA/0.898525) = 1.059688, and
  compressor_polytropic_from_states(288.15, 288.15*1.059688, 1.2) =
  0.898525: the SAME eta_p at the stage level and the overall level, the
  two from-states values agreeing to 1e-12 (stage-count independence).
- Fixed eta_p = 0.898525, isentropic efficiency versus pressure ratio:
  PR 2 -> 0.888187, PR 5 -> 0.873663, PR 10 -> 0.862070, PR 20 ->
  0.850000, PR 40 -> 0.837497. eta_s falls as PR grows.
- reheat_factor_check: 16 stages at 1.2 against their own product
  1.2**16 = 18.49 gives R = 0.9999999999999999 (the equal-stage
  identity); the same 16 stages claimed against overall 20 give
  R = 0.973767 and 17 stages claimed against overall 20 give
  R = 1.034627, both flagging inconsistent stage data.
- Turbine mirror (expansion ratio 3, TIT 1500 K):
  turbine_polytropic_from_isentropic(0.88, 3) = 0.862061, BELOW the
  isentropic 0.88 (the reverse of the compressor ordering); round trip
  turbine_isentropic_from_polytropic(0.862061, 3) = 0.880000; with
  t04 = 1500*(1 - 0.88*(1 - 3**(-KAPPA))) = 1144.392 K,
  turbine_polytropic_from_states(1500, 1144.392, 3) = 0.862061; the
  exponent form 3**(-KAPPA*0.862061) = 0.762928 agrees with the
  whole-drop form. At the same eta_p the turbine isentropic efficiency
  rises with the expansion ratio: eta_s = 0.88 at ratio 3 becomes
  0.897934 at ratio 10.

## Verification

- compressor_polytropic_from_isentropic(0.85, 20) returns 0.898525
  (within 1e-6 of the spec anchor) and the round trip at PR 20 recovers
  0.85 within 1e-12.
- compressor_polytropic_from_states(288.15, 747.002, 20) returns
  0.898525, and the per-stage call at ratio 1.2 returns the same eta_p
  to 1e-12 (stage-count independence).
- The fixed-eta_p ladder is strictly decreasing for the compressor
  (0.862070 at PR 10, 0.837497 at PR 40) and strictly increasing for the
  turbine; every swept eta_s stays in (0, 1).
- reheat_factor_check returns 1 within 1e-12 for any stage list whose
  product equals the overall ratio and deviates from 1 otherwise.
- Every non-physical input raises ValueError: pr <= 1 for all pr
  arguments, eta at 0 or above 1 for all eta arguments, t02 <= t01,
  t04 >= t03, non-positive temperatures, an empty stage list, and a
  stage ratio at or below 1.
- Run the contract test offline: python3
  scripts/test_polytropic_efficiency.py (35 tests, deterministic, no
  imports beyond math).

## Related leaves

- propulsion/axial-compressor/multi-stage-compressor: the overall
  pressure ratio as the product of the stage ratios and the stage
  arithmetic that the effective-stage number ln(20)/ln(1.2) references.
- propulsion/axial-compressor/axial-compressor-stage: the single-stage
  machine view with one efficiency applied to the stage work.
- propulsion/axial-compressor/compressor-map: the map context in which
  the converted efficiency values are quoted for the machine.
- propulsion/gas-turbine-cycle/real-cycle-effects: consumes isentropic
  whole-drop efficiencies over the full machine ratio in the cycle
  temperature computation.
- propulsion/turboprop/free-turbine: consumes a polytropic efficiency as
  a given input for the power-section matching.
- propulsion/axial-compressor/turbine-stage: the turbine-side blade-row
  context that pairs with the turbine efficiency conversions here.

## Contract test

The deterministic contract test lives at
scripts/test_polytropic_efficiency.py and runs offline with:

    python3 scripts/test_polytropic_efficiency.py

It asserts the real module outputs of the worked example within the spec
tolerances (conversion anchors, round trips, from-states resolution,
stage-count independence), the closed-form identities (stage product
versus log-sum, exponent form versus whole-drop form), the monotone
efficiency behavior on both machine sides, the reheat-factor log-sum
cross-check values, and the ValueError rejection list of the spec. It
names the numbered SKILL.md Workflow steps each method exercises.

## Compliance

- Standards referenced, not reproduced: FAR-33 is named for the
  propulsion systems context only; the polytropic relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

## Pitfalls

- Quoting the isentropic efficiency at one pressure ratio and reusing it
  at another: eta_s is ratio-dependent (0.895862 per stage against 0.85
  at overall PR 20 for the same eta_p 0.898525), so always state the
  ratio an isentropic efficiency is quoted at. eta_p is the
  stage-count-independent quantity.
- Carrying the compressor ordering onto the turbine: at pr > 1 the
  compressor eta_s sits BELOW eta_p while the turbine eta_s sits ABOVE
  eta_p, because the polytropic efficiency sits in the denominator of
  the compressor exponent but multiplies the turbine exponent. Applying
  the wrong sign convention moves both conversions in the wrong
  direction.
- Confusing the reheat-factor log-sum check with the work-based reheat
  factor of the multi-stage-compressor leaf: R here equals 1 for
  consistent equal-stage data and is a pressure-ratio-side consistency
  ratio, while the work-based quantity is at or above 1 and grows with
  the stage count. The two share the reheat discussion, not the formula.
- Feeding the compressor pr sense to the turbine functions: the turbine
  relations take the expansion ratio p03/p04 > 1, so an inverted ratio
  below 1 raises ValueError rather than silently returning a wrong
  efficiency.
- Reading a single efficiency number without its states or ratio: the
  from-states resolution requires both total temperatures and the ratio,
  and a t02 at or below t01 (or t04 at or above t03) is a data error,
  not a low-efficiency machine.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_polytropic_efficiency.py

The test covers the conversion contract (isentropic to polytropic and
the reverse on both machine sides at overall and per-stage pressure
ratios, resolved against real module outputs), the from-states
resolution of eta_p and its agreement with the conversion value, the
stage-count independence of eta_p on the log scale, the fixed-eta_p
sweep behavior with eta_s confined to (0, 1), the reheat-factor log-sum
cross-check identities and their inconsistent-data flags, and ValueError
rejection of every non-physical input class in the spec. All 35 methods
pass offline.
