# ARCS-1 — the Agent Run Conformance Specification

ARCS-1 · edition 2026-09-24 · defines `claim@1` · supersedes: edition 2026-09-21

---

## 1. What this document is

A conformance claim under `claim@1` says: *this runtime, against this
specification, over these exact corpora, for this period, attested by this
key.* This document defines what that sentence is made of and how a stranger
checks it.

It exists because the alternative was a string constant. Until this edition,
`ARCS-1` was the value of a variable and the subject of a regular expression
in one module of a private runtime. Two public documents — a README and a
licence — said the specification was published openly so that an outsider
could check a conformance claim without asking us. A conformance claim
against a specification that is not a document is not weak. It is void, and
the correct thing to do about that is to write the document, not to soften
the sentence.

**What is normative here.** The serialisation, the record, the identity
derivation, the context strings, the attestation, the verification
procedure, the status list, and the fifteen conformance criteria in §12.
Where this text and any implementation disagree, this text is the
specification and the implementation has a defect.

**What is not.** This document does not define what makes a corpus fit, what
a gate battery must contain, or what constitutes evidence that an obligation
was met. Those are the assessment, and the assessment is what Ashforde OÜ
sells. Specified here is exactly the part a reader must be able to check
*without us*: whether the document in their hands is intact, authentic,
in force, and not withdrawn.

**This is written to be implemented from the text.** Every structure below
is given as fields and bytes. The reference implementation is named in
places as an example of a conforming one, never as the definition. Anyone
who has to read the reference implementation to build a verifier has found
a defect in this document; §15 says where to send it.

**One honest limitation, stated at the front.** The reference
implementation is not public. That does not weaken this specification —
it raises the standard it has to meet, because a reader cannot fall back
on the source. The conformance criteria in §12 are therefore written as
tests a stranger can run against artefacts they already hold, using
nothing but a SHA-256 and an Ed25519 verifier.

Key words *must*, *must not*, *should* and *may* are used in the sense of
RFC 2119.

---

## 2. Parties and artefacts

| Term | Meaning |
| --- | --- |
| **issuer** | the party whose key signs. The issuer is the key, not a name: a name in a field is a claim, and a signature is a check |
| **record** | one conformance claim, as a JSON object. §5 |
| **status list** | what the issuer now says about records it has already issued. §10 |
| **trust anchor** | the set of public keys the *verifier* has decided to trust. Supplied by the verifier. Never by the record |
| **holder** | anyone in possession of a record |
| **relying party** | anyone about to act on the strength of one |

The separation that matters most is the last row of the first column. A
record carries a public key as a convenience, so a reader knows *which* key
to go and look up. A verifier that checks the signature against that key
has verified that the record is internally consistent and nothing else — a
forger ships their own key too. See C8.

---

## 3. Canonical serialisation

Everything that is hashed, identified or signed is serialised by one rule.
Two serialisers that disagree on one byte produce two digests, and therefore
two identities, for one statement.

`CANON(value)` is UTF-8 encoded JSON in which:

- object keys are sorted ascending by Unicode code point;
- there is no insignificant whitespace — a single `,` between items and a
  single `:` between key and value, with no spaces anywhere else;
- non-ASCII characters are emitted literally and never escaped to `\uXXXX`;
- there is no trailing newline.

Four consequences a conforming implementation must respect:

- **No floating-point numbers appear in any artefact defined here.** Their
  text form is implementation-defined and two runtimes would disagree.
  Counts are integers.
- **No `NaN` and no infinities.** They are not JSON, whatever a permissive
  encoder emits.
- **Object keys are unique.** A duplicate key has no defined serialisation.
- **Byte-for-byte reproducibility is a requirement, not a property.** A
  builder given the same inputs twice produces the same bytes twice. This
  is why no artefact here reads a clock: see C15.

In Python this is
`json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
.encode("utf-8")`. That is a fact about one implementation, offered to save
an hour. The four rules above are the definition.

`SHA(bytes)` is SHA-256, lowercase hexadecimal.

---

## 4. Instants

An instant is RFC 3339 UTC to the second, ending in `Z`:
`YYYY-MM-DDTHH:MM:SSZ`.

