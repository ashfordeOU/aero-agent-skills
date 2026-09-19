#!/usr/bin/env python3
"""Tests for the conformance report.

A report is a claim made to somebody who cannot re-run the work. The tests
that matter are the ones asserting it does not overstate: failures are not
buried, unsigned records are not presented as attested, an empty set does
not render as a clean result, and a signature that did not verify is called
out rather than counted as provenance.

Run: python3 tools/evidence/test_report.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))
from tools.evidence import canonical, report, signing  # noqa: E402


def make_record(ref, overall="PASS", issuer="ashforde-conformance"):
    body = {
        "issued": {"at": "2026-01-01T00:00:00Z", "by": issuer,
                   "tool": "aero-evidence/1.0.0"},
        "subject": {"kind": "leaf", "ref": ref},
        "verdict": {"overall": overall, "counts": {overall: 1}},
    }
    digest = canonical.digest(body)
    return {
        "kind": "aeroskills-evidence-record",
        "schema_version": "1",
        "record_id": "er_" + digest.split(":", 1)[1][:16],
        "body": body,
        "seal": {"algorithm": canonical.DIGEST_ALGORITHM,
                 "canonicalization": canonical.CANONICALIZATION,
                 "body_digest": digest,
                 "binds": signing.BINDS_INTEGRITY},
        "amendments": [],
        "telemetry": {},
    }


class ReportBase(unittest.TestCase):

    def setUp(self):
        self.priv, self.pub = signing.keypair()
        self.trusted = {signing.key_id(self.pub): self.pub}
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, rec):
        path = os.path.join(self.dir.name, rec["record_id"] + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2, sort_keys=True)
        return path

    def render(self, title="Conformance report"):
        rows = report.collect(self.dir.name, self.trusted)
        return report.render_markdown(rows, report.summarise(rows), title), rows


class DoesNotOverstate(ReportBase):

    def test_a_failure_is_listed_before_the_passes(self):
        self.write(signing.attest(make_record("skills/a/b/pass1"), self.priv))
        self.write(signing.attest(make_record("skills/a/b/pass2"), self.priv))
        self.write(signing.attest(make_record("skills/a/b/broken", "FAIL"),
                                  self.priv))
        text, rows = self.render()
        self.assertEqual(rows[0]["overall"], "FAIL")
        findings = text.index("## Findings")
        every = text.index("## Every record in this set")
        self.assertIn("broken", text[findings:every])

    def test_a_clean_set_says_so_without_a_percentage(self):
        self.write(signing.attest(make_record("skills/a/b/c"), self.priv))
        text, _ = self.render()
        self.assertIn("No record reports a verdict other than PASS", text)
        self.assertNotIn("100%", text)

    def test_an_unattested_record_is_not_shown_as_attested(self):
        self.write(make_record("skills/a/b/unsigned"))     # no attest()
        text, _ = self.render()
        self.assertIn("unattested", text)
        self.assertIn("does not prove who issued it", text)

    def test_a_signature_that_does_not_verify_is_called_out(self):
        # Signed by a key the anchor does not carry: a stronger finding than
        # an unsigned record, because provenance was CLAIMED.
        forger, _ = signing.keypair()
        self.write(signing.attest(make_record("skills/a/b/forged"), forger))
        text, _ = self.render()
        self.assertIn("did not verify", text)
        self.assertIn("claimed provenance it could not support", text)

    def test_provenance_is_reported_before_any_verdict(self):
        self.write(signing.attest(make_record("skills/a/b/c"), self.priv))
        text, _ = self.render()
        self.assertLess(text.index("## Provenance"), text.index("## Findings"))

    def test_the_report_states_what_it_does_not_cover(self):
        self.write(signing.attest(make_record("skills/a/b/c"), self.priv))
        text, _ = self.render()
        self.assertIn("What this report does not say", text)
        self.assertIn("its absence is not a pass", text)
        self.assertIn("not certification", text)


class RecordSetDigest(ReportBase):
    """A report must be tied to the evidence it was built from."""

    def test_the_same_records_give_the_same_digest(self):
        self.write(signing.attest(make_record("skills/a/b/c"), self.priv))
        a = report.summarise(report.collect(self.dir.name, self.trusted))
        b = report.summarise(report.collect(self.dir.name, self.trusted))
        self.assertEqual(a["record_set_digest"], b["record_set_digest"])

    def test_adding_a_record_moves_the_digest(self):
        self.write(signing.attest(make_record("skills/a/b/c"), self.priv))
        before = report.summarise(report.collect(self.dir.name, self.trusted))
        self.write(signing.attest(make_record("skills/a/b/d"), self.priv))
        after = report.summarise(report.collect(self.dir.name, self.trusted))
        self.assertNotEqual(before["record_set_digest"],
                            after["record_set_digest"])

    def test_the_digest_appears_in_the_rendered_report(self):
        self.write(signing.attest(make_record("skills/a/b/c"), self.priv))
        text, _ = self.render()
        summary = report.summarise(report.collect(self.dir.name, self.trusted))
        self.assertIn(summary["record_set_digest"], text)


class Counts(ReportBase):

    def test_attested_and_unattested_are_counted_separately(self):
        self.write(signing.attest(make_record("skills/a/b/signed"), self.priv))
        self.write(make_record("skills/a/b/unsigned"))
        s = report.summarise(report.collect(self.dir.name, self.trusted))
        self.assertEqual(s["attested"], 1)
        self.assertEqual(s["unattested"], 1)
        self.assertEqual(s["attested_and_verified"], 1)

    def test_an_untrusted_signature_counts_as_not_verified(self):
        forger, _ = signing.keypair()
        self.write(signing.attest(make_record("skills/a/b/forged"), forger))
        s = report.summarise(report.collect(self.dir.name, self.trusted))
        self.assertEqual(s["attested"], 1)
        self.assertEqual(s["attested_and_verified"], 0)
        self.assertEqual(s["attested_but_not_verified"], 1)


class RefusesToMislead(unittest.TestCase):

    def test_an_empty_directory_is_refused_not_rendered_clean(self):
        # An empty report reads as "nothing wrong". It must not be produced.
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(report.main([d]), 1)

    def test_a_missing_directory_is_an_error(self):
        self.assertEqual(report.main(["/nonexistent-records-dir"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
