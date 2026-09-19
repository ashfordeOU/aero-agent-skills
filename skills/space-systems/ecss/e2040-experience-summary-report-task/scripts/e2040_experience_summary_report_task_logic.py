"""Applicability and completeness assessment for the Experience Summary Report.

Anchor: ECSS-E-ST-20-40C clause 5.8.4 (validation, qualification and
acceptance phase -- capturing the lessons of the development when the
customer asks for such a record). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide applicability first. The report is owed only when the customer has
   asked for it, so a development with no request owes nothing and must not
   be graded as if it did.
2. When a report exists, check that every mandated topic is present.
3. Walk the development event log -- anomalies, tool defects, design
   changes, waivers, methodology deviations, reuse candidates -- and trace
   each event into the topic that is supposed to carry it.
4. Separate the three ways an event can fail to land: carried nowhere,
   carried into a topic that does not own that kind of event, or carried
   into a topic the report never wrote.
5. Weight the major events above the minor ones, since a report that
   captured every trivial item and lost the significant ones is not a
   lessons record.
6. Return a completeness index and one of three dispositions.
"""

import math

__all__ = [
    "COMPLETENESS_TOLERANCE",
    "DISPOSITIONS",
    "EVENT_KINDS",
    "EVENT_TOPIC",
    "MANDATED_TOPICS",
    "SIGNIFICANCE_WEIGHT",
    "WEIGHT_EVENTS",
    "WEIGHT_TOPICS",
    "report_applicability",
    "validate_event",
    "validate_report",
    "topic_coverage",
    "event_capture",
    "completeness_index",
    "assess_experience_summary_report",
]

# The completeness index mixes two integer ratios through float weights; an
# exact unity can land a few ULP either side, so absorb the representation
# error here rather than lowering what "complete" means.
COMPLETENESS_TOLERANCE = 1e-9

# The topics a lessons record has to carry.
MANDATED_TOPICS = (
    "design-issues",
    "tool-issues",
    "methodology-effectiveness",
    "anomalies-and-resolution",
    "reuse-recommendations",
    "schedule-and-effort-deviations",
)

# Which topic owns which kind of development event.
EVENT_TOPIC = {
    "anomaly": "anomalies-and-resolution",
    "tool-defect": "tool-issues",
    "design-change": "design-issues",
    "waiver": "design-issues",
    "methodology-deviation": "methodology-effectiveness",
    "reuse-candidate": "reuse-recommendations",
    "schedule-slip": "schedule-and-effort-deviations",
}
EVENT_KINDS = tuple(sorted(EVENT_TOPIC))

SIGNIFICANCE_WEIGHT = {"minor": 1, "major": 3}

WEIGHT_TOPICS = 0.4
WEIGHT_EVENTS = 0.6

DISPOSITIONS = ("not-required", "complete", "incomplete")


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    return stripped


def report_applicability(customer_requested, request_reference=None):
    """Return whether the report is owed, and on what authority."""
    if not isinstance(customer_requested, bool):
        raise ValueError(
            "customer_requested must be a boolean, got %r" % (customer_requested,)
        )
    if customer_requested:
        reference = _text(request_reference, "request_reference")
        return {"required": True, "request_reference": reference}
    if request_reference is not None:
        raise ValueError(
            "a request reference was given but customer_requested is false; "
            "settle which one is right before grading the report"
        )
    return {"required": False, "request_reference": None}


def validate_event(record):
    """Return a normalised development-event record."""
    if not isinstance(record, dict):
        raise ValueError("event record must be a mapping, got %r" % (record,))
    eid = _text(record.get("id"), "event id")
    kind = _text(record.get("kind"), "event %s kind" % eid).lower()
    if kind not in EVENT_TOPIC:
        raise ValueError(
            "event %s has an unknown kind %r; expected one of %s"
            % (eid, kind, ", ".join(EVENT_KINDS))
        )
    significance = _text(record.get("significance"), "event %s significance" % eid).lower()
    if significance not in SIGNIFICANCE_WEIGHT:
        raise ValueError(
            "event %s significance %r is not one of %s"
            % (eid, significance, ", ".join(sorted(SIGNIFICANCE_WEIGHT)))
        )
    carried = record.get("carried_into")
    if carried is not None:
        carried = _text(carried, "event %s carried_into" % eid).lower()
    return {
        "id": eid,
        "kind": kind,
        "significance": significance,
        "carried_into": carried,
        "owning_topic": EVENT_TOPIC[kind],
    }


def validate_report(record):
    """Return the normalised set of topics the report actually writes."""
    if not isinstance(record, dict):
        raise ValueError("report record must be a mapping, got %r" % (record,))
    topics = record.get("topics")
    if isinstance(topics, str) or not isinstance(topics, (list, tuple)):
        raise ValueError("report topics must be a list of topic names")
    written = []
    for item in topics:
        name = _text(item, "report topic").lower()
        if name not in MANDATED_TOPICS:
            raise ValueError(
                "report topic %r is outside the mandated set %s"
                % (item, ", ".join(MANDATED_TOPICS))
            )
        written.append(name)
    if len(set(written)) != len(written):
        raise ValueError("the report writes the same topic twice")
    issue = _text(record.get("issue", "draft"), "report issue").lower()
    if issue not in ("draft", "issued"):
        raise ValueError("report issue %r must be draft or issued" % issue)
    return {"topics": sorted(written), "issue": issue}


