# Phase 0 — Portable MORB contract foundation

**Engineering status:** authorized for development; contract model only, no production integration. This document describes implementation progress; the normative specification is `spec/CONTRACT.md` Revision 3 on draft PR #2. The individual owner-approval register values in §19 are still pending.

**Code review checkpoint:** draft PR #1, `a7f3239`. This includes Claude's round-2 A/B/C fixes, an import-isolation test, and 22 standard-library unit tests passing in GitHub Actions on Python 3.10, 3.11, and 3.12. Tests demonstrate the limited model behavior below, not a functional or authorized MORB engine.

## Preserved architecture

- Four runtimes: Motion, Communication, Cognitive/Governance and MORB. DockStation supervises; it does not become another motion engine.
- MORB owns mission work and scheduling but never host authority, primary ORB positioning, canonical evidence or CALI SKG credentials.
- The host owns fleet epochs, approval and canonical grants, capability invocation, event authority and authenticated A.I.M.S. custody.
- Report custody transfers only after durable host staging and acknowledgment.
- Temporary mission workspaces and spatial graphs are optional; they do not become competing canonical memory systems.
- Every visible MORB represents a worker or explicitly identified preview/reserve. Animation cannot claim mission success.

## Phase 0 models and test coverage

| Topic | Current model status | Remaining capability |
| --- | --- | --- |
| Assign/Deploy | Separate immutable `GrantProposal` and descriptive `BoundGrant` | Owner/governance approval and actual host grant binding |
| Worker scopes | Immutable capability subsets, worker identities, and finalization for *every* assigned worker including zero-tool workers | Live authorization, revocation, finalization deadlines and report-content validation |
| Assignment states | Normative assignment transitions, including ASSIGNED → FAILED, exhaustively tested | Host reconciliation and per-worker liveness |
| Fleet states | Proposed transitions checked | Lease control, desired/effective state handling, stop/drain enforcement |
| Message identities | Canonical decimal epoch, typed `RequestId` and `InvocationId` | Authenticated transport, negotiated version, durable idempotency |
| Evidence identities | Distinct record type domains and validated identifiers | Durable queue, digest checking, reference resolution, Vault sealing |
| Events | Authoritative/advisory/presentation categories listed and tested | Host-owned event stream, snapshots and replay |
| Package boundary | No engine/host imports via AST-based test | Package relocation and separate release/version verification |

These are **data models**, never permits, actual execution, or evidence preservation.

## Not implemented

No MORB engine process, no simulated host, no production lease, no capability broker, no external actions, no vault writer, no report ingress queue, no canonical SHA-256 trace, no graphical overlay, and no live Desktop Orbot adapter. A full cross-language RFC 8785-compatible restricted serialization implementation is also not yet present.

## Open review questions (not a reason to rewrite architecture)

- **Muse Finding D:** Reporting is required even for zero-tool assignments. Do not restrict finalization membership to workers with nonempty execution scopes. The host must validate what can be submitted, not assume an empty execution-capability list means no report is needed.
- **Muse Finding E:** The simulated host must refuse tool invocation, new evidence acquisition, and unauthorized report contents during finalization. An immutable grant description is never an authorization oracle.
- **Muse Finding F:** Revision 3 should explicitly decide whether a zero-worker proposal/bound grant is valid. Recommended: no successful Deploy with zero approved workers. This clarification must be made in the spec before tightening the model.
- **First simulated host proof:** A previously allowed capability must be refused after host-side revocation even when the same unchanged BoundGrant object still describes it.
- **Owner decisions:** The 11-item register in Revision 3 §19 remains pending; proposed defaults are not yet finalized by the owner.

## Development discipline

Use separate branches and reviewable pull requests. Adopt spec changes before code that depends on them. No new engine capability may bypass the host broker, and no contract-model test should be presented as proof that production governance, custody, or runtime replaceability works.
