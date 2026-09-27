# Measurements

How much of a model's input ADDP saves, measured on synthetic data. This is not a
task-level benchmark: it counts what a model would read, not whether it decides well.

## Setup

`python tools/measure_context.py` uses the reference implementation to build an index of
20 synthetic offers from 20 publishers, runs a query, and forms the decision view a
runtime would give a model. No network connections, no model calls. The first run needs
`--download` once, to fetch two public tokenizer vocabularies into `build/tiktoken`.

Task: the three cheapest new black offers, under a EUR 350 limit on the total. The
index filters on currency and condition and returns 16 of the 20 offers. The runtime
filters colour, ranks by price and keeps three.

Outputs: [measurements.json](measurements.json) and the
[fixture](../examples/context-budget.json) with the query, the index response and the
decision view.

## Result

| Model input | Bytes | Gzip | cl100k_base | o200k_base |
|---|---:|---:|---:|---:|
| Index response, 16 candidates, indented JSON | 10,492 | 632 | 3,215 | 3,199 |
| Same, compact JSON | 7,496 | 576 | 2,226 | 2,243 |
| Same data, CSV | 3,616 | 465 | 1,414 | 1,414 |
| Decision view, 3 candidates | 1,127 | 364 | 315 | 318 |

- **Format.** The same data as CSV instead of compact JSON takes about 36% fewer
  tokens. The script checks that the CSV converts back to exactly the same records.
- **Less data.** The decision view is about 7 times smaller than the compact JSON
  response. That is not compression: the runtime did the filtering and ranking the model
  would otherwise do, and dropped the other 13 candidates. The view still states that
  the delivered total is unknown, that the `max_total` constraint is open, and that the
  data are index claims.
- **Transport compression.** Gzip barely separates the formats. It saves network bytes,
  not model input.

## Not measured

- The tokenizers of most commercial models are not public. The two above are proxies;
  other models will count differently.
- Whether a model picks correctly from the decision view. The saving only matters if the
  success rate does not drop. That needs task-level runs on named models, counting
  retries, helper calls and failed tasks.
- Heterogeneous or deeply nested data, where CSV does not fit.
