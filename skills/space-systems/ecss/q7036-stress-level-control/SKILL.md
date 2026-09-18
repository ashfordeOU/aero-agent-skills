---
name: q7036-stress-level-control
description: "Compute the total sustained tensile stress in a part and grade it against the stress-corrosion allowable of ECSS-Q-ST-70-36C. Use when applied load is only one of the stresses locked into a joint and the cracking threshold has to be defended: sum the sustained applied, assembly fit-up, preload, press-fit, forming-residual and thermal terms together, raise the nominal ones by the elastic concentration factor while leaving the already-local ones alone, subtract a compressive surface residual without letting the total go below zero, then compare with a measured threshold or the fraction of yield the resistance rating permits and rank the reductions that close a shortfall. Trigger: ecss, q-st-70-36c, sustained-tensile-stress-summation, scc-threshold-stress, assembly-fitup-stress, scc-preload-contribution, compressive-residual-relief."
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
  tags: [ecss, q-st-70-materials-scope, q-st-70-36c, q7036-stress-level-control, sustained-tensile-stress-summation, scc-threshold-stress, assembly-fitup-stress, scc-preload-contribution, compressive-residual-relief]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Materials — SCC Stress Level Control (space-systems/ecss/q7036-stress-level-control)

Use when the task is the selection step of ECSS-Q-ST-70-36C that keeps
the sustained tensile stress in a part below the level at which
stress-corrosion cracking initiates -- the control that is exercised
when the alloy state cannot be changed, and the one most often defeated
by a stress nobody put in the sum.

## Domain quick reference

- The cracking driver is the total sustained tensile stress at the
  feature, not the applied load. Assembly fit-up, fastener preload, an
  interference press fit, a forming residual that was never stress
  relieved and a thermal stress held by a constrained interface all act
  at the same time and all belong in one sum.
- Sustained is the operative word. A launch transient at a far higher
  stress is not in this sum; a modest fit-up stress locked in at
  assembly and held through storage, test and flight is.
- The elastic stress-concentration factor of the feature applies to the
  nominal terms. It does not apply twice to terms that are already
  expressed as a local stress at that feature -- a forming residual and
  a press-fit contact stress among them -- and applying it to those
  inflates the total in a way that looks conservative but misdirects the
  reduction effort.
- A compressive surface residual, from shot peening for instance, offsets
  the tensile total and cannot reverse it. Subtracting it below zero
  would assert that the treatment carries the load path, and a total
  driven to zero by it is worth confirming: the treated layer has to
  actually cover the loaded feature.
- The allowable is a measured threshold stress for the state when one
  exists, and otherwise the fraction of the yield strength the
  resistance rating permits -- generous for a resistant state, severe
  for a susceptible one. A threshold quoted above the yield strength is
  not a sustained-stress allowable and is refused.

## Workflow

1. Validate each contribution as a non-negative stress in megapascals;
   a compressive term passed as a negative tensile term is refused, as
   it belongs in the compressive-residual input instead.
2. Validate the stress-concentration factor at unity or above; a feature
   cannot lower the local elastic stress below the nominal.
3. Sum the sustained terms, raising the nominal ones by the
   concentration factor and passing the already-local ones through
   unchanged.
4. Subtract the compressive surface residual and floor the total at
   zero, raising a confirmation finding when the residual cancels the
   whole tensile total.
5. Derive the allowable: the measured threshold if given, otherwise the
   rating's fraction of yield; refuse a threshold above yield.
6. Compare inclusively -- a case built to sit exactly on the allowable
   passes, with the equality resolved by a named tolerance -- and report
   the fractional margin.
7. On a shortfall, rank the reductions by the size of the contribution
   each one attacks, and name the concentration and peening levers last
   because they change the design rather than the assembly.

## Pitfalls

- Summing the applied load alone. Preload and fit-up routinely dominate
  a bolted or interference joint, and a part that passes on applied
  stress can be at twice the allowable once they are in.
- Applying the concentration factor to a residual stress. The residual
  is already the local value; multiplying it again produces a total that
  is wrong in the direction that hides which term to attack.
- Letting a compressive residual drive the total negative. The
  arithmetic is happy and the claim is that the surface treatment now
  carries load; the total is floored at zero instead.
- Quoting a threshold above the yield strength. It is usually a
  fracture-toughness or an ultimate value that has strayed into the
  threshold slot, and it makes every part compliant.
- Relaxing the allowable to pass a case that lands exactly on it. The
  equality is a representation question handled inside the comparison;
  moving the allowable relaxes it for every part that follows.

## Behavior contract (gate 3)

The contribution validation, the concentration-factor rules, the
local-term exemption, the compressive-residual floor, the measured
threshold and rating-fraction allowables, the inclusive comparison and
the ranked reductions are exercised by the gate 3 contract test:
scripts/test_q7036_stress_level_control.py against
scripts/q7036_stress_level_control_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7036_stress_level_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
