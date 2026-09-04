# Wave-36 leaf spec: mil-std-1553-bus-loading (avionics, data-bus pack)

- Path: skills/avionics/data-bus/mil-std-1553-bus-loading/
- Pack: data-bus. Closest siblings: avionics/data-bus/mil-std-1553 (the
  PROTOCOL leaf: word encode/decode, odd parity, format classification,
  qualitative schedule rules; its logic has ZERO timing/utilization
  functions and it explicitly does not compute bus load), arinc429-bus-
  loading (ARINC 429 point-to-point per-label rate budget at 36 bit-
  times/word, 100/12.5 kbps; its SKILL body names mil-std-1553 as a
  sibling loading model), arinc664-afdx (VL BAG utilization symmetry
  anchor). Whole-tree grep: 1553 appears only in mil-std-1553 (protocol),
  arinc429-bus-loading (cross-ref), arinc664-afdx (mention),
  space-systems command-data-handling (bus comparison). ZERO owners for
  MIL-STD-1553 bus-loading math.
- Standards id: mil-std-1553 (reference-only; protocol standard, framing
  only). Ledger Standard: mil-std-1553.
- Family: avionics

## Claim

Compute the MIL-STD-1553 bus loading at the conceptual level: convert a
minor-frame message schedule into wire-word counts per message type
(command/status overhead plus data words), apply the fixed word time
slot at the 1 Mbps data rate, sum the schedule time, and return the bus
utilization against the minor-frame length with an 80 percent loading
guideline verdict. Produces per-message wire words and time, the
schedule total, the percent utilization, the headroom to the 80 percent
budget, and a FITS/OVER verdict.

Does NOT do: word encode/decode, parity, and format classification
(avionics/data-bus/mil-std-1553); ARINC 429 label rate budgets
(arinc429-bus-loading); AFDX virtual-link BAG utilization
(arinc664-afdx).

## Model (implement exactly)

Module constants:
- WORD_TIME_US = 20.0 (microseconds per word at 1 Mbps Manchester
  II biphase: 16 data bits + 3 sync + 1 parity = 20 bit times).
- WORD_GAP_US = 4.0 (microseconds inter-word gap).
- WORD_SLOT_US = WORD_TIME_US + WORD_GAP_US = 24.0.
- FRAME_US_DEFAULT = 5000.0 (microseconds, 5 ms minor frame).
- LOAD_BUDGET_FRACTION = 0.80 (80 percent loading guideline).

Conventions: a message is (kind, data_words). Wire words per message:
BC-to-RT: 1 command + data_words + 1 status = dw + 2; RT-to-BC: 1
command + 1 status + data_words = dw + 2; RT-to-RT: 2 commands + 1
status + data_words = dw + 3. Max 32 data words per message.

Functions (pure stdlib):
- wire_words(kind, data_words) -> int. Kinds: "BCRT", "RTBC", "RTRT".
  ValueErrors: unknown kind; data_words < 1 or > 32.
- message_time_us(kind, data_words) -> float = wire_words *
  WORD_SLOT_US.
- schedule_utilization(messages, frame_us = FRAME_US_DEFAULT) -> dict
  {total_us, utilization_fraction, utilization_pct, budget_us,
  headroom_us, headroom_pct, verdict} with budget = 0.80*frame and
  verdict FITS when total <= budget else OVER. ValueError: frame <= 0;
  empty schedule.
- schedule_headroom(messages, frame_us = FRAME_US_DEFAULT) -> float =
  (0.80*frame - total)/frame*100 (percent headroom to the budget;
  negative when OVER).

Identity to test: wire_words BCRT 16 == 18; RTRT 8 == 11; message time
= wire_words*24 exactly; utilization pct = total/frame*100.

## Worked example

Reference schedule on a 5 ms minor frame (all times verified at prep):
- BC-to-RT 16 data words: 18 wire words = 432 us
- RT-to-BC 32 data words: 34 wire words = 816 us
- RT-to-RT 8 data words: 11 wire words = 264 us
- BC-to-RT 4 data words: 6 wire words = 144 us

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- total = 432 + 816 + 264 + 144 = 1656 us.
- utilization = 1656/5000 = 33.12%; verdict FITS; headroom to the
  80% budget (4000 us) = (4000-1656)/5000 = 46.88%.
- a schedule four times larger (6624 us) = 132.48% -> OVER.
- hand check: RT-to-RT 32 data words = 35 wire words = 840 us.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: unknown kind; data_words 0 or 33; frame <= 0; empty
  schedule.
- Wire words: (BCRT,16)=18; (RTBC,32)=34; (RTRT,8)=11; (BCRT,4)=6;
  (RTRT,32)=35.
- Message time: 432/816/264/144 us within 1e-9.
- Utilization 33.12% within 1e-4; verdict FITS; headroom 46.88% within
  1e-4.
- OVER case: 4x schedule -> 132.48%, verdict OVER, negative headroom.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-mil-std-1553-bus-loading.yaml)

Query 1 (copy verbatim):
  "compute the mil std 1553 bus utilization of a 5 millisecond minor frame schedule with bc to rt and rt to bc messages"
  intent: "avionics; MIL-STD-1553 minor frame bus loading and utilization"
  expected_skill: "avionics/data-bus/mil-std-1553-bus-loading"
Query 2 (copy verbatim):
  "estimate the 1553 data bus loading headroom against the 80 percent guideline for an rt to rt message schedule"
  intent: "avionics; 1553 wire word time budget and loading headroom"
  expected_skill: "avionics/data-bus/mil-std-1553-bus-loading"
Task ids: w36-mil-std-1553-bus-loading-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the MIL-STD-1553 bus
loading:" and include the outputs in the Claim. First tag:
mil-std-1553-bus-loading. Additional tags ONLY: 1553-minor-frame-load,
1553-wire-word-time, 1553-bus-utilization, bc-rt-message-overhead,
1553-schedule-budget. NEVER single generic words (1553, bus, loading,
schedule, message, word, overhead, utilization). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): parity, manchester encoding,
word format, status word decode (mil-std-1553 protocol); label, 36 bit
times, kbps, point-to-point (arinc429-bus-loading); virtual link, bag,
bandwidth allocation gap (arinc664-afdx).
