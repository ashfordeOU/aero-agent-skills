#!/usr/bin/env python3
"""Attestation: who issued this record, provably.

The seal already binds INTEGRITY -- `record.seal.binds == "integrity"`, and
its own comment says plainly that it does not prove who issued anything.
That was the commercial hole. A record's `issued.by` was a free-text string
defaulting to "unattributed", so anyone holding one record could produce a
second one claiming any issuer they liked. Nothing separated an attestation
this project stands behind from one somebody typed.

This adds the missing half:

    seal         the body was not altered after issue   (integrity)
    attestation  and THIS key issued it                 (authenticity)

Why Ed25519 over the stdlib's hmac
----------------------------------
HMAC is symmetric: whoever can verify can also forge. That is exactly wrong
here, because the product is verification by a third party. With a
signature, the public key verifies and only the private key issues -- so the
verifier can be handed to everyone, published, vendored, reimplemented,
while the ability to ISSUE stays with the holder of one 32-byte secret.
That asymmetry is the business model, not an implementation detail.

The one rule that makes this real
---------------------------------
`verify()` requires a TRUST ANCHOR supplied by the caller. A record carries
its own public key for convenience, and that key is never, under any
circumstance, sufficient to verify it. A signature checked against a key
taken from the same document proves only that the document is
self-consistent -- a forger simply ships their own key alongside their own
signature. Records whose embedded key is not in the caller's trusted set are
rejected even when their signature is arithmetically valid.

Key handling
------------
The private key never enters the repository. `keygen` writes it 0600 to a
path the caller names, prints the PUBLIC key, and refuses to write inside
the working tree. The public key belongs in `trusted-keys.json`, committed:
publishing the trust anchor is what lets a stranger check a record.
"""

import json
import os
import stat
import sys

try:                                  # as a package
    from . import canonical, ed25519
except ImportError:                   # as a script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import canonical
    import ed25519

ALGORITHM = "ed25519"
CONTEXT = "aeroskills-evidence-attestation/v1"
TRUST_ANCHOR = "trusted-keys.json"

BINDS_INTEGRITY = "integrity"
BINDS_BOTH = "integrity+authenticity"


# ------------------------------------------------------------------- keys

def keypair(seed=None):
    """(private, public) as 32-byte values. `seed` is for tests only."""
    private = seed if seed is not None else os.urandom(32)
    if len(private) != 32:
        raise ValueError("an Ed25519 private key is exactly 32 bytes")
    return private, ed25519.public_key(private)


def key_id(public):
    """Short stable handle for a public key. Not a secret, not a signature."""
    return "k_" + canonical.digest_bytes(public).split(":", 1)[1][:16]