def topic_coverage(report):
    """Return which mandated topics the report writes and which it omits."""
    checked = report if "topics" in report and "issue" in report else validate_report(report)
    written = set(checked["topics"])
    missing = sorted(name for name in MANDATED_TOPICS if name not in written)
    return {
        "written_topics": sorted(written),
        "missing_topics": missing,
        "topic_fraction": (len(MANDATED_TOPICS) - len(missing)) / float(len(MANDATED_TOPICS)),
    }


def event_capture(events, written_topics):
    """Return how much of the development event log the report captured."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence")
    if isinstance(written_topics, str) or not isinstance(written_topics, (list, tuple, set)):
        raise ValueError("written_topics must be a collection of topic names")
    written = set(written_topics)
    checked = [validate_event(item) for item in events]
    ids = [e["id"] for e in checked]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate event id in the development log")
    if not checked:
        return {
            "uncarried_event_ids": [],
            "misfiled_event_ids": [],
            "carried_into_unwritten_topic_ids": [],
            "captured_weight": 0,
            "total_weight": 0,
            "event_fraction": 1.0,
        }
    uncarried = []
    misfiled = []
    unwritten = []
    captured_weight = 0
    total_weight = 0
    for event in checked:
        weight = SIGNIFICANCE_WEIGHT[event["significance"]]
        total_weight += weight
        target = event["carried_into"]
        if target is None:
            uncarried.append(event["id"])
            continue
        if target not in MANDATED_TOPICS:
            raise ValueError(
                "event %s is carried into %r, which is not a mandated topic"
                % (event["id"], target)
            )
        if target != event["owning_topic"]:
            misfiled.append(event["id"])
            continue
        if target not in written:
            unwritten.append(event["id"])
            continue
        captured_weight += weight
    return {
        "uncarried_event_ids": sorted(uncarried),
        "misfiled_event_ids": sorted(misfiled),
        "carried_into_unwritten_topic_ids": sorted(unwritten),
        "captured_weight": captured_weight,
        "total_weight": total_weight,
        "event_fraction": captured_weight / float(total_weight),
    }


def completeness_index(topic_fraction, event_fraction):
    """Combine topic coverage and event capture into one index in [0, 1]."""
    for label, value in (
        ("topic_fraction", topic_fraction),
        ("event_fraction", event_fraction),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        v = float(value)
        if not math.isfinite(v) or v < 0.0 or v > 1.0:
            raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return WEIGHT_TOPICS * float(topic_fraction) + WEIGHT_EVENTS * float(event_fraction)


def assess_experience_summary_report(spec):
    """Run the full clause 5.8.4 experience summary report assessment.

    spec keys: customer_requested; optional request_reference, report, events.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "customer_requested" not in spec:
        raise ValueError("spec missing required key 'customer_requested'")
    applicability = report_applicability(
        spec["customer_requested"], spec.get("request_reference")
    )
    report = spec.get("report")

    if not applicability["required"]:
        if report is None:
            return {
                "required": False,
                "disposition": "not-required",
                "topic_fraction": None,
                "event_fraction": None,
                "completeness_index": None,
                "findings": [],
            }
        # A report offered without a request is still read, but its shortfalls
        # are informational: nothing was owed.
        coverage = topic_coverage(validate_report(report))
        capture = event_capture(spec.get("events", []), coverage["written_topics"])
        index = completeness_index(coverage["topic_fraction"], capture["event_fraction"])
        return {
            "required": False,
            "disposition": "not-required",
            "topic_fraction": coverage["topic_fraction"],
            "event_fraction": capture["event_fraction"],
            "completeness_index": index,
            "findings": ["a report was offered although the customer asked for none"],
        }

    if report is None:
        return {
            "required": True,
            "request_reference": applicability["request_reference"],
            "disposition": "incomplete",
            "topic_fraction": 0.0,
            "event_fraction": 0.0,
            "completeness_index": 0.0,
            "findings": [
                "the customer asked for an experience summary report (%s) and none exists"
                % applicability["request_reference"]
            ],
        }

    checked_report = validate_report(report)
    coverage = topic_coverage(checked_report)
    capture = event_capture(spec.get("events", []), coverage["written_topics"])
    index = completeness_index(coverage["topic_fraction"], capture["event_fraction"])

    findings = []
    if coverage["missing_topics"]:
        findings.append(
            "mandated topic(s) the report never writes: %s"
            % ", ".join(coverage["missing_topics"])
        )
    if capture["uncarried_event_ids"]:
        findings.append(
            "development event(s) carried into no topic: %s"
            % ", ".join(capture["uncarried_event_ids"])
        )
    if capture["misfiled_event_ids"]:
        findings.append(
            "development event(s) carried into a topic that does not own that kind: %s"
            % ", ".join(capture["misfiled_event_ids"])
        )
    if capture["carried_into_unwritten_topic_ids"]:
        findings.append(
            "development event(s) carried into a topic the report never writes: %s"
            % ", ".join(capture["carried_into_unwritten_topic_ids"])
        )
    if checked_report["issue"] != "issued":
        findings.append("the report is still a draft and has not been issued")

    complete = math.isclose(index, 1.0, rel_tol=0.0, abs_tol=COMPLETENESS_TOLERANCE)
    return {
        "required": True,
        "request_reference": applicability["request_reference"],
        "topic_fraction": coverage["topic_fraction"],
        "event_fraction": capture["event_fraction"],
        "completeness_index": index,
        "missing_topics": coverage["missing_topics"],
        "uncarried_event_ids": capture["uncarried_event_ids"],
        "misfiled_event_ids": capture["misfiled_event_ids"],
        "disposition": "complete" if (complete and not findings) else "incomplete",
        "findings": findings,
    }
