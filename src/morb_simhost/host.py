"""In-memory simulated MORB host for contract conformance tests.

No external tools, secrets, operating-system actions, durable custody, real
authorization, A.I.M.S. integration, or production protocol endpoints.
Grant and evidence checks exercise *host-owned* state, not bearer tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Mapping, Sequence

from morb_contract import (
    BoundGrant, GrantProposal, InvocationId, ProtocolViolation,
    RecordIdentity, RecordKind, require_epoch,
)


class EvidenceOrigin(str, Enum):
    MISSION_SUPPLIED = "mission_supplied"
    HOST_INVOCATION = "host_invocation"


@dataclass(frozen=True)
class EvidenceSubmission:
    """Claimed evidence whose provenance the host must independently match."""
    record: RecordIdentity
    origin: EvidenceOrigin
    source_id: str
    content: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.record, RecordIdentity) or self.record.kind is not RecordKind.EVIDENCE:
            raise ProtocolViolation("invalid_record_identity")
        if not isinstance(self.origin, EvidenceOrigin):
            raise ProtocolViolation("evidence_unresolved")
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ProtocolViolation("evidence_unresolved")
        if not isinstance(self.content, bytes):
            raise ProtocolViolation("evidence_unresolved")


@dataclass(frozen=True)
class EvidenceRejection:
    """A provenance failure, not a verdict about the worker's claim."""
    record: RecordIdentity
    reason_code: str


@dataclass(frozen=True)
class SimulatedReportResult:
    """Not a Vault receipt. An attributed claim is never proof of truth."""
    mission_id: str
    worker_id: str
    worker_claim: str
    claim_verified: bool
    provenance_accepted: tuple[RecordIdentity, ...]
    provenance_rejected: tuple[EvidenceRejection, ...]


@dataclass(frozen=True)
class _Invocation:
    worker_id: str
    capability: str
    result: bytes
    digest: str


