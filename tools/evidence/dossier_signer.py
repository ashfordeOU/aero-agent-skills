#!/usr/bin/env python3
"""Sign and verify a harness dossier with the evidence key machinery.

WHY THE SIGNER LIVES HERE AND NOT IN THE HARNESS
------------------------------------------------
The Ed25519 implementation and the published trust anchor are in this
corpus, because this is the corpus a stranger can clone. Vendoring a second
copy into the harness would give the project two signing implementations to
keep in step, and the day they diverge is the day a record verifies in one
and not the other. The harness names a signer at its boundary
(`--sign-with module:callable`) exactly so it does not have to hold one.

DOMAIN SEPARATION
-----------------
A dossier is signed under its OWN context string. A signature made over an
evidence record cannot be replayed as a dossier attestation, or the
reverse -- which matters more here than usual, because the two documents
are both JSON, both carry digests, and would otherwise be substitutable to
anyone who only checks the arithmetic.

THE TRUST ANCHOR IS THE CALLER'S
--------------------------------
verify() requires an anchor supplied by the caller and will not fall back
to the key the record carries. A record encloses its own public key for
convenience; that key is never sufficient to verify it, because a forger
encloses a key too.

Offline, stdlib only.
"""

import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import ed25519          # noqa: E402

ALGORITHM = "ed25519"
CONTEXT = "aero-harness-dossier-attestation/v1"
KEY_ENV = "AERO_DOSSIER_KEY"


def key_id(public):
    return "k_" + hashlib.sha256(public).hexdigest()[:16]


def payload(body_digest):
    """The exact bytes signed: the context and the body digest, canonically.

    Canonical JSON rather than concatenation, so no pair of (context,
    digest) can be re-cut into a different pair that serialises the same.
    """
    return json.dumps({"context": CONTEXT, "body_digest": body_digest},
                      sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def read_private_key(path):
    raw = io.open(path, encoding="utf-8").read().strip()
    try:
        private = bytes.fromhex(raw)
    except ValueError:
        raise ValueError("%s does not hold a hex Ed25519 private key" % path)
    if len(private) != 32:
        raise ValueError("%s: expected 32 bytes, found %d" % (path, len(private)))
    return private


def sign(record_bytes, private=None, issuer=None):
    """Attest a dossier's canonical bytes. Returns the attestation dict.

    The private key comes from AERO_DOSSIER_KEY when not passed, and never
    from anywhere inside a repository: a signing key that can be committed
    will be committed.
    """
    if private is None:
        path = os.environ.get(KEY_ENV, "").strip()
        if not path:
            raise ValueError(
                "%s is not set. Refusing to invent a key: a dossier signed "
                "by a key nobody published verifies for nobody." % KEY_ENV)
        private = read_private_key(path)
    public = ed25519.public_key(private)
    body_digest = "sha256:" + hashlib.sha256(record_bytes).hexdigest()
    return {
        "algorithm": ALGORITHM,
        "context": CONTEXT,
        "key_id": key_id(public),
        # Convenience only. verify() will not trust it -- it is here so a
        # reader knows WHICH key to go and look up, not so they can skip
        # looking it up.
        "public_key": public.hex(),
        "issuer": issuer or os.environ.get("AERO_DOSSIER_ISSUER",
                                           "unattributed"),
        "body_digest": body_digest,
        "signature": ed25519.sign(private, payload(body_digest)).hex(),
    }


def load_anchor(path):
    """{key_id: public_key_bytes} from a published anchor file."""
    doc = json.load(io.open(path, encoding="utf-8"))
    out = {}
    for entry in doc.get("keys") or []:
        pub = entry.get("public_key") or ""
        try:
            raw = bytes.fromhex(pub)
        except ValueError:
            continue
        if len(raw) == 32:
            out[entry.get("key_id") or key_id(raw)] = raw
    return out


def canonical_body(record):
    """The record without its attestation, canonically. What was signed."""
    body = dict(record)
    body.pop("attestation", None)
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def verify(record, trusted):
    """(ok, notes). `trusted` maps key_id -> public key bytes.

    An empty anchor cannot produce a pass: with nothing trusted, nothing is
    verifiable.
    """
    att = record.get("attestation")
    if not att:
        return False, ["no attestation: this dossier proves nothing about "
                       "who issued it"]
    if att.get("algorithm") != ALGORITHM:
        return False, ["unknown algorithm %r" % att.get("algorithm")]
    if att.get("context") != CONTEXT:
        return False, ["wrong signing context %r -- a signature made for "
                       "another purpose is not a dossier attestation"
                       % att.get("context")]

    actual = "sha256:" + hashlib.sha256(canonical_body(record)).hexdigest()
    if actual != att.get("body_digest"):
        return False, ["the body does not hash to the digest the signature "
                       "covers (%s vs %s): this record was altered after it "
                       "was signed" % (att.get("body_digest"), actual)]

    kid = att.get("key_id")
    anchor = (trusted or {}).get(kid)
    if anchor is None:
        return False, ["key %s is not in the trust anchor: the record is "
                       "signed, but not by anyone you have said you trust "
                       "(a forger ships their own key too)" % kid]
    try:
        embedded = bytes.fromhex(att.get("public_key") or "")
    except ValueError:
        embedded = b""
    if embedded and embedded != anchor:
        return False, ["the record names a key it was not signed by"]
    try:
        sig = bytes.fromhex(att.get("signature") or "")
    except ValueError:
        return False, ["signature is not hex"]
    if not ed25519.verify(anchor, payload(att["body_digest"]), sig):
        return False, ["signature does not verify under the trusted key %s"
                       % kid]

    notes = ["attested by %s (%s) and verified against the trust anchor"
             % (att.get("issuer", "unattributed"), kid)]
    if record.get("specimen"):
        notes.append("SPECIMEN: this record is a demonstration. It is "
                     "genuinely signed and genuinely verifiable, and it "
                     "covers no deployment -- dossier.matches() refuses it.")
    return True, notes


def main(argv):
    if len(argv) < 3 or argv[1] != "verify":
        print("usage: dossier_signer.py verify <record.json> <anchor.json>",
              file=sys.stderr)
        return 2
    record = json.load(io.open(argv[2], encoding="utf-8"))
    anchor = load_anchor(argv[3]) if len(argv) > 3 else {}
    ok, notes = verify(record, anchor)
    for n in notes:
        print(("PASS " if ok else "FAIL ") + "dossier-verify: " + n,
              file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
