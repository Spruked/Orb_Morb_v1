# MORB Interface Contract v1 — Revision 3

| | |
| --- | --- |
| Status | Revision 3. Reconciled by Claude and GPT-6 through owner-relayed review. Bryan Spruk authorized engineering work on 2026-11-12; the owner decisions in §19 remain pending his explicit confirmation. Implementation proceeds on development branches; integration into running systems is a separate checkpoint. |
| Supersedes | Revision 2 (review document, 2026-11-12) |
| Normative language | MUST, MUST NOT, SHOULD, MAY as in RFC 2119 |
| Scope of this file | The interface between a host ORB and a MORB engine. It is the source of truth for code in this repository; where code and this file disagree, this file changes first, through its own pull request. |

This repository is public during development. It must never contain credentials, private infrastructure details, or real Vault data.

---

## 1. Purpose and principle

This contract lets any ORB use MORB workers, and lets any compatible MORB engine be installed, replaced or rolled back without changing the ORB's core.

> **ORB owns the relationship. MORB owns the work. The contract between them survives either implementation.**

**Replaceability Principle.** The MORB Runtime is a separately versioned, independently deployable, replaceable capability module. Hosts interact with it exclusively through stable, versioned interfaces. No MORB implementation owns the host's identity, governance authority, canonical memory, or primary embodiment controls. Compatible implementations may be installed, upgraded, replaced or rolled back without modifying the host's core. Advanced functionality is negotiated through explicit capability discovery.

The host retains authority over identity, permission validation, canonical evidence preservation, and acceptance of mission results. The host does not need to know which scheduler, mission workspace, inference strategy or formation algorithm an engine uses.

**Accountability principle.** A MORB's authority may expire, its engine may fail, and its implementation may be replaced. None of those events erases the host's responsibility to account for what that MORB did, attempted, reported, or failed to complete.

The contract package (`morb_contract`) is versioned separately from both host and engine and MUST NOT import engine or host code.

## 2. Scope

| Area | MORB engine owns | Host owns |
| --- | --- | --- |
| Workers | Worker lifecycle, scheduling, formation logic | Whether the fleet may run at all |
| Missions | Task execution, mission-scoped working state | Who may assign missions, and which |
| Authority | Nothing; requests capabilities under a host-issued bound grant | Policy, grants, revocation |
| Memory | Disposable mission workspace only | The A.I.M.S. vault and CALI's SKG |
| Identity | Worker identities inside its fleet | The ORB's identity and CALI's inculcation |
| Embodiment | MORB visuals via the presentation adapter | The primary ORB window and its position writer |
| Inference and tools | Requests them | Provides them through the capability broker |

Exactly one production engine owns a given fleet at a time.

## 3. Parties and layers

Three parties meet at the contract: the host, the contract package, and a replaceable engine.

```
Host ORB ── Governance (decides grants) ── Host Report Ingress ── A.I.M.S. vault ── CALI SKG (references only)
   │  commands, bound grants, fleet state            ▲ reports, evidence
   ▼                                                  │
MORB Interface Contract v1 (separate package)  ── standard events ──► host event stream ──► DockStation
   ▲
MORB engine (replaceable): workers & missions · mission workspace · presentation adapter
```

Reports travel up through Host Report Ingress into A.I.M.S.; CALI's SKG only references them. Authority travels down from the host; the engine never holds authority of its own.

## 4. Contract boundaries

Version 1 is the smallest complete contract: one host, one engine, local inter-process communication, one lease, no consensus protocol.

| Tier | Contents |
| --- | --- |
| Mandatory core | Message envelope and version negotiation; fleet lease and ownership epoch; grant proposals and bound grants with worker scopes; execution and finalization scopes; assignment and fleet lifecycles; fleet controls; capability broker with invocation identities; durable host mission ledger; Host Report Ingress with evidence staging; authenticated A.I.M.S. receipts; SHA-256 integrity traces over a canonical serialization subset; host-authoritative events; snapshots and bounded replay; structured errors; content-provenance envelope |
| Optional, negotiated capabilities | Formation rendering; presentation states; spatial navigation; mission workspace (mini-SKG); in-mission finding exchange; geometric glyphs; hidden operation; checkpoint export and restore |
| Deferred past v1 | Live cross-engine migration of in-flight missions; more than one engine per host; remote or networked engines; fleets spanning hosts; independently credentialed workers; asynchronous capability handles; mandatory graphical rendering; generalized distributed orchestration |

