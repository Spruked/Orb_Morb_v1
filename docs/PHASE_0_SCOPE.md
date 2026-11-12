# Phase 0: contract foundation (draft)

Status: **implementation started, no production integration, not owner-approved protocol**.

This phase creates small, host-neutral data models and executable boundary tests, without connecting to ORB, MORB, DockStation, CALI, or A.I.M.S. It is deliberately safe to run on a disconnected development machine.

## Preserved decisions

- Four runtimes: Motion, Communication, Cognitive/Governance, MORB. DockStation supervises; it does not become another motion engine.
- The engine owns mission work, never host authority, primary ORB window positioning, canonical evidence, or CALI SKG credentials.
- The host holds fleet ownership epochs, establishes mission-grant scopes, brokers capabilities, and publishes authoritative events.
- The host takes preservation custody only after a durable staging acknowledgment, and preserves through the A.I.M.S. writer, not via direct engine access.
- Temporary mission workspaces and spatial graphs are optional implementation capabilities, not competing canonical memory systems.
- Real fleet presence mirrors real workers; simulated formation activity must be explicitly labelled.

## Deliberately not implemented

- Engine process, leases, authenticated transport, grants issued by governance, capability execution, report queue, A.I.M.S. sealing, SHA-256 RFC 8785 trace, graphical overlay, or a live ORB adapter.
- This is a draft **contract model**, not a permit service or a functioning MORB fleet.

## Blocking specification reconciliations

1. Assign → owner/CALI approval → Deploy binding must never issue execution rights before approval.
2. Cancellation revokes consequential execution but permits narrowly scoped terminal reporting during an explicit finalization period.
3. Report/evidence/host-terminal identities must have separate namespaces.
4. Fleet epoch fencing must survive host restarts without blocking already accepted report custody.
5. Worker liveness and transitions need normative definitions and tests.
6. `invocation_id` must be distinct from transport `request_id` for consequential actions.
7. Direct A.I.M.S. writer access must never be exposed as an engine capability.
8. Host events are authoritative; engine events are advisory.

These items are not permission to change production systems. They are the review checklist for the next bounded implementation cycle.

## Owner approvals still pending

Glyph provider verification; receipt authentication choice; workspace retention; drain timeout; first fleet size; first-engine trust/isolation profile; preservation deadline; plus the other decisions retained in the MORB Contract v1 review document.
