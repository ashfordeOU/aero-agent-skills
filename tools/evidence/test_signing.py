#!/usr/bin/env python3
"""Attestation tests, written from the forger's side.

The positive case is easy and proves little. What matters is whether a
determined forger can produce a record that verifies. Each test below is an
attack:

  * sign with your own key and ship it            -> untrusted key
  * ship your key AND claim our key id            -> key mismatch
  * take our signed record and relabel the issuer -> issuer mismatch
  * take our signature and edit the body          -> digest mismatch
  * take our signature onto a different record    -> digest mismatch
  * present an unsigned record                    -> no attestation
  * present a signed record with no trust anchor  -> nothing is verifiable

The test that matters most is `test_a_valid_signature_from_an_untrusted_key
_is_rejected`. A verifier that checks the signature against the key inside
the document validates every forgery ever made.

Run: python3 tools/evidence/test_signing.py
"""

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canonical  # noqa: E402
import ed25519  # noqa: E402
import signing  # noqa: E402

# record.py uses relative imports, so it has to come in as part of the
# package rather than bare off the tools/evidence path the suite adds.
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
from tools.evidence import record as record_mod  # noqa: E402


def make_record(issuer="ashforde-conformance", verdict="pass"):
    body = {
        "issued": {"at": "2026-01-01T00:00:00Z", "by": issuer,
                   "tool": "aero-evidence/1.0.0"},
        "subject": {"kind": "leaf", "ref": "skills/x/y/z"},
        "verdict": verdict,
    }
    return {
        "kind": "aeroskills-evidence-record",
        "schema_version": "1",
        "record_id": "er_test",
        "body": body,
        "seal": {
            "algorithm": canonical.DIGEST_ALGORITHM,
            "canonicalization": canonical.CANONICALIZATION,
            "body_digest": canonical.digest(body),
            "binds": signing.BINDS_INTEGRITY,
        },
        "amendments": [],
        "telemetry": {},
    }


class HappyPath(unittest.TestCase):

    def setUp(self):
        self.priv, self.pub = signing.keypair()
        self.trusted = {signing.key_id(self.pub): self.pub}

    def test_an_attested_record_verifies(self):
        rec = signing.attest(make_record(), self.priv)
        ok, notes = signing.verify(rec, self.trusted)
        self.assertTrue(ok, notes)

    def test_attesting_upgrades_what_the_seal_binds(self):
        rec = make_record()
        self.assertEqual(rec["seal"]["binds"], signing.BINDS_INTEGRITY)
        signing.attest(rec, self.priv)
        self.assertEqual(rec["seal"]["binds"], signing.BINDS_BOTH)

    def test_the_signature_is_deterministic(self):
        # Ed25519 is deterministic; two runs must agree or the record digest
        # of a re-issued identical record would move for no reason.
        a = signing.attest(make_record(), self.priv)["attestation"]["signature"]
        b = signing.attest(make_record(), self.priv)["attestation"]["signature"]
        self.assertEqual(a, b)


