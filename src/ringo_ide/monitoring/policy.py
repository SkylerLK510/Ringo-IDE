"""Monitoring hook; no rules, classifier, or escalation behavior is implemented."""

from typing import Literal, Protocol

from ringo_ide.editor.context.provider import DocumentSnapshot

MonitoringDecision = Literal["ignore", "suggest", "escalate"]


class MonitoringPolicy(Protocol):
    def decide(self, snapshot: DocumentSnapshot) -> MonitoringDecision:
        """Assess an editor snapshot; not implemented."""
        ...
