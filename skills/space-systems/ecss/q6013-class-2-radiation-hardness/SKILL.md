---
name: q6013-class-2-radiation-hardness
description: "Assess a commercial EEE part against the mission radiation environment at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.2.2.4: set the radiation design margin from the evidence basis, size the total-dose requirement the part has to cover, test destructive single-event immunity above the environment ion energy and, where the part is not immune, allow a protected rate argument only inside the declared mission allowance, check the mitigated upset rate against its budget, decide whether the delivered lot has to be irradiated, and report the dose relief lot testing would buy back. Use when a Class 2 build has to tie a commercial part choice to hardness assurance. Trigger: ecss, q-st-60-13c-clause-5-2-2-4, class-two-radiation-hardness-assurance, commercial-part-total-ionising-dose, radiation-design-margin-by-evidence-basis, destructive-single-event-rate-allowance, single-event-upset-rate-budget, lot-radiation-acceptance-test."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-radiation-hardness, class-two-radiation-hardness-assurance, commercial-part-total-ionising-dose, radiation-design-margin-by-evidence-basis, destructive-single-event-rate-allowance, single-event-upset-rate-budget, lot-radiation-acceptance-test, commercial-part-radiation-evidence-basis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Radiation Hardness (space-systems/ecss/q6013-class-2-radiation-hardness)

Use when the task is the hardness criterion of ECSS-Q-ST-60-13C clause
5.2.2.4 at the intermediate assurance class: a commercial part has been
proposed for a mission with a stated radiation environment, and the
question is whether the evidence in hand lets the project select it.

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
  delivered lot was irradiated), manufacturer-rha (the maker declares a
  level for the line but not for this lot), heritage-data (a different
  lot of the same part number flew), and similarity-argument (a related
  part number was tested).
- A weak basis does not change what the part can survive. It changes
  how much of that capability may be counted, so the basis sets the
  radiation design margin the mission dose is multiplied by before the
  part is asked to cover it. The margins here are the intermediate set:
  narrower than the class above, and still widest where the evidence
  sits furthest from the delivered lot.
- The class difference that matters is on destructive events. The class
  above asks for immunity above the environment ion energy and takes no
  rate credit at all. This class lets a part that is not immune be
  carried on a predicted destructive rate, but only behind a declared
  protection measure and only where the protected rate sits inside a
  declared mission allowance. With no protection there is no credit,
  and the susceptible part falls.
- An undeclared destructive threshold is carried as susceptible. A
  commercial datasheet is silent on effects the part was never tested
  for, and silence is not immunity; such a part can only be carried the
  same way any other susceptible part is.
- Lot testing is compelled in two ways: by a basis that cannot speak
  for the delivered lot at all, and by a maker declaration carried on
  so thin a dose margin that lot-to-lot spread could eat it.
- The gap between the requirement on the current basis and the
  requirement on a lot-tested basis is the dose relief an irradiation
  campaign would buy back, and it is the business case for running one.

## Workflow

1. Declare the evidence basis, the mission dose, the part's dose
   capability, the environment ion energy, the part's destructive
   threshold, any protection measure and destructive allowance, the raw
   upset rate, the mitigation level and the upset budget. Reject an
   uncategorized basis rather than defaulting it.
2. Set the radiation design margin from the basis and size the dose the
   part itself has to cover. Compare the capability against that
   margined figure, never against the bare mission dose.
3. Test destructive immunity against the environment ion energy. Where
   the part is immune the question closes there.
4. Where it is not immune, take the rate argument this class allows:
   apply the declared protection credit to the predicted destructive
   rate and compare the protected rate against the mission allowance.
   With no protection declared, refuse the credit.
5. Apply the mitigation credit to the raw upset rate and compare the
   residual against the mission rate budget.
6. Decide whether the delivered lot has to be irradiated, from the
   basis and from the dose margin the basis is carrying.
7. Close with one verdict -- suitable, needs lot radiation testing,
   needs upset mitigation, or not suitable -- and report the dose
   relief a lot-tested basis would buy back.

## Pitfalls

- Comparing the part's dose capability with the bare mission dose. The
  margined requirement is the one the part has to clear, and skipping
  the multiplier quietly grants a lot-tested basis to evidence that
  never earned it.
- Reading the destructive rate allowance as a general rate credit. It
  is only available behind a declared protection measure; without one
  the predicted rate buys nothing, however small it is.
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
protected-rate allowance, upset budget check, lot-test trigger, dose
relief and overall verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_radiation_hardness.py against
scripts/q6013_class_2_radiation_hardness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_radiation_hardness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
