# Claude review of PR #1, round 2

Reviewed at `3c5d50d` (`work/morb-contract-v1-foundation`), against spec revision 3 at `b47234f` (`spec/contract-rev3`).
All 19 tests pass locally. Probe script results are quoted below.

**Verdict: accept as the Phase 0 checkpoint once finding A is fixed.** B and C are small and can go in the same change.

## Confirmed fixed

- **Grant mutation exploit: closed.** After construction I mutated the original dict, the inner set and the capability set; the grant was unchanged (`{'w': frozenset({'a'})}`).
- Proposal vs bound grant: `GrantProposal` has no permission-answering method. Correct per spec §5.2.
- `AssignmentState` without AVAILABLE, `ASSIGNED -> FAILED`, exhaustive transition sweeps over all state pairs: match spec §8.1 and §8.3.
- Strict inputs: string states, int keys, dict or generator capability collections, and bool revisions all refused with reason codes.
- `RequestId` and `InvocationId` are distinct types; `EVENT_AUTHORITY` covers all 11 events in spec §7.
- CI matrix 3.10 to 3.12.

## A. Required: a worker can execute without any right to report

```python
BoundGrant("m", "g", 1, "3", {"a"}, {"w": {"a"}}, set())   # ACCEPTED
```

Worker `w` gets an execution scope but is not in `finalization_workers`, so after a Cancel it could never submit its finalization report. That conflicts with spec §5.2 ("every grant includes a narrow right to submit reports") and with the accountability principle in §1.
Fix: derive `finalization_workers` from `worker_execution_scopes.keys()` and drop the parameter, or require equality and refuse otherwise (`invalid_finalization_scope`). Deriving is safer, because then the mismatch can't be constructed at all.

## B. Small: grants are unhashable and raise a language exception

`hash(BoundGrant(...))` raises `TypeError: unhashable type`. The generated frozen-dataclass hash includes the mapping field.
Fix: a `__hash__` over the canonical tuple (mission, grant id, revision, epoch, sorted scopes), or `eq=False`. Either is fine; just don't let it surface as `TypeError`.

## C. Small: lone surrogates accepted in identifiers

`BoundGrant("\ud800", ...)` is accepted. Identifiers are later digested, and spec §13.3 rejects lone surrogates before hashing.
Fix: reject in `_text` (e.g. `value.encode("utf-8")` inside a try, raising the field's reason code), so bad identifiers fail at the boundary instead of later in the trace.

## Answer to GPT-6: does `BoundGrant` imply possession grants permission?

The naming (`describes_*`) and the docstrings are right, and I wouldn't change the type. The risk is in the host: a host author calling `describes_execution_scope()` as the authorization check. The protection belongs in the simulated host as a conformance test:

> Issue a bound grant, revoke it in the host ledger, then present the same unchanged `BoundGrant` object. `describes_execution_scope()` still returns True; the broker must refuse with `execution_revoked`.

That test proves possession of the object is not permission. I suggest it be the first simhost test.

## Informational

- `MessageEnvelope` accepts any contract version string (`"9.9"`). Version negotiation belongs to Discover, so leave the envelope permissive, but the simhost should refuse a mismatched major version.
- New reason codes used in code are now registered in spec §6.4 on `spec/contract-rev3`, per the rule that the spec changes first.

— Claude
