#!/usr/bin/env python3
"""Command line for the evidence record and regrade tooling.

  issue       observe leaves, check them, write sealed records
  regrade     re-verdict stored records against a changed checker set
  verify      structure, seal, amendment chain, re-derived verdicts
  amend       append a post-hoc change without rewriting the body
  show        one record, summarised
  checkerset  print a resolved checker set and its digest

Run it either way:
    python3 tools/evidence/cli.py issue --leaf skills/<...>
    python3 -m evidence.cli issue --leaf skills/<...>        (from tools/)
"""

import argparse
import json
import os
import sys

if __package__ in (None, ""):  # invoked as a script, not as a module
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import evidence  # noqa: F401

    __package__ = "evidence"

from . import canonical, checkers, corpus, observers, record as record_module, regrade as regrade_module, signing  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(os.path.dirname(HERE))


def _load_checkerset(path, label):
    if not path:
        return checkers.build_set(label=label)
    with open(path, "r", encoding="utf-8") as fh:
        overrides = json.load(fh)
    return checkers.build_set(label=label, overrides=overrides)


def _leaf_refs(args):
    refs = list(args.leaf or [])
    if args.leaves_file:
        with open(args.leaves_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    refs.append(line)
    seen, ordered = set(), []
    for ref in refs:
        ref = ref.rstrip("/")
        if ref not in seen:
            seen.add(ref)
            ordered.append(ref)
    return ordered


def _trust_anchor(args):
    """The keys the caller is willing to believe. Never the record's own."""
    path = getattr(args, "trust_anchor", None)
    return signing.load_trust_anchor(path)


def cmd_keygen(args):
    """Mint an issuing key. The private half never enters the repository."""
    private, public = signing.keypair()
    try:
        path = signing.write_private_key(args.out, private)
    except ValueError as exc:
        print("keygen: %s" % exc, file=sys.stderr)
        return 2
    kid = signing.key_id(public)
    print("private key written 0600 to %s" % path)
    print("  NEVER commit it, never copy it to a shared host, and note that")
    print("  the signer is not constant time -- sign offline only.")
    print()
    print("key_id     %s" % kid)
    print("public_key %s" % public.hex())
    print()
    print("Add the public half to tools/evidence/%s to make records issued"
          % signing.TRUST_ANCHOR)
    print("by this key verifiable by anyone:")
    print()
    print('  {"keys": [{"key_id": "%s",' % kid)
    print('             "public_key": "%s",' % public.hex())
    print('             "issuer": "<name>", "status": "active"}]}')
    return 0


def cmd_issue(args):
    refs = _leaf_refs(args)
    if not refs:
        print("issue: no leaves given (--leaf or --leaves-file)", file=sys.stderr)
        return 2
    checker_set = _load_checkerset(args.checkerset, args.label)
    print("checker set '%s' %s" % (checker_set["label"], checker_set["digest"]))
    print("hashing the corpus subtree '%s' ..." % args.subtree)
    corpus_block = corpus.corpus_binding(args.root, args.subtree)
    print(
        "corpus %s  %d files  %d bytes"
        % (corpus_block["subtree_digest"], corpus_block["file_count"], corpus_block["byte_count"])
    )
    runner = observers._runner_path()
    written = []
    for ref in refs:
        rec = record_module.build(
            args.root,
            ref,
            checker_set=checker_set,
            corpus_block=corpus_block,
            issuer=args.issuer,
            runner=runner,
        )
        if getattr(args, "signing_key", None):
            signing.attest(rec, signing.read_private_key(args.signing_key))
        path = record_module.save(rec, args.out)
        written.append(path)
        counts = rec["body"]["verdict"]["counts"]
        print(
            "%-11s %s  %s  %s"
            % (
                rec["body"]["verdict"]["overall"],
                rec["record_id"],
                ref,
                " ".join("%s=%d" % kv for kv in sorted(counts.items())),
            )
        )
    print("%d record(s) written to %s" % (len(written), args.out))
    return 0


def cmd_regrade(args):
    pairs = record_module.load_directory(args.inp)
    if not pairs:
        print("regrade: no records in %s" % args.inp, file=sys.stderr)
        return 2
    records = [rec for _path, rec in pairs]
    checker_set = _load_checkerset(args.checkerset, args.label)
    successors, report = regrade_module.regrade_many(
        records, checker_set, issuer=args.issuer
    )
    for successor in successors:
        record_module.save(successor, args.out)
    print("regrade: %d record(s), corpus re-executed: %s" % (len(records), report["corpus_re_executed"]))
    print(
        "checker set  before %s  after %s (%s)"
        % (
            ", ".join(c["digest"][:23] for c in report["checker_set_before"]),
            checker_set["digest"][:23],
            checker_set["label"],
        )
    )
    print("")
    header = "%-46s %-13s %-13s %s" % ("subject", "before", "after", "gate changes")
    print(header)
    print("-" * len(header))
    for entry in report["records"]:
        changed = [g for g in entry["gates"] if g["change"] != "held"]
        summary = ", ".join(
            "%s %s->%s" % (g["gate"], g["before"], g["after"]) for g in changed
        )
        print(
            "%-46s %-13s %-13s %s"
            % (
                entry["subject"].replace("skills/", ""),
                entry["verdict_before"],
                entry["verdict_after"],
                summary or "(none)",
            )
        )
    print("")
    for key, value in sorted(report["summary"].items()):
        print("%-32s %s" % (key, value))
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(canonical.dumps_pretty(report))
        print("report written to %s" % args.report)
    return 0


def cmd_verify(args):
    failures = 0
    targets = []
    for path in args.paths:
        if os.path.isdir(path):
            targets.extend(p for p, _ in record_module.load_directory(path))
        else:
            targets.append(path)
    for path in targets:
        rec = record_module.load(path)
        report = record_module.verify(rec, recompute=not args.no_recompute)
        # Authenticity is a separate question from integrity, and it is
        # asked against the caller's trust anchor -- never against the key
        # the record carries.
        att_ok, att_notes = signing.verify(
            rec, _trust_anchor(args), require=args.require_attestation)
        if not att_ok:
            report["ok"] = False
        status = "OK  " if report["ok"] else "BAD "
        rederivation = report["rederivation"] or {}
        note = ""
        if rederivation.get("unavailable_checkers"):
            note = " (cannot re-derive: %s)" % ", ".join(rederivation["unavailable_checkers"])
        print("%s%s  %s%s" % (status, report["record_id"], report["subject"], note))
        for problem in report["schema_errors"] + report["history_errors"] + rederivation.get("mismatches", []):
            print("      %s" % problem)
        for line in att_notes:
            print("      %s" % line)
        if not report["ok"]:
            failures += 1
    print("%d record(s) checked, %d bad" % (len(targets), failures))
    return 1 if failures else 0


def cmd_amend(args):
    rec = record_module.load(args.record)
    value = json.loads(args.value)
    amended = record_module.amend(
        rec, args.author, args.reason, args.pointer, value
    )
    with open(args.record, "w", encoding="utf-8") as fh:
        fh.write(canonical.dumps_pretty(amended))
    entry = amended["amendments"][-1]
    print(
        "amendment %d appended to %s by %s"
        % (entry["seq"], amended["record_id"], entry["author"])
    )
    print("  pointer      %s" % entry["pointer"])
    print("  prior value  %s" % json.dumps(entry["prior_value"]))
    print("  new value    %s" % json.dumps(entry["new_value"]))
    print("  reason       %s" % entry["reason"])
    print("  body digest unchanged: %s" % amended["seal"]["body_digest"])
    return 0


def cmd_show(args):
    rec = record_module.load(args.record)
    body = record_module.current_view(rec) if args.amended else rec["body"]
    print("record       %s (%s)" % (rec["record_id"], rec["schema_version"]))
    print("subject      %s" % body["subject"]["ref"])
    print("issued       %s by %s" % (body["issued"]["at"], body["issued"]["by"]))
    print("derivation   %s" % body["derivation"]["kind"])
    print("corpus       %s (%d files)" % (body["corpus"]["subtree_digest"], body["corpus"]["file_count"]))
    print("leaf         %s (%d files)" % (body["leaf"]["leaf_digest"], body["leaf"]["file_count"]))
    print("harness      %s/%s" % (body["versions"]["harness_runtime"]["id"], body["versions"]["harness_runtime"]["version"]))
    print("specification %s/%s" % (body["versions"]["specification"]["id"], body["versions"]["specification"]["version"]))
    print("libm         %s" % body["environment"]["libm"]["fingerprint"])
    print("checker set  %s %s" % (body["checker_set"]["label"], body["checker_set"]["digest"]))
    print("standards    %d in scope, %d without a bound edition" % (
        len(body["standards"]["in_scope"]), len(body["standards"]["edition_gaps"])))
    print("verdict      %s %s" % (body["verdict"]["overall"], body["verdict"]["counts"]))
    for gate in body["gates"]:
        print("  %-18s %-14s %s" % (gate["gate"], gate["outcome"]["verdict"], gate["outcome"]["reason"]))
    if rec["amendments"]:
        print("amendments   %d" % len(rec["amendments"]))
        for entry in rec["amendments"]:
            print(
                "  %d %s %s %s -> %s (%s)"
                % (
                    entry["seq"],
                    entry["at"],
                    entry["pointer"],
                    json.dumps(entry["prior_value"]),
                    json.dumps(entry["new_value"]),
                    entry["author"],
                )
            )
    return 0


def cmd_checkerset(args):
    checker_set = _load_checkerset(args.checkerset, args.label)
    print("label  %s" % checker_set["label"])
    print("digest %s" % checker_set["digest"])
    for entry in checker_set["checkers"]:
        print("")
        print("%s@%s  reads %s@%s" % (entry["id"], entry["version"], entry["observation"], entry["observation_version"]))
        print("  %s" % entry["title"])
        print("  params %s" % json.dumps(entry["params"], sort_keys=True))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="evidence", description=__doc__)
    parser.add_argument("--root", default=DEFAULT_ROOT, help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("issue", help="observe and seal records for leaves")
    p.add_argument("--leaf", action="append", help="repository-relative leaf path")
    p.add_argument("--leaves-file")
    p.add_argument("--out", required=True)
    p.add_argument("--checkerset")
    p.add_argument("--label", default="default")
    p.add_argument("--issuer", default="unattributed")
    p.add_argument("--signing-key", default=None,
                   help="attest each record with this Ed25519 key "
                        "(hex, 32 bytes). Without it the record proves "
                        "integrity but not who issued it.")
    p.add_argument("--subtree", default="skills")
    p.set_defaults(func=cmd_issue)

    p = sub.add_parser("regrade", help="re-verdict stored records, no re-execution")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--checkerset")
    p.add_argument("--label", default="regraded")
    p.add_argument("--issuer", default="unattributed")
    p.add_argument("--report")
    p.set_defaults(func=cmd_regrade)

    p = sub.add_parser("keygen", help="mint an issuing key (private half stays out of the repo)")
    p.add_argument("--out", required=True,
                   help="where to write the private key; must be outside the repository")
    p.set_defaults(func=cmd_keygen)

    p = sub.add_parser("verify", help="check structure, seal, history, verdicts and attestation")
    p.add_argument("--trust-anchor", default=None,
                   help="JSON file of trusted issuing keys. Defaults to the "
                        "committed tools/evidence/trusted-keys.json, so a "
                        "fresh clone can verify with no setup.")
    p.add_argument("--require-attestation", action="store_true",
                   help="fail a record that carries no attestation. Without "
                        "it an unsigned record passes with a note saying it "
                        "proves integrity only.")
    p.add_argument("paths", nargs="+")
    p.add_argument("--no-recompute", action="store_true")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("amend", help="append a post-hoc change")
    p.add_argument("--record", required=True)
    p.add_argument("--author", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--pointer", required=True)
    p.add_argument("--value", required=True, help="the new value, as JSON")
    p.set_defaults(func=cmd_amend)

    p = sub.add_parser("show", help="summarise one record")
    p.add_argument("--record", required=True)
    p.add_argument("--amended", action="store_true", help="show the amended reading")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("checkerset", help="print a resolved checker set")
    p.add_argument("--checkerset")
    p.add_argument("--label", default="default")
    p.set_defaults(func=cmd_checkerset)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
