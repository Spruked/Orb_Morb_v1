"""Conformance slice: authority and provenance in the inert simulated host.

These tests do not demonstrate Vault custody, durable ledger recovery,
isolation, authenticated transport, or a deployable MORB engine.
"""
import unittest

from morb_contract import (
    BoundGrant, GrantProposal, InvocationId, ProtocolViolation,
    RecordIdentity, RecordKind,
)
from morb_simhost import EvidenceOrigin, EvidenceSubmission, SimulatedHost


class SimhostTests(unittest.TestCase):
    def setUp(self):
        self.host = SimulatedHost({"read_status": b"healthy", "read_logs": b"logs"})
        self.proposal = GrantProposal(
            "mission-1", {"read_status", "read_logs"},
            {"ops": {"read_status"}, "research": set()},
        )
        self.host.host_assign(self.proposal, {"M": b"mission-supplied-material"})
        self.grant = self.host.host_approve_and_deploy("mission-1", "grant-1")

    def evidence(self, worker, item_id, origin, source_id, content):
        return EvidenceSubmission(
            RecordIdentity(RecordKind.EVIDENCE, "mission-1", worker, item_id),
            origin, source_id, content,
        )

    def test_proposal_alone_cannot_authorize_execution(self):
        host = SimulatedHost({"read_status": b"healthy"})
        proposal = GrantProposal("mission-1", {"read_status"}, {"ops": {"read_status"}})
        host.host_assign(proposal, {})
        forged = BoundGrant(
            "mission-1", "not-approved", 1, "1", {"read_status"},
            {"ops": {"read_status"}},
        )
        with self.assertRaisesRegex(ProtocolViolation, "^grant_not_bound$"):
            host.request_capability(forged, "ops", "read_status", InvocationId("inv-1"))

    def test_revoked_grant_description_still_matches_but_broker_refuses(self):
        self.assertTrue(self.grant.describes_execution_scope("ops", "read_status"))
        self.assertEqual(
            self.host.request_capability(self.grant, "ops", "read_status", InvocationId("inv-1")),
            b"healthy",
        )
        self.host.host_cancel(self.grant.grant_id)
        self.assertTrue(self.grant.describes_execution_scope("ops", "read_status"))
        with self.assertRaisesRegex(ProtocolViolation, "^execution_revoked$"):
            self.host.request_capability(self.grant, "ops", "read_status", InvocationId("inv-2"))

    def test_cancel_preserves_narrow_reporting_but_not_tools(self):
        self.host.host_cancel(self.grant.grant_id)
        self.assertTrue(self.grant.describes_finalization_scope("ops"))
        with self.assertRaisesRegex(ProtocolViolation, "^execution_revoked$"):
            self.host.request_capability(self.grant, "ops", "read_status", InvocationId("new"))
        report = self.host.submit_finalization(self.grant, "ops", "stopped", [])
        self.assertEqual(report.worker_claim, "stopped")
        self.assertFalse(report.claim_verified)

    def test_mission_supplied_evidence_can_be_cited_during_finalization(self):
        self.host.host_cancel(self.grant.grant_id)
        record = self.evidence(
            "research", "E-M", EvidenceOrigin.MISSION_SUPPLIED,
            "M", b"mission-supplied-material",
        )
        receipt = self.host.submit_finalization(self.grant, "research", "I analyzed M", [record])
        self.assertEqual(receipt.provenance_accepted, (record.record,))
        self.assertEqual(receipt.provenance_rejected, ())
        self.assertFalse(receipt.claim_verified)

    def test_pre_revocation_invocation_evidence_remains_traceable(self):
        output = self.host.request_capability(
            self.grant, "ops", "read_status", InvocationId("inv-before"),
        )
        self.host.host_cancel(self.grant.grant_id)
        record = self.evidence(
            "ops", "E-I", EvidenceOrigin.HOST_INVOCATION, "inv-before", output,
        )
        receipt = self.host.submit_finalization(self.grant, "ops", "Observed status", [record])
        self.assertEqual(receipt.provenance_accepted, (record.record,))
        self.assertFalse(receipt.claim_verified)

    def test_untraced_evidence_refused_but_attributed_claim_retained(self):
        self.host.host_cancel(self.grant.grant_id)
        untraced = self.evidence(
            "research", "E-fake", EvidenceOrigin.MISSION_SUPPLIED, "not-M", b"new-data",
        )
        receipt = self.host.submit_finalization(
            self.grant, "research", "I claim E exists", [untraced],
        )
        self.assertEqual(receipt.provenance_accepted, ())
        self.assertEqual(receipt.provenance_rejected, (untraced.record,))
        self.assertFalse(receipt.claim_verified)
        self.assertEqual(receipt.worker_id, "research")
        self.assertEqual(receipt.worker_claim, "I claim E exists")

    def test_wrong_digest_refuses_evidence_even_with_valid_source_id(self):
        self.host.host_cancel(self.grant.grant_id)
        manipulated = self.evidence(
            "research", "E-tampered", EvidenceOrigin.MISSION_SUPPLIED, "M", b"tampered",
        )
        receipt = self.host.submit_finalization(
            self.grant, "research", "My analysis", [manipulated],
        )
        self.assertEqual(receipt.provenance_rejected, (manipulated.record,))

    def test_invocation_reference_cannot_be_reused_by_another_worker(self):
        result = self.host.request_capability(
            self.grant, "ops", "read_status", InvocationId("private-inv"),
        )
        self.host.host_cancel(self.grant.grant_id)
        stolen = self.evidence(
            "research", "E-stolen", EvidenceOrigin.HOST_INVOCATION, "private-inv", result,
        )
        receipt = self.host.submit_finalization(
            self.grant, "research", "Claim about another worker", [stolen],
        )
        self.assertEqual(receipt.provenance_accepted, ())
        self.assertEqual(receipt.provenance_rejected, (stolen.record,))

    def test_zero_tool_worker_may_finalize_but_never_invoke(self):
        self.host.host_cancel(self.grant.grant_id)
        with self.assertRaisesRegex(ProtocolViolation, "^execution_revoked$"):
            self.host.request_capability(
                self.grant, "research", "read_status", InvocationId("blocked"),
            )
        self.assertTrue(self.grant.describes_finalization_scope("research"))
        receipt = self.host.submit_finalization(self.grant, "research", "Could not conclude", [])
        self.assertEqual(receipt.worker_claim, "Could not conclude")

    def test_finalization_closed_is_enforced(self):
        self.host.host_cancel(self.grant.grant_id)
        self.host.host_close_finalization(self.grant.grant_id)
        with self.assertRaisesRegex(ProtocolViolation, "^finalization_closed$"):
            self.host.submit_finalization(self.grant, "research", "I stopped", [])

    def test_forged_grant_cannot_be_used_even_with_live_epoch(self):
        forged = BoundGrant(
            "mission-1", "grant-1", 1, "1",
            {"read_status", "read_logs"}, {"ops": {"read_logs"}, "research": set()},
        )
        with self.assertRaisesRegex(ProtocolViolation, "^grant_not_bound$"):
            self.host.request_capability(
                forged, "ops", "read_logs", InvocationId("forged"),
            )

    def test_worker_attribution_mismatch_is_not_accepted(self):
        self.host.host_cancel(self.grant.grant_id)
        wrong_worker = self.evidence(
            "ops", "e-cross", EvidenceOrigin.MISSION_SUPPLIED,
            "M", b"mission-supplied-material",
        )
        with self.assertRaisesRegex(ProtocolViolation, "^invalid_record_identity$"):
            self.host.submit_finalization(
                self.grant, "research", "Claim cross-worker", [wrong_worker],
            )

    def test_invocation_id_replay_is_bound_to_capability(self):
        invocation = InvocationId("repeat")
        first = self.host.request_capability(
            self.grant, "ops", "read_status", invocation,
        )
        second = self.host.request_capability(
            self.grant, "ops", "read_status", invocation,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(self.host._invocations), 1)
        # A different capability with same invocation id must not initiate
        # another operation; the worker has no scope for read_logs.
        with self.assertRaisesRegex(ProtocolViolation, "^capability_refused$"):
            self.host.request_capability(self.grant, "ops", "read_logs", invocation)

    def test_host_approval_cannot_add_scope_or_workers(self):
        host = SimulatedHost({"read_status": b"healthy"})
        host.host_assign(
            GrantProposal("m", {"read_status"}, {"w": {"read_status"}}), {},
        )
        with self.assertRaisesRegex(ProtocolViolation, "^invalid_worker_scopes$"):
            host.host_approve_and_deploy("m", "g", {"other": set()})
        with self.assertRaisesRegex(ProtocolViolation, "^worker_scope_exceeds_grant$"):
            host.host_approve_and_deploy("m", "g", {"w": {"not_approved"}})

    def test_unknown_report_evidence_type_rejected_at_boundary(self):
        with self.assertRaisesRegex(ProtocolViolation, "^invalid_record_identity$"):
            EvidenceSubmission(
                RecordIdentity(RecordKind.REPORT, "mission-1", "ops", "x"),
                EvidenceOrigin.MISSION_SUPPLIED, "M", b"material",
            )


if __name__ == "__main__":
    unittest.main()
