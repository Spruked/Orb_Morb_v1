# Claude review — simulated host, round 2 (49e3a09)

46 tests pass locally. G–J verified closed:

| Finding | Check | Result |
|---|---|---|
| G | rejected items carry `evidence_unresolved:source_not_found` / `:digest_mismatch` | closed; `:detail` form is permitted by §6.4 |
| H | second, different finalization → `record_conflict`; identical retry → same result | closed |
| I | same identity, different content in one submission → `record_conflict` | closed |
| J | narrowed approval binds only approved capabilities | closed |

## New finding

**K — finalization is accepted before Cancel (medium).**
A worker submitted a "finalization" report while its grant was live, then kept calling tools (`read_status` succeeded), and after the real Cancel its true account was refused with `record_conflict`. An early "terminal" report can pre-empt the report that matters. This is the same issue as GPT's PR #2 question.

Spec answer at `spec/contract-rev3` (§11, §6.4):
- Work reports are sequenced and non-terminal. One terminal report per worker per grant.
- A finalization report is accepted only inside the window: before revocation → `finalization_not_open` (newly registered); after the window → `finalization_closed`.
- An identical retry of a report accepted inside the window returns the original acknowledgement even after the window closes. Currently it is refused `finalization_closed`; fix the check order.

Tests to add: finalization before Cancel refused `finalization_not_open`; identical retry after close returns the original result; changed report after close refused.

After K, freeze the host interface for the two-engine milestone.
