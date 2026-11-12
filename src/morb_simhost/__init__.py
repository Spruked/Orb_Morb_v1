"""Simulated host test double; no production capabilities or evidence custody."""
from .host import EvidenceOrigin, EvidenceSubmission, SimulatedHost, SimulatedReportResult

__all__ = [
    "EvidenceOrigin", "EvidenceSubmission", "SimulatedHost", "SimulatedReportResult",
]