Optional at the protocol level does not mean abandoned at the product level: the MORB Fleet Formation Designer is a committed Desktop Orbot feature, negotiated as a richer capability profile. Existing motion and MORB presentation code is preserved until a verified migration plan exists.

## 5. Identity, authority and trust

### 5.1 Three identities

| Identity | Purpose | Authority |
| --- | --- | --- |
| Engine instance + ownership epoch | Authenticates the engine and its current lease | Runtime identity only; no execution rights by itself |
| Grant (proposal or bound, versioned) | Describes, then authorizes, one mission | Only a bound grant authorizes, and only through the broker |
| Worker identity | Attributes work, findings and events | None of its own |

### 5.2 Grant proposals and bound grants

- A **grant proposal** is produced at Assign. It names the mission, proposed workers, task split and requested capabilities. A proposal MUST NOT be usable to answer any authorization question.
- A **bound grant** is produced only at Deploy, after approval (§10). The host binds each approved worker identity to its scope, registers the grant through governance and the Vault, and stamps it with the current epoch and a revision number.
- A worker scope MUST be a subset of its bound grant. The engine cannot change scopes. Any change is a new grant revision; the previous revision is revoked.
- Grant objects MUST be deeply immutable once validated. An implementation that keeps a reference to caller-owned mutable data is non-conforming.

### 5.3 Execution and finalization scopes

Every bound grant contains two independently enforced scopes:

| Scope | Permits | On Cancel |
| --- | --- | --- |
| Execution | Invoking the worker's approved capabilities | Revoked immediately |
| Finalization | Submitting terminal reports and evidence already acquired before revocation | Stays open for a bounded finalization window, then closes |

The finalization scope MUST NOT permit tool invocation, new evidence acquisition, or any consequential action.

### 5.4 Capability broker

Every consequential effect is a host-provided capability. The engine sends RequestCapability carrying its epoch, bound-grant id and revision, worker id, and an `invocation_id` (§6.2). At that moment the host evaluates the active lease, the grant revision, the worker's execution scope, current policy, revocation and resource limits, then performs or refuses the call. The engine never holds authority, and the engine is never handed a privileged provider (the Vault writer, a model runtime, a tool) directly.

### 5.5 SKG intake

The host's report-intake service is the single registered principal in CALI's SKG. Engines have no SKG access. Each report reference enters with grant, worker and task attribution as metadata, under the SKG's ordinary verification rules.

### 5.6 Trust profile

The engine MAY request a profile in Discover; the host determines and reports the **effective** profile from how the process was actually launched and restricted. A manifest claiming isolation is not evidence of isolation.

- `trusted_local` — first-party engine with ordinary local privileges. Contract boundaries rely partly on trusting its code; an engine running as the same OS user can read whatever that user can read.
- `isolated` — engine under host-verified restrictions that block direct access to protected capabilities, credentials and vault storage.

Third-party engines MUST have the `isolated` profile before receiving consequential capabilities. DockStation MUST show the effective profile. A capability broker alone does not make an unrestricted local engine secure.

## 6. Messages, identities and errors

### 6.1 Envelope

Every message carries: contract version, `request_id`, sender id, fleet id, epoch (decimal string), and mission id where relevant.

### 6.2 Two kinds of identity

| Identifier | Identifies | Lifetime |
| --- | --- | --- |
| `request_id` | One protocol message, for response deduplication | One request and its retries |
| `invocation_id` | One intended consequential operation | Across retries, timeouts, crashes and reconciliation |

They MUST be distinct types; neither may be substituted for the other.

### 6.3 Idempotency

Every mutating command is idempotent under its `request_id` while the host retains that request's record: a duplicate returns the existing result. This is protocol-level deduplication only. It is not a guarantee of exactly-once execution of external effects, which §14 handles through invocation records.

### 6.4 Errors

