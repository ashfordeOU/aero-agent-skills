---
name: e2020-inductive-current-freewheeling-provision
description: "Verify the inductive-current freewheeling provision of ECSS-E-ST-20-20C clause 5.2.7.7.1. Use when a current limiter feeds an inductive load over a long harness and the branch has to keep conducting the instant the limiter opens: sum the load and harness inductance, size the energy trapped at the limitation current, categorize the declared return path as absent, load-freewheel-diode, switch-clamp or active-clamp, derive the decay time and the peak the switching element then stands off, compare that peak against its rating and the decay against the reclosure dead time, and reject a design whose only path is the switch avalanche. Trigger: ecss, e-st-20-20c, limiter-inductive-freewheeling-path, limiter-opening-transient, harness-stored-energy, freewheel-diode-decay, limiter-switch-standoff-margin, clamp-energy-absorption, limiter-reclosure-dead-time."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-inductive-current-freewheeling-provision, limiter-inductive-freewheeling-path, limiter-opening-transient, harness-stored-energy, freewheel-diode-decay, limiter-switch-standoff-margin, limiter-reclosure-dead-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Inductive Current Freewheeling Provision (space-systems/ecss/e2020-inductive-current-freewheeling-provision)

Use when the task is the freewheeling provision of ECSS-E-ST-20-20C
clause 5.2.7.7.1 -- showing that the current in an inductive load and
its harness has somewhere to circulate at the moment a limiter opens,
rather than being forced through the switching element that just tried
to interrupt it.

## Domain quick reference

- Opening a limiter does not stop the current on the branch. The
  inductance of the load and of the harness keeps it flowing, and the
  energy already stored in that inductance has to go somewhere. The
  clause asks for a deliberate path; a design with none has chosen the
  switching element by default.
- The inductance that matters is the series sum along the interrupted
  branch: the load winding plus the go-and-return loop of the harness
  run. A short bench lead hides the harness term, so a result taken on
  the bench harness does not cover the flight run.
- The trapped energy is half the inductance times the square of the
  current at the instant of opening, so it scales with the square of
  the limitation current. Raising a limitation level to cure nuisance
  trips quadruples what the return path has to swallow.
- Return-path provisions, best to weakest: active-clamp (a driven clamp
  holding a chosen voltage), switch-clamp (a passive avalanche or
  transient clamp), load-freewheel-diode (a diode across the inductive
  load), and no-path at all.
- A constant-voltage clamp forces a constant rate of change, so the
  current ramps down linearly and the decay is the inductance times the
  current divided by the clamp voltage. A load freewheel loop decays
  exponentially on the load's own time constant and never reaches zero,
  so its decay is quoted to a declared residual level.
- The two numbers that decide the case pull in opposite directions. A
  harder clamp ends the transient sooner but raises the peak the switch
  stands off; a softer clamp lowers the peak but stretches the decay.
  The design has to satisfy the standoff margin and the reclosure dead
  time at once.
- The decay has to finish before the limiter is allowed to retry. A
  retry into an inductance that is still carrying current starts from a
  pre-loaded initial condition, not from zero, so the second transient
  is worse than the first.

## Workflow

1. Sum the series inductance of the interrupted branch from the load
   winding and the harness run, and reject a case that declares no
   inductance at all -- an interruption case without inductance is not
   the clause's case.
2. Size the energy trapped at the limitation current, and record it as
   the quantity the return path must absorb.
3. Categorize the declared return path into one of the four provisions.
   Reject an uncategorized declaration rather than assuming a diode is
   fitted, because everything downstream depends on this step.
4. Derive the decay: linear to zero for a clamp, exponential to a
   declared residual level for a load freewheel loop, and undefined
   where no path exists.
5. Derive the peak the switching element stands off: the bus plus the
   clamp hold voltage, or the bus plus a diode forward drop. Where no
   path exists there is no defined peak, only the switch avalanche, and
   the case fails on that alone.
6. Compare the peak against the switch standoff rating with the
   required margin, and the decay against the reclosure dead time.
   Close with an adequate, marginal or inadequate verdict, and name the
   check that governed it.

## Pitfalls

- Sizing the path on the load inductance alone. The harness is in
  series with it and a flight run can carry more inductance than the
  load, so a provision qualified on a short bench lead is not qualified
  for the flight harness.
- Assuming the switching element can simply absorb the transient. It
  can, once, into its own avalanche, which is a destructive-energy
  rating and not a design path. The clause asks for a circulating path
  precisely so the switch is not the path.
- Quoting a freewheel decay as if it reached zero. A diode loop decays
  on the load time constant asymptotically, so the decay is only
  meaningful against a declared residual level, and a tighter residual
  costs more time.
- Raising a limitation level without revisiting the provision. The
  trapped energy follows the square of the current, so a modest
  increase to stop nuisance trips can leave the clamp under-rated.
- Choosing the clamp voltage for standoff alone. A soft clamp keeps the
  peak comfortable and stretches the decay past the reclosure dead
  time, which turns a clean single interruption into a retry on a
  pre-loaded inductance.
- Comparing the standoff margin or the decay by bare arithmetic. Both
  come from chains of floating-point operations, so a case designed to
  sit exactly on its limit can land a few units in the last place on
  the wrong side; the comparison absorbs that representation error
  while the rating and the dead time stay untouched.

## Behavior contract (gate 3)

The series-inductance sum, trapped-energy sizing, provision
categorization, clamp and diode decay, peak-standoff derivation,
margin comparison and the adequate/marginal/inadequate verdict are
exercised by the gate 3 contract test:
scripts/test_e2020_inductive_current_freewheeling_provision.py against
scripts/e2020_inductive_current_freewheeling_provision_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_inductive_current_freewheeling_provision.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
