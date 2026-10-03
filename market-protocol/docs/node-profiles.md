# Node and service profiles

Normative module. Blockchain verification mode and network services are independent
choices. Switching either MUST preserve seller identity and accepted obligations.

| Mode | Verification | Trust and cost disclosure |
|---|---|---|
| Managed | Provider submits/reads registry operations | Provider identity, delegation, quotas, receipts, exit/export path |
| Light | Chain-profile light protocol verifies accepted state proofs | Checkpoint bootstrap, consensus assumptions, data availability |
| Pruned full | Validates the selected chain and retains required current state | Initial sync, active state, pruning and recovery requirements |

An ordinary wallet calling a trusted RPC MUST NOT claim light verification. Keeping
only one's catalog MUST NOT be described as a full blockchain node. Archive and
validator functions are separate and optional.

An index service declares categories, regions, document limits, freshness policy,
search quotas and prices. A content service declares allowed data, versions, storage
duration, deletion/rights handling, bytes and bandwidth. Neither requires indexing
or storing the whole commerce network.

Operators MUST reserve resource budgets for the storefront and cap optional services.
If disk, CPU or memory limits are reached, stop accepting additional work or report
unavailability; silently bypassing required chain verification is prohibited.
Private keys for publishing, spending and administration MUST be separable.

## Measurement plan, not measured guarantees

Light mode target: a small 2-vCPU, 2–4-GB-RAM VDS alongside a small store, without a
local LLM or global index. Feasibility depends on the chosen chain and workload.
Measure steady memory, proof validation, update bursts, bandwidth, disk growth,
queue recovery and remaining storefront capacity.

Full mode has no claimed small-VDS guarantee. Measure initial sync, total-chain
verification load, active state, pruning, snapshots and restore time on the actual
candidate network. Small local devnet results do not establish mainnet requirements.

The benchmark workload must state catalog/offer counts, update frequency, document
sizes, query mix, concurrent users, network latency and chain load. Publish failure
thresholds and hardware with results. If no candidate chain meets the light/full
requirements, report the mismatch rather than renaming an RPC client.
