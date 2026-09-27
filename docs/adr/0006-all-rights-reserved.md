# 0006 — All rights reserved

**Status:** Accepted (2026-09). Supersedes [0005](0005-license-fsl.md).

## Context

NeighborIQ moved from MIT to FSL-1.1-ALv2 ([ADR 0005](0005-license-fsl.md)) to stop closed SaaS clones while
letting investors self-host. The FSL still grants broad rights to anyone, and every release converts to
Apache-2.0 after two years, which removes control over the code for good. The copyright is held by one
maintainer, so future versions can be relicensed.

## Decision

From the commit after `50c9118`, NeighborIQ is proprietary: all rights reserved. The source stays visible, but
using, copying, modifying, hosting or distributing it requires the copyright holder's written permission. Data
keeps its publishers' licences.

## Consequences

- No one may self-host, fork or modify new versions without permission; the maintainer grants rights case by case.
- Licences already granted cannot be revoked. Copies obtained under MIT (up to `4c7146f`) keep those terms, and
  copies obtained under FSL-1.1-ALv2 (up to `50c9118`) keep them, including each version's Apache-2.0
  conversion two years after its release.
- Outside contributions need a copyright assignment or an unrestricted licence to the maintainer before merge.
- npm packages declare `"license": "UNLICENSED"`, the npm convention for proprietary code.
- Dependencies (MIT, BSD, ISC, Apache-2.0, LGPL, SIL OFL) remain compatible; their own notices still apply
  when NeighborIQ is distributed.
