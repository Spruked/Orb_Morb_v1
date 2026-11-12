# Claude review — simulated host, round 1 (92fd517)

Branch `work/simhost-revocation-provenance`. 39 tests pass (24 contract + 15 simhost).

## The three agreed tests: covered
| Test | Where | Result |
|---|---|---|
| Revoked grant: same unchanged BoundGrant refused `execution_revoked` | `test_revoked_grant_description_still_matches_but_broker_refuses` | pass |
| After Cancel: brokered call refused though finalization scope is described | `test_cancel_preserves_narrow_reporting_but_not_tools` | pass |
| Provenance, invocation branch (pre-revocation accepted) | `test_pre_revocation_invocation_evidence_remains_traceable` | pass |
| Provenance, post-revocation record | structurally impossible: broker refuses after revocation, so no record can be logged. Acceptable; a comment in the test should say so. | n/a |
| Provenance, mission branch (digest match / altered) | `test_mission_supplied_..._finalization`, `test_wrong_digest_...` | pass |
| No trail → attributed unverified claim | `test_untraced_evidence_refused_but_attributed_claim_retained` | pass |

Also good: forged grant refused, cross-worker invocation reuse refused, invocation-id replay bound to capability, approval cannot widen scope.

## Findings

**G — rejected evidence carries no reason code (low-medium).**
An altered-digest item and an item citing a nonexistent source both land in `provenance_rejected` with nothing to tell them apart. §12.2 registers `evidence_unresolved` for exactly this. Fix: each rejected item records its code (`evidence_unresolved`), so the custody record says *why* proof was lost. The report itself still survives as an attributed, unverified claim; that behavior is right.

**H — a worker can submit more than one finalization report (medium).**
After Cancel, `research` submitted "first", then "rewritten"; both were accepted and stored. A cancelled worker can revise its account after the fact, and nothing says which report is authoritative. §11 step 4 grants *a* finalization report. Fix: a second report from the same worker under the same grant is refused with `record_conflict` (an identical resubmission may be idempotent).

**I — duplicate evidence identity within one submission (low-medium).**
Two items with the same `RecordIdentity` and different content: the first is accepted, the second rejected. One identity must not name two contents (§12.1). Fix: refuse with `record_conflict`.

**J — narrowed approval leaves wide execution_capabilities (low, not exploitable).**
Approving `ops` for `read_status` only still binds a grant whose `execution_capabilities` include `read_logs`. The broker checks worker scope, so nothing can call it, but the bound grant describes authority nobody was given. Fix: bind the union of approved worker scopes.

## Verdict
Authority and provenance enforcement is correct for the agreed tests. G–I should be fixed before the simhost is used as the conformance reference; J can ride along.
