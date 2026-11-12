"""MORB host-neutral draft interface primitives; no execution authority."""

from .model import (
    CONTRACT_VERSION, PROTOCOL_STATUS, EventAuthority, FleetState,
    HOST_ONLY_EVENTS, MessageEnvelope, MissionGrantDescription,
    PreservationState, ProtocolViolation, RecordIdentity, RecordKind,
    WorkerState, WorkOutcome, require_epoch, require_fleet_transition,
    require_worker_transition,
)

__all__ = [
    "CONTRACT_VERSION", "PROTOCOL_STATUS", "EventAuthority", "FleetState",
    "HOST_ONLY_EVENTS", "MessageEnvelope", "MissionGrantDescription",
    "PreservationState", "ProtocolViolation", "RecordIdentity", "RecordKind",
    "WorkerState", "WorkOutcome", "require_epoch", "require_fleet_transition",
    "require_worker_transition",
]