Every refusal or malformed input MUST surface as a structured refusal with a reason code (in code: `ProtocolViolation(reason_code)`), never as a language-level exception. Reason codes are lowercase snake_case, optionally followed by `:detail` fields. Initial codes include `missing_envelope_field`, `invalid_epoch`, `stale_epoch`, `unknown_state`, `invalid_worker_transition`, `invalid_fleet_transition`, `worker_scope_exceeds_grant`, `grant_not_bound`, `execution_revoked`, `finalization_closed`, `preservation_backlog`, `record_conflict`, `evidence_unresolved`, `capability_refused`, `outcome_unknown`.

## 7. Operations and events

| Operation or event | Direction | Requirement | Meaning |
| --- | --- | --- | --- |
| Discover | Host → engine | Mandatory | Contract version, capabilities, requested trust profile |
| SetFleetState | Host → engine | Mandatory | Desired fleet state and its revision; engine acknowledges the effective state |
| Assign | Host → engine | Mandatory | Prepare a mission; engine returns task records and a grant proposal. Authorizes nothing. |
| Deploy | Host → engine | Mandatory | Delivers the bound grant after approval; execution may begin |
| Snapshot | Host → engine | Mandatory | Engine's current view, for reconciliation |
| Recall | Host → engine | Mandatory | Chosen missions or workers end gracefully; fleet stays ACTIVE |
| Cancel | Host → engine | Mandatory | Execution scope revoked first; finalization window opens; Cancel of all sets STOPPED |
| Drain | Host → engine | Mandatory | Whole fleet: refuse new work, apply drain policy, then release the lease |
| Heartbeat | Engine → host | Mandatory | Engine liveness, lease renewal, and a per-worker liveness summary |
| RequestCapability | Engine → host | Mandatory | Synchronous brokered call with `invocation_id` and timeout semantics (§14) |
| SubmitReport | Engine → host | Mandatory | Evidence item, worker report, or finalization report for custody (§12) |
| ReleaseLease | Engine → host | Mandatory | Orderly end of ownership after drain |
| operational_state_changed | Engine → host | Mandatory | Engine claim; advisory until the host reconciles it |
| finding_shared | Engine → host | Optional | Mission-scoped finding exchange; republished by the host |
| worker_state | Host stream | Mandatory | Authoritative, reconciled assignment state with an increasing revision |
| fleet_state_changed | Host stream | Mandatory | Requested state, last confirmed effective state, any communication failure |
| mission_assigned | Host stream | Mandatory | Mission, workers, approved split |
| report_accepted | Host stream | Mandatory | Durably staged; preservation pending |
| result_delivered | Host stream | Mandatory | A.I.M.S. receipt confirmed |
| mission_terminal | Host stream | Mandatory | Operational outcome plus preservation status |
| authority_changed | Host stream | Mandatory | Grant revision, revocation, scope or finalization-window change |
| error | Host stream | Mandatory | Structured error; engine errors are reported to the host and republished after validation |
| presentation_state_changed | Local only | Optional | Visual state; never part of the operational stream |

**Single authoritative pathway.** Operational events flow engine → host validation and reconciliation → host event stream → DockStation. Subscribers MUST NOT consume raw engine events as operational truth. Presentation events stay local and transient and MUST NOT imply mission success, evidence custody, or execution permission.

## 8. Lifecycles

### 8.1 Assignment lifecycle (normative)

