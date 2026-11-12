"""Pure MORB contract conformance tests; never execute consequential work."""
from dataclasses import FrozenInstanceError
import ast
from pathlib import Path
import unittest

from morb_contract import (
    AssignmentState, BoundGrant, CONTRACT_VERSION, EVENT_AUTHORITY, EventAuthority,
    FleetState, GrantProposal, HOST_ONLY_EVENTS, InvocationId, MessageEnvelope,
    PreservationState, ProtocolViolation, RecordIdentity, RecordKind, RequestId,
    require_assignment_transition, require_epoch, require_fleet_transition,
)

ASSIGNMENT_ALLOWED = {
    AssignmentState.ASSIGNED: {AssignmentState.RUNNING, AssignmentState.FAILED, AssignmentState.CANCELLED},
    AssignmentState.RUNNING: {AssignmentState.COMPLETING, AssignmentState.FAILED, AssignmentState.CANCELLED},
    AssignmentState.COMPLETING: {AssignmentState.COMPLETED, AssignmentState.FAILED, AssignmentState.CANCELLED},
    AssignmentState.COMPLETED: set(),
    AssignmentState.FAILED: set(),
    AssignmentState.CANCELLED: set(),
}
FLEET_ALLOWED = {
    FleetState.OFF: {FleetState.ACTIVE},
    FleetState.ACTIVE: {FleetState.DRAINING, FleetState.STOPPED},
    FleetState.DRAINING: {FleetState.OFF, FleetState.STOPPED},
    FleetState.STOPPED: {FleetState.OFF},
}


