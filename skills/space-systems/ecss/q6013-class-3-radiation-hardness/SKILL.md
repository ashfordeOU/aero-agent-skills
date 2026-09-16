---
name: q6013-class-3-radiation-hardness
description: "Use when a Class 3 build ties a commercial part choice to thin radiation evidence. Assess a commercial EEE part against the mission radiation environment at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.2.2.4: set the radiation design margin from the evidence basis, size the total-dose the part itself has to cover, test destructive single-event immunity against the environment ion energy, take a bare predicted destructive rate only on a non-critical function, check the mitigated upset rate against its budget, decide when the delivered lot still has to be screened, and report the dose relief screening buys back. Trigger: ecss, q-st-60-13c-clause-6-2-2-4, class-three-radiation-hardness-assurance, commercial-part-total-ionising-dose, radiation-design-margin-by-evidence-basis, unprotected-destructive-rate-allowance, function-criticality-radiation-gate, lot-radiation-screening-trigger."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-radiation-hardness, class-three-radiation-hardness-assurance, commercial-part-total-ionising-dose, radiation-design-margin-by-evidence-basis, unprotected-destructive-rate-allowance, function-criticality-radiation-gate, lot-radiation-screening-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Radiation Hardness (space-systems/ecss/q6013-class-3-radiation-hardness)

Use when the task is the hardness criterion of ECSS-Q-ST-60-13C clause
6.2.2.4 at the lowest assurance class: a commercial part has been
proposed for a mission with a stated radiation environment, the
evidence behind it is thin, and the question is whether that evidence
still lets the project select it.

## Domain quick reference

- A commercial part carries no radiation guarantee. Nothing in the
  catalogue entry is a hardness statement, so a selection at this class
  is tied to the mission environment by project evidence or it is not
  tied at all.
- Three effects are weighed separately because they fail differently.
  Total ionising dose is a cumulative parameter drift, so it is a dose
  budget. Single-event upset is a recoverable state flip, so it is a
  rate budget mitigation can work against. Latch-up and burnout are
  destructive and take the part with them.
- Evidence basis, strongest to weakest: lot-radiation-test (the
  delivered lot was irradiated), manufacturer-rha-declaration (the
  maker declares a level for the line but not for this lot),
  heritage-flight-data (a different lot of the same part number flew),
  similarity-argument (a related part number was tested), and
  generic-family-data (nothing closer than the family exists).
- A weak basis does not change what the part can survive. It changes
  how much of that capability may be counted, so the basis sets the
  radiation design margin the mission dose is multiplied by before the
  part is asked to cover it. The margins here are the thinnest set of
  the three classes, because this class carries the lowest assurance
  target and accepts the spread that comes with it.
- Thin margin is not free. A basis that cannot speak for the delivered
  lot at all, and a maker declaration carried on so little dose
  headroom that lot-to-lot spread could eat it, both drive a lot
  radiation screening even though the arithmetic closed.
- The class difference that matters is on destructive events. The
  classes above want immunity above the environment ion energy, or a
  protected rate inside a declared allowance. This class opens one
  further route: a susceptible part with no protection measure at all
  may be carried on its bare predicted rate, but only where the
  function it serves is non-critical. A critical function still needs
  immunity or a declared protection measure, and a bare-rate credit
  travels with the part as a restriction on where it may be used.
- An undeclared destructive threshold is carried as susceptible. A
  commercial datasheet is silent on effects the part was never tested
  for, and silence is not immunity.
- The gap between the requirement on the current basis and the
  requirement a lot-screened basis would set is the dose relief a
  screening campaign buys back, and it is the business case for
  running one.

## Workflow

1. Declare the evidence basis, the function criticality, the mission
   dose, the part's dose capability, the environment ion energy, the
   part's destructive threshold, any protection measure and destructive
   allowance, the raw upset rate, the mitigation credit and the upset
   budget. Reject an uncategorized basis or criticality rather than
   defaulting it.
2. Set the radiation design margin from the basis and size the dose the
   part itself has to cover. Compare the capability against that
   margined figure, never against the bare mission dose. An undeclared
   capability is an open item, not a pass.
3. Test destructive immunity against the environment ion energy. Where
   the part is immune the question closes there.
4. Where it is not immune, take the rate argument in the order this
   class allows: a declared protection measure first, and only failing
   that the bare predicted rate, which is available on a non-critical
   function alone.
5. Apply the mitigation credit to the raw upset rate and compare the
   residual against the mission rate budget.
6. Decide whether the delivered lot has to be irradiated, from the
   basis and from the dose headroom the basis is carrying.
7. Close with one verdict -- suitable, needs lot radiation screening,
   needs upset mitigation, restricted to a non-critical function, or
   not suitable -- and report the dose relief a lot-screened basis
   would buy back.

## Pitfalls

- Comparing the part's dose capability with the bare mission dose. The
  margined requirement is the one the part has to clear, and skipping
  the multiplier quietly grants a lot-screened basis to evidence that
  never earned it.
- Reading the thinner margins as the whole of the class relief. The
  screening trigger is the other half: a thin margin that closes on
  paper still buys a lot irradiation when the headroom behind it is
  too small for commercial lot spread.
- Taking the bare destructive rate on a critical function. That route
  exists only where the function can afford to lose the part, and a
  part carried on it is restricted to non-critical use for the rest of
  the build.
- Counting upset mitigation against latch-up or burnout. Scrubbing and
  redundancy restore a flipped state; they do not restore a part that
  has already burned out, so the two budgets never share a credit.
- Reading an absent destructive threshold as an absent problem. Silence
  in a commercial datasheet has to be carried as susceptible until a
  test says otherwise.
- Letting heritage stand in for the delivered lot. Heritage says a
  different lot survived; commercial lines move wafer fab, die revision
  and assembly site without notice, so the lot in the box is a
  different population.
- Comparing a capability with a requirement by bare arithmetic. The
  requirement is a product and a protected rate is a product too, so a
  case built to sit exactly on its limit can land a few units in the
  last place the wrong side of it; the comparison absorbs that
  representation error while the limit stays untouched.

## Behavior contract (gate 3)

The design-margin selection, dose sizing, destructive immunity test,
protected and bare rate allowances, criticality gate, upset budget
check, lot-screening trigger, dose relief and overall verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_3_radiation_hardness.py against
scripts/q6013_class_3_radiation_hardness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_radiation_hardness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