A conforming implementation **must refuse** an offset, a fractional second
and a lowercase `z`, rather than normalising them. Two spellings of one
instant produce two record identities, so a serial that depends on how its
date was typed is not a serial. Refusal is also the honest option:
normalising silently would mean the string the issuer supplied is not the
string that was signed.

---

## 5. The record

A record is a JSON object. Exactly these fields are defined:

| field | type | presence | meaning |
| --- | --- | --- | --- |
| `context` | string | required | exactly `aeroskills-harness-dossier/v3`. §7 |
| `customer` | string | required | who the claim was issued to; non-empty |
| `runtime` | string | required | the issuing implementation's own version. Provenance, never a conformance input |
| `spec` | string | required | `ARCS-1` |
| `claim` | string | required | `claim@1` |
| `corpora` | object | required | corpus name to 64-character lowercase hexadecimal SHA-256; at least one entry |
| `issued_at` | instant | required | when the claim was made |
| `not_before` | instant | required | not earlier than `issued_at` |
| `not_after` | instant | required | strictly later than `not_before` |
| `record_id` | string | required | derived, never assigned. §6 |
| `binding_integrity` | object | conditional | required when the record names a corpus that references another corpus it also names |
| `specimen` | boolean | optional | present and `true` on a demonstration, absent otherwise. §9 |
| `provenance` | object | optional | free-form. Never a matching criterion |
| `attestation` | object | optional | §8 |

**A field not in this table is not defined by `claim@1`, and a verifier
must refuse the record rather than ignore the field.** This is deliberate
and it costs extensibility on purpose. An undefined field is either a
private extension a verifier cannot honour, or a qualification on the claim
that the verifier is about to act without having read. The whole design
below reads doubt as a reason to refuse; an unknown field is doubt.

Corpora are named **by hash, never by version**. A corpus that grows — the
skills corpus grows hourly — does not invalidate a record, and a corpus that
has been *edited* cannot quietly pass as the one that was assessed. There is
deliberately no notion here of one corpus being newer than another. A
runtime that can order corpora will eventually be asked to prefer one, and
the isolation between the three version streams dies at that point.

`binding_integrity`, where present, carries the integer counts `roles`,
`bindings` and `resolved`, and the boolean `ok`, which must be `true`. A
record asserting a cross-corpus pairing it never checked would be a claim
about work that was not done.

### Three version streams, and why the record names two of them

| stream | field | moves |
| --- | --- | --- |
| runtime | `runtime` | rarely, semantically versioned; it is a product |
| specification | `spec` | on a breaking change only; a new integer means a claim written against the old one no longer means what it said |
| claim dialect | `claim` | with the specification |

The corpus has no version field anywhere in this specification, by design;
it has a hash. Binding the three into one number would make every corpus
addition a re-qualification event.

A record names the specification and **not the edition of this document**.
An edition clarifies; it never changes what conforms. An edition that
changed what conforms would be a different specification and would be
called ARCS-2. So the edition is precisely the thing a reader does not need
in order to check a record, and putting it in the record would be inviting
them to check the wrong thing. §14.

---

## 6. Record identity

Let `payload` be the record with the fields `record_id` and `attestation`
removed. Then

    record_id = PREFIX + "-" + G1 + "-" + G2 + "-" + G3

where `SHA(CANON(payload))` truncated to its first 24 hexadecimal
characters is split into three groups of 8, and

| PREFIX | when |
| --- | --- |
| `AHD` | an issued record |
| `SPECIMEN` | a demonstration — the record carries `specimen: true` |

Three properties follow, all deliberate.

**It is derived, never assigned.** Any holder recomputes it from the
document in their hands. An identifier that cannot be checked is
decoration, and decoration on a certification artefact is worse than none.
A mismatch means the payload was edited after issue, or the serial was
copied from another record. A signature catches both as well — but only for
a reader who has the anchor, and this check needs nothing but the record.

**It identifies the statement, not the act of issuing.** Two runs over the
same corpora, for the same customer, at the same instants, produce one
identifier, because they produced one statement. To get a second
identifier, something a reader would care about has to differ.