The state machine below belongs to an **assignment** (one worker's part of one mission). Terminal states are final; a worker's next mission is a new assignment.

| State | Meaning |
| --- | --- |
| ASSIGNED | Assignment prepared by Assign; no execution authorized |
| RUNNING | Bound grant delivered by Deploy; worker executing its approved task |
| COMPLETING | Work ended; final report being prepared or submitted |
| COMPLETED | Worker finished its assignment successfully (work outcome only) |
| FAILED | Worker could not finish; includes engine or lease loss |
| CANCELLED | Assignment ended by cancellation |

| From | Permitted next states |
| --- | --- |
| ASSIGNED | RUNNING (only via Deploy with a bound grant), CANCELLED, FAILED |
| RUNNING | COMPLETING, FAILED, CANCELLED |
| COMPLETING | COMPLETED, FAILED, CANCELLED |
| COMPLETED, FAILED, CANCELLED | none |

Every other transition MUST be refused with `invalid_worker_transition`. Unknown states MUST be refused with `unknown_state`. An engine's claim of a transition is advisory; only the host's reconciled `worker_state` is authoritative. COMPLETED describes the work outcome, never evidence preservation.

### 8.2 Worker availability

Availability is a property of the worker, not of an assignment: a worker is **available** when it has no non-terminal assignment and the engine's heartbeat lists it as live; **busy** when it has a non-terminal assignment; **unavailable** otherwise.

### 8.3 Fleet lifecycle

The host owns the desired fleet state and its revision; the engine acknowledges what it has actually reached.

| State | Engine behavior | Permitted next states |
| --- | --- | --- |
| OFF | No assignments or deployments accepted | ACTIVE |
| ACTIVE | Authorized assignments and deployments permitted | DRAINING, STOPPED |
| DRAINING | New work refused; existing work follows drain policy | OFF, STOPPED |
| STOPPED | New work refused; applicable operations cancelled or halted | OFF |

If the engine is unreachable, the host reports the requested state, the last confirmed effective state and the communication failure. A stop request is not proof an external operation stopped; for brokered capabilities the host revokes access immediately, even when the engine is unresponsive.

### 8.4 Liveness

The engine heartbeat carries a liveness summary for every worker with a non-terminal assignment. A worker missing from the summary, or reported stalled, past a host-configured deadline is declared FAILED by the host, even while the engine itself is healthy. No per-worker transport is required.

### 8.5 Termination and preservation

Every assigned mission reaches a known outcome, and every deployed worker gets an auditable terminal disposition:

- A completed worker submits its own work report.
- A deployed worker that fails, crashes or is cancelled gets a **host-authored terminal record**: last verified state, grant revision, epoch, last heartbeat, failure reason, and any invocations with unknown outcome. The host names itself as author and never attributes findings to a worker that did not produce them. A cancelled worker MAY also submit a finalization report within its window.
- A mission cancelled before Deploy gets an authoritative lifecycle record, not a fabricated worker report.
- Mission outcome resolves from its assignments: Completed, Partially completed, Failed or Cancelled.

| Operational outcome | Preservation status | Meaning |
| --- | --- | --- |
| Completed | Sealed | Work done; report preserved |
| Completed | Pending | Work done; preservation outstanding |
| Failed | Sealed | Host terminal record preserved |
| Failed | Pending | Host terminal record staged, awaiting the vault |
| Cancelled | Sealed | Cancellation, finalization report and partial results preserved |
| Any | Failed | Preservation definitively refused; owner alerted |
| Any | Unpreserved | Preservation deadline passed; owner alerted; obligation still open |
| — | Not applicable | Only where no deployed work occurred |

Unpreserved never triggers deletion or abandonment of a staged record. The host never fabricates a successful report.

## 9. Missions

A mission is a filled-in template. A template defines: objective; mission type (research, diagnostics, pointer, utility); workers and each worker's task; evidence required; capabilities each worker's scope needs; deliverables and completion conditions; and whether a worker may work hidden.

Joint missions:

1. Each worker has its own assignment, identity and reports; a joint mission is never one shared record.
2. Workers MAY share findings within the mission's scope; each share is a `finding_shared` event.
3. Each worker finishes on its own, without waiting for the others.
4. The mission is terminal when every assignment is terminal; preservation status is tracked separately.

When several workers of one type are requested, the engine proposes a task split (for example: service health, logs, interface contracts, contradiction check). Task divisions are tasks, not new worker types.

## 10. Assign → approval → Deploy

1. **Assign.** The host sends the mission. The engine returns assignments in ASSIGNED and a grant proposal. Nothing is authorized.
2. **Approval.** The owner (manual deployment) or CALI within an owner-authorized scope (automatic deployment) approves the proposal, possibly narrowed.
3. **Deploy.** The host binds the approved worker identities to their scopes, registers the bound grant through governance and the Vault, records it in the ledger, and sends it with Deploy. Assignments move to RUNNING.
4. **Change.** Any later scope change is a new grant revision; the old revision is revoked and `authority_changed` is published.

A test MUST show that a grant proposal alone never authorizes any capability.

## 11. Cancellation and finalization

1. The host revokes the execution scope and records the revocation.
2. The host publishes `authority_changed` and opens the finalization window (host-configured duration).
3. The host signals Cancel to the engine.
4. Within the window, a worker MAY submit a finalization report with evidence acquired before revocation. Brokered requests are refused with `execution_revoked`; submissions after the window are refused with `finalization_closed`.
5. Independently of the worker, the host writes its own terminal record.
6. Reports already accepted before the window closed continue through preservation.

Operations already running at revocation are reported as stopped, not stoppable, or outcome unknown.

## 12. Report custody

### 12.1 Record identities

| Record | Idempotency identity |
| --- | --- |
| Evidence item | `evidence` + mission id + worker id + evidence item id |
| Worker report (work or finalization) | `report` + mission id + worker id + report sequence |
| Host terminal record | `host_terminal` + mission id + worker id + host record id |

The record type is part of the canonical identity domain, so records of different kinds never collide.

### 12.2 Custody sequence

The host takes custody of a submission the moment it durably stages it; from then on preservation is the host's responsibility, even if the engine disappears or is replaced.

1. The engine calls SubmitReport for evidence items, then for the report that references them.
2. The host authenticates lease and epoch, validates the bound grant (or finalization scope), worker attribution and schema, and computes all digests itself.
3. The host verifies that every evidence reference in a report resolves to a staged or sealed evidence item with the expected digest (`evidence_unresolved` otherwise).
4. The host durably stages the submission in a bounded preservation queue, and only then returns `report_accepted`. A full queue refuses with `preservation_backlog`; nothing accepted is ever dropped.
5. A.I.M.S. seals referenced evidence first; a report is never sealed while mandatory evidence is unpreserved.
6. A.I.M.S. seals the report and returns its authenticated receipt.
7. The host records the receipt in its ledger, publishes `result_delivered`, and removes the staged copy under verified cleanup policy.

### 12.3 Rules

- Before acknowledgement, the engine keeps enough to retry or report failure. A submission lost before acknowledgement is lost, and the host terminal record says so.
- Same identity and same digest returns the existing acknowledgement or receipt; same identity and different digest is refused with `record_conflict` and logged as a possible tamper signal. After an ambiguous vault outcome, the host reconciles by identity and digest before trying again.
- The staging queue is transport, not a vault; staged records are non-canonical until A.I.M.S. accepts them.
- A sealed evidence item whose report later fails may remain, with provenance tracked; orphan clean-up is an explicit, recorded decision.
- Mission workspace retention starts only when the receipt exists, and a workspace is never purged while preservation is unconfirmed.

### 12.4 Report contents

Report id; record identity; grant id and revision; engine id, engine version, contract version; result with stated uncertainty; evidence references; findings shared or received; invocation ids used; the integrity trace; a provenance envelope for every external finding; and timestamps kept in three separate categories: **worker-reported** (claims about when work happened), **host-observed** (when the host saw events), and **vault-sealed** (from the receipt). These are never interchangeable; a vault timestamp proves when custody was sealed, not when work occurred.

### 12.5 Provenance envelope

For external content: origin and source reference, acquisition method and time, trust classification, content digest, worker and mission attribution, and whether the content is a quotation, observation, inference or proposed action. External content is data: neither a MORB nor CALI may treat instructions inside it as authorization. External-origin findings enter CALI's SKG at most as "reported". A proposed action is never executable. Recording a conclusion does not make it true.

## 13. Integrity trace

### 13.1 Mechanisms

| Mechanism | Responsibility | Never used for |
| --- | --- | --- |
| SHA-256 integrity chain (mandatory) | Shows whether the recorded sequence and contents changed | Judging meaning or similarity |
| A.I.M.S. authenticated receipt (mandatory) | Custody and acceptance: record digest, vault timestamp, vault record id, sealing algorithm, key id | — |
| Geometric glyph signature (optional) | Semantic similarity and relational retrieval | Proof of integrity, authorship or truth |

The absence of a glyph never invalidates a cryptographically intact report.

### 13.2 Digest input

Exactly: serialization algorithm and version, digest algorithm, domain identifier, record type, mission and worker ids, sequence number, previous digest, and the canonical entry content. The digest field is never part of its own input. Digests are lowercase hexadecimal.

### 13.3 Canonical serialization subset

The contract defines a deliberately restricted subset of JSON whose canonical form coincides with RFC 8785 for every value the subset admits. Implementations MUST reject anything outside the subset before hashing, identically in every language, and MUST NOT claim unrestricted RFC 8785 compatibility.

- Types: objects with string keys, arrays, strings, integers, `true`, `false`, `null`. No floating-point numbers anywhere.
- Integers within ±(2⁵³ − 1). Larger identifiers, including epochs, travel as decimal strings.
- Decimals, including glyph coordinates, travel as canonical fixed-precision decimal strings (format defined with the glyph capability).
- Strings are valid Unicode; lone surrogates are rejected. Key order and string escaping follow RFC 8785.
- Timestamps use one normalized UTC format: `YYYY-MM-DDTHH:MM:SS.ffffffZ`.
- Output is verified against published canonicalization fixtures, including non-ASCII and escaping cases, in Python and at least one other language.
- The genesis entry is derived deterministically per mission from a versioned domain plus the mission identity; never a global constant.
- Python's built-in `hash()` MUST NOT be used anywhere in integrity computation.

### 13.4 Glyph

The TPC/ACP 18-dimensional glyph is the intended implementation once a read-only inspection confirms it encodes MORB findings faithfully, including a test that distinct findings yield distinct glyphs. There is no separate MORB glyph family.

## 14. Errors and recovery

| Information | Persistence |
| --- | --- |
| Formation movement, visual effects | Transient |
| UI events, progress | Host snapshot plus a short replay window |
| Assignments, grant proposals and bound grants, revocations, finalization windows, lease epochs, invocation records, terminal outcomes, receipts | Minimal durable host mission ledger |
| Accepted reports and evidence | Canonical A.I.M.S. vault |

The ledger is operational state, not canonical evidence and not CALI's SKG; it uses the host's existing durable storage. Host snapshots are authoritative; replay is a convenience, not a recovery mechanism.

**Invocation records.** Before invoking a consequential capability, the host durably records the `invocation_id` with the grant revision, worker, capability, and arguments digest. Afterwards it records the confirmed outcome. A crash between the two leaves the invocation explicitly unresolved.

**Timeouts.** Two cases are distinguished: *refused before execution* (the host knows it never ran) and *outcome unknown* (it may have started). Every host capability declares whether it is idempotent. Idempotent invocations may be retried under the same `invocation_id` per declared policy. A non-idempotent invocation with unknown outcome is first reconciled against available external evidence; if that is impossible, it requires a new authorized decision, never a blind retry.

**Restarts.** On restart the host rebuilds operational state from the ledger and staging queue, resumes preservation, and reconciles everything pending. DockStation reconnects with a snapshot plus events since its last sequence number, or the snapshot alone when the gap is outside the replay window. It never shows work as active or complete without host confirmation. Authoritative updates carry increasing revisions so stale messages cannot overwrite newer state.

## 15. Epochs, leases and replacement

### 15.1 Fencing rule

> Ownership epochs fence engine-originated requests and execution authority. They do not invalidate evidence or reports already accepted into the host's durable preservation queue under a previously valid epoch. A.I.M.S. accepts preservation operations only through the authorized host writer and validates the host's authority and the recorded provenance of the staged submission, not the originating engine's lease.

- The epoch is a decimal string, durable across host restarts, strictly increasing, and never reused.
- The host advances and durably records the epoch before admitting a replacement engine.
- The host grants the lease with the epoch and its capability list in one message; the engine renews it by heartbeat.
- Engine requests carrying an older epoch are refused with `stale_epoch`. An engine that restarts after a crash gets a new epoch; an old engine never regains authority by reconnecting with previously valid credentials.
- If a lease lapses, the host treats the engine as failed: its non-terminal assignments get host terminal records, or are restored from a checkpoint if negotiated.

### 15.2 Replacement protocol

1. The owner starts the replacement; the host sends Drain; the fleet goes to DRAINING and refuses new work.
2. Outstanding missions finish, checkpoint, or are safely cancelled within the configurable drain window. The owner can cancel at once; a forced cancellation leaves an audit record.
3. The engine sends ReleaseLease; the host records it, revokes the lease, and durably advances the epoch.
4. The new engine answers Discover; the host checks contract and capability compatibility and grants the lease.
5. If both engines negotiated checkpoint restoration with the same checkpoint schema version, the new engine imports the checkpoint; the host records which epoch produced it and allows exactly one restore. Otherwise the new engine starts with an empty fleet.
6. The host sets the fleet to ACTIVE.

ReleaseLease is an optimisation, not a prerequisite: a crashed or hung engine is fenced without its cooperation. Accepted custody continues regardless (§12). A replacement engine never submits a predecessor's unacknowledged work. Rollback follows the same steps; sealed vault records are untouched.

## 16. Capabilities

Capabilities run both ways; anything not announced is absent.

| Direction | Capability | Notes |
| --- | --- | --- |
| Host provides | Inference | Brokered access to a shared local model; workers need no model of their own |
| Host provides | Spatial environment | Host-resolved target handles for desktop windows or web elements |
| Host provides | Tools | Each behind its own scope, invoked only through the broker |
| Host provides | Host Report Ingress | Authenticated, scoped evidence and report submission; host-controlled staging and A.I.M.S. preservation. The engine calls SubmitReport; only the host's report service invokes the canonical Vault writer. |
| Engine announces | Formation rendering | Presets, custom slot layouts |
| Engine announces | Mission workspace | Mini-SKG per mission |
| Engine announces | Spatial navigation | Routes, targets, monitor crossings |
| Engine announces | Checkpoint restoration | Schema version for resuming in-flight missions |

Every capability carries its own version; an older host ignores unknown capabilities; a host never calls a capability the engine did not announce. Contract v1 is grounded in Desktop Orbot and a simulated host; other hosts extend it through new capabilities when they become real.

## 17. Presentation

- The formation designer and visible fleet consume the host stream (`worker_state`, `fleet_state_changed`, `result_delivered`, `mission_terminal`) and host snapshots, plus local `presentation_state_changed`. Never raw engine claims.
- The ORB's handoff pulse plays on the host's `result_delivered`, never on a worker's arrival.
- Every visible MORB corresponds to a real worker or an explicitly idle reserve worker; a preview or demonstration says so on screen.
- Visible and operational are separate: hiding the fleet never changes operational state.
- Operational behavior overrides formation style when a task requires it.
- Formation slots are logical offsets from the ORB anchor; spatial targets are host-resolved handles, never pixel coordinates; the host adapter maps them across monitors and scale factors.
- On Desktop Orbot the fleet has its own native window and position writer, never the primary ORB's.
- The fleet yields to the owner's work using the same signals as the ORB's interaction hold.

## 18. Conformance

An engine is called replaceable only when every test passes against the same, unmodified host. Tests are written with the standard-library `unittest` and run on Python 3.10–3.12.

**Replaceability and authority**

- [ ] Two different engine implementations operate through the same unmodified host contract.
- [ ] A grant proposal alone never authorizes any capability.
- [ ] An unauthorized capability request is refused; a worker cannot exceed its scope inside a valid bound grant.
- [ ] A validated grant cannot be widened by mutating the data it was built from.
- [ ] An old engine cannot act after its epoch is revoked, including after reconnecting and after a host restart.
- [ ] An engine cannot reach the canonical Vault writer except through Host Report Ingress, under the effective trust profile.

**Lifecycle and events**

- [ ] Every state pair outside the permitted tables (§8.1, §8.3) is refused; unknown states are refused.
- [ ] Engine state claims cannot bypass the host's authoritative state machine.
- [ ] A stalled worker is detected while its engine stays healthy.
- [ ] A reconnect with a stale event revision does not overwrite the current snapshot; DockStation never shows invented active or completed work.
- [ ] Malformed inputs surface as structured refusals, never language exceptions.

**Custody and integrity**

- [ ] Cancel during partial reporting: execution ends, permitted finalization reporting succeeds, later submissions are refused.
- [ ] A report acknowledged by the host survives engine replacement and is eventually sealed.
- [ ] Duplicate submissions produce one receipt; a changed digest under the same identity is refused.
- [ ] Evidence, report and host-terminal identities never collide.
- [ ] A report cannot seal while referenced evidence is unresolved or unpreserved.
- [ ] Queue saturation applies backpressure without dropping accepted submissions.
- [ ] Staged reports survive a host restart and are reconciled.
- [ ] A crashed worker reaches a terminal state with a correctly attributed host record.
- [ ] A consequential operation with unknown outcome is not silently repeated.
- [ ] A forged or altered digest fails validation; a sealed report still verifies after runtime restart, engine replacement and host restart.
- [ ] Canonical serialization fixtures produce identical digests in Python and at least one other language; inputs outside the subset are rejected identically.

**Presentation**

- [ ] The same formation designer drives both engines' fleets from host events alone.

Passing in simulation proves the contract, not authorized production behavior; that also requires Orbot's governance and Vault authority paths to be operationally verified.

## 19. Owner approval register

Bryan Spruk authorized engineering work on 2026-11-12. That authorization is not approval of the individual values below: each is a recommended value, pending his explicit confirmation. Implementations use them as configurable defaults until then.

| # | Decision | Recommended value | Status |
| --- | --- | --- | --- |
| 1 | Glyph | One glyph family; TPC/ACP 18-dimensional glyph via a versioned interface | Pending; also conditional on read-only inspection (§13.4) |
| 2 | Canonical serialization | Restricted subset coinciding with RFC 8785 (§13.3), SHA-256, per-mission genesis | Pending |
| 3 | Host seal | Authenticated A.I.M.S. receipt after host validation | Pending |
| 4 | Grant authority | Cognitive/Governance decides; the Vault registers and validates | Pending |
| 5 | Mission workspace retention | 7 days after seal; never purged while unconfirmed | Pending; configurable |
| 6 | Drain window | 5 minutes | Pending; configurable |
| 7 | Large evidence | Separate vault records referenced by digest and id | Pending |
| 8 | Version 1 fleet | 4 visible, up to 8 concurrent; Orbit, Escort, Triad, Stealth, Hidden but Active, Custom | Pending; operational configuration, not contract |
| 9 | First-engine trust profile | `trusted_local`, shown in DockStation; `isolated` for third parties | Pending |
| 10 | Receipt authentication | Ed25519 signature by the vault | Pending |
| 11 | Preservation deadline | 24 hours before Unpreserved and owner alert | Pending; Claude's recommended default |

## 20. Changes from revision 2

| Change | Section | Source |
| --- | --- | --- |
| Assign → approval → Deploy; proposals vs bound grants | §5.2, §10 | GPT-6 Round 5 #1 |
| Execution and finalization scopes; cancellation window | §5.3, §11 | GPT-6 Round 5 #2 |
| Record-type namespaces; evidence resolution check | §12.1, §12.2 | GPT-6 Round 5 #3 |
| Fencing rule; durable, never-reused epochs | §15.1 | GPT-6 Round 5 #4 |
| Normative state and transition tables; per-worker liveness | §8.1, §8.4 | GPT-6 Round 5 #5 |
| `invocation_id` vs `request_id`; deduplication wording | §6.2, §6.3, §14 | GPT-6 Round 5 #6 |
| Host Report Ingress wording | §16 | GPT-6 Round 5 #7 |
| Single host event pathway; three timestamp categories | §7, §12.4 | GPT-6 Round 5 #8 |
| Added conformance cases; glyph decimals as strings; ±(2⁵³ − 1) | §18, §13.3 | GPT-6 Round 5 #9 |
| Assignment lifecycle separated from worker availability; ASSIGNED → FAILED | §8.1, §8.2 | Claude review of PR #1 |
| Deep immutability of grants; structured refusals only | §5.2, §6.4 | Claude review of PR #1 |
| Restricted canonical subset, honestly not "full RFC 8785" | §13.3 | GPT-6 implementation round 2 |
| Owner register marked pending: engineering authorization is not value approval | §19, status | GPT-6 review of PR #2 |

Revision 2's resolved-disagreements record stands; the points above were agreed without dispute.
