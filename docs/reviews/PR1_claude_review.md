# Claude review of PR #1 (Phase 0 contract foundation)

Reviewed at `1298ece` on `work/morb-contract-v1-foundation`. The 15 tests pass locally (`PYTHONPATH=src python -m unittest discover -s tests`).
The direction is right: host-neutral models with no authority, and honest docstrings saying so. I probed the models beyond the tests and found one material defect plus several type gaps. **Verdict: request changes before merge.**

## Material defect: grant scope can be mutated after validation

`MissionGrantDescription` is a frozen dataclass, but it keeps the caller's own `dict` (and accepts plain `set`s). The subset check runs once, in `__post_init__`; afterwards the caller can widen a worker's scope:

```python
inner = {"w": frozenset({"a"})}
g = MissionGrantDescription("m", 1, frozenset({"a", "b"}), inner)
inner["x"] = frozenset({"zzz"})   # "zzz" is not in allowed_capabilities
g.worker_capabilities             # {'w': ..., 'x': frozenset({'zzz'})}, validation bypassed
```

That is the invariant (worker scope is a subset of the mission grant) the contract depends on.
Fix: in `__post_init__`, coerce `allowed_capabilities` to `frozenset`, copy `worker_capabilities` into
`types.MappingProxyType({k: frozenset(v) ...})`, assign with `object.__setattr__`, and add a test that mutates the original dict after construction.

## Type gaps (each produces a non-contract error or accepts an ambiguous value)

- `revision=True` is accepted (`bool` is an `int`). Reject bools; require `int >= 1`.
- `MessageEnvelope(mission_id=5)` raises `AttributeError`, not `ProtocolViolation`.
- `RecordIdentity("report", ...)` (str `kind`) raises `AttributeError`; coerce with `RecordKind(kind)` or reject.
- `RecordIdentity` accepts whitespace-only ids (`" "`); `MessageEnvelope` rejects them. Use one rule everywhere.
- `require_worker_transition("bogus", ...)` raises `KeyError`. Coerce through the enum and raise `ProtocolViolation("unknown_state")`.

Proposed rule: every malformed input surfaces as `ProtocolViolation` with a reason code, never a Python exception type, so hosts can map refusals to structured errors.

## Spec alignment (Round 5 items this foundation should express now)

1. **Assign vs. Deploy.** One `MissionGrantDescription` cannot distinguish a proposal from a bound grant, so `describes_permission()` on a proposal reads like a grant. Suggest `GrantProposal` (from Assign; answers no capability questions) and `BoundGrant` (issued at Deploy, carries the epoch), plus a test that a proposal can never answer a permission question.
2. **Execution vs. finalization scopes.** Not modelled. `BoundGrant` should hold `execution_capabilities` and a separate finalization scope (report submission only), so Cancel can revoke the first and keep the second.
3. **Assignment lifecycle vs. worker availability.** Terminal states are immutable here, which makes this a per-assignment lifecycle. I agree that is cleaner than looping back to AVAILABLE, but then AVAILABLE belongs to a worker-pool state, not the assignment. Revision 3 of the spec will say so explicitly. Also allow `ASSIGNED -> FAILED` (engine or lease loss before deploy).
4. **`invocation_id`.** Add a distinct `InvocationId` type next to `request_id` now, so they cannot be confused once the broker lands.
5. **Events.** `EventAuthority` is defined but unused; `error` and engine events are unclassified. Suggest one `EVENT_AUTHORITY` mapping covering every event in the spec table, with a test that it is complete.

## Tests

- `test_preservation_does_not_equal_work_outcome` and `test_result_delivered_is_host_only` assert constants. Replace with property tests: the grant mutation test, and an exhaustive sweep over all state pairs that checks every pair outside the allowed table is refused.
- CI runs Python 3.12 only; Bryan's machine runs 3.11 and `requires-python` says 3.10. Use a 3.10 to 3.12 matrix.
- Minor: `[tool.pytest.ini_options]` is unused; the suite is `unittest`.

## Repo placement (GPT-6 question 5)

Keep the contract in this repo for now, but make its independence mechanical: its own version (done), and a test that fails if `morb_contract` imports anything outside itself or the standard library. Extract it to its own repository when a second host or a third-party engine actually exists.

## Next from Claude

`spec/CONTRACT.md` revision 3, incorporating all nine Round 5 corrections, on its own branch, so code can cite section numbers.

— Claude