**It excludes exactly two fields, for two different reasons.**
`record_id` because a digest cannot cover its own output. `attestation`
because the signature is computed over the body and added afterwards; were
it covered, signing would change the identifier and the identifier would
name a record that no longer exists. Every other field is covered,
provenance and binding counts included. Adding a field and expecting the
identifier to stay where it was is the mistake this paragraph exists to
prevent.

Twenty-four hexadecimal characters is 96 bits. The length is chosen so that
a serial read down a telephone and typed into somebody else's tracking
system survives the trip, and so that two records never collide.

A status list identifier is derived the same way, from the list's own
payload, with the prefix `AHS`. A reader who is handed one document where
the other belongs notices at the fourth character rather than at a schema
error eight fields in.

---

## 7. Context strings, and why none replays as another

Four strings separate the domains. Every one of them sits inside bytes that
a signature covers, and each stops a different substitution.

| string | where it sits | what it stops |
| --- | --- | --- |
| `aero-harness-dossier-attestation/v1` | inside the bytes the Ed25519 signature is computed over | a signature this key made for any other purpose — a licence, a release tag, a challenge-response — being presented as a conformance attestation, and the reverse |
| `aeroskills-harness-dossier/v3` | the `context` field of the record, inside the signed body | a record of an earlier shape passing as this one. A v2 record has no identity and no window, and no reader can infer them after the event |
| `aeroskills-harness-status-list/v1` | the `context` field of the list, inside the signed body | a record being read as a judgement about records, and a list being read as a claim |
| `aero-dossier-trust-anchor/v1` | the `schema` field of the anchor document | any other JSON file that happens to carry a `keys` array being loaded as a set of trusted keys |

A fifth string appears in a list and is not a fifth domain: `covers_context`
quotes the record context a list resolves. A list states what it governs
rather than leaving it implied, so that a record of another shape resolves
to *unknown* and not to *current*. See C13.

### The separation an implementer must not assume

**The attestation context is the same for a record and for a status list.**
Both are signed by the same routine and both carry
`aero-harness-dossier-attestation/v1`. The signature payload therefore does
*not* say which kind of document was signed; only the body digest does, and
the body's own `context` field is what names the type.

This is safe, and it is only safe because of C7: a conforming verifier
checks the `context` field of the body after the signature verifies, and
before reading anything else. A verifier that checks the signature and then
consumes the body without checking its type would accept a status list
wherever a record was expected. That is stated here as a requirement rather
than repaired in the format, because repairing it would change the bytes
under every signature already issued.

### The strings are inconsistent and will stay that way

Three prefixes appear above — `aeroskills-harness-`, `aero-harness-` and
`aero-` — and there is no good reason for the difference. They are not
going to be tidied. A context string is inside the signed bytes of every
document already in somebody's hands; changing one would withdraw every
record issued under it, for a cosmetic gain. Consistency is not worth a
countermand. What is worth one is for the issuer's countermand policy to
say, and §14 says how this document defers to it.

---

## 8. The attestation

An attestation is an object carrying exactly these fields:

| field | meaning |
| --- | --- |
| `algorithm` | `ed25519` |
| `context` | `aero-harness-dossier-attestation/v1` |
| `key_id` | `k_` followed by the first 16 hexadecimal characters of `SHA(public_key_bytes)` |
| `public_key` | 32 bytes, hexadecimal. A convenience so a reader knows which key to look up. Never a basis for trust |
| `issuer` | a name. Also never a basis for trust |
| `body_digest` | `sha256:` followed by `SHA(CANON(body))`, where `body` is the document with `attestation` removed |
| `signature` | 64 bytes, hexadecimal |

The signature is computed over

    CANON({"context": "aero-harness-dossier-attestation/v1",
           "body_digest": <the body_digest above>})

— canonical JSON rather than a concatenation, so that no pair of context
and digest can be re-cut into a different pair that serialises identically.

A document with no attestation is not malformed. It proves integrity to
whoever already has it and authenticity to nobody, and §11 says what a
verifier does with one.

---

## 9. Specimens

A specimen is a record built to demonstrate the machinery rather than to
cover a deployment. Everything in it is real — real digests over real
corpora, a real binding verdict, a real signature — which is exactly why it
needs a marker. A demonstration indistinguishable from an issue is a
forgery waiting to be found lying around.

The marker appears in **three** places, and a conforming implementation
requires all three to agree:

1. the field `specimen`, set to `true`;
2. the `customer` field, beginning
   `SPECIMEN (not issued to a customer): `;
3. the record identifier, whose prefix is `SPECIMEN` rather than `AHD`.

Three places because a flag can be dropped by a reader summarising the
record, and a prefix cannot. A record whose flag and prefix disagree is
refused: guessing which of the two is wrong would mean guessing whether a
real deployment is covered.

A specimen covers no deployment whatever it names. A conforming
implementation's corpus-matching function returns false for a specimen
against any corpus set at all.

Specimen keys are published in an anchor of their own, separate from any
production anchor. A specimen key listed beside a production key would
verify exactly like one, and the only thing distinguishing a demonstration
from an issue would be a reader noticing a status field. Separate files
cannot be misread.

---

## 10. Standing: what the issuer says later

A record cannot testify to its own withdrawal. Whatever it says about
itself it says in the words it had on the day it was signed, and the
interesting question is always asked later: *is this still good?* A record
that could answer it would be a record an issuer could never correct,
because the correction would have to be written into a document already in
somebody else's hands.

So standing lives outside the record, in a separately signed list keyed by
`record_id`.

A status list is a JSON object carrying exactly these fields:

| field | type | presence | meaning |
| --- | --- | --- | --- |
| `context` | string | required | exactly `aeroskills-harness-status-list/v1` |
| `covers_context` | string | required | the record context this list resolves |
| `sequence` | integer | required | 1 for the first list, then one more each time |
| `as_of` | instant | required | when this state was cut |
| `next_update` | instant | required | strictly later than `as_of`. The promise of a successor |
| `entries` | object | required | `record_id` to finding. May be empty |
| `list_id` | string | required | derived as in §6, prefix `AHS` |
| `previous_digest` | string | optional | `SHA(CANON(previous list, attestation included))` |
| `attestation` | object | optional | §8 |

A finding carries exactly `state`, `at`, `reason`, and — only when the state
is `superseded` — `superseded_by`.

| state | meaning |
| --- | --- |
| `superseded` | a later record replaces this one. The work was not wrong; it has been re-done. The successor **must** be named: superseded by nothing is withdrawal wearing a politer word |
| `withdrawn` | do not rely on this record |

There is no state meaning *this one is fine*. A record in good standing is
one the list says nothing about. `at` is when the finding **took effect**,
not when it was noticed — for a compromised key that is the compromise and
not the discovery, because dating the entry to the day somebody found out
would certify the gap. `reason` is capped at 200 characters: this document
goes to everyone holding any record, and the detail belongs in the notice,
not in the index.

Each list is **complete**: a reader answers the question from one document
and never by assembling a chain. The chain exists so that a holder who has
two adjacent lists can prove neither was rewritten between them.

### What a list is not

It is not a roster of everything ever issued. Absence from it is therefore
not evidence that a record was ever issued, and a fabricated record naming
a plausible serial is also not listed. What separates a real record from a
fabricated one is its signature.

### The rule that orders everything

**A finding is honoured from any list in scope. Assurance is granted only
by a list that is in scope, authenticated and fresh. Doubt can only ever
remove assurance; it can never launder a finding.**

Every revocation system that has failed in the field failed by reading
*I could not check* as *it is fine*.

---

## 11. The verification procedure

A verifier is given: a record; a trust anchor of its own choosing; an
instant `at`; and, when standing is in question, a status list. It returns
exactly one conclusion. These steps are normative and their order is
normative.

**Step 0 — the anchor is the verifier's.** Load the set of trusted public
keys from a document the verifier chose. Never from the record. An empty
anchor is a valid input and cannot produce a pass: with nothing trusted,
nothing is verifiable.

**Step 1 — shape.** Check the record against §5: `context` is exactly the
string in §7, every required field is present, no undefined field is
present, every instant parses under §4, and the window is non-empty. Report
every problem at once; a reader holding a file somebody sent them is owed
all of what is wrong with it.

**Step 2 — identity.** Recompute `record_id` per §6 and compare. A serial
that does not bind its payload is not a lookup key, and nothing after this
step means anything without it.

