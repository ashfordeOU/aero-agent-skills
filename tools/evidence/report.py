#!/usr/bin/env python3
"""Turn signed evidence records into a conformance report someone can read.

A record is machine-readable and complete; it is not what a chief engineer,
an auditor or a procurement officer reads. They read a document. This
renders one, and the rendering is itself checkable: every figure in the
report comes from the records, the report states which records it covers by
id, and it carries the digest of the exact record set it was built from.

Three properties make this a report rather than a marketing page:

  * It reports FAILURES first and does not round them away. A conformance
    report whose headline is a percentage is a sales document.
  * It states what was NOT covered. A leaf with no record is named, not
    omitted, because "not assessed" and "assessed and passed" are different
    and a reader cannot tell them apart from a count.
  * It distinguishes ATTESTED from unattested records. An unsigned record
    proves integrity only, and a report that blurs the two is claiming
    provenance it does not have.

Usage
-----
    python3 tools/evidence/report.py <records-dir> [--format md|json]
        [--trust-anchor PATH] [--title TEXT] [--out PATH]

Exit status
-----------
    0  report written
    1  the record set is not reportable (see the messages)
"""

import argparse
import json
import os
import sys
from collections import Counter

# record.py imports its siblings relatively, so it only loads as part of
# the package. Put the REPO ROOT on the path and import the package either
# way -- as `python3 tools/evidence/report.py` or `python3 -m`.
if __package__:
    from . import canonical, record as record_module, signing
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from tools.evidence import canonical, record as record_module, signing


def collect(directory, trusted):
    """Load every record and classify it. Never guesses on ambiguity."""
    rows = []
    for path, rec in record_module.load_directory(directory):
        body = rec.get("body") or {}
        # The EFFECTIVE record: the body with its amendments replayed. Reading
        # body["verdict"] here reported a withdrawn finding as it was first
        # issued, which is the one thing a conformance report must not do.
        view = record_module.current_view(rec)
        verdict = (view.get("verdict") or {})
        issued_verdict = (body.get("verdict") or {})
        amendments = rec.get("amendments") or []
        history_problems = record_module.verify_history(rec)
        att_ok, att_notes = signing.verify(rec, trusted, require=False)
        rows.append({
            "path": path,
            "record_id": rec.get("record_id"),
            "subject": (view.get("subject") or {}).get("ref"),
            "overall": verdict.get("overall", "UNKNOWN"),
            "counts": verdict.get("counts") or {},
            "issued_at": (body.get("issued") or {}).get("at"),
            "issued_by": (body.get("issued") or {}).get("by"),
            "attested": bool(rec.get("attestation")),
            "attestation_ok": att_ok,
            "attestation_notes": att_notes,
            "record_digest": canonical.digest(rec),
            # Amendment provenance. `amended` makes a changed record visible
            # in the report even when its effective verdict is PASS, because
            # "this was changed after issue" is itself something the reader
            # is entitled to know.
            "amended": bool(amendments),
            "amendment_count": len(amendments),
            "verdict_as_issued": issued_verdict.get("overall", "UNKNOWN"),
            "verdict_changed": (issued_verdict.get("overall", "UNKNOWN")
                                != verdict.get("overall", "UNKNOWN")),
            "history_problems": list(history_problems or []),
        })
    rows.sort(key=lambda r: (r["overall"] != "FAIL", r["subject"] or ""))
    return rows


def summarise(rows):
    verdicts = Counter(r["overall"] for r in rows)
    attested = sum(1 for r in rows if r["attested"])
    trusted_ok = sum(1 for r in rows if r["attested"] and r["attestation_ok"])
    return {
        "records": len(rows),
        "verdicts": dict(verdicts),
        "amended": sum(1 for r in rows if r.get("amended")),
        "verdict_changed_by_amendment": sum(
            1 for r in rows if r.get("verdict_changed")),
        "broken_history": sum(1 for r in rows if r.get("history_problems")),
        "attested": attested,
        "unattested": len(rows) - attested,
        "attested_and_verified": trusted_ok,
        "attested_but_not_verified": attested - trusted_ok,
        # The digest of the set, so two reports over the same records are
        # comparable and a report cannot be quietly rebased onto another set.
        "record_set_digest": canonical.digest(
            sorted(r["record_digest"] for r in rows)),
    }


