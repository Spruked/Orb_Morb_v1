# Muse review of PR #1 at 3c5d50d — GrantProposal / BoundGrant, spec §5.2 / §5.3
Date: 2026-11-12
Reviewer: Muse (Mark) — independent adversarial verification
Code reviewed: `work/morb-contract-v1-foundation` at `3c5d50d`
Spec reviewed: `spec/contract-rev3` at `ddf8e93` (Revision 3, settled; §19 register pending)
Claude round-2 reviewed: `review/claude-pr1` at `17180ec`

This pass was assigned by Claude: try to construct any `BoundGrant` or `GrantProposal` that violates spec §5.2 or §5.3 at those commits. Finding A is one case; this review asks whether there are others.
Revision 3 is settled and the owner-register question is closed — this review does not reopen it.

## Verdict
No new §5.2/§5.3 violation of the same severity as Finding A was found by construction, but two new gaps in the same area were found, plus one model under-specification. Finding A, B, and C from Claude round-2 are confirmed still open at `3c5d50d` (reproduced below, not re-claimed as new).

## Confirmed still open at 3c5d50d (Claude round-2, reproduced independently)
**A — required. Execution without finalization.**
```python
BoundGrant("m", "g", 1, "3", {"a"}, {"w": {"a"}}, set())  # ACCEPTED
# describes_execution_scope('w','a') == True
# describes_finalization_scope('w') == False
```
A cancelled worker `w` could never file its finalization report. This is a gap in the code against settled spec §5.2 / §5.3 and the §1 accountability principle. Fix before the foundation is called accepted, per Claude: derive `finalization_workers` from `worker_execution_scopes.keys()` and drop the parameter, or require equality.

Note on citation: rev3 §5.3 as written does not literally say "every execution worker MUST be in finalization_workers" — it says every bound grant contains two scopes, and finalization permits terminal reports. The "every grant includes a narrow right to submit reports" wording is in rev2 §5. The spec should be strengthened to state the equality explicitly, then the code fix follows. Do not treat the code fix alone as closing the spec gap.

**B — small. Unhashable grant.**
```python
hash(BoundGrant('m','g',1,'3', {'a'}, {'w': {'a'}}, {'w'}))
# TypeError: unhashable type: 'dict'
```
Frozen-dataclass hash includes the mapping field. Fix: `__hash__` over the canonical tuple, or `eq=False`.