def write_private_key(path, private, repo_root=None):
    """Write 0600, and refuse to put a private key inside the repository."""
    path = os.path.abspath(path)
    root = os.path.abspath(repo_root or os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if path == root or path.startswith(root + os.sep):
        raise ValueError(
            "refusing to write a private key inside the repository (%s). "
            "A signing key that can be committed will be committed." % path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(private.hex() + "\n")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


def read_private_key(path):
    with open(path, encoding="utf-8") as fh:
        raw = fh.read().strip()
    try:
        private = bytes.fromhex(raw)
    except ValueError:
        raise ValueError("%s does not hold a hex Ed25519 private key" % path)
    if len(private) != 32:
        raise ValueError("%s: expected 32 bytes, found %d" % (path, len(private)))
    return private


def load_trust_anchor(path=None):
    """{key_id: public_key_bytes} from the committed trust anchor."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                TRUST_ANCHOR)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = {}
    for entry in doc.get("keys") or []:
        pub = entry.get("public_key")
        if not pub:
            continue
        try:
            raw = bytes.fromhex(pub)
        except ValueError:
            continue
        if len(raw) == 32:
            out[entry.get("key_id") or key_id(raw)] = raw
    return out


# ------------------------------------------------------------- the payload

def payload(body_digest, issuer):
    """The exact bytes signed.

    Canonical JSON rather than concatenation, so no pair of (digest, issuer)
    can be re-cut into a different pair that serialises the same way. The
    context string is domain separation: a signature made here cannot be
    replayed as a signature for anything else this project ever signs.
    """
    return canonical.canonical_bytes({
        "context": CONTEXT,
        "body_digest": body_digest,
        "issuer": issuer,
    })


# ------------------------------------------------------------------ issue

def attest(record, private, issuer=None):
    """Attach an attestation. Returns the record (mutated in place)."""
    seal = record.get("seal") or {}
    body_digest = seal.get("body_digest")
    if not body_digest:
        raise ValueError("record has no seal.body_digest to attest")
    issuer = issuer or (record.get("body", {})
                        .get("issued", {})
                        .get("by", "unattributed"))
    public = ed25519.public_key(private)
    record["attestation"] = {
        "algorithm": ALGORITHM,
        "context": CONTEXT,
        "key_id": key_id(public),
        # Convenience only. verify() will not trust it -- see the module
        # docstring. It is here so a reader can identify WHICH key to go
        # and look up, not so they can skip looking it up.
        "public_key": public.hex(),
        "issuer": issuer,
        "signature": ed25519.sign(private, payload(body_digest, issuer)).hex(),
    }
    seal["binds"] = BINDS_BOTH
    return record


# ----------------------------------------------------------------- verify

def verify(record, trusted=None, require=True):
    """(ok, notes). `trusted` maps key_id -> public key bytes.

    require=True  -- an unattested record FAILS.
    require=False -- an unattested record passes with a note, for the
                     legacy records issued before attestation existed.

    An attested record is verified against `trusted` ONLY. Passing an empty
    trust anchor cannot produce a pass for an attested record: with nothing
    trusted, nothing is verifiable.
    """
    notes = []
    att = record.get("attestation")
    if not att:
        if require:
            return False, ["no attestation: this record proves integrity but "
                           "not who issued it"]
        return True, ["unattested (integrity only) -- issued before "
                      "attestation existed"]

    if att.get("algorithm") != ALGORITHM:
        return False, ["unknown attestation algorithm %r" % att.get("algorithm")]
    if att.get("context") != CONTEXT:
        return False, ["wrong signing context %r -- a signature made for "
                       "another purpose is not an attestation here"
                       % att.get("context")]

    body_digest = (record.get("seal") or {}).get("body_digest")
    if not body_digest:
        return False, ["record has no seal.body_digest"]

    # The body must actually hash to what the seal claims, or the signature
    # is over a digest that describes some other document.
    actual = canonical.digest(record.get("body"))
    if actual != body_digest:
        return False, ["seal.body_digest %s does not match the body (%s): the "
                       "signature covers a digest this body does not produce"
                       % (body_digest, actual)]

    trusted = {} if trusted is None else trusted
    embedded = att.get("public_key") or ""
    try:
        embedded_raw = bytes.fromhex(embedded)
    except ValueError:
        embedded_raw = b""

    kid = att.get("key_id")
    anchor = trusted.get(kid)
    if anchor is None:
        return False, ["key %s is not in the trust anchor: the record is "
                       "signed, but not by anyone you have said you trust "
                       "(a forger ships their own key too)" % kid]
    if embedded_raw and embedded_raw != anchor:
        return False, ["the embedded public key does not match the trusted "
                       "key for %s -- the record names a key it was not "
                       "signed by" % kid]

    try:
        sig = bytes.fromhex(att.get("signature") or "")
    except ValueError:
        return False, ["signature is not hex"]

    issuer = att.get("issuer", "unattributed")
    if not ed25519.verify(anchor, payload(body_digest, issuer), sig):
        return False, ["signature does not verify under the trusted key %s" % kid]

    claimed = (record.get("body", {}).get("issued", {}).get("by"))
    if claimed is not None and claimed != issuer:
        return False, ["the attestation says issuer %r but the sealed body "
                       "says %r" % (issuer, claimed)]

    notes.append("attested by %s (%s) and verified against the trust anchor"
                 % (issuer, kid))
    return True, notes
