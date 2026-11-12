"""Simulated host test double; no production capabilities or evidence custody."""
from .host import (
    EvidenceOrigin, EvidenceRejection, EvidenceSubmission,
    SimulatedHost, SimulatedReportResult,
)

__all__ = [
    "EvidenceOrigin", "EvidenceRejection", "EvidenceSubmission",
    "SimulatedHost", "SimulatedReportResult",
]
