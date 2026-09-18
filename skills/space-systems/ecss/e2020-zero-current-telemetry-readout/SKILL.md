---
name: e2020-zero-current-telemetry-readout
description: "Determine whether a current telemetry channel still reports inside its accuracy budget all the way down to zero load, the recommendation of ECSS-E-ST-20-20C clause 5.2.8.6.1. Use when a power-supply current channel carries an offset, a quantisation step and a noise floor that do not shrink as the load falls: build the error at zero from those fixed terms, set it against the part of the budget that survives at zero, solve for the lowest current the channel actually reports inside budget, name the fixed term dominating any shortfall, and treat a declared blanking deadband as an unreportable band rather than a measured zero. Trigger: ecss, e-st-20-20c-clause-5-2-8-6-1, zero-current-telemetry-readout, current-telemetry-accuracy-budget, telemetry-offset-error-floor, telemetry-quantisation-step, telemetry-blanking-deadband, lowest-reportable-current."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-zero-current-telemetry-readout, current-telemetry-accuracy-budget, telemetry-offset-error-floor, telemetry-quantisation-step, telemetry-blanking-deadband, lowest-reportable-current, zero-load-telemetry-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Zero-Current Telemetry Readout (space-systems/ecss/e2020-zero-current-telemetry-readout)

Use when the task is the clause 5.2.8.6.1 recommendation of
ECSS-E-ST-20-20C: a current telemetry channel is expected to stay able
to report a current down to zero, and to still be inside the accuracy
it was specified to when it does.

## Domain quick reference

- The error of a current telemetry channel splits into terms that
  scale with the reading and terms that do not. The gain term shrinks
  with the load; the offset, the half-step of the acquisition
  resolution and the readout noise do not. At zero load only the fixed
  terms are left, so the zero end of the range is governed by exactly
  the terms a full-scale accuracy figure hides.
- The budget splits the same way. A specification written as a percent
  of reading plus a percent of full scale keeps only its full-scale
  part at zero, and that residue is the entire allowance the fixed
  error has to fit inside. A budget written purely as a percent of
  reading collapses to nothing at zero and can never be met there.
- Both sides being affine in the reported current makes the crossing
  closed form: the lowest current reported inside budget is the excess
  fixed error divided by the difference between the two slopes. No
  search, no sweep, and the answer is a current rather than a verdict.
- A blanking deadband is not a zero reading. A channel that forces its
  output to zero below a threshold cannot report the currents inside
  that band at all, so the deadband raises the lowest reportable
  current even when the accuracy would have been met there.
- When the gain term outruns the reading part of the budget the channel
  also has an upper limit, above which it is out of budget for the
  opposite reason. That is a separate shortfall from the zero-end one
  and is reported separately rather than folded in.
- The clause is a recommendation, so a channel that cannot reach zero
  is not automatically non-compliant; it carries a deviation, and the
  useful output is the current where reporting starts and the term that
  put it there.

## Workflow

1. Take the channel description: full scale, the two accuracy terms,
   the gain error, the offset, the acquisition resolution, the noise
   and any blanking deadband. Reject a missing term rather than
   defaulting it, and reject a budget that is zero on both terms.
2. Build the fixed error at zero from the offset, half a step of the
   acquisition resolution and the readout noise, and set it against the
   full-scale part of the budget.
3. Solve for the accuracy floor: zero when the fixed error already
   fits, otherwise the excess divided by the slope difference, and no
   floor at all when the reading budget never outgrows the gain error
   inside the range.
4. Raise the floor to the blanking deadband where one is declared, and
   record the deadband as a reportability limit in its own right.
5. Name the dominant fixed term and the reduction in each term that
   would alone retire the shortfall, so the fix is attached to a part
   rather than to the channel as a whole.
6. Close with the verdict, the lowest reportable current, the margin or
   shortfall at zero, and the upper limit where the gain term creates
   one.

## Pitfalls

- Quoting a single percent-of-full-scale accuracy and assuming it holds
  at zero. It usually does, but only because the full-scale term is
  carrying the whole fixed error; the moment the specification is
  rewritten as a percent of reading the zero end has no allowance left.
- Treating the blanking deadband as a zero reading. The channel is
  reporting zero for every current in the band, so a real current below
  the threshold is indistinguishable from no current, which is the
  failure the clause is aimed at.
- Leaving the acquisition resolution out of the fixed error. Half a
  step is a constant current, and on a coarse converter over a wide
  range it can exceed the offset and the noise together.
- Comparing the fixed error against the budget by bare arithmetic. A
  channel sized so the fixed error exactly consumes the full-scale term
  can land a few units in the last place either side of the bound, so
  the comparison absorbs the representation error while the budget
  itself stays untouched.
- Reporting only the zero-end shortfall on a channel whose gain error
  exceeds its reading budget. Such a channel leaves budget at the top
  of the range as well, and a report naming only the floor sends the
  design team after the wrong term.

## Behavior contract (gate 3)

The channel validation, quantisation step, fixed-term build-up, error
and budget at a load point, accuracy floor, blanking-limited
reportable current, upper budget limit, dominant term, retirement
options and the recommendation verdict are exercised by the gate 3
contract test:
scripts/test_e2020_zero_current_telemetry_readout.py against
scripts/e2020_zero_current_telemetry_readout_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_zero_current_telemetry_readout.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
