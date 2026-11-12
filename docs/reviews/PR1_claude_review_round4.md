# Claude review — PR #1, round 4 (fc6cd5c)

Verdict: **F closed. No regressions. Phase 0 model is accepted from the spec side.**

Verified independently against CONTRACT.md rev 3 at 95d5ecf:

| Check | Result |
|---|---|
| Test suite (24) | pass |
| BoundGrant, empty roster | refused `invalid_worker_scopes` |
| BoundGrant, capabilities but no workers | refused `invalid_worker_scopes` |
| GrantProposal, empty roster | refused `invalid_worker_scopes` |
| Zero-tool worker (bound and proposal) | accepted; holds finalization (§5.3) |
| Mutation exploit (caller mutates input dict) | still closed |
| Lone surrogate in identity | refused `invalid_grant_identity` |
| BoundGrant hashable | yes |

Provenance concern: already resolved in spec at 95d5ecf (§5.3, §10, §12.2).
Evidence must trace to an invocation record written before revocation, or to
mission-supplied material the host recorded with its digest at Assign.
Anything else is accepted only as an attributed unverified claim.

Next: simulated host, opening with
1. revoked grant: the same BoundGrant object is refused with `execution_revoked`;
2. after Cancel, a brokered tool call is refused even though `describes_finalization_scope` is True;
3. provenance table, covering both trace branches (amended per Muse's review):
   - invocation branch: E citing an invocation record logged before revocation → accepted;
     E citing a record logged after revocation, or a nonexistent record → not evidence;
   - mission-supplied branch: cited M with matching digest → accepted with M's provenance;
     altered digest → `evidence_unresolved`;
   - no trail: E with no M and no invocation record → attributed unverified claim.