**Step 3 — authenticity.** With the attestation removed, recompute
`SHA(CANON(body))` and compare to `body_digest`. Look up `key_id` in the
anchor; if it is absent, stop — the record is signed, but not by anyone the
verifier said it trusts. If the record also carries `public_key`, it must
equal the anchored key, or the record names a key it was not signed by.
Then verify the Ed25519 signature over the bytes in §8 **under the anchored
key**, never under the embedded one.

**Step 4 — type.** Confirm the body's own `context` names the kind of
document the verifier is about to consume it as. See §7.

**Step 5 — window.** Compare `at` against `not_before` and `not_after`.
The three outcomes are `not_yet_valid`, `valid` and `expired`. This is the
one question the record can answer about itself, and it is **not** a
withdrawal state: on its own it will call a withdrawn record valid,
correctly, because that is all its question asks.

**Step 6 — standing.** Against a status list, in this order:

1. the list itself is well-formed, or no verdict can be read from it;
2. the record's `context` equals the list's `covers_context`, or the answer
   is `unknown` — a record of another shape must be re-issued, never
   assumed current;
3. the key that signed the record and the key that signed the list are the
   same, or the answer is `unknown`. One issuer's list does not govern
   another issuer's record, and the key is the only thing here that says
   whose is whose. This is the single place a finding is *not* honoured,
   and it has to be, or a competitor could withdraw our records by
   publishing a list;
4. a finding whose `at` is at or before the instant asked about is
   returned, before every check below it;
5. then, and only then, the checks that can remove assurance: an unsigned
   record or list gives `unauthenticated`; a record issued after the list
   was cut gives `unknown`, because the list's silence does not reach it; a
   list read after its own `next_update` gives `stale` — it still carries
   its findings and can no longer say that none has been filed since;
6. the record's window, last, so that a withdrawal is never reported as an
   expiry.

The conclusions are exactly:

    unsound_id  unknown  withdrawn  superseded  unauthenticated
    stale  not_yet_valid  expired  current

**Exactly one of them permits reliance: `current`.** Every other
conclusion, including every form of *I could not tell*, is on the refusing
side by construction rather than by the caller's judgement. A verifier that
exposes a single boolean must set it true for `current` and for nothing
else, so that a caller reading only the boolean fails safe on every form of
doubt.

A verifier that reports an exit status should distinguish *refused* from
*cannot be determined*. They are different facts, and a caller that
collapses them will eventually treat a failed fetch as a clean bill of
health.

---

## 12. Conformance criteria

Each is a test against artefacts a stranger already holds. An
implementation conforms to `claim@1` when all fifteen hold.

### C1 — Canonical serialisation

Serialisation follows §3.
**Test.** Serialise the object in vector `canonical-ordering` (§13) and
compare the bytes.

### C2 — Instants are refused, not normalised

An instant outside the form in §4 is rejected rather than repaired.
**Test.** Offer `2026-09-21T00:00:00+00:00`, `2026-09-21T00:00:00.000Z`
and `2026-09-21t00:00:00z` where an instant is required. All three are
refused.

### C3 — The record carries exactly the defined fields

Every required field of §5 is present; no field outside that table is.
**Test.** Add a field named `note` to a valid record and re-derive its
identifier. The record is refused as non-conforming even though its
identifier is sound.

### C4 — The identifier is derived and recomputable

§6, from the record alone, with no anchor and no network.
**Test.** Vector `minimal-record` (§13): recompute and compare. Then change
one character of `customer` and confirm the identifier no longer matches.

### C5 — A specimen is marked in three places

§9, and the three must agree.
**Test.** Take a specimen record, delete the `specimen` field, and confirm
it is refused rather than read as an issued record.

### C6 — The window is stated and non-empty

`not_after` is strictly later than `not_before`, which is not earlier than
`issued_at`.
**Test.** A record with `not_after` equal to `not_before` is refused. A
certification artefact covering no time would read as current to anyone who
does not check the dates.

### C7 — The body names its own type, and the verifier checks it

§7, and step 4 of §11.
**Test.** Present a valid signed status list where a record is expected.
It is refused on its `context` field, not accepted because its signature
verified.

### C8 — Verification uses the verifier's anchor, never the record's key

