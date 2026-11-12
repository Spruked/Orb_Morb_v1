"""Draft host-neutral MORB contract models: no execution authority.

Only a host can bind, revoke, verify, or enforce real authority. These
immutable values describe interface messages; they never serve as bearer
permits, trusted runtime identities, Vault writers, or evidence of isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from types import MappingProxyType
from typing import Mapping

PROTOCOL_STATUS = "v1-draft-implementation"
CONTRACT_VERSION = "1.0-draft"
_EPOCH_RE = re.compile(r"^(0|[1-9][0-9]*)$")


class ProtocolViolation(ValueError):
    """A protocol-facing structured violation (reason_code[:detail])."""


def _text(value: object, reason: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ProtocolViolation(reason)
    return value


def _id_collection(values: object, reason: str) -> frozenset[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple, set, frozenset)):
        raise ProtocolViolation(reason)
    result: set[str] = set()
    for item in values:
        result.add(_text(item, reason))
    return frozenset(result)


def _scoped_workers(
    workers: object, allowed: frozenset[str], out_of_scope_reason: str
) -> Mapping[str, frozenset[str]]:
    if not isinstance(workers, Mapping):
        raise ProtocolViolation("invalid_worker_scopes")
    frozen: dict[str, frozenset[str]] = {}
    for worker_id, capabilities in workers.items():
        name = _text(worker_id, "invalid_worker_identity")
        permissions = _id_collection(capabilities, "invalid_capability_name")
        if not permissions.issubset(allowed):
            raise ProtocolViolation(out_of_scope_reason)
        frozen[name] = permissions
    return MappingProxyType(frozen)


def require_epoch(value: object) -> str:
    """Epochs are canonical decimal strings: never JSON numbers or booleans."""
    if not isinstance(value, str) or not _EPOCH_RE.fullmatch(value):
        raise ProtocolViolation("invalid_epoch")
    return value


class FleetState(str, Enum):
    OFF = "off"
    ACTIVE = "active"
    DRAINING = "draining"
    STOPPED = "stopped"


class AssignmentState(str, Enum):
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


_ASSIGNMENT_TRANSITIONS: Mapping[AssignmentState, frozenset[AssignmentState]] = MappingProxyType({
    AssignmentState.ASSIGNED: frozenset({AssignmentState.RUNNING, AssignmentState.CANCELLED, AssignmentState.FAILED}),
    AssignmentState.RUNNING: frozenset({AssignmentState.COMPLETING, AssignmentState.FAILED, AssignmentState.CANCELLED}),
    AssignmentState.COMPLETING: frozenset({AssignmentState.COMPLETED, AssignmentState.FAILED, AssignmentState.CANCELLED}),
    AssignmentState.COMPLETED: frozenset(),
    AssignmentState.FAILED: frozenset(),
    AssignmentState.CANCELLED: frozenset(),
})
_FLEET_TRANSITIONS: Mapping[FleetState, frozenset[FleetState]] = MappingProxyType({
    FleetState.OFF: frozenset({FleetState.ACTIVE}),
    FleetState.ACTIVE: frozenset({FleetState.DRAINING, FleetState.STOPPED}),
    FleetState.DRAINING: frozenset({FleetState.OFF, FleetState.STOPPED}),
    FleetState.STOPPED: frozenset({FleetState.OFF}),
})


def _state(value: object, enum: type[Enum]) -> Enum:
    if not isinstance(value, enum):
        raise ProtocolViolation("unknown_state")
    return value


def require_assignment_transition(before: AssignmentState, after: AssignmentState) -> None:
    """Validate an assignment claim, NOT an authoritative host decision."""
    old = _state(before, AssignmentState)
    new = _state(after, AssignmentState)
    if new not in _ASSIGNMENT_TRANSITIONS[old]:
        raise ProtocolViolation(f"invalid_worker_transition:{old.value}:{new.value}")


def require_fleet_transition(before: FleetState, after: FleetState) -> None:
    """Validate a proposed fleet transition, not proof of execution."""
    old = _state(before, FleetState)
    new = _state(after, FleetState)
    if new not in _FLEET_TRANSITIONS[old]:
        raise ProtocolViolation(f"invalid_fleet_transition:{old.value}:{new.value}")


@dataclass(frozen=True)
class RequestId:
    """Identity for a protocol message and its retries."""
    value: str

    def __post_init__(self) -> None:
        _text(self.value, "invalid_request_id")


@dataclass(frozen=True)
class InvocationId:
    """Identity for one intended consequential operation across retries."""
    value: str

    def __post_init__(self) -> None:
        _text(self.value, "invalid_invocation_id")


@dataclass(frozen=True)
class MessageEnvelope:
    """Common envelope; neither authentication nor permission."""
    contract_version: str
    request_id: RequestId
    sender_id: str
    fleet_id: str
    epoch: str
    mission_id: str | None = None

    def __post_init__(self) -> None:
        _text(self.contract_version, "missing_envelope_field")
        if not isinstance(self.request_id, RequestId):
            raise ProtocolViolation("invalid_request_id")
        _text(self.sender_id, "missing_envelope_field")
        _text(self.fleet_id, "missing_envelope_field")
        require_epoch(self.epoch)
        if self.mission_id is not None:
            _text(self.mission_id, "invalid_mission_id")


@dataclass(frozen=True)
class GrantProposal:
    """Unapproved Assign response. MUST NOT answer authorization questions."""
    mission_id: str
    requested_capabilities: frozenset[str]
    worker_requests: Mapping[str, frozenset[str]]

    def __post_init__(self) -> None:
        _text(self.mission_id, "invalid_grant_identity")
        caps = _id_collection(self.requested_capabilities, "invalid_capability_name")
        workers = _scoped_workers(self.worker_requests, caps, "worker_scope_exceeds_grant")
        object.__setattr__(self, "requested_capabilities", caps)
        object.__setattr__(self, "worker_requests", workers)


@dataclass(frozen=True)
class BoundGrant:
    """Immutable DESCRIPTION of a host-bound grant, never a bearer permit.

    The host broker MUST check its canonical grant, current epoch, current
    revocation status, worker scope and actual policy at invocation time.
    This type cannot make or substitute for that decision.
    """
    mission_id: str
    grant_id: str
    revision: int
    epoch: str
    execution_capabilities: frozenset[str]
    worker_execution_scopes: Mapping[str, frozenset[str]]
    finalization_workers: frozenset[str]

    def __post_init__(self) -> None:
        _text(self.mission_id, "invalid_grant_identity")
        _text(self.grant_id, "invalid_grant_identity")
        if type(self.revision) is not int or self.revision < 1:
            raise ProtocolViolation("invalid_grant_revision")
        require_epoch(self.epoch)
        caps = _id_collection(self.execution_capabilities, "invalid_capability_name")
        scopes = _scoped_workers(self.worker_execution_scopes, caps, "worker_scope_exceeds_grant")
        final = _id_collection(self.finalization_workers, "invalid_worker_identity")
        if not final.issubset(scopes.keys()):
            raise ProtocolViolation("invalid_finalization_scope")
        object.__setattr__(self, "execution_capabilities", caps)
        object.__setattr__(self, "worker_execution_scopes", scopes)
        object.__setattr__(self, "finalization_workers", final)

    def describes_execution_scope(self, worker_id: str, capability: str) -> bool:
        """Static scope description only; never a live authorization verdict."""
        return capability in self.worker_execution_scopes.get(worker_id, frozenset())

    def describes_finalization_scope(self, worker_id: str) -> bool:
        """Static report right, NOT a check of host finalization-window status."""
        return worker_id in self.finalization_workers


class RecordKind(str, Enum):
    EVIDENCE = "evidence"
    REPORT = "report"
    HOST_TERMINAL = "host_terminal"


@dataclass(frozen=True)
class RecordIdentity:
    kind: RecordKind
    mission_id: str
    worker_id: str
    item_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, RecordKind):
            raise ProtocolViolation("invalid_record_kind")
        for value in (self.mission_id, self.worker_id, self.item_id):
            _text(value, "invalid_record_identity")

    def parts(self) -> tuple[str, str, str, str]:
        """Record type participates in canonical identity; no collisions."""
        return self.kind.value, self.mission_id, self.worker_id, self.item_id


class EventAuthority(str, Enum):
    ENGINE_ADVISORY = "engine_advisory"
    HOST_AUTHORITATIVE = "host_authoritative"
    PRESENTATION_ONLY = "presentation_only"


EVENT_AUTHORITY: Mapping[str, EventAuthority] = MappingProxyType({
    "operational_state_changed": EventAuthority.ENGINE_ADVISORY,
    "finding_shared": EventAuthority.ENGINE_ADVISORY,
    "worker_state": EventAuthority.HOST_AUTHORITATIVE,
    "fleet_state_changed": EventAuthority.HOST_AUTHORITATIVE,
    "mission_assigned": EventAuthority.HOST_AUTHORITATIVE,
    "report_accepted": EventAuthority.HOST_AUTHORITATIVE,
    "result_delivered": EventAuthority.HOST_AUTHORITATIVE,
    "mission_terminal": EventAuthority.HOST_AUTHORITATIVE,
    "authority_changed": EventAuthority.HOST_AUTHORITATIVE,
    "error": EventAuthority.HOST_AUTHORITATIVE,
    "presentation_state_changed": EventAuthority.PRESENTATION_ONLY,
})
HOST_ONLY_EVENTS = frozenset(k for k, authority in EVENT_AUTHORITY.items() if authority is EventAuthority.HOST_AUTHORITATIVE)
