"""Existing software (reused, off-the-shelf, open source) and firmware.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025), clause 6.2.7 (reuse of
existing software: benefit analysis, assessment against functional,
quality and security needs, the quality-level evidence, suitability
aspects, corrective actions, recovery of missing evidence by reverse
engineering or service history, configuration control), clause 7.3
(software developed to be reused) and clause 7.5 (programmable devices,
named firmware before Revision 2). Paraphrased into checks; no requirement
text is reproduced.

Procedure implemented here
--------------------------
1. Sort an item into its kind of existing software; development tools are
   out of scope here and follow the tools clause instead.
2. Grade the quality-level evidence, the suitability aspects and the
   security aspects of an existing item, each gap becoming a corrective
   action for the reuse file.
3. Choose how missing evidence is recovered and grade a service history.
4. Check open-source and third-party licences against the way the product
   is distributed.
5. Check a component built for future reuse.
6. Check a programmable device: programming procedure, marking, the
   calibration of the programming equipment on the day, and the image
   digest against the configuration file.
"""

import datetime
import hashlib

__all__ = [
    "EXISTING_KINDS",
    "QUALITY_EVIDENCE",
    "SUITABILITY_ASPECTS",
    "SECURITY_ASPECTS",
    "SERVICE_HISTORY_ITEMS",
    "categorize_existing",
    "grade_existing_software",
    "choose_recovery",
    "grade_service_history",
    "check_licences",
    "check_intended_reuse",
    "check_programmable_device",
]

EXISTING_KINDS = ("supplier-heritage", "customer-furnished", "cots", "mots",
                  "freeware", "open-source")

# Evidence on which the quality level of an existing item is judged.
QUALITY_EVIDENCE = (
    "requirements-doc", "design-doc", "traceability", "unit-tests-and-coverage",
    "integration-tests-and-coverage", "validation-and-coverage",
    "verification-reports", "performance", "operational-performance",
    "residual-ncr-waivers-alerts", "user-doc", "code-quality",
    "known-vulnerabilities-incl-dependencies",
)

# Further aspects of suitability for reuse.
SUITABILITY_ASPECTS = (
    "acceptance-and-warranty", "support-documentation", "installation-and-training",
    "cm-registration", "maintenance-responsibility", "method-and-tool-durability",
    "ipr-and-modification-rights", "licensing", "exportability",
)

SECURITY_ASPECTS = ("authorisation-for-use", "security-sensitivity",
                    "security-assurance-requirements", "security-evaluation-or-certification")

SERVICE_HISTORY_ITEMS = (
    "relevance-to-new-environment", "cm-and-change-control", "problem-reporting-effectiveness",
    "error-rates-and-maintenance-records", "modification-impact", "vulnerability-statistics",
)

# Evidence a category D item may lack without it being a gap; everything
# else is expected for A to C.
_D_OPTIONAL = {"unit-tests-and-coverage", "integration-tests-and-coverage", "design-doc"}

_STRONG_COPYLEFT = {"GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later",
                    "AGPL-3.0-only", "AGPL-3.0-or-later"}
_WEAK_COPYLEFT = {"LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0-only", "LGPL-3.0-or-later",
                  "MPL-2.0", "EPL-2.0"}
_PERMISSIVE = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "Zlib", "BSL-1.0"}


def categorize_existing(item):
    """Return the kind of existing software, or 'tool' for development tools.

    item: dict with origin in EXISTING_KINDS and is_tool (bool).
    """
    if item.get("is_tool"):
        return "tool"
    kind = str(item.get("origin", "")).lower()
    if kind not in EXISTING_KINDS:
        raise ValueError("unknown existing-software origin %r" % (kind,))
    return kind


def grade_existing_software(item, category, sensitive=False):
    """Grade an existing item for the reuse file.

    item: dict with evidence (set of QUALITY_EVIDENCE keys held),
        suitability (set of SUITABILITY_ASPECTS assessed), security (set of
        SECURITY_ASPECTS assessed), benefit_analysis (bool).
    Returns dict(quality_gaps, suitability_gaps, security_gaps,
        corrective_actions, level) where level is 'full', 'partial' or
        'insufficient' reuse evidence.
    """
    cat = str(category).strip().upper()
    if cat not in ("A", "B", "C", "D"):
        raise ValueError("unknown software criticality category %r" % (category,))
    held = set(item.get("evidence") or ())
    needed = [e for e in QUALITY_EVIDENCE if not (cat == "D" and e in _D_OPTIONAL)]
    q_gaps = [e for e in needed if e not in held]
    s_gaps = [a for a in SUITABILITY_ASPECTS if a not in set(item.get("suitability") or ())]
    sec_needed = SECURITY_ASPECTS if sensitive else ("authorisation-for-use", "security-sensitivity")
    sec_gaps = [a for a in sec_needed if a not in set(item.get("security") or ())]
    actions = []
    if not item.get("benefit_analysis"):
        actions.append("record why reuse is preferred over new development")
    actions += ["recover evidence: %s" % g for g in q_gaps]
    actions += ["assess: %s" % g for g in s_gaps + sec_gaps]
    if not q_gaps and not s_gaps and not sec_gaps:
        level = "full"
    elif len(q_gaps) <= len(needed) // 2:
        level = "partial"
    else:
        level = "insufficient"
    return {"quality_gaps": q_gaps, "suitability_gaps": s_gaps, "security_gaps": sec_gaps,
            "corrective_actions": actions, "level": level}


