# Evidence attestation: the wire format

An evidence record states what was measured, against which corpus, which
standards editions, which harness version, in which environment. Its **seal**
proves the body was not altered after issue. Its **attestation** proves who
issued it.

This document specifies the attestation so that anyone can write a verifier.
That is deliberate. A verdict only one party can check is not evidence, it is
an assertion; the format is worth nothing to a buyer unless their own auditor
can confirm it without asking us for anything.

Everything here is implementable in a few dozen lines against any Ed25519
library. The reference verifier in `tools/evidence/` uses the Python standard
library only and takes no dependencies.

---

## 1. What each layer binds

| layer | field | proves | does not prove |
|---|---|---|---|
| seal | `seal.body_digest` | the body is byte-for-byte what was sealed | who sealed it |
| attestation | `attestation.signature` | a specific key issued it | that the key is one you trust |
| trust anchor | your own list | that the key is one you trust | — |

The three are separate on purpose. A record with a seal and no attestation is
still a valid record; it proves integrity and says nothing about origin.
`seal.binds` reads `integrity` in that case and `integrity+authenticity` once
attested.

The third row is the one implementers get wrong. See §5.

---

## 2. The attestation block

```json
"attestation": {
  "algorithm":  "ed25519",
  "context":    "aeroskills-evidence-attestation/v1",
  "key_id":     "k_05cdb4e9541397df",
  "public_key": "4af29ba0...414d",
  "issuer":     "ashforde-conformance",
  "signature":  "3a91...be07"
}
```

| field | meaning |
|---|---|
| `algorithm` | `ed25519`. Reject anything else rather than guessing. |
| `context` | domain separation. A signature made under another context is not an attestation here, even if valid. |
| `key_id` | `"k_" + sha256(public_key)[:16]` — a handle for looking the key up. Not a credential. |
| `public_key` | 64 hex chars. **A convenience for identifying which key to look up. Never sufficient to verify.** |
| `issuer` | the issuing party, and it must equal `body.issued.by`. |
| `signature` | 128 hex chars, Ed25519 over the payload in §3. |

---

## 3. The signed payload

The signature covers the canonical JSON encoding of exactly:

```json
{"body_digest":"sha256:...","context":"aeroskills-evidence-attestation/v1","issuer":"..."}
```

Canonical JSON here means: keys sorted, `,` and `:` separators with no
whitespace, UTF-8, no floats. It is the same canonicalization the record digest
uses, specified in `tools/evidence/canonical.py`.

Structured encoding rather than string concatenation is deliberate: with
concatenation, a `(digest, issuer)` pair can sometimes be re-cut into a
different pair producing identical bytes. With a canonical object it cannot.

`body_digest` transitively covers the issuer as well, because `body.issued.by`
is inside the sealed body — but the issuer is bound explicitly too, so that
moving that field later cannot silently unbind it.

---

## 4. Verifying, in order

Stop at the first failure.

1. `attestation.algorithm == "ed25519"`, else reject.
2. `attestation.context == "aeroskills-evidence-attestation/v1"`, else reject.
3. Recompute the body digest. It must equal `seal.body_digest`. Without this
   the signature covers a digest that describes some other document.
4. Look `attestation.key_id` up **in your own trust anchor**. Not found →
   reject. See §5.
5. If `attestation.public_key` is present it must equal the trusted key for
   that `key_id`. A record naming a key it was not signed by is a forgery
   attempt.
6. Verify the signature over §3's payload using the **trusted** key.
7. `attestation.issuer` must equal `body.issued.by`.

A verifier meets untrusted bytes by definition. Malformed input — a short key,
a truncated signature, non-hex — must produce a rejection, never an exception.

---

## 5. The rule everything depends on

**Never verify a record against the public key inside that record.**

A signature checked against a key taken from the same document proves only
that the document is internally consistent. A forger generates their own
keypair, signs their own record, and encloses their own public key; every
check passes. The result validates every forgery ever made.

The key must come from a trust anchor the verifier already holds. For records
issued by this project that anchor is `tools/evidence/trusted-keys.json`, which
is committed precisely so a stranger can clone the repository and verify
without asking anyone for anything.

The reference suite asserts this directly, in
`test_a_valid_signature_from_an_untrusted_key_is_rejected`. An implementation
that passes every other test and fails that one is not a verifier.

---

## 6. Key lifecycle

Private keys are never committed; `evidence keygen` refuses to write one inside
the repository, on the grounds that a signing key which *can* be committed
eventually *is*.

Retiring a key means setting `"status": "retired"` in the trust anchor and
leaving the entry in place. Deleting it would invalidate every record that key
ever issued, which is the opposite of what an evidence archive is for. A
retired key still verifies its history; it must not issue anything new.

---

## 7. Known limits, stated rather than discovered

* **The reference signer is not constant time.** `point_mul` branches on scalar
  bits, so signing leaks timing about the private key. Sign offline, on a
  controlled machine. Verification touches no secret and is safe anywhere. To
  sign in a hostile environment, swap in a constant-time library — the wire
  format is unchanged, which is the advantage of using a standard.
* **There is no revocation transport.** Revocation is a manual edit to the
  trust anchor. There is no CRL, no OCSP, no expiry.
* **There is no timestamp authority.** `body.issued.at` is asserted by the
  issuer, not proven. A signature says who, not when.
* **One key, one issuer.** No delegation, no chain, no intermediate
  certificates.

None of these block the use this format has today. All of them would need
answering before it could carry a legal or certification claim, and it does
not: an evidence record is a technical statement about what was measured.
