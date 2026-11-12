# Claude review of PR #1, round 3 (closing)

Reviewed at `a7f3239` (`work/morb-contract-v1-foundation`) against spec revision 3 at `ddf8e93`. All 22 tests pass locally.

**Verdict: findings A, B and C are closed, with no regressions found. Accept as the Phase 0 contract-foundation checkpoint, subject to Bryan's merge approval.**

## Verification

- **A (finalization right): closed.** `BoundGrant` no longer takes `finalization_workers`; membership is derived from scope keys. A worker with an empty execution scope (`{"r": set()}`) still gets the finalization right (`describes_finalization_scope("r") -> True`). Passing the removed argument now fails at the constructor signature, which is an intended API change, not a contract input path.
- **B (hashing): closed.** `hash(BoundGrant)` works. Equal grants built with different key order hash equal; grants with different scopes are unequal and hash differently.
- **C (lone surrogates): closed.** Refused for worker ids, capability names, request ids and proposal mission ids, each with its field's reason code. A valid non-BMP character (an emoji, encoded as a surrogate pair in UTF-16) is still accepted, which is correct.
- **Original mutation exploit:** re-tested, still closed.

## Notes for the next cycle (non-blocking)

1. The import-isolation test only allows relative imports of `.model` from `__init__.py`. The first new module (for example canonicalization) that imports `.model` will fail it. Loosen it to "any relative import inside `morb_contract`, plus the stdlib allowlist."
2. The test cannot see dynamic imports (`__import__`, `importlib`). `importlib` is already outside the allowlist; consider also rejecting calls to `__import__` in the AST walk.
3. `test_preservation_independent_of_work` still only asserts constants. It's harmless; replace it when the preservation logic exists in the simulated host.

## Next

Agree with GPT-6: simulated host next, opening with the revoked-grant test (the same unchanged `BoundGrant` refused with `execution_revoked` after revocation in the host ledger).

— Claude
