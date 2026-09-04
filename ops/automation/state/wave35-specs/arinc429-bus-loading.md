# Wave-35 leaf spec: arinc429-bus-loading (avionics, data-bus pack)

- Path: skills/avionics/data-bus/arinc429-bus-loading/
- Pack: data-bus. Closest siblings: arinc429-protocol (word format
  encode/decode, octal label, SDI/SSM, parity, BNR/BCD, and the
  CAPACITY FACT statement that 32 data bit-times plus a 4-bit gap
  gives about 2778 words per second at 100 kbps and about 347 at
  12.5 kbps - it does not sum a per-label schedule or compute
  percent utilization), arinc664-afdx (its symmetry anchor: VL
  bandwidth utilization of the 100 Mbps link, e.g. utilization
  0.9108), mil-std-1553 (command-response bus scheduling). Repo-wide
  grep proves ZERO owners for ARINC 429 bus loading, label rate
  schedule sum, percent utilization.
- Standards id: arinc-429 (reference-only; verified in
  standards-map.yaml). Ledger Standard: arinc-429.
- Family: avionics

## Claim

Budget an ARINC 429 transmit schedule: sum the per-label
transmission rates (labels per second) into the total words per
second, compute the bus load in bits per second as the word rate
times 36 bits per word (32 data bits plus the 4-bit gap), compute
the percent utilization of the 100 kbps (or 12.5 kbps) link speed,
flag schedules that exceed the word-per-second capacity (about 2778
words per second at 100 kbps, 100 percent utilization), and report
the headroom against the common 80 percent design guideline.
Produces the total word rate, the bus load, the percent utilization,
the capacity verdict, and the headroom that gate the ARINC 429 label
rate table.

Does NOT do: word construction and decode, parity, BNR/BCD
conversion, SDI/SSM interpretation, label formats
(arinc429-protocol); AFDX BAG/jitter/latency and VL scheduling
(arinc664-afdx); MIL-STD-1553 command-response scheduling and minor
frames (mil-std-1553).

## Model (implement exactly)

Module constants:
- BITS_PER_WORD = 36.0 (32 data bits + 4-bit gap).
- RATE_100_KBPS = 100000.0.
- RATE_12_5_KBPS = 12500.0.
- DESIGN_GUIDELINE_PCT = 80.0 (common headroom guideline).

Conventions: the input is a list of label rates in labels per second
(or a dict {label: rate}); every transmitted ARINC 429 word occupies
36 bit-times regardless of the label content.

Functions (pure stdlib):
- total_word_rate(label_rates) -> sum of the rates. ValueErrors:
  empty input; any negative rate.
- bus_load_bps(total_words_per_s, bits_per_word = BITS_PER_WORD) ->
  words * bits. ValueErrors: words < 0; bits <= 0.
- percent_utilization(bus_load_bps, link_rate_bps = RATE_100_KBPS)
  -> load / link * 100. ValueErrors: load < 0; link <= 0.
- word_capacity(link_rate_bps = RATE_100_KBPS, bits_per_word =
  BITS_PER_WORD) -> link / bits. ValueErrors: link <= 0; bits <= 0.
- capacity_verdict(total_words_per_s, link_rate_bps =
  RATE_100_KBPS) -> dict {capacity_wps, utilization_pct, verdict,
  headroom_pct}: verdict OVER when utilization > 100 else FITS;
  headroom = max(0, 80 - utilization) reported against the design
  guideline. ValueErrors as above.
- bus_loading_summary(label_rates, link_rate_bps =
  RATE_100_KBPS) -> dict with total words/s, load bps, utilization,
  capacity words/s, verdict, headroom.

Identity to test: a schedule at exactly the word capacity gives 100
percent utilization; at exactly the 80 percent design load the
headroom is zero; doubling every label rate doubles the utilization.

## Worked example

Reference schedule at 100 kbps: 3 labels at 50 Hz, 4 labels at
20 Hz, 2 labels at 10 Hz.

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- total_word_rate: 3*50 + 4*20 + 2*10 = 150 + 80 + 20 = 250 words/s.
- bus_load: 250 * 36 = 9000 bps.
- percent_utilization: 9000 / 100000 = 9.0%.
- word_capacity: 100000 / 36 = 2777.8 words/s.
- Adding one 100 Hz label: 350 words/s -> 12.6%.
- Over-capacity check: 30 labels at 100 Hz = 3000 words/s ->
  108.0% -> verdict OVER (the schedule needs a second bus or rate
  reduction).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty label list; negative rate; link_rate <= 0;
  bits <= 0.
- Word rate: [50]*3 + [20]*4 + [10]*2 -> 250; single 1 Hz label ->
  1.
- Load: 250 words/s -> 9000 bps; 100 words/s -> 3600 bps.
- Utilization: worked case 9.0%; boundary at capacity 2777.8 ->
  100.0% within 1e-6; 3000 words/s -> 108.0% -> OVER.
- 12.5 kbps link: capacity 12500/36 = 347.2 words/s; a 300 words/s
  schedule -> 86.4% FITS; 350 words/s -> 100.8% OVER.
- Headroom: at 9% utilization headroom = 71.0; at 80% headroom =
  0; over-capacity headroom 0.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-arinc429-bus-loading.yaml)

Query 1 (copy verbatim):
  "compute the ARINC 429 bus loading from the per label transmission rates and the percent utilization of the 100 kbps link"
  intent: "avionics; ARINC 429 bus load and percent utilization from label rates"
  expected_skill: "avionics/data-bus/arinc429-bus-loading"
Query 2 (copy verbatim):
  "check the ARINC 429 transmit schedule word rate against the capacity and the design headroom guideline"
  intent: "avionics; ARINC 429 transmit schedule capacity and headroom check"
  expected_skill: "avionics/data-bus/arinc429-bus-loading"
Task ids: w35-arinc429-bus-loading-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must budget the ARINC 429 bus
loading:" and include the outputs in the Claim. First tag:
arinc429-bus-loading. Additional tags ONLY: label-rate-budget,
bus-utilization-percent, word-rate-capacity,
transmit-schedule-headroom. NEVER single generic words (bus, load,
label, rate, word, utilization, schedule). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): word format, octal label,
sdi, ssm, odd parity, bnr, bcd, encode, decode (arinc429-protocol);
afdx, bag, jitter, virtual link (arinc664-afdx); command response,
remote terminal, minor frame, mode code, manchester (mil-std-1553).
