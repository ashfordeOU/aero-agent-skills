---
name: e2008-protection-diode-test-general
description: "Verify the electrical spike levels a protection diode has to withstand were accepted by both parties and then captured on the control drawing, under ECSS-E-ST-20-08C clause 9.6.1: refuse a level only one side signed up to, treat a drawing that records no level or that predates the agreement as an allowance never captured, reject a drawing figure contradicting the agreed one, carry the amplitude-duration product rather than volts alone, and refuse a bench that under-stressed or over-stressed the part. Use when a protection diode spike allowance has to be established, captured or tested against. Trigger: ecss, e-st-20-08-photovoltaic-assembly-scope, protection-diode-spike-allowance, spike-level-drawing-capture, diode-spike-agreement-state, applied-spike-adequacy, protection-diode-spike-stress-integral."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-protection-diode-test-general, protection-diode-spike-allowance, spike-level-drawing-capture, diode-spike-agreement-state, applied-spike-adequacy, protection-diode-spike-stress-integral, protection-diode-spike-overstress-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Protection Diode Test General Provisions (space-systems/ecss/e2008-protection-diode-test-general)

Use when the task is the general provision of ECSS-E-ST-20-08C clause
9.6.1 -- the electrical spike levels a protection diode is required to
withstand are settled between customer and supplier and then written
into the control drawing, and a bench result only means something once
that has actually happened.

## Domain quick reference

- The clause hands nobody a number. The spike level is negotiated, so
  the first question is never "did it pass" but "against what, agreed
  by whom, recorded where".
- Two parties have to have accepted. A supplier proposal the customer
  never answered is not an agreed level, and neither is a customer
  instruction the supplier never confirmed it can build to. Either way
  there is nothing to sentence a part against.
- The capture is the half that fails. A level agreed in a minute or an
  e-mail and never carried onto the drawing leaves the allowance
  unestablished however firm the agreement felt, because the drawing is
  what parts are bought and inspected against.
- A drawing carrying a different figure is worse than one carrying
  none. It is a live document contradicting the agreement, parts are
  being accepted against one of the two, and nobody has said which.
- A drawing issued before the agreement was reached cannot contain what
  was agreed afterwards. A matching figure on an earlier issue is a
  coincidence to be traced to a later issue, not a capture.
- A spike is an amplitude held for a duration, so the stress it imposes
  is the product. Comparing amplitudes alone lets a short pulse at the
  right volts stand in for the agreed stress.
- An under-stressed bench has demonstrated nothing. A diode that saw
  less than the captured level is not evidence it withstands the
  captured level, and a green line in the report says otherwise.
- Over-stress is a finding too, not a bonus. A flight part driven well
  past what was bought has been damaged in a way nobody budgeted for,
  so it goes to review rather than being accepted for being generous.
- The repetition count is part of the level. One spike at the right
  amplitude does not demonstrate a duty of many.
- A spike of the wrong polarity says nothing at all about the
  allowance, whatever its amplitude.

## Workflow

1. Normalise the negotiated level and record which parties accepted it;
   anything short of both is an unestablished allowance.
2. Normalise the control drawing, allowing for a drawing that carries
   no spike level at all.
3. Settle the capture state -- captured, missing, contradicted or stale
   -- comparing polarity, repetitions, amplitude and duration within
   the declared tolerance and checking the issue is not older than the
   agreement.
4. Disposition the allowance itself before looking at any bench result.
5. Where the allowance is established, sentence each bench spike on
   polarity, survival, repetitions and the amplitude-duration product
   against the captured level.
6. Where it is not, carry the bench spikes as advisories rather than
   scoring them against a level nobody agreed; validate them anyway so
   a malformed record is not hidden by the missing allowance.
7. Roll up by severity rather than record order: the governing verdict,
   the capture state, the diodes with no captured level and the bench
   spikes not accepted.

## Pitfalls

- Reading the clause as a test procedure and going straight to the
  bench. The provenance half comes first and it is the half that fails.
- Accepting a level one party proposed and the other never answered.
- Treating an agreement as a capture. The drawing is what the part is
  bought against, and an allowance that never reached it is not an
  allowance.
- Letting a drawing that contradicts the agreement pass as a
  disagreement to be tidied later. Parts are being accepted against it
  now.
- Accepting a matching figure on a drawing issue older than the
  agreement.
- Comparing amplitudes and ignoring duration, so a short pulse at the
  right volts stands in for the agreed stress.
- Reporting an under-stressed bench as a pass.
- Treating over-stress as margin rather than as damage to a flight part
  that has to be dispositioned.
- Sentencing a bench spike of the wrong polarity at all.
- Comparing a stress fraction with its bound by bare arithmetic. The
  fraction is a quotient of products, so a bench that sits exactly on
  the bound can evaluate a few units in the last place off it; the
  comparison absorbs that representation error while the bound stays
  untouched.

## Behavior contract (gate 3)

The agreement state, the capture state including the missing,
contradicted and stale cases, the allowance disposition, the
amplitude-duration stress, the polarity, repetition, under-stress and
over-stress rules on a bench spike, the advisory path when no level is
captured and the severity rollup are exercised by the gate 3 contract
test: scripts/test_e2008_protection_diode_test_general.py against
scripts/e2008_protection_diode_test_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_protection_diode_test_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
