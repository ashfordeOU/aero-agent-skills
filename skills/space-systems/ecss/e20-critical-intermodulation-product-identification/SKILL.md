---
name: e20-critical-intermodulation-product-identification
description: "Use when identify which intermodulation products of a transmit carrier-plan fall inside a sensitive receive-band or a protected-band under ECSS-E-ST-20C clause 7.4.3: enumerate the integer coefficient sets of every carrier combination up to the declared maximum intermodulation-order, compute each product frequency, drop the non-physical and the mirrored-duplicate sets, test every surviving frequency against the victim band edges widened by the guard-band, rank the hits by intermodulation-order and by frequency-margin, and report the lowest critical order that drives the hardware design and the verification campaign. Trigger: ecss, e-st-20-electrical-scope, intermodulation-product, passive-intermodulation, protected-band, receive-band-overlap, mixing-product-frequency, intermodulation-order, guard-band."
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
  tags: [ecss, e-st-20-electrical-scope, e20-critical-intermodulation-product-identification, intermodulation-product, passive-intermodulation, protected-band, receive-band-overlap, mixing-product-frequency, intermodulation-order, guard-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Critical Intermodulation-Product Identification (space-systems/ecss/e20-critical-intermodulation-product-identification)

Use when the task is the ECSS-E-ST-20C clause 7.4.3 activity of working out
which of the many intermodulation products a transmit carrier-plan can
generate are actually critical -- that is, which land inside a sensitive
receive-band or a protected-band, and at what intermodulation-order they
first do so.

## Domain quick reference

- An intermodulation product of a carrier set is described by one integer
  coefficient per carrier. Its frequency is the coefficient-weighted sum of
  the carrier frequencies; its intermodulation-order is the sum of the
  absolute coefficients. A coefficient set and its sign-flipped mirror
  describe the same physical line, so exactly one of the pair is kept.
- Which member of the mirror pair is the physical one depends on the carrier
  frequencies, not on the coefficients alone, so the pair is resolved after
  the frequency is computed: the member with a strictly positive weighted sum
  is the line that exists, its mirror is the same line counted twice, and a
  zero sum is a direct-current beat rather than a spectral line in a
  receive-band. Resolving the pair on the coefficients alone silently loses
  every product whose higher-frequency carrier carries the positive
  coefficient.
- Products whose coefficients sum (with sign) to one sit close to the
  transmit carriers themselves; these are the near-carrier products that
  threaten a co-located receive-chain. Products whose signed coefficient sum
  is larger land near a harmonic of the transmit band. Both families are
  enumerated; the signed sum is reported so the reader can tell them apart.
- Product amplitude falls steeply with intermodulation-order, so the lowest
  order that hits a victim band is the one that sizes the hardware and the
  one the verification campaign must measure. A ninth-order hit in a band
  that a third-order hit already violates changes nothing.
- The band test is inclusive of the edges and is widened by a guard-band
  representing receive-filter skirt and frequency-uncertainty. A product
  landing exactly on a widened edge is a hit, not a pass -- the comparison
  absorbs float representation error rather than shaving the band.
- Enumeration grows quickly with carrier count and with maximum order, so
  the search is bounded and a request that would explode is refused rather
  than silently truncated -- a truncated search reports fewer critical
  products than exist, which is the one failure mode this step cannot have.

## Workflow

1. Capture the transmit carrier-plan (at least two distinct positive
   frequencies) and every victim band: identifier, band edges, and whether
   it is a receive-band or a protected-band. Reject inverted edges, a
   non-positive lower edge and a negative guard-band.
2. Choose the maximum intermodulation-order to screen and whether to keep
   only the odd orders (the usual passive case) or all orders. Reject an
   order below three and one above the supported bound.
3. Enumerate every coefficient set from the minimum order up to the maximum,
   both members of each mirror pair, discarding the sets below the minimum
   order and (in the passive case) the even orders.
4. Compute each product frequency, drop the sets whose weighted sum is not
   strictly positive (the mirrors and the direct-current beats), and test
   every survivor against each victim band widened by that band's
   guard-band, edges inclusive.
5. For each hit record the coefficient set, the intermodulation-order, the
   signed coefficient sum, the product frequency, the victim band and the
   frequency-margin to the nearest widened edge (zero when inside).
6. Rank the hits by intermodulation-order first, then by frequency-margin,
   then by frequency, so the ordering is deterministic and the head of the
   list is the design driver.
7. Report the lowest critical order per victim band and across the system;
   that order is the input to the acceptance-level derivation and the one
   the verification campaign measures.

## Pitfalls

- Screening only the third-order product because it is the familiar one --
  a fifth or seventh-order product can be the only one that lands in the
  victim band, and the third-order line can fall harmlessly outside it.
- Counting a coefficient set and its mirror as two products, which doubles
  the apparent hit count and corrupts any per-band tally built on it.
- Taking the absolute value of a negative weighted sum instead of dropping
  that set, so the same physical line is screened twice under two different
  coefficient sets -- or, worse, deciding the mirror pair from the sign of
  the first non-zero coefficient, which drops real products entirely.
- Confusing the intermodulation-order (sum of absolute coefficients) with
  the signed coefficient sum (which tells you whether the product sits near
  the carriers or near a harmonic) -- they are different numbers and the
  order is the one that drives amplitude.
- Testing against the nominal receive-band edges with no guard-band, so a
  product just outside the band is declared harmless although the
  receive-filter skirt and the frequency-uncertainty still admit it.
- Silently truncating the enumeration when the carrier count or maximum
  order grows -- a short search under-reports critical products, which
  reads as a clean result.

## Behavior contract (gate 3)

The coefficient-set enumeration, the mirror and direct-current filtering, the
product-frequency computation, the guard-band-widened band test and the
deterministic ranking are exercised by the gate 3 contract test:
`scripts/test_e20_critical_intermodulation_product_identification.py` against
`scripts/e20_critical_intermodulation_product_identification_logic.py`
(stdlib unittest, offline, deterministic). Run:
python3 scripts/test_e20_critical_intermodulation_product_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