def choose_recovery(lifecycle_data_available, source_available):
    """Choose how missing evidence of an existing item is recovered.

    With life cycle data or source code, reverse engineering generates the
    missing documents and coverage. Without them, verification documents
    are built from the user documentation and tests are run to reach the
    coverage, and product service history is argued. Returns a list of
    method keys.
    """
    if lifecycle_data_available or source_available:
        return ["reverse-engineering"]
    return ["user-doc-based-vv-and-testing", "service-history"]


def grade_service_history(history):
    """Grade a product service history argument.

    history: mapping SERVICE_HISTORY_ITEMS key -> evidence text, plus
        optional numbers operating_hours and errors_found.
    Returns dict(missing, error_rate_per_1000h or None, usable).
    """
    missing = [k for k in SERVICE_HISTORY_ITEMS if not str(history.get(k) or "").strip()]
    rate = None
    hours = history.get("operating_hours")
    if hours:
        rate = round(1000.0 * float(history.get("errors_found") or 0) / float(hours), 3)
    return {"missing": missing, "error_rate_per_1000h": rate,
            "usable": not missing and rate is not None}


def check_licences(components, distribution, modified=()):
    """Check third-party licences against how the product is distributed.

    components: mapping name -> SPDX licence identifier (or '' unknown).
    distribution: 'internal', 'binary-to-customer' or 'source-to-customer'.
    modified: names of components the supplier changed.
    Returns a list of (component, finding); unknown licences always block.
    """
    if distribution not in ("internal", "binary-to-customer", "source-to-customer"):
        raise ValueError("unknown distribution %r" % (distribution,))
    out = []
    for name, lic in sorted(dict(components).items()):
        lic = str(lic or "").strip()
        if not lic or lic in ("NOASSERTION", "UNKNOWN"):
            out.append((name, "licence unknown: reuse blocked until established"))
        elif lic in _STRONG_COPYLEFT:
            if lic.startswith("AGPL") or distribution != "internal":
                out.append((name, "%s: source of the combined work owed to recipients" % lic))
        elif lic in _WEAK_COPYLEFT:
            if distribution != "internal" and name in modified:
                out.append((name, "%s: source of the modified component owed" % lic))
        elif lic not in _PERMISSIVE:
            out.append((name, "%s: not on the reviewed list, needs legal review" % lic))
    return out


def check_intended_reuse(component):
    """Check a component developed so that later projects can reuse it.

    component: dict with separate_docs, self_contained_docs (bools),
        ts_requirements (set of 'maintainability', 'portability',
        'verification'), cm_provisions (set of 'long-lifetime',
        'environment-evolution', 'transfer-to-next-project'),
        target_platforms, tested_platforms (lists), coc_limitations (text).
    Returns a list of findings.
    """
    found = []
    if not component.get("separate_docs"):
        found.append("reuse component not separated in the documentation")
    if not component.get("self_contained_docs"):
        found.append("reuse component documentation not self-contained")
    for r in ("maintainability", "portability", "verification"):
        if r not in set(component.get("ts_requirements") or ()):
            found.append("technical specification lacks %s requirements" % r)
    for p in ("long-lifetime", "environment-evolution", "transfer-to-next-project"):
        if p not in set(component.get("cm_provisions") or ()):
            found.append("configuration management lacks provision: %s" % p)
    untested = sorted(set(component.get("target_platforms") or ()) -
                      set(component.get("tested_platforms") or ()))
    if untested and not str(component.get("coc_limitations") or "").strip():
        found.append("not tested on %s and the certificate of conformance states no limitation"
                     % ", ".join(untested))
    return found


def check_programmable_device(device, image=None):
    """Check a programmed device (FPGA configuration, PROM, flash image).

    device: dict with programming_procedure, duplication_procedure (bools),
        marking_hw_ref, marking_sw_ref (text), marking_indelible (bool),
        marking_required (protective marking needed, bool),
        protective_marking (text), programmed_on (ISO date),
        calibration_valid_until (ISO date of the programmer's calibration),
        scf_digest (sha256 hex recorded in the configuration file).
    image: bytes programmed into the device; its SHA-256 is compared with
        the configuration file digest.
    Returns a list of findings.
    """
    found = []
    if not device.get("programming_procedure"):
        found.append("no device programming procedure")
    if not device.get("duplication_procedure"):
        found.append("no procedure for duplicating programmed devices")
    if not str(device.get("marking_hw_ref") or "").strip() or \
            not str(device.get("marking_sw_ref") or "").strip():
        found.append("marking does not identify both hardware and software references")
    if not device.get("marking_indelible"):
        found.append("marking is not indelible")
    if device.get("marking_required") and not str(device.get("protective_marking") or "").strip():
        found.append("protective marking required and absent")
    try:
        prog = datetime.date.fromisoformat(str(device.get("programmed_on")))
        cal = datetime.date.fromisoformat(str(device.get("calibration_valid_until")))
        if prog > cal:
            found.append("programming equipment out of calibration on %s" % prog.isoformat())
    except ValueError:
        found.append("programming date or calibration date missing")
    if image is not None:
        if hashlib.sha256(image).hexdigest() != str(device.get("scf_digest") or "").lower():
            found.append("programmed image does not match the configuration file digest")
    return found