class Forgery(unittest.TestCase):
    """Every one of these must fail."""

    def setUp(self):
        self.priv, self.pub = signing.keypair()
        self.trusted = {signing.key_id(self.pub): self.pub}
        self.forger_priv, self.forger_pub = signing.keypair()

    def test_a_valid_signature_from_an_untrusted_key_is_rejected(self):
        # THE test. The forger's record is internally perfect: their
        # signature verifies under their key, which they helpfully enclose.
        # Trusting the enclosed key would validate every forgery ever made.
        rec = signing.attest(make_record(), self.forger_priv)
        ok, notes = signing.verify(rec, self.trusted)
        self.assertFalse(ok, notes)
        self.assertIn("trust anchor", " ".join(notes))

    def test_claiming_our_key_id_while_signing_with_another_is_rejected(self):
        rec = signing.attest(make_record(), self.forger_priv)
        rec["attestation"]["key_id"] = signing.key_id(self.pub)   # lie
        ok, notes = signing.verify(rec, self.trusted)
        self.assertFalse(ok, notes)

    def test_relabelling_the_issuer_on_a_signed_record_is_rejected(self):
        rec = signing.attest(make_record(issuer="ashforde-conformance"),
                             self.priv)
        rec["attestation"]["issuer"] = "someone-else"
        ok, notes = signing.verify(rec, self.trusted)
        self.assertFalse(ok, notes)

    def test_editing_the_body_after_signing_is_rejected(self):
        rec = signing.attest(make_record(verdict="pass"), self.priv)
        rec["body"]["verdict"] = "fail"        # the attack that matters
        ok, notes = signing.verify(rec, self.trusted)
        self.assertFalse(ok, notes)

    def test_editing_the_body_and_the_seal_together_is_rejected(self):
        # A smarter forger updates the digest to match the edited body.
        # The signature still covers the OLD digest.
        rec = signing.attest(make_record(verdict="pass"), self.priv)
        rec["body"]["verdict"] = "fail"
        rec["seal"]["body_digest"] = canonical.digest(rec["body"])
        ok, notes = signing.verify(rec, self.trusted)
        self.assertFalse(ok, notes)

    def test_transplanting_a_signature_onto_another_record_is_rejected(self):
        good = signing.attest(make_record(verdict="pass"), self.priv)
        other = make_record(verdict="fail")
        other["attestation"] = copy.deepcopy(good["attestation"])
        ok, notes = signing.verify(other, self.trusted)
        self.assertFalse(ok, notes)

    def test_a_flipped_signature_bit_is_rejected(self):
        rec = signing.attest(make_record(), self.priv)
        sig = bytearray(bytes.fromhex(rec["attestation"]["signature"]))
        sig[0] ^= 1
        rec["attestation"]["signature"] = sig.hex()
        self.assertFalse(signing.verify(rec, self.trusted)[0])

    def test_a_signature_made_in_another_context_is_rejected(self):
        # Domain separation: a signature over the same digest made for some
        # other purpose must not read as an attestation.
        rec = make_record()
        digest = rec["seal"]["body_digest"]
        other = canonical.canonical_bytes({
            "context": "some-other-protocol/v1",
            "body_digest": digest,
            "issuer": "ashforde-conformance",
        })
        rec["attestation"] = {
            "algorithm": signing.ALGORITHM,
            "context": signing.CONTEXT,
            "key_id": signing.key_id(self.pub),
            "public_key": self.pub.hex(),
            "issuer": "ashforde-conformance",
            "signature": ed25519.sign(self.priv, other).hex(),
        }
        self.assertFalse(signing.verify(rec, self.trusted)[0])

    def test_the_attestation_issuer_must_match_the_sealed_body(self):
        rec = make_record(issuer="ashforde-conformance")
        signing.attest(rec, self.priv, issuer="ashforde-conformance")
        rec["body"]["issued"]["by"] = "somebody-else"
        rec["seal"]["body_digest"] = canonical.digest(rec["body"])
        self.assertFalse(signing.verify(rec, self.trusted)[0])


class TrustAnchor(unittest.TestCase):

    def setUp(self):
        self.priv, self.pub = signing.keypair()

    def test_an_empty_anchor_verifies_nothing(self):
        rec = signing.attest(make_record(), self.priv)
        ok, notes = signing.verify(rec, {})
        self.assertFalse(ok, notes)

    def test_no_anchor_argument_verifies_nothing(self):
        rec = signing.attest(make_record(), self.priv)
        self.assertFalse(signing.verify(rec)[0])

    def test_an_unattested_record_fails_when_attestation_is_required(self):
        self.assertFalse(signing.verify(make_record(), {})[0])

    def test_an_unattested_record_passes_with_a_note_when_not_required(self):
        # Legacy records predate attestation. They may pass, but the note
        # must say what they do not prove.
        ok, notes = signing.verify(make_record(), {}, require=False)
        self.assertTrue(ok)
        self.assertIn("integrity only", " ".join(notes))

    def test_the_anchor_file_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "trusted-keys.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"keys": [{"key_id": signing.key_id(self.pub),
                                     "public_key": self.pub.hex()}]}, fh)
            anchor = signing.load_trust_anchor(path)
        rec = signing.attest(make_record(), self.priv)
        self.assertTrue(signing.verify(rec, anchor)[0])


class KeyHandling(unittest.TestCase):

    def test_a_private_key_may_not_be_written_into_the_repo(self):
        priv, _ = signing.keypair()
        repo = Path(__file__).resolve().parent.parent.parent
        with self.assertRaises(ValueError):
            signing.write_private_key(str(repo / "leaked.key"), priv,
                                      repo_root=str(repo))

    def test_a_private_key_is_written_0600(self):
        priv, _ = signing.keypair()
        with tempfile.TemporaryDirectory() as d:
            path = signing.write_private_key(os.path.join(d, "k"), priv,
                                             repo_root="/nonexistent-root")
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(signing.read_private_key(path), priv)

    def test_a_short_key_is_refused(self):
        with self.assertRaises(ValueError):
            signing.keypair(seed=b"short")



