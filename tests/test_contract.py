"""Draft conformance tests: pure contract behavior, no live runtime."""
import unittest

from morb_contract import (
    CONTRACT_VERSION, EventAuthority, FleetState, HOST_ONLY_EVENTS,
    MessageEnvelope, MissionGrantDescription, PreservationState,
    ProtocolViolation, RecordIdentity, RecordKind, WorkerState,
    require_epoch, require_fleet_transition, require_worker_transition,
)


class ContractModelTests(unittest.TestCase):
    def test_envelope_accepts_canonical_epoch(self):
        e = MessageEnvelope(CONTRACT_VERSION, "request-1", "host", "fleet-1", "22")
        self.assertEqual(e.epoch, "22")

    def test_epoch_rejects_noncanonical_numbers(self):
        for epoch in ("01", "-1", "1.0", " 1", "", 1):
            with self.subTest(epoch=epoch), self.assertRaises(ProtocolViolation):
                require_epoch(epoch)

    def test_envelope_rejects_missing_sender(self):
        with self.assertRaises(ProtocolViolation):
            MessageEnvelope(CONTRACT_VERSION, "r1", "", "fleet", "1")

    def test_assign_then_run(self):
        require_worker_transition(WorkerState.AVAILABLE, WorkerState.ASSIGNED)
        require_worker_transition(WorkerState.ASSIGNED, WorkerState.RUNNING)
        require_worker_transition(WorkerState.RUNNING, WorkerState.COMPLETING)
        require_worker_transition(WorkerState.COMPLETING, WorkerState.COMPLETED)

    def test_worker_cannot_claim_completion_before_work(self):
        with self.assertRaises(ProtocolViolation):
            require_worker_transition(WorkerState.ASSIGNED, WorkerState.COMPLETED)

    def test_worker_terminal_assignment_cannot_restart(self):
        with self.assertRaises(ProtocolViolation):
            require_worker_transition(WorkerState.COMPLETED, WorkerState.RUNNING)

    def test_cancel_before_deploy(self):
        require_worker_transition(WorkerState.ASSIGNED, WorkerState.CANCELLED)

    def test_fleet_activation_does_not_create_workers(self):
        require_fleet_transition(FleetState.OFF, FleetState.ACTIVE)

    def test_drain_and_stop_are_distinct(self):
        require_fleet_transition(FleetState.ACTIVE, FleetState.DRAINING)
        require_fleet_transition(FleetState.DRAINING, FleetState.OFF)
        require_fleet_transition(FleetState.ACTIVE, FleetState.STOPPED)
        with self.assertRaises(ProtocolViolation):
            require_fleet_transition(FleetState.STOPPED, FleetState.ACTIVE)

    def test_worker_scope_must_be_subset(self):
        with self.assertRaises(ProtocolViolation):
            MissionGrantDescription("mission", 1, frozenset({"read_logs"}), {"worker": frozenset({"restart_server"})})

    def test_worker_restriction_and_attribution(self):
        g = MissionGrantDescription("mission", 2, frozenset({"read_logs", "read_status"}), {
            "diagnostic": frozenset({"read_logs"}), "observer": frozenset({"read_status"})
        })
        self.assertTrue(g.describes_permission("diagnostic", "read_logs"))
        self.assertFalse(g.describes_permission("diagnostic", "read_status"))
        self.assertFalse(g.describes_permission("unknown", "read_logs"))

    def test_distinct_record_namespaces(self):
        identities = [RecordIdentity(kind, "mission", "worker", "1").parts() for kind in RecordKind]
        self.assertEqual(len(set(identities)), len(RecordKind))

    def test_report_identity_distinguishes_workers(self):
        a = RecordIdentity(RecordKind.REPORT, "mission", "worker-a", "1").parts()
        b = RecordIdentity(RecordKind.REPORT, "mission", "worker-b", "1").parts()
        self.assertNotEqual(a, b)

    def test_preservation_does_not_equal_work_outcome(self):
        self.assertNotEqual(PreservationState.PENDING, PreservationState.SEALED)

    def test_result_delivered_is_host_only(self):
        self.assertIn("result_delivered", HOST_ONLY_EVENTS)
        self.assertEqual(EventAuthority.HOST_AUTHORITATIVE.value, "host_authoritative")


if __name__ == "__main__":
    unittest.main()
