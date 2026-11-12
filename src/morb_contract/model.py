"""Host-neutral MORB contract primitives (draft; no runtime authority).

These models are transport and validation structures, NOT execution permits,
Vault writers, capability brokers, or proof of an isolated deployment.
Only the host may establish effective authority or authoritative outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Mapping


PROTOCOL_STATUS = "v1-draft-not-owner-approved"
CONTRACT_VERSION = "1.0-draft"
_EPOCH_RE = re.compile(r"^(0|[1-9][0-9]*)$")


class ProtocolViolation(ValueError):
    """A contract structure or state transition is invalid."""


class FleetState(str, Enum):
    OFF = "off"
    ACTIVE = "active"
    DRAINING = "draining"
    STOPPED = "stopped"


class WorkerState(str, Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkOutcome(str, Enum):
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PreservationState(str, Enum):
    PENDING = "pending"
    SEALED = "sealed"
    FAILED = "failed"
    UNPRESERVED = "unpreserved"
    NOT_APPLICABLE = "not_applicable"


# Per-worker assignment lifecycle. Terminal assignments are immutable.
_ALLOWED_WORKER_TRANSITIONS: dict[WorkerState, frozenset[WorkerState]] = {
    WorkerState.AVAILABLE: frozenset({WorkerState.ASSIGNED}),
    WorkerState.ASSIGNED: frozenset({WorkerState.RUNNING, WorkerState.CANCELLED}),
    WorkerState.RUNNING: frozenset({WorkerState.COMPLETING, WorkerState.FAILED, WorkerState.CANCELLED}),
    WorkerState.COMPLETING: frozenset({WorkerState.COMPLETED, WorkerState.FAILED, WorkerState.CANCELLED}),
    WorkerState.COMPLETED: frozenset(),
    WorkerState.FAILED: frozenset(),
    WorkerState.CANCELLED: frozenset(),
}

_ALLOWED_FLEET_TRANSITIONS: dict[FleetState, frozenset[FleetState]] = {
    FleetState.OFF: frozenset({FleetState.ACTIVE}),
    FleetState.ACTIVE: frozenset({FleetState.DRAINING, FleetState.STOPPED}),
    FleetState.DRAINING: frozenset({FleetState.OFF, FleetState.STOPPED}),
    FleetState.STOPPED: frozenset({FleetState.OFF}),
}


def require_worker_transition(before: WorkerState, after: WorkerState) -> None:
    """Validate a reported transition; host must independently reconcile it."""
    if after not in _ALLOWED_WORKER_TRANSITIONS[before]:
        raise ProtocolViolation(f"invalid_worker_transition:{before.value}:{after.value}")


def require_fleet_transition(before: FleetState, after: FleetState) -> None:
    """Validate proposed state; this does not prove engine acknowledgement."""
    if after not in _ALLOWED_FLEET_TRANSITIONS[before]:
        raise ProtocolViolation(f"invalid_fleet_transition:{before.value}:{after.value}")


def require_epoch(value: str) -> str:
    """An epoch is a canonical decimal string, not a float or JS number."""
    if not isinstance(value, str) or not _EPOCH_RE.fullmatch(value):
        raise ProtocolViolation("invalid_epoch")
    return value


@dataclass(frozen=True)
class MessageEnvelope:
    """Common request envelope, not an authentication token."""

    contract_version: str
    request_id: str
    sender_id: str
    fleet_id: str
    epoch: str
    mission_id: str | None = None

    def __post_init__(self) -> None:
        for value in (self.contract_version, self.request_id, self.sender_id, self.fleet_id):
            if not isinstance(value, str) or not value.strip():
                raise ProtocolViolation("missing_envelope_field")
        require_epoch(self.epoch)
        if self.mission_id is not None and not self.mission_id.strip():
            raise ProtocolViolation("invalid_mission_id")


@dataclass(frozen=True)
class MissionGrantDescription:
    """Host-approved scope description, NOT a bearer execution permit.

    Permission enforcement is exclusively performed by the host broker
    against canonical grants and revocations at invocation time.
    """

    mission_id: str
    revision: int
    allowed_capabilities: frozenset[str]
    worker_capabilities: Mapping[str, frozenset[str]]

    def __post_init__(self) -> None:
        if not self.mission_id or self.revision < 1:
            raise ProtocolViolation("invalid_grant_identity")
        if any(not cap for cap in self.allowed_capabilities):
            raise ProtocolViolation("invalid_capability_name")
        for worker, caps in self.worker_capabilities.items():
            if not worker:
                raise ProtocolViolation("invalid_worker_identity")
            if not caps.issubset(self.allowed_capabilities):
                raise ProtocolViolation("worker_scope_exceeds_mission")

    def describes_permission(self, worker_id: str, capability: str) -> bool:
        """Descriptive check only; NOT an authorization decision."""
        return capability in self.worker_capabilities.get(worker_id, frozenset())


class RecordKind(str, Enum):
    EVIDENCE = "evidence"
    REPORT = "report"
    HOST_TERMINAL = "host_terminal"


@dataclass(frozen=True)
class RecordIdentity:
    """Domain-separated identifier for idempotent report/evidence submission."""

    kind: RecordKind
    mission_id: str
    worker_id: str
    item_id: str

    def __post_init__(self) -> None:
        if any(not isinstance(v, str) or not v for v in (self.mission_id, self.worker_id, self.item_id)):
            raise ProtocolViolation("invalid_record_identity")

    def parts(self) -> tuple[str, str, str, str]:
        return (self.kind.value, self.mission_id, self.worker_id, self.item_id)


class EventAuthority(str, Enum):
    ENGINE_ADVISORY = "engine_advisory"
    HOST_AUTHORITATIVE = "host_authoritative"
    PRESENTATION_ONLY = "presentation_only"


HOST_ONLY_EVENTS = frozenset({
    "worker_state", "fleet_state_changed", "mission_assigned",
    "report_accepted", "result_delivered", "mission_terminal", "authority_changed",
})