Step 3 of §11.
**Test.** Re-sign a record with a freshly generated key, write that key's
public half into the record's `public_key` field, and verify against an
anchor that does not list it. The result is a refusal. An implementation
that passes this record is trusting the forger's own key.

### C9 — An empty anchor cannot produce a pass

**Test.** Verify any genuine record against an anchor with no keys in it.
The result is a refusal.

### C10 — Standing is resolved from the list, never from the record

**Test.** Take a record in good standing, add a finding against it to a
list, and confirm the conclusion changes although the record did not.

### C11 — Doubt removes assurance and never launders a finding

**Test.** Take a list carrying a withdrawal, and read it after its own
`next_update`. The conclusion is still `withdrawn` and not `stale`. Then
remove every attestation and read it again: still `withdrawn`, and not
`unauthenticated`.

### C12 — One conclusion permits reliance

**Test.** Enumerate the nine conclusions in §11 and confirm the
implementation's reliance boolean is true for `current` alone.

### C13 — A list states its own scope, cut and successor

**Test.** Resolve a record whose `context` differs from the list's
`covers_context`. The conclusion is `unknown`, never `current`. Then
resolve a record whose `issued_at` is after the list's `as_of`: also
`unknown`, because the list's silence was cut before the record existed.

### C14 — A finding is never softened or dropped

A later list may escalate a finding and may never weaken one, and may not
omit one the earlier list carried.
**Test.** Build a list marking a record `withdrawn`, then attempt a
successor marking it `superseded`, and a successor omitting it. Both are
refused.

### C15 — No clock

No routine that builds or checks an artefact defined here reads the
system clock. Every instant is an argument.
**Test.** Build the same record twice from the same inputs and compare the
bytes. Then resolve a record at an instant in the past and confirm the
answer is about that instant. *Was this covered when the work ran* is the
normal audit question, and a clock cannot be asked it.

---

## 13. Test vectors

A specification without vectors is a specification nobody can check they
have implemented. Each block below is self-contained and copyable.

### `canonical-ordering`

Keys sort by code point at every level, non-ASCII survives unescaped, and
`true`, `false` and `null` are spelled the JSON way.

```json
{
  "vector": "canonical-ordering",
  "value": {"z": 1, "n": 10, "a": {"é": "café", "b": [true, false, null]}},
  "canonical": "{\"a\":{\"b\":[true,false,null],\"é\":\"café\"},\"n\":10,\"z\":1}",
  "canonical_sha256": "7faf486e6129a55e5dc413cc85f758aadd764ecaa1eb62d9ababf31aa556a5dd"
}
```

### `minimal-record`

The smallest conforming record: one corpus, so no binding verdict is owed.
`payload_sha256` is `SHA(CANON(record without record_id and attestation))`,
and the identifier is its first 24 characters in three groups.

```json
{
  "vector": "minimal-record",
  "record": {
    "claim": "claim@1",
    "context": "aeroskills-harness-dossier/v3",
    "corpora": {"skills": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
    "customer": "Example Aerospace GmbH",
    "issued_at": "2026-09-21T00:00:00Z",
    "not_after": "2026-12-20T00:00:00Z",
    "not_before": "2026-09-21T00:00:00Z",
    "record_id": "AHD-86446bd1-3e0f8893-b6b56d24",
    "runtime": "0.1.0",
    "spec": "ARCS-1"
  },
  "payload_sha256": "86446bd13e0f8893b6b56d242797da3dd22ab74d5355c7d5836dc72040d05c1b",
  "record_id": "AHD-86446bd1-3e0f8893-b6b56d24"
}
```

### `attestation-payload`

The bytes an Ed25519 signature is computed over, for the record above.
`body_digest` covers the record *including* its identifier.

```json
{
  "vector": "attestation-payload",
  "body_digest": "sha256:b2c29bd5cf5986ea54ece845950292e1ce8fddf728e2a57f91083433f43f42b0",
  "signed_bytes": "{\"body_digest\":\"sha256:b2c29bd5cf5986ea54ece845950292e1ce8fddf728e2a57f91083433f43f42b0\",\"context\":\"aero-harness-dossier-attestation/v1\"}",
  "signed_bytes_sha256": "46ca3e957354e721a6dd5a909a8004d6045d7a8346cbffa3088934e0b66f2a44"
}
```