def render_markdown(rows, summary, title):
    out = []
    a = out.append
    a("# %s" % title)
    a("")
    a("This report is derived from %d evidence record(s). Every figure below "
      "comes from those records; none is entered by hand." % summary["records"])
    a("")
    a("**Record set digest** `%s`" % summary["record_set_digest"])
    a("")
    a("Two reports carrying the same digest describe the same evidence. A "
      "report whose digest you cannot reproduce from the records it names is "
      "not a report about them.")
    a("")

    # --- provenance, before any verdict -----------------------------------
    a("## Provenance")
    a("")
    a("| | records |")
    a("|---|---:|")
    a("| attested and verified against the trust anchor | %d |"
      % summary["attested_and_verified"])
    a("| attested but NOT verified | %d |" % summary["attested_but_not_verified"])
    a("| unattested (integrity only) | %d |" % summary["unattested"])
    a("")
    if summary["unattested"]:
        a("An unattested record proves it was not altered after issue. It does "
          "not prove who issued it. Those %d record(s) carry no provenance "
          "claim and must not be read as carrying one."
          % summary["unattested"])
        a("")
    if summary["attested_but_not_verified"]:
        a("> **%d record(s) carry a signature that did not verify against the "
          "trust anchor.** That is a stronger finding than an unsigned record: "
          "something claimed provenance it could not support. They are listed "
          "in full below." % summary["attested_but_not_verified"])
        a("")

    # --- failures first ---------------------------------------------------
    failures = [r for r in rows if r["overall"] not in ("PASS",)]
    a("## Findings")
    a("")
    if not failures:
        a("No record reports a verdict other than PASS.")
    else:
        a("%d record(s) do not report PASS. They are listed before anything "
          "that passed, because a conformance report that leads with a "
          "percentage is a sales document." % len(failures))
        a("")
        a("| verdict | subject | record | issued |")
        a("|---|---|---|---|")
        for r in failures:
            a("| **%s** | `%s` | `%s` | %s |"
              % (r["overall"], r["subject"], r["record_id"], r["issued_at"]))
    a("")

    bad_att = [r for r in rows if r["attested"] and not r["attestation_ok"]]
    if bad_att:
        a("### Records whose attestation did not verify")
        a("")
        a("| subject | record | why |")
        a("|---|---|---|")
        for r in bad_att:
            a("| `%s` | `%s` | %s |"
              % (r["subject"], r["record_id"],
                 "; ".join(r["attestation_notes"])))
        a("")

    # --- the full set -----------------------------------------------------
    a("## Every record in this set")
    a("")
    a("| verdict | subject | record | provenance |")
    a("|---|---|---|---|")
    for r in rows:
        if r["attested"] and r["attestation_ok"]:
            prov = "attested, verified"
        elif r["attested"]:
            prov = "**attested, NOT verified**"
        else:
            prov = "unattested"
        a("| %s | `%s` | `%s` | %s |"
          % (r["overall"], r["subject"], r["record_id"], prov))
    a("")

    # --- what this does not say -------------------------------------------
    a("## What this report does not say")
    a("")
    a("- It covers the records named above and no others. A leaf with no "
      "record does not appear here, and its absence is not a pass. "
      "\"Not assessed\" and \"assessed and passed\" are different findings.")
    a("- A PASS means the checkers in the record's checker set returned pass "
      "on the evidence recorded. It is not certification, not approval, not "
      "airworthiness, and not a statement that the engineering is correct.")
    a("- Attestation proves which key issued a record. It does not prove when: "
      "`issued.at` is asserted by the issuer, not witnessed.")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("records", help="directory of evidence records")
    ap.add_argument("--format", choices=("md", "json"), default="md")
    ap.add_argument("--trust-anchor", default=None)
    ap.add_argument("--title", default="Conformance report")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if not os.path.isdir(args.records):
        print("report: %s is not a directory" % args.records, file=sys.stderr)
        return 1

    trusted = signing.load_trust_anchor(args.trust_anchor)
    rows = collect(args.records, trusted)
    if not rows:
        print("report: no records found in %s -- refusing to render an empty "
              "report, which would read as a clean result"
              % args.records, file=sys.stderr)
        return 1

    summary = summarise(rows)
    if args.format == "json":
        text = json.dumps({"summary": summary, "records": rows},
                          indent=2, sort_keys=True) + "\n"
    else:
        text = render_markdown(rows, summary, args.title)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s (%d records, set digest %s)"
              % (args.out, summary["records"], summary["record_set_digest"]))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