class ContractTests(unittest.TestCase):
    def test_envelope_accepts_epoch_and_request_id(self):
        e = MessageEnvelope(CONTRACT_VERSION, RequestId("r-1"), "host", "fleet-1", "22")
        self.assertEqual(e.epoch, "22")
        self.assertIsInstance(e.request_id, RequestId)

    def test_invalid_epoch(self):
        for value in ("01", "-1", "1.0", " 1", "", 1, True, None):
            with self.subTest(value=value), self.assertRaises(ProtocolViolation):
                require_epoch(value)

    def test_malformed_envelopes_are_protocol_violations(self):
        bad = [
            (CONTRACT_VERSION, RequestId("ok"), "", "fleet", "1", None),
            (CONTRACT_VERSION, RequestId("ok"), "host", "fleet", "1", 5),
            (CONTRACT_VERSION, "not-a-RequestId", "host", "fleet", "1", None),
            (CONTRACT_VERSION, RequestId("ok"), "host", "fleet", "1", " "),
        ]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ProtocolViolation):
                MessageEnvelope(*args)

    def test_request_and_invocation_id_types_are_distinct(self):
        self.assertNotEqual(type(RequestId("x")), type(InvocationId("x")))
        with self.assertRaises(ProtocolViolation):
            MessageEnvelope(CONTRACT_VERSION, InvocationId("x"), "host", "fleet", "1")
        for cls in (RequestId, InvocationId):
            for value in ("", " ", 42):
                with self.subTest(cls=cls, value=value), self.assertRaises(ProtocolViolation):
                    cls(value)

    def test_assignment_transition_complete_sweep(self):
        self.assertEqual(set(ASSIGNMENT_ALLOWED), set(AssignmentState))
        for old in AssignmentState:
            for new in AssignmentState:
                with self.subTest(old=old, new=new):
                    if new in ASSIGNMENT_ALLOWED[old]:
                        require_assignment_transition(old, new)
                    else:
                        with self.assertRaisesRegex(ProtocolViolation, "invalid_worker_transition"):
                            require_assignment_transition(old, new)

    def test_fleet_transition_complete_sweep(self):
        for old in FleetState:
            for new in FleetState:
                with self.subTest(old=old, new=new):
                    if new in FLEET_ALLOWED[old]:
                        require_fleet_transition(old, new)
                    else:
                        with self.assertRaisesRegex(ProtocolViolation, "invalid_fleet_transition"):
                            require_fleet_transition(old, new)

    def test_unknown_states_are_structured_violations(self):
        for before, after in (("bogus", AssignmentState.RUNNING), (AssignmentState.RUNNING, "bogus"), (None, None)):
            with self.subTest(before=before, after=after), self.assertRaisesRegex(ProtocolViolation, "unknown_state"):
                require_assignment_transition(before, after)
        with self.assertRaisesRegex(ProtocolViolation, "unknown_state"):
            require_fleet_transition("bogus", FleetState.ACTIVE)

    def test_grant_proposal_is_not_a_permission(self):
        p = GrantProposal("mission", {"read_log"}, {"worker": {"read_log"}})
        self.assertFalse(hasattr(p, "describes_execution_scope"))
        self.assertFalse(hasattr(p, "grant_id"))
        self.assertEqual(p.worker_requests["worker"], frozenset({"read_log"}))

    def test_proposal_immutability_copies_caller_data(self):
        scopes = {"worker": {"read_log"}}
        allowed = {"read_log"}
        p = GrantProposal("mission", allowed, scopes)
        scopes["worker"].add("restart_server")
        scopes["new"] = {"restart_server"}
        allowed.add("restart_server")
        self.assertEqual(set(p.worker_requests), {"worker"})
        self.assertEqual(p.worker_requests["worker"], frozenset({"read_log"}))
        self.assertEqual(p.requested_capabilities, frozenset({"read_log"}))
        with self.assertRaises(TypeError):
            p.worker_requests["new"] = frozenset()

    def test_bound_grant_immutability_copies_caller_data(self):
        allowed = {"read_log", "status"}
        scopes = {"worker": {"read_log"}}
        g = BoundGrant("mission", "grant", 1, "17", allowed, scopes)
        scopes["worker"].add("restart_server")
        scopes["ghost"] = {"status"}
        allowed.add("restart_server")
        self.assertEqual(g.execution_capabilities, frozenset({"read_log", "status"}))
        self.assertEqual(g.worker_execution_scopes["worker"], frozenset({"read_log"}))
        self.assertEqual(set(g.worker_execution_scopes), {"worker"})
        self.assertFalse(g.describes_execution_scope("worker", "restart_server"))
        self.assertFalse(g.describes_execution_scope("ghost", "status"))
        self.assertTrue(g.describes_finalization_scope("worker"))
        self.assertFalse(g.describes_finalization_scope("ghost"))
        with self.assertRaises(TypeError):
            g.worker_execution_scopes["worker"] = frozenset({"restart_server"})
        with self.assertRaises(FrozenInstanceError):
            g.revision = 2

    def test_no_worker_proposal_or_bound_grant_is_refused(self):
        cases = [
            lambda: GrantProposal("mission", set(), {}),
            lambda: GrantProposal("mission", {"read_log"}, {}),
            lambda: BoundGrant("mission", "grant", 1, "3", set(), {}),
            lambda: BoundGrant("mission", "grant", 1, "3", {"read_log"}, {}),
        ]
        for index, construct in enumerate(cases):
            with self.subTest(case=index), self.assertRaisesRegex(
                ProtocolViolation, "^invalid_worker_scopes$"
            ):
                construct()

    def test_one_worker_with_zero_execution_capabilities_is_valid(self):
        proposal = GrantProposal("mission", set(), {"observer": set()})
        grant = BoundGrant("mission", "grant", 1, "3", set(), {"observer": set()})
        self.assertEqual(set(proposal.worker_requests), {"observer"})
        self.assertEqual(set(grant.worker_execution_scopes), {"observer"})
        self.assertFalse(grant.describes_execution_scope("observer", "anything"))
        self.assertTrue(grant.describes_finalization_scope("observer"))

    def test_worker_scope_can_only_narrow(self):
        with self.assertRaisesRegex(ProtocolViolation, "worker_scope_exceeds_grant"):
            BoundGrant("m", "g", 1, "1", {"read_log"}, {"w": {"restart_server"}})
        with self.assertRaisesRegex(ProtocolViolation, "worker_scope_exceeds_grant"):
            GrantProposal("m", {"read_log"}, {"w": {"restart_server"}})

    def test_every_assigned_worker_can_finalize_even_without_tools(self):
        g = BoundGrant("m", "g", 1, "1", {"read_log"}, {"w": {"read_log"}, "observer": set()})
        self.assertEqual(g.finalization_workers, frozenset({"w", "observer"}))
        self.assertTrue(g.describes_finalization_scope("w"))
        self.assertTrue(g.describes_finalization_scope("observer"))
        self.assertFalse(g.describes_finalization_scope("ghost"))
        self.assertFalse(g.describes_execution_scope("observer", "read_log"))

    def test_bound_grant_hash_uses_immutable_canonical_components(self):
        first = BoundGrant("m", "g", 1, "1", {"a", "b"}, {"b": {"b"}, "a": {"a"}})
        second = BoundGrant("m", "g", 1, "1", {"b", "a"}, {"a": {"a"}, "b": {"b"}})
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))
        self.assertEqual(len({first, second}), 1)

    def test_lone_surrogates_rejected_at_identifier_boundary(self):
        bad = "\ud800"
        constructors = [
            lambda: RequestId(bad),
            lambda: InvocationId(bad),
            lambda: MessageEnvelope(CONTRACT_VERSION, RequestId("ok"), bad, "fleet", "1"),
            lambda: GrantProposal(bad, set(), {}),
            lambda: BoundGrant("m", bad, 1, "1", {"read_log"}, {"w": {"read_log"}}),
            lambda: BoundGrant("m", "g", 1, "1", {"read_log"}, {bad: {"read_log"}}),
            lambda: RecordIdentity(RecordKind.REPORT, "m", bad, "1"),
        ]
        for index, create in enumerate(constructors):
            with self.subTest(case=index), self.assertRaises(ProtocolViolation):
                create()

    def test_bound_grant_revision_rejects_bool(self):
        for revision in (True, False, 0, -1, "1", None, 1.5):
            with self.subTest(revision=revision), self.assertRaisesRegex(ProtocolViolation, "invalid_grant_revision"):
                BoundGrant("m", "g", revision, "1", {"read_log"}, {"w": {"read_log"}})

    def test_grant_malformed_inputs(self):
        cases = [
            (5, "g", 1, "1", {"read_log"}, {"w": {"read_log"}}),
            ("m", " ", 1, "1", {"read_log"}, {"w": {"read_log"}}),
            ("m", "g", 1, 1, {"read_log"}, {"w": {"read_log"}}),
            ("m", "g", 1, "1", "read_log", {"w": {"read_log"}}),
            ("m", "g", 1, "1", {"read_log"}, ["w"]),
            ("m", "g", 1, "1", {"read_log"}, {7: {"read_log"}}),
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ProtocolViolation):
                BoundGrant(*case)

    def test_record_identity_namespaces_are_distinct(self):
        ids = [RecordIdentity(kind, "mission", "worker", "1").parts() for kind in RecordKind]
        self.assertEqual(len(ids), len(set(ids)))

    def test_record_identity_invalid_values_are_structured(self):
        for kind, mission, worker, item in (
            ("report", "m", "w", "1"),
            (RecordKind.REPORT, " ", "w", "1"),
            (RecordKind.REPORT, "m", 5, "1"),
            (RecordKind.REPORT, "m", "w", ""),
        ):
            with self.subTest(kind=kind), self.assertRaises(ProtocolViolation):
                RecordIdentity(kind, mission, worker, item)

    def test_event_authority_covers_all_spec_events(self):
        expected = {
            "operational_state_changed", "finding_shared", "worker_state", "fleet_state_changed",
            "mission_assigned", "report_accepted", "result_delivered", "mission_terminal",
            "authority_changed", "error", "presentation_state_changed",
        }
        self.assertEqual(set(EVENT_AUTHORITY), expected)
        self.assertEqual({k for k, v in EVENT_AUTHORITY.items() if v is EventAuthority.HOST_AUTHORITATIVE}, HOST_ONLY_EVENTS)
        self.assertEqual(EVENT_AUTHORITY["result_delivered"], EventAuthority.HOST_AUTHORITATIVE)
        self.assertEqual(EVENT_AUTHORITY["operational_state_changed"], EventAuthority.ENGINE_ADVISORY)
        self.assertEqual(EVENT_AUTHORITY["presentation_state_changed"], EventAuthority.PRESENTATION_ONLY)

    def test_event_authority_is_immutable(self):
        with self.assertRaises(TypeError):
            EVENT_AUTHORITY["result_delivered"] = EventAuthority.ENGINE_ADVISORY

    def test_contract_imports_only_stdlib_or_own_package(self):
        package = Path(__file__).resolve().parents[1] / "src" / "morb_contract"
        allowed_stdlib = {"__future__", "dataclasses", "enum", "re", "types", "typing"}
        for source in package.glob("*.py"):
            syntax = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(syntax):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split(".")[0], allowed_stdlib, source.name)
                if isinstance(node, ast.ImportFrom):
                    if node.level:
                        self.assertEqual(node.module, "model", source.name)
                        self.assertEqual(source.name, "__init__.py")
                    else:
                        self.assertIn(node.module.split(".")[0], allowed_stdlib, source.name)

    def test_preservation_independent_of_work(self):
        self.assertEqual(PreservationState.PENDING.value, "pending")
        self.assertNotEqual(PreservationState.PENDING, PreservationState.SEALED)


if __name__ == "__main__":
    unittest.main()