class SimulatedHost:
    """A deterministic in-memory host policy test double.

    Methods named host_* represent privileged host actions in the harness.
    No network listener or engine-accessible endpoint is exposed.
    Cancel closes execution immediately but preserves a narrow, explicitly
    closable terminal-reporting window. No wall-clock deadline is claimed.
    """

    def __init__(self, capability_fixtures: Mapping[str, bytes], epoch: str = "1") -> None:
        self.epoch = require_epoch(epoch)
        if not isinstance(capability_fixtures, Mapping):
            raise ProtocolViolation("capability_refused")
        self._fixtures: dict[str, bytes] = {}
        for name, result in capability_fixtures.items():
            if not isinstance(name, str) or not name or not isinstance(result, bytes):
                raise ProtocolViolation("capability_refused")
            self._fixtures[name] = bytes(result)
        self._proposals: dict[str, GrantProposal] = {}
        self._assigned_material: dict[tuple[str, str], str] = {}
        self._grants: dict[str, BoundGrant] = {}
        self._revoked: set[str] = set()
        self._finalization_closed: set[str] = set()
        self._invocations: dict[tuple[str, str, str], _Invocation] = {}
        self._reports: list[SimulatedReportResult] = []
        # One terminal report per (grant, worker); identical retries return
        # the original in-memory result without creating a second record.
        self._finalizations: dict[
            tuple[str, str],
            tuple[tuple[str, tuple[EvidenceSubmission, ...]], SimulatedReportResult],
        ] = {}

    def host_assign(self, proposal: GrantProposal, mission_material: Mapping[str, bytes]) -> None:
        """Host records material digests at Assign; proposals authorize nothing."""
        if not isinstance(proposal, GrantProposal) or not isinstance(mission_material, Mapping):
            raise ProtocolViolation("invalid_grant_identity")
        if proposal.mission_id in self._proposals:
            raise ProtocolViolation("record_conflict")
        source_digests: dict[tuple[str, str], str] = {}
        for reference, content in mission_material.items():
            if not isinstance(reference, str) or not reference.strip() or not isinstance(content, bytes):
                raise ProtocolViolation("invalid_record_identity")
            source_digests[(proposal.mission_id, reference)] = sha256(content).hexdigest()
        self._proposals[proposal.mission_id] = proposal
        self._assigned_material.update(source_digests)

    def host_approve_and_deploy(
        self, mission_id: str, grant_id: str,
        approved_worker_scopes: Mapping[str, frozenset[str]] | None = None,
    ) -> BoundGrant:
        """Host-only test fixture for approval; never accepts an engine-issued grant."""
        proposal = self._proposals.get(mission_id)
        if proposal is None:
            raise ProtocolViolation("grant_not_bound")
        if grant_id in self._grants or any(g.mission_id == mission_id for g in self._grants.values()):
            raise ProtocolViolation("record_conflict")
        if approved_worker_scopes is None:
            selected: Mapping[str, frozenset[str]] = proposal.worker_requests
        else:
            if not isinstance(approved_worker_scopes, Mapping):
                raise ProtocolViolation("invalid_worker_scopes")
            selected = {}
            for worker, capabilities in approved_worker_scopes.items():
                if worker not in proposal.worker_requests:
                    raise ProtocolViolation("invalid_worker_scopes")
                if not isinstance(capabilities, (set, frozenset, tuple, list)):
                    raise ProtocolViolation("invalid_capability_name")
                try:
                    requested = frozenset(capabilities)
                except (TypeError, ValueError):
                    raise ProtocolViolation("invalid_capability_name") from None
                if not requested.issubset(proposal.worker_requests[worker]):
                    raise ProtocolViolation("worker_scope_exceeds_grant")
                selected[worker] = requested
        # Describe only capabilities actually approved for at least one worker.
        effective_capabilities = frozenset(
            capability for worker_caps in selected.values() for capability in worker_caps
        )
        grant = BoundGrant(
            mission_id, grant_id, 1, self.epoch,
            effective_capabilities, selected,
        )
        self._grants[grant_id] = grant
        return grant

    def _canonical_grant(self, description: BoundGrant) -> BoundGrant:
        if not isinstance(description, BoundGrant):
            raise ProtocolViolation("grant_not_bound")
        canonical = self._grants.get(description.grant_id)
        if canonical is None or canonical != description:
            raise ProtocolViolation("grant_not_bound")
        if description.epoch != self.epoch:
            raise ProtocolViolation("stale_epoch")
        return canonical

    def request_capability(
        self, grant: BoundGrant, worker_id: str,
        capability: str, invocation_id: InvocationId,
    ) -> bytes:
        """Broker executes *only* an inert fixture after checking host state."""
        canonical = self._canonical_grant(grant)
        if canonical.grant_id in self._revoked:
            raise ProtocolViolation("execution_revoked")
        if not isinstance(invocation_id, InvocationId):
            raise ProtocolViolation("invalid_invocation_id")
        if not canonical.describes_execution_scope(worker_id, capability):
            raise ProtocolViolation("capability_refused")
        if capability not in self._fixtures:
            raise ProtocolViolation("capability_refused")
        key = (canonical.grant_id, worker_id, invocation_id.value)
        recorded = self._invocations.get(key)
        if recorded is not None:
            if recorded.capability != capability:
                raise ProtocolViolation("record_conflict")
            return recorded.result
        output = self._fixtures[capability]
        self._invocations[key] = _Invocation(worker_id, capability, output, sha256(output).hexdigest())
        return output

    def host_cancel(self, grant_id: str) -> None:
        """Simulation: execution revocation precedes report finalization."""
        if grant_id not in self._grants:
            raise ProtocolViolation("grant_not_bound")
        self._revoked.add(grant_id)

    def host_close_finalization(self, grant_id: str) -> None:
        """Deterministic substitute for the real host's finalization deadline."""
        if grant_id not in self._grants:
            raise ProtocolViolation("grant_not_bound")
        self._finalization_closed.add(grant_id)

    def submit_finalization(
        self, grant: BoundGrant, worker_id: str, claim: str,
        evidence: Sequence[EvidenceSubmission],
    ) -> SimulatedReportResult:
        """Accept attributed claims; validate evidence provenance independently.

        A rejected evidence item is NEVER treated as verified. The report
        continues as an attributed, unverified worker claim so loss of proof
        does not erase accountability. This is not durable report custody.
        """
        canonical = self._canonical_grant(grant)
        if not canonical.describes_finalization_scope(worker_id):
            raise ProtocolViolation("grant_not_bound")
        if canonical.grant_id in self._finalization_closed:
            raise ProtocolViolation("finalization_closed")
        if not isinstance(claim, str) or not claim.strip():
            raise ProtocolViolation("invalid_record_identity")
        if not isinstance(evidence, (tuple, list)):
            raise ProtocolViolation("invalid_record_identity")
        # Check all evidence identities before committing any report state.
        # Exact repeated entries are collapsed; a conflicting record payload
        # or provenance source under the same identity is a hard conflict.
        seen: dict[RecordIdentity, EvidenceSubmission] = {}
        normalized: list[EvidenceSubmission] = []
        for item in evidence:
            if not isinstance(item, EvidenceSubmission):
                raise ProtocolViolation("invalid_record_identity")
            if item.record.mission_id != canonical.mission_id or item.record.worker_id != worker_id:
                raise ProtocolViolation("invalid_record_identity")
            prior = seen.get(item.record)
            if prior is not None:
                if prior != item:
                    raise ProtocolViolation("record_conflict")
                continue
            seen[item.record] = item
            normalized.append(item)

        submission = (claim, tuple(normalized))
        finalization_key = (canonical.grant_id, worker_id)
        existing = self._finalizations.get(finalization_key)
        if existing is not None:
            if existing[0] == submission:
                return existing[1]
            raise ProtocolViolation("record_conflict")

        accepted: list[RecordIdentity] = []
        rejected: list[EvidenceRejection] = []
        for item in normalized:
            digest = sha256(item.content).hexdigest()
            expected_digest: str | None
            if item.origin is EvidenceOrigin.MISSION_SUPPLIED:
                expected_digest = self._assigned_material.get(
                    (canonical.mission_id, item.source_id)
                )
            else:
                logged = self._invocations.get((canonical.grant_id, worker_id, item.source_id))
                expected_digest = logged.digest if logged is not None else None

            if expected_digest is None:
                rejected.append(EvidenceRejection(item.record, "evidence_unresolved:source_not_found"))
            elif expected_digest != digest:
                rejected.append(EvidenceRejection(item.record, "evidence_unresolved:digest_mismatch"))
            else:
                accepted.append(item.record)

        result = SimulatedReportResult(
            canonical.mission_id, worker_id, claim, False,
            tuple(accepted), tuple(rejected),
        )
        self._finalizations[finalization_key] = (submission, result)
        self._reports.append(result)
        return result
