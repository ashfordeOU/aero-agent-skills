---
name: e2008-sca-visual-inspection-deviations
description: "Use when a nonconforming cell assembly is being argued for use as is. Assess a requested departure from the solar cell assembly visible defect rules under ECSS-E-ST-20-08C clause 6.4.3.1.3: refuse one aimed at a criterion that carries no allowance, size the exceedance against the criterion it leaves behind, weigh the predicted performance debit against a single-departure allowance, score the evidence the case rests on before it reaches a customer at all, gate every surviving request on recorded agreement so a sound case with no answer stays pending rather than passing, and add the carried debits so individually small departures cannot sum past the package allowance unnoticed. Trigger: ecss, e-st-20-08c, clause-6-4-3-1-3, sca-visual-defect-deviation, use-as-is-departure-request, sca-customer-agreement-gate, cumulative-performance-debit, non-deviable-defect-criterion."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-visual-inspection-deviations, sca-visual-defect-deviation, use-as-is-departure-request, sca-customer-agreement-gate, cumulative-performance-debit, non-deviable-defect-criterion, sca-deviation-evidence-strength]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Cell Assembly Visual Inspection Deviations (space-systems/ecss/e2008-sca-visual-inspection-deviations)

Use when the task is the departure provision of ECSS-E-ST-20-08C clause
6.4.3.1.3 -- an assembly that does not meet a visible defect rule being argued
for use as it stands, on the twin footing that performance is not harmed and
the customer agrees.

## Domain quick reference

- The clause carries two conditions and they fail independently. A technically
  flawless case with no recorded agreement is not usable, and a recorded
  agreement does not repair a departure that costs performance. Running them as
  one test is how an article ends up flying on a rationale nobody signed.
- Some criteria cannot be departed from at all. Those findings are decided by
  presence rather than by size, so there is no value below which they pass and
  nothing for a measurement to argue about. A request against one of them is
  refused where it stands, before any of the other four steps runs.
- The exceedance is the requested value over the criterion value. It is the
  measure of how far outside the rule the request reaches, and past a declared
  ratio the request has stopped describing a departure from this article and
  started describing a different one.
- A request at or inside the criterion is not a departure. It is a conforming
  article recorded as a nonconformance, and accepting it as a deviation puts a
  paper trail under something that never needed one.
- Every departure carries a predicted electrical debit, and one above the
  single-departure allowance is refused however good the evidence is. Evidence
  establishes that a claimed debit is real; it cannot make a real debit
  acceptable.
- Evidence kinds are not interchangeable. Test, analysis, an inspection record
  and an argument from similarity carry different weight, and below a declared
  strength the case is not solid enough to put to a customer at all. That is a
  review outcome, not a rejection -- the case may well stand once it is made
  properly.
- Agreement has four states and only one of them is a pass. Granted makes a
  surviving request usable as is; refused sends the article to rework;
  requested and not-yet-requested both leave it pending, which is a real state
  and not a soft yes.
- The debits add. Departures each inside the single allowance can sum past the
  cumulative one, and when they do the whole carried set goes back together
  rather than each one passing on its own merits. A per-request loop never sees
  this, which is exactly why it is the step that gets skipped.

## Workflow

1. Validate the policy: the non-deviable criteria, the exceedance ratio, the
   single and cumulative debit allowances, the evidence strength floor and a
   score for every evidence kind, refusing a cumulative allowance that sits
   below the single one.
2. Per request, refuse outright any departure aimed at a non-deviable
   criterion.
3. Reject a request that asks for no more than the criterion already allows; it
   is not a departure and should not be recorded as one.
4. Take the exceedance ratio and refuse a request past the declared limit.
5. Compare the predicted debit with the single-departure allowance and refuse
   one above it regardless of the evidence behind it.
6. Score the evidence and send a weak case to review rather than into the
   agreement queue.
7. Gate what survives on the recorded agreement state: granted is usable as is,
   refused is rework, and either unanswered state is pending.
8. Sum the debits of the carried departures. If they pass the package
   allowance, move the whole carried set to review together and say so.
9. Close with the package verdict, the pending count, and the accept, rework,
   review and reject lists kept apart.

## Pitfalls

- Treating agreement as a formality once the technical case closes. It is a
  condition in its own right, and an article carrying a pending departure is
  not accepted.
- Reading "requested" as agreed. Nothing has come back, so the state is the
  same as not having asked as far as the article is concerned.
- Arguing a non-deviable criterion on size. There is no allowance to depart
  from, so a more careful measurement cannot change the answer.
- Letting strong evidence carry a large debit. Evidence shows a debit is real;
  it does not make a real debit harmless.
- Recording a conforming article as a deviation. The request asks for no more
  than the rule already gives, and the paperwork implies a nonconformance that
  does not exist.
- Dispositioning departures one at a time and stopping. Each can sit inside the
  single allowance while the set sits outside the package one, and nothing in a
  per-request loop ever notices.
- Counting a rejected or reworked departure in the cumulative debit. It is not
  being carried on the article, so adding it makes the package look worse than
  it is and can hold departures that were fine.
- Comparing an exceedance or a cumulative debit with its allowance by bare
  arithmetic. The first is a quotient of two declared limits and the second a
  sum of measured fractions, so a request sitting exactly on an allowance can
  evaluate a few units in the last place above it; the comparison absorbs that
  representation error while the allowance stays untouched.

## Behavior contract (gate 3)

The non-deviable refusal, the not-a-departure rejection, the exceedance ratio,
the single-departure debit allowance, the evidence strength floor, the
four-state agreement gate and the cumulative debit rollup that holds the whole
carried set are exercised by the gate 3 contract test:
scripts/test_e2008_sca_visual_inspection_deviations.py against
scripts/e2008_sca_visual_inspection_deviations_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_visual_inspection_deviations.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
