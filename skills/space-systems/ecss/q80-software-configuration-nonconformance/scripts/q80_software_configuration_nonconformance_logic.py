"""Software configuration management and problem/nonconformance control.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025), clause 6.2.4 (software
configuration management on top of the project configuration standard:
regeneration from backup, the configuration file and release document with
every delivery, controlled documents, corruption protection, integrity and
authenticity, delivery labelling, branching and merging) and clauses 5.2.5
and 5.2.6 (software problem reports, their interface with the
nonconformance system, the review board and its dispositions). Paraphrased
into checks; no requirement text is reproduced.

Procedure implemented here
--------------------------
1. Grade a software configuration management plan for the provisions it
   must contain.
2. Check a controlled-document register for the document families that
   must be under control.
3. Check a delivery: label content, configuration file and release
   document, and the integrity value recomputed from the delivered bytes.
4. Check the configuration file is current at each milestone that owes it.
5. Move a software problem report through its states, refusing illegal
   moves and closure without the content a closed report carries.
6. Decide whether a problem becomes a nonconformance, and check a
   nonconformance disposition and its board.
"""

import hashlib

__all__ = [
    "SCMP_PROVISIONS",
    "CONTROLLED_FAMILIES",
    "SPR_STATES",
    "SPR_TRANSITIONS",
    "DISPOSITIONS",
    "check_scm_plan",
    "check_controlled_documents",
    "integrity_value",
    "check_delivery",
    "check_scf_currency",
    "spr_transition",
    "qualifies_as_nonconformance",
    "check_ncr_disposition",
]

# Provisions the software configuration management plan must make.
SCMP_PROVISIONS = (
    "regenerate-reference-version-from-backup",
    "branching-and-merging-procedure",
    "generator-customisation-under-control",
    "change-control-procedure",
    "corruption-protection-method",
    "integrity-and-authenticity-mechanism",
)

# Families of documents that must be under document control.
CONTROLLED_FAMILIES = (
    "quality-procedures", "planning", "phase-inputs", "phase-outputs",
    "vv-plans-and-results", "test-specifications-procedures-reports",
    "traceability-matrices", "validation-control", "operator-and-user-docs",
    "maintenance-docs", "retirement-docs",
)

SPR_STATES = ("open", "analysed", "dispositioned", "implemented", "verified",
              "closed", "rejected")
SPR_TRANSITIONS = {
    "open": ("analysed", "rejected"),
    "analysed": ("dispositioned", "rejected"),
    "dispositioned": ("implemented", "closed"),
    "implemented": ("verified", "analysed"),
    "verified": ("closed", "analysed"),
    "closed": ("open",),
    "rejected": ("open",),
}

# Fields a report must carry before it can be closed after a fix.
_SPR_CLOSE_FIELDS = ("item", "description", "recommended_solution",
                     "final_disposition", "modifications", "tests_rerun")

DISPOSITIONS = ("use-as-is", "fix", "return-to-supplier")
_FIX_KINDS = ("correction", "patch", "redesign")
_MILESTONES = ("srr", "pdr", "cdr", "qr", "ar", "orr")


def check_scm_plan(provisions, uses_code_generator=False):
    """Return the provisions missing from a configuration management plan.

    provisions: mapping provision key -> section reference (empty when the
        plan does not cover it).
    The generator provision is owed only when user-customisable code
    generator components exist.
    """
    missing = []
    for key in SCMP_PROVISIONS:
        if key == "generator-customisation-under-control" and not uses_code_generator:
            continue
        if not str((provisions or {}).get(key) or "").strip():
            missing.append(key)
    return missing


def check_controlled_documents(register):
    """Check a document register for the families under control.

    register: list of dicts with id, family (from CONTROLLED_FAMILIES) and
        controlled (bool, i.e. identified, versioned and approved).
    Returns dict(missing_families, uncontrolled ids, unknown_family ids).
    """
    present, uncontrolled, unknown = set(), [], []
    for doc in register:
        fam = doc.get("family")
        if fam not in CONTROLLED_FAMILIES:
            unknown.append(doc.get("id"))
            continue
        present.add(fam)
        if not doc.get("controlled"):
            uncontrolled.append(doc.get("id"))
    return {
        "missing_families": [f for f in CONTROLLED_FAMILIES if f not in present],
        "uncontrolled": sorted(uncontrolled),
        "unknown_family": sorted(unknown),
    }


def integrity_value(data, algorithm="sha256"):
    """Return the hex integrity value of delivered bytes (sha256 or sha512)."""
    if algorithm not in ("sha256", "sha512"):
        raise ValueError("unsupported integrity algorithm %r" % (algorithm,))
    return hashlib.new(algorithm, data).hexdigest()


