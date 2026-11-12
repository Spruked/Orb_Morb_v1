# MORB Runtime

Portable, replaceable worker runtime for the ORBS ecosystem.

**Status:** engineering foundation only; not connected to production ORB, CALI, DockStation, or A.I.M.S. No consequential execution authority is implemented or implied.

## Architecture

- The host ORB owns identity, authorization, capability execution, and canonical A.I.M.S. preservation.
- MORB Runtime owns bounded mission work, worker scheduling, ephemeral workspaces, and optional fleet presentation.
- A separately versioned protocol contract joins host and engine.
- The host must verify actual isolation before enabling third-party consequential capabilities.

**Doctrine:** ORB owns the relationship. MORB owns the work. The contract survives either implementation.

Development will proceed through reviewed branches and conformance tests. This repository must never contain credentials, private Vault records, or live user data.