### `status-list`

A first list, sequence 1, carrying one withdrawal against the record above.

```json
{
  "vector": "status-list",
  "listing": {
    "as_of": "2026-09-22T00:00:00Z",
    "context": "aeroskills-harness-status-list/v1",
    "covers_context": "aeroskills-harness-dossier/v3",
    "entries": {
      "AHD-86446bd1-3e0f8893-b6b56d24": {
        "at": "2026-09-25T00:00:00Z",
        "reason": "the corpus digest no longer resolves",
        "state": "withdrawn"
      }
    },
    "list_id": "AHS-d48d5c2b-9b3f768b-493ca350",
    "next_update": "2026-10-22T00:00:00Z",
    "sequence": 1
  },
  "list_id": "AHS-d48d5c2b-9b3f768b-493ca350"
}
```

A worked artefact, signed and verifiable against a published anchor, is
published beside this document as `specimen/aero-capability-dossier.json`,
with its anchor at `specimen/specimen-trust-anchor.json` (§16). It is a
specimen: it covers no deployment, and §9 says how you can tell.

---

## 14. Editions of this document

This document carries an **edition** — a date — alongside the
specification name. The two move for different reasons and a reader must
not conflate them.

**An edition clarifies. It never changes what conforms.** Wording, worked
examples, a criterion stated more precisely, a limitation admitted that was
always true: all of these are a new edition of ARCS-1, and an
implementation that conformed to an earlier edition still conforms.

**A change that makes a conforming implementation non-conforming, or the
reverse, is not an edition.** It is ARCS-2, it has a new context string,
and records under the old one keep meaning what they said. That is the
entire reason `spec` is an integer-suffixed name and not a version number
with a minor component: there is nothing a minor bump could honestly mean.

A record therefore names `ARCS-1` and never an edition. The runtime knows
which edition it implements — the reference implementation states it in
`harness/version.py` and `make gate-spec` holds that statement to this
document — but that is the implementation's provenance, not the claim's.

When a defect in this document is found and corrected, the correction is a
new edition and the previous line above is replaced with the edition it
supersedes. Corrections are not silent: where a defect meant a published
record said something that was not true, the issuer's countermand policy
applies, on the terms in force on the day the trigger was confirmed. This
document does not set those terms. What it does fix is the channel: a
correction reaches holders the way standing does, in a signed list (§10),
because a record already in somebody's hands cannot be edited without
ceasing to be the record it was (§6).

---

## 15. Defects in this specification

A passage that cannot be implemented without reading our source is a defect
in this document, not a question to be answered privately, and correcting
it correctly means correcting it for everyone. Report one to
contact@ashforde.org. A correction ships as a new edition under §14.

Nothing in this document grants a licence to the reference implementation.
The specification is open so that a claim can be checked; the runtime is
not, and the licence of the runtime's own repository is the only statement
of what may be done with it. What may be done with this document is in §16.

---

## 16. Where this is published, and on what terms

This document is published at
<https://github.com/ashfordeOU/aero-agent-skills/tree/main/spec>, with the
files below beside it. A copy found anywhere else is a copy; `SHA256SUMS`
says whether it is an intact one.

| file | what it is |
| --- | --- |
| `ARCS-1.md` | this document |
| `specimen/aero-capability-dossier.json` | the worked record §13 refers to, marked as a specimen in all three places §9 requires |
| `specimen/specimen-trust-anchor.json` | the anchor that record verifies against. It lists specimen keys and nothing else (§9) |
| `LICENSE` | the terms below, repeated where a reader looks for them first |
| `SHA256SUMS` | the SHA-256 of every other file in this table, in the format `shasum -a 256 -c` reads |

The set is built from the reference implementation's own tree and never
edited by hand where it is published. A file here that disagrees with the
tree it was built from is a defect of the kind §15 describes.

### Terms

Any person may copy this document and the files published beside it, quote
them, implement the specification, and build and sell a verifier from it,
with no permission from Ashforde OÜ and no obligation to it. These terms
travel with the files: they apply wherever a copy is found, and a licence
covering the repository that happens to carry a copy does not replace
them. Implementing the specification grants no right to the reference
implementation, and conformance to it is not certification by
Ashforde OÜ.