**C — small. Lone surrogates accepted.**
```python
BoundGrant("\ud800", 'g', 1, '3', {'a'}, {'w': {'a'}}, {'w'})  # ACCEPTED
BoundGrant('m', 'g', 1, '3', {'\ud800'}, {'w': {'\ud800'}}, {'w'})  # ACCEPTED
```
Spec §13.3 rejects lone surrogates before hashing. Fix: reject in `_text` (e.g. `value.encode("utf-8")` in try, raising the field's reason code).

## New findings in §5.2 / §5.3

### D — new, medium. Finalization without execution (inverse of A)
```python
BoundGrant('m','g',1,'3', {'a'}, {'w': set()}, {'w'})  # ACCEPTED
# worker 'w' has empty execution scope, but IS in finalization_workers
```
Code enforces `finalization_workers ⊆ worker_execution_scopes.keys()`, but not that a finalization worker has a non-empty execution scope. A worker can therefore hold a finalization right for work it never executed. §5.3 finalization is for "evidence already acquired before revocation" — a worker with no execution scope acquired nothing. This is the same class as A, in the other direction. Fix with A: derive finalization from workers with non-empty execution scopes, or require `finalization_workers == {w for w, caps in scopes.items() if caps}`.

### E — new, medium. Finalization scope carries no content restriction
`BoundGrant.finalization_workers` is a set of worker ids only. There is no capability list, report type, or evidence-age field for finalization.
```python
g = BoundGrant('m','g',1,'3', {'a','read_logs'}, {'w': {'a'}}, {'w'})
g.describes_finalization_scope('w')  # True — says nothing about what 'w' may submit
```
§5.3: "The finalization scope MUST NOT permit tool invocation, new evidence acquisition, or any consequential action." The model cannot express that distinction — a host reading `True` as "worker may act" could allow tool use or new-evidence submission, and the model would not refuse it. This is not a construction that violates §5.3 literally; it is a model under-specification that leaves §5.3 unenforceable at this layer. Enforcement must live in the host / simhost (refuse brokered calls with `execution_revoked`, refuse submissions after the window with `finalization_closed`), and the simhost should test exactly that. If the model is meant to carry the restriction, add an explicit finalization capability set (report submission only) rather than a bare worker-id set.

### F — new, minor. Vacuous grants accepted
```python
BoundGrant('m','g',1,'3', set(), {}, set())  # ACCEPTED
GrantProposal('m', set(), {})  # ACCEPTED
BoundGrant('m','g',1,'3', {'a'}, {}, set())  # ACCEPTED — grant with capabilities, no workers
```
Spec §5.2 / §10: a bound grant binds each approved worker identity to its scope; Deploy binds approved workers. A grant with zero workers, or a proposal with zero workers, is vacuous — it authorizes nothing and describes no mission work. The spec does not explicitly forbid it, so this is a spec-silence gap, not a MUST violation. Recommend: require at least one worker in `worker_execution_scopes` for `BoundGrant` and in `worker_requests` for `GrantProposal`, or state explicitly in the spec that vacuous grants are permitted for testing. Do not leave it ambiguous — a deployed vacuous grant would pass all current tests while doing nothing.

## Checked and found sound at 3c5d50d
- **Proposal cannot answer authorization:** `GrantProposal` has no `describes_execution_scope`, no `describes_finalization_scope`, no `grant_id` / `revision` / `epoch` / `execution_capabilities` fields. Distinct field names (`requested_capabilities` / `worker_requests` vs `execution_capabilities` / `worker_execution_scopes`) prevent accidental confusion.
- **Worker scope subset:** `BoundGrant` and `GrantProposal` both refuse a worker scope exceeding the grant (`worker_scope_exceeds_grant`).
- **Finalization superset refused:** `finalization_workers={'ghost'}` with no such execution worker → `ProtocolViolation invalid_finalization_scope`.
- **Deep immutability (normal API):** mutating the caller's set/dict after construction leaves the grant unchanged (`{'w': frozenset({'a'})}`, `describes_execution_scope('x','zzz') == False`). `MappingProxyType` blocks dict mutation; normal `setattr` on a frozen dataclass raises `FrozenInstanceError`. (`object.__setattr__` bypasses frozen dataclasses in Python — that is a deliberate escape hatch, not a model defect, and is out of scope for a same-process `trusted_local` engine.)
- **Strict inputs:** revision `0` / `True` refused (`invalid_grant_revision`), epoch `"01"` refused (`invalid_epoch`), empty/whitespace capability refused, non-mapping worker scopes refused, string finalization set refused.
- **Epoch / revision forgery is out of model scope:** `BoundGrant` accepts arbitrary `grant_id`, epoch `"0"` / huge epoch, huge revision, and a `grant_id` unrelated to `mission_id`. That is expected for a description type — the host broker MUST check its canonical grant, current epoch, revocation status, and policy at invocation time (docstring, spec §5.4). The protection is Claude's proposed simhost test: issue a bound grant, revoke it in the host ledger, present the same unchanged object — `describes_execution_scope()` still returns True, the broker must refuse with `execution_revoked`. That test does not exist yet.

## What this pass did not find
No construction was found that lets a `GrantProposal` answer a permission question, widens a validated scope after construction through the normal API, or lets a worker exceed its bound grant's execution capabilities. Those invariants hold at `3c5d50d`.

## Recommendation
Fix A (and D with it, by deriving finalization), B, and C before calling the Phase 0 foundation accepted. Add the import-isolation test and update `PHASE_0_SCOPE.md` (its "blocking reconciliations" are resolved by rev3; point to spec sections). Then merge in Claude's order: PR #2 (spec) first, PR #1 (code, rebased) second, PR #3 + this review (documents) third. Next milestone after that is the simulated host with two interchangeable engines — first simhost test should be the revoked-grant test above.

## Method
Read-only clone / fetch. Ran 19 tests at `3c5d50d` (all pass, Python 3.12.3). Ran a construction fuzz script over `BoundGrant` / `GrantProposal` covering: A, finalization subset/superset, final-only, vacuous grants, scope subset, post-construction mutation, epoch/revision/grant-id forgery, finalization content, hash/equality, lone surrogates, proposal-as-permission. No GitHub changes made by this review.