def check_delivery(delivery, payload=None, marking_required=False):
    """Check one software delivery from supplier to customer.

    delivery: dict with name, version, scf_ref (configuration file
        reference), release_document (id), integrity (dict algorithm,
        value, as recorded in the configuration file), marking (protective
        marking text), distribution_caveats (text or empty; may be empty
        when there are none, but must then be stated as 'none').
    payload: delivered bytes; when given, the integrity value is recomputed.

    Returns dict(findings, recomputed, verdict 'accept' or 'reject').
    """
    found = []
    for key, text in (("name", "software name"), ("version", "version number"),
                      ("scf_ref", "configuration file reference"),
                      ("release_document", "release document")):
        if not str(delivery.get(key) or "").strip():
            found.append("delivery lacks the %s" % text)
    if marking_required and not str(delivery.get("marking") or "").strip():
        found.append("protective marking required and absent")
    if not str(delivery.get("distribution_caveats") or "").strip():
        found.append("distribution caveats not stated (write 'none' when there are none)")
    integ = delivery.get("integrity") or {}
    recomputed = None
    if not str(integ.get("value") or "").strip():
        found.append("no integrity value in the configuration file")
    elif payload is not None:
        recomputed = integrity_value(payload, integ.get("algorithm", "sha256"))
        if recomputed != str(integ["value"]).lower():
            found.append("integrity value does not match the delivered bytes")
    return {"findings": found, "recomputed": recomputed,
            "verdict": "reject" if found else "accept"}


def check_scf_currency(scf_issues, baselines, milestone):
    """Check the software configuration file is current at each milestone.

    scf_issues: mapping milestone -> baseline id the configuration file
        describes at that milestone.
    baselines: mapping milestone -> the baseline actually presented.
    The file is owed from CDR on (CDR, QR, AR, ORR).
    Returns the list of (milestone, problem).
    """
    ms = str(milestone).lower()
    if ms not in _MILESTONES:
        raise ValueError("unknown milestone %r" % (milestone,))
    out = []
    for m in _MILESTONES[2:_MILESTONES.index(ms) + 1]:
        described = str(scf_issues.get(m) or "").strip()
        actual = str(baselines.get(m) or "").strip()
        if not described:
            out.append((m, "no configuration file"))
        elif actual and described != actual:
            out.append((m, "file describes %s, baseline presented is %s" % (described, actual)))
    return out


def spr_transition(report, target):
    """Move a software problem report to a new state.

    report: dict with state and the _SPR_CLOSE_FIELDS keys as available.
    Closing after a fix (from 'verified') needs every close field; closing
    from 'dispositioned' is allowed only for use-as-is, which needs the
    item, description and final disposition. Returns the updated copy;
    raises ValueError on an illegal move or missing content.
    """
    cur = report.get("state", "open")
    if cur not in SPR_STATES or target not in SPR_STATES:
        raise ValueError("unknown state %r -> %r" % (cur, target))
    if target not in SPR_TRANSITIONS[cur]:
        raise ValueError("illegal move %s -> %s" % (cur, target))
    if target == "closed":
        if cur == "dispositioned":
            if str(report.get("final_disposition", "")).lower() != "use-as-is":
                raise ValueError("only a use-as-is disposition closes without a fix")
            need = ("item", "description", "final_disposition")
        else:
            need = _SPR_CLOSE_FIELDS
        missing = [f for f in need if not report.get(f)]
        if missing:
            raise ValueError("cannot close, missing: %s" % ", ".join(missing))
    if target == "rejected" and not str(report.get("rationale") or "").strip():
        raise ValueError("a rejected report needs a rationale")
    new = dict(report)
    new["state"] = target
    return new


def qualifies_as_nonconformance(report, ncr_from, current_milestone):
    """Apply the project's problem-to-nonconformance interface.

    The assurance plan names the life cycle point from which nonconformance
    procedures apply (ncr_from). From then on, a problem in a baselined
    item, a problem against a requirement of the customer, or a problem
    in procured software becomes a nonconformance.

    report: dict with baselined (bool), against_customer_requirement
        (bool), procured (bool).
    Returns (bool, reason).
    """
    ncr_from, now = str(ncr_from).lower(), str(current_milestone).lower()
    if ncr_from not in _MILESTONES or now not in _MILESTONES:
        raise ValueError("unknown milestone")
    if _MILESTONES.index(now) < _MILESTONES.index(ncr_from):
        return False, "before the point from which nonconformance procedures apply"
    for key, why in (("procured", "problem in procured software"),
                     ("against_customer_requirement", "departure from a customer requirement"),
                     ("baselined", "problem in a baselined item")):
        if report.get(key):
            return True, why
    return False, "internal problem in a non-baselined item"


def check_ncr_disposition(ncr, board_roles):
    """Check a software nonconformance disposition and its board.

    ncr: dict with id, disposition (DISPOSITIONS), fix_kind (for fix),
        procured (bool), possible_security_impact (bool), justification.
    board_roles: iterable of roles present.
    Returns a list of findings.
    """
    found = []
    roles = {str(r).lower() for r in board_roles}
    for role in ("software-product-assurance", "software-engineering"):
        if role not in roles:
            found.append("board lacks %s" % role)
    if ncr.get("possible_security_impact") and "software-security" not in roles:
        found.append("board lacks software-security for a possible security impact")
    disp = ncr.get("disposition")
    if disp not in DISPOSITIONS:
        found.append("disposition %r is not use-as-is, fix or return-to-supplier" % (disp,))
    elif disp == "fix" and ncr.get("fix_kind") not in _FIX_KINDS:
        found.append("fix without saying correction, patch or redesign")
    elif disp == "return-to-supplier" and not ncr.get("procured"):
        found.append("return to supplier used for software that was not procured")
    elif disp == "use-as-is" and not str(ncr.get("justification") or "").strip():
        found.append("use-as-is without a usability justification")
    return found
