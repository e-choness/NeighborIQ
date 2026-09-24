# 0005 — Functional Source License (FSL-1.1-ALv2)

**Status:** Accepted (2026-09)

## Context

NeighborIQ was MIT-licensed. It is being built as a real product for small investors, who self-host it or use
a hosted version. MIT lets anyone, including a well-funded competitor, run the code as a paid hosted service
without contributing back. The copyright is held essentially by one maintainer, so the licence can change for
future versions. Code already released under MIT stays MIT.

Options considered:

| Licence | Investors self-host freely | Stops closed SaaS clones | OSI open source | Notes |
|---|---|---|---|---|
| MIT (status quo) | Yes | No | Yes | Maximum adoption, no protection |
| Apache-2.0 | Yes | No | Yes | MIT plus patent grant and trademark clause |
| AGPL-3.0 | Yes | Partly: clones must publish source | Yes | Many companies avoid AGPL; dual licensing needs a CLA |
| BUSL-1.1 | Depends on the Additional Use Grant | Yes | No | Flexible but custom terms; up to 4 years to convert |
| **FSL-1.1-ALv2** | **Yes** (internal use explicitly permitted) | **Yes** | No (source-available) | Fixed, standard terms; converts to Apache-2.0 after 2 years |
| PolyForm Noncommercial | No (a rental business is commercial) | Yes | No | Wrong fit for the users |

## Decision

License NeighborIQ under **FSL-1.1-ALv2** from the commit after `4c7146f` (the last MIT-licensed commit). Data keeps its publishers' licences.
Contributions are accepted under the same terms.

## Consequences

- Investors, companies, educators and consultants can use, modify and self-host NeighborIQ. Only offering it,
  or a substitute built from it, as a commercial product or service is excluded.
- Every release becomes Apache-2.0 two years after it ships, so no version stays restricted indefinitely.
- NeighborIQ is "source-available", not "open source" in the OSI sense; the README and docs say so.
- To sell a different licence to a company later, the maintainer needs rights to all contributed code. Accepting
  outside contributions under the FSL alone may require a contributor licence agreement at that point.
- Dependencies are permissive (MIT, BSD, ISC, Apache-2.0), weak-copyleft (psycopg2, LGPL) or font licences
  (Geist, SIL OFL), all compatible with distributing NeighborIQ under the FSL.