class AmendmentsAreInsideTheSignature(unittest.TestCase):
    """An amendment changes what the record says, so it must be signed.

    Regression for 2026-09-20. The seal and the attestation cover `body`
    only; `amend()` appends to `record["amendments"]` and states "The body is
    not touched"; `current_view()` derives the EFFECTIVE record by replaying
    those amendments. So the content a reader acts on was decided by data
    outside the signed surface, and a post-hoc verdict flip verified clean.

    `verify_history()` did not help: it checks the chain's own
    view_digest_before/after, which are self-consistent data inside the
    record. An attacker appending an entry simply computes them correctly.
    """

    def setUp(self):
        self.priv, self.pub = signing.keypair(seed=b"\x07" * 32)
        self.kid = signing.key_id(self.pub)
        self.anchor = {self.kid: self.pub}
        self.rec = signing.attest(make_record(verdict="pass"), self.priv)

    def _amend(self, record, value="fail", author="someone"):
        return record_mod.amend(record, author=author, reason="a reason",
                                pointer="/verdict", new_value=value)

    def test_an_unattested_amendment_fails_the_record(self):
        rec = self._amend(self.rec)
        ok, notes = signing.verify(rec, trusted=self.anchor)
        self.assertFalse(ok, "an unsigned verdict change must not verify")
        self.assertIn("not attested", " ".join(notes))

    def test_the_effective_verdict_really_did_change(self):
        # Guards the test above from passing for the wrong reason: if the
        # amendment did not actually alter the view, refusing it proves little.
        rec = self._amend(self.rec)
        self.assertEqual(record_mod.current_view(self.rec)["verdict"], "pass")
        self.assertEqual(record_mod.current_view(rec)["verdict"], "fail")

    def test_the_body_signature_alone_is_not_enough(self):
        # The exact shape of the defect: body untouched, chain self-consistent.
        rec = self._amend(self.rec)
        self.assertEqual(rec["attestation"]["signature"],
                         self.rec["attestation"]["signature"])
        self.assertFalse(record_mod.verify_history(rec),
                         "chain is self-consistent, which is why it is not a control")
        self.assertFalse(signing.verify(rec, trusted=self.anchor)[0])

    def test_a_properly_attested_amendment_verifies(self):
        rec = self._amend(self.rec)
        signing.attest_amendment(rec, 1, self.priv)
        ok, notes = signing.verify(rec, trusted=self.anchor)
        self.assertTrue(ok, notes)
        self.assertIn("amendment 1 attested", " ".join(notes))

    def test_an_amendment_signed_by_an_untrusted_key_fails(self):
        other, _ = signing.keypair(seed=b"\x08" * 32)
        rec = self._amend(self.rec)
        signing.attest_amendment(rec, 1, other)
        ok, notes = signing.verify(rec, trusted=self.anchor)
        self.assertFalse(ok)
        self.assertIn("not in the trust anchor", " ".join(notes))

    def test_a_tampered_amendment_fails_after_signing(self):
        rec = self._amend(self.rec)
        signing.attest_amendment(rec, 1, self.priv)
        rec["amendments"][0]["new_value"] = "pass-with-conditions"
        ok, notes = signing.verify(rec, trusted=self.anchor)
        self.assertFalse(ok)
        self.assertIn("does not verify", " ".join(notes))

    def test_an_amendment_signature_cannot_be_lifted_onto_another_record(self):
        rec = self._amend(self.rec)
        signing.attest_amendment(rec, 1, self.priv)
        stolen = rec["amendments"][0]

        other = signing.attest(make_record(verdict="pass"), self.priv)
        other["record_id"] = "er_other"
        other = self._amend(other)
        other["amendments"][0]["attestation"] = stolen["attestation"]

        ok, notes = signing.verify(other, trusted=self.anchor)
        self.assertFalse(ok, "a signature bound to one record must not travel")

    def test_a_record_attestation_cannot_be_replayed_as_an_amendment(self):
        rec = self._amend(self.rec)
        rec["amendments"][0]["attestation"] = dict(self.rec["attestation"])
        ok, notes = signing.verify(rec, trusted=self.anchor)
        self.assertFalse(ok)
        self.assertIn("context", " ".join(notes))

    def test_an_unamended_record_is_unaffected(self):
        ok, _ = signing.verify(self.rec, trusted=self.anchor)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
