#!/usr/bin/env python3
"""Entry condition for system-level electromagnetic verification under
ECSS-E-ST-20-07C clause 5.3.1.

Paraphrased, implementable procedure (no verbatim standard text):

* System-level compatibility work is only meaningful once every unit and
  every subsystem it contains has cleared its own functional acceptance. A
  unit that does not yet work correctly on its own bench turns a system
  finding into an ambiguity: the interaction and the latent unit defect
  produce the same symptom.
* The entry condition is therefore evaluated on an inventory, not on a
  single article. Every unit names the subsystem that holds it, every
  subsystem holds at least one unit, and a unit that names no existing
  parent has no place in the roll-up.
* Acceptance rolls upward. A subsystem cannot be presented as accepted
  while any unit inside it is unaccepted, whatever the subsystem's own
  record says.
* An open non-conformance at or above the blocking severity holds the
  entry, because the system test would be run on an article that is known
  to be wrong.
* A waiver admits an article only when it carries an authority reference
  and has not aged past its validity window. A waiver without an authority
  is an assertion, not a disposition.
* Acceptance evidence ages. Evidence older than the validity window is
  re-confirmed before it is used to authorize a system campaign.

Day values are whole-day counters, so ages are exact integers and no
rounding enters the entry decision.

Stdlib only, offline, deterministic.
"""

import math

# Named tolerance for the one reported fraction; every gating comparison in
# this module is on integers and never touches it.
RATIO_EPS = 1e-9

UNIT = "unit"
SUBSYSTEM = "subsystem"
LEVELS = (UNIT, SUBSYSTEM)

ACCEPTED = "passed"
ACCEPTANCE_STATUSES = ("passed", "failed", "not-run", "waived")

SEVERITY_RANK = {"minor": 1, "major": 2, "critical": 3}

DEFAULT_ENTRY_SPEC = {
    "acceptance_validity_days": 365,
    "waiver_validity_days": 180,
    "blocking_severity_rank": 2,
}


def _require_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, float) and not math.isnan(value) and value.is_integer():
            return int(value)
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    return int(value)


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard entry specification."""
    spec = dict(DEFAULT_ENTRY_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_ENTRY_SPEC:
            raise ValueError("unrecognized entry specification key %r" % (key,))
        number = _require_int(value, "spec %r" % key)
        if number < 0:
            raise ValueError("spec %r must not be negative, got %r" % (key, value))
        spec[key] = number
    return spec


def normalize_status(value):
    """Map an acceptance status to the vocabulary used by the entry check."""
    text = _require_text(value, "acceptance status").strip().lower().replace("_", "-")
    if text not in ACCEPTANCE_STATUSES:
        raise ValueError(
            "unrecognized acceptance status %r (expected one of %s)"
            % (value, ", ".join(ACCEPTANCE_STATUSES))
        )
    return text


def severity_rank(name):
    """Rank one non-conformance severity."""
    text = _require_text(name, "severity").strip().lower()
    if text not in SEVERITY_RANK:
        raise ValueError(
            "unrecognized severity %r (expected one of %s)"
            % (name, ", ".join(sorted(SEVERITY_RANK)))
        )
    return SEVERITY_RANK[text]


def validate_article(article):
    """Normalize one inventory article: a unit or a subsystem."""
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    name = _require_text(article.get("name"), "article 'name'")
    level = article.get("level")
    if level not in LEVELS:
        raise ValueError(
            "article %r has unrecognized level %r (expected one of %s)"
            % (name, level, ", ".join(LEVELS))
        )
    status = normalize_status(article.get("status"))
    parent = article.get("parent")
    if level == UNIT:
        parent = _require_text(parent, "unit %r 'parent'" % name)
        if parent == name:
            raise ValueError("unit %r names itself as its parent subsystem" % (name,))
    elif parent is not None:
        raise ValueError("subsystem %r must not name a parent, got %r" % (name, parent))
    acceptance_day = article.get("acceptance_day")
    if status == ACCEPTED:
        acceptance_day = _require_int(acceptance_day, "article %r acceptance_day" % name)
    elif acceptance_day is not None:
        acceptance_day = _require_int(acceptance_day, "article %r acceptance_day" % name)
    findings_in = article.get("nonconformances", ())
    if not isinstance(findings_in, (list, tuple)):
        raise ValueError("article %r nonconformances must be a sequence" % (name,))
    severities = [severity_rank(item) for item in findings_in]
    waiver = article.get("waiver")
    if waiver is not None and not isinstance(waiver, dict):
        raise ValueError("article %r waiver must be a mapping, got %r" % (name, waiver))
    return {
        "name": name,
        "level": level,
        "parent": parent,
        "status": status,
        "acceptance_day": acceptance_day,
        "severities": severities,
        "waiver": waiver,
    }


def build_inventory(articles):
    """Validate the inventory and its unit-to-subsystem structure."""
    if not isinstance(articles, (list, tuple)) or not articles:
        raise ValueError("articles must be a non-empty sequence")
    records = [validate_article(article) for article in articles]
    names = [record["name"] for record in records]
    if len(set(names)) != len(names):
        raise ValueError("article names must be unique, got %r" % (names,))
    subsystems = {r["name"]: r for r in records if r["level"] == SUBSYSTEM}
    units = [r for r in records if r["level"] == UNIT]
    if not subsystems:
        raise ValueError("the inventory holds no subsystem to enter the system test")
    if not units:
        raise ValueError("the inventory holds no unit under any subsystem")
    children = {name: [] for name in subsystems}
    for unit in units:
        if unit["parent"] not in subsystems:
            raise ValueError(
                "unit %r names subsystem %r which is not in the inventory"
                % (unit["name"], unit["parent"])
            )
        children[unit["parent"]].append(unit["name"])
    empty = [name for name, kids in children.items() if not kids]
    if empty:
        raise ValueError("subsystem(s) %r hold no unit in the inventory" % (sorted(empty),))
    return {"records": records, "subsystems": subsystems, "units": units, "children": children}


def blocking_severities(record, spec=None):
    """Severities on one article at or above the blocking rank."""
    spec = resolve_spec(spec)
    limit = spec["blocking_severity_rank"]
    return [rank for rank in record["severities"] if rank >= limit]


def acceptance_age_days(record, campaign_day):
    """Whole days between the acceptance record and the campaign decision."""
    campaign_day = _require_int(campaign_day, "campaign_day")
    if record["acceptance_day"] is None:
        return None
    age = campaign_day - record["acceptance_day"]
    if age < 0:
        raise ValueError(
            "article %r is accepted on a day after the campaign decision" % (record["name"],)
        )
    return age


def waiver_admissible(waiver, campaign_day, spec=None):
    """Decide whether a waiver may stand in for functional acceptance."""
    spec = resolve_spec(spec)
    campaign_day = _require_int(campaign_day, "campaign_day")
    if not isinstance(waiver, dict):
        raise ValueError("waiver must be a mapping, got %r" % (waiver,))
    authority = waiver.get("authority")
    if not isinstance(authority, str) or not authority.strip():
        return (False, "waiver carries no approving authority reference")
    raised_day = _require_int(waiver.get("raised_day"), "waiver raised_day")
    age = campaign_day - raised_day
    if age < 0:
        raise ValueError("waiver is raised on a day after the campaign decision")
    if age > spec["waiver_validity_days"]:
        return (False, "waiver has aged past its validity window")
    return (True, "waiver admissible")


def article_findings(record, campaign_day, spec=None):
    """Entry findings raised by one article on its own record."""
    spec = resolve_spec(spec)
    findings = []
    if record["status"] == "failed":
        findings.append("%s has not passed functional acceptance" % record["name"])
    elif record["status"] == "not-run":
        findings.append("%s has no functional acceptance result" % record["name"])
    elif record["status"] == "waived":
        if record["waiver"] is None:
            findings.append("%s is waived with no waiver record" % record["name"])
        else:
            admissible, reason = waiver_admissible(record["waiver"], campaign_day, spec)
            if not admissible:
                findings.append("%s: %s" % (record["name"], reason))
    blocking = blocking_severities(record, spec)
    if blocking:
        findings.append(
            "%s carries %d open non-conformance(s) at or above the blocking severity"
            % (record["name"], len(blocking))
        )
    age = acceptance_age_days(record, campaign_day)
    if age is not None and age > spec["acceptance_validity_days"]:
        findings.append("%s acceptance evidence is older than its validity window" % record["name"])
    return findings


def subsystem_rollup(inventory, admitted):
    """Subsystems held by an unadmitted unit beneath them."""
    if not isinstance(admitted, dict):
        raise ValueError("admitted must be a mapping of article name to bool")
    findings = []
    held = {}
    for subsystem, unit_names in sorted(inventory["children"].items()):
        blocked = [name for name in sorted(unit_names) if not admitted.get(name, False)]
        held[subsystem] = blocked
        if blocked:
            findings.append(
                "subsystem %s cannot enter the system test while %s is unaccepted"
                % (subsystem, ", ".join(blocked))
            )
    return {"findings": findings, "held": held}


def admitted_fraction(admitted):
    """Share of inventory articles admitted on their own record."""
    if not isinstance(admitted, dict) or not admitted:
        raise ValueError("admitted must be a non-empty mapping")
    passing = sum(1 for value in admitted.values() if value)
    return passing / float(len(admitted))


def entry_status(findings):
    """Gate token for the finding list of one entry decision."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "system-emc-test-authorized" if not findings else "hold-system-test"


def evaluate_entry_condition(config):
    """End-to-end clause 5.3.1 entry-condition check for one campaign."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    for key in ("articles", "campaign_day"):
        if key not in config:
            raise ValueError("config missing required key %r" % (key,))
    spec = resolve_spec(config.get("spec"))
    campaign_day = _require_int(config["campaign_day"], "campaign_day")
    inventory = build_inventory(config["articles"])

    per_article = []
    admitted = {}
    findings = []
    for record in inventory["records"]:
        own = article_findings(record, campaign_day, config.get("spec"))
        admitted[record["name"]] = not own
        per_article.append(
            {
                "name": record["name"],
                "level": record["level"],
                "parent": record["parent"],
                "status": record["status"],
                "age_days": acceptance_age_days(record, campaign_day),
                "blocking_nonconformances": len(blocking_severities(record, config.get("spec"))),
                "findings": own,
                "admitted": not own,
            }
        )
        findings.extend(own)

    rollup = subsystem_rollup(inventory, admitted)
    findings.extend(rollup["findings"])

    return {
        "spec": spec,
        "articles": per_article,
        "held_subsystems": rollup["held"],
        "admitted_fraction": admitted_fraction(admitted),
        "findings": findings,
        "status": entry_status(findings),
        "authorized": not findings,
    }
